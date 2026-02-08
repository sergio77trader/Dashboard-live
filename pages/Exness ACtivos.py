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
st.set_page_config(layout="wide", page_title="SYSTEMATRADER | MACRO CLASSIFIED")

st.markdown("""
<style>
    .stDataFrame { font-size: 11px; font-family: 'Roboto Mono', monospace; }
    h1 { color: #00897B; font-weight: 800; border-bottom: 2px solid #00897B; }
    [data-testid="stMetricValue"] { font-size: 14px; }
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
# BÓVEDA DE ACTIVOS CLASIFICADA (LISTA ESPECÍFICA)
# ─────────────────────────────────────────────
ASSET_DB = {
    # TECH & SEMICONDUCTORES
    'AAPL': 'Tech / Hardware', 'MSFT': 'Tech / Software', 'NVDA': 'Semis / AI', 'AMD': 'Semis / Chips', 
    'AVGO': 'Semis / Infrastructure', 'INTC': 'Semis / Chips', 'TSM': 'Semis / Foundry', 'ADBE': 'Tech / Software', 
    'ORCL': 'Tech / Cloud', 'CSCO': 'Tech / Networking', 'IBM': 'Tech / Enterprise', 'INTU': 'Tech / Software', 
    'FTNT': 'Tech / Security', 'ASML': 'Semis / Equipment', 'LRCX': 'Semis / Equipment',
    # COMUNICACIONES & SOCIAL
    'GOOGL': 'Comm / Search', 'META': 'Comm / Social', 'NFLX': 'Comm / Streaming', 'CHTR': 'Comm / Cable', 
    'CMCSA': 'Comm / Entertainment', 'TMUS': 'Comm / Wireless', 'T': 'Comm / Telecom', 'VZ': 'Comm / Telecom', 
    'BIDU': 'Comm / China Search', 'NTES': 'Comm / China Gaming', 'TME': 'Comm / China Music',
    # CONSUMO DISCRECIONAL
    'AMZN': 'Consumo / E-commerce', 'TSLA': 'Consumo / EV', 'NKE': 'Consumo / Apparel', 'SBUX': 'Consumo / Restaurants', 
    'MCD': 'Consumo / Restaurants', 'HD': 'Consumo / Retail', 'EBAY': 'Consumo / E-commerce', 'YUMC': 'Consumo / China Food',
    # CONSUMO BÁSICO
    'COST': 'Staples / Retail', 'KO': 'Staples / Beverage', 'PEP': 'Staples / Beverage', 'PG': 'Staples / Household', 
    'PM': 'Staples / Tobacco', 'MO': 'Staples / Tobacco', 'MDLZ': 'Staples / Food', 'WMT': 'Staples / Retail',
    # SALUD & BIOTECH
    'LLY': 'Health / Pharma', 'UNH': 'Health / Insurer', 'JNJ': 'Health / Pharma', 'ABBV': 'Health / Biotech', 
    'MRK': 'Health / Pharma', 'PFE': 'Health / Pharma', 'AMGN': 'Health / Biotech', 'GILD': 'Health / Biotech', 
    'ISRG': 'Health / Med-Tech', 'VRTX': 'Health / Biotech', 'REGN': 'Health / Biotech', 'TMO': 'Health / Equipment', 
    'BMY': 'Health / Pharma', 'ABT': 'Health / Equipment', 'CVS': 'Health / Retail', 'BIIB': 'Health / Biotech',
    # FINANZAS
    'JPM': 'Financiero / Banco', 'BAC': 'Financiero / Banco', 'MS': 'Financiero / Investment', 'C': 'Financiero / Banco', 
    'WFC': 'Financiero / Banco', 'MA': 'Financiero / Pagos', 'V': 'Financiero / Pagos', 'PYPL': 'Financiero / Fintech', 
    'CME': 'Financiero / Exchange', 'ADP': 'Financiero / Services', 'FUTU': 'Financiero / China Broker',
    # INDUSTRIAL & ENERGÍA
    'BA': 'Industrial / Aerospace', 'LMT': 'Industrial / Defense', 'GE': 'Industrial / Diversified', 
    'MMM': 'Industrial / Diversified', 'UPS': 'Industrial / Logistics', 'CSX': 'Industrial / Rail', 
    'XOM': 'Energía / Oil', 'LIN': 'Materiales / Gas', 'F': 'Industrial / Auto',
    # REAL ESTATE
    'AMT': 'REIT / Towers', 'EQIX': 'REIT / Data Centers',
    # CHINA & EMERGENTES
    'BABA': 'China / E-commerce', 'JD': 'China / E-commerce', 'PDD': 'China / E-commerce', 'LI': 'China / EV', 
    'NIO': 'China / EV', 'XPEV': 'China / EV', 'BILI': 'China / Video', 'VIPS': 'China / Retail', 
    'PDD': 'China / E-commerce', 'TAL': 'China / Education', 'EDU': 'China / Education', 'BEKE': 'China / Housing',
    'ZTO': 'China / Logistics', 'YUMC': 'China / Food'
}

TICKERS_LIST = sorted(list(ASSET_DB.keys()))

# ─────────────────────────────────────────────
# MOTOR TÉCNICO SLY
# ─────────────────────────────────────────────
def run_sly_engine(df):
    if df.empty or len(df) < 35: return 0, 0, None
    macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
    if macd is None: return 0, 0, None
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
def analyze_asset(symbol):
    row = {"Activo": symbol, "Sector": ASSET_DB.get(symbol, "Otros")}
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
# INTERFAZ
# ─────────────────────────────────────────────
st.title("🦅 TRIPLE MACRO MATRIX: SECTORIAL RADAR")

with st.sidebar:
    st.header("⚙️ Control de Radar")
    
    all_sectors = sorted(list(set(ASSET_DB.values())))
    f_sector = st.multiselect("Filtrar por Sectores:", options=all_sectors, default=all_sectors)
    
    # Filtrar tickers según sector elegido
    filtered_tickers = [k for k, v in ASSET_DB.items() if v in f_sector]
    
    b_size = st.selectbox("Batch Size:", [10, 25, 50], index=1)
    batches = [filtered_tickers[i:i+b_size] for i in range(0, len(filtered_tickers), b_size)]
    
    if batches:
        sel_batch = st.selectbox("Seleccionar Lote:", range(len(batches)), format_func=lambda x: f"Lote {x} ({len(batches[x])} activos)")
        acc = st.checkbox("Acumular Resultados", value=True)
        
        if st.button("🚀 INICIAR ESCANEO", type="primary", use_container_width=True):
            results = []
            prog = st.progress(0)
            targets = batches[sel_batch]
            for idx, sym in enumerate(targets):
                prog.progress((idx+1)/len(targets), text=f"Analizando: {sym}")
                results.append(analyze_asset(sym))
                time.sleep(0.1)
            
            if acc:
                current = {x["Activo"]: x for x in st.session_state["sniper_results"]}
                for r in results: current[r["Activo"]] = r
                st.session_state["sniper_results"] = list(current.values())
            else:
                st.session_state["sniper_results"] = results
            st.rerun()

    if st.button("Limpiar Memoria"):
        st.session_state["sniper_results"] = []
        st.rerun()

# ─────────────────────────────────────────────
# TABLA FINAL
# ─────────────────────────────────────────────
if st.session_state["sniper_results"]:
    df_final = pd.DataFrame(st.session_state["sniper_results"])
    
    # Re-filtrar por sector si se cambió el sidebar después del escaneo
    df_final = df_final[df_final["Sector"].isin(f_sector)]
    
    cols_order = ["Sector", "Activo", "Precio", 
                  "1D Signal", "1D Fecha", "1D PnL",
                  "1S Signal", "1S Fecha", "1S PnL",
                  "1M Signal", "1M Fecha", "1M PnL"]
    
    df_final = df_final[[c for c in cols_order if c in df_final.columns]]
    df_final = df_final.sort_values(["Sector", "Activo"])

    def style_table(val):
        if "LONG" in str(val): return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
        if "SHORT" in str(val): return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
        if "%" in str(val):
            try:
                v = float(str(val).replace("%",""))
                return f'color: {"#2E7D32" if v >= 0 else "#C62828"}; font-weight: bold;'
            except: return ''
        return ''

    st.dataframe(df_final.style.applymap(style_table), use_container_width=True, height=800)
else:
    st.info("👈 Seleccione los sectores e inicie el escaneo de los activos detallados.")
