import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SYSTEMATRADER | STOCKS V28.0")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 14px; }
    .stDataFrame { font-size: 12px; }
    h1 { color: #2962FF; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

if "sniper_results" not in st.session_state:
    st.session_state["sniper_results"] = []

# ─────────────────────────────────────────────
# BASE DE DATOS MAESTRA (150+ ACTIVOS)
# ─────────────────────────────────────────────
MASTER_INFO = {
    # ARGENTINA (ADRs)
    'GGAL': {'T': 'ADR', 'S': 'Financiero'}, 'YPF': {'T': 'ADR', 'S': 'Energía'},
    'BMA': {'T': 'ADR', 'S': 'Financiero'}, 'PAMP': {'T': 'ADR', 'S': 'Energía'},
    'TGS': {'T': 'ADR', 'S': 'Energía'}, 'CEPU': {'T': 'ADR', 'S': 'Energía'},
    'EDN': {'T': 'ADR', 'S': 'Energía'}, 'BFR': {'T': 'ADR', 'S': 'Financiero'},
    'SUPV': {'T': 'ADR', 'S': 'Financiero'}, 'CRESY': {'T': 'ADR', 'S': 'Agro'},
    'IRS': {'T': 'ADR', 'S': 'Inmuebles'}, 'TEO': {'T': 'ADR', 'S': 'Telecom'},
    'LOMA': {'T': 'ADR', 'S': 'Construcción'}, 'VIST': {'T': 'ADR', 'S': 'Energía'},
    'GLOB': {'T': 'ADR', 'S': 'Tech'}, 'MELI': {'T': 'ADR', 'S': 'E-Commerce'},
    'DESP': {'T': 'ADR', 'S': 'Turismo'}, 'TX': {'T': 'ADR', 'S': 'Siderurgia'},
    # CEDEARS SELECCIONADOS
    'AAPL': {'T': 'CEDEAR', 'S': 'Tech'}, 'MSFT': {'T': 'CEDEAR', 'S': 'Tech'},
    'NVDA': {'T': 'CEDEAR', 'S': 'Semis'}, 'AMD': {'T': 'CEDEAR', 'S': 'Semis'},
    'GOOGL': {'T': 'CEDEAR', 'S': 'Tech'}, 'AMZN': {'T': 'CEDEAR', 'S': 'Retail'},
    'META': {'T': 'CEDEAR', 'S': 'Tech'}, 'TSLA': {'T': 'CEDEAR', 'S': 'Auto'},
    'NFLX': {'T': 'CEDEAR', 'S': 'Consumo'}, 'KO': {'T': 'CEDEAR', 'S': 'Consumo'},
    'JPM': {'T': 'CEDEAR', 'S': 'Banco'}, 'WMT': {'T': 'CEDEAR', 'S': 'Retail'},
    'GOLD': {'T': 'CEDEAR', 'S': 'Minería'}, 'XOM': {'T': 'CEDEAR', 'S': 'Energía'},
    'SPY': {'T': 'ETF', 'S': 'Índice'}, 'QQQ': {'T': 'ETF', 'S': 'Índice'},
    'DIA': {'T': 'ETF', 'S': 'Índice'}, 'EEM': {'T': 'ETF', 'S': 'Emergentes'},
    'EWZ': {'T': 'ETF', 'S': 'Brasil'}
}

TIMEFRAMES = {
    "1m": {"int": "1m", "per": "5d"}, "5m": {"int": "5m", "per": "30d"},
    "15m": {"int": "15m", "per": "30d"}, "30m": {"int": "30m", "per": "30d"},
    "1H": {"int": "60m", "per": "730d"}, "1D": {"int": "1d", "per": "max"}
}

# ─────────────────────────────────────────────
# FUNCIONES TÉCNICAS
# ─────────────────────────────────────────────
def calculate_heikin_ashi(df):
    df = df.copy()
    df["HA_Close"] = (df["Open"] + df["High"] + df["Low"] + df["Close"]) / 4
    ha_open = [df["Open"].iloc[0]]
    for i in range(1, len(df)):
        ha_open.append((ha_open[-1] + df["HA_Close"].iloc[i-1]) / 2)
    df["HA_Open"], df["HA_Color"] = ha_open, np.where(df["HA_Close"] > ha_open, 1, -1)
    return df

def analyze_ticker_tf(symbol, config):
    try:
        df = yf.download(symbol, interval=config['int'], period=config['per'], progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        if df.empty or len(df) < 35: return None

        macd = ta.macd(df["Close"])
        df["Hist"], df["MACD"], df["Signal"] = macd["MACDh_12_26_9"], macd["MACD_12_26_9"], macd["MACDs_12_26_9"]
        df["RSI"] = ta.rsi(df["Close"], length=14)
        df = calculate_heikin_ashi(df)

        pos = "NEUTRO"
        for i in range(1, len(df)):
            h, ph, hc = df["Hist"].iloc[i], df["Hist"].iloc[i-1], df["HA_Color"].iloc[i]
            if pos == "LONG" and h < ph: pos = "NEUTRO"
            elif pos == "SHORT" and h > ph: pos = "NEUTRO"
            if pos == "NEUTRO":
                if hc == 1 and h > ph: pos = "LONG"
                elif hc == -1 and h < ph: pos = "SHORT"

        rsi_v = round(df["RSI"].iloc[-1], 1)
        rsi_s = "RSI↑" if rsi_v > 55 else "RSI↓" if rsi_v < 45 else "RSI="
        
        return {
            "sig": f"{'🟢' if pos=='LONG' else '🔴' if pos=='SHORT' else '⚪'} {pos} | {rsi_s}",
            "m0": "SOBRE 0" if df["MACD"].iloc[-1] > 0 else "BAJO 0",
            "h": "SUBIENDO" if df["Hist"].iloc[-1] > df["Hist"].iloc[-2] else "BAJANDO"
        }
    except: return None

# ─────────────────────────────────────────────
# INTERFAZ DE CONTROL
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("🎯 Stock Sniper Control")
    mode = st.radio("Modo:", ["Pool Institucional", "Inserción Manual"])
    min_liq = st.number_input("Liquidez Mínima USD:", 1, value=1000000)
    
    if mode == "Pool Institucional":
        available = list(MASTER_INFO.keys())
        b_size = st.selectbox("Lote:", [10, 20, 50], index=1)
        batches = [available[i:i+b_size] for i in range(0, len(available), b_size)]
        sel = st.selectbox("Seleccionar Lote:", range(len(batches)))
        targets = batches[sel] if batches else []
    else:
        custom = st.text_input("Tickers (ej: TSLA,AAPL):")
        targets = [x.strip().upper() for x in custom.split(",")] if custom else []

    acc = st.checkbox("Acumular", value=True)
    
    if st.button("🚀 INICIAR RADAR"):
        temp_results = []
        prog = st.progress(0)
        for idx, sym in enumerate(targets):
            prog.progress((idx+1)/len(targets), text=f"Analizando {sym}")
            
            # Chequeo de Liquidez Seguro
            check = yf.Ticker(sym).history(period="1d")
            if not check.empty:
                # CORRECCIÓN ValueError: Asegurar que real_vol sea un escalar
                real_vol = (check['Close'].iloc[-1] * check['Volume'].iloc[-1])
                if real_vol < min_liq: continue
                
                row = {
                    "Activo": sym, 
                    "Tipo": MASTER_INFO.get(sym, {}).get('T', 'MANUAL'),
                    "Sector": MASTER_INFO.get(sym, {}).get('S', 'CUSTOM')
                }
                
                valid_any = False
                for label, config in TIMEFRAMES.items():
                    res = analyze_ticker_tf(sym, config)
                    if res:
                        valid_any = True
                        row[f"{label} H.A./MACD"] = res["sig"]
                        row[f"{label} Hist."] = res["h"]
                        if label == "1D": row["1D Hist."] = res["h"]; row["1D MACD 0"] = res["m0"]
                    else:
                        row[f"{label} H.A./MACD"], row[f"{label} Hist."] = "-", "-"

                if valid_any:
                    bulls = sum(1 for tf in TIMEFRAMES if "LONG" in str(row.get(f"{tf} H.A./MACD","")))
                    bears = sum(1 for tf in TIMEFRAMES if "SHORT" in str(row.get(f"{tf} H.A./MACD","")))
                    row["VEREDICTO"] = "🔥 COMPRA" if bulls >= 5 and "SOBRE 0" in str(row.get("1D MACD 0","")) else "🩸 VENTA" if bears >= 5 and "BAJO 0" in str(row.get("1D MACD 0","")) else "⚖️ RANGO"
                    temp_results.append(row)
            time.sleep(0.1)

        if acc:
            current = {x["Activo"]: x for x in st.session_state["sniper_results"]}
            for r in temp_results: current[r["Activo"]] = r
            st.session_state["sniper_results"] = list(current.values())
        else:
            st.session_state["sniper_results"] = temp_results
        st.rerun()

    if st.button("Limpiar Memoria"):
        st.session_state["sniper_results"] = []; st.rerun()

# ─────────────────────────────────────────────
# FILTROS Y TABLA FINAL
# ─────────────────────────────────────────────
if st.session_state["sniper_results"]:
    df_f = pd.DataFrame(st.session_state["sniper_results"])
    
    st.sidebar.divider()
    st.sidebar.subheader("🧹 Filtros de Tabla")
    f_ver = st.sidebar.multiselect("Veredicto:", options=df_f["VEREDICTO"].unique(), default=df_f["VEREDICTO"].unique())
    f_sec = st.sidebar.multiselect("Sector:", options=df_f["Sector"].unique(), default=df_f["Sector"].unique())
    f_tip = st.sidebar.multiselect("Tipo:", options=df_f["Tipo"].unique(), default=df_f["Tipo"].unique())
    f_h1d = st.sidebar.multiselect("1D Hist:", options=df_f["1D Hist."].unique(), default=df_f["1D Hist."].unique())

    # Aplicación de Filtros
    mask = (df_f["VEREDICTO"].isin(f_ver)) & (df_f["Sector"].isin(f_sec)) & (df_f["Tipo"].isin(f_tip)) & (df_f["1D Hist."].isin(f_h1d))
    df_filtered = df_f[mask]

    def style_matrix(val):
        v = str(val).upper()
        if any(x in v for x in ["LONG", "SOBRE 0", "SUBIENDO", "COMPRA"]): return 'background-color: #d4edda; color: #155724;'
        if any(x in v for x in ["SHORT", "BAJO 0", "BAJANDO", "VENTA"]): return 'background-color: #f8d7da; color: #721c24;'
        return ''

    # Orden Institucional de Columnas
    prio = ["Activo", "Tipo", "Sector", "VEREDICTO", "1D Hist.", "1D H.A./MACD"]
    other = [c for c in df_filtered.columns if c not in prio]
    st.dataframe(df_filtered[prio + other].style.applymap(style_matrix), use_container_width=True, height=800)
else:
    st.info("👈 Configure y presione INICIAR RADAR.")
