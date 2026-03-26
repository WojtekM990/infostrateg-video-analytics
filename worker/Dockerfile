# worker/Dockerfile

FROM python:3.9-slim

RUN apt-get update && apt-get install -y ffmpeg libsm6 libxext6

WORKDIR /app

# BARDZO WAZNE: Instalujemy narzedzia systemowe Linuxa wymagane przez OpenCV i YOLO
# Dodajemy build-essential i ffmpeg dla stabilnego dekodowania wideo
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    build-essential \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Instalujemy aktualizacje narzedzi budowania
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# BLOKADA NUMPY: Wymuszamy wersje < 2 przed instalacja reszty
RUN pip install --no-cache-dir "numpy<2"

# Instalujemy biblioteki AI i bazy danych
# Dodajemy pymysql i cryptography, by móc wysyłać dane przez MYSQL_DB_PORT
RUN pip install --no-cache-dir \
    requests \
    opencv-python==4.8.0.76 \
    ultralytics \
    lapx \
    pymysql \
    cryptography \
    pika==1.3.2

# KROK KLUCZOWY: Pobieramy model YOLOv8n do obrazu TERAZ.
# Dzieki temu kontener nie bedzie go sciagal z internetu podczas startu w Kubernetes.
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

# Kopiujemy nasz kod i plik wideo
COPY worker.py .
COPY sample.mp4 .

ENV PYTHONUNBUFFERED=1

# Start aplikacji
CMD ["python", "worker.py"]