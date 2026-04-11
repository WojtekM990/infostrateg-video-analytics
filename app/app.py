# app/app.py

from fastapi import FastAPI
import pymysql
import os
import time

app = FastAPI()

DB_HOST = os.getenv("DB_HOST", "mysql-service")
DB_USER = os.getenv("DB_USER", "user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "behavior_db")

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
                        video_name VARCHAR(255) NULL,
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

@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/detections")
def get_detections(limit: int = 100):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM detections ORDER BY detected_at DESC LIMIT %s",
                (limit,)
            )
            rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/simulate_detection")
def simulate_detection(camera_id: str, video_id: str, behavior: str, video_name: str = None, person_id: int = None, speed: float = None, frame_number: int = None, frame_id: int = None, confidence: float = 0.0):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = "INSERT INTO detections (camera_id, video_id, video_name, person_id, behavior, speed, frame_number, frame_id, confidence) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
            cursor.execute(sql, (camera_id, video_id, video_name, person_id, behavior, speed, frame_number, frame_id, confidence))
        conn.commit()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
