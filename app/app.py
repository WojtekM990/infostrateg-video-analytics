# api/main.py

from fastapi import FastAPI
import pymysql
import os
import time
import threading
import pika
import json

app = FastAPI()

DB_HOST = os.getenv("DB_HOST", "mysql-service")
DB_USER = os.getenv("DB_USER", "user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "behavior_db")
DB_PORT = int(os.getenv("MYSQL_DB_PORT", 3306))

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

def consume_rabbitmq():
    print("API: Oczekuje na uruchomienie RabbitMQ...")
    time.sleep(10) # Dajemy chwile na start RabbitMQ
    
    while True:
        try:
            credentials = pika.PlainCredentials('admin', 'admin123')
            parameters = pika.ConnectionParameters('rabbitmq-service', 5672, '/', credentials)
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            
            # Deklarujemy kolejke (durable=True, zeby zabezpieczyc dane przed utrata)
            channel.queue_declare(queue='detections_queue', durable=True)
            
            def callback(ch, method, properties, body):
                payload = json.loads(body)
                try:
                    conn = get_db_connection()
                    with conn.cursor() as cursor:
                        sql = "INSERT INTO detections (camera_id, person_id, behavior, speed, frame_number, frame_id, confidence) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                        cursor.execute(sql, (
                            payload.get('camera_id'), 
                            payload.get('person_id'), 
                            payload.get('behavior'), 
                            payload.get('speed'), 
                            payload.get('frame_number'),
                            payload.get('frame_id'),
                            payload.get('confidence')
                        ))
                    conn.commit()
                    conn.close()
                    
                    # Raczka w gore - potwierdzamy RabbitMQ, ze baza zjadla log i mozna go usunac z kolejki
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    print(f"[RabbitMQ Konsument] Zapisano log: ID: {payload.get('person_id')} | Klatka: {payload.get('frame_number')} | V: {payload.get('speed')}")
                except Exception as e:
                    print(f"[RabbitMQ Konsument] Blad bazy MySQL. Odrzucam wiadomosc do poprawki: {e}")
                    # W przypadku zadlawienia bazy, wrzucamy wiadomosc z powrotem do kolejki!
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            
            # Pobieraj z kolejki maksymalnie 1 wiadomosc na raz, aby nie zapchac pamieci API
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue='detections_queue', on_message_callback=callback)
            
            print("API: Konsument podlaczony! Rozpoczynam bezwzgledne zasysanie wiadomosci z RabbitMQ...")
            channel.start_consuming()
        except Exception as e:
            print(f"Blad polaczenia z RabbitMQ: {e}. Ponawiam za 5s...")
            time.sleep(5)

@app.on_event("startup")
def startup_event():
    init_db()
    # Uruchamiamy zasysanie w osobnym watku (w tle), by nie zamrozic endpointow HTTP
    thread = threading.Thread(target=consume_rabbitmq, daemon=True)
    thread.start()

# Endpoint zostawiamy na wypadek testow bezposrednich z przegladarki
@app.post("/simulate_detection")
def simulate_detection(camera_id: str, behavior: str, person_id: int = None, speed: float = None, frame_number: int = None, frame_id: int = None, confidence: float = 0.0):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = "INSERT INTO detections (camera_id, person_id, behavior, speed, frame_number, frame_id, confidence) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            cursor.execute(sql, (camera_id, person_id, behavior, speed, frame_number, frame_id, confidence))
        conn.commit()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}