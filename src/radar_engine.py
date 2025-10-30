# --- ARCHIVO: src/radar_engine.py ---
# (NUEVO ARCHIVO para la lógica de análisis masivo)

import pandas as pd
import numpy as np
import streamlit as st
from src import config # Importa la configuración

def _calculate_sku_kpis(
    sku, 
    df_stock_sku, 
    df_consumo_sku, 
    df_oc_sku, 
    mapa_nombres,
    lead_time_days, 
    service_level_z
):
    """
    Calcula los KPIs clave para un solo SKU.
    Es una versión "lite" del motor de simulación.
    """
    try:
        today = pd.Timestamp.now().floor('D')
        
        # --- 1. Stock Inicial ---
        initial_stock = pd.to_numeric(df_stock_sku['DisponibleParaPrometer'], errors='coerce').sum()

        # --- 2. Métricas de Demanda ---
        daily_demand_mean = 0.0
        daily_demand_std = 0.0
        monthly_demand_mean = 0.0

        if not df_consumo_sku.empty:
            start_of_current_month = today.replace(day=1)
            
            df_consumo_indexed = df_consumo_sku.set_index('FechaSolicitud')
            consumo_mensual = df_consumo_indexed.resample('MS')['CantidadSolicitada'].sum()
            
            consumo_historico = consumo_mensual[consumo_mensual.index < start_of_current_month]
            
            if len(consumo_historico) > 1:
                monthly_demand_mean = consumo_historico.mean()
                monthly_demand_std = consumo_historico.std()
                daily_demand_mean = monthly_demand_mean / config.AVERAGE_DAYS_PER_MONTH
                daily_demand_std = monthly_demand_std / np.sqrt(config.AVERAGE_DAYS_PER_MONTH)
            elif len(consumo_historico) == 1:
                monthly_demand_mean = consumo_historico.mean()
                daily_demand_mean = monthly_demand_mean / config.AVERAGE_DAYS_PER_MONTH

        # --- 3. Días de Cobertura (DOS) ---
        if daily_demand_mean > 0:
            days_of_supply = initial_stock / daily_demand_mean
        else:
            days_of_supply = np.inf # O 0, según prefieras
            
        # --- 4. SS y ROP ---
        demand_during_lead_time = daily_demand_mean * lead_time_days
        std_dev_during_lead_time = daily_demand_std * np.sqrt(lead_time_days)
        safety_stock = service_level_z * std_dev_during_lead_time
        reorder_point = demand_during_lead_time + safety_stock

        # --- 5. Llegadas (OCs) ---
        df_llegadas = df_oc_sku[
            (df_oc_sku['Cantidad'] > 0) & 
            (df_oc_sku['Fecha de entrega de la línea'] >= today)
        ]
        
        llegadas_map = df_llegadas.groupby('Fecha de entrega de la línea')['Cantidad'].sum()
        
        next_arrival_date = df_llegadas['Fecha de entrega de la línea'].min()
        if pd.isna(next_arrival_date):
            next_arrival_date = None
        else:
            next_arrival_date = next_arrival_date.strftime('%Y-%m-%d')

        # --- 6. Lógica de Recomendación (Proyectada) ---
        forecast_date = today + pd.DateOffset(days=lead_time_days)
        
        # Suma llegadas DENTRO del Lead Time
        llegadas_en_lt = llegadas_map[llegadas_map.index <= forecast_date].sum()
        
        # Proyección simple: Stock + Llegadas - Consumo
        projected_stock_at_lt = initial_stock + llegadas_en_lt - (daily_demand_mean * lead_time_days)

        suggested_order_qty = 0.0
        if projected_stock_at_lt < reorder_point:
            suggested_order_qty = reorder_point - projected_stock_at_lt
            suggested_order_qty = max(0.0, suggested_order_qty)

        # --- 7. Alertas ---
        alert_stock_actual = initial_stock < safety_stock
        alert_proyectada = projected_stock_at_lt < reorder_point

        return {
            "SKU": sku,
            "Nombre": mapa_nombres.get(sku, "N/A"),
            "Stock Actual": initial_stock,
            "DOS (Días)": days_of_supply,
            "Alerta Stock (vs SS)": "🔴" if alert_stock_actual else "🟢",
            "Stock Proy. (en LT)": projected_stock_at_lt,
            "ROP": reorder_point,
            "Alerta Proy. (vs ROP)": "🔴" if alert_proyectada else "🟢",
            "Pedido Sugerido": suggested_order_qty,
            "Próx. Llegada": next_arrival_date,
            "Demanda Prom. Diaria": daily_demand_mean
        }
    
    except Exception as e:
        print(f"Error procesando SKU {sku}: {e}")
        return None


@st.cache_data(ttl=3600) # Cachea el reporte por 1 hora
def run_full_radar_analysis(
    _df_stock, 
    _df_consumo, 
    _df_oc,
    bodega_stock_sel,
    bodega_consumo_sel,
    lead_time_days,
    service_level_z
):
    """
    Ejecuta el cálculo de KPIs para todos los SKUs relevantes.
    """
    
    # --- 1. Preparar Datos (Filtros y Mapas) ---
    df_stock = _df_stock[_df_stock['CodigoBodega'] == bodega_stock_sel].copy()
    df_consumo = _df_consumo[_df_consumo['BodegaDestino_Requerida'] == bodega_consumo_sel].copy()
    
    # Pre-limpieza de OCs
    df_oc = _df_oc.copy()
    df_oc['Fecha de entrega de la línea'] = pd.to_datetime(df_oc['Fecha de entrega de la línea'], format='%Y-m-%d', errors='coerce')
    df_oc['Cantidad'] = pd.to_numeric(df_oc['Cantidad'], errors='coerce')

    # Mapa de nombres
    mapa_nombres = _df_stock.drop_duplicates(subset=['CodigoArticulo']).set_index('CodigoArticulo')['NombreArticulo'].to_dict()

    # Lista de SKUs a procesar (todos los que tienen stock o consumo)
    skus_stock = df_stock['CodigoArticulo'].unique()
    skus_consumo = df_consumo['CodigoArticulo'].unique()
    all_skus = sorted(list(set(skus_stock) | set(skus_consumo)))
    
    results_list = []
    
    # Barra de progreso
    progress_bar = st.progress(0, text="Iniciando análisis masivo...")

    # --- 2. Iterar por cada SKU ---
    for i, sku in enumerate(all_skus):
        
        # Filtrar dataframes para este SKU (eficiente)
        df_stock_sku = df_stock[df_stock['CodigoArticulo'] == sku]
        df_consumo_sku = df_consumo[df_consumo['CodigoArticulo'] == sku]
        df_oc_sku = df_oc[df_oc['Número de artículo'] == sku]
        
        # Calcular KPIs
        kpis = _calculate_sku_kpis(
            sku, 
            df_stock_sku, 
            df_consumo_sku, 
            df_oc_sku, 
            mapa_nombres,
            lead_time_days, 
            service_level_z
        )
        
        if kpis:
            results_list.append(kpis)
            
        # Actualizar barra de progreso
        progress_bar.progress((i + 1) / len(all_skus), text=f"Procesando SKU: {sku} ({i+1}/{len(all_skus)})")

    progress_bar.empty() # Limpiar barra
    
    if not results_list:
        return pd.DataFrame() # Retorna DF vacío si no hay resultados

    # --- 3. Retornar DataFrame final ---
    df_results = pd.DataFrame(results_list)
    
    # Organizar columnas
    column_order = [
        "SKU", "Nombre", "Stock Actual", "DOS (Días)", "Alerta Stock (vs SS)",
        "Stock Proy. (en LT)", "ROP", "Alerta Proy. (vs ROP)", "Pedido Sugerido",
        "Próx. Llegada", "Demanda Prom. Diaria"
    ]
    df_results = df_results[column_order]
    
    return df_results