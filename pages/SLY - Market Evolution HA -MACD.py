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
st.set_page_config(layout="wide", page_title="SYSTEMATRADER | TOTAL MACRO MATRIX V47.1")

st.markdown("""
<style>
    .stDataFrame { font-size: 11px; font-family: 'Roboto Mono', monospace; }
    h1 { color: #2962FF; font-weight: 800; border-bottom: 2px solid #2962FF; }
    h3 { color: #00E676; border-left: 5px solid #00E676; padding-left: 10px; margin-top: 20px; }
    .stProgress > div > div > div > div { background-color: #2962FF; }
</style>
""", unsafe_allow_html=True)

if "sniper_results" not in st.session_state:
    st.session_state["sniper_results"] = []

MACRO_CONFIG = {
    "1D": {"int": "1d", "per": "2y"},
    "1S": {"int": "1wk", "per": "5y"},
    "1M": {"int": "1mo", "per": "max"}
}

# ─────────────────────────────────────────────
# LISTADO MAESTRO DE OPERABILIDAD (ByMA)
# ─────────────────────────────────────────────
OPERABLE_BYMA = [
    "GGAL", "YPF", "BMA", "PAMP", "TGS", "CEPU", "EDN", "BFR", "SUPV", "CRESY", "IRS", "TEO", "LOMA", "VIST", "GLOB", "MELI", "TX",
    "AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "ADBE", "CRM", "AMD", "TXN", "QCOM", "INTC",
    "JPM", "V", "MA", "BAC", "GS", "MS", "WFC", "BLK", "AXP", "XOM", "CVX", "COP", "SLB", "OXY", "PBR",
    "LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "PFE", "AMGN", "GILD", "GE", "CAT", "UNP", "HON", "RTX", "LOW", "DE", "LMT", "BA",
    "PG", "COST", "PEP", "KO", "PM", "WMT", "MO", "MDLZ", "CL", "TGT", "AMZN", "TSLA", "HD", "MCD", "BKNG", "SBUX",
    "GOOGL", "META", "NFLX", "DIS", "TMUS", "VZ", "LIN", "FCX", "NEM", "GOLD", "RIO", "BHP", "PAAS", "HMY", "AU",
    "BABA", "JD", "BIDU", "NIO", "PDD", "TSM", "VALE", "ITUB", "BBD", "ERJ", "ABEV", "GGB", "MSTR", "COIN", "MARA", "RIOT",
    "SPY", "QQQ", "DIA", "EEM", "EWZ", "FXI", "XLE", "XLF", "XLK", "XLV", "XLI", "XLP", "ARKK", "GLD", "SLV", "XLB", "XLU", "XLY"
]

ASSET_DATABASE = {
    "YPF":  ["ARG / Energía & Oil", ["YPF"]],
    "PAMP": ["ARG / Energía & Oil", ["PAMP"]],
    "VIST": ["ARG / Energía & Oil", ["VIST"]],
    "TGS":  ["ARG / Energía & Oil", ["TGS"]],
    "CEPU": ["ARG / Energía & Oil", ["CEPU"]],
    "EDN":  ["ARG / Energía & Oil", ["EDN"]],
    "GGAL": ["ARG / Bancos", ["GGAL"]],
    "BMA":  ["ARG / Bancos", ["BMA"]],
    "BFR":  ["ARG / Bancos", ["BFR"]],
    "SUPV": ["ARG / Bancos", ["SUPV"]],
    "MELI": ["ARG / Tech & E-Comm", ["MELI"]],
    "GLOB": ["ARG / Tech & E-Comm", ["GLOB"]],
    "TX":   ["ARG / Siderurgia", ["TX"]],
    "CRESY":["ARG / Inmuebles & Const.", ["CRESY"]],
    "LOMA": ["ARG / Inmuebles & Const.", ["LOMA"]],
    "TEO":  ["ARG / Telecom", ["TEO"]],
    "SPY":  ["Índice / S&P 500", ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "LLY", "JPM", "TSLA"]],
    "QQQ":  ["Índice / Nasdaq 100", ["AAPL", "MSFT", "NVDA", "AMZN", "META", "AVGO", "GOOGL", "COST", "TSLA"]],
    "ARKK": ["Índice / Innovación", ["TSLA", "COIN", "ROKU", "PLTR", "PATH", "DKNG", "HOOD", "TWLO"]],
    "EEM":  ["Índice / Emergentes", ["TSM", "BABA", "PDD", "JD", "VALE", "BIDU", "NIO", "MELI", "ITUB"]],
    "EWZ":  ["Índice / Brasil", ["VALE", "ITUB", "BBD", "ABEV", "GGB"]],
    "FXI":  ["Índice / China", ["BABA", "JD", "BIDU", "PDD", "NIO"]],
    "XLK":  ["Sector / Tecnología", ["AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "ADBE", "CRM", "AMD"]],
    "XLF":  ["Sector / Financiero", ["JPM", "V", "MA", "BAC", "GS", "MS", "WFC", "BLK"]],
    "XLE":  ["Sector / Energía", ["XOM", "CVX", "COP", "SLB", "MPC", "PSX", "VLO", "OXY"]],
    "XLV":  ["Sector / Salud", ["LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "PFE", "AMGN"]],
    "XLI":  ["Sector / Industrial", ["GE", "CAT", "UNP", "HON", "RTX", "LOW", "DE", "LMT"]],
    "XLP":  ["Sector / Consumo Básico", ["PG", "COST", "PEP", "KO", "PM", "WMT", "MO", "MDLZ"]],
    "XLB":  ["Sector / Materiales", ["LIN", "SHW", "APD", "FCX", "CTVA", "ECL", "NEM", "ALB"]],
    "XLU":  ["Sector / Utilities", ["NEE", "SO", "DUK", "CEG", "SRE", "AEP", "D", "XEL"]],
    "XLY":  ["Sector / Consumo Disc.", ["AMZN", "TSLA", "HD", "MCD", "NKE", "BKNG", "SBUX", "TJX"]],
    "GLD":  ["Metales / Oro", ["GLD", "NEM", "GOLD", "AU", "HMY"]],
    "SLV":  ["Metales / Plata", ["SLV", "PAAS", "AG", "FSM", "WPM"]],
    "BTC-USD": ["Cripto / Bitcoin", ["BTC-USD", "MSTR", "MARA", "RIOT", "CLSK"]],
    "ETH-USD": ["Cripto / Ethereum", ["ETH-USD", "COIN", "LINK-USD", "UNI-USD"]],
    "DX-Y.NYB": ["Macro / Dollar Index", ["DX-Y.NYB", "UUP"]]
}

TICKERS_LIST = sorted(list(ASSET_DATABASE.keys()))

# ─────────────────────────────────────────────
# MOTOR TÉCNICO SLY
# ─────────────────────────────────────────────
def run_sly_engine(df):
    if df.empty or len(df) < 35: return 0, 0, None
    macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
    if macd is None or macd.empty: return 0, 0, None
    hist = macd['MACDh_12_26_9']
    
    ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    ha_open = np.zeros(len(df))
    ha_open[0] = (df['Open'].iloc[0] + df['Close'].iloc[0]) / 2
    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i-1] + ha_close.iloc[i-1]) / 2
    ha_dir = np.where(ha_close > ha_open, 1, -1)
    
    state, entry_px, entry_tm = 0, 0.0, None
    for i in range(1, len(df)):
        h, h_prev = hist.iloc[i], hist.iloc[i-1]
        hd, hd_prev = ha_dir[i], ha_dir[i-1]
        longC = (hd == 1 and hd_prev == -1 and h < 0 and h > h_prev)
        shrtC = (hd == -1 and hd_prev == 1 and h > 0 and h < h_prev)
        if longC: state, entry_px, entry_tm = 1, df['Close'].iloc[i], df.index[i]
        elif shrtC: state, entry_px, entry_tm = -1, df['Close'].iloc[i], df.index[i]
        elif state != 0:
            if (state == 1 and h < h_prev) or (state == -1 and h > h_prev): state = 0
    return state, entry_px, entry_tm

# ─────────────────────────────────────────────
# ANALIZADOR
# ─────────────────────────────────────────────
def analyze_asset(symbol, category="Custom"):
    row = {"Categoría": category, "Activo": symbol}
    clean_sym = symbol.split("-")[0].split(".")[0].split(":")[0].upper()
    row["Operable (ByMA)"] = "✅ SÍ" if clean_sym in OPERABLE_BYMA else "❌ NO"
    
    current_price = None
    for tf_key, config in MACRO_CONFIG.items():
        try:
            df = yf.download(symbol, interval=config['int'], period=config['per'], progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if df.empty: continue
            if tf_key == "1D": current_price = df['Close'].iloc[-1]
            st_val, px_in, tm_in = run_sly_engine(df)
            if st_val != 0:
                pnl = (df['Close'].iloc[-1] - px_in) / px_in * 100 if st_val == 1 else (px_in - df['Close'].iloc[-1]) / px_in * 100
                row[f"{tf_key} Signal"] = "LONG 🟢" if st_val == 1 else "SHORT 🔴"
                row[f"{tf_key} Fecha"] = tm_in.strftime("%d/%m/%y")
                row[f"{tf_key} PnL"] = f"{pnl:.2f}%"
            else:
                row[f"{tf_key} Signal"] = "FUERA ⚪"
                row[f"{tf_key} Fecha"] = "-"
                row[f"{tf_key} PnL"] = "-"
        except: row[f"{tf_key} Signal"] = "ERR"
    row["Precio"] = f"{current_price:,.2f}" if current_price else "-"
    return row

# ─────────────────────────────────────────────
# PARCHE DE ESTILO (PANDAS 2.1+ COMPATIBILITY)
# ─────────────────────────────────────────────
def style_macro(df):
    def apply_color(val):
        str_val = str(val)
        if "LONG" in str_val: return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
        if "SHORT" in str_val: return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
        if "✅ SÍ" in str_val: return 'color: #00E676; font-weight: bold;'
        if "%" in str_val:
            try:
                v = float(str_val.replace("%",""))
                return f'color: {"#2E7D32" if v >= 0 else "#C62828"}; font-weight: bold;'
            except: return ''
        return ''
    
    # Intenta usar .map() (Pandas 2.1+), si falla vuelve a .applymap() (Versiones viejas)
    try:
        return df.style.map(apply_color)
    except AttributeError:
        return df.style.applymap(apply_color)

# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
st.title("🦅 GLOBAL MACRO TRIPLE SYNC V47.1")

with st.sidebar:
    st.header("⚙️ Radar Control")
    if st.button("🚀 ACTUALIZAR MATRIZ GLOBAL", type="primary", use_container_width=True):
        results = []
        prog = st.progress(0)
        for idx, sym in enumerate(TICKERS_LIST):
            prog.progress((idx+1)/len(TICKERS_LIST), text=f"Analizando: {sym}")
            results.append(analyze_asset(sym, ASSET_DATABASE[sym][0]))
            time.sleep(0.01)
        st.session_state["sniper_results"] = results
        st.rerun()

if st.session_state["sniper_results"]:
    df_f = pd.DataFrame(st.session_state["sniper_results"])
    df_f = df_f.sort_values(by=["Categoría", "Activo"], ascending=[True, True])
    main_cols = ["Categoría", "Activo", "Precio", "1D Signal", "1D Fecha", "1D PnL", "1S Signal", "1S Fecha", "1S PnL", "1M Signal", "1M Fecha", "1M PnL"]
    st.dataframe(style_macro(df_f[main_cols]), use_container_width=True, height=600)

    st.divider()
    st.header("🔍 Auditoría de Componentes")
    selected_main = st.selectbox("Seleccione Activo para auditar componentes:", TICKERS_LIST)
    
    if st.button(f"🔎 ANALIZAR COMPONENTES DE {selected_main}"):
        constituents = ASSET_DATABASE[selected_main][1]
        detailed_results = []
        prog_detail = st.progress(0)
        for idx, comp in enumerate(constituents):
            prog_detail.progress((idx+1)/len(constituents), text=f"Subyacente: {comp}")
            detailed_results.append(analyze_asset(comp, f"Driver de {selected_main}"))
        
        df_detailed = pd.DataFrame(detailed_results)
        cols_final = ["Operable (ByMA)", "Activo", "Precio", "1D Signal", "1D Fecha", "1D PnL", "1S Signal", "1S Fecha", "1S PnL", "1M Signal", "1M Fecha", "1M PnL"]
        st.dataframe(style_macro(df_detailed[cols_final]), use_container_width=True)
else:
    st.info("Pulse 'ACTUALIZAR MATRIZ GLOBAL' para cargar el sistema.")
