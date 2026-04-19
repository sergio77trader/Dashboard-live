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
st.set_page_config(layout="wide", page_title="SYSTEMATRADER | TRIPLE MACRO SYNC V47.1")

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

MASTER_TICKERS = sorted([
    'GGAL', 'YPF', 'BMA', 'PAMP', 'TGS', 'CEPU', 'EDN', 'BFR', 'SUPV', 'CRESY', 'IRS', 'TEO', 'LOMA', 'DESP', 'VIST', 'GLOB', 'MELI', 'BIOX', 'TX',
    'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NFLX', 'CRM', 'ORCL', 'ADBE', 'IBM', 'CSCO', 'PLTR', 'SNOW', 'SHOP', 'SPOT', 'UBER', 'ABNB', 'AMD', 'INTC', 'QCOM', 'AVGO', 'TXN', 'MU', 'ADI', 'AMAT', 'ARM', 'SMCI', 'TSM', 'ASML', 'LRCX',
    'JPM', 'BAC', 'C', 'WFC', 'GS', 'MS', 'V', 'MA', 'AXP', 'BRK-B', 'PYPL', 'SQ', 'COIN', 'BLK', 'USB', 'NU', 'KO', 'PEP', 'MCD', 'SBUX', 'DIS', 'NKE', 'WMT', 'COST', 'TGT', 'HD', 'LOW', 'PG', 'CL', 'MO', 'PM', 'KMB', 'EL',
    'JNJ', 'PFE', 'MRK', 'LLY', 'ABBV', 'UNH', 'BMY', 'AMGN', 'GILD', 'AZN', 'NVO', 'NVS', 'CVS', 'BA', 'CAT', 'DE', 'GE', 'MMM', 'LMT', 'RTX', 'HON', 'UNP', 'UPS', 'FDX', 'XOM', 'CVX', 'SLB', 'OXY', 'HAL', 'BP', 'SHEL', 'TTE', 'PBR', 'VLO', 'VALE', 'ITUB', 'BBD', 'ERJ', 'ABEV', 'GGB', 'SID', 'NBR', 'GOLD', 'NEM', 'PAAS', 'FCX', 'SCCO', 'RIO', 'BHP', 'ALB', 'SQM',
    'SPY', 'QQQ', 'IWM', 'DIA', 'EEM', 'EWZ', 'FXI', 'XLE', 'XLF', 'XLK', 'XLV', 'XLI', 'XLP', 'XLU', 'XLY', 'ARKK', 'SMH', 'TAN', 'GLD', 'SLV', 'GDX'
])

# ─────────────────────────────────────────────
# MOTOR TÉCNICO SLY RECURSIVO (HEIKIN ASHI + MACD)
# ─────────────────────────────────────────────
def run_sly_engine(df):
    if df.empty or len(df) < 35: return 0, 0, None
    
    # Limpieza de datos
    df = df.copy()
    
    # 1. MACD
    macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
    if macd is None or macd.empty: return 0, 0, None
    hist = macd['MACDh_12_26_9']
    
    # 2. Heikin Ashi Manual (Recursivo)
    ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    ha_open = np.zeros(len(df))
    ha_open[0] = (df['Open'].iloc[0] + df['Close'].iloc[0]) / 2
    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i-1] + ha_close.iloc[i-1]) / 2
    ha_dir = np.where(ha_close > ha_open, 1, -1)
    
    # 3. Máquina de Estados (State Machine)
    state = 0
    entry_px = 0.0
    entry_tm = None
    
    for i in range(1, len(df)):
        h, h_prev = hist.iloc[i], hist.iloc[i-1]
        hd, hd_prev = ha_dir[i], ha_dir[i-1]
        
        # Gatillos SLY
        longC = (hd == 1 and hd_prev == -1 and h < 0 and h > h_prev)
        shrtC = (hd == -1 and hd_prev == 1 and h > 0 and h < h_prev)
        
        if longC:
            state, entry_px, entry_tm = 1, df['Close'].iloc[i], df.index[i]
        elif shrtC:
            state, entry_px, entry_tm = -1, df['Close'].iloc[i], df.index[i]
        elif state != 0:
            # Salida por agotamiento de momentum (Mntm Exit)
            if (state == 1 and h < h_prev) or (state == -1 and h > h_prev):
                state = 0
                
    return state, entry_px, entry_tm

# ─────────────────────────────────────────────
# ANALIZADOR TRIPLE CICLO
# ─────────────────────────────────────────────
def analyze_triple_cycle(symbol):
    row = {"Activo": symbol}
    current_price = None
    
    for tf_key, config in MACRO_CONFIG.items():
        try:
            df = yf.download(symbol, interval=config['int'], period=config['per'], progress=False, auto_adjust=True)
            
            # Parche para MultiIndex de yfinance v0.2.x
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            if df.empty or len(df) < 50:
                row[f"{tf_key} Signal"] = "S/D"
                continue
            
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
        except Exception:
            row[f"{tf_key} Signal"] = "ERR"
            
    row["Precio"] = f"{current_price:.2f}" if current_price else "-"
    return row

# ─────────────────────────────────────────────
# INTERFAZ Streamlit
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("🦅 Control Triple Sync")
    
    b_size = st.selectbox("Tamaño Lote:", [10, 20, 50], index=1)
    batches = [MASTER_TICKERS[i:i+b_size] for i in range(0, len(MASTER_TICKERS), b_size)]
    sel_batch = st.selectbox("Seleccionar Lote:", range(len(batches)), format_func=lambda x: f"Lote {x} ({len(batches[x])} activos)")
    
    acc = st.checkbox("Acumular Resultados", value=True)
    
    if st.button("🚀 ESCANEAR MATRIZ MACRO", type="primary", use_container_width=True):
        results = []
        prog = st.progress(0)
        targets = batches[sel_batch]
        
        for idx, sym in enumerate(targets):
            prog.progress((idx+1)/len(targets), text=f"Procesando: {sym}")
            res = analyze_triple_cycle(sym)
            results.append(res)
            time.sleep(0.05) # Jitter estocástico para evitar 429 de Yahoo
            
        if acc:
            # Unión inteligente por Activo
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
# TABLA FINAL (RENDERIZADO CON PARCHE .map)
# ─────────────────────────────────────────────
st.title("🦅 SLY TRIPLE MACRO MATRIX")

if st.session_state["sniper_results"]:
    df_final = pd.DataFrame(st.session_state["sniper_results"])
    
    # Columnas ordenadas
    cols_order = ["Activo", "Precio", 
                  "1D Signal", "1D Fecha", "1D PnL",
                  "1S Signal", "1S Fecha", "1S PnL",
                  "1M Signal", "1M Fecha", "1M PnL"]
    
    df_final = df_final[[c for c in cols_order if c in df_final.columns]]

    def style_table(val):
        str_val = str(val)
        if "LONG" in str_val: return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
        if "SHORT" in str_val: return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
        if "%" in str_val:
            try:
                v = float(str_val.replace("%",""))
                return f'color: {"#2E7D32" if v >= 0 else "#C62828"}; font-weight: bold;'
            except: return ''
        return ''

    # El cambio fundamental: .applymap() -> .map()
    # Usamos try-except para máxima compatibilidad institucional
    try:
        st.dataframe(df_final.style.map(style_table), use_container_width=True, height=800)
    except AttributeError:
        st.dataframe(df_final.style.applymap(style_table), use_container_width=True, height=800)
else:
    st.info("👈 Presione el botón para iniciar la sincronización de activos.")
