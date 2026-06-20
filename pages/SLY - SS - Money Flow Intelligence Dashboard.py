import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import plotly.express as px
import time
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# CONFIGURACIÓN INSTITUCIONAL SLY
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | TOTAL INTELLIGENCE", page_icon="🦅")

st.markdown("""
<style>
    .stApp { background-color: #0B0E11; color: #EAECEF; }
    .report-card { 
        background-color: #1E2329; padding: 20px; border-radius: 12px; 
        border-left: 6px solid #F0B90B; margin-bottom: 15px;
    }
    .verdict-title { color: #F0B90B; font-weight: bold; font-size: 1.3em; margin-bottom: 8px; }
    .verdict-text { color: #EAECEF; font-size: 1.1em; line-height: 1.4; }
    .highlight-green { color: #00FFAA; font-weight: bold; }
    .highlight-red { color: #FF3B30; font-weight: bold; }
    .stDataFrame { font-size: 12px; font-family: 'Roboto Mono', monospace; }
    h1 { color: #2962FF; font-weight: 800; border-bottom: 2px solid #2962FF; }
    h3 { color: #00E676; border-left: 5px solid #00E676; padding-left: 10px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# BASES DE DATOS Y CONFIGURACIÓN
# ─────────────────────────────────────────────
OPERABLE_BYMA = ["GGAL", "YPF", "BMA", "PAMP", "TGS", "CEPU", "EDN", "BFR", "SUPV", "CRESY", "IRS", "TEO", "LOMA", "VIST", "GLOB", "MELI", "TX", "AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "ADBE", "CRM", "AMD", "TXN", "QCOM", "INTC", "JPM", "V", "MA", "BAC", "GS", "MS", "WFC", "BLK", "AXP", "XOM", "CVX", "COP", "SLB", "OXY", "PBR", "LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "PFE", "AMGN", "GILD", "GE", "CAT", "UNP", "HON", "RTX", "LOW", "DE", "LMT", "BA", "PG", "COST", "PEP", "KO", "PM", "WMT", "MO", "MDLZ", "CL", "TGT", "AMZN", "TSLA", "HD", "MCD", "BKNG", "SBUX", "GOOGL", "META", "NFLX", "DIS", "TMUS", "VZ", "LIN", "FCX", "NEM", "GOLD", "RIO", "BHP", "PAAS", "HMY", "AU", "BABA", "JD", "BIDU", "NIO", "PDD", "TSM", "VALE", "ITUB", "BBD", "ERJ", "ABEV", "GGB", "MSTR", "COIN", "MARA", "RIOT", "SPY", "QQQ", "DIA", "EEM", "EWZ", "FXI", "XLE", "XLF", "XLK", "XLV", "XLI", "XLP", "ARKK", "GLD", "SLV", "XLB", "XLU", "XLY"]

ASSET_DATABASE = {
    "YPF":  ["ARG / Energía", ["YPF"]],
    "GGAL": ["ARG / Bancos", ["GGAL", "BMA", "BFR", "SUPV"]],
    "SPY":  ["Índice / S&P 500", ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "LLY", "JPM", "TSLA"]],
    "QQQ":  ["Índice / Nasdaq 100", ["AAPL", "MSFT", "NVDA", "AMZN", "META", "AVGO", "GOOGL", "COST", "TSLA"]],
    "XLK":  ["Sector / Tecnología", ["AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "ADBE", "CRM", "AMD"]],
    "XLF":  ["Sector / Financiero", ["JPM", "V", "MA", "BAC", "GS", "MS", "WFC", "BLK"]],
    "XLE":  ["Sector / Energía", ["XOM", "CVX", "COP", "SLB", "OXY"]],
    "BTC-USD": ["Cripto / Bitcoin", ["BTC-USD", "MSTR", "MARA", "RIOT", "CLSK"]]
}

MARKETS = {
    "Sectores USA": ["XLK", "XLF", "XLE", "XLV", "XLI", "XLP", "XLU", "XLY", "XLB", "XLC", "XLRE"],
    "Global & Risk": ["SPY", "QQQ", "IWM", "EEM", "BTC-USD", "GLD"]
}

MACRO_CONFIG = {"1D": {"int": "1d", "per": "2y"}, "1S": {"int": "1wk", "per": "5y"}, "1M": {"int": "1mo", "per": "max"}}

# ─────────────────────────────────────────────
# MOTORES TÉCNICOS SLY
# ─────────────────────────────────────────────
def run_sly_engine(df):
    if df.empty or len(df) < 35: return 0, 0, None
    macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
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
    row["ByMA"] = "✅" if clean_sym in OPERABLE_BYMA else "❌"
    for tf, config in MACRO_CONFIG.items():
        try:
            df = yf.download(symbol, interval=config['int'], period=config['per'], progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if tf == "1D": row["Precio"] = f"{df['Close'].iloc[-1]:,.2f}"
            st_val, px_in, tm_in = run_sly_engine(df)
            if st_val != 0:
                pnl = (df['Close'].iloc[-1] - px_in) / px_in * 100 if st_val == 1 else (px_in - df['Close'].iloc[-1]) / px_in * 100
                row[f"{tf} Signal"] = "LONG 🟢" if st_val == 1 else "SHORT 🔴"
                row[f"{tf} PnL"] = f"{pnl:.2f}%"
            else: row[f"{tf} Signal"] = "FUERA ⚪"
        except: row[f"{tf} Signal"] = "ERR"
    return row

def style_df(df):
    def color_signals(val):
        if "LONG" in str(val): return 'background-color: #1B5E20; color: white;'
        if "SHORT" in str(val): return 'background-color: #B71C1C; color: white;'
        return ''
    return df.style.map(color_signals)

# ─────────────────────────────────────────────
# UI - SECCIÓN 1: MONEY FLOW INTELLIGENCE
# ─────────────────────────────────────────────
st.title("🦅 SLY MONEY FLOW & COMPONENT AUDITOR")

with st.sidebar:
    st.header("⚙️ CONFIG")
    lookback = st.selectbox("Ventana:", ["1 Mes", "3 Meses", "YTD"], index=0)
    selected_cat = st.multiselect("Categorías:", list(MARKETS.keys()), default="Sectores USA")

all_f = []
for c in selected_cat: all_f.extend(MARKETS[c])

if all_f:
    today = datetime.now()
    dates = {"1 Mes": 30, "3 Meses": 90, "YTD": (today - datetime(today.year, 1, 1)).days}
    df_raw = yf.download(all_f, start=today - timedelta(days=dates[lookback]), progress=False)
    
    if not df_raw.empty:
        c_f, v_f = df_raw['Close'].ffill().bfill(), df_raw['Volume'].ffill().fillna(0)
        ret_f = ((c_f.iloc[-1] / c_f.iloc[0].replace(0, np.nan)) - 1) * 100
        rv_f = v_f.iloc[-5:].mean() / v_f.mean().replace(0, np.nan)
        score_f = (ret_f * rv_f).replace([np.inf, -np.inf], np.nan).dropna()
        stats_df = pd.DataFrame({"Ret %": ret_f, "RVOL": rv_f, "Score": score_f}).dropna().sort_values("Score", ascending=False)

        # --- EXPLICACIONES FORENSES ---
        st.subheader("🕵️ Veredicto Forense del Sistema")
        v1, v2 = st.columns(2)
        with v1:
            top_a = stats_df.index[0]
            verdict_top = f"Inyección masiva en <span class='highlight-green'>{top_a}</span> confirmada por volumen." if stats_df.iloc[0]["RVOL"] > 1.1 else f"Subida técnica en <span class='highlight-green'>{top_a}</span> con volumen bajo (Rally frágil)."
            st.markdown(f"<div class='report-card'><div class='verdict-title'>🚀 LÍDER DE FLUJO</div><div class='verdict-text'>{verdict_top}</div></div>", unsafe_allow_html=True)
        with v2:
            worst_a = stats_df.index[-1]
            verdict_worst = f"Distribución pesada en <span class='highlight-red'>{worst_a}</span>. Salida institucional." if stats_df.iloc[-1]["RVOL"] > 1.2 else f"Debilidad en <span class='highlight-red'>{worst_a}</span> por falta de interés."
            st.markdown(f"<div class='report-card'><div class='verdict-title'>⚠️ FUGA DE CAPITAL</div><div class='verdict-text'>{verdict_worst}</div></div>", unsafe_allow_html=True)

        # --- GRÁFICO Y TABLA ---
        c1, c2 = st.columns([2, 1])
        with c1:
            fig = px.scatter(stats_df, x="Ret %", y="RVOL", size=stats_df["Score"].abs().clip(lower=5), color="Score", text=stats_df.index, color_continuous_scale="RdYlGn", template="plotly_dark")
            fig.update_traces(textposition='top center')
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.dataframe(stats_df.style.background_gradient(cmap='RdYlGn', subset=['Score']).format(precision=2), use_container_width=True)

# ─────────────────────────────────────────────
# UI - SECCIÓN 2: AUDITORÍA DE COMPONENTES
# ─────────────────────────────────────────────
st.divider()
st.header("🔍 Auditoría de Componentes (Drill-Down)")
sel_audit = st.selectbox("Seleccione Activo Principal para auditar:", list(ASSET_DATABASE.keys()))

if st.button(f"🔎 ANALIZAR COMPONENTES DE {sel_audit}"):
    comps = ASSET_DATABASE[sel_audit][1]
    results = []
    prog = st.progress(0)
    for idx, cp in enumerate(comps):
        prog.progress((idx+1)/len(comps), text=f"Analizando: {cp}")
        results.append(analyze_asset(cp, f"Driver de {sel_audit}"))
    
    df_res = pd.DataFrame(results)
    cols = ["ByMA", "Activo", "Precio", "1D Signal", "1D PnL", "1S Signal", "1S PnL", "1M Signal", "1M PnL"]
    st.dataframe(style_df(df_res[cols]), use_container_width=True)
