# dashboard/app.py

import streamlit as st
import requests
import os
import pandas as pd
from google.cloud import storage as gcs

API_URL = os.getenv("API_URL", "http://video-api-service")
GCS_BUCKET = os.getenv("GCS_BUCKET", "infostrateg-video-output-video-rec-runners")

def get_data():
    try:
        response = requests.get(f"{API_URL}/detections", timeout=5)
        response.raise_for_status()
        return pd.DataFrame(response.json())
    except Exception as e:
        st.error(f"Blad polaczenia z API: {e}")
        return pd.DataFrame()

st.set_page_config(page_title="INFOSTRATEG IX Dashboard", layout="wide")

st.title("INFOSTRATEG IX - Centrum Monitoringu")

st.write("Wizualizacja na zywo detekcji z kamer przemyslowych.")

if st.button("Odswiez dane"):
    st.rerun()

df = get_data()

if not df.empty:

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Ostatnie Wykryte Zdarzenia")
        st.dataframe(df[['camera_id', 'video_name', 'person_id', 'behavior', 'speed', 'confidence', 'detected_at']])

    with col2:
        st.subheader("Statystyki Zachowan")
        behavior_counts = df['behavior'].value_counts()
        st.bar_chart(behavior_counts)

else:
    st.warning("Brak danych do wyswietlenia. Czekam na Workera...")

st.markdown("---")
st.header("Ostatnio Przetworzone Wideo")

try:
    client = gcs.Client()
    bucket = client.bucket(GCS_BUCKET)
    blobs = sorted(bucket.list_blobs(), key=lambda b: b.updated, reverse=True)

    if blobs:
        latest = blobs[0]
        st.write(f"Odtwarzanie pliku: **{latest.name}**")
        video_bytes = latest.download_as_bytes()
        st.video(video_bytes)
    else:
        st.info("Oczekuje na dane... Brak plikow wideo w GCS.")
except Exception as e:
    st.warning(f"Blad polaczenia z GCS: {e}")
