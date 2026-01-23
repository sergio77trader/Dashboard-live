import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SystemaTrader: MACD Titan Matrix")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 14px; }
    .stProgress > div > div > div > div { background-color: #2962FF; }
    /* Ajuste para que las celdas multilinea se vean bien */
    div[data-testid="stVerticalBlock"] div[data-testid="stDataFrame"] div[role="grid"] {
        white-space: pre-wrap !important; 
    }
</style>
""", unsafe_allow_html=True)

# --- MEMORIA ---
if 'titan_results' not in st.session_state:
    st.session_state['titan_results'] = []

# --- TEMPORALIDADES SOLICITADAS ---
TIMEFRAMES = {
    '15m': '15m',
    '1H': '1h',
    '4H': '4h',
    '1D': '1d',
    '1W': '1w'
}

# --- CONEXIÓN KUCOIN ---
@st.cache_resource
def get_exchange():
    return ccxt.kucoinfutures({
        'enableRateLimit': True,
        'timeout': 30000
    })

@st.cache_data(ttl=3600)
def get_active_pairs():
    try:
        ex = get_exchange()
        tickers = ex.fetch_tickers()
        valid = []
        for s in tickers:
            if '/USDT:USDT' in s and tickers[s].get('quoteVolume'):
                valid.append({'symbol': s, 'vol': tickers[s]['quoteVolume']})
        return pd.DataFrame(valid).sort_values('vol', ascending=False)['symbol'].tolist()
    except: return []

# --- LÓGICA DE ANÁLISIS ---
def calculate_heikin_ashi(df):
    df_ha = df.copy()
    df_ha['HA_Close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    ha_open = [df['open'].iloc[0]]
    for i in range(1, len(df)):
        ha_open.append((ha_open[-1] + df_ha['HA_Close'].iloc[i-1]) / 2)
    df_ha['HA_Open'] = ha_open
    df_ha['HA_Color'] = np.where(df_ha['HA_Close'] > df_ha['HA_Open'], 1, -1)
    return df_ha

def analyze_ticker_tf(symbol, tf_code, exchange):
    try:
        # Bajamos historial suficiente para detectar cruces viejos
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=200)
        if not ohlcv or len(ohlcv) < 50: return None
        
        df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
        df['dt'] = pd.to_datetime(df['time'], unit='ms')
        
        # 1. MACD
        macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
        df['MACD'] = macd['MACD_12_26_9']
        df['Signal'] = macd['MACDs_12_26_9']
        df['Hist'] = macd['MACDh_12_26_9']
        
        # 2. Heikin Ashi
        df = calculate_heikin_ashi(df)
        
        # --- ANÁLISIS DE ESTADO HA (TU ESTRATEGIA ORIGINAL) ---
        position = "NEUTRO"
        
        for i in range(1, len(df)):
            hist = df['Hist'].iloc[i]
            prev_hist = df['Hist'].iloc[i-1]
            ha_color = df['HA_Color'].iloc[i]
            
            if position == "LONG" and hist < prev_hist: position = "NEUTRO"
            elif position == "SHORT" and hist > prev_hist: position = "NEUTRO"
            
            if position == "NEUTRO":
                if ha_color == 1 and hist > prev_hist: position = "LONG"
                elif ha_color == -1 and hist < prev_hist: position = "SHORT"

        # --- ANÁLISIS DE HISTOGRAMA (MOMENTUM) ---
        curr_hist = df['Hist'].iloc[-1]
        prev_hist = df['Hist'].iloc[-2]
        
        # ¿Sube o baja respecto a la vela anterior?
        hist_status = "📈 Subiendo" if curr_hist > prev_hist else "📉 Bajando"
        
        # --- ANÁLISIS DE CRUCE (CROSSOVER) ---
        # Detectar cuándo cruzó MACD y Signal
        df['Cross'] = np.where(df['MACD'] > df['Signal'], 1, -1)
        df['Change'] = df['Cross'].diff() # Donde no es 0, hubo cruce
        
        last_cross_row = df[df['Change'] != 0].iloc[-1]
        cross_type = "🐂 GOLDEN" if last_cross_row['Cross'] == 1 else "🐻 DEATH"
        
        # Ajuste horario Argentina (-3h)
        cross_dt = last_cross_row['dt'] - pd.Timedelta(hours=3)
        cross_str = cross_dt.strftime('%d/%m %H:%M')
        
        return {
            "pos": position,
            "hist_st": hist_status,
            "cross_type": cross_type,
            "cross_time": cross_str,
            "raw_hist": curr_hist # Para recomendaciones
        }
        
    except Exception: return None

# --- RECOMENDACIÓN IA ---
def get_recommendations(row):
    # Estrategia HA (Original)
    bull_count = 0
    bear_count = 0
    
    # Estrategia MACD Pura
    macd_bull_mom = 0
    
    for tf in TIMEFRAMES:
        raw = row.get(f"raw_{tf}")
        if raw:
            if raw['pos'] == "LONG": bull_count += 1
            if raw['pos'] == "SHORT": bear_count += 1
            if "Subiendo" in raw['hist_st']: macd_bull_mom += 1

    # Diagnóstico HA
    ha_diag = "⚖️ Rango"
    if bull_count >= 3: ha_diag = "🔥 COMPRA"
    if bear_count >= 3: ha_diag = "🩸 VENTA"
    
    # Diagnóstico MACD
    macd_diag = "Neutro"
    if macd_bull_mom >= 4: macd_diag = "🚀 Potencia Alcista"
    elif macd_bull_mom == 0: macd_diag = "📉 Caída Libre"
    
    return ha_diag, macd_diag

# --- BUCLE ---
def scan_batch(targets):
    ex = get_exchange()
    results = []
    prog = st.progress(0, text="Iniciando...")
    
    for idx, sym in enumerate(targets):
        clean = sym.replace(':USDT', '').replace('/USDT', '')
        prog.progress(idx/len(targets), text=f"Analizando {clean}...")
        
        try:
            ticker = ex.fetch_ticker(sym)
            price = ticker['last']
        except: price = 0
            
        row = {'Activo': clean, 'Precio': price}
        
        # Iterar TFs
        for label, tf_code in TIMEFRAMES.items():
            res = analyze_ticker_tf(sym, tf_code, ex)
            if res:
                # Guardamos datos crudos para el diagnóstico
                row[f"raw_{label}"] = res
                
                # --- FORMATEO DE CELDA (MULTILINEA) ---
                # Icono Estado
                icon = "🟢" if res['pos'] == "LONG" else "🔴" if res['pos'] == "SHORT" else "⚪"
                
                # Construcción del texto visible
                # Línea 1: Estado HA
                # Línea 2: Histograma
                # Línea 3: Cruce MACD
                cell_text = f"{icon} {res['pos']}\nH: {res['hist_st']}\nX: {res['cross_type']} ({res['cross_time']})"
                
                row[label] = cell_text
            else:
                row[label] = "⚠️ Error"
        
        # Generar Diagnósticos
        strat_ha, strat_macd = get_recommendations(row)
        row['Estrategia HA'] = strat_ha
        row['Radar MACD'] = strat_macd
        
        results.append(row)
        time.sleep(0.1)
        
    prog.empty()
    return results

# --- INTERFAZ ---
st.title("🛡️ SystemaTrader: MACD Titan Matrix")
st.caption("Heikin Ashi Trend + MACD Deep Dive (Datos Histograma y Cruces)")

with st.sidebar:
    st.header("Configuración")
    all_symbols = get_active_pairs()
    
    if all_symbols:
        st.success(f"Mercado: {len(all_symbols)} activos")
        BATCH_SIZE = st.selectbox("Lote:", [10, 20, 30, 50], index=1)
        batches = [all_symbols[i:i + BATCH_SIZE] for i in range(0, len(all_symbols), BATCH_SIZE)]
        sel_batch = st.selectbox("Seleccionar:", range(len(batches)), format_func=lambda x: f"Lote {x+1}")
        
        accumulate = st.checkbox("Acumular", value=True)
        
        if st.button("🚀 ESCANEAR", type="primary"):
            target = batches[sel_batch]
            with st.spinner("Procesando datos complejos..."):
                new_data = scan_batch(target)
                if accumulate:
                    existing = {x['Activo'] for x in st.session_state['titan_results']}
                    for item in new_data:
                        if item['Activo'] not in existing:
                            st.session_state['titan_results'].append(item)
                else:
                    st.session_state['titan_results'] = new_data
    
    if st.button("Limpiar"):
        st.session_state['titan_results'] = []
        st.rerun()

# --- TABLA ---
if st.session_state['titan_results']:
    df = pd.DataFrame(st.session_state['titan_results'])
    
    # Colores para diagnósticos
    def style_diag(val):
        if "COMPRA" in str(val) or "Potencia" in str(val): return "color: #00FF00; font-weight: bold"
        if "VENTA" in str(val) or "Caída" in str(val): return "color: #FF0000; font-weight: bold"
        return ""

    # Ordenar columnas
    cols = ['Activo', 'Estrategia HA', 'Radar MACD', 'Precio', '15m', '1H', '4H', '1D', '1W']
    
    st.dataframe(
        df[cols].style.map(style_diag, subset=['Estrategia HA', 'Radar MACD']),
        column_config={
            "Activo": st.column_config.TextColumn("Crypto", width="small", pinned=True),
            "Estrategia HA": st.column_config.TextColumn("Diag. Tendencia", width="small"),
            "Radar MACD": st.column_config.TextColumn("Diag. Momentum", width="small"),
            "Precio": st.column_config.NumberColumn(format="$%.4f"),
            
            # Las columnas de tiempo son anchas para que entre el texto
            "15m": st.column_config.TextColumn("15 Minutos", width="medium"),
            "1H": st.column_config.TextColumn("1 Hora", width="medium"),
            "4H": st.column_config.TextColumn("4 Horas", width="medium"),
            "1D": st.column_config.TextColumn("Diario", width="medium"),
            "1W": st.column_config.TextColumn("Semanal", width="medium"),
        },
        use_container_width=True,
        height=800
    )
else:
    st.info("👈 Selecciona un lote. El análisis incluye Fecha de Cruce y Dirección del Histograma.")
