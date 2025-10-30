# --- ARCHIVO: src/ui_helpers.py ---
# (Modificado para importar 'config' y 'analysis' desde 'src')

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import locale
import config   # Importa config.py desde la misma carpeta 'src'
import analysis # Importa analysis.py desde la misma carpeta 'src'
import altair as alt


def setup_locale():
    """Configura el locale a español para los nombres de los meses."""
    try:
        locale.setlocale(locale.LC_TIME, config.LOCALE_ES)
    except locale.Error:
        try:
            locale.setlocale(locale.LC_TIME, config.LOCALE_ES_FALLBACK)
        except locale.Error:
            print(f"Locale '{config.LOCALE_ES}' o '{config.LOCALE_ES_FALLBACK}' no encontrado.")

def create_sku_options(all_skus, df_stock):
    """
    Crea la lista de opciones para el selector de SKU (Req. 2).
    Formato: "SKU | Nombre"
    """
    mapa_nombres = df_stock.drop_duplicates(subset=['CodigoArticulo']).set_index('CodigoArticulo')['NombreArticulo'].to_dict()
    
    opciones_selector_sku = []
    for sku in all_skus:
        nombre = mapa_nombres.get(sku, "Nombre no encontrado")
        opciones_selector_sku.append(f"{sku} | {nombre}")
        
    # Buscar el índice del SKU por defecto
    default_sku = 'EXI-009231'
    default_index = 0
    for i, option in enumerate(opciones_selector_sku):
        if option.startswith(default_sku):
            default_index = i
            break
            
    return opciones_selector_sku, mapa_nombres, default_index

def display_metrics(metrics, lead_time_days, service_level_z):
    """Muestra todas las métricas en la app de Streamlit."""
    
    st.subheader("Métricas Clave")
    col1, col2, col3 = st.columns(3)
    col1.metric("Stock Inicial (Disp.)", f"{metrics['initial_stock']:,.0f}")
    col2.metric("Consumo Prom. (Simulación)", f"{metrics['monthly_demand_mean']:,.0f}", 
                help="Promedio mensual de todos los datos de consumo cargados, usado para calcular SS y ROP.")
    col3.metric("Llegadas Programadas", f"{metrics['llegadas_count']}")
    
    st.markdown("---")

    # Requerimiento 1: Consumo histórico
    st.subheader("Consumo Histórico Reciente")
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric(f"Demanda {metrics['demand_M_0'][0].strftime('%B').capitalize()} (Actual)", f"{metrics['demand_M_0'][1]:,.0f}")
    col2.metric(f"Demanda {metrics['demand_M_1'][0].strftime('%B').capitalize()}", f"{metrics['demand_M_1'][1]:,.0f}")
    col3.metric(f"Demanda {metrics['demand_M_2'][0].strftime('%B').capitalize()}", f"{metrics['demand_M_2'][1]:,.0f}")
    col4.metric(f"Demanda {metrics['demand_M_3'][0].strftime('%B').capitalize()}", f"{metrics['demand_M_3'][1]:,.0f}")
    
    # Gráfico de Barras de Consumo Histórico
    st.write("") 
    
    try:
        hist_data = [
            {"Fecha": metrics['demand_M_3'][0], "Consumo": metrics['demand_M_3'][1], "Mes": metrics['demand_M_3'][0].strftime('%Y-%m')},
            {"Fecha": metrics['demand_M_2'][0], "Consumo": metrics['demand_M_2'][1], "Mes": metrics['demand_M_2'][0].strftime('%Y-%m')},
            {"Fecha": metrics['demand_M_1'][0], "Consumo": metrics['demand_M_1'][1], "Mes": metrics['demand_M_1'][0].strftime('%Y-%m')},
            {"Fecha": metrics['demand_M_0'][0], "Consumo": metrics['demand_M_0'][1], "Mes": metrics['demand_M_0'][0].strftime('%Y-%m')},
        ]
        df_hist = pd.DataFrame(hist_data)
        
        chart_hist = alt.Chart(df_hist).mark_line(point=True).encode(
            x=alt.X('Mes:O', 
                    sort=alt.EncodingSortField(field="Fecha", op="min", order='ascending'), 
                    title='Mes'), 
            y=alt.Y('Consumo:Q', title='Consumo Mensual'),
            tooltip=[
                alt.Tooltip('Mes:O'),
                alt.Tooltip('Consumo:Q', format=',.0f')
            ]
        ).properties(
            title='Consumo Histórico de Meses Usados para Simulación'
        )
        
        st.altair_chart(chart_hist, use_container_width=True)
        
    except Exception as e:
        st.warning(f"No se pudo generar el gráfico de consumo histórico: {e}")

    st.markdown("---")
    
    st.subheader("Parámetros de Simulación (Calculados)")
    col1, col2, col3 = st.columns(3)
    col1.metric("Lead Time (Días)", f"{lead_time_days}", help="Parámetro de entrada.")
    col2.metric("Safety Stock (SS)", f"{metrics['safety_stock']:,.0f}", f"Nivel Servicio {service_level_z}Z")
    col3.metric("Punto de Reorden (ROP)", f"{metrics['reorder_point']:,.0f}")

def generate_simulation_plot(df_sim, metrics, llegadas_map, sku_name, simulation_days):
    """
    Genera un gráfico interactivo de Altair.
    (El contenido de esta función no cambia)
    """
    
    # --- 1. PREPARACIÓN DE DATOS ---
    df_plot = df_sim.reset_index()
    df_plot['ROP'] = metrics['reorder_point']
    df_plot['SafetyStock'] = metrics['safety_stock']
    
    df_lines = df_plot.melt(
        id_vars=['Fecha'],
        value_vars=['NivelInventario', 'ROP', 'SafetyStock'],
        var_name='Leyenda', 
        value_name='Valor'
    )
    
    df_llegadas = pd.DataFrame(list(llegadas_map.items()), columns=['Fecha', 'CantidadLlegada'])
    df_llegadas = pd.merge(df_llegadas, df_plot, on='Fecha', how='left')
    df_llegadas['Leyenda'] = 'Llegada de OC' 

    df_zero_line = pd.DataFrame({'y': [0]})

    # --- 2. DEFINICIÓN DE CAPAS DEL GRÁFICO ---
    domain = ['NivelInventario', 'ROP', 'SafetyStock', 'Llegada de OC']
    range_colors = ['#1f77b4', '#ff7f0e', '#9467bd', '#2ca02c'] 

    # Capa 1: Línea de Inventario
    inventory_line = alt.Chart(
        df_lines.loc[df_lines['Leyenda'] == 'NivelInventario']
    ).mark_line(
        interpolate='step-after', point=True
    ).encode(
        x=alt.X('Fecha:T', title='Fecha', axis=alt.Axis(format="%Y-%m-%d")),
        y=alt.Y('Valor:Q', title='Unidades en Stock'),
        color=alt.Color('Leyenda:N', scale=alt.Scale(domain=domain, range=range_colors), title='Leyenda'),
        tooltip=[
            alt.Tooltip('Fecha:T', format="%Y-%m-%d"), 
            alt.Tooltip('Leyenda:N', title='Tipo'),
            alt.Tooltip('Valor:Q', title='Stock Proyectado', format=',.0f')
        ]
    )
    
    # Capa 2: Líneas de Referencia (ROP y SS)
    reference_lines = alt.Chart(
        df_lines.loc[df_lines['Leyenda'] != 'NivelInventario']
    ).mark_line(
        strokeDash=[5, 5]
    ).encode(
        x=alt.X('Fecha:T'), 
        y=alt.Y('Valor:Q'),
        color=alt.Color('Leyenda:N', scale=alt.Scale(domain=domain, range=range_colors)),
        tooltip=[
            alt.Tooltip('Leyenda:N', title='Tipo'),
            alt.Tooltip('Valor:Q', title='Nivel', format=',.0f')
        ]
    )
    
    # Capa 3: Puntos de Llegada (OCs)
    arrival_points = alt.Chart(df_llegadas).mark_circle(size=100, opacity=0.9).encode(
        x=alt.X('Fecha:T'),
        y=alt.Y('NivelInventario:Q'),
        color=alt.Color('Leyenda:N', scale=alt.Scale(domain=domain, range=range_colors)),
        tooltip=[
            alt.Tooltip('Fecha:T', title='Llegada de OC', format="%Y-%m-%d"),
            alt.Tooltip('CantidadLlegada:Q', title='Cantidad Recibida', format=',.0f')
        ]
    )

    # Capa 4: Línea de Cero
    zero_line = alt.Chart(df_zero_line).mark_rule(
        color='red', strokeDash=[2, 2]
    ).encode(
        y='y',
        tooltip=alt.value("Stock Cero") 
    )

    # --- 3. COMBINAR Y RENDERIZAR ---
    
    final_chart = (inventory_line + reference_lines + arrival_points + zero_line).properties(
        title=f'Proyección de Inventario para {sku_name} ({simulation_days} días)'
    ).interactive() 
    
    return final_chart


def prepare_end_of_month_table(df_sim):
    """
    Toma el DataFrame de simulación diaria y lo resume a fin de mes (Req. 3).
    (El contenido de esta función no cambia)
    """
    df_fin_de_mes = df_sim['NivelInventario'].resample('ME').last().reset_index()
    
    df_fin_de_mes['Mes'] = df_fin_de_mes['Fecha'].dt.strftime('%Y-%m (%B)')
    df_fin_de_mes['Stock al Cierre'] = df_fin_de_mes['NivelInventario'].apply(lambda x: f"{x:,.0f}")
    
    return df_fin_de_mes[['Mes', 'Stock al Cierre']]

# --- FUNCIÓN MODIFICADA (REFACTORIZADA) ---
def display_order_recommendation(metrics, llegadas_map, df_sim, lead_time_days):
    """
    Muestra la recomendación de pedido (UI).
    La lógica de cálculo ahora está en 'analysis.py' y usa la proyección.
    """
    
    # --- 1. Llamar a la función de análisis ---
    reco = analysis.calculate_order_recommendation(
        metrics, llegadas_map, df_sim, lead_time_days
    )

    # --- 2. Mostrar en la UI ---
    st.subheader("Recomendación de Abastecimiento 💡")
    
    # Manejar caso de error (simulación muy corta)
    if reco["status"] == "error":
        st.error(f"**Error de Proyección:** {reco['error_message']}")
        st.info("Aumente los 'Días a Simular' para que sean mayores o iguales al Lead Time.")
        return

    col1, col2, col3 = st.columns(3)
    
    col1.metric(
        f"Stock Proyectado (en {reco['lead_time_days']} días)", 
        f"{reco['projected_stock_at_lt']:,.0f}",
        help=f"Nivel de stock simulado para el {reco['forecast_date'].strftime('%Y-%m-%d')}."
    )
    
    col2.metric(
        "Safety Stock (ss)", 
        f"{reco['ss']:,.0f}", 
        help="Si el stock proyectado cae bajo este número, se debe pedir."
    )
    
    col3.metric(
        "Recomendación de Pedido",
        f"{reco['suggested_order_qty']:,.0f} uds.",
        delta=f"{reco['suggested_order_qty']:,.0f} uds." if reco['status'] == 'success' else None,
        delta_color="inverse"
    )


    # Mostrar el veredicto final
    if reco['status'] == 'success':
        st.success(f"**Recomendación:** Pedir **{reco['suggested_order_qty']:,.0f} unidades**.\n\n"
                   f"El stock proyectado ({reco['projected_stock_at_lt']:,.0f}) está por debajo del ss ({reco['ss']:,.0f}).")
    
    else: # 'info'
        st.info(f"**No se necesita pedido.** El stock proyectado ({reco['projected_stock_at_lt']:,.0f}) se mantiene por encima del Punto de Reorden ({reco['ss']:,.0f}).")


def display_arrival_details(df_llegadas_detalle):
    """
    Muestra una tabla con el detalle de las próximas llegadas (OCs).
    """
    st.subheader("Detalle de Próximas Llegadas (OC)")
    
    columna_oc = 'Número de documento' 
    
    if columna_oc not in df_llegadas_detalle.columns:
        st.error(f"Error: La columna '{columna_oc}' no se encontró en el archivo OPOR.")
        st.info("No se puede mostrar el detalle de OCs.")
        return

    if df_llegadas_detalle.empty:
        st.info("No hay órdenes de compra programadas para este SKU.")
    else:
        # Seleccionamos, renombramos y ordenamos las columnas para mostrar
        df_display = df_llegadas_detalle[[
            'Fecha de entrega de la línea', 
            columna_oc, 
            'Cantidad',
            'Comentarios'
        ]].copy()
        
        df_display.rename(columns={
            'Fecha de entrega de la línea': 'Fecha Llegada',
            columna_oc: 'N° Orden Compra',
            'Cantidad': 'Cantidad',
            'Comentarios': 'Comentarios'
        }, inplace=True)
        
        df_display = df_display.sort_values(by='Fecha Llegada')
        
        # Formatear para mejor visualización
        df_display['Fecha Llegada'] = df_display['Fecha Llegada'].dt.strftime('%Y-%m-%d')
        df_display['Cantidad'] = df_display['Cantidad'].apply(lambda x: f"{x:,.0f}")
        
        # Mostramos la tabla
        st.dataframe(df_display, use_container_width=True, hide_index=True)