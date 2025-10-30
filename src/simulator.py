# --- ARCHIVO: src/simulator.py ---
# (Modificado para importar 'config' desde 'src')

import pandas as pd
import numpy as np
import config # Importa config.py desde la misma carpeta 'src'

def run_inventory_simulation(
    sku_to_simulate: str,
    warehouse_code: str,
    consumption_warehouse: str,
    df_stock_raw: pd.DataFrame,
    df_consumo_raw: pd.DataFrame,
    df_oc_raw: pd.DataFrame,
    simulation_days: int,
    lead_time_days: int, 
    service_level_z: float
):
    """
    Ejecuta la lógica de simulación de inventario día a día.
    (El contenido de esta función no cambia)
    """
    
    # Define la fecha de 'hoy' (inicio de la simulación)
    today = pd.Timestamp.now().floor('D')
    
    # --- B. CÁLCULO DE STOCK INICIAL (I_0) ---
    
    # Filtra el DataFrame de stock para el SKU y bodega específicos
    df_stock_filtered = df_stock_raw[
        (df_stock_raw['CodigoArticulo'] == sku_to_simulate) &
        (df_stock_raw['CodigoBodega'] == warehouse_code)
    ].copy()
    
    # Asegura que el stock sea numérico y calcula el total
    df_stock_filtered['DisponibleParaPrometer'] = pd.to_numeric(df_stock_filtered['DisponibleParaPrometer'], errors='coerce')
    initial_stock = df_stock_filtered['DisponibleParaPrometer'].sum()

    # --- C. CÁLCULO DE CONSUMO ---
    
    # Filtra el DataFrame de consumo para el SKU y bodega de consumo específicos
    df_consumo_filtered = df_consumo_raw[
        (df_consumo_raw['CodigoArticulo'] == sku_to_simulate) &
        (df_consumo_raw['BodegaDestino_Requerida'] == consumption_warehouse)
    ].copy()
    
    # Inicializa métricas de demanda (buena práctica para asegurar que existan)
    daily_demand_mean = 0.0
    daily_demand_std = 0.0
    monthly_demand_mean = 0.0
    demand_M_0, demand_M_1, demand_M_2, demand_M_3 = 0.0, 0.0, 0.0, 0.0

    # Define las fechas de inicio para los meses a analizar (M, M-1, M-2, M-3)
    start_of_current_month = today.replace(day=1)
    start_of_M_minus_1 = start_of_current_month - pd.DateOffset(months=1)
    start_of_M_minus_2 = start_of_current_month - pd.DateOffset(months=2)
    start_of_M_minus_3 = start_of_current_month - pd.DateOffset(months=3)
    
    # Solo procesa si hay historial de consumo
    if not df_consumo_filtered.empty:
        
        # 1. Preparación de datos de consumo
        
        # Asegura que la cantidad sea numérica (ignora errores de formato)
        df_consumo_filtered['CantidadSolicitada'] = pd.to_numeric(df_consumo_filtered['CantidadSolicitada'], errors='coerce')
        
        # Establece la fecha como índice para poder re-muestrear (resample)
        df_consumo_indexed = df_consumo_filtered.set_index('FechaSolicitud')
        
        # Agrupa el consumo por mes ('MS' = Month Start) y suma las cantidades
        consumo_mensual = df_consumo_indexed.resample('MS')['CantidadSolicitada'].sum()
        
        # 2. Cálculo para SS y ROP (promedios históricos)
        
        # --- MODIFICACIÓN CLAVE ---
        # Excluimos el mes actual de los cálculos estadísticos (media, std)
        consumo_historico_completo = consumo_mensual[consumo_mensual.index < start_of_current_month]
        # --- FIN DE LA MODIFICACIÓN ---

        if len(consumo_historico_completo) > 1:
            # Calcula la media y std usando SOLO los meses históricos completos
            monthly_demand_mean = consumo_historico_completo.mean()
            monthly_demand_std = consumo_historico_completo.std()
            
            # Convierte las métricas mensuales a diarias
            daily_demand_mean = monthly_demand_mean / config.AVERAGE_DAYS_PER_MONTH
            daily_demand_std = monthly_demand_std / np.sqrt(config.AVERAGE_DAYS_PER_MONTH) 
            
        elif len(consumo_historico_completo) == 1:
            monthly_demand_mean = consumo_historico_completo.mean()
            daily_demand_mean = monthly_demand_mean / config.AVERAGE_DAYS_PER_MONTH
            # daily_demand_std se mantiene en 0.0 (inicializado)

        # 3. Cálculo para Req. 1 (meses individuales)
        
        # Aquí SÍ usamos 'consumo_mensual' (el original)
        demand_M_0 = consumo_mensual.get(start_of_current_month, 0)
        demand_M_1 = consumo_mensual.get(start_of_M_minus_1, 0)
        demand_M_2 = consumo_mensual.get(start_of_M_minus_2, 0)
        demand_M_3 = consumo_mensual.get(start_of_M_minus_3, 0)

    # --- D. CÁLCULO DE SS y ROP ---
    
    demand_during_lead_time = daily_demand_mean * lead_time_days
    std_dev_during_lead_time = daily_demand_std * np.sqrt(lead_time_days)
    safety_stock = service_level_z * std_dev_during_lead_time
    reorder_point = demand_during_lead_time + safety_stock

    # --- E. CÁLCULO DE LLEGADAS (OC) ---
    
    df_oc_clean = df_oc_raw.copy()
    try:
        df_oc_clean['Fecha de entrega de la línea'] = pd.to_datetime(df_oc_clean['Fecha de entrega de la línea'], format='%Y-m-%d', errors='coerce')
        df_oc_clean['Cantidad'] = pd.to_numeric(df_oc_clean['Cantidad'], errors='coerce')
    except Exception as e:
        print(f"Error limpiando df_oc: {e}.") 

    # Filtra OC relevantes
    df_llegadas_detalle = df_oc_clean[
        (df_oc_clean['Número de artículo'] == sku_to_simulate) &
        (df_oc_clean['Cantidad'] > 0) & 
        (df_oc_clean['Fecha de entrega de la línea'] >= today)
    ]
    
    llegadas_por_fecha = df_llegadas_detalle.groupby('Fecha de entrega de la línea')['Cantidad'].sum() 
    llegadas_map = llegadas_por_fecha.to_dict()
    
    # --- F. EJECUTAR SIMULACIÓN DÍA A DÍA ---
    
    inventory_level = initial_stock
    history_list = [] 
    date_list = []    

    for day in range(simulation_days):
        current_date = today + pd.Timedelta(days=day)
        
        history_list.append(inventory_level)
        date_list.append(current_date)
        
        inventory_level += llegadas_map.get(current_date, 0)
        
        if daily_demand_std > 0:
            daily_consumption = np.random.normal(loc=daily_demand_mean, scale=0) #, scale=daily_demand_std)
        else:
            daily_consumption = daily_demand_mean
            
        daily_consumption = max(0, daily_consumption)
        inventory_level -= daily_consumption
        
    df_sim = pd.DataFrame({'NivelInventario': history_list}, index=pd.Index(date_list, name='Fecha'))

    # --- G. EMPAQUETAR RESULTADOS ---
    
    metrics = {
        'initial_stock': initial_stock,
        'monthly_demand_mean': monthly_demand_mean,
        'llegadas_count': len(llegadas_map),
        'safety_stock': safety_stock,
        'reorder_point': reorder_point,
        'demand_M_0': (start_of_current_month, demand_M_0),
        'demand_M_1': (start_of_M_minus_1, demand_M_1),
        'demand_M_2': (start_of_M_minus_2, demand_M_2),
        'demand_M_3': (start_of_M_minus_3, demand_M_3),
    }

    return df_sim, metrics, llegadas_map, df_llegadas_detalle