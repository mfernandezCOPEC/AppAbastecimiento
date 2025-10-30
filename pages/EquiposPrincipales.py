# --- ARCHIVO: pages/Equipos_Principales.py ---
# (NUEVA PÁGINA)

import streamlit as st
import pandas as pd
import altair as alt
import sys
from pathlib import Path

# --- 1. Configuración del Path ---
# (Necesario para importar módulos desde 'src')
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.append(src_path)
    
# (No es necesario importar data_loader, Menu.py ya cargó los datos)

# --- 2. Configuración de la Página ---
st.set_page_config(
    layout="wide",
    page_title="Análisis Equipos Principales",
    page_icon="💡" # Ícono de ejemplo
)

# --- 3. Carga y Verificación de Datos ---
# Verificamos que los datos estén en la sesión
if 'data_loaded' not in st.session_state or not st.session_state.data_loaded:
    st.error("No se pudieron cargar los datos. Por favor, reinicie desde la página 'Menú'.")
    st.stop()

# Accedemos a los datos desde la sesión
try:
    df_stock = st.session_state.df_stock.copy()
    df_consumo = st.session_state.df_consumo.copy()
    
    # --- Verificación de Columnas Necesarias ---
    # Asumimos que 'CostoUnitario' existe para calcular el valor.
    # Si tu columna de costo se llama diferente, ajústala aquí.
    columnas_stock = ['Familia', 'CodigoArticulo', 'NombreArticulo', 'DisponibleParaPrometer', 'CostoUnitario']
    columnas_consumo = ['CodigoArticulo', 'CantidadSolicitada']
    
    missing_stock_cols = [col for col in columnas_stock if col not in df_stock.columns]
    missing_consumo_cols = [col for col in columnas_consumo if col not in df_consumo.columns]
    
    if missing_stock_cols:
        st.error(f"Error: El archivo 'Stock.xlsx' no contiene las columnas necesarias. Faltan: {missing_stock_cols}")
        st.stop()
    if missing_consumo_cols:
        st.error(f"Error: El archivo 'ST_OWTR.xlsx' no contiene las columnas necesarias. Faltan: {missing_consumo_cols}")
        st.stop()
        
except AttributeError:
    st.error("Error al acceder a 'df_stock' o 'df_consumo' en st.session_state. Vuelva al 'Menú' principal.")
    st.stop()
except Exception as e:
    st.error(f"Ocurrió un error inesperado al preparar los datos: {e}")
    st.stop()


# --- 4. Título y Encabezado ---
try:
    st.image("assets/COPEC-FLUX.svg", width=150)
except Exception as e:
    st.warning(f"No se pudo cargar el logo: {e}")

st.title("💡 Análisis de Equipos Principales")
st.markdown("Dashboard con KPIs para la familia 'EQUIPOS PRINCIPALES'.")

# --- 5. Lógica de Filtro y Preparación ---

# Asegurar tipos numéricos antes de filtrar y calcular
df_stock['DisponibleParaPrometer'] = pd.to_numeric(df_stock['DisponibleParaPrometer'], errors='coerce').fillna(0)
df_stock['CostoUnitario'] = pd.to_numeric(df_stock['CostoUnitario'], errors='coerce').fillna(0)
df_consumo['CantidadSolicitada'] = pd.to_numeric(df_consumo['CantidadSolicitada'], errors='coerce').fillna(0)

# --- Filtro Principal (Core Logic) ---
df_equipos_stock = df_stock[
    (df_stock['Familia'].str.strip().str.upper() == 'EQUIPOS PRINCIPALES')
].copy()

if df_equipos_stock.empty:
    st.warning("No se encontró ningún artículo en la familia 'EQUIPOS PRINCIPALES'.")
    st.stop()

# Calcular Valor Total de Stock
df_equipos_stock['ValorTotalStock'] = df_equipos_stock['DisponibleParaPrometer'] * df_equipos_stock['CostoUnitario']

# Filtrar Consumo solo para esos SKUs
lista_skus_equipos = df_equipos_stock['CodigoArticulo'].unique()
df_equipos_consumo = df_consumo[df_consumo['CodigoArticulo'].isin(lista_skus_equipos)].copy()

# Agrupar datos de stock (un SKU puede estar en varias líneas)
df_equipos_stock_agrupado = df_equipos_stock.groupby(['CodigoArticulo', 'NombreArticulo']).agg(
    Unidades_Stock=('DisponibleParaPrometer', 'sum'),
    Valor_Stock=('ValorTotalStock', 'sum')
).reset_index()


# --- 6. KPIs Principales (Métricas) ---
st.header("Métricas Globales (Equipos Principales)")

col1, col2, col3, col4 = st.columns(4)

# KPI 1: SKUs Únicos
total_skus = len(lista_skus_equipos)
col1.metric("SKUs Únicos (en Stock.xlsx)", f"{total_skus}")

# KPI 2: Unidades Totales
total_unidades = df_equipos_stock_agrupado['Unidades_Stock'].sum()
col2.metric("Unidades Totales en Stock", f"{total_unidades:,.0f}")

# KPI 3: Valor Total Inventario
valor_total_inventario = df_equipos_stock_agrupado['Valor_Stock'].sum()
col3.metric("Valor Total del Inventario", f"${valor_total_inventario:,.0f} CLP")

# KPI 4: Consumo Reciente
total_consumo_periodo = df_equipos_consumo['CantidadSolicitada'].sum()
col4.metric("Consumo Reciente (Últ. 4 Meses)", f"{total_consumo_periodo:,.0f} Uds.")

st.markdown("---")

# --- 7. Análisis Visual (Ranking de Productos) ---
st.header("Ranking de Productos")

c1, c2 = st.columns(2)

# --- Gráfico 1: Mayor Valor de Inventario ---
with c1.container(border=True):
    st.subheader("Top 10 por Valor de Inventario")
    
    df_valor = df_equipos_stock_agrupado.nlargest(10, 'Valor_Stock')
    
    chart_valor = alt.Chart(df_valor).mark_bar().encode(
        x=alt.X('Valor_Stock', title='Valor Total (CLP)', axis=alt.Axis(format='$,.0f')),
        y=alt.Y('NombreArticulo', title='Producto', sort='-x'),
        color=alt.Color('NombreArticulo', legend=None),
        tooltip=[
            alt.Tooltip('NombreArticulo', title='Producto'),
            alt.Tooltip('Valor_Stock', title='Valor Total', format='$,.0f'),
            alt.Tooltip('Unidades_Stock', title='Unidades', format=',.0f')
        ]
    ).interactive()
    st.altair_chart(chart_valor, use_container_width=True)

# --- Gráfico 2: Mayor Stock (Unidades) ---
with c2.container(border=True):
    st.subheader("Top 10 por Stock (Unidades)")
    
    df_stock_qty = df_equipos_stock_agrupado.nlargest(10, 'Unidades_Stock')
    
    chart_stock = alt.Chart(df_stock_qty).mark_bar().encode(
        x=alt.X('Unidades_Stock', title='Unidades en Stock'),
        y=alt.Y('NombreArticulo', title='Producto', sort='-x'),
        color=alt.Color('NombreArticulo', legend=None),
        tooltip=[
            alt.Tooltip('NombreArticulo', title='Producto'),
            alt.Tooltip('Unidades_Stock', title='Unidades', format=',.0f'),
            alt.Tooltip('Valor_Stock', title='Valor Total', format='$,.0f')
        ]
    ).interactive()
    st.altair_chart(chart_stock, use_container_width=True)

st.markdown("---")

# --- Gráfico 3: Mayor Rotación (Consumo) ---
with st.container(border=True):
    st.subheader("Top 10 por Rotación (Consumo Reciente)")
    
    if df_equipos_consumo.empty:
        st.info("No se encontró historial de consumo reciente para esta familia de productos.")
    else:
        # Agrupar consumo
        df_rotacion = df_equipos_consumo.groupby('CodigoArticulo')['CantidadSolicitada'].sum().reset_index()
        
        # Merge con nombres (usando los datos de stock agrupado)
        df_nombres = df_equipos_stock_agrupado[['CodigoArticulo', 'NombreArticulo']]
        df_rotacion = df_rotacion.merge(df_nombres, on='CodigoArticulo', how='left').nlargest(10, 'CantidadSolicitada')
        
        # Llenar N/A si un SKU consumido ya no tiene nombre en stock
        df_rotacion['NombreArticulo'] = df_rotacion['NombreArticulo'].fillna(df_rotacion['CodigoArticulo'])
        
        chart_consumo = alt.Chart(df_rotacion).mark_bar().encode(
            x=alt.X('CantidadSolicitada', title='Unidades Consumidas (Últ. 4 Meses)'),
            y=alt.Y('NombreArticulo', title='Producto', sort='-x'),
            color=alt.Color('NombreArticulo', legend=None),
            tooltip=[
                alt.Tooltip('NombreArticulo', title='Producto'),
                alt.Tooltip('CodigoArticulo', title='SKU'),
                alt.Tooltip('CantidadSolicitada', title='Unidades Consumidas', format=',.0f')
            ]
        ).interactive()
        st.altair_chart(chart_consumo, use_container_width=True)
        
# --- 8. Vista de Datos (Detalle) ---
with st.expander("Ver tabla de datos completa ('Equipos Principales')"):
    st.dataframe(
        df_equipos_stock_agrupado.sort_values(by='Valor_Stock', ascending=False),
        column_config={
            "Unidades_Stock": st.column_config.NumberColumn(format="%.0f"),
            "Valor_Stock": st.column_config.NumberColumn(format="$%.0f")
        },
        use_container_width=True
    )