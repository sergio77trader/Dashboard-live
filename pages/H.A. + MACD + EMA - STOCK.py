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
st.set_page_config(layout="wide", page_title="SYSTEMATRADER | STOCKS V36.0")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 14px; }
    .stDataFrame { font-size: 12px; border: 1px solid #333; }
    h1 { color: #2962FF; font-weight: 800; border-bottom: 2px solid #2962FF; }
    .stExpander { border: 2px solid #2962FF !important; border-radius: 8px !important; }
</style>
""", unsafe_allow_html=True)

if "sniper_results" not in st.session_state:
    st.session_state["sniper_results"] = []

# JERARQUÍA MAESTRA: 4 FRACTALES SELECCIONADOS
TIMEFRAMES = {
    "5m": {"int": "5m", "per": "30d"},
    "15m": {"int": "15m", "per": "30d"},
    "1H": {"int": "60m", "per": "730d"},
    "1D": {"int": "1d", "per": "max"}
}

# ─────────────────────────────────────────────
# BÓVEDA DE ACTIVOS (172 ACTIVOS VERIFICADOS)
# ─────────────────────────────────────────────
MASTER_INFO = {
    # --- ARGENTINA ADRs (19) ---
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

    # --- CEDEARS: TECH, SaaS & BIG DATA (35) ---
    'AAPL': {'T': 'CEDEAR', 'S': 'Tech'}, 'MSFT': {'T': 'CEDEAR', 'S': 'Tech'},
    'GOOGL': {'T': 'CEDEAR', 'S': 'Tech'}, 'AMZN': {'T': 'CEDEAR', 'S': 'E-Commerce'},
    'META': {'T': 'CEDEAR', 'S': 'Tech'}, 'TSLA': {'T': 'CEDEAR', 'S': 'Auto'},
    'NFLX': {'T': 'CEDEAR', 'S': 'Consumo'}, 'CRM': {'T': 'CEDEAR', 'S': 'SaaS'},
    'ORCL': {'T': 'CEDEAR', 'S': 'SaaS'}, 'ADBE': {'T': 'CEDEAR', 'S': 'SaaS'},
    'SAP': {'T': 'CEDEAR', 'S': 'SaaS'}, 'INTU': {'T': 'CEDEAR', 'S': 'SaaS'},
    'NOW': {'T': 'CEDEAR', 'S': 'SaaS'}, 'IBM': {'T': 'CEDEAR', 'S': 'Tech'},
    'PLTR': {'T': 'CEDEAR', 'S': 'Big Data'}, 'SNOW': {'T': 'CEDEAR', 'S': 'Cloud'},
    'SHOP': {'T': 'CEDEAR', 'S': 'Retail'}, 'SPOT': {'T': 'CEDEAR', 'S': 'Music'},
    'UBER': {'T': 'CEDEAR', 'S': 'Transporte'}, 'ABNB': {'T': 'CEDEAR', 'S': 'Turismo'},
    'PANW': {'T': 'CEDEAR', 'S': 'Ciberseguridad'}, 'CRWD': {'T': 'CEDEAR', 'S': 'Ciberseguridad'},
    'DDOG': {'T': 'CEDEAR', 'S': 'Cloud'}, 'MDB': {'T': 'CEDEAR', 'S': 'Cloud'},
    'SQ': {'T': 'CEDEAR', 'S': 'Fintech'}, 'PYPL': {'T': 'CEDEAR', 'S': 'Fintech'},
    'DOCU': {'T': 'CEDEAR', 'S': 'SaaS'}, 'NET': {'T': 'CEDEAR', 'S': 'Ciberseguridad'},
    'TEAM': {'T': 'CEDEAR', 'S': 'SaaS'}, 'ZS': {'T': 'CEDEAR', 'S': 'Ciberseguridad'},
    'OKTA': {'T': 'CEDEAR', 'S': 'Ciberseguridad'}, 'ZK': {'T': 'CEDEAR', 'S': 'Tech'},
    'FSLY': {'T': 'CEDEAR', 'S': 'Tech'}, 'GDDY': {'T': 'CEDEAR', 'S': 'Tech'},
    'SE': {'T': 'CEDEAR', 'S': 'E-Commerce'},

    # --- CEDEARS: SEMICONDUCTORES (15) ---
    'NVDA': {'T': 'CEDEAR', 'S': 'Semis'}, 'AMD': {'T': 'CEDEAR', 'S': 'Semis'},
    'INTC': {'T': 'CEDEAR', 'S': 'Semis'}, 'AVGO': {'T': 'CEDEAR', 'S': 'Semis'},
    'TXN': {'T': 'CEDEAR', 'S': 'Semis'}, 'MU': {'T': 'CEDEAR', 'S': 'Semis'},
    'ADI': {'T': 'CEDEAR', 'S': 'Semis'}, 'AMAT': {'T': 'CEDEAR', 'S': 'Semis'},
    'ARM': {'T': 'CEDEAR', 'S': 'Semis'}, 'SMCI': {'T': 'CEDEAR', 'S': 'Hardware'},
    'TSM': {'T': 'CEDEAR', 'S': 'Semis'}, 'ASML': {'T': 'CEDEAR', 'S': 'Semis'},
    'LRCX': {'T': 'CEDEAR', 'S': 'Semis'}, 'QCOM': {'T': 'CEDEAR', 'S': 'Semis'},
    'KLAC': {'T': 'CEDEAR', 'S': 'Semis'},

    # --- CEDEARS: FINANZAS & PAGOS (20) ---
    'JPM': {'T': 'CEDEAR', 'S': 'Financiero'}, 'BAC': {'T': 'CEDEAR', 'S': 'Financiero'},
    'C': {'T': 'CEDEAR', 'S': 'Financiero'}, 'WFC': {'T': 'CEDEAR', 'S': 'Financiero'},
    'GS': {'T': 'CEDEAR', 'S': 'Financiero'}, 'MS': {'T': 'CEDEAR', 'S': 'Financiero'},
    'V': {'T': 'CEDEAR', 'S': 'Pagos'}, 'MA': {'T': 'CEDEAR', 'S': 'Pagos'},
    'AXP': {'T': 'CEDEAR', 'S': 'Pagos'}, 'BRK-B': {'T': 'CEDEAR', 'S': 'Inversiones'},
    'BLK': {'T': 'CEDEAR', 'S': 'Inversiones'}, 'NU': {'T': 'CEDEAR', 'S': 'Fintech'},
    'HSBC': {'T': 'CEDEAR', 'S': 'Financiero'}, 'SCHW': {'T': 'CEDEAR', 'S': 'Financiero'},
    'USB': {'T': 'CEDEAR', 'S': 'Financiero'}, 'PNC': {'T': 'CEDEAR', 'S': 'Financiero'},
    'DFS': {'T': 'CEDEAR', 'S': 'Financiero'}, 'TROW': {'T': 'CEDEAR', 'S': 'Inversiones'},
    'BK': {'T': 'CEDEAR', 'S': 'Financiero'}, 'AIG': {'T': 'CEDEAR', 'S': 'Seguros'},

    # --- CEDEARS: CONSUMO & RETAIL (25) ---
    'KO': {'T': 'CEDEAR', 'S': 'Consumo'}, 'PEP': {'T': 'CEDEAR', 'S': 'Consumo'},
    'MCD': {'T': 'CEDEAR', 'S': 'Consumo'}, 'SBUX': {'T': 'CEDEAR', 'S': 'Consumo'},
    'DIS': {'T': 'CEDEAR', 'S': 'Entretenimiento'}, 'NKE': {'T': 'CEDEAR', 'S': 'Consumo'},
    'WMT': {'T': 'CEDEAR', 'S': 'Retail'}, 'COST': {'T': 'CEDEAR', 'S': 'Retail'},
    'TGT': {'T': 'CEDEAR', 'S': 'Retail'}, 'HD': {'T': 'CEDEAR', 'S': 'Construcción'},
    'LOW': {'T': 'CEDEAR', 'S': 'Construcción'}, 'PG': {'T': 'CEDEAR', 'S': 'Consumo'},
    'CL': {'T': 'CEDEAR', 'S': 'Consumo'}, 'KMB': {'T': 'CEDEAR', 'S': 'Consumo'},
    'EL': {'T': 'CEDEAR', 'S': 'Consumo'}, 'MO': {'T': 'CEDEAR', 'S': 'Consumo'},
    'PM': {'T': 'CEDEAR', 'S': 'Consumo'}, 'MAR': {'T': 'CEDEAR', 'S': 'Turismo'},
    'BKNG': {'T': 'CEDEAR', 'S': 'Turismo'}, 'AZO': {'T': 'CEDEAR', 'S': 'Retail'},
    'ORLY': {'T': 'CEDEAR', 'S': 'Retail'}, 'TJX': {'T': 'CEDEAR', 'S': 'Retail'},
    'CVS': {'T': 'CEDEAR', 'S': 'Salud Retail'}, 'LULU': {'T': 'CEDEAR', 'S': 'Consumo'},
    'KR': {'T': 'CEDEAR', 'S': 'Retail'},

    # --- CEDEARS: INDUSTRIAL, ENERGÍA & DEFENSA (25) ---
    'CAT': {'T': 'CEDEAR', 'S': 'Industrial'}, 'DE': {'T': 'CEDEAR', 'S': 'Industrial'},
    'GE': {'T': 'CEDEAR', 'S': 'Industrial'}, 'BA': {'T': 'CEDEAR', 'S': 'Aeroespacial'},
    'HON': {'T': 'CEDEAR', 'S': 'Industrial'}, 'LMT': {'T': 'CEDEAR', 'S': 'Defensa'},
    'NOC': {'T': 'CEDEAR', 'S': 'Defensa'}, 'RTX': {'T': 'CEDEAR', 'S': 'Defensa'},
    'XOM': {'T': 'CEDEAR', 'S': 'Energía'}, 'CVX': {'T': 'CEDEAR', 'S': 'Energía'},
    'SLB': {'T': 'CEDEAR', 'S': 'Energía'}, 'PBR': {'T': 'CEDEAR', 'S': 'Energía'},
    'GOLD': {'T': 'CEDEAR', 'S': 'Minería'}, 'VALE': {'T': 'CEDEAR', 'S': 'Minería'},
    'RIO': {'T': 'CEDEAR', 'S': 'Minería'}, 'BHP': {'T': 'CEDEAR', 'S': 'Minería'},
    'FCX': {'T': 'CEDEAR', 'S': 'Minería'}, 'MMM': {'T': 'CEDEAR', 'S': 'Industrial'},
    'FDX': {'T': 'CEDEAR', 'S': 'Logística'}, 'UPS': {'T': 'CEDEAR', 'S': 'Logística'},
    'UNP': {'T': 'CEDEAR', 'S': 'Transporte'}, 'COP': {'T': 'CEDEAR', 'S': 'Energía'},
    'BP': {'T': 'CEDEAR', 'S': 'Energía'}, 'SHEL': {'T': 'CEDEAR', 'S': 'Energía'},
    'HMY': {'T': 'CEDEAR', 'S': 'Minería'},

    # --- CEDEARS: SALUD & BIOTECH (15) ---
    'JNJ': {'T': 'CEDEAR', 'S': 'Salud'}, 'PFE': {'T': 'CEDEAR', 'S': 'Salud'},
    'MRK': {'T': 'CEDEAR', 'S': 'Salud'}, 'LLY': {'T': 'CEDEAR', 'S': 'Salud'},
    'ABBV': {'T': 'CEDEAR', 'S': 'Salud'}, 'UNH': {'T': 'CEDEAR', 'S': 'Salud'},
    'BMY': {'T': 'CEDEAR', 'S': 'Salud'}, 'AMGN': {'T': 'CEDEAR', 'S': 'Salud'},
    'GILD': {'T': 'CEDEAR', 'S': 'Salud'}, 'VRTX': {'T': 'CEDEAR', 'S': 'Salud'},
    'ISRG': {'T': 'CEDEAR', 'S': 'Salud Tech'}, 'TMO': {'T': 'CEDEAR', 'S': 'Salud Tech'},
    'ZTS': {'T': 'CEDEAR', 'S': 'Salud Animal'}, 'MDT': {'T': 'CEDEAR', 'S': 'Salud Tech'},
    'AZN': {'T': 'CEDEAR', 'S': 'Salud'},

    # --- CEDEARS: CHINA & BRASIL (11) ---
    'BABA': {'T': 'CEDEAR', 'S': 'China'}, 'JD': {'T': 'CEDEAR', 'S': 'China'},
    'BIDU': {'T': 'CEDEAR', 'S': 'China'}, 'NIO': {'T': 'CEDEAR', 'S': 'China'},
    'PDD': {'T': 'CEDEAR', 'S': 'China'}, 'ITUB': {'T': 'CEDEAR', 'S': 'Brasil'},
    'BBD': {'T': 'CEDEAR', 'S': 'Brasil'}, 'ERJ': {'T': 'CEDEAR', 'S': 'Brasil'},
    'ABEV': {'T': 'CEDEAR', 'S': 'Brasil'}, 'GGB': {'T': 'CEDEAR', 'S': 'Brasil'},
    'PDD': {'T': 'CEDEAR', 'S': 'China'},

    # --- CEDEARs ETFs (12) ---
    'SPY': {'T': 'CEDEAR ETF', 'S': 'Índice'}, 'QQQ': {'T': 'CEDEAR ETF', 'S': 'Índice'},
    'DIA': {'T': 'CEDEAR ETF', 'S': 'Índice'}, 'IWM': {'T': 'CEDEAR ETF', 'S': 'Índice'},
    'EEM': {'T': 'CEDEAR ETF', 'S': 'Emergentes'}, 'EWZ': {'T': 'CEDEAR ETF', 'S': 'Brasil'},
    'XLK': {'T': 'CEDEAR ETF', 'S': 'Tech'}, 'XLF': {'T': 'CEDEAR ETF', 'S': 'Financiero'},
    'XLE': {'T': 'CEDEAR ETF', 'S': 'Energía'}, 'XLV': {'T': 'CEDEAR ETF', 'S': 'Salud'},
    'GLD': {'T': 'CEDEAR ETF', 'S': 'Oro'}, 'ARKK': {'T': 'CEDEAR ETF', 'S': 'Innovación'}
}

# ─────────────────────────────────────────────
# MANUAL OPERATIVO
# ─────────────────────────────────────────────
with st.expander("📘 MANUAL DE ESTRATEGIA DUAL SNIPER (4 FRACTALES)"):
    st.markdown("""
    ### 🛡️ Matriz de Decisión Independiente
    1. **TRADE ALTA PROBABILIDAD:** Mira la **Ubicación**.
       * Si el **MACD 1D** está por encima de **0**, permite buscar **COMPRA**.
    
    2. **SINCRONÍA MOMENTUM 1D:** Mira la **Aceleración**.
       * Compara si los tiempos cortos (5m, 15m, 1H) acompañan el **Histograma 1D**.
    
    *Nota: Se eliminaron 1m y 30m para maximizar velocidad y estabilidad de la API.*
    """)

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
        position = "NEUTRO"
        for i in range(1, len(df)):
            h, ph, hc = df["Hist"].iloc[i], df["Hist"].iloc[i-1], df["HA_Color"].iloc[i]
            if position == "LONG" and h < ph: position = "NEUTRO"
            elif position == "SHORT" and h > ph: position = "NEUTRO"
            if position == "NEUTRO":
                if hc == 1 and h > ph: position = "LONG"
                elif hc == -1 and h < ph: position = "SHORT"
        return {
            "sig": position,
            "m0": "SOBRE 0" if df["MACD"].iloc[-1] > 0 else "BAJO 0",
            "h": "SUBIENDO" if df["Hist"].iloc[-1] > df["Hist"].iloc[-2] else "BAJANDO",
            "price": f"{df['Close'].iloc[-1]:.2f}"
        }
    except: return None

def get_column_verdicts(row):
    # Alineación de los 3 TFs cortos (5m, 15m, 1H)
    bulls_short = sum(1 for tf in ["5m", "15m", "1H"] if "LONG" in str(row.get(f"{tf} H.A./MACD","")))
    bears_short = sum(1 for tf in ["5m", "15m", "1H"] if "SHORT" in str(row.get(f"{tf} H.A./MACD","")))
    m0_1d = str(row.get("1D MACD 0", ""))
    hist_1d = str(row.get("1D Hist.", ""))

    # 1. TRADE ALTA PROBABILIDAD (Relación con Línea Cero)
    trade_prob = "⚖️ RANGO"
    if bulls_short >= 2 and "SOBRE 0" in m0_1d: trade_prob = "🔥 COMPRA"
    elif bears_short >= 2 and "BAJO 0" in m0_1d: trade_prob = "🩸 VENTA"

    # 2. SINCRONÍA MOMENTUM 1D (Relación con Histograma)
    momentum_sync = "⚪ SIN SINCRONÍA"
    if bulls_short >= 2 and "SUBIENDO" in hist_1d: momentum_sync = "🚀 SUBIENDO (SYNC)"
    elif bears_short >= 2 and "BAJANDO" in hist_1d: momentum_sync = "🩸 BAJANDO (SYNC)"
    
    return trade_prob, momentum_sync

# ─────────────────────────────────────────────
# MOTOR DE ESCANEO
# ─────────────────────────────────────────────
def scan_stocks(targets, acc):
    results = []
    prog = st.progress(0)
    for idx, sym in enumerate(targets):
        prog.progress((idx+1)/len(targets), text=f"Analizando {sym}")
        try:
            row = {"Activo": sym, "Tipo": MASTER_INFO.get(sym, {}).get('T', 'MANUAL'), "Sector": MASTER_INFO.get(sym, {}).get('S', 'Custom')}
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
                    for c in ["H.A./MACD", "Hist."]: row[f"{label} {c}"] = "-"
            
            if valid:
                row["TRADE ALTA PROBABILIDAD"], row["SINCRONÍA MOMENTUM 1D"] = get_column_verdicts(row)
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
# INTERFAZ Y RENDERIZADO
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("🎯 Sniper Stocks V36")
    mode = st.radio("Modo:", ["Pool Lotes", "Manual"])
    if mode == "Pool Lotes":
        all_t = sorted(list(MASTER_INFO.keys()))
        b_size = st.selectbox("Lote de:", [10, 20, 50, 100], index=2)
        batches = [all_t[i:i+b_size] for i in range(0, len(all_t), b_size)]
        sel = st.selectbox("Seleccionar Lote:", range(len(batches)))
        targets = batches[sel] if batches else []
    else:
        custom = st.text_input("Escriba Tickers:")
        targets = [x.strip().upper() for x in custom.split(",")] if custom else []

    acc = st.checkbox("Acumular Resultados", value=True)
    if st.button("🚀 INICIAR ESCANEO", type="primary"):
        st.session_state["sniper_results"] = scan_stocks(targets, acc)
        st.rerun()

    if st.session_state["sniper_results"]:
        st.divider()
        df_temp = pd.DataFrame(st.session_state["sniper_results"])
        f_ver = st.multiselect("Trade Alta Prob:", options=df_temp["TRADE ALTA PROBABILIDAD"].unique(), default=df_temp["TRADE ALTA PROBABILIDAD"].unique())
        f_sync = st.multiselect("Sincronía Momentum:", options=df_temp["SINCRONÍA MOMENTUM 1D"].unique(), default=df_temp["SINCRONÍA MOMENTUM 1D"].unique())
        f_sec = st.multiselect("Sector:", options=df_temp["Sector"].unique(), default=df_temp["Sector"].unique())

    if st.button("Limpiar Memoria"): st.session_state["sniper_results"] = []; st.rerun()

if st.session_state["sniper_results"]:
    df_f = pd.DataFrame(st.session_state["sniper_results"])
    df_filtered = df_f[(df_f["TRADE ALTA PROBABILIDAD"].isin(f_ver)) & (df_f["SINCRONÍA MOMENTUM 1D"].isin(f_sync)) & (df_f["Sector"].isin(f_sec))]
    
    def style_matrix(val):
        v = str(val).upper()
        if any(x in v for x in ["LONG", "SOBRE 0", "SUBIENDO", "COMPRA"]): return 'background-color: #d4edda; color: #155724; font-weight: bold;'
        if any(x in v for x in ["SHORT", "BAJO 0", "BAJANDO", "VENTA"]): return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
        return ''

    prio = ["Activo", "Tipo", "Sector", "TRADE ALTA PROBABILIDAD", "SINCRONÍA MOMENTUM 1D", "Precio", "1D Hist.", "1D MACD 0"]
    other = [c for c in df_filtered.columns if c not in prio]
    st.dataframe(df_filtered[prio + other].style.applymap(style_matrix), use_container_width=True, height=800)
else:
    st.info("👈 Inicie el escaneo para ver la radiografía fractal del mercado.")
