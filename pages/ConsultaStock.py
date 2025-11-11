# --- ARCHIVO: pages/3_📡_Radar.py ---
# (PÁGINA MODIFICADA CON FILTRO DE FAMILIA)

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# --- Configuración del Path ---
# Asegura que la app pueda encontrar los módulos en la carpeta 'src'
src_path = str(Path(__file__).resolve().parent.parent / "src")
if src_path not in sys.path:
    sys.path.append(src_path)

import config
import radar_engine # <-- Importamos nuestro motor de radar
import ui_helpers # Para la barra lateral (si la tienes personalizada)

# --- 1. Configuración de Página ---
st.set_page_config(layout="wide", page_title="Radar de Inventario")
st.title("Radar de Inventario 📡")
st.markdown("Visión general del estado del inventario para priorizar acciones.")

# (Opcional: si tienes la barra lateral personalizada, descomenta la línea de abajo)
# ui_helpers.add_sidebar_navigation() 

# --- 2. Verificar Carga de Datos ---
# Comprueba si los datos fueron cargados en la página principal (Menu.py)
if 'data_loaded' not in st.session_state or not st.session_state.data_loaded:
    st.error("Los datos no se han cargado. Por favor, vuelva al Menú Principal e inténtelo de nuevo.")
    st.stop() # Detiene la ejecución de la página si no hay datos

# --- 3. Acceder a los Datos desde st.session_state ---
# Trae los DataFrames cargados desde la memoria de la sesión
df_stock = st.session_state.df_stock
df_oc = st.session_state.df_oc
df_consumo = st.session_state.df_consumo

# --- 4. Controles de Simulación (en la página principal) ---
st.subheader("Parámetros del Reporte")

# --- NUEVO: Obtener lista de Familias ---
try:
    # Obtiene valores únicos de la col 'Familia', elimina nulos (NaN), ordena alfabéticamente
    familias_list = sorted(df_stock['Familia'].dropna().unique())
    # Inserta "Todas" al principio de la lista como opción por defecto
    familias_list.insert(0, "Todas")
except KeyError:
    # Maneja el error si la columna 'Familia' no existe en Stock.xlsx
    st.error("Error: La columna 'Familia' no se encontró en 'Stock.xlsx'. No se puede filtrar.")
    familias_list = ["Todas"] # Permite que la app continúe
# --- FIN NUEVO ---

# Obtiene listas únicas para los filtros de bodega
lista_bodegas_stock = sorted(df_stock['CodigoBodega'].dropna().unique())
lista_bodegas_consumo = sorted(df_consumo['BodegaDestino_Requerida'].dropna().unique())

# --- MODIFICADO: 5 columnas para incluir el nuevo filtro de Familia ---
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    # --- NUEVO: Widget de filtro por Familia ---
    familia_sel = st.selectbox(
        "Familia (Categoría):",
        familias_list,
        index=0  # Por defecto selecciona "Todas"
    )
    # --- FIN NUEVO ---
with col2:
    bodega_stock_sel = st.selectbox(
        "Bodega de Stock:",
        lista_bodegas_stock,
        index=lista_bodegas_stock.index('BF0001') if 'BF0001' in lista_bodegas_stock else 0
    )
with col3:
    bodega_consumo_sel = st.selectbox(
        "Bodega de Consumo:",
        lista_bodegas_consumo,
        index=lista_bodegas_consumo.index('Bodega de Proyectos RE') if 'Bodega de Proyectos RE' in lista_bodegas_consumo else 0
    )
with col4:
    service_level_str = st.select_slider(
        "Nivel de Servicio (para SS):",
        options=list(config.Z_SCORE_MAP.keys()),
        value="99%"
    )
    service_level_z = config.Z_SCORE_MAP[service_level_str]
with col5: # Movido a col5
    lead_time_days = st.number_input("Lead Time (Días) (para ROP):", min_value=1, max_value=120, value=90)

# --- 5. Botón de Ejecución ---
if st.button("🚀 Generar Reporte de Radar", type="primary", width='stretch'):
    
    # --- NUEVO: Pre-filtrado de DataFrames por Familia ---
    # Por defecto, usamos los DataFrames completos cargados en sesión
    df_stock_radar = df_stock
    df_consumo_radar = df_consumo
    df_oc_radar = df_oc

    # Si el usuario selecciona una familia específica (diferente a "Todas")
    if familia_sel != "Todas":
        try:
            # 1. Filtra el DataFrame de stock
            df_stock_radar = df_stock[df_stock['Familia'] == familia_sel]
            
            if df_stock_radar.empty:
                st.warning(f"No se encontraron SKUs de stock para la familia '{familia_sel}'.")
                st.stop() # Detiene la ejecución si no hay nada que procesar

            # 2. Obtiene la lista de SKUs únicos que pertenecen a esa familia
            #    (Asegúrate que la columna de SKU se llame 'SKU' en tus 3 archivos)
            skus_de_familia = df_stock_radar['SKU'].unique() 
            
            # 3. Filtra Consumo y OC para que solo incluyan esos SKUs
            df_consumo_radar = df_consumo[df_consumo['SKU'].isin(skus_de_familia)]
            df_oc_radar = df_oc[df_oc['SKU'].isin(skus_de_familia)]
            
            st.info(f"Filtrando por {len(skus_de_familia)} SKUs de la familia '{familia_sel}'.")

        except KeyError as e:
            # Captura error si 'Familia' o 'SKU' no existen
            st.error(f"Error: No se encontró la columna 'Familia' o 'SKU' en los DataFrames. Detalle: {e}")
            st.stop()
    # --- FIN NUEVO ---
    
    with st.spinner("Calculando KPIs para todos los SKUs... Esto puede tardar un momento."):
        df_radar = radar_engine.run_full_radar_analysis(
            # --- MODIFICADO: Usar DFs filtrados ---
            df_stock_radar,
            df_consumo_radar,
            df_oc_radar,
            # --- FIN MODIFICADO ---
            bodega_stock_sel,
            bodega_consumo_sel,
            lead_time_days,
            service_level_z
        )

    # --- MODIFICADO: Mensajes de resultado con filtro ---
    if df_radar.empty:
        st.warning(f"No se encontraron datos para los parámetros seleccionados (Familia: {familia_sel}).")
    else:
        st.success(f"Reporte generado. Se analizaron {len(df_radar)} SKUs para la familia '{familia_sel}'.")
    # --- FIN MODIFICADO ---
        
        # --- 6. Mostrar Resultados ---
        st.subheader("Resultados del Radar")
        
        # Opciones de visualización
        col1, col2 = st.columns([1, 1])
        with col1:
            filtro_alerta = st.selectbox(
                "Filtrar por Alerta:",
                ["Todas", "Solo Alertas de Stock 🔴", "Solo Alertas Proyectadas 🔴"]
            )
        
        df_display = df_radar.copy()
        
        # Aplicar filtros de visualización
        if filtro_alerta == "Solo Alertas de Stock 🔴":
            df_display = df_display[df_display["Alerta Stock (vs SS)"] == "🔴"]
        elif filtro_alerta == "Solo Alertas Proyectadas 🔴":
            df_display = df_display[df_display["Alerta Proy. (vs ROP)"] == "🔴"]

        # Formatear el DataFrame para visualización
        st.dataframe(
            df_display.sort_values(by="DOS (Días)"), # Ordenar por el más crítico
            width='stretch',
            hide_index=True,
            column_config={
                "Stock Actual": st.column_config.NumberColumn(format="%.0f"),
                "DOS (Días)": st.column_config.NumberColumn(format="%.1f"),
                "Stock Proy. (en LT)": st.column_config.NumberColumn(format="%.0f"),
                "ROP": st.column_config.NumberColumn(format="%.0f"),
                "Pedido Sugerido": st.column_config.NumberColumn(format="%.0f"),
                "Demanda Prom. Diaria": st.column_config.NumberColumn(format="%.2f"),
            }
        )
        
        # Guardar en sesión para descargar
        st.session_state.df_radar_results = df_display.to_csv(index=False).encode('utf-8')

    if 'df_radar_results' in st.session_state:
        st.download_button(
            label="📥 Descargar Reporte (.csv)",
            data=st.session_state.df_radar_results,
            # --- MODIFICADO: Nombre de archivo más descriptivo ---
            file_name=f"radar_inventario_{familia_sel.replace(' ', '_')}_{bodega_stock_sel}.csv",
            mime="text/csv",
            width='stretch'
        )
else:
    st.info("Ajuste los parámetros y presione 'Generar Reporte de Radar' para comenzar.")