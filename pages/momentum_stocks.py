import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Scanner Exacto TV")

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

# --- 1. CÁLCULOS MATEMÁTICOS (REPLICA EXACTA) ---

def calculate_heikin_ashi(df):
    """
    Cálculo de Heikin Ashi con memoria histórica (Iterativo).
    Esto es crucial para que coincida con TradingView en tendencias largas.
    """
    df_ha = df.copy()
    
    # HA Close (Promedio simple)
    df_ha['HA_Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    
    # HA Open (Este es el que necesita memoria)
    # haOpen = (haOpen_prev + haClose_prev) / 2
    ha_open_list = [df['Open'].iloc[0]] # El primero es igual al precio real
    ha_close_list = [df_ha['HA_Close'].iloc[0]]
    
    for i in range(1, len(df)):
        # Usamos los valores calculados en el paso anterior
        prev_open = ha_open_list[-1]
        prev_close = ha_close_list[i-1] # El close ya está calculado arriba vectorizado, pero para claridad lo tomamos
        
        current_open = (prev_open + prev_close) / 2
        ha_open_list.append(current_open)
        ha_close_list.append(df_ha['HA_Close'].iloc[i]) # Solo por consistencia de lista
        
    df_ha['HA_Open'] = ha_open_list
    
    # Recalculamos High y Low HA para el gráfico
    df_ha['HA_High'] = df_ha[['High', 'HA_Open', 'HA_Close']].max(axis=1)
    df_ha['HA_Low'] = df_ha[['Low', 'HA_Open', 'HA_Close']].min(axis=1)
    
    # Color: 1 Verde, -1 Rojo
    df_ha['Color'] = np.where(df_ha['HA_Close'] > df_ha['HA_Open'], 1, -1)
    
    return df_ha

def calculate_macd(df, fast=12, slow=26, sig=9):
    # EWM con adjust=False es idéntico a la EMA de TradingView
    exp1 = df['Close'].ewm(span=fast, adjust=False).mean()
    exp2 = df['Close'].ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=sig, adjust=False).mean()
    hist = macd - signal
    df['Hist'] = hist
    return df

# --- 2. MOTOR DE ESTRATEGIA (LOGICA DE ENTRADA) ---

def find_signals(ticker, interval, period):
    try:
        # Descarga
        df = yf.download(ticker, interval=interval, period=period, progress=False, auto_adjust=True)
        if df.empty: return None, None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        # Indicadores
        df = calculate_heikin_ashi(df)
        df = calculate_macd(df)
        
        signals = []
        
        # Bucle de Señales (Empieza en 1 para comparar con i-1)
        for i in range(1, len(df)):
            date = df.index[i]
            price = df['Close'].iloc[i]
            
            # Estado Actual
            curr_c = df['Color'].iloc[i]
            curr_h = df['Hist'].iloc[i]
            
            # Estado Anterior
            prev_c = df['Color'].iloc[i-1]
            prev_h = df['Hist'].iloc[i-1]
            
            # --- LÓGICA EXACTA DE TU PINE SCRIPT ---
            
            # LONG (Entrada)
            # 1. HA Cambia de Rojo (-1) a Verde (1)
            # 2. Histograma es Negativo (< 0)
            # 3. Histograma está subiendo (Actual > Previo)
            if (prev_c == -1 and curr_c == 1) and (curr_h < 0) and (curr_h > prev_h):
                signals.append({"Tipo": "LONG", "Fecha": date, "Precio": price, "Icon": "🟢", "Color": "signal-long"})
            
            # SHORT (Entrada)
            # 1. HA Cambia de Verde (1) a Rojo (-1)
            # 2. Histograma es Positivo (> 0)
            # 3. Histograma está bajando (Actual < Previo)
            elif (prev_c == 1 and curr_c == -1) and (curr_h > 0) and (curr_h < prev_h):
                signals.append({"Tipo": "SHORT", "Fecha": date, "Precio": price, "Icon": "🔴", "Color": "signal-short"})
                
        return df, signals

    except: return None, None

# --- 3. INTERFAZ ---

st.title("🛡️ Signal Hunter: Exact Replica")

col1, col2 = st.columns([1, 3])
with col1:
    ticker = st.text_input("Ticker:", value="AAPL").upper().strip()
    btn = st.button("ANALIZAR")

if btn and ticker:
    # Usamos "max" en todos para asegurar que el cálculo HA sea perfecto desde el origen
    tasks = [
        ("DIARIO", "1d", "max"),
        ("SEMANAL", "1wk", "max"),
        ("MENSUAL", "1mo", "max") 
    ]
    
    cols = st.columns(3)
    curr_p = 0
    
    for i, (label, interval, period) in enumerate(tasks):
        with cols[i]:
            with st.spinner(f"{label}..."):
                df, signals = find_signals(ticker, interval, period)
                
                if df is not None:
                    curr_p = df['Close'].iloc[-1]
                    
                    # Buscamos la última señal de la lista
                    if signals:
                        last_sig = signals[-1]
                        f_date = last_sig['Fecha'].strftime('%d-%m-%Y')
                        
                        st.markdown(f"""
                        <div class="metric-box">
                            <div style="color: #aaa;">{label}</div>
                            <div class="{last_sig['Color']}">{last_sig['Icon']} {last_sig['Tipo']}</div>
                            <div class="price-tag">${last_sig['Precio']:.2f}</div>
                            <div class="date-tag">Fecha: <b>{f_date}</b></div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.warning("Sin señales recientes")
                    
                    # --- GRÁFICO ---
                    # Mostramos gráfico para verificar visualmente
                    # Cortamos los últimos 5 años para que se vea bien
                    chart_data = df.tail(100)
                    
                    fig = go.Figure()
                    
                    # Velas HA (Usamos las calculadas por nosotros)
                    fig.add_trace(go.Candlestick(
                        x=chart_data.index,
                        open=chart_data['HA_Open'], high=chart_data['HA_High'],
                        low=chart_data['HA_Low'], close=chart_data['HA_Close'],
                        name='Heikin Ashi'
                    ))
                    
                    # Flechas de Señal
                    if signals:
                        visible_sigs = [s for s in signals if s['Fecha'] >= chart_data.index[0]]
                        for s in visible_sigs:
                            fig.add_trace(go.Scatter(
                                x=[s['Fecha']], 
                                y=[s['Precio'] * (0.95 if s['Tipo']=="LONG" else 1.05)],
                                mode='markers',
                                marker=dict(symbol="triangle-up" if s['Tipo']=="LONG" else "triangle-down", size=15, color="blue" if s['Tipo']=="LONG" else "orange"),
                                name=s['Tipo']
                            ))

                    fig.update_layout(height=300, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False, template="plotly_dark")
                    st.plotly_chart(fig, use_container_width=True)

    if curr_p > 0:
        st.markdown(f"<h3 style='text-align: center;'>Precio Actual: ${curr_p:.2f}</h3>", unsafe_allow_html=True)
