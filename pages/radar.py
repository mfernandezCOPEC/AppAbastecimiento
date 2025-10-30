# --- ARCHIVO: pages/3_📡_Radar.py ---
# (NUEVA PÁGINA)

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# --- Configuración del Path ---
src_path = str(Path(__file__).resolve().parent.parent / "src")
if src_path not in sys.path:
    sys.path.append(src_path)

import config
import radar_engine # <-- Importamos nuestro nuevo motor
import ui_helpers # Para la barra lateral (si la tienes personalizada)

# --- 1. Configuración de Página ---
st.set_page_config(layout="wide", page_title="Radar de Inventario")
st.title("Radar de Inventario 📡")
st.markdown("Visión general del estado del inventario para priorizar acciones.")

# (Opcional: si tienes la barra lateral personalizada, descomenta la línea de abajo)
# ui_helpers.add_sidebar_navigation() 

# --- 2. Verificar Carga de Datos ---
if 'data_loaded' not in st.session_state or not st.session_state.data_loaded:
    st.error("Los datos no se han cargado. Por favor, vuelva al Menú Principal e inténtelo de nuevo.")
    st.stop()

# --- 3. Acceder a los Datos desde st.session_state ---
df_stock = st.session_state.df_stock
df_oc = st.session_state.df_oc
df_consumo = st.session_state.df_consumo

# --- 4. Controles de Simulación (en la página principal) ---
st.subheader("Parámetros del Reporte")

# Usamos los mismos selectores que el Simulador para consistencia
lista_bodegas_stock = sorted(df_stock['CodigoBodega'].dropna().unique())
lista_bodegas_consumo = sorted(df_consumo['BodegaDestino_Requerida'].dropna().unique())

col1, col2, col3, col4 = st.columns(4)
with col1:
    bodega_stock_sel = st.selectbox(
        "Bodega de Stock:",
        lista_bodegas_stock,
        index=lista_bodegas_stock.index('BF0001') if 'BF0001' in lista_bodegas_stock else 0
    )
with col2:
    bodega_consumo_sel = st.selectbox(
        "Bodega de Consumo:",
        lista_bodegas_consumo,
        index=lista_bodegas_consumo.index('Bodega de Proyectos RE') if 'Bodega de Proyectos RE' in lista_bodegas_consumo else 0
    )
with col3:
    service_level_str = st.select_slider(
        "Nivel de Servicio (para SS):",
        options=list(config.Z_SCORE_MAP.keys()),
        value="99%"
    )
    service_level_z = config.Z_SCORE_MAP[service_level_str]
with col4:
    lead_time_days = st.number_input("Lead Time (Días) (para ROP):", min_value=1, max_value=120, value=90)

# --- 5. Botón de Ejecución ---
if st.button("🚀 Generar Reporte de Radar", type="primary", width='stretch'):
    
    with st.spinner("Calculando KPIs para todos los SKUs... Esto puede tardar un momento."):
        df_radar = radar_engine.run_full_radar_analysis(
            df_stock,
            df_consumo,
            df_oc,
            bodega_stock_sel,
            bodega_consumo_sel,
            lead_time_days,
            service_level_z
        )

    if df_radar.empty:
        st.warning("No se encontraron datos para los parámetros seleccionados.")
    else:
        st.success(f"Reporte generado. Se analizaron {len(df_radar)} SKUs.")
        
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
        
        # Aplicar filtros
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
            file_name=f"radar_inventario_{bodega_stock_sel}.csv",
            mime="text/csv",
            width='stretch'
        )
else:
    st.info("Ajuste los parámetros y presione 'Generar Reporte de Radar' para comenzar.")