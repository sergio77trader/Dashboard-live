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
st.set_page_config(layout="wide", page_title="SLY | CRIPTO ALPHA TERMINAL")

st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    .stDataFrame { font-size: 12px; font-family: 'Roboto Mono', monospace; }
    h1 { color: #00897B; font-weight: 800; border-bottom: 2px solid #00897B; }
    .stButton>button { border-radius: 8px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

if "accumulated_results" not in st.session_state:
    st.session_state["accumulated_results"] = []
if "all_symbols" not in st.session_state:
    st.session_state["all_symbols"] = []
if "pointer" not in st.session_state:
    st.session_state["pointer"] = 0

# ─────────────────────────────────────────────
# MOTOR TÉCNICO SLY RECURSIVO (Manual HA)
# ─────────────────────────────────────────────
def run_sly_engine(df):
    if df.empty or len(df) < 35: return "FUERA ⚪", "-", "-"
    
    # 1. MACD
    macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
    hist = macd['MACDh_12_26_9']
    
    # 2. Heikin Ashi Manual
    ha_close = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    ha_open = np.zeros(len(df))
    ha_open[0] = (df['open'].iloc[0] + df['close'].iloc[0]) / 2
    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i-1] + ha_close.iloc[i-1]) / 2
    ha_dir = np.where(ha_close > ha_open, 1, -1)
    
    # 3. Máquina de Estados (Igual que el Script de Acciones)
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
            state, entry_px, entry_tm = 1, df['close'].iloc[i], df['dt'].iloc[i]
        elif shrtC:
            state, entry_px, entry_tm = -1, df['close'].iloc[i], df['dt'].iloc[i]
        elif state != 0:
            # Salida por giro de momentum
            if (state == 1 and h < h_prev) or (state == -1 and h > h_prev):
                state = 0
                
    if state != 0:
        pnl = (df['close'].iloc[-1] - entry_px) / entry_px * 100 if state == 1 else (entry_px - df['close'].iloc[-1]) / entry_px * 100
        signal = "LONG 🟢" if state == 1 else "SHORT 🔴"
        return signal, entry_tm.strftime("%d/%m/%y"), f"{pnl:+.2f}%"
    
    return "FUERA ⚪", "-", "-"

# ─────────────────────────────────────────────
# MOTOR DE DATOS (KUCOIN)
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    return ccxt.kucoin({"enableRateLimit": True, "timeout": 30000})

def fetch_universe():
    try:
        ex = get_exchange()
        markets = ex.load_markets()
        symbols = [s for s in markets if '/USDT' in s and markets[s].get('active', True)]
        return sorted(symbols)
    except: return []

# ─────────────────────────────────────────────
# ESCÁNER DE BLOQUE
# ─────────────────────────────────────────────
def scan_crypto_batch(targets, btc_change):
    ex = get_exchange()
    new_data = []
    prog = st.progress(0)
    
    for idx, sym in enumerate(targets):
        prog.progress((idx+1)/len(targets), text=f"Analizando {sym}")
        try:
            # Pedimos 100 velas diarias para el Warm-up
            ohlcv = ex.fetch_ohlcv(sym, timeframe='1d', limit=100)
            if not ohlcv or len(ohlcv) < 50: continue
            
            df = pd.DataFrame(ohlcv, columns=['t','open','high','low','close','v'])
            df['dt'] = pd.to_datetime(df['t'], unit='ms')
            
            # Calculamos Delta vs BTC
            alt_change = ((df['close'].iloc[-1] / df['close'].iloc[-2]) - 1) * 100
            delta_btc = alt_change - btc_change
            
            # Corremos lógica SLY
            signal, fecha, pnl = run_sly_engine(df)
            
            new_data.append({
                "Activo": sym.replace("/USDT", ""),
                "Precio": f"{df['close'].iloc[-1]:,.4f}",
                "Vs BTC (Delta)": round(delta_btc, 2),
                "1D Signal": signal,
                "1D Fecha": fecha,
                "1D PnL": pnl
            })
            time.sleep(0.1)
        except: continue
    
    prog.empty()
    return new_data

# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
st.title("🛡️ SLY CRIPTO ALPHA TERMINAL")

with st.sidebar:
    st.header("🎯 Radar de Lotes")
    if st.button("📡 1. CARGAR MERCADO KUCOIN"):
        st.session_state["all_symbols"] = fetch_universe()
        st.rerun()
    
    if st.session_state["all_symbols"]:
        b_size = st.number_input("Tamaño Lote:", 10, 100, 50)
        pointer = st.session_state["pointer"]
        
        if st.button(f"🚀 ESCANEAR LOTE {pointer} a {pointer+b_size}"):
            ex = get_exchange()
            btc_ticker = ex.fetch_ticker('BTC/USDT')
            btc_change = btc_ticker.get('percentage', 0)
            
            targets = st.session_state["all_symbols"][pointer : pointer+b_size]
            results = scan_crypto_batch(targets, btc_change)
            
            # Acumular
            existing = {x["Activo"]: x for x in st.session_state["accumulated_results"]}
            for r in results: existing[r["Activo"]] = r
            st.session_state["accumulated_results"] = list(existing.values())
            st.session_state["pointer"] += b_size
            st.rerun()

    if st.button("🗑️ LIMPIAR TODO"):
        st.session_state["accumulated_results"] = []
        st.session_state["pointer"] = 0
        st.rerun()

# ─────────────────────────────────────────────
# RENDERIZADO DE TABLA (ESTILO IMAGEN)
# ─────────────────────────────────────────────
if st.session_state["accumulated_results"]:
    df_final = pd.DataFrame(st.session_state["accumulated_results"])
    
    def style_table(val):
        if "LONG" in str(val): return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
        if "SHORT" in str(val): return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
        if "%" in str(val):
            try:
                v = float(val.replace("%",""))
                return f'color: {"#2E7D32" if v >= 0 else "#C62828"}; font-weight: bold;'
            except: return ''
        return ''

    st.subheader(f"📊 Tabla de Inteligencia Acumulada ({len(df_final)} activos)")
    # Reordenar para que sea igual a la imagen
    df_final = df_final[["Activo", "Precio", "Vs BTC (Delta)", "1D Signal", "1D Fecha", "1D PnL"]]
    st.dataframe(df_final.style.applymap(style_table), use_container_width=True, height=600)
else:
    st.info("👈 Utiliza el panel lateral para iniciar el escaneo de Alpha.")
