# worker/Dockerfile

FROM python:3.9-slim

WORKDIR /app

# 1. Łączymy instalacje systemowe w jedną warstwę i czyścimy cache instalatora
# Dzieki temu obraz jest mniejszy o kilkaset MB
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    build-essential \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# 2. Instalujemy narzedzia budowania (rzadko sie zmieniaja)
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# 3. BLOKADA NUMPY i instalacja bibliotek AI (To jest te 7GB)
# Robimy to PRZED kopiowaniem kodu, zeby Docker mogl to zapamietac (cache)
RUN pip install --no-cache-dir "numpy<2"
RUN pip install --no-cache-dir \
    requests \
    opencv-python==4.8.0.76 \
    ultralytics \
    lapx \
    confluent-kafka
# USUNIETO: pymysql i cryptography (Worker juz nie laczy sie z baza, robi to API)

# 4. KROK KLUCZOWY: Pobieramy model YOLOv8n (Rowniez zapamietane w cache)
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

# 5. KOPIOWANIE KODU (Na samym koncu!)
# Teraz, gdy zmienisz tylko worker.py, Docker wykona tylko ten krok w 1 sekunde
COPY worker.py .

ENV PYTHONUNBUFFERED=1

# Start aplikacji
CMD ["python", "worker.py"]