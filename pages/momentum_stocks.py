import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import time

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SystemaTrader: Modo Rápido")

# --- BASE DE DATOS ---
CEDEAR_DATABASE = sorted([
    'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'TSLA', 'META', 'AMD', 'NFLX', 
    'GGAL', 'YPF', 'BMA', 'PAMP', 'TGS', 'CEPU', 'EDN', 'BFR', 'SUPV', 'MELI',
    'KO', 'PEP', 'MCD', 'SBUX', 'DIS', 'XOM', 'CVX', 'JPM', 'BAC', 'C', 'WFC',
    'SPY', 'QQQ', 'IWM', 'EEM', 'XLE', 'XLF', 'GLD', 'SLV', 'ARKK'
])

# --- FUNCIONES TÉCNICAS (Optimizadas) ---
def calculate_rsi(series, period=14):
    if len(series) < period: return 50
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs)).iloc[-1]

def analyze_ticker_fast(ticker):
    try:
        # Descarga rápida solo de precio (sin fundamentales pesados)
        df = yf.download(ticker, period="1y", interval="1d", progress=False, auto_adjust=True)
        
        if df.empty: return None
        
        # Limpieza MultiIndex
        if isinstance(df.columns, pd.MultiIndex): 
            df.columns = df.columns.get_level_values(0)
            
        price = df['Close'].iloc[-1]
        rsi = calculate_rsi(df['Close'])
        
        # Heikin Ashi Simple
        ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
        ha_open = (df['Open'].shift(1) + df['Close'].shift(1)) / 2
        color = "Verde" if ha_close.iloc[-1] > ha_open.iloc[-1] else "Rojo"
        
        # Estrategia Simple
        signal = "NEUTRO"
        if rsi < 30 and color == "Verde": signal = "🟢 COMPRA"
        elif rsi > 70 and color == "Rojo": signal = "🔴 VENTA"
        elif rsi > 70: signal = "⚠️ SOBRECOMPRA"
        
        return {
            "Ticker": ticker,
            "Precio": price,
            "RSI": rsi,
            "Vela": color,
            "Señal": signal
        }
    except: return None

# --- INTERFAZ ---
st.title("⚡ SystemaTrader: Escáner Rápido (Diagnóstico)")
st.caption("Si este script funciona, el anterior fallaba por bloqueo de Yahoo Finance.")

if "fast_results" not in st.session_state:
    st.session_state["fast_results"] = []

with st.sidebar:
    st.header("Control")
    # Lotes pequeños para probar
    batch_size = 5 
    batches = [CEDEAR_DATABASE[i:i + batch_size] for i in range(0, len(CEDEAR_DATABASE), batch_size)]
    batch_labels = [f"Lote {i+1}: {b[0]} - {b[-1]}" for i, b in enumerate(batches)]
    
    sel_batch = st.selectbox("Elige Lote:", range(len(batches)), format_func=lambda x: batch_labels[x])
    
    if st.button("▶️ ESCANEAR LOTE"):
        targets = batches[sel_batch]
        placeholder = st.empty()
        
        for t in targets:
            placeholder.info(f"⏳ Analizando {t}...")
            res = analyze_ticker_fast(t)
            if res:
                st.session_state["fast_results"].append(res)
            time.sleep(0.5) # Pausa para evitar bloqueo
            
        placeholder.success("✅ ¡Escaneo terminado!")

    if st.button("🗑️ Limpiar"):
        st.session_state["fast_results"] = []
        st.rerun()

# --- TABLA ---
if st.session_state["fast_results"]:
    df = pd.DataFrame(st.session_state["fast_results"])
    
    # Colores
    def color_rsi(val):
        if val > 70: return 'color: red; font-weight: bold'
        if val < 30: return 'color: green; font-weight: bold'
        return ''
        
    st.dataframe(
        df.style.map(color_rsi, subset=['RSI']),
        use_container_width=True,
        column_config={
            "Precio": st.column_config.NumberColumn(format="$%.2f"),
            "RSI": st.column_config.NumberColumn(format="%.1f")
        }
    )
else:
    st.info("Selecciona un lote y pulsa Escanear. Deberías ver resultados en segundos.")
