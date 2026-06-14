import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime

# ─────────────────────────────────────────────
# 1. CONFIGURACIÓN DEL SISTEMA
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | TOTAL MACRO TERMINAL")

st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    .stDataFrame { font-size: 10px; font-family: 'Roboto Mono', monospace; }
    h1 { color: #00897B; font-weight: 800; border-bottom: 2px solid #00897B; }
    .vol-info { background-color: #E1F5FE; padding: 10px; border-left: 5px solid #0288D1; border-radius: 5px; margin-bottom: 20px; color: #01579B; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

if "sniper_results" not in st.session_state:
    st.session_state["sniper_results"] = []

# Mapeo de temporalidades adaptado para Cripto y Acciones
MACRO_CONFIG = {
    "1D/1H": {"int": "1h", "per": "2y"},
    "1S/4H": {"int": "4h", "per": "5y"},
    "1M/1D": {"int": "1d", "per": "max"}
}

RAW_TICKERS = "BIL, SPY, QQQ, ARKK, GLD, AAPL, AMZN, TSLA, MSFT, META, NVDA, GOOGL, GGAL, YPF, PAMP, BMA, BTC-USD, ETH-USD, SOL-USD"
MASTER_TICKERS = sorted(list(set([t.strip() for t in RAW_TICKERS.split(",") if t.strip()])))

# ─────────────────────────────────────────────
# 2. MOTORES TÉCNICOS (MACD & RSI)
# ─────────────────────────────────────────────
def get_hist_dynamics(current, previous):
    if current > previous:
        return "Subiendo 📈" if current > 0 else "Recuperando ↗️"
    else:
        return "Bajando 📉" if current < 0 else "Agotándose ↘️"

def run_sly_engine(df, offset=False):
    if df.empty or len(df) < 35: return "FUERA ⚪", "-", "S/D", "S/D"
    
    # MACD
    macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
    hist = macd['MACDh_12_26_9']
    
    # RSI
    rsi = ta.rsi(df['Close'], length=14)
    
    # Offset para Semanal (ignorar vela actual)
    idx = -2 if offset else -1
    prev_idx = idx - 1
    
    # Dinámica Histograma
    dyn = get_hist_dynamics(hist.iloc[idx], hist.iloc[prev_idx])
    
    # Dinámica RSI
    rsi_val = rsi.iloc[idx]
    rsi_dyn = "Subiendo" if rsi.iloc[idx] > rsi.iloc[prev_idx] else "Bajando"
    rsi_label = f"{rsi_val:.1f} {rsi_dyn}"
    
    # Heikin Ashi
    ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    ha_open = np.zeros(len(df)); ha_open[0] = (df['Open'].iloc[0] + df['Close'].iloc[0]) / 2
    for i in range(1, len(df)): ha_open[i] = (ha_open[i-1] + ha_close.iloc[i-1]) / 2
    ha_color = "VERDE 🟢" if ha_close.iloc[idx] > ha_open.iloc[idx] else "ROJO 🔴"
    
    return ha_color, rsi_label, dyn, df['Close'].iloc[idx]

# ─────────────────────────────────────────────
# 3. ANALIZADOR DE ACTIVOS
# ─────────────────────────────────────────────
def analyze_asset(symbol):
    row = {"Activo": symbol, "Sector": "S/D", "País": "S/D", "Precio": 0.0}
    try:
        info = yf.Ticker(symbol).info
        row["Sector"] = info.get('sector', 'ETF/Cripto')
        row["País"] = info.get('country', 'Global')
    except: pass

    for tf_label, config in MACRO_CONFIG.items():
        try:
            df = yf.download(symbol, interval=config['int'], period=config['per'], progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if df.empty or len(df) < 35: continue
            
            # Aplicar offset solo en la temporalidad intermedia (Semanal/4H)
            is_offset = True if "1S" in tf_label else False
            ha, rsi, hist, price = run_sly_engine(df, offset=is_offset)
            
            if "1D" in tf_label: row["Precio"] = float(price)
            
            row[f"{tf_label} HA"] = ha
            row[f"{tf_label} RSI"] = rsi
            row[f"{tf_label} Hist."] = hist
            
            # Volumen en 4H (Intermedia)
            if "1S/4H" in tf_label:
                curr_v = df['Volume'].tail(4).sum()
                prev_v = df['Volume'].iloc[-8:-4].sum()
                row["Vol 4H %"] = round(((curr_v - prev_v) / prev_v * 100), 2) if prev_v > 0 else 0.0
        except: pass
    return row

# ─────────────────────────────────────────────
# 4. INTERFAZ Y RENDERIZADO
# ─────────────────────────────────────────────
st.title("🛡️ SLY TOTAL TERMINAL v52.0")
st.markdown('<div class="vol-info">📊 ANALÍTICA INTEGRADA: Metadata + Dinámica MACD/RSI | Lógica Cripto-Híbrida.</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Configuración")
    b_size = st.selectbox("Lote de Escaneo:", [10, 25, 50], index=0)
    batches = [MASTER_TICKERS[i:i+b_size] for i in range(0, len(MASTER_TICKERS), b_size)]
    sel_batch = st.selectbox("Seleccionar Lote:", range(len(batches)), format_func=lambda x: f"Lote {x+1}")
    
    if st.button("🚀 INICIAR ESCANEO", type="primary", use_container_width=True):
        results = []
        prog = st.progress(0)
        targets = batches[sel_batch]
        for idx, sym in enumerate(targets):
            prog.progress((idx+1)/len(targets), text=f"Analizando: {sym}")
            results.append(analyze_asset(sym))
        
        current = {x["Activo"]: x for x in st.session_state["sniper_results"]}
        for r in results: current[r["Activo"]] = r
        st.session_state["sniper_results"] = list(current.values())
        st.rerun()

    if st.button("Limpiar Memoria"):
        st.session_state["sniper_results"] = []; st.rerun()

if st.session_state["sniper_results"]:
    df = pd.DataFrame(st.session_state["sniper_results"])
    
    def style_matrix(v):
        v_str = str(v)
        if "VERDE" in v_str or "Subiendo" in v_str or "Recuperando" in v_str: return 'color: #2E7D32; font-weight: bold;'
        if "ROJO" in v_str or "Bajando" in v_str or "Agotándose" in v_str: return 'color: #C62828; font-weight: bold;'
        return ''

    st.dataframe(df.style.map(style_matrix), use_container_width=True, height=800)
else:
    st.info("👈 Seleccione un lote para iniciar la auditoría institucional.")
