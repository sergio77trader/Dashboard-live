import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURACIÓN DEL SISTEMA
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SYSTEMATRADER | STOCKS V27.0")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 14px; }
    .stDataFrame { font-size: 12px; }
    h1 { color: #2962FF; font-weight: 800; }
    .stExpander { border: 2px solid #2962FF !important; }
</style>
""", unsafe_allow_html=True)

if "sniper_results" not in st.session_state:
    st.session_state["sniper_results"] = []

# ─────────────────────────────────────────────
# BASE DE DATOS INSTITUCIONAL (150+ ACTIVOS)
# ─────────────────────────────────────────────
# Curaduría de ADRs y CEDEARs con liquidez estructural
MASTER_INFO = {
    # ARGENTINA (ADRs NYSE/NASDAQ)
    'GGAL': {'T': 'ADR', 'S': 'Financiero'}, 'YPF': {'T': 'ADR', 'S': 'Energía'},
    'BMA': {'T': 'ADR', 'S': 'Financiero'}, 'PAMP': {'T': 'ADR', 'S': 'Energía'},
    'TGS': {'T': 'ADR', 'S': 'Energía'}, 'CEPU': {'T': 'ADR', 'S': 'Energía'},
    'EDN': {'T': 'ADR', 'S': 'Energía'}, 'BFR': {'T': 'ADR', 'S': 'Financiero'},
    'SUPV': {'T': 'ADR', 'S': 'Financiero'}, 'CRESY': {'T': 'ADR', 'S': 'Agro'},
    'IRS': {'T': 'ADR', 'S': 'Inmuebles'}, 'TEO': {'T': 'ADR', 'S': 'Telecom'},
    'LOMA': {'T': 'ADR', 'S': 'Construcción'}, 'VIST': {'T': 'ADR', 'S': 'Energía'},
    'GLOB': {'T': 'ADR', 'S': 'Tech'}, 'MELI': {'T': 'ADR', 'S': 'E-Commerce'},
    'DESP': {'T': 'ADR', 'S': 'Turismo'}, 'TX': {'T': 'ADR', 'S': 'Siderurgia'},
    
    # CEDEARS - TECH & SEMIS
    'AAPL': {'T': 'CEDEAR', 'S': 'Tech'}, 'MSFT': {'T': 'CEDEAR', 'S': 'Tech'},
    'NVDA': {'T': 'CEDEAR', 'S': 'Semis'}, 'AMD': {'T': 'CEDEAR', 'S': 'Semis'},
    'GOOGL': {'T': 'CEDEAR', 'S': 'Tech'}, 'AMZN': {'T': 'CEDEAR', 'S': 'Retail'},
    'META': {'T': 'CEDEAR', 'S': 'Tech'}, 'TSLA': {'T': 'CEDEAR', 'S': 'Auto'},
    'NFLX': {'T': 'CEDEAR', 'S': 'Entretenimiento'}, 'INTC': {'T': 'CEDEAR', 'S': 'Semis'},
    'CRM': {'T': 'CEDEAR', 'S': 'SaaS'}, 'ORCL': {'T': 'CEDEAR', 'S': 'SaaS'},
    'ADBE': {'T': 'CEDEAR', 'S': 'SaaS'}, 'AVGO': {'T': 'CEDEAR', 'S': 'Semis'},
    'ASML': {'T': 'CEDEAR', 'S': 'Semis'}, 'SHOP': {'T': 'CEDEAR', 'S': 'Retail'},
    'UBER': {'T': 'CEDEAR', 'S': 'Transporte'}, 'PLTR': {'T': 'CEDEAR', 'S': 'Big Data'},
    'SNOW': {'T': 'CEDEAR', 'S': 'Cloud'}, 'SPOT': {'T': 'CEDEAR', 'S': 'Music'},

    # CEDEARS - FINANCIERO & CONSUMO
    'JPM': {'T': 'CEDEAR', 'S': 'Banco'}, 'BAC': {'T': 'CEDEAR', 'S': 'Banco'},
    'C': {'T': 'CEDEAR', 'S': 'Banco'}, 'GS': {'T': 'CEDEAR', 'S': 'Banco'},
    'V': {'T': 'CEDEAR', 'S': 'Pagos'}, 'MA': {'T': 'CEDEAR', 'S': 'Pagos'},
    'AXP': {'T': 'CEDEAR', 'S': 'Pagos'}, 'PYPL': {'T': 'CEDEAR', 'S': 'Fintech'},
    'KO': {'T': 'CEDEAR', 'S': 'Consumo'}, 'PEP': {'T': 'CEDEAR', 'S': 'Consumo'},
    'MCD': {'T': 'CEDEAR', 'S': 'Consumo'}, 'SBUX': {'T': 'CEDEAR', 'S': 'Consumo'},
    'DIS': {'T': 'CEDEAR', 'S': 'Entretenimiento'}, 'WMT': {'T': 'CEDEAR', 'S': 'Retail'},
    'COST': {'T': 'CEDEAR', 'S': 'Retail'}, 'PG': {'T': 'CEDEAR', 'S': 'Consumo'},
    'NKE': {'T': 'CEDEAR', 'S': 'Consumo'}, 'CAT': {'T': 'CEDEAR', 'S': 'Industrial'},
    
    # ENERGÍA & MINERÍA
    'XOM': {'T': 'CEDEAR', 'S': 'Petróleo'}, 'CVX': {'T': 'CEDEAR', 'S': 'Petróleo'},
    'PBR': {'T': 'CEDEAR', 'S': 'Petróleo'}, 'BP': {'T': 'CEDEAR', 'S': 'Petróleo'},
    'GOLD': {'T': 'CEDEAR', 'S': 'Oro'}, 'NEM': {'T': 'CEDEAR', 'S': 'Oro'},
    'VALE': {'T': 'CEDEAR', 'S': 'Hierro'}, 'RIO': {'T': 'CEDEAR', 'S': 'Minería'},
    'HMY': {'T': 'CEDEAR', 'S': 'Oro'}, 'AUY': {'T': 'CEDEAR', 'S': 'Oro'},

    # ETFs
    'SPY': {'T': 'ETF', 'S': 'S&P500'}, 'QQQ': {'T': 'ETF', 'S': 'Nasdaq'},
    'DIA': {'T': 'ETF', 'S': 'DowJones'}, 'IWM': {'T': 'ETF', 'S': 'SmallCaps'},
    'EEM': {'T': 'ETF', 'S': 'Emergentes'}, 'EWZ': {'T': 'ETF', 'S': 'Brasil'},
    'ARKK': {'T': 'ETF', 'S': 'Innovación'}, 'XLF': {'T': 'ETF', 'S': 'Financiero'},
    'XLK': {'T': 'ETF', 'S': 'Tech'}, 'GLD': {'T': 'ETF', 'S': 'Oro'}
}

TIMEFRAMES = {
    "1m": {"int": "1m", "per": "5d"}, "5m": {"int": "5m", "per": "30d"},
    "15m": {"int": "15m", "per": "30d"}, "30m": {"int": "30m", "per": "30d"},
    "1H": {"int": "60m", "per": "730d"}, "1D": {"int": "1d", "per": "max"}
}

# ─────────────────────────────────────────────
# MOTOR DE ANÁLISIS
# ─────────────────────────────────────────────
def calculate_heikin_ashi(df):
    df = df.copy()
    df["HA_Close"] = (df["Open"] + df["High"] + df["Low"] + df["Close"]) / 4
    ha_open = [df["Open"].iloc[0]]
    for i in range(1, len(df)):
        ha_open.append((ha_open[-1] + df["HA_Close"].iloc[i-1]) / 2)
    df["HA_Open"], df["HA_Color"] = ha_open, np.where(df["HA_Close"] > ha_open, 1, -1)
    return df

def analyze_stock_tf(symbol, config):
    try:
        df = yf.download(symbol, interval=config['int'], period=config['per'], progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        if df.empty or len(df) < 35: return None

        macd = ta.macd(df["Close"])
        df["Hist"], df["MACD"], df["Signal"] = macd["MACDh_12_26_9"], macd["MACD_12_26_9"], macd["MACDs_12_26_9"]
        df["RSI"] = ta.rsi(df["Close"], length=14)
        df = calculate_heikin_ashi(df)

        position = "NEUTRO"
        for i in range(1, len(df)):
            h, ph, hc = df["Hist"].iloc[i], df["Hist"].iloc[i-1], df["HA_Color"].iloc[i]
            if position == "LONG" and h < ph: position = "NEUTRO"
            elif position == "SHORT" and h > ph: position = "NEUTRO"
            if position == "NEUTRO":
                if hc == 1 and h > ph: position = "LONG"
                elif hc == -1 and h < ph: position = "SHORT"

        rsi_v = round(df["RSI"].iloc[-1], 1)
        rsi_s = "RSI↑" if rsi_v > 55 else "RSI↓" if rsi_v < 45 else "RSI="
        
        return {
            "sig": f"{'🟢' if position=='LONG' else '🔴' if position=='SHORT' else '⚪'} {position} | {rsi_s}",
            "m0": "SOBRE 0" if df["MACD"].iloc[-1] > 0 else "BAJO 0",
            "h": "SUBIENDO" if df["Hist"].iloc[-1] > df["Hist"].iloc[-2] else "BAJANDO",
            "vol_usd": df["Close"].iloc[-1] * df["Volume"].iloc[-1]
        }
    except: return None

# ─────────────────────────────────────────────
# INTERFAZ Y CONTROL
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("🎯 Stock Sniper ARG/US")
    mode = st.radio("Modo de Análisis:", ["Pool Institucional", "Inserción Manual"])
    
    # Filtro de Liquidez Automático
    min_liq = st.number_input("Liquidez Mínima USD (Subyacente):", 1000000, step=1000000)
    
    if mode == "Pool Institucional":
        f_tipo = st.multiselect("Tipos:", ["ADR", "CEDEAR", "ETF"], default=["ADR", "CEDEAR", "ETF"])
        available = [k for k, v in MASTER_INFO.items() if v['T'] in f_tipo]
        b_size = st.selectbox("Lote:", [10, 20, 50], index=1)
        batches = [available[i:i+b_size] for i in range(0, len(available), b_size)]
        sel = st.selectbox("Seleccionar Lote:", range(len(batches)))
        targets = batches[sel] if batches else []
    else:
        custom = st.text_input("Escriba Tickers (ej: AAPL,GGAL,TSLA):")
        targets = [x.strip().upper() for x in custom.split(",")] if custom else []

    acc = st.checkbox("Acumular Resultados", value=True)
    
    if st.button("🚀 INICIAR RADAR", type="primary"):
        ex_results = []
        prog = st.progress(0)
        for idx, sym in enumerate(targets):
            prog.progress((idx+1)/len(targets), text=f"Analizando {sym}...")
            # 1. Chequeo de Liquidez Rápido
            check_df = yf.download(sym, period="1d", progress=False)
            if not check_df.empty:
                real_vol = (check_df['Close'] * check_df['Volume']).iloc[-1]
                if real_vol < min_liq: continue # Gatekeeper
                
                row = {"Activo": sym, "Tipo": MASTER_INFO.get(sym, {}).get('T', 'Manual'), "Sector": MASTER_INFO.get(sym, {}).get('S', 'Custom')}
                valid = False
                for label, config in TIMEFRAMES.items():
                    res = analyze_stock_tf(sym, config)
                    if res:
                        valid = True
                        row[f"{label} H.A./MACD"], row[f"{label} Hist."] = res["sig"], res["h"]
                        if label == "1D": row["1D MACD 0"] = res["m0"]
                    else:
                        row[f"{label} H.A./MACD"], row[f"{label} Hist."] = "-", "-"
                
                if valid:
                    bulls = sum(1 for tf in TIMEFRAMES if "LONG" in str(row.get(f"{tf} H.A./MACD","")))
                    bears = sum(1 for tf in TIMEFRAMES if "SHORT" in str(row.get(f"{tf} H.A./MACD","")))
                    bias_1d = str(row.get("1D MACD 0", ""))
                    if bulls >= 5 and "SOBRE 0" in bias_1d: row["VEREDICTO"] = "🔥 COMPRA"
                    elif bears >= 5 and "BAJO 0" in bias_1d: row["VEREDICTO"] = "🩸 VENTA"
                    else: row["VEREDICTO"] = "⚖️ RANGO"
                    ex_results.append(row)
            time.sleep(0.2)
        
        if acc:
            current = {x["Activo"]: x for x in st.session_state["sniper_results"]}
            for r in ex_results: current[r["Activo"]] = r
            st.session_state["sniper_results"] = list(current.values())
        else:
            st.session_state["sniper_results"] = ex_results
        st.rerun()

    if st.button("Limpiar Memoria"):
        st.session_state["sniper_results"] = []; st.rerun()

# ─────────────────────────────────────────────
# TABLA FINAL
# ─────────────────────────────────────────────
if st.session_state["sniper_results"]:
    df_f = pd.DataFrame(st.session_state["sniper_results"])
    
    # Post-Filtros Dinámicos
    with st.expander("🧹 Filtros Avanzados"):
        f_ver = st.multiselect("Veredicto:", options=df_f["VEREDICTO"].unique(), default=df_f["VEREDICTO"].unique())
        f_sec = st.multiselect("Sector:", options=df_f["Sector"].unique(), default=df_f["Sector"].unique())
        f_hi = st.multiselect("1D Hist:", options=["SUBIENDO", "BAJANDO"], default=["SUBIENDO", "BAJANDO"])

    df_filtered = df_f[(df_f["VEREDICTO"].isin(f_ver)) & (df_f["Sector"].isin(f_sec)) & (df_f["1D Hist."].isin(f_hi))]

    def style_matrix(val):
        v = str(val).upper()
        if any(x in v for x in ["LONG", "SOBRE 0", "SUBIENDO", "COMPRA"]): return 'background-color: #d4edda; color: #155724;'
        if any(x in v for x in ["SHORT", "BAJO 0", "BAJANDO", "VENTA"]): return 'background-color: #f8d7da; color: #721c24;'
        return ''

    prio = ["Activo", "Tipo", "Sector", "VEREDICTO", "1D H.A./MACD", "1D Hist."]
    st.dataframe(df_filtered[prio + [c for c in df_filtered.columns if c not in prio]].style.applymap(style_matrix), use_container_width=True, height=800)
else:
    st.info("Sistema listo. Seleccione un modo de análisis.")
