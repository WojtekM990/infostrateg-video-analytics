FROM python:3.9-slim

WORKDIR /app

# Instalacja Javy (Open JRE) niezbędnej do działania Apache Spark
RUN apt-get update && apt-get install -y default-jre && rm -rf /var/lib/apt/lists/*

# Kopiowanie i instalacja bibliotek (korzystamy z Cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiowanie kodu aplikacji
COPY app.py .

# Uruchomienie skryptu
CMD ["python", "app.py"]