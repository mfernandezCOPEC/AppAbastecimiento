# --- ARCHIVO: appv3.py ---
# (Rediseñado para una mejor Experiencia de Usuario - UX)

import streamlit as st
import sys
from pathlib import Path

# --- 1. Configuración de la Página y del Path ---
src_path = str(Path(__file__).parent / "src")
if src_path not in sys.path:
    sys.path.append(src_path)

import data_loader 

# --- 2. Configuración de la Página (Debe ser lo primero) ---
st.set_page_config(
    layout="wide",
    page_title="Menú Abastecimiento", 
    page_icon="assets/COPEC-FLUX.svg"
)

# --- 3. Carga de Datos en Session State ---
# Esto se ejecuta primero. data_loader.py se encarga del cache
# y de guardar todo en st.session_state.
data_loader.load_data_into_session()

# --- 4. Lógica de la Página del Menú Principal ---

# --- Encabezado Profesional (Logo + Título) ---
col1, col2 = st.columns([1, 4])
with col1:
    try:
        st.image("assets/COPEC-FLUX.svg", width=150)
    except Exception as e:
        st.error(f"No se pudo cargar logo: {e}")

with col2:
    st.title("Asistente de Abastecimiento Flux")
    st.caption("Bienvenido al portal de simulación y consulta de inventario.")

st.markdown("---") # Separador visual

# --- (NUEVO) Sección "Cómo Empezar" ---
with st.expander("👋 ¡Bienvenido! Haz clic aquí para ver cómo usar la app", expanded=True):
    st.markdown(
        """
        Esta plataforma centraliza las herramientas clave para la gestión de inventario.
        
        **Cómo Empezar (2 Pasos):**
        
        1.  **👈 Navega en la Barra Lateral:** Todas las herramientas (Simulador, Llegadas, KPIs) se encuentran en el menú de la izquierda.
        2.  **🔍 Usa los Filtros:** Dentro de cada herramienta, encontrarás filtros (usualmente en la barra lateral) para seleccionar SKUs, compradores o fechas.
        
        """
    )

# --- (NUEVO) Estado de los Datos ---
st.header("Estado de la Aplicación")
if 'data_loaded' in st.session_state and st.session_state.data_loaded:
    st.success(
        """
        ¡Datos cargados correctamente!
        
        Se han cargado los archivos de `Stock`, `OPOR (OCs)`, `Consumo` y `Residencial`. 
        La aplicación está lista para ser usada.
        """
    )
else:
    st.error(
        """
        Error en la carga de datos.
        
        Asegúrate de que los archivos 'Stock.xlsx', 'OPOR.xlsx', 'ST_OWTR.xlsx' y 'BD_Master_Residencial.xlsx' 
        existan en la carpeta `data/`.
        """
    )

st.markdown("---")

# --- (NUEVO) Navegación por Pestañas de Módulos ---
st.header("Herramientas Disponibles")

tab1, tab2, tab3 = st.tabs([
    "📈 Simulador de Inventario", 
    "📦 Consulta de Llegadas", 
    "📊 KPIs Compradores"
])

with tab1:
    st.subheader("Quiero proyectar mi inventario y saber cuándo pedir.")
    st.markdown(
        """
        Utiliza el **Simulador** para:
        - Proyectar tu inventario futuro basado en el consumo histórico.
        - Calcular automáticamente el Stock de Seguridad (SS) y el Punto de Reorden (ROP).
        - Recibir recomendaciones claras sobre *qué* y *cuánto* pedir.
        """
    )
    st.info("Selecciona **'Simulator'** (o el nombre de tu página) en el menú lateral para comenzar.")

with tab2:
    st.subheader("Quiero saber cuándo llega un pedido específico.")
    st.markdown(
        """
        Utiliza la **Consulta de Llegadas** para:
        - Rastrear todas las Órdenes de Compra (OC) que están en tránsito.
        - Filtrar por SKU, número de documento o proveedor.
        - Ver las fechas de llegada programadas y las cantidades pendientes.
        """
    )
    st.info("Selecciona **'Llegadas'** en el menú lateral para ver detalles.")

with tab3:
    st.subheader("Quiero analizar el rendimiento del equipo de compras.")
    st.markdown(
        """
        Utiliza el Dashboard de **KPIs Compradores** para:
        - Ver el total de OCs generadas por mes, divididas por comprador.
        - Analizar los montos totales (CLP) gestionados por cada miembro del equipo.
        - Identificar tendencias y comparar el rendimiento.
        """
    )
    st.info("Selecciona **'KPIs Compradores'** en el menú lateral para ver el dashboard.")


# --- Configuración de la Barra Lateral (Sidebar) ---
st.sidebar.markdown("---")
st.sidebar.image("assets/COPEC-FLUX.svg", use_container_width=True)
st.sidebar.header("Navegación Principal")
st.sidebar.info("Seleccione la herramienta que desea utilizar en el menú de arriba. 👆")
st.sidebar.markdown("---")


# --- Pie de Página (Footer) ---
st.markdown("---")
st.caption("© 2025 Copec Flux S.A. | Todos los derechos reservados.")
st.caption("Desarrollado por el equipo de Abastecimiento Copec Flux.")
