# --- ARCHIVO: pages/1_📈_Simulador.py ---
# (Modificado para selección múltiple de bodegas y mostrar tabla de consumo)
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
# Verifica si los datos están cargados (deben haber sido cargados por app.py
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

# --- (MODIFICADO) Selectores de Bodega con Default Específico ---
# (MODIFICADO) Lógica para default de Bodega de Stock
default_stock_val = 'BF0001'
if default_stock_val in lista_bodegas_stock:
    default_stock_selection = [default_stock_val]
elif lista_bodegas_stock: # Si BF0001 no está, selecciona el primero de la lista
    default_stock_selection = [lista_bodegas_stock[0]]
else:
    default_stock_selection = [] # Lista vacía si no hay opciones

bodega_stock_sel = st.sidebar.multiselect(
    "2. Seleccione Bodega(s) de Stock:",
    options=lista_bodegas_stock,
    default=default_stock_selection # <-- Default cambiado
)

# (MODIFICADO) Lógica para default de Bodega de Consumo
default_consumo_val = 'Bodega de Proyectos RE'
if default_consumo_val in lista_bodegas_consumo:
    default_consumo_selection = [default_consumo_val]
elif lista_bodegas_consumo: # Si 'Bodega de Proyectos RE' no está, selecciona el primero
    default_consumo_selection = [lista_bodegas_consumo[0]]
else:
    default_consumo_selection = [] # Lista vacía si no hay opciones

bodega_consumo_sel = st.sidebar.multiselect(
    "3. Seleccione Bodega(s) de Consumo:",
    options=lista_bodegas_consumo,
    default=default_consumo_selection # <-- Default cambiado
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
    # (NUEVO) Verificación de que se seleccionó al menos una bodega
    if not bodega_stock_sel:
        st.error("Por favor, seleccione al menos una Bodega de Stock.")
        st.stop()
    if not bodega_consumo_sel:
        st.error("Por favor, seleccione al menos una Bodega de Consumo.")
        st.stop()

    with st.spinner("Calculando simulación..."):

        # --- A. Ejecutar Simulación ---
        # (MODIFICADO) Pasamos las listas 'bodega_stock_sel' y 'bodega_consumo_sel'
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

        # --- G. Mostrar Tabla de Consumo Utilizada ---
        st.markdown("---")
        with st.expander("Ver datos de consumo utilizados para esta simulación"):

            st.subheader(f"Historial de Consumo para {sku_seleccionado}")
            st.caption(f"Filtrado por bodegas: {', '.join(bodega_consumo_sel)}")

            # Re-filtramos los datos de consumo tal como lo hace el simulador
            # (El df_consumo global ya fue filtrado por fecha en data_loader.py)
            df_consumo_usado = df_consumo[
                (df_consumo['CodigoArticulo'] == sku_seleccionado) &
                (df_consumo['BodegaDestino_Requerida'].isin(bodega_consumo_sel))
            ].copy()

            if df_consumo_usado.empty:
                st.warning("No se encontró historial de consumo para este SKU y bodegas.")
            else:
                # --- INICIO DE LA MODIFICACIÓN ---
                # Limpiamos y seleccionamos columnas relevantes para mostrar
                columnas_a_mostrar = [
                    'FechaSolicitud', 
                    'CantidadSolicitada', 
                    'BodegaDestino_Requerida',
                    'SolicitadoPor',         # <-- Columna añadida
                    'CodigoProyecto',         # <-- Columna añadida
                    'NombreProyecto',         # <-- Columna añadida
                    'CodigoUnidadNegocio',    # <-- Columna añadida
                    'CeCo' # Este es un supuesto, podría no estar
                ]
                # --- FIN DE LA MODIFICACIÓN ---
                # Filtramos solo columnas que realmente existen en el DataFrame
                columnas_existentes = [col for col in columnas_a_mostrar if col in df_consumo_usado.columns]
                df_display_consumo = df_consumo_usado[columnas_existentes].sort_values(by='FechaSolicitud', ascending=False)
                st.dataframe(df_display_consumo, use_container_width=True)
                # Mostramos un resumen del consumo mensual
                st.subheader("Resumen de Consumo Mensual (Base del Cálculo)")
                try:
                    df_consumo_usado['FechaSolicitud'] = pd.to_datetime(df_consumo_usado['FechaSolicitud'])
                    consumo_mensual = df_consumo_usado.set_index('FechaSolicitud')['CantidadSolicitada'].resample('MS').sum().reset_index()
                    consumo_mensual.columns = ["Mes", "Total Solicitado"]
                    st.dataframe(consumo_mensual.sort_values(by="Mes", ascending=False), use_container_width=True)
                except Exception as e:
                    st.error(f"No se pudo generar el resumen mensual: {e}")

else:
    # Mensaje de bienvenida inicial
    st.info("Ajuste los parámetros en la barra lateral y presione 'Ejecutar Simulación'")