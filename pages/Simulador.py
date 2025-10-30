# --- ARCHIVO: pages/1_📈_Simulador.py ---

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# --- Configuración del Path ---
# (Necesario en CADA archivo de 'pages' para encontrar 'src')
src_path = str(Path(__file__).resolve().parent.parent / "src")
if src_path not in sys.path:
    sys.path.append(src_path)

import config         # Importa constantes
import simulator      # Importa el motor de simulación
import ui_helpers     # Importa las funciones de gráficos y métricas
import altair as alt  # Importamos Altair

# --- 1. LÓGICA DE LA PÁGINA DEL SIMULADOR ---

# Verifica si los datos están cargados (deben haber sido cargados por app.py)
if 'data_loaded' not in st.session_state or not st.session_state.data_loaded:
    st.error("Los datos no se han cargado. Por favor, vuelva al Menú Principal e inténtelo de nuevo.")
    st.stop()

# --- Configuración de Idioma y Título del Simulador ---
ui_helpers.setup_locale() # Configura meses en español
st.title("Simulador de Proyección de Inventario 📈")

st.sidebar.markdown("---") # Separador

# --- 2. Acceder a los Datos desde st.session_state ---
# No los cargamos de nuevo, solo los referenciamos
df_stock = st.session_state.df_stock
df_oc = st.session_state.df_oc
df_consumo = st.session_state.df_consumo
# df_residencial no se usa en esta página, pero está disponible si se necesita

# --- 3. Construcción de la Barra Lateral (Sidebar) ---
st.sidebar.header("Configuración de Simulación")

# --- Listas para selectores ---
lista_skus_stock = df_stock['CodigoArticulo'].dropna().unique()
lista_skus_consumo = df_consumo['CodigoArticulo'].dropna().unique()
all_skus = sorted(list(set(lista_skus_stock) | set(lista_skus_consumo)))

lista_bodegas_stock = sorted(df_stock['CodigoBodega'].dropna().unique())
lista_bodegas_consumo = sorted(df_consumo['BodegaDestino_Requerida'].dropna().unique())

# --- Requerimiento 2: Selector de SKU (usando ui_helper) ---
opciones_selector_sku, mapa_nombres, default_index = ui_helpers.create_sku_options(all_skus, df_stock)

sku_seleccionado_formateado = st.sidebar.selectbox(
    "1. Seleccione un SKU (busque por código o nombre):",
    opciones_selector_sku, 
    index=default_index
)
sku_seleccionado = sku_seleccionado_formateado.split(" | ")[0]

# --- Otros Selectores ---
bodega_stock_sel = st.sidebar.selectbox(
    "2. Seleccione Bodega de Stock:",
    lista_bodegas_stock,
    index=lista_bodegas_stock.index('BF0001') if 'BF0001' in lista_bodegas_stock else 0
)

bodega_consumo_sel = st.sidebar.selectbox(
    "3. Seleccione Bodega de Consumo:",
    lista_bodegas_consumo,
    index=lista_bodegas_consumo.index('Bodega de Proyectos RE') if 'Bodega de Proyectos RE' in lista_bodegas_consumo else 0
)

st.sidebar.markdown("---")

# --- Parámetros de Simulación ---
service_level_str = st.sidebar.select_slider(
    "4. Nivel de Servicio (para Safety Stock):",
    options=list(config.Z_SCORE_MAP.keys()),
    value="99%"
)
service_level_z = config.Z_SCORE_MAP[service_level_str]

lead_time_days = st.sidebar.number_input("5. Lead Time (Días):", min_value=1, max_value=120, value=90)

dias_a_simular = st.sidebar.number_input("6. Días a Simular:", min_value=30, max_value=365, value=100)


# --- 4. Disparador de Ejecución ---
if st.sidebar.button("🚀 Ejecutar Simulación", type="primary"):
    with st.spinner("Calculando simulación..."):
        
        # --- A. Ejecutar Simulación ---
        df_sim, metrics, llegadas_map, df_llegadas_detalle = simulator.run_inventory_simulation(
            sku_to_simulate=sku_seleccionado,
            warehouse_code=bodega_stock_sel,
            consumption_warehouse=bodega_consumo_sel,
            df_stock_raw=df_stock,  # Pasando el df desde session_state
            df_consumo_raw=df_consumo, # Pasando el df desde session_state
            df_oc_raw=df_oc,       # Pasando el df desde session_state
            simulation_days=dias_a_simular,
            lead_time_days=lead_time_days,
            service_level_z=service_level_z
        )
        
        # --- B. Mostrar Métricas ---
        st.subheader(f"Resultados para: {sku_seleccionado}")
        st.caption(f"Nombre: {mapa_nombres.get(sku_seleccionado, 'N/A')}")
        ui_helpers.display_metrics(metrics, lead_time_days, service_level_z)
        
        # --- C. Mostrar Recomendación de Pedido (Refactorizada) ---
        st.markdown("---") # Separador
        ui_helpers.display_order_recommendation(metrics, llegadas_map, df_sim, lead_time_days)
        
        # --- D. Mostrar Detalle de Llegadas ---
        st.markdown("---") # Separador
        ui_helpers.display_arrival_details(df_llegadas_detalle)

        st.markdown("---") # Separador
        
        # --- E. Generar y Mostrar Gráfico ---
        sku_name = mapa_nombres.get(sku_seleccionado, sku_seleccionado)
        fig = ui_helpers.generate_simulation_plot(
            df_sim, 
            metrics, 
            llegadas_map, 
            sku_name, 
            dias_a_simular
        )
        st.altair_chart(fig, use_container_width=True)
        
        # --- F. Mostrar Tabla Fin de Mes (Req. 3) ---
        df_tabla_resultados = ui_helpers.prepare_end_of_month_table(df_sim)
        st.subheader("Stock Simulado a Fin de Mes")
        st.dataframe(df_tabla_resultados, width='stretch', hide_index=True)
        
else:
    # Mensaje de bienvenida inicial
    st.info("Ajuste los parámetros en la barra lateral y presione 'Ejecutar Simulación'")