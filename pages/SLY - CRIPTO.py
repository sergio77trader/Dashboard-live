import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURACIÓN DEL SISTEMA
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | CRIPTO OMNI-MATRIX")

st.markdown("""
<style>
    .stDataFrame { font-size: 10px; font-family: 'Roboto Mono', monospace; }
    h1 { color: #F3BA2F; font-weight: 800; border-bottom: 2px solid #F3BA2F; }
    .vol-info { background-color: #FFF3E0; padding: 10px; border-left: 5px solid #E64A19; border-radius: 5px; margin-bottom: 20px; color: #BF360C; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

if "sniper_results" not in st.session_state:
    st.session_state["sniper_results"] = []

# Mapeo de temporalidades solicitado para Cripto
MACRO_CONFIG = {
    "1H": "1h",
    "4H": "4h",
    "1D": "1d"
}

# ─────────────────────────────────────────────
# MOTOR DE DATOS (CCXT / KUCOIN)
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    return ccxt.kucoinfutures({"enableRateLimit": True, "timeout": 30000})

@st.cache_data(ttl=300)
def get_active_symbols(min_vol):
    try:
        ex = get_exchange()
        tickers = ex.fetch_tickers()
        valid = []
        for s, t in tickers.items():
            if "/USDT:USDT" in s:
                vol = t.get("quoteVolume", 0)
                if vol >= min_vol:
                    valid.append(s)
        return sorted(valid)
    except: return []

# ─────────────────────────────────────────────
# MOTOR TÉCNICO SLY RECURSIVO
# ─────────────────────────────────────────────
def run_sly_engine(df):
    if df.empty or len(df) < 35: return 0, 0, None
    
    # MACD
    macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
    if macd is None or macd.empty: return 0, 0, None
    hist = macd['MACDh_12_26_9']
    
    # Heikin Ashi Manual
    ha_close = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    ha_open = np.zeros(len(df)); ha_open[0] = (df['open'].iloc[0] + df['close'].iloc[0]) / 2
    for i in range(1, len(df)): ha_open[i] = (ha_open[i-1] + ha_close.iloc[i-1]) / 2
    ha_dir = np.where(ha_close > ha_open, 1, -1)
    
    state, entry_px, entry_tm = 0, 0.0, None
    for i in range(1, len(df)):
        h, h_prev, hd, hd_prev = hist.iloc[i], hist.iloc[i-1], ha_dir[i], ha_dir[i-1]
        if hd == 1 and hd_prev == -1 and h < 0 and h > h_prev: state, entry_px, entry_tm = 1, df['close'].iloc[i], df.index[i]
        elif hd == -1 and hd_prev == 1 and h > 0 and h < h_prev: state, entry_px, entry_tm = -1, df['close'].iloc[i], df.index[i]
        elif state != 0:
            if (state == 1 and h < h_prev) or (state == -1 and h > h_prev): state = 0
    return state, entry_px, entry_tm

def analyze_crypto(symbol, exchange):
    row = {"Activo": symbol.split(":")[0].replace("/USDT", ""), "Precio": 0.0}
    
    for label, tf in MACRO_CONFIG.items():
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=100)
            df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
            df['dt'] = pd.to_datetime(df['time'], unit='ms')
            df.set_index('dt', inplace=True)
            
            if tf == "1h": row["Precio"] = float(df['close'].iloc[-1])
            
            # --- CÁLCULO DE VOLUMEN SOBRE 4 HORAS ---
            if tf == "4h":
                for l in [2, 3, 4, 6, 21, 42]:
                    curr = df['vol'].tail(l).sum()
                    prev = df['vol'].iloc[-(l*2):-l].sum()
                    row[f"Vol {l}v(4H)%"] = round(((curr-prev)/prev*100), 2) if prev > 0 else 0.0
            
            st_val, px_in, tm_in = run_sly_engine(df)
            pnl = ((df['close'].iloc[-1]-px_in)/px_in*100) if st_val == 1 else ((px_in-df['close'].iloc[-1])/px_in*100) if st_val == -1 else 0.0
            
            row[f"{label} Signal"] = "LONG 🟢" if st_val == 1 else "SHORT 🔴" if st_val == -1 else "FUERA ⚪"
            row[f"{label} Fecha"] = tm_in.strftime("%d/%m %H:%M") if tm_in else "-"
            row[f"{label} PnL%"] = round(pnl, 2)
        except: pass
    return row

# ─────────────────────────────────────────────
# INTERFAZ Y CONTROL
# ─────────────────────────────────────────────
st.title("🛡️ SLY CRIPTO OMNI-MATRIX")
st.markdown('<div class="vol-info">📊 ANALÍTICA: Volumen 4 Horas (4H) | Señales 1H, 4H y 1D (Binance/KuCoin).</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Configuración")
    min_vol = st.number_input("Volumen Mínimo 24h (USDT):", value=5000000, step=1000000)
    
    if st.button("📡 1. SINCRONIZAR MERCADO", use_container_width=True):
        st.session_state["all_symbols"] = get_active_symbols(min_vol)
        st.rerun()

    if "all_symbols" in st.session_state and st.session_state["all_symbols"]:
        total = len(st.session_state["all_symbols"])
        st.success(f"Activos filtrados: {total}")
        
        b_size = st.selectbox("Tamaño Lote:", [10, 25, 50], index=1)
        batches = [st.session_state["all_symbols"][i:i+b_size] for i in range(0, total, b_size)]
        sel_batch = st.selectbox("Seleccionar Lote:", range(len(batches)), format_func=lambda x: f"Lote {x+1}")
        
        if st.button("🚀 INICIAR ESCANEO", type="primary", use_container_width=True):
            ex = get_exchange()
            results = []
            prog = st.progress(0)
            targets = batches[sel_batch]
            for idx, sym in enumerate(targets):
                prog.progress((idx+1)/len(targets), text=f"Analizando: {sym}")
                results.append(analyze_crypto(sym, ex))
                time.sleep(0.05)
            
            # Acumular
            current = {x["Activo"]: x for x in st.session_state["sniper_results"]}
            for r in results: current[r["Activo"]] = r
            st.session_state["sniper_results"] = list(current.values())
            st.rerun()

    if st.button("Limpiar Memoria"):
        st.session_state["sniper_results"] = []; st.rerun()

# ─────────────────────────────────────────────
# RENDERIZADO
# ─────────────────────────────────────────────
if st.session_state["sniper_results"]:
    df = pd.DataFrame(st.session_state["sniper_results"])
    
    def style_matrix(v):
        if "LONG" in str(v): return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
        if "SHORT" in str(v): return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
        if isinstance(v, (int, float)):
            if v > 0: return 'color: #2E7D32; font-weight: bold;'
            if v < 0: return 'color: #C62828; font-weight: bold;'
        return ''

    st.dataframe(
        df.style.map(style_matrix),
        use_container_width=True,
        height=800,
        column_config={
            "Precio": st.column_config.NumberColumn(format="%.4f"),
            "1H PnL%": st.column_config.NumberColumn(format="%.2f%%"),
            "4H PnL%": st.column_config.NumberColumn(format="%.2f%%"),
            "1D PnL%": st.column_config.NumberColumn(format="%.2f%%"),
            "Vol 2v(4H)%": st.column_config.NumberColumn(format="%.2f%%"),
            "Vol 42v(4H)%": st.column_config.NumberColumn(format="%.2f%%"),
        }
    )
else:
    st.info("👈 Inicie el escaneo para visualizar la matriz cripto.")
