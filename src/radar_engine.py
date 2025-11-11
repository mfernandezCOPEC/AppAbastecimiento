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
        Calcula los KPIs clave de inventario para un solo SKU.

        Esta función toma los datos filtrados de stock, consumo (demanda) y 
        órdenes de compra (OC) para un SKU específico, y calcula métricas
        esenciales como el Punto de Reorden (ROP), Stock de Seguridad (SS),
        Días de Cobertura (DOS) y una sugerencia de pedido.

        Parámetros:
        -----------
        sku : str
            El identificador (código) del SKU que se está procesando.
        df_stock_sku : pd.DataFrame
            DataFrame de Pandas filtrado que contiene únicamente la información
            de stock para este SKU.
        df_consumo_sku : pd.DataFrame
            DataFrame de Pandas filtrado con el historial de consumo (demanda)
            para este SKU. Debe contener 'FechaSolicitud' y 'CantidadSolicitada'.
        df_oc_sku : pd.DataFrame
            DataFrame de Pandas filtrado con las órdenes de compra (OC) abiertas
            para este SKU. Debe contener 'Fecha de entrega de la línea' y 'Cantidad'.
        mapa_nombres : dict
            Un diccionario que mapea códigos de SKU a nombres descriptivos 
            (ej. {'SKU-123': 'Tornillo 1/4'}).
        lead_time_days : float or int
            El tiempo de entrega del proveedor en días.
        service_level_z : float
            El factor de servicio (puntuación Z) correspondiente al nivel de 
            servicio deseado (ej. 1.645 para un 95% de nivel de servicio).

        Retorna:
        --------
        dict
            Un diccionario que contiene todos los KPIs calculados para el SKU.
            Las claves incluyen: "SKU", "Nombre", "Stock Actual", "DOS (Días)",
            "ROP", "Stock Proy. (en LT)", "Pedido Sugerido", "Alerta Stock (vs SS)",
            "Alerta Proy. (vs ROP)", "Próx. Llegada", "Demanda Prom. Diaria".
        None
            Retorna None si se produce una excepción durante el procesamiento del SKU.
        """
    try:

        # Obtiene la fecha y hora actual y la trunca al inicio del día (00:00:00).
        today = pd.Timestamp.now().floor('D')
        
        # --- 1. Stock Inicial ---
        # Suma todo el stock "DisponibleParaPrometer" para este SKU. 
        # 'coerce' convierte errores de conversión (ej. texto) en NaN, que sum() ignora.
        initial_stock = pd.to_numeric(df_stock_sku['DisponibleParaPrometer'], errors='coerce').sum()

        # --- 2. Métricas de Demanda ---
        # Inicializa las métricas de demanda. Serán 0 si no hay historial de consumo.
        daily_demand_mean = 0.0
        daily_demand_std = 0.0
        monthly_demand_mean = 0.0

        # Procesa solo si hay datos históricos de consumo.
        if not df_consumo_sku.empty:
            # Define el primer día del mes actual para poder filtrar el historial.
            start_of_current_month = today.replace(day=1)
            
            # Establece la fecha como índice para poder re-muestrear (resample) por tiempo.
            df_consumo_indexed = df_consumo_sku.set_index('FechaSolicitud')
            # Agrupa el consumo por mes ('MS' = Month Start) y suma las cantidades.
            consumo_mensual = df_consumo_indexed.resample('MS')['CantidadSolicitada'].sum()
            
            # Filtra para usar solo meses completos pasados (excluye el mes actual en curso).
            consumo_historico = consumo_mensual[consumo_mensual.index < start_of_current_month]
            
            # Se necesita más de 1 mes de historial para calcular la desviación estándar.
            if len(consumo_historico) > 1:
                # Calcula la media y desviación estándar de la demanda mensual.
                monthly_demand_mean = consumo_historico.mean()
                monthly_demand_std = consumo_historico.std()
                
                # Convierte la demanda mensual a diaria.
                daily_demand_mean = monthly_demand_mean / config.AVERAGE_DAYS_PER_MONTH
                # IMPORTANTE: La desviación estándar se escala con la raíz cuadrada del tiempo.
                daily_demand_std = monthly_demand_std / np.sqrt(config.AVERAGE_DAYS_PER_MONTH)
            
            # Si solo hay 1 mes de historial, solo podemos calcular la media (std es 0).
            elif len(consumo_historico) == 1:
                monthly_demand_mean = consumo_historico.mean()
                daily_demand_mean = monthly_demand_mean / config.AVERAGE_DAYS_PER_MONTH

        # --- 3. Días de Cobertura (DOS - Days of Supply) ---
        # Evita la división por cero si no hay demanda registrada.
        if daily_demand_mean > 0:
            # DOS = Stock Actual / Demanda Diaria Promedio.
            days_of_supply = initial_stock / daily_demand_mean
        else:
            # Si la demanda es 0, la cobertura es "infinita".
            days_of_supply = np.inf # O 0, según se prefiera definir.
            
        # --- 4. Stock de Seguridad (SS) y Punto de Reorden (ROP) ---
        # Demanda promedio esperada *durante* el tiempo de entrega (Lead Time).
        demand_during_lead_time = daily_demand_mean * lead_time_days
        # Desviación estándar de la demanda *durante* el Lead Time (escalada por raíz de LT).
        std_dev_during_lead_time = daily_demand_std * np.sqrt(lead_time_days)
        
        # Fórmula de Stock de Seguridad (SS) = Z * (Desviación Estándar durante LT).
        safety_stock = service_level_z * std_dev_during_lead_time
        # Fórmula de Punto de Reorden (ROP) = (Demanda durante LT) + Stock de Seguridad.
        reorder_point = demand_during_lead_time + safety_stock

        # --- 5. Llegadas (Órdenes de Compra Pendientes) ---
        # Filtra las Órdenes de Compra (OC) para encontrar llegadas futuras y válidas.
        df_llegadas = df_oc_sku[
            (df_oc_sku['Cantidad'] > 0) & 
            (df_oc_sku['Fecha de entrega de la línea'] >= today)
        ]
        
        # Agrupa las llegadas por fecha y suma las cantidades (por si hay varias OC el mismo día).
        # Esto crea una Serie de Pandas (Fecha -> Cantidad).
        llegadas_map = df_llegadas.groupby('Fecha de entrega de la línea')['Cantidad'].sum()
        
        # Encuentra la fecha de la próxima llegada más cercana.
        next_arrival_date = df_llegadas['Fecha de entrega de la línea'].min()
        
        # Maneja el caso de que no haya llegadas (min() devuelve NaT - Not a Time).
        if pd.isna(next_arrival_date):
            next_arrival_date = None
        else:
            # Formatea la fecha a string para el reporte.
            next_arrival_date = next_arrival_date.strftime('%Y-%m-%d')

        # --- 6. Lógica de Recomendación (Proyección) ---
        # Calcula la fecha en que llegaría un pedido hecho hoy (Hoy + Lead Time).
        forecast_date = today + pd.DateOffset(days=lead_time_days)
        
        # Suma todas las llegadas programadas *dentro* de la ventana de Lead Time (entre hoy y la 'forecast_date').
        llegadas_en_lt = llegadas_map[llegadas_map.index <= forecast_date].sum()
        
        # Proyecta el stock al final del Lead Time:
        # Stock Proyectado = Stock Actual + Llegadas en LT - Demanda en LT
        projected_stock_at_lt = initial_stock + llegadas_en_lt - (daily_demand_mean * lead_time_days)

        # Inicializa la cantidad sugerida de pedido.
        suggested_order_qty = 0.0
        # Comprueba si el stock proyectado al final del LT estará por debajo del ROP.
        if projected_stock_at_lt < reorder_point:
            # Si es así, sugiere pedir la diferencia para volver a cubrir el ROP.
            # (Esta es una política de "pedir hasta ROP"; otras políticas podrían pedir hasta un "Máximo").
            suggested_order_qty = reorder_point - projected_stock_at_lt
            # Asegura que la cantidad sugerida no sea negativa (por si acaso).
            suggested_order_qty = max(0.0, suggested_order_qty)

        # --- 7. Alertas ---
        # Alerta si el stock *actual* ya está por debajo del Stock de Seguridad.
        alert_stock_actual = initial_stock < safety_stock
        # Alerta si el stock *proyectado* caerá por debajo del ROP (¡necesita pedir!).
        # Esta es la misma condición que se usa para sugerir el pedido.
        alert_proyectada = projected_stock_at_lt < reorder_point

        # Retorna un diccionario con todos los KPIs calculados para este SKU.
        return {
            "SKU": sku,
            # Usa .get() para obtener el nombre, o "N/A" si el SKU no está en el mapa.
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
    
    # Bloque de captura de errores para evitar que un SKU fallido detenga todo el proceso.
    except Exception as e:
        # Imprime el error en la consola para depuración.
        print(f"Error procesando SKU {sku}: {e}")
        # Retorna None para que este SKU pueda ser filtrado o ignorado más adelante.
        return None


@st.cache_data(ttl=3600)
def run_full_radar_analysis(
    _df_stock_full,     # <-- Renombrado para claridad
    _df_consumo_full,   # <-- Renombrado para claridad
    _df_oc_full,        # <-- Renombrado para claridad
    familia_sel,        # <-- El NUEVO argumento
    bodega_stock_sel,
    bodega_consumo_sel,
    lead_time_days,
    service_level_z
):
    # --- 1. (NUEVO) Filtrado por Familia ---
    if familia_sel != "Todas":
        try:
            # Filtra stock por familia
            _df_stock = _df_stock_full[_df_stock_full['Familia'] == familia_sel].copy()
            
            if _df_stock.empty:
                st.warning(f"No se encontraron SKUs de stock para la familia '{familia_sel}'.")
                return pd.DataFrame() # Retorna DF vacío

            # Obtiene SKUs de esa familia
            # (Asegúrate que la columna de SKU se llame 'CodigoArticulo' en Stock)
            skus_de_familia = _df_stock['CodigoArticulo'].unique() 
            
            # Filtra consumo y OC por esos SKUs
            _df_consumo = _df_consumo_full[_df_consumo_full['CodigoArticulo'].isin(skus_de_familia)].copy()
            _df_oc = _df_oc_full[_df_oc_full['Número de artículo'].isin(skus_de_familia)].copy()
        
        except KeyError as e:
            st.error(f"Error: No se encontró la columna 'Familia' o 'SKU' en los DataFrames. Detalle: {e}")
            return pd.DataFrame()
    else:
        # Si es "Todas", usa los dataframes completos
        _df_stock = _df_stock_full.copy()
        _df_consumo = _df_consumo_full.copy()
        _df_oc = _df_oc_full.copy()


    # --- 2. Preparar Datos (Filtros de Bodega) ---
    # (Este código ya lo tenías, se queda igual)
    df_stock = _df_stock[_df_stock['CodigoBodega'] == bodega_stock_sel].copy()
    df_consumo = _df_consumo[_df_consumo['BodegaDestino_Requerida'] == bodega_consumo_sel].copy()
    
    # Pre-limpieza de OCs
    df_oc = _df_oc.copy() # _df_oc ya está filtrado por familia
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