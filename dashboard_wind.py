import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import requests # ¡Importante! Asegúrate de tenerlo

# --- Configuración de la Página ---
st.set_page_config(page_title="Historial de Viento", layout="wide")

# --- 1. Función Real para Llamar a la API ---

def get_wind_data_real(location, start_date, end_date, api_key):
    """
    Obtiene datos reales de la API de Visual Crossing.
    """
    # Convertir fechas a string en formato YYYY-MM-DD
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    # Construye la URL de la API (ajusta 'elements' si necesitas más datos)
    url = (f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/"
           f"{location}/{start_str}/{end_str}?unitGroup=metric&key={api_key}"
           f"&include=days&elements=datetime,windspeed,winddir")
    
    try:
        response = requests.get(url)
        response.raise_for_status() # Lanza un error si la respuesta no es 200
        
        data = response.json()
        
        # --- Procesamiento del JSON ---
        # La estructura de datos depende de la API. Basado en la URL,
        # esperamos una clave 'days'.
        
        days_data = data.get('days', [])
        
        if not days_data:
            st.warning("La API no devolvió datos para esta ubicación o rango.")
            return pd.DataFrame()

        # Convertimos la lista de días en un DataFrame
        df = pd.DataFrame(days_data)
        
        # Aseguramos que la columna 'datetime' sea de tipo fecha
        df['datetime'] = pd.to_datetime(df['datetime'])
        
        # Renombramos columnas para que coincidan con los gráficos (si es necesario)
        # Ajusta esto a los nombres reales que devuelve la API
        df = df.rename(columns={
            'windspeed': 'wind_speed_kmh',
            'winddir': 'wind_direction_deg'
        })
        
        # Seleccionamos solo las columnas que nos interesan
        columns_of_interest = ['datetime', 'wind_speed_kmh', 'wind_direction_deg']
        df = df[columns_of_interest]
        
        return df
        
    except requests.exceptions.HTTPError as err:
        st.error(f"Error de API: {err.response.text}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Ocurrió un error inesperado: {e}")
        return pd.DataFrame()

# --- 2. Interfaz de Usuario (UI) con Streamlit ---

st.title("🌬️ Visor de Historial de Viento")
st.markdown("Esta aplicación obtiene datos históricos de [Visual Crossing](https://www.visualcrossing.com/).")

# Usamos la barra lateral para los controles
with st.sidebar:
    st.header("Configuración")
    
    location = st.text_input("Ubicación", "Bogota, Colombia")
    
    # Campos para seleccionar fechas
    today = datetime.date.today()
    one_week_ago = today - datetime.timedelta(days=7)
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Fecha de Inicio", one_week_ago)
    with col2:
        end_date = st.date_input("Fecha de Fin", today)
        
    # Botón para ejecutar
    fetch_button = st.button("Obtener Datos")

# --- 3. Lógica Principal (Qué pasa al presionar el botón) ---

if fetch_button:
    # Validaciones
    if not location:
        st.warning("Por favor, introduce una ubicación.")
    elif start_date > end_date:
        st.error("Error: La fecha de inicio no puede ser posterior a la fecha de fin.")
    else:
        # --- Obtener la API Key desde Streamlit Secrets ---
        # (Ver el paso 3 de esta guía)
        try:
            api_key = st.secrets["VISUAL_CROSSING_KEY"]
        except (KeyError, FileNotFoundError):
            st.error("Error de configuración: No se encontró la API Key. (El desarrollador debe configurarla en st.secrets).")
            api_key = None # Detiene la ejecución

        if api_key:
            # Todo está bien, llamamos a la función REAL
            with st.spinner(f"Obteniendo datos para '{location}'..."):
                data_df = get_wind_data_real(location, start_date, end_date, api_key)
            
            # --- 4. Mostrar Resultados (si se obtuvieron datos) ---
            if not data_df.empty:
                st.success("¡Datos cargados con éxito!")
                
                st.subheader(f"Datos de Viento para {location}")
                st.dataframe(data_df)
                
                # --- 5. Visualización con Plotly ---
                st.subheader("Gráficos")
                
                # Gráfico de Línea: Velocidad del Viento
                fig_speed = px.line(data_df, 
                                    x='datetime', 
                                    y='wind_speed_kmh', 
                                    title="Velocidad del Viento",
                                    labels={"datetime": "Fecha", "wind_speed_kmh": "Velocidad (km/h)"})
                st.plotly_chart(fig_speed, use_container_width=True)
                
                # Gráfico de Dispersión: Dirección vs Velocidad
                fig_dir = px.scatter(data_df, 
                                     x='datetime', 
                                     y='wind_direction_deg', 
                                     color='wind_speed_kmh',
                                     title="Dirección y Velocidad del Viento",
                                     labels={"datetime": "Fecha", "wind_direction_deg": "Dirección (°)", "wind_speed_kmh": "Velocidad (km/h)"})
                st.plotly_chart(fig_dir, use_container_width=True)
            else:
                # El error ya se mostró dentro de la función get_wind_data_real
                st.info("No se encontraron datos para los parámetros seleccionados.")
else:
    st.info("Configura los parámetros en la barra lateral y presiona 'Obtener Datos'.")
