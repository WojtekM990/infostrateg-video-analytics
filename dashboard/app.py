# dashboard/app.py

import streamlit as st
import requests
import os
import pandas as pd
import glob

API_URL = os.getenv("API_URL", "http://video-api-service")

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

video_dir = "/app/video-output"

if os.path.exists(video_dir):
    mp4_files = glob.glob(os.path.join(video_dir, "*.mp4"))

    if mp4_files:
        latest_video = max(mp4_files, key=os.path.getctime)
        st.write(f"Odtwarzanie pliku: **{os.path.basename(latest_video)}**")

        with open(latest_video, 'rb') as video_file:
            video_bytes = video_file.read()
            st.video(video_bytes)
    else:
        st.info("Oczekuje na dane... Brak przekonwertowanych plikow wideo w folderze.")
else:
    st.warning(f"Brak dostepu do folderu {video_dir}. Upewnij sie, ze wolumen w Kubernetesie jest poprawnie podpiety.")
