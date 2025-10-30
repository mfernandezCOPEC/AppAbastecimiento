# --- ARCHIVO: src/data_loader.py ---
# (Modificado para usar rutas de 'data/' y 'st.session_state')

import pandas as pd
import streamlit as st
import config # Importamos nuestro archivo de configuración local

# --- 1. Función de Carga Real (Cacheada) ---
@st.cache_data
def _load_all_data():
    """
    Carga, limpia y pre-procesa todos los archivos de datos iniciales.
    Usa la carpeta 'data/'.
    
    Retorna:
    - tupla(pd.DataFrame): (df_stock, df_oc, df_consumo, df_residencial)
    
    Lanza:
    - FileNotFoundError: Si no se encuentra un archivo Excel esencial.
    """
    print("--- (EJECUTANDO CACHE) Cargando y Limpiando Datos Globales ---")
    
    try:
        # RUTAS ACTUALIZADAS A LA CARPETA 'data/'
        df_stock = pd.read_excel('data/Stock.xlsx')
        df_residencial = pd.read_excel("data/BD_Master_Residencial.xlsx")
        df_oc = pd.read_excel("data/OPOR.xlsx")
        df_consumo = pd.read_excel('data/ST_OWTR.xlsx')
        print("Archivos 'Stock', 'OPOR' y 'ST_OWTR' cargados desde 'data/'.")
    
    except FileNotFoundError as e:
        print(f"Error: No se pudo encontrar el archivo: {e.filename} en la carpeta 'data/'.")
        raise e # Esto detendrá la carga
    except Exception as e:
        st.error(f"Error inesperado al leer archivos: {e}")
        return None, None, None, None

    # --- Limpieza Global de Fechas ---
    df_oc['Fecha de contabilización'] = pd.to_datetime(df_oc['Fecha de contabilización'], format='%Y-m-%d', errors='coerce')
    df_consumo['FechaSolicitud'] = pd.to_datetime(df_consumo['FechaSolicitud'], errors='coerce')
    
    df_oc = df_oc.dropna(subset=['Fecha de contabilización'])
    df_consumo = df_consumo.dropna(subset=['FechaSolicitud'])

    # --- Filtro Global de 4 Meses ---
    hoy = pd.Timestamp.now()
    hace_4_meses = (hoy - pd.DateOffset(months=4)).replace(day=1) 
    
    df_oc = df_oc[df_oc['Fecha de contabilización'] >= hace_4_meses].copy()
    df_oc = df_oc[~df_oc['Comentarios'].str.contains('PROA', na=False)].copy()    
    df_consumo = df_consumo[df_consumo['FechaSolicitud'] >= hace_4_meses].copy()

    # --- Limpieza Global de SKUs (Usando config) ---
    df_consumo['CodigoArticulo'] = df_consumo['CodigoArticulo'].replace(config.MAPEO_SKUS)
    # df_oc['Número de artículo'] = df_oc['Número de artículo'].replace(config.MAPEO_SKUS)
    # df_stock['CodigoArticulo'] = df_stock['CodigoArticulo'].replace(config.MAPEO_SKUS)
    
    print("Datos globales cargados y limpiados.")
    
    return df_stock, df_oc, df_consumo, df_residencial

# --- 2. Función de Acceso a Session State ---
def load_data_into_session():
    """
    Wrapper que llama a la función cacheada y guarda los datos
    en st.session_state para que todas las páginas los usen.
    """
    if 'data_loaded' not in st.session_state:
        try:
            # Llama a la función cacheada
            (st.session_state.df_stock, 
             st.session_state.df_oc, 
             st.session_state.df_consumo, 
             st.session_state.df_residencial) = _load_all_data()
            
            st.session_state.data_loaded = True
            print("Datos cargados en st.session_state.")

        except FileNotFoundError as e:
            st.error(f"Error Crítico: No se pudo encontrar el archivo: {e.filename}.")
            st.info(f"Por favor, asegúrese de que el archivo '{e.filename}' esté en la carpeta 'data/'.")
            st.stop()
        except Exception as e:
            st.error(f"Ocurrió un error inesperado durante la carga de datos: {e}")
            st.stop()