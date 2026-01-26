import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
import random
from datetime import datetime
import requests

# ─────────────────────────────────────────────
# CONFIGURACIÓN DEL SISTEMA
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SYSTEMATRADER | STOCKS V29.0")

st.markdown("""
<style>
    .stDataFrame { font-size: 12px; }
    h1 { color: #2962FF; font-weight: 800; }
    .stExpander { border: 2px solid #2962FF !important; }
</style>
""", unsafe_allow_html=True)

if "sniper_results" not in st.session_state:
    st.session_state["sniper_results"] = []

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE SESIÓN ANTI-BLOQUEO
# ─────────────────────────────────────────────
@st.cache_resource
def get_stealth_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    })
    return session

# ─────────────────────────────────────────────
# BASE DE DATOS MAESTRA
# ─────────────────────────────────────────────
MASTER_INFO = {
    'GGAL': {'T': 'ADR', 'S': 'Financiero'}, 'YPF': {'T': 'ADR', 'S': 'Energía'},
    'BMA': {'T': 'ADR', 'S': 'Financiero'}, 'PAMP': {'T': 'ADR', 'S': 'Energía'},
    'VIST': {'T': 'ADR', 'S': 'Energía'}, 'MELI': {'T': 'ADR', 'S': 'E-Commerce'},
    'AAPL': {'T': 'CEDEAR', 'S': 'Tech'}, 'MSFT': {'T': 'CEDEAR', 'S': 'Tech'},
    'NVDA': {'T': 'CEDEAR', 'S': 'Semis'}, 'TSLA': {'T': 'CEDEAR', 'S': 'Auto'},
    'KO': {'T': 'CEDEAR', 'S': 'Consumo'}, 'SPY': {'T': 'ETF', 'S': 'Índice'},
    'QQQ': {'T': 'ETF', 'S': 'Índice'}, 'DIA': {'T': 'ETF', 'S': 'Índice'}
}

# Timeframes configurados para reducir carga
TIMEFRAMES = {
    "1D": {"int": "1d", "per": "1y"},
    "1H": {"int": "60m", "per": "730d"},
    "30m": {"int": "30m", "per": "30d"},
    "15m": {"int": "15m", "per": "30d"},
    "5m": {"int": "5m", "per": "30d"},
    "1m": {"int": "1m", "per": "5d"}
}

# ─────────────────────────────────────────────
# CÁLCULOS TÉCNICOS
# ─────────────────────────────────────────────
def calculate_heikin_ashi(df):
    df = df.copy()
    df["HA_Close"] = (df["Open"] + df["High"] + df["Low"] + df["Close"]) / 4
    ha_open = [df["Open"].iloc[0]]
    for i in range(1, len(df)):
        ha_open.append((ha_open[-1] + df["HA_Close"].iloc[i-1]) / 2)
    df["HA_Open"], df["HA_Color"] = ha_open, np.where(df["HA_Close"] > ha_open, 1, -1)
    return df

def analyze_stock_tf(symbol, label, config, session):
    try:
        # Petición usando la sesión con User-Agent
        df = yf.download(symbol, interval=config['int'], period=config['per'], 
                         progress=False, auto_adjust=True, session=session)
        
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        if df.empty or len(df) < 35: return None

        macd = ta.macd(df["Close"])
        df["Hist"], df["MACD"], df["Signal"] = macd["MACDh_12_26_9"], macd["MACD_12_26_9"], macd["MACDs_12_26_9"]
        df = calculate_heikin_ashi(df)

        pos = "NEUTRO"
        for i in range(1, len(df)):
            h, ph, hc = df["Hist"].iloc[i], df["Hist"].iloc[i-1], df["HA_Color"].iloc[i]
            if pos == "LONG" and h < ph: pos = "NEUTRO"
            elif pos == "SHORT" and h > ph: pos = "NEUTRO"
            if pos == "NEUTRO":
                if hc == 1 and h > ph: pos = "LONG"
                elif hc == -1 and h < ph: pos = "SHORT"

        return {
            "sig": f"{'🟢' if pos=='LONG' else '🔴' if pos=='SHORT' else '⚪'} {pos}",
            "m0": "SOBRE 0" if df["MACD"].iloc[-1] > 0 else "BAJO 0",
            "h": "SUBIENDO" if df["Hist"].iloc[-1] > df["Hist"].iloc[-2] else "BAJANDO",
            "p": df["Close"].iloc[-1],
            "v_usd": df["Close"].iloc[-1] * df["Volume"].iloc[-1]
        }
    except: return None

# ─────────────────────────────────────────────
# INTERFAZ DE CONTROL
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("🎯 Stock Sniper V29 PRO")
    min_liq = st.number_input("Liquidez Mínima USD:", 1, value=1000000)
    mode = st.radio("Modo:", ["Pool", "Manual"])
    
    if mode == "Pool":
        available = list(MASTER_INFO.keys())
        b_size = st.selectbox("Lote:", [5, 10, 20], index=1)
        batches = [available[i:i+b_size] for i in range(0, len(available), b_size)]
        sel = st.selectbox("Seleccionar Lote:", range(len(batches)))
        targets = batches[sel] if batches else []
    else:
        custom = st.text_input("Tickers (ej: TSLA,AAPL):")
        targets = [x.strip().upper() for x in custom.split(",")] if custom else []

    if st.button("🚀 INICIAR ESCANEO"):
        session = get_stealth_session()
        temp_results = []
        prog = st.progress(0)
        
        for idx, sym in enumerate(targets):
            prog.progress((idx+1)/len(targets), text=f"Analizando {sym}")
            
            # --- PASO 1: Descargar 1D PRIMERO (Ahorro de peticiones) ---
            res_1d = analyze_stock_tf(sym, "1D", TIMEFRAMES["1D"], session)
            
            if res_1d and res_1d["v_usd"] >= min_liq:
                row = {
                    "Activo": sym, "Precio": f"{res_1d['p']:.2f}",
                    "Tipo": MASTER_INFO.get(sym, {}).get('T', 'MANUAL'),
                    "Sector": MASTER_INFO.get(sym, {}).get('S', 'CUSTOM'),
                    "1D H.A./MACD": res_1d["sig"], "1D Hist.": res_1d["h"], "1D MACD 0": res_1d["m0"]
                }
                
                # --- PASO 2: Descargar el resto solo si superó liquidez ---
                for label in ["1H", "30m", "15m", "5m", "1m"]:
                    res = analyze_stock_tf(sym, label, TIMEFRAMES[label], session)
                    if res:
                        row[f"{label} H.A./MACD"] = res["sig"]
                        row[f"{label} Hist."] = res["h"]
                    else:
                        row[f"{label} H.A./MACD"], row[f"{label} Hist."] = "-", "-"
                    time.sleep(random.uniform(0.1, 0.3)) # Throttling entre TFs
                
                # Veredicto
                bulls = sum(1 for label in TIMEFRAMES if "LONG" in str(row.get(f"{label} H.A./MACD", "")))
                bears = sum(1 for label in TIMEFRAMES if "SHORT" in str(row.get(f"{label} H.A./MACD", "")))
                row["VEREDICTO"] = "🔥 COMPRA" if bulls >= 4 and "SOBRE 0" in row["1D MACD 0"] else "🩸 VENTA" if bears >= 4 and "BAJO 0" in row["1D MACD 0"] else "⚖️ RANGO"
                temp_results.append(row)
            
            time.sleep(random.uniform(1.0, 2.0)) # Throttling entre Activos

        st.session_state["sniper_results"] = temp_results
        st.rerun()

# ─────────────────────────────────────────────
# FILTROS Y TABLA FINAL
# ─────────────────────────────────────────────
if st.session_state["sniper_results"]:
    df_f = pd.DataFrame(st.session_state["sniper_results"])
    
    st.sidebar.divider()
    f_ver = st.sidebar.multiselect("Veredicto:", options=df_f["VEREDICTO"].unique(), default=df_f["VEREDICTO"].unique())
    f_sec = st.sidebar.multiselect("Sector:", options=df_f["Sector"].unique(), default=df_f["Sector"].unique())
    f_h1d = st.sidebar.multiselect("1D Hist:", options=df_f["1D Hist."].unique(), default=df_f["1D Hist."].unique())

    df_filtered = df_f[(df_f["VEREDICTO"].isin(f_ver)) & (df_f["Sector"].isin(f_sec)) & (df_f["1D Hist."].isin(f_h1d))]

    def style_matrix(val):
        v = str(val).upper()
        if any(x in v for x in ["LONG", "SOBRE 0", "SUBIENDO", "COMPRA"]): return 'background-color: #d4edda; color: #155724;'
        if any(x in v for x in ["SHORT", "BAJO 0", "BAJANDO", "VENTA"]): return 'background-color: #f8d7da; color: #721c24;'
        return ''

    prio = ["Activo", "Tipo", "Sector", "VEREDICTO", "1D Hist.", "1D H.A./MACD", "Precio"]
    st.dataframe(df_filtered[prio + [c for c in df_filtered.columns if c not in prio]].style.applymap(style_matrix), use_container_width=True, height=800)
