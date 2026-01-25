import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY DASHBOARD | V34.0 MIRROR")

st.markdown("""
<style>
    .stDataFrame { font-size: 12px; font-family: monospace; }
    h1 { color: #2962FF; font-weight: 800; border-bottom: 2px solid #2962FF; }
</style>
""", unsafe_allow_html=True)

if "sniper_results" not in st.session_state:
    st.session_state["sniper_results"] = []

TIMEFRAMES = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1H": "1h", "4H": "4h", "1D": "1d"
}

# ─────────────────────────────────────────────
# MOTOR DE CONEXIÓN
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    return ccxt.kucoinfutures({"enableRateLimit": True, "timeout": 45000})

@st.cache_data(ttl=600)
def get_active_pairs():
    try:
        ex = get_exchange()
        tickers = ex.fetch_tickers()
        return [s for s, t in tickers.items() if "/USDT:USDT" in s and t.get("quoteVolume", 0) > 10000]
    except: return []

# ─────────────────────────────────────────────
# NÚCLEO SLY MIRROR (PINE SCRIPT CLONE)
# ─────────────────────────────────────────────
def run_sly_mirror_engine(df, use_ema, use_zero):
    # 1. EMA 200 Exacta (Necesita mucho historial para coincidir con TV)
    ema200 = ta.ema(df['close'], length=200)
    
    # 2. MACD Exacto (ta.macd de Pine)
    macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
    hist = macd['MACDh_12_26_9']

    # 3. Heikin Ashi Recursivo (Cálculo exacto Pine)
    ha_close = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    ha_open = np.zeros(len(df))
    # Inicialización: na(haOpen[1]) ? (open + close) / 2
    ha_open[0] = (df['open'].iloc[0] + df['close'].iloc[0]) / 2
    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i-1] + ha_close.iloc[i-1]) / 2
    
    ha_color = np.where(ha_close > ha_open, 1, -1)

    # 4. Simulación de Máquina de Estados (Loop barra por barra)
    estado = 0
    entry_time = None
    
    # Empezamos el loop desde la vela 201 para que la EMA200 sea idéntica a TV
    for i in range(200, len(df)):
        h = hist.iloc[i]
        h_prev = hist.iloc[i-1]
        price = df['close'].iloc[i]
        e200 = ema200.iloc[i]
        
        # Saltamos si hay nulos
        if pd.isna(e200) or pd.isna(h): continue

        # --- LÓGICA SLY DASHBOARD ---
        
        # A. Salidas (Ocurren antes que las entradas en Pine)
        if estado == 1 and h < h_prev: # hist_bajando
            estado = 0
        elif estado == -1 and h > h_prev: # hist_subiendo
            estado = 0
            
        # B. Entradas (Solo si estamos en estado 0)
        if estado == 0:
            f_ema_long = (price > e200) if use_ema else True
            f_ema_short = (price < e200) if use_ema else True
            f_zero_long = (h < 0) if use_zero else True
            f_zero_short = (h > 0) if use_zero else True
            
            long_cond = (ha_color[i] == 1) and (h > h_prev) and f_ema_long and f_zero_long
            short_cond = (ha_color[i] == -1) and (h < h_prev) and f_ema_short and f_zero_short
            
            if long_cond:
                estado = 1
                entry_time = df['dt'].iloc[i]
            elif short_cond:
                estado = -1
                entry_time = df['dt'].iloc[i]
                
    return estado, entry_time

# ─────────────────────────────────────────────
# ANALIZADOR MTF
# ─────────────────────────────────────────────
def analyze_ticker(symbol, exchange, utc_h, use_ema, use_zero):
    row = {"Activo": symbol.split(":")[0].replace("/USDT", "")}
    
    for label, tf_code in TIMEFRAMES.items():
        try:
            # Pedimos 1000 velas para convergencia total de la EMA
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=1000)
            
            if not ohlcv or len(ohlcv) < 250:
                row[f"{label} Señal"] = "POCO HIST."
                row[f"{label} Horario"] = "-"
                continue
                
            df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
            df['dt'] = pd.to_datetime(df['time'], unit='ms')
            
            st_val, tm_val = run_sly_mirror_engine(df, use_ema, use_zero)
            
            if st_val == 1:
                row[f"{label} Señal"] = "LONG 🟢"
                row[f"{label} Horario"] = (tm_val + pd.Timedelta(hours=utc_h)).strftime("%d/%m %H:%M")
            elif st_val == -1:
                row[f"{label} Señal"] = "SHORT 🔴"
                row[f"{label} Horario"] = (tm_val + pd.Timedelta(hours=utc_h)).strftime("%d/%m %H:%M")
            else:
                row[f"{label} Señal"] = "FUERA ⚪"
                row[f"{label} Horario"] = "-"
        except:
            row[f"{label} Señal"] = "Error"
            row[f"{label} Horario"] = "-"
            
    return row

# ─────────────────────────────────────────────
# UI Streamlit
# ─────────────────────────────────────────────
st.title("🎯 SLY DASHBOARD | TRADINGVIEW MIRROR V34")

with st.sidebar:
    st.header("Configuración de Filtros")
    u_ema = st.checkbox("Filtro EMA 200", value=True)
    u_zero = st.checkbox("Filtro Cruce Cero", value=False)
    utc_val = st.number_input("Horario UTC Offset", value=-3)
    
    st.divider()
    all_pairs = get_active_pairs()
    if all_pairs:
        st.success(f"Mercado: {len(all_pairs)} activos")
        b_size = st.selectbox("Batch Size", [10, 20, 50], index=1)
        batches = [all_pairs[i:i+b_size] for i in range(0, len(all_pairs), b_size)]
        sel_batch = st.selectbox("Lote", range(len(batches)), format_func=lambda x: f"Lote {x} ({len(batches[x])} pares)")
        
        if st.button("🚀 SINCRONIZAR", type="primary", use_container_width=True):
            ex = get_exchange()
            results = []
            prog = st.progress(0)
            for idx, sym in enumerate(batches[sel_batch]):
                prog.progress((idx+1)/len(batches[sel_batch]), text=f"Clonando data de {sym}")
                results.append(analyze_ticker(sym, ex, utc_val, u_ema, u_zero))
                time.sleep(0.1)
            st.session_state["sniper_results"] = results
            prog.empty()

    if st.button("Limpiar Memoria"):
        st.session_state["sniper_results"] = []
        st.rerun()

# RENDERIZADO
if st.session_state["sniper_results"]:
    df_final = pd.DataFrame(st.session_state["sniper_results"])
    
    def color_signals(val):
        if "LONG" in str(val): return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold'
        if "SHORT" in str(val): return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold'
        return ''

    st.dataframe(df_final.style.applymap(color_signals), use_container_width=True, height=800)
else:
    st.info("👈 Presione SINCRONIZAR para obtener los datos idénticos a TradingView.")
