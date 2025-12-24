import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Signal Hunter: Exact Match")

# --- ESTILOS ---
st.markdown("""
<style>
    .signal-box {
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 10px;
        font-family: sans-serif;
    }
    .long-box { background-color: #0f3d0f; border: 2px solid #00ff00; }
    .short-box { background-color: #3d0f0f; border: 2px solid #ff0000; }
    .no-signal { background-color: #1e1e1e; border: 1px solid #444; color: #888; }
    
    .sig-title { font-size: 1.5rem; font-weight: bold; margin-bottom: 5px; color: white; }
    .sig-date { font-size: 1.1rem; color: #ddd; margin-bottom: 5px; }
    .sig-price { font-size: 1.2rem; font-weight: bold; color: white; }
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
    
    # Heikin Ashi Iterativo (Para precisión máxima)
    ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    ha_open = [df['Open'].iloc[0]]
    for i in range(1, len(df)):
        ha_open.append((ha_open[-1] + ha_close.iloc[i-1]) / 2)
        
    df['HA_Close'] = ha_close
    df['HA_Open'] = ha_open
    
    # 1: Verde, -1: Rojo
    df['Color'] = np.where(df['HA_Close'] > df['HA_Open'], 1, -1)
    
    return df

# --- 2. MOTOR DE BÚSQUEDA DE SEÑAL PURA ---
def find_latest_entry(ticker, interval, period):
    try:
        # Descargamos MAX historia para que el MACD se estabilice igual que en TV
        df = yf.download(ticker, interval=interval, period=period, progress=False, auto_adjust=True)
        if df.empty: return None, 0
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        df = calculate_indicators(df)
        
        last_long = None
        last_short = None
        
        # Recorremos el DataFrame buscando la ÚLTIMA vez que se cumplió la condición
        # Iteramos desde el final hacia el principio para encontrar la más reciente rápido
        # (Aunque aquí iteramos normal para guardar la última que sobrescriba)
        
        for i in range(1, len(df)):
            date = df.index[i]
            price = df['Close'].iloc[i]
            
            # Variables
            curr_c = df['Color'].iloc[i]
            prev_c = df['Color'].iloc[i-1]
            curr_h = df['Hist'].iloc[i]
            prev_h = df['Hist'].iloc[i-1]
            
            # --- CONDICIONES EXACTAS DE PINE SCRIPT ---
            
            # LONG:
            # 1. Cambio a Verde (Ayer Rojo, Hoy Verde)
            # 2. Histograma Negativo (< 0)
            # 3. Histograma Subiendo (Hoy > Ayer)
            if (prev_c == -1 and curr_c == 1) and (curr_h < 0) and (curr_h > prev_h):
                last_long = {"Tipo": "LONG", "Fecha": date, "Precio": price}
            
            # SHORT:
            # 1. Cambio a Rojo (Ayer Verde, Hoy Rojo)
            # 2. Histograma Positivo (> 0)
            # 3. Histograma Bajando (Hoy < Ayer)
            elif (prev_c == 1 and curr_c == -1) and (curr_h > 0) and (curr_h < prev_h):
                last_short = {"Tipo": "SHORT", "Fecha": date, "Precio": price}

        # Decidir cuál mostrar: La que tenga fecha más reciente
        final_signal = None
        
        if last_long and last_short:
            if last_long['Fecha'] > last_short['Fecha']:
                final_signal = last_long
            else:
                final_signal = last_short
        elif last_long:
            final_signal = last_long
        elif last_short:
            final_signal = last_short
            
        return final_signal, df['Close'].iloc[-1]

    except Exception as e:
        return None, 0

# --- 3. INTERFAZ ---
st.title("🛡️ Signal Hunter: Exact Match")

ticker = st.text_input("Ticker:", value="AAPL").upper().strip()
btn = st.button("ANALIZAR")

if btn and ticker:
    # Configuración de Tareas
    tasks = [
        ("DIARIO", "1d", "5y"),
        ("SEMANAL", "1wk", "10y"),
        ("MENSUAL", "1mo", "max") # Max historia es CLAVE para AAPL mensual
    ]
    
    cols = st.columns(3)
    current_price = 0
    
    for i, (label, interval, period) in enumerate(tasks):
        with cols[i]:
            sig, price = find_latest_entry(ticker, interval, period)
            if interval == '1d': current_price = price
            
            if sig:
                # Formato de Fecha
                f_date = sig['Fecha'].strftime('%d/%m/%Y')
                css_class = "long-box" if sig['Tipo'] == "LONG" else "short-box"
                icon = "🟢" if sig['Tipo'] == "LONG" else "🔴"
                
                st.markdown(f"""
                <div class="signal-box {css_class}">
                    <div style="font-size:0.9rem; color:#ccc;">{label}</div>
                    <div class="sig-title">{icon} {sig['Tipo']}</div>
                    <div class="sig-price">${sig['Precio']:.2f}</div>
                    <div class="sig-date">📅 {f_date}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="signal-box no-signal">
                    <div>{label}</div>
                    <div>Sin señal reciente</div>
                </div>
                """, unsafe_allow_html=True)

    if current_price > 0:
        st.markdown(f"<h3 style='text-align: center;'>Precio Actual: ${current_price:.2f}</h3>", unsafe_allow_html=True)
