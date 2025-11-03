# --- ARCHIVO: pages/5_📈_Residencial.py ---
# (Versión Corregida con tipos de datos de Altair)

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
    # Convertimos las columnas a los tipos correctos
    df_residencial['kWp'] = pd.to_numeric(df_residencial['kWp'], errors='coerce')
    df_residencial['Fecha de ganado'] = pd.to_datetime(df_residencial['Fecha de ganado'], errors='coerce')
    df_residencial['Fecha de inicio de instalación real'] = pd.to_datetime(df_residencial['Fecha de inicio de instalación real'], errors='coerce')

    # Eliminamos filas donde las fechas o kWp sean nulos
    df_residencial = df_residencial.dropna(subset=['Fecha de ganado', 'Fecha de inicio de instalación real', 'kWp', 'CeCo'])

    # --- Cálculo de Métricas Clave ---
    # Días desde la venta hasta el inicio de la instalación
    df_residencial['Dias (Venta a Instalación)'] = (df_residencial['Fecha de inicio de instalación real'] - df_residencial['Fecha de ganado']).dt.days
    
    # Extraer Mes y Año para agrupar
    df_residencial['Mes Fecha de ganado'] = df_residencial['Fecha de ganado'].dt.to_period('M').astype(str)

    # Filtramos datos ilógicos (instalaciones antes de ganar)
    df_analisis = df_residencial[df_residencial['Dias (Venta a Instalación)'] >= 0].copy()

except Exception as e:
    st.error(f"Error al procesar los datos residenciales: {e}")
    st.info("Asegúrese que las columnas 'CeCo', 'kWp', 'Fecha de ganado', y 'Fecha de inicio de instalación real' existen en 'BD_Master_Residencial.xlsx'.")
    st.stop()

# --- 3. Mostrar KPIs Principales ---
st.subheader("KPIs Generales")

# Filtro de Años
anos_disponibles = sorted(df_analisis['Fecha de ganado'].dt.year.unique(), reverse=True)
if not anos_disponibles:
    st.warning("No hay datos suficientes para mostrar KPIs.")
    st.stop()
    
ano_seleccionado = st.selectbox("Seleccione Año para KPIs:", anos_disponibles)
df_filtrado = df_analisis[df_analisis['Fecha de ganado'].dt.year == ano_seleccionado]

if df_filtrado.empty:
    st.warning(f"No hay datos para el año {ano_seleccionado}.")
else:
    col1, col2, col3 = st.columns(3)
    col1.metric(
        label=f"Proyectos Fecha de ganados ({ano_seleccionado})",
        value=df_filtrado['CeCo'].nunique()
    )
    col2.metric(
        label=f"Total kWp Fecha de ganados ({ano_seleccionado})",
        value=f"{df_filtrado['kWp'].sum():,.1f} kWp"
    )
    col3.metric(
        label=f"Tiempo Prom. (Venta a Instalación) ({ano_seleccionado})",
        value=f"{df_filtrado['Dias (Venta a Instalación)'].mean():.1f} días"
    )

st.markdown("---")

# --- 4. Visualizaciones ---
st.subheader("Visualizaciones")

# --- Gráfico 1: kWp Fecha de ganados por Mes (CORREGIDO) ---
st.markdown("#### kWp Fecha de ganados por Mes")
chart_kWp_mes = alt.Chart(df_analisis).mark_bar().encode(
    # 'Fecha de ganado' es Temporal (T), 'yearmonth' es una función de Altair
    x=alt.X('yearmonth(Fecha de ganado):T', title='Mes (Proyecto Fecha de ganado)'),
    
    # 'kWp' es Cuantitativo (Q), le aplicamos la agregación 'sum'
    y=alt.Y('kWp:Q', aggregate='sum', title='Suma de kWp'),
    
    tooltip=[
        alt.Tooltip('yearmonth(Fecha de ganado):T', title='Mes'),
        alt.Tooltip('kWp:Q', aggregate='sum', title='Total kWp'),
        alt.Tooltip('count()', title='N° Proyectos') # 'count()' es la forma robusta de contar
    ]
).interactive()
st.altair_chart(chart_kWp_mes, use_container_width=True)


# --- Gráfico 2: N° de Proyectos Fecha de ganados por Mes (CORREGIDO) ---
st.markdown("#### N° de Proyectos Fecha de ganados por Mes")
chart_proyectos_mes = alt.Chart(df_analisis).mark_line(point=True).encode(
    x=alt.X('yearmonth(Fecha de ganado):T', title='Mes (Proyecto Fecha de ganado)'),
    
    # Usamos 'count()' para contar el número de registros (proyectos)
    y=alt.Y('count()', title='Número de Proyectos'),
    
    tooltip=[
        alt.Tooltip('yearmonth(Fecha de ganado):T', title='Mes'),
        alt.Tooltip('count()', title='N° Proyectos')
    ]
).interactive()
st.altair_chart(chart_proyectos_mes, use_container_width=True)


# --- (NUEVO) GRÁFICO 3: N° de Proyectos Iniciados (Instalación) por Mes ---
st.markdown("#### N° de Proyectos Iniciados (Instalación) por Mes")
chart_proyectos_instalados_mes = alt.Chart(df_analisis).mark_bar(color='#2ca02c', opacity=0.8).encode(
    # Usamos la columna 'Fecha de inicio de instalación real'
    x=alt.X('yearmonth(Fecha de inicio de instalación real):T', title='Mes (Inicio Instalación)'),
    
    # Usamos 'count()' para contar el número de proyectos
    y=alt.Y('count()', title='Número de Proyectos Iniciados'),
    
    tooltip=[
        alt.Tooltip('yearmonth(Fecha de inicio de instalación real):T', title='Mes Inicio'),
        alt.Tooltip('count()', title='N° Proyectos Iniciados')
    ]
).interactive()
st.altair_chart(chart_proyectos_instalados_mes, use_container_width=True)



# --- Gráfico 3: Histograma de Tiempos de Ciclo (CORREGIDO) ---
st.markdown("#### Distribución: Días de Venta a Instalación")
st.markdown("Muestra cuántos proyectos tardan 'X' días en comenzar a instalarse después de la venta.")
chart_histogram_lag = alt.Chart(df_analisis).mark_bar().encode(
    # 'Dias...' es Cuantitativo (Q) y lo agrupamos (bin=True)
    x=alt.X('Dias (Venta a Instalación):Q', bin=alt.Bin(maxbins=30), title='Días (Venta a Instalación)'),
    
    y=alt.Y('count()', title='Cantidad de Proyectos'),
    
    tooltip=[
        alt.Tooltip('Dias (Venta a Instalación):Q', bin=alt.Bin(maxbins=30), title='Rango (Días)'),
        alt.Tooltip('count()', title='Cantidad de Proyectos')
    ]
).interactive()
st.altair_chart(chart_histogram_lag, use_container_width=True)


# --- Gráfico 4: Relación entre Tamaño de Proyecto (kWp) y Tiempo (CORREGIDO) ---
st.markdown("#### Relación: kWp vs. Días de Venta a Instalación")
st.markdown("Ayuda a ver si los proyectos más grandes (más kWp) tardan más en instalarse.")
chart_scatter_lag_kWp = alt.Chart(df_analisis).mark_circle(opacity=0.6).encode(
    # 'kWp' es Cuantitativo (Q)
    x=alt.X('kWp:Q', title='kWp del Proyecto', scale=alt.Scale(zero=False)),
    
    # 'Dias...' es Cuantitativo (Q)
    y=alt.Y('Dias (Venta a Instalación):Q', title='Días (Venta a Instalación)', scale=alt.Scale(zero=False)),
    
    # 'CeCo' es Nominal (N)
    tooltip=['CeCo:N', 'kWp:Q', 'Dias (Venta a Instalación):Q']
).interactive()
st.altair_chart(chart_scatter_lag_kWp, use_container_width=True)

# --- 5. Detalle de Datos (Opcional) ---
with st.expander("Ver tabla de datos procesados"):
    st.dataframe(df_analisis, use_container_width=True)