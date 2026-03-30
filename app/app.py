# app/app.py

from fastapi import FastAPI
import pymysql
import os
import time
import threading
from confluent_kafka import Consumer, KafkaError
import json

app = FastAPI()

DB_HOST = os.getenv("DB_HOST", "mysql-service")
DB_USER = os.getenv("DB_USER", "user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "behavior_db")

# Bezpieczne pobieranie portu (zabezpieczenie przed pustym stringiem z Kubernetesa)
port_str = os.getenv("MYSQL_DB_PORT", "3306")
DB_PORT = int(port_str) if port_str.strip() else 3306

def get_db_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT,
        cursorclass=pymysql.cursors.DictCursor
    )

def init_db():
    retries = 5
    while retries > 0:
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS detections (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        camera_id VARCHAR(255),
                        video_id VARCHAR(255),
                        person_id INT NULL,
                        behavior VARCHAR(255),
                        speed FLOAT NULL,
                        frame_number INT NULL,
                        frame_id INT NULL,
                        confidence FLOAT,
                        detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            conn.commit()
            conn.close()
            print("Baza danych zainicjalizowana pomyslnie.")
            break
        except Exception as e:
            print(f"Czekam na baze danych... ({e})")
            retries -= 1
            time.sleep(5)

def consume_kafka():
    print("API: Oczekuje na uruchomienie Kafki...")
    time.sleep(10) # Dajemy chwile na start
    
    conf = {
        'bootstrap.servers': 'kafka-service:9092',
        'group.id': 'video-api-group',
        'auto.offset.reset': 'earliest'
    }
    consumer = Consumer(conf)
    consumer.subscribe(['detections_topic'])
    
    print("API: Konsument podlaczony! Rozpoczynam bezwzgledne zasysanie wiadomosci z Kafki...")
    
    while True:
        try:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                print(f"[Kafka Konsument] Blad odczytu: {msg.error()}")
                continue
                
            payload = json.loads(msg.value().decode('utf-8'))
            
            conn = get_db_connection()
            with conn.cursor() as cursor:
                
                # --- NOWOŚĆ: LOGIKA CZYSZCZENIA BAZY PRZED STARTEM NOWEGO FILMU ---
                if payload.get('behavior') == 'init_video_cleanup':
                    video_id = payload.get('video_id')
                    sql = "DELETE FROM detections WHERE video_id = %s"
                    cursor.execute(sql, (video_id,))
                    print(f"[Kafka Konsument] Otrzymano sygnal startu. Wyczyszczono stare dane dla wideo o ID: {video_id}")
                else:
                    # POPRAWKA: Dodano brakujący %s, teraz jest ich 8
                    sql = "INSERT INTO detections (camera_id, video_id, person_id, behavior, speed, frame_number, frame_id, confidence) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
                    cursor.execute(sql, (
                        payload.get('camera_id'), 
                        payload.get('video_id'),
                        payload.get('person_id'), 
                        payload.get('behavior'), 
                        payload.get('speed'), 
                        payload.get('frame_number'),
                        payload.get('frame_id'),
                        payload.get('confidence')
                    ))
            
            conn.commit()
            conn.close()
            
            # Print logów tylko dla detekcji (nie dla czyszczenia)
            if payload.get('behavior') != 'init_video_cleanup':
                print(f"[Kafka Konsument] Zapisano log: ID: {payload.get('person_id')} | Klatka: {payload.get('frame_number')} | V: {payload.get('speed')}")
            
        except Exception as e:
            print(f"[Kafka Konsument] Blad bazy MySQL: {e}")

@app.on_event("startup")
def startup_event():
    init_db()
    # Uruchamiamy zasysanie w osobnym watku (w tle), by nie zamrozic endpointow HTTP
    thread = threading.Thread(target=consume_kafka, daemon=True)
    thread.start()

# Endpoint zostawiamy na wypadek testow bezposrednich z przegladarki
@app.post("/simulate_detection")
def simulate_detection(camera_id: str, video_id: str, behavior: str, person_id: int = None, speed: float = None, frame_number: int = None, frame_id: int = None, confidence: float = 0.0):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # POPRAWKA: Dodano brakujący %s, teraz jest ich 8
            sql = "INSERT INTO detections (camera_id, video_id, person_id, behavior, speed, frame_number, frame_id, confidence) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
            cursor.execute(sql, (camera_id, video_id, person_id, behavior, speed, frame_number, frame_id, confidence))
        conn.commit()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}