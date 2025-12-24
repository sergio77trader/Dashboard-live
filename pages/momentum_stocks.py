import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Scanner HA + MACD (TradingView Logic)")

# --- ESTILOS ---
st.markdown("""
<style>
    .metric-box {
        background-color: #1e1e1e;
        border: 1px solid #444;
        border-radius: 8px;
        padding: 15px;
        text-align: center;
        margin-bottom: 10px;
    }
    .signal-long { color: #00ff00; font-weight: bold; font-size: 1.5rem; }
    .signal-short { color: #ff3333; font-weight: bold; font-size: 1.5rem; }
    .price-tag { font-size: 1.1rem; color: white; margin-top: 5px; }
    .date-tag { font-size: 0.9rem; color: #888; }
</style>
""", unsafe_allow_html=True)

# --- 1. CÁLCULO DE INDICADORES (REPLICA EXACTA) ---

def calculate_indicators(df, fast=12, slow=26, sig=9):
    # --- MACD ---
    # [macdLine, signalLine, hist] = ta.macd(...)
    exp1 = df['Close'].ewm(span=fast, adjust=False).mean()
    exp2 = df['Close'].ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=sig, adjust=False).mean()
    hist = macd - signal
    
    df['Hist'] = hist
    
    # --- HEIKIN ASHI ---
    # Cálculo iterativo para coincidir con TV (haOpen depende del anterior)
    ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    ha_open = [df['Open'].iloc[0]]
    
    for i in range(1, len(df)):
        # haOpen := (haOpen[1] + haClose[1]) / 2
        prev_o = ha_open[-1]
        prev_c = ha_close.iloc[i-1]
        ha_open.append((prev_o + prev_c) / 2)
        
    df['HA_Close'] = ha_close
    df['HA_Open'] = ha_open
    
    # haColor = haClose > haOpen ? 1 : -1
    df['HA_Color'] = np.where(df['HA_Close'] > df['HA_Open'], 1, -1)
    
    return df

# --- 2. MOTOR DE ESTRATEGIA ---

def get_last_signal(ticker, interval, period):
    # Descarga
    try:
        df = yf.download(ticker, interval=interval, period=period, progress=False, auto_adjust=True)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    except: return None
    
    # Calcular
    df = calculate_indicators(df)
    
    last_signal = None
    
    # Recorremos el histórico para encontrar la última señal
    # Empezamos desde el índice 1 porque necesitamos comparar con [i-1]
    for i in range(1, len(df)):
        
        # Datos Actuales
        curr_ha = df['HA_Color'].iloc[i]
        curr_hist = df['Hist'].iloc[i]
        date = df.index[i]
        price = df['Close'].iloc[i]
        
        # Datos Anteriores
        prev_ha = df['HA_Color'].iloc[i-1]
        prev_hist = df['Hist'].iloc[i-1]
        
        # --- LÓGICA DE TU SCRIPT ---
        
        # 1. Detectar Cambio de Color HA
        # ha_cambio_verde = (haColor == 1) and (haColor[1] == -1)
        ha_cambio_verde = (curr_ha == 1) and (prev_ha == -1)
        # ha_cambio_rojo = (haColor == -1) and (haColor[1] == 1)
        ha_cambio_rojo = (curr_ha == -1) and (prev_ha == 1)
        
        # 2. Dirección del Histograma
        # hist_subiendo = hist > hist[1]
        hist_subiendo = curr_hist > prev_hist
        # hist_bajando = hist < hist[1]
        hist_bajando = curr_hist < prev_hist
        
        # --- ENTRADAS ---
        
        # LONG: Cambio Verde + Hist < 0 + Hist Subiendo
        if ha_cambio_verde and (curr_hist < 0) and hist_subiendo:
            last_signal = {"Tipo": "LONG", "Fecha": date, "Precio": price, "Color": "signal-long", "Icono": "🟢"}
            
        # SHORT: Cambio Rojo + Hist > 0 + Hist Bajando
        elif ha_cambio_rojo and (curr_hist > 0) and hist_bajando:
            last_signal = {"Tipo": "SHORT", "Fecha": date, "Precio": price, "Color": "signal-short", "Icono": "🔴"}
            
    # Obtenemos precio actual para mostrar
    curr_price = df['Close'].iloc[-1]
    
    return last_signal, curr_price

# --- 3. INTERFAZ VISUAL ---

st.title("🛡️ SystemaTrader: HA + MACD Momentum Scanner")
st.markdown("Analiza la última señal válida basada en tu estrategia de TradingView.")

col1, col2 = st.columns([1, 3])
with col1:
    ticker = st.text_input("Ticker:", value="AAPL").upper().strip()
    btn = st.button("ANALIZAR")

if btn and ticker:
    # Definimos las 3 temporalidades que pediste
    tasks = [
        ("DIARIO", "D", "1d", "5y"),
        ("SEMANAL", "S", "1wk", "10y"),
        ("MENSUAL", "M", "1mo", "max")
    ]
    
    # Contenedor de resultados
    results_cols = st.columns(3)
    
    # Variables para el encabezado
    current_price_display = 0
    
    for idx, (label, prefix, interval, period) in enumerate(tasks):
        with results_cols[idx]:
            with st.spinner(f"Analizando {label}..."):
                signal, curr_price = get_last_signal(ticker, interval, period)
                if interval == "1d": current_price_display = curr_price
                
                if signal:
                    f_date = signal['Fecha'].strftime('%d-%m-%Y')
                    st.markdown(f"""
                    <div class="metric-box">
                        <div style="color: #aaa; margin-bottom:5px;">{label} ({prefix})</div>
                        <div class="{signal['Color']}">{signal['Icono']} {signal['Tipo']}</div>
                        <div class="price-tag">${signal['Precio']:.2f}</div>
                        <div class="date-tag">📅 {f_date}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="metric-box">
                        <div style="color: #aaa;">{label}</div>
                        <h3 style="color: #666;">SIN SEÑAL</h3>
                        <div class="date-tag">No se cumplieron condiciones recientemente</div>
                    </div>
                    """, unsafe_allow_html=True)

    # Mostrar Precio Actual Grande
    if current_price_display > 0:
        st.markdown(f"<h3 style='text-align: center; margin-top: 20px;'>Precio Actual {ticker}: ${current_price_display:.2f}</h3>", unsafe_allow_html=True)
