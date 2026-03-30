FROM python:3.9-slim

WORKDIR /app

# Instalacja zaleznosci
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    pymysql \
    cryptography \
    confluent-kafka

# Kopiujemy zawartosc folderu app do Workdir
COPY app/ .

# BARDZO WAZNE: Uruchamiamy app:app (plik app.py, obiekt app)
# Ustawiamy port 8080, skoro tak pokazuja Twoje logi
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]