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
st.set_page_config(layout="wide", page_title="STOCKS SNIPER V37.0 | SLY REPLICA")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 14px; }
    .stDataFrame { font-size: 12px; font-family: monospace; }
    h1 { color: #00897B; font-weight: 800; border-bottom: 2px solid #00897B; }
</style>
""", unsafe_allow_html=True)

if "sniper_results" not in st.session_state:
    st.session_state["sniper_results"] = []

# ─────────────────────────────────────────────
# BÓVEDA UNIFICADA (SCRIPTS V1 A V6)
# ─────────────────────────────────────────────
MASTER_TICKERS = sorted([
    # ARGENTINA ADRs
    'GGAL', 'YPF', 'BMA', 'PAMP', 'TGS', 'CEPU', 'EDN', 'BFR', 'SUPV', 'CRESY', 'IRS', 'TEO', 'LOMA', 'DESP', 'VIST', 'GLOB', 'MELI', 'BIOX', 'TX',
    # TECH & SEMIS
    'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NFLX', 'CRM', 'ORCL', 'ADBE', 'IBM', 'CSCO', 'PLTR', 'SNOW', 'SHOP', 'SPOT', 'UBER', 'ABNB', 'AMD', 'INTC', 'QCOM', 'AVGO', 'TXN', 'MU', 'ADI', 'AMAT', 'ARM', 'SMCI', 'TSM', 'ASML', 'LRCX',
    # FINANZAS & CONSUMO
    'JPM', 'BAC', 'C', 'WFC', 'GS', 'MS', 'V', 'MA', 'AXP', 'BRK-B', 'PYPL', 'SQ', 'COIN', 'BLK', 'USB', 'NU', 'KO', 'PEP', 'MCD', 'SBUX', 'DIS', 'NKE', 'WMT', 'COST', 'TGT', 'HD', 'LOW', 'PG', 'CL', 'MO', 'PM', 'KMB', 'EL',
    # ENERGÍA, MINERÍA & INDUSTRIAL
    'JNJ', 'PFE', 'MRK', 'LLY', 'ABBV', 'UNH', 'BMY', 'AMGN', 'GILD', 'AZN', 'NVO', 'NVS', 'CVS', 'BA', 'CAT', 'DE', 'GE', 'MMM', 'LMT', 'RTX', 'HON', 'UNP', 'UPS', 'FDX', 'XOM', 'CVX', 'SLB', 'OXY', 'HAL', 'BP', 'SHEL', 'TTE', 'PBR', 'VLO', 'VALE', 'ITUB', 'BBD', 'ERJ', 'ABEV', 'GGB', 'SID', 'NBR', 'GOLD', 'NEM', 'PAAS', 'FCX', 'SCCO', 'RIO', 'BHP', 'ALB', 'SQM',
    # ETFs
    'SPY', 'QQQ', 'IWM', 'DIA', 'EEM', 'EWZ', 'FXI', 'XLE', 'XLF', 'XLK', 'XLV', 'XLI', 'XLP', 'XLU', 'XLY', 'ARKK', 'SMH', 'TAN', 'GLD', 'SLV', 'GDX'
])

# ─────────────────────────────────────────────
# MOTOR TÉCNICO REPLICA TRADINGVIEW
# ─────────────────────────────────────────────
def calculate_heikin_ashi(df):
    ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    ha_open = np.zeros(len(df))
    ha_open[0] = (df['Open'].iloc[0] + df['Close'].iloc[0]) / 2
    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i-1] + ha_close.iloc[i-1]) / 2
    return ha_open, ha_close

def run_sly_logic(df):
    # MACD
    macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
    hist = macd['MACDh_12_26_9']
    
    # Heikin Ashi
    ha_open, ha_close = calculate_heikin_ashi(df)
    ha_dir = np.where(ha_close > ha_open, 1, -1)
    
    # Máquina de Estados (State Machine)
    state = 0
    entry_price = 0.0
    entry_time = None
    
    for i in range(1, len(df)):
        h = hist.iloc[i]
        h_prev = hist.iloc[i-1]
        hd = ha_dir[i]
        hd_prev = ha_dir[i-1]
        
        # Condiciones Script 6
        longCond = (hd == 1 and hd_prev == -1 and h < 0 and h > h_prev)
        shortCond = (hd == -1 and hd_prev == 1 and h > 0 and h < h_prev)
        
        if longCond:
            state = 1
            entry_price = df['Close'].iloc[i]
            entry_time = df.index[i]
        elif shortCond:
            state = -1
            entry_price = df['Close'].iloc[i]
            entry_time = df.index[i]
        elif state != 0:
            # Salida dinámica por giro de histograma
            if (state == 1 and h < h_prev) or (state == -1 and h > h_prev):
                state = 0
                
    return state, entry_price, entry_time

# ─────────────────────────────────────────────
# ANALIZADOR
# ─────────────────────────────────────────────
def analyze_ticker(symbol, interval):
    try:
        # Descarga con periodos optimizados por intervalo
        period = "1mo" if "m" in interval else "2y"
        df = yf.download(symbol, interval=interval, period=period, progress=False, auto_adjust=True)
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        if df.empty or len(df) < 35: return None

        state, p_entry, t_entry = run_sly_logic(df)
        curr_p = df['Close'].iloc[-1]
        
        # PnL Calculation
        pnl_val = 0.0
        if state == 1: pnl_val = (curr_p - p_entry) / p_entry * 100
        elif state == -1: pnl_val = (p_entry - curr_p) / p_entry * 100
        
        return {
            "Activo": symbol,
            "Estado": "LONG 🟢" if state == 1 else "SHORT 🔴" if state == -1 else "FUERA",
            "Precio": f"{curr_p:.2f}",
            "Hora": t_entry.strftime("%d/%m %H:%M") if t_entry else "-",
            "PnL": f"{pnl_val:.2f}%" if state != 0 else "-"
        }
    except: return None

# ─────────────────────────────────────────────
# INTERFAZ Streamlit
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("🎯 Stock Sniper Control")
    tf_selected = st.selectbox("Temporalidad (TF):", ["1m", "5m", "15m", "30m", "1h", "1d"], index=4)
    
    # Manejo de Lotes
    b_size = st.selectbox("Tamaño del Lote:", [10, 20, 50, 100], index=1)
    batches = [MASTER_TICKERS[i:i+b_size] for i in range(0, len(MASTER_TICKERS), b_size)]
    sel_batch = st.selectbox("Seleccionar Lote:", range(len(batches)), format_func=lambda x: f"Lote {x} ({len(batches[x])} activos)")
    
    acc = st.checkbox("Acumular Resultados", value=True)
    
    if st.button("🚀 INICIAR ESCANEO", type="primary"):
        results = []
        prog = st.progress(0)
        targets = batches[sel_batch]
        
        for idx, sym in enumerate(targets):
            prog.progress((idx+1)/len(targets), text=f"Analizando {sym}...")
            res = analyze_ticker(sym, tf_selected)
            if res: results.append(res)
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
# TABLA FINAL (LEGIBILIDAD INSTITUCIONAL)
# ─────────────────────────────────────────────
st.title("🦅 SLY SYSTEMATRADER STOCKS")

if st.session_state["sniper_results"]:
    df_f = pd.DataFrame(st.session_state["sniper_results"])
    
    def style_matrix(val):
        if "LONG" in str(val): return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
        if "SHORT" in str(val): return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
        if "%" in str(val):
            v = float(val.replace("%",""))
            return f'color: {"#2E7D32" if v >= 0 else "#C62828"}; font-weight: bold;'
        return ''

    st.dataframe(df_f.style.applymap(style_matrix), use_container_width=True, height=800)
else:
    st.info("👈 Seleccione un lote y presione INICIAR ESCANEO para ver los estados del mercado.")
