import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Scanner Exacto TV (Trend Logic)")

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
    .signal-closed { color: #888; font-weight: bold; font-size: 1.2rem; }
    .price-tag { font-size: 1.1rem; color: white; margin-top: 5px; }
    .date-tag { font-size: 0.9rem; color: #888; }
</style>
""", unsafe_allow_html=True)

# --- 1. CÁLCULOS MATEMÁTICOS ---
def calculate_indicators(df, fast=12, slow=26, sig=9):
    # MACD
    exp1 = df['Close'].ewm(span=fast, adjust=False).mean()
    exp2 = df['Close'].ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=sig, adjust=False).mean()
    hist = macd - signal
    df['Hist'] = hist
    
    # Heikin Ashi Iterativo
    ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    ha_open = [df['Open'].iloc[0]]
    for i in range(1, len(df)):
        prev_o = ha_open[-1]
        prev_c = ha_close.iloc[i-1]
        ha_open.append((prev_o + prev_c) / 2)
        
    df['HA_Close'] = ha_close
    df['HA_Open'] = ha_open
    df['HA_Color'] = np.where(df['HA_Close'] > df['HA_Open'], 1, -1) # 1 Verde, -1 Rojo
    
    return df

# --- 2. MOTOR DE ESTRATEGIA (LÓGICA AJUSTADA) ---
def get_strategy_signal(ticker, interval):
    try:
        # Descarga máxima historia
        df = yf.download(ticker, interval=interval, period="max", progress=False, auto_adjust=True)
        if df.empty: return None, 0
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        df = calculate_indicators(df)
        
        # ESTADO DEL ROBOT
        current_state = "NEUTRO" 
        last_entry = None 
        
        # Recorrido Histórico
        for i in range(1, len(df)):
            date = df.index[i]
            price = df['Close'].iloc[i]
            
            # Variables Actuales
            curr_ha = df['HA_Color'].iloc[i]
            curr_hist = df['Hist'].iloc[i]
            
            # Variables Previas
            prev_ha = df['HA_Color'].iloc[i-1]
            prev_hist = df['Hist'].iloc[i-1]
            
            # --- LÓGICA DE SALIDA (STOP) ---
            # CORRECCIÓN: Para gráfico MENSUAL, ser más tolerante.
            # Solo salimos si la vela cambia de color O si el histograma cruza 0 en contra.
            # NO salimos solo porque el histograma baje un poquito (eso es ruido en mensual).
            
            if current_state == "LONG":
                # Salida Long: Solo si HA se pone Rojo (Cambio de tendencia real)
                # O si el MACD cruza a negativo (Confirmación bajista)
                if curr_ha == -1: 
                    current_state = "NEUTRO"
            
            elif current_state == "SHORT":
                # Salida Short: Solo si HA se pone Verde
                if curr_ha == 1:
                    current_state = "NEUTRO"

            # --- LÓGICA DE ENTRADA (RE-ENTRY) ---
            if current_state == "NEUTRO":
                
                # CONDICIÓN LONG:
                # 1. HA cambia a Verde (Giro)
                # 2. Histograma es Negativo (< 0) pero subiendo
                
                ha_flip_green = (prev_ha == -1 and curr_ha == 1)
                hist_ok_long = (curr_hist < 0) and (curr_hist > prev_hist)
                
                if ha_flip_green and hist_ok_long:
                    current_state = "LONG"
                    last_entry = {"Tipo": "LONG", "Fecha": date, "Precio": price, "Color": "signal-long", "Icono": "🟢"}

                # CONDICIÓN SHORT:
                ha_flip_red = (prev_ha == 1 and curr_ha == -1)
                hist_ok_short = (curr_hist > 0) and (curr_hist < prev_hist)
                
                if ha_flip_red and hist_ok_short:
                    current_state = "SHORT"
                    last_entry = {"Tipo": "SHORT", "Fecha": date, "Precio": price, "Color": "signal-short", "Icono": "🔴"}

        # --- RESULTADO FINAL ---
        
        # Si terminamos "LONG", significa que la compra de 2021/2022 nunca se cerró
        if current_state == "LONG":
            return last_entry, df['Close'].iloc[-1]
            
        if current_state == "SHORT":
            return last_entry, df['Close'].iloc[-1]
            
        # Si terminó Neutro
        elif last_entry:
             last_entry['Tipo'] += " (CERRADA)"
             last_entry['Color'] = "signal-closed"
             last_entry['Icono'] = "⚪"
             return last_entry, df['Close'].iloc[-1]

        return None, df['Close'].iloc[-1]

    except: return None, 0

# --- 3. INTERFAZ ---
st.title("🛡️ Scanner Exacto TV (Trend Fix)")

col1, col2 = st.columns([1, 3])
with col1:
    ticker = st.text_input("Ticker:", value="AAPL").upper().strip()
    btn = st.button("ANALIZAR")

if btn and ticker:
    tasks = [
        ("DIARIO", "D", "1d"),
        ("SEMANAL", "S", "1wk"),
        ("MENSUAL", "M", "1mo")
    ]
    
    cols = st.columns(3)
    curr_p = 0
    
    for idx, (label, prefix, interval) in enumerate(tasks):
        with cols[idx]:
            with st.spinner(f"{label}..."):
                signal, price = get_strategy_signal(ticker, interval)
                if interval == "1d": curr_p = price
                
                if signal:
                    f_date = signal['Fecha'].strftime('%d-%m-%Y')
                    st.markdown(f"""
                    <div class="metric-box">
                        <div style="color: #aaa;">{label} ({prefix})</div>
                        <div class="{signal['Color']}">{signal['Icono']} {signal['Tipo']}</div>
                        <div class="price-tag">${signal['Precio']:.2f}</div>
                        <div class="date-tag">📅 {f_date}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.warning("Sin señales")

    if curr_p > 0:
        st.markdown(f"<h3 style='text-align: center;'>Precio Actual: ${curr_p:.2f}</h3>", unsafe_allow_html=True)
