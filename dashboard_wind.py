# dashboard_wind.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import time
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
import plotly.express as px
import os

# ----------------------------
# CONFIGURACIÓN
# ----------------------------
LAT, LON = 22.400, -97.920
API_KEY = "PNRL9UYWRR623NMV7AJHQE5CS"  # reemplaza con tu API key
CSV_FILE = "wind_history.csv"
WINDOW_SIZE = 24       # Últimas 24 horas para LSTM
REFRESH_INTERVAL = 3600  # segundos

# ----------------------------
# FUNCIONES AUXILIARES
# ----------------------------
def deg_to_cardinal(deg):
    dirs = ['N','NE','E','SE','S','SW','W','NW']
    return dirs[int((deg+22.5)/45)%8]

def download_vc_history(lat, lon, start, end, api_key):
    all_records = []
    current_start = start
    while current_start <= end:
        current_end = min(current_start + timedelta(days=30), end)
        url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{lat},{lon}/{current_start.date()}/{current_end.date()}"
        params = {
            "unitGroup": "metric",
            "include": "hours",
            "key": api_key,
            "contentType": "json"
        }
        try:
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()
            for day in data.get("days", []):
                day_date = day.get("datetime")
                for hour in day.get("hours", []):
                    hour_time = hour.get("datetime")
                    try:
                        ts = datetime.fromisoformat(f"{day_date}T{hour_time}")
                    except Exception:
                        continue
                    speed = hour.get("windspeed")
                    deg = hour.get("winddir")
                    if speed is not None and deg is not None:
                        all_records.append([ts, speed, deg])
        except Exception as e:
            st.warning(f"Error descargando datos: {e}")
        current_start = current_end + timedelta(days=1)
        time.sleep(1)
    return pd.DataFrame(all_records, columns=["time","speed","deg"])

# ----------------------------
# INTERFAZ STREAMLIT
# ----------------------------
st.title("🌬️ Dashboard de Viento en Tiempo Real")

# ----------------------------
# CARGAR HISTÓRICO
# ----------------------------
if st.button("Actualizar datos desde Visual Crossing"):
    st.info("Descargando datos nuevos...")
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE, parse_dates=["time"])
        last_date = df["time"].max()
        start_date = last_date + timedelta(hours=1)
    else:
        df = pd.DataFrame(columns=["time","speed","deg"])
        start_date = datetime(2025,1,1)

    end_date = datetime.now()
    if start_date <= end_date:
        new_data = download_vc_history(LAT, LON, start_date, end_date, API_KEY)
        if not new_data.empty:
            df = pd.concat([df, new_data], ignore_index=True)
            df["cardinal"] = df["deg"].apply(deg_to_cardinal)
            df.to_csv(CSV_FILE, index=False)
            st.success(f"✅ Histórico actualizado. Registros totales: {len(df)}")
        else:
            st.warning("⚠️ No se obtuvieron nuevos datos.")
else:
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE, parse_dates=["time"])
        df["cardinal"] = df["deg"].apply(deg_to_cardinal)
    else:
        st.warning("No hay datos históricos disponibles.")
        st.stop()

# ----------------------------
# MOSTRAR TABLA Y GRÁFICOS
# ----------------------------
st.subheader("Últimos registros")
st.dataframe(df.tail(10))

st.subheader("Velocidad del viento (m/s)")
fig_speed = px.line(df, x="time", y="speed", title="Velocidad del viento")
st.plotly_chart(fig_speed)

st.subheader("Dirección del viento (grados)")
fig_deg = px.line(df, x="time", y="deg", title="Dirección en grados")
st.plotly_chart(fig_deg)

st.subheader("Dirección cardinal")
fig_card = px.histogram(df, x="cardinal", title="Distribución de dirección cardinal")
st.plotly_chart(fig_card)

# ----------------------------
# PREDICCIÓN LSTM
# ----------------------------
if len(df) >= WINDOW_SIZE:
    data_values = df[["speed","deg"]].values
    scaler = MinMaxScaler()
    data_scaled = scaler.fit_transform(data_values)

    X = np.array([data_scaled[i-WINDOW_SIZE:i] for i in range(WINDOW_SIZE, len(data_scaled))])
    y = np.array([data_scaled[i] for i in range(WINDOW_SIZE, len(data_scaled))])

    model = Sequential([
        LSTM(64, input_shape=(WINDOW_SIZE,2), activation='tanh'),
        Dense(32, activation='relu'),
        Dense(2)
    ])
    model.compile(optimizer='adam', loss='mse')
    model.fit(X, y, epochs=10, batch_size=32, verbose=0)

    last_window = data_scaled[-WINDOW_SIZE:].reshape(1,WINDOW_SIZE,2)
    pred_scaled = model.predict(last_window)[0]
    pred_speed, pred_deg = scaler.inverse_transform([pred_scaled])[0]
    pred_dir = deg_to_cardinal(pred_deg)

    st.subheader("Predicción LSTM")
    st.metric("Velocidad pronosticada", f"{pred_speed:.2f} m/s")
    st.metric("Dirección pronosticada", f"{pred_deg:.0f}° ({pred_dir})")
else:
    st.info("No hay suficientes datos para la predicción LSTM.")

# ----------------------------
# REFRESCO AUTOMÁTICO
# ----------------------------
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=REFRESH_INTERVAL*1000, key="auto_refresh")
