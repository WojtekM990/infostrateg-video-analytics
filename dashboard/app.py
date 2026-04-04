# dashboard/app.py

import streamlit as st
import pymysql
import os
import pandas as pd
import glob

# Pobieramy konfiguracje bazy danych

db_host = os.getenv("DB_HOST", "mysql-service")
db_user = os.getenv("DB_USER", "root")
db_password = os.getenv("DB_PASSWORD", "infostrateg_root")
db_name = os.getenv("DB_NAME", "behavior_db")

# Uzywamy wymaganej zmiennej portu!

port_str = str(os.getenv("MYSQL_DB_PORT", "3306"))
db_port = int(port_str) if port_str.strip() else 3306

def get_data():
    
    # Funkcja laczaca sie z baza i pobierajaca dane do ramki Pandas
    
    try:
        
        conn = pymysql.connect(
            host=db_host,
            user=db_user,
            password=db_password,
            database=db_name,
            port=db_port
        )
        
        # Pobieramy 100 najnowszych wpisow
        
        query = "SELECT * FROM detections ORDER BY detected_at DESC LIMIT 100"
        df = pd.read_sql(query, conn)
        
        conn.close()
        return df
        
    except Exception as e:
        
        st.error(f"Blad polaczenia z baza: {e}")
        return pd.DataFrame()

# Interfejs wizualny Streamlit

st.set_page_config(page_title="INFOSTRATEG IX Dashboard", layout="wide")

st.title("INFOSTRATEG IX - Centrum Monitoringu")

st.write("Wizualizacja na zywo detekcji z kamer przemyslowych.")

# Przycisk do odswiezania danych

if st.button("Odswiez dane"):
    
    st.rerun()
    
df = get_data()

if not df.empty:
    
    col1, col2 = st.columns(2)
    
    with col1:
        
        st.subheader("Ostatnie Wykryte Zdarzenia")
        st.dataframe(df[['camera_id', 'person_id', 'behavior', 'speed', 'confidence', 'detected_at']])
        
    with col2:
        
        st.subheader("Statystyki Zachowan")
        
        # Prosty wykres slupkowy zdan
        
        behavior_counts = df['behavior'].value_counts()
        st.bar_chart(behavior_counts)
        
else:
    
    st.warning("Brak danych do wyswietlenia. Czekam na Workera...")

# --- NOWA SEKCJA: ODTWARZACZ WIDEO ---
st.markdown("---")
st.header("Ostatnio Przetworzone Wideo")

# Definiujemy sciezke do folderu, w ktorym Worker zapisuje wyniki
video_dir = "/app/video-output"

# Sprawdzamy, czy folder w ogole istnieje i czy Streamlit go widzi
if os.path.exists(video_dir):
    
    # Szukamy wszystkich plikow z rozszerzeniem mp4 w tym folderze
    mp4_files = glob.glob(os.path.join(video_dir, "*.mp4"))
    
    if mp4_files:
        # Bierzemy najnowszy plik (posortowany po dacie modyfikacji/stworzenia)
        latest_video = max(mp4_files, key=os.path.getctime)
        st.write(f"Odtwarzanie pliku: **{os.path.basename(latest_video)}**")
        
        # Wczytujemy plik w trybie binarnym ('rb' - read binary) i przekazujemy do Streamlita
        with open(latest_video, 'rb') as video_file:
            video_bytes = video_file.read()
            st.video(video_bytes)
            
    else:
        st.info("Oczekuje na dane... Brak przekonwertowanych plikow wideo w folderze.")
else:
    st.warning(f"Brak dostepu do folderu {video_dir}. Upewnij sie, ze wolumen w Kubernetesie jest poprawnie podpiety.")