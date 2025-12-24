import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Scanner HA + MACD (Logic Fix)")

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

# --- 1. INDICADORES ---
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

# --- 2. MOTOR DE ESTRATEGIA (STATEFUL) ---
def get_strategy_state(ticker, interval, period):
    try:
        df = yf.download(ticker, interval=interval, period=period, progress=False, auto_adjust=True)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        df = calculate_indicators(df)
        
        # VARIABLES DE ESTADO (MEMORIA DEL ROBOT)
        current_state = "NEUTRO" # LONG, SHORT, NEUTRO
        entry_date = None
        entry_price = 0.0
        
        # Simulación Vela por Vela (Backtest Rápido)
        for i in range(1, len(df)):
            # Datos actuales
            date = df.index[i]
            price = df['Close'].iloc[i]
            
            # HA y MACD
            curr_ha = df['HA_Color'].iloc[i]
            prev_ha = df['HA_Color'].iloc[i-1]
            
            curr_hist = df['Hist'].iloc[i]
            prev_hist = df['Hist'].iloc[i-1]
            
            # --- LÓGICA DE ENTRADA ---
            
            # LONG: HA cambia a Verde + Hist < 0 + Hist Subiendo
            ha_green_flip = (prev_ha == -1) and (curr_ha == 1)
            hist_up = (curr_hist > prev_hist)
            
            if ha_green_flip and (curr_hist < 0) and hist_up:
                current_state = "LONG"
                entry_date = date
                entry_price = price
                
            # SHORT: HA cambia a Rojo + Hist > 0 + Hist Bajando
            ha_red_flip = (prev_ha == 1) and (curr_ha == -1)
            hist_down = (curr_hist < prev_hist)
            
            if ha_red_flip and (curr_hist > 0) and hist_down:
                current_state = "SHORT"
                entry_date = date
                entry_price = price
                
            # --- LÓGICA DE SALIDA (STOP MACD) ---
            # Si estamos en Long y el Histograma baja -> Salimos
            if current_state == "LONG" and hist_down:
                current_state = "NEUTRO" # Salimos del mercado
                
            # Si estamos en Short y el Histograma sube -> Salimos
            if current_state == "SHORT" and hist_up:
                current_state = "NEUTRO"
        
        # --- RESULTADO FINAL ---
        # Si terminamos "NEUTRO", buscamos la última señal válida para mostrar "Última conocida"
        # O mostramos "SIN POSICIÓN ACTIVA".
        # Para coincidir con tu gráfico que MANTIENE la flecha, vamos a mostrar la última ENTRADA que hubo,
        # aunque el MACD la haya sacado después (para que veas cuándo fue el gatillo).
        
        # Sin embargo, tu gráfico de TV parece NO tener "Stop MACD" activado visualmente en las flechas,
        # sino que las flechas son SOLO entradas.
        
        # Vamos a devolver la ÚLTIMA ENTRADA que ocurrió, ignorando las salidas intermedias,
        # para ver si coincide con la flecha azul.
        
        if current_state == "NEUTRO" and entry_date is not None:
             # Si salió, mostramos la última entrada pero avisamos que salió
             return {
                 "Tipo": "CERRADA (" + ("LONG" if df['Hist'].iloc[-1] > 0 else "SHORT") + ")", 
                 "Fecha": entry_date, 
                 "Precio": entry_price, 
                 "Color": "signal-none", 
                 "Icono": "⚪"
             }, df['Close'].iloc[-1]
             
        # Si sigue abierta
        if current_state == "LONG":
            return {"Tipo": "LONG", "Fecha": entry_date, "Precio": entry_price, "Color": "signal-long", "Icono": "🟢"}, df['Close'].iloc[-1]
            
        if current_state == "SHORT":
            return {"Tipo": "SHORT", "Fecha": entry_date, "Precio": entry_price, "Color": "signal-short", "Icono": "🔴"}, df['Close'].iloc[-1]
            
        return None, df['Close'].iloc[-1]

    except: return None, 0

# --- 3. INTERFAZ ---
st.title("🛡️ Scanner HA + MACD (Estado Real)")

col1, col2 = st.columns([1, 3])
with col1:
    ticker = st.text_input("Ticker:", value="AAPL").upper().strip()
    btn = st.button("ANALIZAR")

if btn and ticker:
    tasks = [
        ("DIARIO", "D", "1d", "5y"),
        ("SEMANAL", "S", "1wk", "10y"),
        ("MENSUAL", "M", "1mo", "max")
    ]
    
    results_cols = st.columns(3)
    curr_p = 0
    
    for idx, (label, prefix, interval, period) in enumerate(tasks):
        with results_cols[idx]:
            with st.spinner(f"{label}..."):
                signal, price = get_strategy_state(ticker, interval, period)
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
                    st.error("Sin datos")

    if curr_p > 0:
        st.markdown(f"<h3 style='text-align: center;'>Precio Actual: ${curr_p:.2f}</h3>", unsafe_allow_html=True)
