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
st.set_page_config(layout="wide", page_title="SYSTEMATRADER | RSI MACRO MATRIX V27.1")

st.markdown("""
<style>
    .stDataFrame { font-size: 12px; }
    h1 { color: #2962FF; font-weight: 800; border-bottom: 2px solid #2962FF; }
</style>
""", unsafe_allow_html=True)

if "rsi_matrix_results" not in st.session_state:
    st.session_state["rsi_matrix_results"] = []

RSI_PERIODS = [2, 4, 8, 12, 24, 84, 168]

# ─────────────────────────────────────────────
# MOTOR DE DATOS (SIN CACHÉ AGRESIVO)
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    return ccxt.kucoinfutures({"enableRateLimit": True, "timeout": 30000})

# Eliminamos el cache de los pares para tener precios frescos
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
# CÁLCULOS TÉCNICOS (REPLICA TRADINGVIEW)
# ─────────────────────────────────────────────
def calculate_heikin_ashi(df):
    df = df.copy()
    # HA Close
    df["HA_Close"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
    # HA Open (Recursivo)
    ha_open = [ (df["open"].iloc[0] + df["close"].iloc[0]) / 2 ]
    for i in range(1, len(df)):
        ha_open.append((ha_open[-1] + df["HA_Close"].iloc[i-1]) / 2)
    df["HA_Open"] = ha_open
    df["HA_Color"] = np.where(df["HA_Close"] > df["HA_Open"], 1, -1)
    return df

def analyze_ticker_rsi_logic(symbol, exchange):
    try:
        # Descargamos un poco más de data para estabilizar el RSI 168
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=400)
        if not ohlcv or len(ohlcv) < 200: return None
        
        df = pd.DataFrame(ohlcv, columns=["time", "open", "high", "low", "close", "vol"])
        
        # 1. MACD (12, 26, 9)
        macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
        df["Hist"] = macd["MACDh_12_26_9"]
        
        # 2. Heikin Ashi
        df = calculate_heikin_ashi(df)
        
        # 3. RSIs con suavizado EMA (Standard TV)
        rsi_signals = {}
        for p in RSI_PERIODS:
            rsi_raw = ta.rsi(df["close"], length=p)
            # El Smoothing Length pedido: aplicamos EMA sobre el RSI
            rsi_smooth = ta.ema(rsi_raw, length=p)
            
            curr_rsi = rsi_smooth.iloc[-1]
            prev_rsi = rsi_smooth.iloc[-2]
            
            if curr_rsi > prev_rsi:
                rsi_signals[f"RSI {p}"] = f"📈 SUBE ({round(curr_rsi,1)})"
            else:
                rsi_signals[f"RSI {p}"] = f"📉 BAJA ({round(curr_rsi,1)})"

        # Lógica MACD Hist + HA (Basado en tu descripción)
        hist_now = df["Hist"].iloc[-1]
        hist_prev = df["Hist"].iloc[-2]
        ha_now = df["HA_Color"].iloc[-1]
        ha_prev = df["HA_Color"].iloc[-2]
        
        # Interpretación de impulso
        if hist_now > hist_prev:
            macd_momentum = "SUBE (Impulso)" if hist_now > 0 else "SUBE (Recuperando)"
        else:
            macd_momentum = "BAJA (Cediendo)" if hist_now > 0 else "BAJA (Cayendo)"
            
        ha_status = "VERDE 🟢" if ha_now == 1 else "ROJO 🔴"
        ha_trend = "CAMBIO" if ha_now != ha_prev else "Mantiene"

        return {
            "RSI_Data": rsi_signals,
            "MACD_Hist": macd_momentum,
            "HA_Color": ha_status,
            "HA_Trend": ha_trend,
            "Price": df["close"].iloc[-1]
        }
    except: return None

# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuración")
    min_volume = st.number_input("Volumen Mínimo (USDT):", value=500000)
    all_sym = get_active_pairs_by_vol(min_volume)
    
    if all_sym:
        b_size = st.selectbox("Lote:", [10, 20, 50], index=1)
        batches = [all_sym[i:i+b_size] for i in range(0, len(all_sym), b_size)]
        sel_lote = st.selectbox("Seleccionar Lote:", range(len(batches)))
        
        if st.button("🚀 ACTUALIZAR RADAR", type="primary", use_container_width=True):
            ex = get_exchange()
            results = []
            prog = st.progress(0)
            targets = batches[sel_lote]
            for idx, sym in enumerate(targets):
                prog.progress((idx+1)/len(targets), text=f"Analizando {sym}")
                analysis = analyze_ticker_rsi_logic(sym, ex)
                if analysis:
                    row = {
                        "Activo": sym.split(":")[0].replace("/USDT", ""),
                        "Precio": f"{analysis['Price']:.4f}",
                        "HA 1H": analysis["HA_Color"],
                        "HA Estado": analysis["HA_Trend"],
                        "MACD Hist": analysis["MACD_Hist"]
                    }
                    row.update(analysis["RSI_Data"])
                    results.append(row)
                time.sleep(0.05)
            st.session_state["rsi_matrix_results"] = results
            prog.empty()

    if st.button("Limpiar Memoria"):
        st.session_state["rsi_matrix_results"] = []
        st.rerun()

# ─────────────────────────────────────────────
# TABLA
# ─────────────────────────────────────────────
st.title("🎯 SNIPER MATRIX V27.1")

if st.session_state["rsi_matrix_results"]:
    df = pd.DataFrame(st.session_state["rsi_matrix_results"])
    
    def style_matrix(val):
        v = str(val).upper()
        if "SUBE" in v or "VERDE" in v: return 'background-color: #d4edda; color: #155724;'
        if "BAJA" in v or "ROJO" in v: return 'background-color: #f8d7da; color: #721c24;'
        return ''

    cols = ["Activo", "Precio", "HA 1H", "HA Estado", "MACD Hist"] + [f"RSI {p}" for p in RSI_PERIODS]
    st.dataframe(df[cols].style.applymap(style_matrix), use_container_width=True, height=800)
else:
    st.info("👈 Inicie el escaneo. La lógica ha sido ajustada para coincidir con Heikin Ashi y MACD de TradingView.")
