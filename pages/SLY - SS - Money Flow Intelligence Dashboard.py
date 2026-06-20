import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# CONFIGURACIÓN DEL SISTEMA E INTEGRIDAD DE DATOS
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | MONEY FLOW & COMPONENT AUDIT", page_icon="🦅")

st.markdown("""
<style>
    .stApp { background-color: #0B0E11; color: #EAECEF; }
    .report-card { 
        background-color: #1E2329; padding: 20px; border-radius: 12px; 
        border-left: 6px solid #F0B90B; margin-bottom: 15px;
    }
    .verdict-title { color: #F0B90B; font-weight: bold; font-size: 1.4em; }
    .highlight-green { color: #00FFAA; font-weight: bold; }
    .highlight-red { color: #FF3B30; font-weight: bold; }
    .stDataFrame { font-size: 12px; font-family: 'Roboto Mono', monospace; }
    h1 { color: #2962FF; font-weight: 800; border-bottom: 2px solid #2962FF; }
    h3 { color: #00E676; border-left: 5px solid #00E676; padding-left: 10px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# BASES DE DATOS (FUSIÓN)
# ─────────────────────────────────────────────
OPERABLE_BYMA = [
    "GGAL", "YPF", "BMA", "PAMP", "TGS", "CEPU", "EDN", "BFR", "SUPV", "CRESY", "IRS", "TEO", "LOMA", "VIST", "GLOB", "MELI", "TX",
    "AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "ADBE", "CRM", "AMD", "TXN", "QCOM", "INTC", "JPM", "V", "MA", "BAC", "GS", "MS", "WFC", 
    "BLK", "AXP", "XOM", "CVX", "COP", "SLB", "OXY", "PBR", "LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "PFE", "AMGN", "GILD", "GE", 
    "CAT", "UNP", "HON", "RTX", "LOW", "DE", "LMT", "BA", "PG", "COST", "PEP", "KO", "PM", "WMT", "MO", "MDLZ", "CL", "TGT", "AMZN", 
    "TSLA", "HD", "MCD", "BKNG", "SBUX", "GOOGL", "META", "NFLX", "DIS", "TMUS", "VZ", "LIN", "FCX", "NEM", "GOLD", "RIO", "BHP", 
    "PAAS", "HMY", "AU", "BABA", "JD", "BIDU", "NIO", "PDD", "TSM", "VALE", "ITUB", "BBD", "ERJ", "ABEV", "GGB", "MSTR", "COIN", "MARA", "RIOT",
    "SPY", "QQQ", "DIA", "EEM", "EWZ", "FXI", "XLE", "XLF", "XLK", "XLV", "XLI", "XLP", "ARKK", "GLD", "SLV", "XLB", "XLU", "XLY"
]

ASSET_DATABASE = {
    "YPF":  ["ARG / Energía & Oil", ["YPF"]],
    "PAMP": ["ARG / Energía & Oil", ["PAMP"]],
    "GGAL": ["ARG / Bancos", ["GGAL", "BMA", "BFR", "SUPV"]],
    "SPY":  ["Índice / S&P 500", ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "LLY", "JPM", "TSLA"]],
    "QQQ":  ["Índice / Nasdaq 100", ["AAPL", "MSFT", "NVDA", "AMZN", "META", "AVGO", "GOOGL", "COST", "TSLA"]],
    "ARKK": ["Índice / Innovación", ["TSLA", "COIN", "ROKU", "PLTR", "PATH", "DKNG", "HOOD", "TWLO"]],
    "XLK":  ["Sector / Tecnología", ["AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "ADBE", "CRM", "AMD"]],
    "XLF":  ["Sector / Financiero", ["JPM", "V", "MA", "BAC", "GS", "MS", "WFC", "BLK"]],
    "XLE":  ["Sector / Energía", ["XOM", "CVX", "COP", "SLB", "MPC", "PSX", "VLO", "OXY"]],
    "BTC-USD": ["Cripto / Bitcoin", ["BTC-USD", "MSTR", "MARA", "RIOT", "CLSK"]],
}

MARKETS = {
    "Sectores USA": ["XLK", "XLF", "XLE", "XLV", "XLI", "XLP", "XLU", "XLY", "XLB", "XLC", "XLRE"],
    "Global & Risk": ["SPY", "QQQ", "IWM", "EEM", "BTC-USD", "GLD"]
}

MACRO_CONFIG = {"1D": {"int": "1d", "per": "2y"}, "1S": {"int": "1wk", "per": "5y"}, "1M": {"int": "1mo", "per": "max"}}

# ─────────────────────────────────────────────
# MOTORES TÉCNICOS (SLY CORE)
# ─────────────────────────────────────────────
def run_sly_engine(df):
    if df.empty or len(df) < 35: return 0, 0, None
    macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
    if macd is None or macd.empty: return 0, 0, None
    hist = macd['MACDh_12_26_9']
    ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    ha_open = np.zeros(len(df))
    ha_open[0] = (df['Open'].iloc[0] + df['Close'].iloc[0]) / 2
    for i in range(1, len(df)): ha_open[i] = (ha_open[i-1] + ha_close.iloc[i-1]) / 2
    ha_dir = np.where(ha_close > ha_open, 1, -1)
    state, entry_px, entry_tm = 0, 0.0, None
    for i in range(1, len(df)):
        h, h_prev, hd, hd_prev = hist.iloc[i], hist.iloc[i-1], ha_dir[i], ha_dir[i-1]
        if (hd == 1 and hd_prev == -1 and h < 0 and h > h_prev): state, entry_px, entry_tm = 1, df['Close'].iloc[i], df.index[i]
        elif (hd == -1 and hd_prev == 1 and h > 0 and h < h_prev): state, entry_px, entry_tm = -1, df['Close'].iloc[i], df.index[i]
        elif state != 0:
            if (state == 1 and h < h_prev) or (state == -1 and h > h_prev): state = 0
    return state, entry_px, entry_tm

def analyze_asset(symbol, category="Custom"):
    row = {"Categoría": category, "Activo": symbol}
    clean_sym = symbol.split("-")[0].upper()
    row["Operable (ByMA)"] = "✅ SÍ" if clean_sym in OPERABLE_BYMA else "❌ NO"
    current_price = None
    for tf_key, config in MACRO_CONFIG.items():
        try:
            df = yf.download(symbol, interval=config['int'], period=config['per'], progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if tf_key == "1D" and not df.empty: current_price = df['Close'].iloc[-1]
            st_val, px_in, tm_in = run_sly_engine(df)
            if st_val != 0:
                pnl = (df['Close'].iloc[-1] - px_in) / px_in * 100 if st_val == 1 else (px_in - df['Close'].iloc[-1]) / px_in * 100
                row[f"{tf_key} Signal"], row[f"{tf_key} Fecha"], row[f"{tf_key} PnL"] = ("LONG 🟢" if st_val == 1 else "SHORT 🔴"), tm_in.strftime("%d/%m/%y"), f"{pnl:.2f}%"
            else: row[f"{tf_key} Signal"], row[f"{tf_key} Fecha"], row[f"{tf_key} PnL"] = "FUERA ⚪", "-", "-"
        except: row[f"{tf_key} Signal"] = "ERR"
    row["Precio"] = f"{current_price:,.2f}" if current_price else "-"
    return row

def style_macro(df):
    def apply_color(val):
        str_v = str(val)
        if "LONG" in str_v: return 'background-color: #1B5E20; color: white; font-weight: bold;'
        if "SHORT" in str_v: return 'background-color: #B71C1C; color: white; font-weight: bold;'
        if "✅ SÍ" in str_v: return 'color: #00E676; font-weight: bold;'
        return ''
    return df.style.map(apply_color)

# ─────────────────────────────────────────────
# UI - SECCIÓN 1: MONEY FLOW INTELLIGENCE
# ─────────────────────────────────────────────
st.title("🦅 SLY MONEY FLOW & MACRO AUDITOR")

with st.sidebar:
    st.header("⚙️ CONFIGURACIÓN")
    lookback = st.selectbox("Ventana Money Flow:", ["1 Mes", "3 Meses", "YTD"], index=0)
    selected_cat = st.multiselect("Filtros Dashboard:", list(MARKETS.keys()), default="Sectores USA")

# [Lógica de Money Flow aquí - Versión Robusta anterior integrada]
all_tickers_flow = []
for cat in selected_cat: all_tickers_flow.extend(MARKETS[cat])

if all_tickers_flow:
    # Obtener data para el Scatter Plot
    today = datetime.now()
    dates = {"1 Mes": 30, "3 Meses": 90, "YTD": (today - datetime(today.year, 1, 1)).days}
    start_flow = today - timedelta(days=dates[lookback])
    df_raw = yf.download(all_tickers_flow, start=start_flow, progress=False)
    close_f, vol_f = df_raw['Close'].ffill().bfill(), df_raw['Volume'].ffill().fillna(0)
    
    returns_f = ((close_f.iloc[-1] / close_f.iloc[0].replace(0, np.nan)) - 1) * 100
    rvol_f = vol_f.iloc[-5:].mean() / vol_f.mean().replace(0, np.nan)
    mfs_f = (returns_f * rvol_f).replace([np.inf, -np.inf], np.nan).dropna()
    
    stats_df = pd.DataFrame({"Retorno %": returns_f, "RVOL": rvol_f, "Score": mfs_f}).dropna().sort_values(by="Score", ascending=False)

    # Renderizado Money Flow
    st.subheader("🕵️ Análisis de Flujo de Capital (Smart Money)")
    c1, c2 = st.columns([2, 1])
    with c1:
        fig = px.scatter(stats_df, x="Retorno %", y="RVOL", size=stats_df["Score"].abs().clip(lower=5),
                         color="Score", text=stats_df.index, color_continuous_scale="RdYlGn", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.dataframe(stats_df.style.background_gradient(cmap='RdYlGn', subset=['Score']), use_container_width=True)

# ─────────────────────────────────────────────
# UI - SECCIÓN 2: AUDITORÍA DE COMPONENTES (EL PEDIDO)
# ─────────────────────────────────────────────
st.divider()
st.header("🔍 Auditoría de Componentes (Drill-Down)")

selected_main = st.selectbox("Seleccione Activo Principal para auditar sus drivers:", list(ASSET_DATABASE.keys()))

if st.button(f"🔎 ANALIZAR COMPONENTES DE {selected_main}"):
    constituents = ASSET_DATABASE[selected_main][1]
    detailed_results = []
    prog_detail = st.progress(0)
    
    for idx, comp in enumerate(constituents):
        prog_detail.progress((idx+1)/len(constituents), text=f"Auditando: {comp}")
        detailed_results.append(analyze_asset(comp, f"Driver de {selected_main}"))
    
    df_detailed = pd.DataFrame(detailed_results)
    cols_final = ["Operable (ByMA)", "Activo", "Precio", "1D Signal", "1D PnL", "1S Signal", "1S PnL", "1M Signal", "1M PnL"]
    st.subheader(f"📋 Ficha Técnica: Componentes de {selected_main}")
    st.dataframe(style_macro(df_detailed[cols_final]), use_container_width=True)
