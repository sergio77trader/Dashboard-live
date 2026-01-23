import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SystemaTrader: Hybrid Matrix")
st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 14px; }
    .stProgress > div > div > div > div { background-color: #2962FF; }
    /* Ajuste para celdas multilínea */
    .stDataFrame td { white-space: pre-wrap !important; }
</style>
""", unsafe_allow_html=True)

if 'hybrid_results' not in st.session_state:
    st.session_state['hybrid_results'] = []

TIMEFRAMES = {
    '15m': '15m',
    '1H': '1h',
    '4H': '4h',
    'Diario': '1d',
    'Semanal': '1w'
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

# --- LÓGICA COMBINADA (HA + MACD) ---
def analyze_tf(symbol, tf_code, exchange):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=200)
        if not ohlcv or len(ohlcv) < 50: return None
        
        df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
        df['dt'] = pd.to_datetime(df['time'], unit='ms')
        
        # 1. HEIKIN ASHI (Tu lógica original)
        df['HA_Close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
        ha_open = [df['open'].iloc[0]]
        for i in range(1, len(df)):
            ha_open.append((ha_open[-1] + df['HA_Close'].iloc[i-1]) / 2)
        df['HA_Open'] = ha_open
        
        # Estado HA Actual
        ha_state = "LONG" if df['HA_Close'].iloc[-1] > df['HA_Open'].iloc[-1] else "SHORT"

        # 2. MACD (Lo nuevo que pediste)
        macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
        df['MACD'] = macd['MACD_12_26_9']
        df['Signal'] = macd['MACDs_12_26_9']
        df['Hist'] = macd['MACDh_12_26_9']

        # A. Histograma vs Vela Anterior
        curr_hist = df['Hist'].iloc[-1]
        prev_hist = df['Hist'].iloc[-2]
        hist_trend = "Subiendo 📈" if curr_hist > prev_hist else "Bajando 📉"

        # B. Cruce de Líneas y Fecha
        df['Cross'] = np.where(df['MACD'] > df['Signal'], 1, -1)
        df['Change'] = df['Cross'].diff() # != 0 implica cruce
        
        # Buscar el último cruce real
        cross_rows = df[df['Change'] != 0]
        if not cross_rows.empty:
            last_cross = cross_rows.iloc[-1]
            c_type = "GOLDEN (Alcista)" if last_cross['Cross'] == 1 else "DEATH (Bajista)"
            # Ajuste Hora Argentina (-3)
            c_time = (last_cross['dt'] - pd.Timedelta(hours=3)).strftime('%d/%m %H:%M')
        else:
            c_type = "Sin Cruce"
            c_time = "-"

        return {
            "ha": ha_state,
            "hist": hist_trend,
            "c_type": c_type,
            "c_time": c_time
        }

    except: return None

# --- RECOMENDACIÓN IA ---
def get_verdict(row):
    score = 0
    # Pesos por temporalidad
    weights = {'15m': 1, '1H': 2, '4H': 3, 'Diario': 4}
    
    for tf, w in weights.items():
        # Leemos el estado HA que guardamos en la columna
        cell_data = row.get(tf, "") 
        if "LONG" in cell_data: score += w
        if "SHORT" in cell_data: score -= w
        
        # Bonus si el histograma acompaña
        if "Subiendo" in cell_data and "LONG" in cell_data: score += 0.5
        if "Bajando" in cell_data and "SHORT" in cell_data: score -= 0.5

    if score >= 6: return "🔥 COMPRA FUERTE"
    if score >= 2: return "🟢 ALCISTA"
    if score <= -6: return "🩸 VENTA FUERTE"
    if score <= -2: return "🔴 BAJISTA"
    return "⚖️ NEUTRO / RANGO"

# --- BUCLE ---
def scan_batch(targets):
    ex = get_exchange()
    results = []
    prog = st.progress(0, text="Escaneando...")
    
    for idx, sym in enumerate(targets):
        clean = sym.replace(':USDT', '').replace('/USDT', '')
        prog.progress(idx/len(targets), text=f"Procesando {clean}...")
        
        # Precio actual
        try: px = ex.fetch_ticker(sym)['last']
        except: px = 0
        
        row = {'Activo': clean, 'Precio': px}
        
        for label, tf_code in TIMEFRAMES.items():
            res = analyze_tf(symbol=sym, tf_code=tf_code, exchange=ex)
            if res:
                # COLUMNA 1: ESTADO HA + HISTOGRAMA (Lo Original + Detalle)
                icon = "🟢" if res['ha'] == "LONG" else "🔴"
                # Formato: 🟢 LONG | 📈 Subiendo
                row[label] = f"{icon} {res['ha']} | {res['hist']}"
                
                # COLUMNA 2: DETALLE CRUCE (Lo que pediste ahora)
                # Formato: GOLDEN 23/01 15:00
                c_icon = "🐂" if "GOLDEN" in res['c_type'] else "🐻"
                row[f"{label} Cruce"] = f"{c_icon} {res['c_type']}\n🕒 {res['c_time']}"
            else:
                row[label] = "-"
                row[f"{label} Cruce"] = "-"
        
        row['RECOMENDACIÓN'] = get_verdict(row)
        results.append(row)
        time.sleep(0.1)
        
    prog.empty()
    return results

# --- INTERFAZ ---
st.title("🛡️ SystemaTrader: Hybrid Matrix (HA + MACD Detail)")

with st.sidebar:
    st.header("Configuración")
    all_symbols = get_active_pairs()
    
    if all_symbols:
        st.success(f"Mercado: {len(all_symbols)} activos")
        BATCH = st.selectbox("Lote:", [10, 20, 30, 50], index=1)
        batches = [all_symbols[i:i+BATCH] for i in range(0, len(all_symbols), BATCH)]
        sel = st.selectbox("Seleccionar:", range(len(batches)), format_func=lambda x: f"Lote {x+1}")
        
        acc = st.checkbox("Acumular", value=True)
        
        if st.button("🚀 ESCANEAR", type="primary"):
            target = batches[sel]
            with st.spinner("Analizando cruces y tendencias..."):
                new = scan_batch(target)
                if acc: st.session_state['hybrid_results'].extend(new)
                else: st.session_state['hybrid_results'] = new
    
    if st.button("Limpiar"):
        st.session_state['hybrid_results'] = []
        st.rerun()

# --- TABLA ---
if st.session_state['hybrid_results']:
    df = pd.DataFrame(st.session_state['hybrid_results'])
    
    # Ordenar columnas lógicamente
    cols = ['Activo', 'RECOMENDACIÓN', 'Precio']
    for tf in TIMEFRAMES:
        cols.append(tf)         # Columna Estado Original + Histograma
        cols.append(f"{tf} Cruce") # Columna Nueva con Fecha y Tipo
        
    # Filtrar existentes
    final_cols = [c for c in cols if c in df.columns]
    
    def style_rec(val):
        if "COMPRA" in str(val): return "background-color: #1b3a1b; color: #00ff00; font-weight: bold"
        if "VENTA" in str(val): return "background-color: #3a1b1b; color: #ff0000; font-weight: bold"
        return ""

    st.dataframe(
        df[final_cols].style.map(style_rec, subset=['RECOMENDACIÓN']),
        column_config={
            "Activo": st.column_config.TextColumn("Crypto", pinned=True),
            "Precio": st.column_config.NumberColumn(format="$%.4f"),
            "RECOMENDACIÓN": st.column_config.TextColumn("Diagnóstico IA", width="medium"),
            
            # Configuración de columnas TF
            "15m": st.column_config.TextColumn("15m Estado", width="medium"),
            "15m Cruce": st.column_config.TextColumn("15m Cruce MACD", width="medium"),
            
            "1H": st.column_config.TextColumn("1H Estado", width="medium"),
            "1H Cruce": st.column_config.TextColumn("1H Cruce MACD", width="medium"),
            
            "4H": st.column_config.TextColumn("4H Estado", width="medium"),
            "4H Cruce": st.column_config.TextColumn("4H Cruce MACD", width="medium"),
            
            "Diario": st.column_config.TextColumn("1D Estado", width="medium"),
            "Diario Cruce": st.column_config.TextColumn("1D Cruce MACD", width="medium"),
            
            "Semanal": st.column_config.TextColumn("1W Estado", width="medium"),
            "Semanal Cruce": st.column_config.TextColumn("1W Cruce MACD", width="medium"),
        },
        use_container_width=True,
        height=800
    )
else:
    st.info("👈 Selecciona un lote. La tabla mostrará Tendencia, Histograma y Fecha de Cruce.")
