# worker/worker.py

import cv2
import time
import requests
from confluent_kafka import Producer
import json
from ultralytics import YOLO
import math
from collections import defaultdict
import os
import glob
import shutil
import statistics
# USUNIETO: import mysql.connector (powodowal blad ModuleNotFoundError)
import hashlib

API_URL = "http://video-api-service/simulate_detection"
CAMERAS = ["KAM-01"]
FRAME_INTERVAL = 5  # <-- Zmieniajac te cyfre, zmieniasz czestotliwosc analizy w calym skrypcie!

def get_file_hash(filepath):
    """Funkcja generujaca unikalny odcisk palca (MD5) dla pliku wideo."""
    hasher = hashlib.md5()
    with open(filepath, 'rb') as afile:
        buf = afile.read(65536) # Czytamy w paczkach po 64KB, by oszczedzac RAM
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(65536)
    return hasher.hexdigest()

def send_to_kafka(payload):
    try:
        conf = {'bootstrap.servers': 'kafka-service:9092'}
        producer = Producer(conf)
        producer.produce('detections_topic', value=json.dumps(payload).encode('utf-8'))
        producer.flush()
    except Exception as e:
        pass # Ignorujemy drobne bledy sieci, zeby nie zasmiecac terminala

def process_video_stream(video_path, output_mp4_name):
    
    print(f"Inicjalizacja AI dla pliku: {video_path} (Hash ID: {output_mp4_name})...")
    
    # --- NOWY KOD (POPRAWIONY): SYGNALIZACJA STARTU PRZEZ KAFKE ---
    # Zamiast laczyc sie z baza, wysylamy specjalny komunikat "init", ktory odbierze API
    try:
        send_to_kafka({
            "video_id": output_mp4_name,
            "camera_id": CAMERAS[0],
            "behavior": "init_video_cleanup",
            "frame_number": 0,
            "confidence": 1.0
        })
        print(f"Wyslano sygnal inicjalizacji (cleanup) dla wideo o ID: {output_mp4_name}")
    except Exception as e:
        print(f"Ostrzezenie: Nie udalo sie wyslac sygnalu startu: {e}")
    # --------------------------------------------------------
    
    model = YOLO("yolov8n.pt")
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print("Blad: Nie mozna otworzyc pliku wideo.")
        return
        
    # --- NOWY KOD: PRZYGOTOWANIE ZAPISU WIDEO ---
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    if fps <= 0 or fps > 120: fps = 30 # Poprawione zabezpieczenie przed blednym odczytem FPS
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    
    # Zmieniona sciezka na video-output
    roboczy_avi = f"/app/video-output/roboczy_{output_mp4_name}.avi"
    out = cv2.VideoWriter(roboczy_avi, fourcc, fps, (width, height))
    # --------------------------------------------
        
    frame_count = 0
    
    # --- ZAAWANSOWANE AI: PAMIEC POZYCJI DLA KAZDEGO ID ---
    track_history = defaultdict(lambda: [])
    # ------------------------------------------------------
    
    while cap.isOpened():
        
        ret, frame = cap.read()
        
        if not ret:
            print("Koniec filmu. Proces liczenia zakonczony!")
            break
            
        frame_count += 1
        
        if frame_count > 300: # Limit na sztywno 300 klatek (10s), niezaleznie od FPS
            print("Osiagnieto limit 300 klatek. Konczenie...")
            break
        
        # Opcja C: SLEDZENIE (TRACKING)
        # Wymuszamy zaawansowany tracker BoT-SORT aby wyeliminowac ID Switch
        results = model.track(frame, persist=True, verbose=False, tracker="botsort.yaml")
        result = results[0]
        
        # --- NOWY KOD: RYSOWANIE RAMEK I ZAPIS KLATKI ---
        # result.plot() automatycznie naklada ramki z YOLO na obraz
        annotated_frame = result.plot()
        out.write(annotated_frame)
        # ------------------------------------------------
        
        # Opcja A: ZLICZANIE (COUNTING) i wysylka do bazy
        if frame_count % FRAME_INTERVAL == 0:
            
            people_count = 0
            
            if result.boxes is not None:
                
                # Pobranie wspolrzednych i klas bezposrednio z GPU do pamieci CPU
                boxes = result.boxes.xywh.cpu()
                classes = result.boxes.cls.int().cpu().tolist()
                track_ids = result.boxes.id.int().cpu().tolist() if result.boxes.id is not None else []
                
                # --- KROK 1: ZNALEZIENIE BAGAŻY / PRZEDMIOTÓW W RĘKACH ---
                # Klasy COCO: 24(plecak), 25(parasol), 26(torebka), 28(walizka), 39(butelka), 67(telefon)
                carried_objects = []
                for box, cls in zip(boxes, classes):
                    if int(cls) in [24, 25, 26, 28, 39, 67]:
                        carried_objects.append(box)
                
                # Zbieranie danych o ludziach i ich wektorach
                active_angles = []
                persons_data = []
                
                if track_ids:
                    for box, track_id, cls in zip(boxes, track_ids, classes):
                        if int(cls) == 0: # Klasa 0 to 'person'
                            people_count += 1
                            x, y, w, h = box
                            
                            # --- KROK 2: CZY OSOBA COŚ TRZYMA? ---
                            is_carrying = False
                            for ox, oy, ow, oh in carried_objects:
                                # Proste sprawdzenie czy srodek przedmiotu jest wewnatrz prostokata osoby
                                if (x - w/2 < ox < x + w/2) and (y - h/2 < oy < y + h/2):
                                    is_carrying = True
                                    break
                                    
                            track_history[track_id].append((float(x), float(y)))
                            
                            if len(track_history[track_id]) > 30:
                                track_history[track_id].pop(0)
                                
                            speed = 0.0
                            angle = 0.0
                            
                            # TUTAJ BYL BLAD - zmieniamy na >= 2 zeby nie czekac 5 sekund na obliczenia
                            if len(track_history[track_id]) >= 2: 
                                start_point = track_history[track_id][0]
                                end_point = track_history[track_id][-1]
                                distance = math.hypot(end_point[0] - start_point[0], end_point[1] - start_point[1])
                                speed = distance / len(track_history[track_id])
                                
                                dx = end_point[0] - start_point[0]
                                dy = end_point[1] - start_point[1]
                                angle = math.degrees(math.atan2(dy, dx))
                                
                                # Do glownego nurtu bierzemy tylko tych, ktorzy poruszaja sie dosc szybko
                                if speed > 2.0:
                                    active_angles.append(angle)
                                    
                            persons_data.append({"id": track_id, "speed": speed, "angle": angle, "carrying": is_carrying})
                            
                # --- KROK 3: OBLICZENIE KIERUNKU GŁÓWNEGO NURTU (TŁUMU) ---
                main_flow_angle = None
                if active_angles:
                    main_flow_angle = statistics.median(active_angles)
                    
                # --- KROK 4: KLASYFIKACJA (BIEGACZ VS GAP) ---
                for p in persons_data:
                    role = "PRZECHODZIEN"
                    
                    if p["speed"] >= 4.0: # Regula 1: Predkosc biegu
                        if not p["carrying"]: # Regula 2: Puste rece/brak bagazu
                            if main_flow_angle is not None:
                                # Regula 3: Kierunek zgodny z tlumem (tolerancja 45 stopni)
                                angle_diff = abs(p["angle"] - main_flow_angle)
                                if angle_diff > 180: angle_diff = 360 - angle_diff
                                
                                if angle_diff <= 45:
                                    role = "ZAWODNIK"
                    elif p["speed"] < 2.0:
                        role = "GAP_STOI"
                        
                    now = time.strftime("%H:%M:%S")
                    
                    try:
                        send_to_kafka({
                            "video_id": output_mp4_name,
                            "camera_id": CAMERAS[0], 
                            "person_id": p['id'], 
                            "behavior": role.lower(), 
                            "speed": round(p["speed"], 2), 
                            "frame_number": frame_count,
                            "frame_id": frame_count // FRAME_INTERVAL,
                            "confidence": 0.95
                        })
                    except Exception as e:
                        pass
                        
            now = time.strftime("%H:%M:%S")
            
            # Ogolny status kamery
            payload = {
                "video_id": output_mp4_name,
                "camera_id": CAMERAS[0],
                "person_id": None,
                "behavior": f"wykryto_{people_count}_osob",
                "speed": None,
                "frame_number": frame_count,
                "frame_id": frame_count // FRAME_INTERVAL,
                "confidence": 0.99
            }
            
            try:
                send_to_kafka(payload)
            except Exception as e:
                print(f"Blad komunikacji z kolejka: {e}")
            
    cap.release()
    out.release() # --- NOWY KOD: ZAMKNIECIE PLIKU WIDEO ---
    
    # --- NOWY KOD: KONWERSJA DLA MACA / STREAMLITA ---
    print("Rozpoczynam konwersje wideo na format Apple/Web (H.264)...")
    koncowy_mp4 = f"/app/video-output/wynik_{output_mp4_name}.mp4"
    os.system(f"ffmpeg -y -i {roboczy_avi} -vcodec libx264 {koncowy_mp4}")
    os.remove(roboczy_avi)
    # -------------------------------------------------
    
    print(f"Przetwarzanie wideo {output_mp4_name} calkowicie zakonczone.")

def watch_folder_and_process():
    # Zmienione nazwy folderow
    input_folder = "/app/video-input"
    archive_folder = "/app/video-archive"
    
    os.makedirs(input_folder, exist_ok=True)
    os.makedirs(archive_folder, exist_ok=True)
    
    print(f"Rozpoczynam nasluchiwanie w folderze: {input_folder}")
    
    while True:
        video_files = glob.glob(os.path.join(input_folder, "*.mp4"))
        
        if not video_files:
            time.sleep(5)
            continue
            
        current_video = video_files[0]
        video_name = os.path.basename(current_video)
        
        # --- ZMIANA NA ODCISC PALCA ---
        video_core_name = get_file_hash(current_video)
        print(f"\n--- ZNALEZIONO NOWY FILM: {video_name} (Zaszyfrowane ID: {video_core_name}) ---")
        
        process_video_stream(current_video, video_core_name)
        
        archive_path = os.path.join(archive_folder, video_name)
        shutil.move(current_video, archive_path)
        print(f"Film {video_name} przeniesiony do archiwum. Czekam na kolejne zadania...")

if __name__ == "__main__":
    watch_folder_and_process()