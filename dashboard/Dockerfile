# dashboard/Dockerfile

FROM python:3.9-slim

WORKDIR /app

# Instalujemy zaleznosci dla Dashboardu
RUN pip install --no-cache-dir \
    streamlit \
    requests \
    pandas \
    google-cloud-storage

# Kopiujemy kod Dashboardu
COPY . .

# Informujemy, ze aplikacja bedzie dzialac na porcie 8501
EXPOSE 8501

# Startujemy Streamlit z odpowiednimi flagami dla pracy w kontenerze
# Ustawiamy adres 0.0.0.0, aby byl dostepny z zewnatrz kontenera
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]