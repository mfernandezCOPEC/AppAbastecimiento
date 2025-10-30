# --- ARCHIVO: pages/2_📦_Llegadas.py ---

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# --- Configuración del Path ---
# (Necesario en CADA archivo de 'pages' para encontrar 'src')
src_path = str(Path(__file__).resolve().parent.parent / "src")
if src_path not in sys.path:
    sys.path.append(src_path)

import ui_helpers     # Importa las funciones de gráficos y métricas
import data_loader    # Importamos esto solo por si acaso, pero los datos ya están cargados

# --- 1. Título de la Página ---
st.title("Consulta de Próximas Llegadas 📦")

# Verifica si los datos están cargados (deben haber sido cargados por app.py)
if 'data_loaded' not in st.session_state or not st.session_state.data_loaded:
    st.error("Los datos no se han cargado. Por favor, vuelva al Menú Principal e inténtelo de nuevo.")
    st.stop()

# --- 2. Acceder a los Datos desde st.session_state ---
df_stock = st.session_state.df_stock
df_oc = st.session_state.df_oc
df_consumo = st.session_state.df_consumo

# --- 3. Crear Selectores de Filtro ---

# Listas para el selector de SKU
lista_skus_stock = df_stock['CodigoArticulo'].dropna().unique()
lista_skus_consumo = df_consumo['CodigoArticulo'].dropna().unique()
all_skus = sorted(list(set(lista_skus_stock) | set(lista_skus_consumo)))

opciones_selector_sku, mapa_nombres, _ = ui_helpers.create_sku_options(all_skus, df_stock)

# Añadimos la opción "Todas" al selector de SKU
opciones_con_todas = ["Todas"] + opciones_selector_sku

# Creamos columnas para los filtros
col1, col2 = st.columns(2)

with col1:
    sku_seleccionado_formateado = st.selectbox(
        "Filtrar por SKU:",
        opciones_con_todas, 
        index=0, # Por defecto muestra "Todas"
        help="Seleccione el producto para ver sus Órdenes de Compra futuras."
    )
    sku_seleccionado = sku_seleccionado_formateado.split(" | ")[0]

with col2:
    oc_buscada = st.text_input(
        "Filtrar por N° de Orden de Compra (OC):",
        help="Escriba un número de OC para filtrar los resultados (búsqueda parcial)."
    )

st.subheader(f"Resultados de la Búsqueda")
st.markdown("---")

# --- 4. Filtrar y Mostrar OCs ---
today = pd.Timestamp.now().floor('D')

# Limpiamos las fechas y cantidades de OC
df_oc_clean = df_oc.copy()
try:
    df_oc_clean['Fecha de entrega de la línea'] = pd.to_datetime(df_oc_clean['Fecha de entrega de la línea'], format='%Y-m-%d', errors='coerce')
    df_oc_clean['Cantidad'] = pd.to_numeric(df_oc_clean['Cantidad'], errors='coerce')
except Exception as e:
    st.error(f"Error procesando datos de OC: {e}")
    st.stop()

# Convertimos la OC a string para permitir la búsqueda parcial
df_oc_clean['Número de documento'] = df_oc_clean['Número de documento'].astype(str)

# Empezamos con el filtro base (futuras y con cantidad)
df_llegadas_detalle = df_oc_clean[
    (df_oc_clean['Cantidad'] > 0) & 
    (df_oc_clean['Fecha de entrega de la línea'] >= today)  
].copy() # Hacemos una copia para evitar SettingWithCopyWarning

# Aplicamos el filtro de SKU si no es "Todas"
if sku_seleccionado != "Todas":
    df_llegadas_detalle = df_llegadas_detalle[
        df_llegadas_detalle['Número de artículo'] == sku_seleccionado
    ]

# Aplicamos el filtro de OC si se escribió algo
if oc_buscada:
    df_llegadas_detalle = df_llegadas_detalle[
        df_llegadas_detalle['Número de documento'].str.contains(
            oc_buscada, 
            case=False, # Ignora mayúsculas/minúsculas
            na=False    # Trata los NaN como si no coincidieran
        )
    ]

# --- 5. Mostrar DataFrame ---
if df_llegadas_detalle.empty:
    st.info("No se encontraron llegadas programadas que coincidan con los filtros.")
else:
    # Validamos que las columnas existan
    if 'Comentarios' not in df_llegadas_detalle.columns:
            df_llegadas_detalle['Comentarios'] = 'N/A' 
                
    if 'Número de documento' not in df_llegadas_detalle.columns:
            st.error("Columna 'Número de documento' (OC) no encontrada en OPOR.xlsx")
            st.stop()

    # Seleccionamos las columnas de interés
    df_display = df_llegadas_detalle[[
        'Número de documento',
        'Número de artículo',
        'Fecha de entrega de la línea',
        'Cantidad',
        'Comentarios'
    ]].copy()
    
    # Agregamos el nombre del artículo usando el mapa
    df_display['Nombre Artículo'] = df_display['Número de artículo'].map(mapa_nombres).fillna('Nombre no encontrado')
    
    # Reordenamos y Renombramos
    df_display = df_display[[
        'Número de documento',
        'Número de artículo',
        'Nombre Artículo',
        'Cantidad',
        'Fecha de entrega de la línea',
        'Comentarios'
    ]]
    
    df_display.rename(columns={
        'Número de documento': 'N° Orden Compra',
        'Número de artículo': 'SKU',
        'Nombre Artículo': 'Producto',
        'Cantidad': 'Cantidad',
        'Fecha de entrega de la línea': 'Fecha Llegada',
        'Comentarios': 'Comentarios'
    }, inplace=True)
    
    df_display = df_display.sort_values(by='Fecha Llegada')

    # Formateamos para mejor lectura
    df_display['Fecha Llegada'] = df_display['Fecha Llegada'].dt.strftime('%Y-%m-%d')
    df_display['Cantidad'] = df_display['Cantidad'].apply(lambda x: f"{x:,.0f}")

    st.dataframe(df_display, width='stretch', hide_index=True)