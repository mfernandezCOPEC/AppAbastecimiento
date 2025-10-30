# --- ARCHIVO: src/analysis.py ---
# (NUEVO ARCHIVO para la lógica de negocio separada)
import pandas as pd

def calculate_order_recommendation(metrics, llegadas_map, df_sim, lead_time_days):
    """
    Calcula la lógica de recomendación de pedido (cuánto pedir) basado
    en la proyección futura del inventario.
    
    Lógica:
    1. Encuentra el stock proyectado en T + lead_time_days.
    2. Compara ese stock con el ROP.
    3. Si el stock proyectado < ROP, recomienda pedir (ROP - stock_proyectado).
    
    Retorna un diccionario con los cálculos y la decisión.
    """
    
    # --- 1. Obtener Métricas Clave ---
    ss = metrics['safety_stock']
    
    # --- 2. Calcular Proyección Futura ---
    
    # Aseguramos que el índice sea Datetime
    if not isinstance(df_sim.index, pd.DatetimeIndex):
         df_sim.index = pd.to_datetime(df_sim.index)
         
    today = df_sim.index.min()
    forecast_date = today + pd.DateOffset(days=lead_time_days)
    
    # --- 3. Validar si la simulación cubre la fecha de pronóstico ---
    if forecast_date > df_sim.index.max():
        msg = f"La simulación ({len(df_sim)} días) es más corta que el Lead Time ({lead_time_days} días). No se puede proyectar la recomendación."
        return { "status": "error", "error_message": msg }

    # --- 4. Obtener Stock Proyectado y Generar Recomendación ---
    
    # Usamos .asof para encontrar el valor más cercano si la fecha exacta no existe
    projected_stock = df_sim.asof(forecast_date)['NivelInventario']
    
    is_below_rop = projected_stock < ss
    suggested_order_qty = 0.0
    status = "info"

    if is_below_rop:
        suggested_order_qty = ss - projected_stock
        suggested_order_qty = max(0.0, suggested_order_qty) 
        
        if suggested_order_qty > 0:
            status = "success"
    else:
        status = "info"
        
    # --- 5. Retornar los resultados ---
    return {
        "projected_stock_at_lt": projected_stock,
        "ss": ss,
        "lead_time_days": lead_time_days,
        "forecast_date": forecast_date,
        "suggested_order_qty": suggested_order_qty,
        "is_below_rop": is_below_rop,
        "status": status,
        "error_message": None
    }