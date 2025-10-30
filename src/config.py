# --- ARCHIVO: src/config.py ---
# (El contenido es el mismo, solo cambia su ubicación)

import pandas as pd

# --- Constantes Globales ---
AVERAGE_DAYS_PER_MONTH = 30.4375
LOCALE_ES = 'es_ES.UTF-8' # Para nombres de meses en español
LOCALE_ES_FALLBACK = 'Spanish_Spain.1252'

# --- Parámetros de Simulación ---
Z_SCORE_MAP = {
    "90%": 1.28, 
    "95%": 1.65, 
    "98%": 2.05, 
    "99%": 2.33
}

# --- Mapeo de SKUs (Homogenización) ---
MAPEO_SKUS = {
    # Grupo 1 (SKUs -> EXI-009231) Inversores 1P5kw Hibrido
    'EXI-008656': 'EXI-009231',
    'EXI-008391': 'EXI-009231', # de 3.6
    'EXI-009287': 'EXI-009231', # de 3.6
    # Paneles
    # Grupo 2 (SKUs -> EXI-009545) Paneles black
    'EXI-008842': 'EXI-008805',
    'EXI-008844': 'EXI-008805',
    'EXI-008805': 'EXI-009545',
    # Panel 650 BIFACIAL EXI-009392
    'EXI-009168': 'EXI-009392',
    'EXI-009275': 'EXI-009392',
    'EXI-008870': 'EXI-009392',
    'EXI-009158': 'EXI-009392',
    'EXI-009477': 'EXI-009392',
    'EXI-008853': 'EXI-009392',
    'EXI-008848': 'EXI-009392',
    'EXI-008853': 'EXI-009392',
    'EXI-008852': 'EXI-009392',
    'EXI-008851': 'EXI-009392',


    # Grupo 3 (SKUs -> EXI-009216) Paneles blue 595
    'EXI-008854': 'EXI-009216', # de 580
    'EXI-008854': 'EXI-009216', # de 580

    # Inversores
    # inversores ongrid 1p5kw solis EXI-008660 
    'EXI-007037': 'EXI-008660', # huawei anterior 5Kw
    #Inversores 25KTL HUAWEI C&I
    'EXI-006082': 'EXI-009219', # huawei anterior 25Kw

    # Baterias 
    # 5wkp 006594
    'EXI-009496': 'EXI-006594', # huawei anterior 5Kw
}