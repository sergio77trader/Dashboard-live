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
st.set_page_config(layout="wide", page_title="SYSTEMATRADER | RSI MACRO MATRIX")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 14px; }
    .stDataFrame { font-size: 12px; border: 1px solid #333; }
    h1 { color: #00E676; font-weight: 800; border-bottom: 2px solid #00E676; }
</style>
""", unsafe_allow_html=True)

if "rsi_matrix_results" not in st.session_state:
    st.session_state["rsi_matrix_results"] = []

# Periodos definidos por el usuario
RSI_PERIODS = [2, 4, 8, 12, 24, 84, 168]

# ─────────────────────────────────────────────
# MOTOR DE DATOS
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    ex = ccxt.kucoinfutures({"enableRateLimit": True, "timeout": 30000})
    ex.load_markets()
    return ex

@st.cache_data(ttl=300)
def get_active_pairs_by_vol(min_vol):
    try:
        ex = get_exchange()
        tickers = ex.fetch_tickers()
        valid = []
        for s, t in tickers.items():
            if "/USDT:USDT" in s and t.get("quoteVolume", 0) >= min_vol:
                valid.append({"symbol": s, "vol": t["quoteVolume"]})
        return pd.DataFrame(valid).sort_values("vol", ascending=False)["symbol"].tolist()
    except: return []

# ─────────────────────────────────────────────
# CÁLCULOS TÉCNICOS
# ─────────────────────────────────────────────
def calculate_heikin_ashi(df):
    df = df.copy()
    df["HA_Close"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
    ha_open = [df["open"].iloc[0]]
    for i in range(1, len(df)):
        ha_open.append((ha_open[-1] + df["HA_Close"].iloc[i-1]) / 2)
    df["HA_Open"] = ha_open
    df["HA_Color"] = np.where(df["HA_Close"] > df["HA_Open"], 1, -1)
    return df

def analyze_ticker_rsi_logic(symbol, exchange, current_price):
    try:
        # Necesitamos suficiente data para el RSI 168
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=300)
        if not ohlcv or len(ohlcv) < 170: return None
        
        ohlcv[-1][4] = current_price
        df = pd.DataFrame(ohlcv, columns=["time", "open", "high", "low", "close", "vol"])
        
        # 1. MACD (12, 26, 9)
        macd = ta.macd(df["close"])
        df["Hist"] = macd["MACDh_12_26_9"]
        
        # 2. Heikin Ashi
        df = calculate_heikin_ashi(df)
        
        # 3. RSIs con suavizado dinámico
        rsi_signals = {}
        for p in RSI_PERIODS:
            rsi_raw = ta.rsi(df["close"], length=p)
            # Aplicamos suavizado (Smoothing) igual al periodo
            rsi_smooth = ta.sma(rsi_raw, length=p)
            
            curr_rsi = rsi_smooth.iloc[-1]
            prev_rsi = rsi_smooth.iloc[-2]
            
            if curr_rsi > prev_rsi:
                rsi_signals[f"RSI {p}"] = "📈 SUBE"
            else:
                rsi_signals[f"RSI {p}"] = "📉 BAJA"

        # Lógica MACD Hist + HA
        hist_now = df["Hist"].iloc[-1]
        hist_prev = df["Hist"].iloc[-2]
        ha_now = df["HA_Color"].iloc[-1]
        ha_prev = df["HA_Color"].iloc[-2]
        
        macd_momentum = "Neutral"
        if hist_now > hist_prev:
            macd_momentum = "Acelerando 🚀" if hist_now > 0 else "Recuperando ⤴️"
        else:
            macd_momentum = "Cediendo 📉" if hist_now > 0 else "Cayendo 🩸"
            
        ha_status = "VERDE 🟢" if ha_now == 1 else "ROJO 🔴"
        ha_change = "CAMBIO" if ha_now != ha_prev else "Mantiene"

        return {
            "RSI_Data": rsi_signals,
            "MACD_Hist": macd_momentum,
            "HA_Color": ha_status,
            "HA_Trend": ha_change
        }
    except Exception as e:
        return None

# ─────────────────────────────────────────────
# INTERFAZ DE CONTROL
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuración RSI Sync")
    min_volume = st.number_input("Volumen Mínimo (USDT):", value=1000000, step=100000)
    all_sym = get_active_pairs_by_vol(min_volume)
    
    if all_sym:
        st.success(f"Activos disponibles: {len(all_sym)}")
        b_size = st.selectbox("Lote:", [10, 20, 50], index=1)
        batches = [all_sym[i:i+b_size] for i in range(0, len(all_sym), b_size)]
        sel_lote = st.selectbox("Seleccionar Lote:", range(len(batches)))
        
        if st.button("🚀 INICIAR ESCANEO", type="primary", use_container_width=True):
            ex = get_exchange()
            results = []
            prog = st.progress(0)
            targets = batches[sel_lote]
            
            for idx, sym in enumerate(targets):
                prog.progress((idx+1)/len(targets), text=f"Analizando {sym}")
                try:
                    price = ex.fetch_ticker(sym)["last"]
                    analysis = analyze_ticker_rsi_logic(sym, ex, price)
                    if analysis:
                        row = {
                            "Activo": sym.split(":")[0].replace("/USDT", ""),
                            "Precio": f"{price:,.4f}",
                            "HA 1H": analysis["HA_Color"],
                            "HA Estado": analysis["HA_Trend"],
                            "MACD Hist": analysis["MACD_Hist"]
                        }
                        # Integrar los RSIs en la fila
                        row.update(analysis["RSI_Data"])
                        results.append(row)
                except: continue
                time.sleep(0.1)
            
            st.session_state["rsi_matrix_results"] = results
            prog.empty()

    if st.button("Limpiar Memoria"):
        st.session_state["rsi_matrix_results"] = []
        st.rerun()

# ─────────────────────────────────────────────
# RENDERIZADO DE TABLA
# ─────────────────────────────────────────────
st.title("🎯 SNIPER MATRIX: CONVERGENCIA RSI & MACD")

if st.session_state["rsi_matrix_results"]:
    df = pd.DataFrame(st.session_state["rsi_matrix_results"])
    
    def style_matrix(val):
        color = ''
        if "SUBE" in str(val) or "Acelerando" in str(val) or "VERDE" in str(val) or "Recuperando" in str(val):
            color = 'background-color: #d4edda; color: #155724;'
        elif "BAJA" in str(val) or "Cayendo" in str(val) or "ROJO" in str(val) or "Cediendo" in str(val):
            color = 'background-color: #f8d7da; color: #721c24;'
        return color

    # Ordenar columnas para visualización lógica
    cols = ["Activo", "Precio", "HA 1H", "HA Estado", "MACD Hist"] + [f"RSI {p}" for p in RSI_PERIODS]
    st.dataframe(df[cols].style.applymap(style_matrix), use_container_width=True, height=800)
else:
    st.info("👈 Configure el volumen y el lote para iniciar el análisis multitemporal de RSI.")
