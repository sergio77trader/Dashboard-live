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
st.set_page_config(layout="wide", page_title="SYSTEMATRADER | TOTAL MACRO MATRIX")

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
# LISTADO MAESTRO DE CEDEARS OPERABLES (ByMA)
# ─────────────────────────────────────────────
CEDEAR_LIST = [
    "AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "ADBE", "CRM", "AMD", "TXN", "QCOM", # Tech
    "JPM", "V", "MA", "BAC", "GS", "MS", "WFC", "BLK", "AXP", "HSBC", # Finanzas
    "XOM", "CVX", "COP", "SLB", "OXY", "HAL", "BP", "PBR", "VIST", # Energía
    "LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "ABT", "PFE", "AMGN", "GILD", # Salud
    "GE", "CAT", "UNP", "HON", "RTX", "LOW", "DE", "LMT", "UPS", "BA", "MMM", # Industrial
    "PG", "COST", "PEP", "KO", "PM", "WMT", "MO", "MDLZ", "CL", "TGT", "NKE", # Consumo
    "AMZN", "TSLA", "HD", "MCD", "BKNG", "SBUX", "TJX", "MELI", "EBAY", # Consumo Disc
    "GOOGL", "META", "NFLX", "DIS", "TMUS", "VZ", "T", # Comunicaciones
    "LIN", "SHW", "FCX", "NEM", "NUE", "DOW", "ALB", "GOLD", "RIO", "BHP", # Materiales
    "BABA", "JD", "BIDU", "NIO", "PDD", "TSM", "TCEHY", # China / Emergentes
    "VALE", "ITUB", "BBD", "ERJ", "ABEV", "GGB", # Brasil
    "MSTR", "COIN", "MARA", "RIOT", "CLSK", # Cripto Relacionados
    "SPY", "QQQ", "DIA", "EEM", "EWZ", "XLE", "XLF", "XLK", "XLV", "XLI", "XLP", "XLK", "ARKK", "GLD", "SLV" # ETFs
]

# ─────────────────────────────────────────────
# BÓVEDA DE ACTIVOS Y COMPONENTES
# ─────────────────────────────────────────────
ASSET_DATABASE = {
    "XLK": ["Sector / Tecnología", ["AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "ADBE", "CRM", "AMD", "TXN", "QCOM"]],
    "XLF": ["Sector / Financiero", ["JPM", "V", "MA", "BAC", "GS", "MS", "WFC", "BLK", "SPGI", "AXP"]],
    "XLE": ["Sector / Energía", ["XOM", "CVX", "COP", "SLB", "MPC", "PSX", "VLO", "OXY", "BKR", "HAL"]],
    "XLV": ["Sector / Salud", ["LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "ABT", "DHR", "PFE", "AMGN"]],
    "XLI": ["Sector / Industrial", ["GE", "CAT", "UNP", "HON", "RTX", "LOW", "DE", "LMT", "UPS", "BA"]],
    "XLP": ["Sector / Consumo Básico", ["PG", "COST", "PEP", "KO", "PM", "WMT", "MO", "MDLZ", "CL", "TGT"]],
    "XLY": ["Sector / Consumo Disc.", ["AMZN", "TSLA", "HD", "MCD", "NKE", "BKNG", "SBUX", "TJX", "ORLY", "LULU"]],
    "XLC": ["Sector / Comunicaciones", ["GOOGL", "META", "NFLX", "DIS", "TMUS", "VZ", "T", "CHTR", "CMCSA", "PARA"]],
    "SPY": ["Índice / S&P 500", ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "BRK-B", "LLY", "JPM", "TSLA"]],
    "QQQ": ["Índice / Nasdaq 100", ["AAPL", "MSFT", "NVDA", "AMZN", "META", "AVGO", "GOOGL", "GOOG", "COST", "TSLA"]],
    "BTC-USD": ["Cripto / Bitcoin", ["BTC-USD", "MSTR", "MARA", "RIOT", "CLSK"]],
    "ETH-USD": ["Cripto / Ethereum", ["ETH-USD", "COIN", "ETHE", "LINK-USD", "UNI-USD"]],
    "GLD": ["Metales / Oro", ["GLD", "NEM", "GOLD", "AU", "HMY"]],
    "SLV": ["Metales / Plata", ["SLV", "PAAS", "AG", "FSM", "WPM"]],
    "USO": ["Macro / Petróleo", ["USO", "XOM", "CVX", "OXY", "RIG"]],
    "CORN": ["Macro / Agro", ["CORN", "ADM", "BG", "CTVA", "DE"]]
}

TICKERS_LIST = sorted(list(ASSET_DATABASE.keys()))

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
def analyze_asset(symbol, category="Custom"):
    row = {"Categoría": category, "Activo": symbol}
    
    # NUEVO: Marca de Operabilidad CEDEAR
    clean_sym = symbol.split("-")[0].split(".")[0] # Limpiar sufijos de Yahoo
    row["CEDEAR (ByMA)"] = "✅ SÍ" if clean_sym in CEDEAR_LIST else "❌ NO"
    
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

def style_macro(df):
    def apply_color(val):
        if "LONG" in str(val): return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
        if "SHORT" in str(val): return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
        if "✅ SÍ" in str(val): return 'color: #00E676; font-weight: bold;'
        if "%" in str(val):
            try:
                v = float(str(val).replace("%",""))
                return f'color: {"#2E7D32" if v >= 0 else "#C62828"}; font-weight: bold;'
            except: return ''
        return ''
    return df.style.applymap(apply_color)

# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
st.title("🦅 GLOBAL MACRO TRIPLE SYNC V45")

with st.sidebar:
    st.header("⚙️ Radar Control")
    if st.button("🚀 ACTUALIZAR MATRIZ GLOBAL", type="primary", use_container_width=True):
        results = []
        prog = st.progress(0)
        for idx, sym in enumerate(TICKERS_LIST):
            prog.progress((idx+1)/len(TICKERS_LIST), text=f"Sincronizando: {sym}")
            results.append(analyze_asset(sym, ASSET_DATABASE[sym][0]))
            time.sleep(0.05)
        st.session_state["sniper_results"] = results
        st.rerun()

# TABLA PRINCIPAL
if st.session_state["sniper_results"]:
    df_f = pd.DataFrame(st.session_state["sniper_results"])
    main_cols = ["Categoría", "Activo", "Precio", "1D Signal", "1D Fecha", "1D PnL", "1S Signal", "1S Fecha", "1S PnL", "1M Signal", "1M Fecha", "1M PnL"]
    st.dataframe(style_macro(df_f[main_cols]), use_container_width=True, height=500)

    # ─────────────────────────────────────────────
    # SECCIÓN: DEEP DIVE - DESGLOSE DE COMPONENTES CON FILTRO AR
    # ─────────────────────────────────────────────
    st.divider()
    st.header("🔍 Análisis de Componentes e Inversión CEDEAR")
    
    selected_main = st.selectbox("Seleccione para desglosar acciones operables:", TICKERS_LIST)
    
    if st.button(f"🔎 AUDITAR COMPONENTES DE {selected_main}"):
        constituents = ASSET_DATABASE[selected_main][1]
        detailed_results = []
        prog_detail = st.progress(0)
        
        for idx, comp in enumerate(constituents):
            prog_detail.progress((idx+1)/len(constituents), text=f"Calculando subyacente: {comp}")
            detailed_results.append(analyze_asset(comp, f"Holding de {selected_main}"))
            time.sleep(0.05)
        
        st.subheader(f"📊 Desglose de Activos: {selected_main}")
        df_detailed = pd.DataFrame(detailed_results)
        
        # Reordenar para poner la columna CEDEAR al inicio
        cols_final = ["CEDEAR (ByMA)", "Activo", "Precio", "1D Signal", "1D Fecha", "1D PnL", "1S Signal", "1S Fecha", "1S PnL", "1M Signal", "1M Fecha", "1M PnL"]
        st.dataframe(style_macro(df_detailed[cols_final]), use_container_width=True)
else:
    st.info("Pulse 'ACTUALIZAR MATRIZ GLOBAL' para cargar el sistema.")
