# --- ARCHIVO: pages/5_📈_Residencial.py ---
# (Versión Corregida con lógica de datos separada)

import streamlit as st
import pandas as pd
import altair as alt
import sys
from pathlib import Path

# --- Configuración del Path ---
# (Necesario en CADA archivo de 'pages' para encontrar 'src')
src_path = str(Path(__file__).resolve().parent.parent / "src")
if src_path not in sys.path:
    sys.path.append(src_path)

import ui_helpers  # Importamos los helpers para la localización

# --- 1. Configuración de Página y Verificación de Datos ---
st.set_page_config(layout="wide", page_title="Análisis Residencial")
ui_helpers.setup_locale() # Configura meses en español

st.title("Análisis de Proyectos Residenciales 🏡")
st.markdown("KPIs sobre ventas, potencia instalada y tiempos de ciclo.")

if 'data_loaded' not in st.session_state or not st.session_state.data_loaded:
    st.error("Los datos no se han cargado. Por favor, vuelva al Menú Principal.")
    st.stop()

# --- 2. Acceder y Preparar los Datos ---
try:
    # Usamos los datos cargados en la sesión
    df_residencial = st.session_state.df_residencial.copy()

    # --- Limpieza y Transformación de Datos ---
    # Convertimos las columnas a los tipos correctos (usando los nombres de tu código)
    df_residencial['kWp'] = pd.to_numeric(df_residencial['kWp'], errors='coerce')
    df_residencial['Fecha de ganado'] = pd.to_datetime(df_residencial['Fecha de ganado'], errors='coerce')
    df_residencial['Fecha de inicio de instalación real'] = pd.to_datetime(df_residencial['Fecha de inicio de instalación real'], errors='coerce')

    # --- (CORRECCIÓN IMPORTANTE) ---
    # CREAMOS DOS DATAFRAMES:
    
    # 1. df_ventas: Para KPIs de ventas. Solo requiere datos de venta.
    df_ventas = df_residencial.dropna(subset=['Fecha de ganado', 'kWp', 'CeCo']).copy()
    df_ventas['Mes Fecha de ganado'] = df_ventas['Fecha de ganado'].dt.to_period('M').astype(str)

    # 2. df_instalaciones: Para KPIs de ciclo e instalación. Requiere AMBAS fechas.
    df_instalaciones = df_residencial.dropna(subset=['Fecha de ganado', 'Fecha de inicio de instalación real', 'kWp', 'CeCo']).copy()
    
    # --- Cálculo de Métricas Clave (Solo en df_instalaciones) ---
    if not df_instalaciones.empty:
        # Días desde la venta hasta el inicio de la instalación
        df_instalaciones['Dias (Venta a Instalación)'] = (df_instalaciones['Fecha de inicio de instalación real'] - df_instalaciones['Fecha de ganado']).dt.days
        
        # Filtramos datos ilógicos (instalaciones antes de ganar)
        df_instalaciones = df_instalaciones[df_instalaciones['Dias (Venta a Instalación)'] >= 0].copy()

except Exception as e:
    st.error(f"Error al procesar los datos residenciales: {e}")
    st.info("Asegúrese que las columnas 'CeCo', 'kWp', 'Fecha de ganado', y 'Fecha de inicio de instalación real' existen en 'BD_Master_Residencial.xlsx'.")
    st.stop()

# --- 3. Mostrar KPIs Principales ---
st.subheader("KPIs Generales")

# El filtro de año se basa en las VENTAS (df_ventas)
anos_disponibles = sorted(df_ventas['Fecha de ganado'].dt.year.unique(), reverse=True)
if not anos_disponibles:
    st.warning("No hay datos suficientes para mostrar KPIs.")
    st.stop()
    
ano_seleccionado = st.selectbox("Seleccione Año para KPIs:", anos_disponibles)

# Filtramos ambos DataFrames
df_filtrado_ventas = df_ventas[df_ventas['Fecha de ganado'].dt.year == ano_seleccionado]
df_filtrado_instal = df_instalaciones[df_instalaciones['Fecha de ganado'].dt.year == ano_seleccionado]

if df_filtrado_ventas.empty:
    st.warning(f"No hay datos para el año {ano_seleccionado}.")
else:
    col1, col2, col3 = st.columns(3)
    # KPI de Ventas (usa df_filtrado_ventas)
    col1.metric(
        label=f"Proyectos Ganados ({ano_seleccionado})",
        value=df_filtrado_ventas['CeCo'].nunique()
    )
    # KPI de Ventas (usa df_filtrado_ventas)
    col2.metric(
        label=f"Total kWp Ganados ({ano_seleccionado})",
        value=f"{df_filtrado_ventas['kWp'].sum():,.1f} kWp"
    )
    # KPI de Ciclo (usa df_filtrado_instal)
    if not df_filtrado_instal.empty:
        col3.metric(
            label=f"Tiempo Prom. (Venta a Instalación) ({ano_seleccionado})",
            value=f"{df_filtrado_instal['Dias (Venta a Instalación)'].mean():.1f} días"
        )
    else:
        col3.metric(
            label=f"Tiempo Prom. (Venta a Instalación) ({ano_seleccionado})",
            value="N/A"
        )

st.markdown("---")

# --- 4. Visualizaciones ---
st.subheader("Visualizaciones")

# --- Gráfico 1: kWp Ganados por Mes ---
st.markdown("#### kWp Ganados por Mes")
chart_kWp_mes = alt.Chart(df_ventas).mark_bar().encode( # Usa df_ventas
    x=alt.X('yearmonth(Fecha de ganado):T', title='Mes (Proyecto Ganado)'),
    y=alt.Y('kWp:Q', aggregate='sum', title='Suma de kWp'),
    tooltip=[
        alt.Tooltip('yearmonth(Fecha de ganado):T', title='Mes'),
        alt.Tooltip('kWp:Q', aggregate='sum', title='Total kWp'),
        alt.Tooltip('count()', title='N° Proyectos')
    ]
).interactive()
st.altair_chart(chart_kWp_mes, use_container_width=True)

# --- Gráfico 2: N° de Proyectos Ganados por Mes ---
st.markdown("#### N° de Proyectos Ganados por Mes")
chart_proyectos_mes = alt.Chart(df_ventas).mark_line(point=True).encode( # Usa df_ventas
    x=alt.X('yearmonth(Fecha de ganado):T', title='Mes (Proyecto Ganado)'),
    y=alt.Y('count()', title='Número de Proyectos'),
    tooltip=[
        alt.Tooltip('yearmonth(Fecha de ganado):T', title='Mes'),
        alt.Tooltip('count()', title='N° Proyectos')
    ]
).interactive()
st.altair_chart(chart_proyectos_mes, use_container_width=True)


# --- Gráfico 3: N° de Proyectos Iniciados (Instalación) por Mes ---
st.markdown("#### N° de Proyectos Iniciados (Instalación) por Mes")
chart_proyectos_instalados_mes = alt.Chart(df_instalaciones).mark_bar(color='#2ca02c', opacity=0.8).encode( # Usa df_instalaciones
    x=alt.X('yearmonth(Fecha de inicio de instalación real):T', title='Mes (Inicio Instalación)'),
    y=alt.Y('count()', title='Número de Proyectos Iniciados'),
    tooltip=[
        alt.Tooltip('yearmonth(Fecha de inicio de instalación real):T', title='Mes Inicio'),
        alt.Tooltip('count()', title='N° Proyectos Iniciados')
    ]
).interactive()
st.altair_chart(chart_proyectos_instalados_mes, use_container_width=True)

# --- (NUEVO) GRÁFICO 4: kWp Instalados por Mes ---
st.markdown("#### kWp Instalados por Mes")
chart_kWp_instalados_mes = alt.Chart(df_instalaciones).mark_bar(color='#1f77b4', opacity=0.8).encode( # Usa df_instalaciones
    # Usamos la columna 'Fecha de inicio de instalación real'
    x=alt.X('yearmonth(Fecha de inicio de instalación real):T', title='Mes (Inicio Instalación)'),
    
    # Sumamos los 'kWp'
    y=alt.Y('kWp:Q', aggregate='sum', title='Suma de kWp Instalados'),
    
    tooltip=[
        alt.Tooltip('yearmonth(Fecha de inicio de instalación real):T', title='Mes Inicio'),
        alt.Tooltip('kWp:Q', aggregate='sum', title='Total kWp Instalados'),
        alt.Tooltip('count()', title='N° Proyectos Iniciados')
    ]
).interactive()
st.altair_chart(chart_kWp_instalados_mes, use_container_width=True)


# --- Gráfico 5: Histograma de Tiempos de Ciclo ---
st.markdown("#### Distribución: Días de Venta a Instalación")
st.markdown("Muestra cuántos proyectos tardan 'X' días en comenzar a instalarse después de la venta.")
chart_histogram_lag = alt.Chart(df_instalaciones).mark_bar().encode( # Usa df_instalaciones
    x=alt.X('Dias (Venta a Instalación):Q', bin=alt.Bin(maxbins=30), title='Días (Venta a Instalación)'),
    y=alt.Y('count()', title='Cantidad de Proyectos'),
    tooltip=[
        alt.Tooltip('Dias (Venta a Instalación):Q', bin=alt.Bin(maxbins=30), title='Rango (Días)'),
        alt.Tooltip('count()', title='Cantidad de Proyectos')
    ]
).interactive()
st.altair_chart(chart_histogram_lag, use_container_width=True)


# --- Gráfico 6: Relación entre Tamaño de Proyecto (kWp) y Tiempo ---
st.markdown("#### Relación: kWp vs. Días de Venta a Instalación")
st.markdown("Ayuda a ver si los proyectos más grandes (más kWp) tardan más en instalarse.")
chart_scatter_lag_kWp = alt.Chart(df_instalaciones).mark_circle(opacity=0.6).encode( # Usa df_instalaciones
    x=alt.X('kWp:Q', title='kWp del Proyecto', scale=alt.Scale(zero=False)),
    y=alt.Y('Dias (Venta a Instalación):Q', title='Días (Venta a Instalación)', scale=alt.Scale(zero=False)),
    tooltip=['CeCo:N', 'kWp:Q', 'Dias (Venta a Instalación):Q']
).interactive()
st.altair_chart(chart_scatter_lag_kWp, use_container_width=True)

# --- 5. Detalle de Datos (Opcional) ---
with st.expander("Ver tabla de datos de Ventas (Todos los ganados)"):
    st.dataframe(df_ventas, use_container_width=True)

with st.expander("Ver tabla de datos de Instalaciones (Solo con fecha de inicio)"):
    st.dataframe(df_instalaciones, use_container_width=True)