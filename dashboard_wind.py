import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import requests # Necesario para hacer la llamada a la API

# --- Configuración de la Página ---
# Establece el título y el modo de layout amplio
st.set_page_config(page_title="Historial Horario de Viento y Clima", layout="wide")

# --- 1. Función Real para Llamar a la API ---

def get_wind_data_real(location, start_date, end_date, api_key):
    """
    Obtiene datos REALES de la API de Visual Crossing, AHORA POR HORA.
    Incluye: velocidad, dirección, temperatura, presión, humedad, ráfagas y nubosidad.
    """
    # Convertir fechas a string en formato YYYY-MM-DD
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    # --- LISTA DE ELEMENTOS EXPANDIDA ---
    # Los elementos son los mismos, pero la API los devolverá por cada hora.
    elements_list = "datetime,windspeed,winddir,temp,pressure,humidity,windgust,cloudcover"
    
    # --- CAMBIO CRÍTICO: SE SOLICITAN DATOS POR HORA ---
    # '&include=days,hours' fuerza a la API a incluir los datos horarios anidados dentro de cada día.
    url = (f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/"
           f"{location}/{start_str}/{end_str}?unitGroup=metric&key={api_key}"
           f"&include=days,hours&elements={elements_list}")
    
    try:
        response = requests.get(url)
        response.raise_for_status() 
        data = response.json()
        
        # --- Procesamiento del JSON para APLANAR Datos Horarios ---
        all_hourly_data = []
        days_data = data.get('days', [])
        
        if not days_data:
            st.warning("La API no devolvió datos para esta ubicación o rango. Revisa la ubicación o el periodo.")
            return pd.DataFrame()

        # Iterar sobre cada día y luego sobre cada hora para aplanar la estructura
        for day in days_data:
            day_date = day['datetime'] # La fecha del día (YYYY-MM-DD)
            hours_data = day.get('hours', [])
            
            for hour in hours_data:
                # El campo 'datetime' en el objeto hora solo contiene la hora (HH:MM:SS),
                # lo combinamos con la fecha del día para formar un timestamp completo.
                full_datetime_str = f"{day_date} {hour['datetime']}"
                
                # Creamos un registro horario, extrayendo las métricas
                record = {
                    'datetime': full_datetime_str, # Timestamp completo
                    'windspeed': hour.get('windspeed'),
                    'winddir': hour.get('winddir'),
                    'temp': hour.get('temp'),
                    'pressure': hour.get('pressure'),
                    'humidity': hour.get('humidity'),
                    'windgust': hour.get('windgust'),
                    'cloudcover': hour.get('cloudcover')
                }
                all_hourly_data.append(record)

        # Creamos el DataFrame a partir de la lista de registros horarios
        df = pd.DataFrame(all_hourly_data)
        
        # Aseguramos que la columna 'datetime' sea de tipo datetime, lo que habilita 
        # las visualizaciones correctas de la serie de tiempo.
        df['datetime'] = pd.to_datetime(df['datetime'])
        
        # --- RENOMBRADO DE COLUMNAS ---
        df = df.rename(columns={
            'windspeed': 'wind_speed_kmh',
            'winddir': 'wind_direction_deg',
            'temp': 'temperature_celsius',      # Temperatura horaria
            'pressure': 'pressure_hPa',          # Presión horaria
            'humidity': 'humidity_percent',      # Humedad horaria
            'windgust': 'wind_gust_kmh',         # Ráfaga horaria
            'cloudcover': 'cloud_cover_percent'  # Nubosidad horaria
        })
        
        # Seleccionamos solo las columnas que nos interesan
        columns_of_interest = [
            'datetime', 
            'wind_speed_kmh', 
            'wind_direction_deg', 
            'temperature_celsius', 
            'pressure_hPa', 
            'humidity_percent', 
            'wind_gust_kmh',
            'cloud_cover_percent'
        ]
        
        df = df.reindex(columns=columns_of_interest).dropna(subset=['wind_speed_kmh', 'wind_direction_deg'])
        
        return df
        
    except requests.exceptions.HTTPError as err:
        st.error(f"Error de API: Verifica la clave o la ubicación. Mensaje: {err.response.text}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Ocurrió un error inesperado: {e}")
        return pd.DataFrame()

# --- 2. Interfaz de Usuario (UI) con Streamlit ---

st.title("⏱️ Visor de Historial Horario de Viento y Clima")
st.markdown("Esta aplicación obtiene datos históricos **por hora** de [Visual Crossing](https://www.visualcrossing.com/).")

# Usamos la barra lateral para los controles
with st.sidebar:
    st.header("Configuración")
    
    location = st.text_input("Ubicación (Ciudad, País o Coordenadas)", "Bogota, Colombia")
    
    # Campos para seleccionar fechas
    today = datetime.date.today()
    # Se recomienda un rango pequeño (ej. 7 días) para datos horarios
    one_week_ago = today - datetime.timedelta(days=7) 
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Fecha de Inicio", one_week_ago)
    with col2:
        end_date = st.date_input("Fecha de Fin", today)
        
    fetch_button = st.button("Obtener Datos Horarios")

# --- 3. Lógica Principal (Qué pasa al presionar el botón) ---

if fetch_button:
    # Validaciones de input
    if not location:
        st.warning("Por favor, introduce una ubicación.")
    elif start_date > end_date:
        st.error("Error: La fecha de inicio no puede ser posterior a la fecha de fin.")
    else:
        # --- Obtener la API Key desde Streamlit Secrets ---
        try:
            api_key = st.secrets["VISUAL_CROSSING_KEY"]
        except (KeyError, FileNotFoundError):
            st.error("Error de configuración: No se encontró la API Key 'VISUAL_CROSSING_KEY' en `st.secrets`.")
            api_key = None 

        if api_key:
            # Llamada a la función REAL
            with st.spinner(f"Obteniendo {int((end_date - start_date).days + 1) * 24} datos horarios para '{location}'..."):
                data_df = get_wind_data_real(location, start_date, end_date, api_key)
            
            # --- 4. Mostrar Resultados (si se obtuvieron datos) ---
            if not data_df.empty:
                st.success(f"¡{len(data_df)} registros horarios cargados con éxito!")
                
                st.subheader(f"Datos Horarios para {location}")
                st.dataframe(data_df, use_container_width=True)
                
                # --- 5. Visualización con Plotly ---
                st.subheader("Gráficos de Tendencia Horaria")
                
                # Organización de gráficos en columnas para mejor visualización
                col_wind_speed, col_temp = st.columns(2)
                
                # Gráfico 1: Velocidad y Ráfagas de Viento
                with col_wind_speed:
                    st.markdown("#### Velocidad y Ráfagas (Horario)")
                    # Combina velocidad y ráfaga en un solo gráfico
                    fig_wind = px.line(data_df, 
                                        x='datetime', 
                                        y=['wind_speed_kmh', 'wind_gust_kmh'],
                                        title="Velocidad y Ráfaga (km/h)",
                                        labels={"datetime": "Fecha y Hora", "value": "Velocidad (km/h)", "variable": "Tipo de Viento"},
                                        template="plotly_white")
                    fig_wind.update_layout(legend_title_text='Métrica')
                    st.plotly_chart(fig_wind, use_container_width=True)
                
                # Gráfico 2: Temperatura
                with col_temp:
                    st.markdown("#### Temperatura (°C) (Horario)")
                    fig_temp = px.line(data_df, 
                                        x='datetime', 
                                        y='temperature_celsius', 
                                        title="Temperatura Horaria (°C)",
                                        labels={"datetime": "Fecha y Hora", "temperature_celsius": "Temperatura (°C)"},
                                        template="plotly_white")
                    st.plotly_chart(fig_temp, use_container_width=True)

                # Organización de gráficos en una segunda fila
                col_dir_cloud, col_press_humid = st.columns(2)

                # Gráfico 3: Dirección del Viento y Nubosidad
                with col_dir_cloud:
                    st.markdown("#### Dirección y Nubosidad (Horario)")
                    # Ahora el eje X es la hora, mostrando la variación intra-día
                    fig_dir = px.scatter(data_df, 
                                         x='datetime', 
                                         y='wind_direction_deg', 
                                         color='cloud_cover_percent', # El color indica la nubosidad
                                         color_continuous_scale=px.colors.sequential.Plasma,
                                         title="Dirección del Viento vs Nubosidad (%)",
                                         labels={"datetime": "Fecha y Hora", "wind_direction_deg": "Dirección (°)", "cloud_cover_percent": "Nubosidad (%)"})
                    fig_dir.update_yaxes(range=[0, 360])
                    st.plotly_chart(fig_dir, use_container_width=True)
                
                # Gráfico 4: Presión y Humedad
                with col_press_humid:
                    st.markdown("#### Presión y Humedad (Horario)")
                    fig_env = px.line(data_df,
                                     x='datetime',
                                     y=['pressure_hPa', 'humidity_percent'],
                                     title="Presión (hPa) y Humedad (%)",
                                     labels={"datetime": "Fecha y Hora", "value": "Valor", "variable": "Métrica"},
                                     template="plotly_white")
                    fig_env.update_layout(legend_title_text='Métrica')
                    st.plotly_chart(fig_env, use_container_width=True)

            else:
                st.info("No se encontraron datos para los parámetros seleccionados.")
else:
    st.info("Configura la ubicación y el rango de fechas en la barra lateral y presiona 'Obtener Datos Horarios'.")
