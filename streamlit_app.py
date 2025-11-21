import streamlit as st
import pandas as pd
import requests

# URL base para la API de NASA POWER (Datos Horarios por punto)
NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/hourly/point"

st.title("Descarga de Datos Climáticos Históricos (NASA POWER)")

# --- 1. Entrada de Variables del Usuario ---
st.header("Configuración de la Descarga")

with st.form("nasa_power_form"):
    # Asume que ya tienes las coordenadas
    latitud = st.number_input("Latitud (ej: 19.43)", value=19.43, format="%.2f", step=0.01)
    longitud = st.number_input("Longitud (ej: -99.13)", value=-99.13, format="%.2f", step=0.01)
    
    # Rango de fechas (limitado a 1 año en la API)
    fecha_inicio = st.date_input("Fecha de Inicio", value=pd.to_datetime("2024-01-01"))
    fecha_fin = st.date_input("Fecha de Fin", value=pd.to_datetime("2024-01-31"))

    # Variables a solicitar
    variables_disp = {
        "Velocidad del Viento a 10m (WS10M)": "WS10M",
        "Dirección del Viento a 10m (WD10M)": "WD10M",
        "Temperatura a 2m (T2M)": "T2M",
        "Humedad Relativa a 2m (RH2M)": "RH2M",
        "Precipitación Total (PRECTOTCORR)": "PRECTOTCORR"
    }
    
    variables_sel = st.multiselect(
        "Selecciona las Variables Climáticas:",
        options=list(variables_disp.keys()),
        default=list(variables_disp.keys())[:2]
    )
    
    # Mapeo de variables seleccionadas al formato de NASA
    variables_nasa = [variables_disp[v] for v in variables_sel]

    submit_button = st.form_submit_button(label="Obtener y Mostrar Datos")

# --- 2. Función para obtener datos de NASA ---

def obtener_datos_nasa(lat, lon, start_date, end_date, variables):
    """Realiza la solicitud a la API de NASA POWER."""
    
    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")
    
    params = {
        "parameters": ",".join(variables),
        "community": "RE", # Renewable Energy - buen conjunto de datos
        "latitude": lat,
        "longitude": lon,
        "start": start_str,
        "end": end_str,
        "format": "JSON"
    }
    
    # Construcción de la URL de solicitud
    url_final = f"{NASA_POWER_URL}?{pd.io.json.build_url_query(params)}"
    
    try:
        response = requests.get(url_final)
        response.raise_for_status() # Lanza un error para códigos de estado HTTP erróneos
        data = response.json()
        
        # Extracción y procesamiento de datos
        # La estructura de datos de NASA POWER es compleja, necesitamos llegar hasta 'hourly'
        hourly_data = data['properties']['parameter']
        
        # Crear un DataFrame de pandas
        df = pd.DataFrame(hourly_data)
        
        # Convertir el índice (tiempo) a formato datetime
        df.index = pd.to_datetime(df.index, format='%Y%m%d%H')
        df.index.name = "Fecha_Hora_GMT"
        
        return df

    except requests.exceptions.RequestException as e:
        st.error(f"Error en la solicitud a la API de NASA POWER: {e}")
        st.info("Asegúrate de que la Latitud y Longitud son correctas y el rango de fechas es válido.")
        return None
    except KeyError:
        st.error("Error al procesar los datos: La API no devolvió el formato esperado. Revise las variables solicitadas.")
        return None
        
# --- 3. Ejecución y Visualización ---

if submit_button:
    if not variables_nasa:
        st.warning("Por favor, selecciona al menos una variable climática.")
    else:
        st.subheader("Datos Descargados de NASA POWER")
        
        with st.spinner('Descargando datos, por favor espera...'):
            df_datos = obtener_datos_nasa(
                latitud, 
                longitud, 
                fecha_inicio, 
                fecha_fin, 
                variables_nasa
            )
        
        if df_datos is not None:
            st.success(f"¡Datos obtenidos! {len(df_datos)} registros horarios desde {fecha_inicio} hasta {fecha_fin}.")
            
            # Muestra la tabla en Streamlit
            st.dataframe(df_datos)
            
            # Convertir DataFrame a CSV para el botón de descarga
            @st.cache_data
            def convert_df_to_csv(df):
                # Importante: Codificación UTF-8 para compatibilidad de caracteres
                return df.to_csv(index=True, encoding='utf-8')

            csv_file = convert_df_to_csv(df_datos)
            
            # Botón de Descarga
            st.download_button(
                label="📥 Descargar Datos en CSV",
                data=csv_file,
                file_name=f"datos_climaticos_nasa_{fecha_inicio.strftime('%Y%m%d')}_a_{fecha_fin.strftime('%Y%m%d')}.csv",
                mime="text/csv",
                key='download_button'
            )
        else:
            st.error("No se pudieron obtener los datos. Intenta con un rango de fechas o ubicación diferente.")
