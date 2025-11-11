# --- ARCHIVO: pages/3_📡_Radar.py ---
# (VERSIÓN REACTIVA CON SELECCIÓN INICIAL REQUERIDA)

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# --- Configuración del Path ---
src_path = str(Path(__file__).resolve().parent.parent / "src")
if src_path not in sys.path:
    sys.path.append(src_path)

import config
import radar_engine 
import ui_helpers 

# --- 1. Configuración de Página ---
st.set_page_config(layout="wide", page_title="Radar de Inventario")
st.title("Radar de Inventario 📡")
st.markdown("Visión general del estado del inventario para priorizar acciones.")

# --- 2. Verificar Carga de Datos ---
if 'data_loaded' not in st.session_state or not st.session_state.data_loaded:
    st.error("Los datos no se han cargado. Por favor, vuelva al Menú Principal e inténtelo de nuevo.")
    st.stop()

# --- 3. Acceder a los Datos desde st.session_state ---
df_stock = st.session_state.df_stock
df_oc = st.session_state.df_oc
df_consumo = st.session_state.df_consumo

# --- 4. Controles de Simulación ---
st.subheader("Parámetros del Reporte")

# --- MODIFICADO: Obtener lista de Familias con Placeholder ---
try:
    familias_list = sorted(df_stock['Familia'].dropna().unique())
    # Añadimos "Todas"
    familias_list.insert(0, "Todas")
    # Añadimos el placeholder como la primera opción
    familias_list.insert(0, "(Seleccione una Familia)") 
except KeyError:
    st.error("Error: La columna 'Familia' no se encontró en 'Stock.xlsx'. No se puede filtrar.")
    familias_list = ["(Seleccione una Familia)"]
# --- FIN MODIFICADO ---

# Obtiene listas únicas para los filtros de bodega
lista_bodegas_stock = sorted(df_stock['CodigoBodega'].dropna().unique())
lista_bodegas_consumo = sorted(df_consumo['BodegaDestino_Requerida'].dropna().unique())

# --- 5 columnas para filtros ---
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    # --- MODIFICADO: Filtro por Familia con Placeholder ---
    familia_sel = st.selectbox(
        "Familia (Categoría):",
        familias_list,
        index=0  # Por defecto selecciona "(Seleccione una Familia)"
    )
    # --- FIN MODIFICADO ---
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
with col5: 
    lead_time_days = st.number_input("Lead Time (Días) (para ROP):", min_value=1, max_value=120, value=90)


# --- 5. LÓGICA DE EJECUCIÓN (CON BLOQUEO INICIAL) ---
# Solo se ejecuta si el usuario ha seleccionado una familia válida (incluyendo "Todas")
if familia_sel != "(Seleccione una Familia)":

    # --- Pre-filtrado de DataFrames por Familia ---
    df_stock_radar = df_stock
    df_consumo_radar = df_consumo
    df_oc_radar = df_oc

    if familia_sel != "Todas":
        try:
            # 1. Filtra el DataFrame de stock
            df_stock_radar = df_stock[df_stock['Familia'] == familia_sel]
            
            if df_stock_radar.empty:
                st.warning(f"No se encontraron SKUs de stock para la familia '{familia_sel}'.")
                st.stop()

            # 2. Obtiene la lista de SKUs únicos que pertenecen a esa familia
            skus_de_familia = df_stock_radar['CodigoArticulo'].unique() 
            
            # 3. Filtra Consumo y OC para que solo incluyan esos SKUs
            df_consumo_radar = df_consumo[df_consumo['CodigoArticulo'].isin(skus_de_familia)]
            df_oc_radar = df_oc[df_oc['Número de artículo'].isin(skus_de_familia)]
            
            st.info(f"Filtrando por {len(skus_de_familia)} SKUs de la familia '{familia_sel}'.")

        except KeyError as e:
            st.error(f"Error: No se encontró la columna 'Familia' o 'SKU' en los DataFrames. Detalle: {e}")
            st.stop()
    # --- Fin Pre-filtrado ---

    with st.spinner("Calculando KPIs para todos los SKUs... Esto puede tardar un momento."):
        df_radar = radar_engine.run_full_radar_analysis(
            df_stock_radar,
            df_consumo_radar,
            df_oc_radar,
            bodega_stock_sel,
            bodega_consumo_sel,
            lead_time_days,
            service_level_z
        )

    # --- Mensajes de resultado ---
    if df_radar.empty:
        st.warning(f"No se encontraron datos para los parámetros seleccionados (Familia: {familia_sel}).")
        
        # Limpia resultados anteriores si esta corrida no produce nada
        if 'df_radar_results' in st.session_state:
            del st.session_state.df_radar_results
            
    else:
        st.success(f"Reporte generado. Se analizaron {len(df_radar)} SKUs para la familia '{familia_sel}'.")
        
        # --- 6. Mostrar Resultados ---
        st.subheader("Resultados del Radar")
        
        col1_res, col2_res = st.columns([1, 1])
        with col1_res:
            # ESTE ES EL FILTRO DE VISUALIZACIÓN
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

    # El botón de descarga solo aparece si hay resultados
    if 'df_radar_results' in st.session_state:
        st.download_button(
            label="📥 Descargar Reporte (.csv)",
            data=st.session_state.df_radar_results,
            file_name=f"radar_inventario_{familia_sel.replace(' ', '_')}_{bodega_stock_sel}.csv",
            mime="text/csv",
            width='stretch'
        )

# --- FIN DEL BLOQUE 'if' ---

else:
    # --- MENSAJE INICIAL ---
    # Esto es lo que se muestra cuando familia_sel == "(Seleccione una Familia)"
    st.info("Por favor, seleccione una familia y ajuste los parámetros para comenzar el análisis.")
    
    # Limpia el botón de descarga si volvemos al estado inicial
    if 'df_radar_results' in st.session_state:
        del st.session_state.df_radar_results