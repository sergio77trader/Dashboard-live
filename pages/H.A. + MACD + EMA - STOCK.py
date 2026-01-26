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
st.set_page_config(layout="wide", page_title="SYSTEMATRADER | STOCKS V28.0 FULL")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 14px; }
    .stDataFrame { font-size: 12px; border: 1px solid #333; }
    h1 { color: #2962FF; font-weight: 800; }
    .stExpander { border: 2px solid #2962FF !important; border-radius: 8px !important; }
</style>
""", unsafe_allow_html=True)

if "sniper_results" not in st.session_state:
    st.session_state["sniper_results"] = []

TIMEFRAMES = {
    "1m": {"int": "1m", "per": "5d"}, "5m": {"int": "5m", "per": "30d"},
    "15m": {"int": "15m", "per": "30d"}, "30m": {"int": "30m", "per": "30d"},
    "1H": {"int": "60m", "per": "730d"}, "1D": {"int": "1d", "per": "max"}
}

# ─────────────────────────────────────────────
# POOL INSTITUCIONAL COMPLETO (150+ ACTIVOS)
# ─────────────────────────────────────────────
MASTER_INFO = {
    # --- ARGENTINA ADRs ---
    'GGAL': {'T': 'Acción ARG', 'S': 'Financiero'}, 'YPF': {'T': 'Acción ARG', 'S': 'Energía'},
    'BMA': {'T': 'Acción ARG', 'S': 'Financiero'}, 'PAMP': {'T': 'Acción ARG', 'S': 'Energía'},
    'TGS': {'T': 'Acción ARG', 'S': 'Energía'}, 'CEPU': {'T': 'Acción ARG', 'S': 'Energía'},
    'EDN': {'T': 'Acción ARG', 'S': 'Energía'}, 'BFR': {'T': 'Acción ARG', 'S': 'Financiero'},
    'SUPV': {'T': 'Acción ARG', 'S': 'Financiero'}, 'CRESY': {'T': 'Acción ARG', 'S': 'Agro'},
    'IRS': {'T': 'Acción ARG', 'S': 'Inmuebles'}, 'TEO': {'T': 'Acción ARG', 'S': 'Telecom'},
    'LOMA': {'T': 'Acción ARG', 'S': 'Construcción'}, 'VIST': {'T': 'Acción ARG', 'S': 'Energía'},
    'GLOB': {'T': 'Acción ARG', 'S': 'Tech'}, 'MELI': {'T': 'Acción ARG', 'S': 'E-Commerce'},
    'TX': {'T': 'Acción ARG', 'S': 'Industrial'}, 'DESP': {'T': 'Acción ARG', 'S': 'Turismo'},
    'BIOX': {'T': 'Acción ARG', 'S': 'Agro'},

    # --- CEDEARS: TECNOLOGÍA & SEMIS ---
    'AAPL': {'T': 'CEDEAR', 'S': 'Tech'}, 'MSFT': {'T': 'CEDEAR', 'S': 'Tech'},
    'NVDA': {'T': 'CEDEAR', 'S': 'Semis'}, 'AMD': {'T': 'CEDEAR', 'S': 'Semis'},
    'GOOGL': {'T': 'CEDEAR', 'S': 'Tech'}, 'AMZN': {'T': 'CEDEAR', 'S': 'E-Commerce'},
    'META': {'T': 'CEDEAR', 'S': 'Tech'}, 'TSLA': {'T': 'CEDEAR', 'S': 'Auto'},
    'NFLX': {'T': 'CEDEAR', 'S': 'Consumo'}, 'INTC': {'T': 'CEDEAR', 'S': 'Semis'},
    'CRM': {'T': 'CEDEAR', 'S': 'SaaS'}, 'ORCL': {'T': 'CEDEAR', 'S': 'SaaS'},
    'ADBE': {'T': 'CEDEAR', 'S': 'SaaS'}, 'AVGO': {'T': 'CEDEAR', 'S': 'Semis'},
    'ASML': {'T': 'CEDEAR', 'S': 'Semis'}, 'SHOP': {'T': 'CEDEAR', 'S': 'Retail'},
    'SPOT': {'T': 'CEDEAR', 'S': 'Music'}, 'PLTR': {'T': 'CEDEAR', 'S': 'Big Data'},
    'SNOW': {'T': 'CEDEAR', 'S': 'Cloud'}, 'UBER': {'T': 'CEDEAR', 'S': 'Transporte'},
    'SMCI': {'T': 'CEDEAR', 'S': 'Hardware'}, 'TSM': {'T': 'CEDEAR', 'S': 'Semis'},
    'ARM': {'T': 'CEDEAR', 'S': 'Semis'}, 'HPQ': {'T': 'CEDEAR', 'S': 'Hardware'},
    'DELL': {'T': 'CEDEAR', 'S': 'Hardware'}, 'CSCO': {'T': 'CEDEAR', 'S': 'Telecom'},

    # --- CEDEARS: FINANZAS & PAGOS ---
    'JPM': {'T': 'CEDEAR', 'S': 'Financiero'}, 'BAC': {'T': 'CEDEAR', 'S': 'Financiero'},
    'C': {'T': 'CEDEAR', 'S': 'Financiero'}, 'GS': {'T': 'CEDEAR', 'S': 'Financiero'},
    'MS': {'T': 'CEDEAR', 'S': 'Financiero'}, 'V': {'T': 'CEDEAR', 'S': 'Pagos'},
    'MA': {'T': 'CEDEAR', 'S': 'Pagos'}, 'AXP': {'T': 'CEDEAR', 'S': 'Pagos'},
    'PYPL': {'T': 'CEDEAR', 'S': 'Pagos'}, 'SQ': {'T': 'CEDEAR', 'S': 'Pagos'},
    'COIN': {'T': 'CEDEAR', 'S': 'Crypto'}, 'BRK-B': {'T': 'CEDEAR', 'S': 'Inversiones'},
    'NU': {'T': 'CEDEAR', 'S': 'Fintech'}, 'BLK': {'T': 'CEDEAR', 'S': 'Inversiones'},

    # --- CEDEARS: CONSUMO & INDUSTRIAL ---
    'KO': {'T': 'CEDEAR', 'S': 'Consumo'}, 'PEP': {'T': 'CEDEAR', 'S': 'Consumo'},
    'MCD': {'T': 'CEDEAR', 'S': 'Consumo'}, 'SBUX': {'T': 'CEDEAR', 'S': 'Consumo'},
    'DIS': {'T': 'CEDEAR', 'S': 'Entretenimiento'}, 'WMT': {'T': 'CEDEAR', 'S': 'Retail'},
    'COST': {'T': 'CEDEAR', 'S': 'Retail'}, 'TGT': {'T': 'CEDEAR', 'S': 'Retail'},
    'HD': {'T': 'CEDEAR', 'S': 'Construcción'}, 'NKE': {'T': 'CEDEAR', 'S': 'Consumo'},
    'PG': {'T': 'CEDEAR', 'S': 'Consumo'}, 'PM': {'T': 'CEDEAR', 'S': 'Consumo'},
    'CAT': {'T': 'CEDEAR', 'S': 'Industrial'}, 'DE': {'T': 'CEDEAR', 'S': 'Industrial'},
    'GE': {'T': 'CEDEAR', 'S': 'Industrial'}, 'BA': {'T': 'CEDEAR', 'S': 'Industrial'},
    'MMM': {'T': 'CEDEAR', 'S': 'Industrial'}, 'LMT': {'T': 'CEDEAR', 'S': 'Defensa'},

    # --- CEDEARS: ENERGÍA & MINERÍA ---
    'XOM': {'T': 'CEDEAR', 'S': 'Energía'}, 'CVX': {'T': 'CEDEAR', 'S': 'Energía'},
    'SLB': {'T': 'CEDEAR', 'S': 'Energía'}, 'OXY': {'T': 'CEDEAR', 'S': 'Energía'},
    'PBR': {'T': 'CEDEAR', 'S': 'Energía'}, 'GOLD': {'T': 'CEDEAR', 'S': 'Minería'},
    'NEM': {'T': 'CEDEAR', 'S': 'Minería'}, 'VALE': {'T': 'CEDEAR', 'S': 'Minería'},
    'RIO': {'T': 'CEDEAR', 'S': 'Minería'}, 'BHP': {'T': 'CEDEAR', 'S': 'Minería'},
    'FCX': {'T': 'CEDEAR', 'S': 'Minería'}, 'HMY': {'T': 'CEDEAR', 'S': 'Minería'},

    # --- CEDEARS: SALUD & OTROS ---
    'JNJ': {'T': 'CEDEAR', 'S': 'Salud'}, 'PFE': {'T': 'CEDEAR', 'S': 'Salud'},
    'MRK': {'T': 'CEDEAR', 'S': 'Salud'}, 'ABBV': {'T': 'CEDEAR', 'S': 'Salud'},
    'LLY': {'T': 'CEDEAR', 'S': 'Salud'}, 'UNH': {'T': 'CEDEAR', 'S': 'Salud'},
    'NVO': {'T': 'CEDEAR', 'S': 'Salud'}, 'VZ': {'T': 'CEDEAR', 'S': 'Telecom'},
    'T': {'T': 'CEDEAR', 'S': 'Telecom'}, 'TMUS': {'T': 'CEDEAR', 'S': 'Telecom'},
    'BABA': {'T': 'CEDEAR', 'S': 'China'}, 'JD': {'T': 'CEDEAR', 'S': 'China'},
    'BIDU': {'T': 'CEDEAR', 'S': 'China'}, 'NIO': {'T': 'CEDEAR', 'S': 'China'},

    # --- ETFs (CEDEARs) ---
    'SPY': {'T': 'CEDEAR ETF', 'S': 'Índice'}, 'QQQ': {'T': 'CEDEAR ETF', 'S': 'Índice'},
    'DIA': {'T': 'CEDEAR ETF', 'S': 'Índice'}, 'IWM': {'T': 'CEDEAR ETF', 'S': 'Índice'},
    'EEM': {'T': 'CEDEAR ETF', 'S': 'Emergentes'}, 'EWZ': {'T': 'CEDEAR ETF', 'S': 'Brasil'},
    'XLE': {'T': 'CEDEAR ETF', 'S': 'Energía'}, 'XLF': {'T': 'CEDEAR ETF', 'S': 'Financiero'},
    'XLK': {'T': 'CEDEAR ETF', 'S': 'Tech'}, 'ARKK': {'T': 'CEDEAR ETF', 'S': 'Innovación'},
    'GLD': {'T': 'CEDEAR ETF', 'S': 'Oro'}, 'SLV': {'T': 'CEDEAR ETF', 'S': 'Plata'}
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

def analyze_stock_tf(symbol, label, config):
    try:
        df = yf.download(symbol, interval=config['int'], period=config['per'], progress=False, auto_adjust=True)
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
            "price": f"{df['Close'].iloc[-1]:.2f}"
        }
    except: return None

def scan_stocks(targets, acc):
    results = []
    prog = st.progress(0)
    for idx, sym in enumerate(targets):
        prog.progress((idx+1)/len(targets), text=f"Sincronizando {sym}")
        try:
            row = {"Activo": sym, "Tipo": MASTER_INFO.get(sym, {}).get('T', 'MANUAL'), "Sector": MASTER_INFO.get(sym, {}).get('S', 'CUSTOM')}
            valid = False
            for label, config in TIMEFRAMES.items():
                res = analyze_stock_tf(sym, label, config)
                if res:
                    valid = True
                    row[f"{label} H.A./MACD"] = res["sig"]
                    row[f"{label} Hist."] = res["h"]
                    row["Precio"] = res["price"]
                    if label == "1D": row["1D MACD 0"] = res["m0"]
                else:
                    row[f"{label} H.A./MACD"], row[f"{label} Hist."] = "-", "-"
            
            if valid:
                bulls = sum(1 for tf in TIMEFRAMES if "LONG" in str(row.get(f"{tf} H.A./MACD","")))
                bears = sum(1 for tf in TIMEFRAMES if "SHORT" in str(row.get(f"{tf} H.A./MACD","")))
                bias_1d = str(row.get("1D MACD 0", ""))
                row["VEREDICTO"] = "🔥 COMPRA" if bulls >= 5 and "SOBRE 0" in bias_1d else "🩸 VENTA" if bears >= 5 and "BAJO 0" in bias_1d else "⚖️ RANGO"
                results.append(row)
            time.sleep(0.1)
        except: continue
    prog.empty()
    if acc:
        curr = {x["Activo"]: x for x in st.session_state["sniper_results"]}
        for r in results: curr[r["Activo"]] = r
        return list(curr.values())
    return results

# ─────────────────────────────────────────────
# INTERFAZ Y FILTROS
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("🎯 Stock Sniper Control")
    mode = st.radio("Modo:", ["Lotes Institucionales", "Escribir Tickers"])
    
    if mode == "Lotes Institucionales":
        all_t = sorted(list(MASTER_INFO.keys()))
        b_size = st.selectbox("Lote de:", [10, 20, 50, 100], index=2)
        batches = [all_t[i:i+b_size] for i in range(0, len(all_t), b_size)]
        sel = st.selectbox("Seleccionar Lote:", range(len(batches)), format_func=lambda x: f"Lote {x} ({len(batches[x])} activos)")
        targets = batches[sel] if batches else []
    else:
        custom = st.text_input("Escriba Tickers (ej: NVDA,GGAL,TSLA):")
        targets = [x.strip().upper() for x in custom.split(",")] if custom else []

    acc = st.checkbox("Acumular Resultados", value=True)
    if st.button("🚀 INICIAR ESCANEO", type="primary"):
        st.session_state["sniper_results"] = scan_stocks(targets, acc)
        st.rerun()

    st.divider()
    if st.session_state["sniper_results"]:
        df_temp = pd.DataFrame(st.session_state["sniper_results"])
        f_ver = st.multiselect("Veredicto:", options=df_temp["VEREDICTO"].unique(), default=df_temp["VEREDICTO"].unique())
        f_sec = st.multiselect("Sector:", options=df_temp["Sector"].unique(), default=df_temp["Sector"].unique())
        f_tip = st.multiselect("Tipo:", options=df_temp["Tipo"].unique(), default=df_temp["Tipo"].unique())

    if st.button("Limpiar Memoria"):
        st.session_state["sniper_results"] = []; st.rerun()

# ─────────────────────────────────────────────
# TABLA FINAL
# ─────────────────────────────────────────────
if st.session_state["sniper_results"]:
    df_f = pd.DataFrame(st.session_state["sniper_results"])
    df_filtered = df_f[(df_f["VEREDICTO"].isin(f_ver)) & (df_f["Sector"].isin(f_sec)) & (df_f["Tipo"].isin(f_tip))]
    
    def style_matrix(val):
        v = str(val).upper()
        if any(x in v for x in ["LONG", "SOBRE 0", "SUBIENDO", "COMPRA"]): return 'background-color: #d4edda; color: #155724;'
        if any(x in v for x in ["SHORT", "BAJO 0", "BAJANDO", "VENTA"]): return 'background-color: #f8d7da; color: #721c24;'
        return ''

    prio = ["Activo", "Tipo", "Sector", "VEREDICTO", "Precio"]
    other = [c for c in df_filtered.columns if c not in prio]
    st.dataframe(df_filtered[prio + other].style.applymap(style_matrix), use_container_width=True, height=800)
else:
    st.info("👈 Seleccione un lote y presione INICIAR ESCANEO.")
