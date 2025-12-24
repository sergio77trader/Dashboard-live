import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Scanner: TV Clone Exact")

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

# --- 1. CÁLCULOS MATEMÁTICOS DE PRECISIÓN ---

def calculate_heikin_ashi(df):
    """
    Cálculo de Heikin Ashi idéntico a TradingView.
    """
    df_ha = df.copy()
    
    # HA Close: Promedio simple
    df_ha['HA_Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    
    # HA Open: Recursivo (vital para precisión)
    ha_open_list = [df['Open'].iloc[0]]
    ha_close_list = [df_ha['HA_Close'].iloc[0]]
    
    for i in range(1, len(df)):
        # HA Open = (HA Open prev + HA Close prev) / 2
        prev_open = ha_open_list[-1]
        prev_close = ha_close_list[i-1] # Usamos el Close calculado previamente
        
        current_open = (prev_open + prev_close) / 2
        
        ha_open_list.append(current_open)
        ha_close_list.append(df_ha['HA_Close'].iloc[i])
        
    df_ha['HA_Open'] = ha_open_list
    
    # Recalcular High/Low HA (TradingView usa máximos/mínimos modificados)
    df_ha['HA_High'] = df_ha[['High', 'HA_Open', 'HA_Close']].max(axis=1)
    df_ha['HA_Low'] = df_ha[['Low', 'HA_Open', 'HA_Close']].min(axis=1)
    
    # Color (1=Verde, -1=Rojo)
    df_ha['HA_Color'] = np.where(df_ha['HA_Close'] > df_ha['HA_Open'], 1, -1)
    
    return df_ha

def calculate_macd(df, fast=12, slow=26, sig=9):
    """
    Cálculo de MACD usando EMA estándar (TradingView usa EMA, no RMA para MACD).
    """
    # EMA (Exponential Moving Average)
    exp1 = df['Close'].ewm(span=fast, adjust=False).mean()
    exp2 = df['Close'].ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=sig, adjust=False).mean()
    hist = macd - signal
    df['Hist'] = hist
    return df

# --- 2. MOTOR DE ESTRATEGIA (CON MEMORIA DE ESTADO) ---

def get_strategy_signal(ticker, interval):
    try:
        # Descargamos MAX historia para que el cálculo recursivo tenga datos desde el inicio
        df = yf.download(ticker, interval=interval, period="max", progress=False, auto_adjust=True)
        if df.empty: return None, 0
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # Calcular Indicadores
        df = calculate_heikin_ashi(df)
        df = calculate_macd(df)
        
        # --- SIMULACIÓN DE TRADING ---
        # Replicamos el comportamiento de `strategy.entry` y `strategy.close`
        
        current_position = "FLAT" # FLAT, LONG, SHORT
        last_entry_signal = None  # Guardamos la info de la última entrada realizada
        
        for i in range(1, len(df)):
            # Datos actuales
            date = df.index[i]
            price = df['Close'].iloc[i]
            
            curr_ha = df['HA_Color'].iloc[i]
            prev_ha = df['HA_Color'].iloc[i-1]
            curr_hist = df['Hist'].iloc[i]
            prev_hist = df['Hist'].iloc[i-1]
            
            # --- CONDICIONES DE ENTRADA ---
            
            # LONG ENTRY
            # 1. HA pasa de Rojo a Verde (Giro)
            # 2. Histograma es Negativo (< 0)
            # 3. Histograma está subiendo (Recuperando)
            go_long = (prev_ha == -1 and curr_ha == 1) and (curr_hist < 0) and (curr_hist > prev_hist)
            
            # SHORT ENTRY
            # 1. HA pasa de Verde a Rojo
            # 2. Histograma es Positivo (> 0)
            # 3. Histograma está bajando
            go_short = (prev_ha == 1 and curr_ha == -1) and (curr_hist > 0) and (curr_hist < prev_hist)
            
            # --- CONDICIONES DE SALIDA (STOP MACD) ---
            exit_long = (current_position == "LONG") and (curr_hist < prev_hist) # Histograma baja
            exit_short = (current_position == "SHORT") and (curr_hist > prev_hist) # Histograma sube
            
            # --- EJECUCIÓN DE ÓRDENES ---
            
            # 1. Revisar Salidas PRIMERO (TradingView cierra antes de abrir si pasa en la misma vela)
            if exit_long:
                current_position = "FLAT"
            if exit_short:
                current_position = "FLAT"
                
            # 2. Revisar Entradas (Solo si estamos FLAT)
            if current_position == "FLAT":
                if go_long:
                    current_position = "LONG"
                    last_entry_signal = {"Tipo": "LONG", "Fecha": date, "Precio": price, "Icono": "🟢", "Color": "signal-long"}
                elif go_short:
                    current_position = "SHORT"
                    last_entry_signal = {"Tipo": "SHORT", "Fecha": date, "Precio": price, "Icono": "🔴", "Color": "signal-short"}
        
        # --- RESULTADO AL DÍA DE HOY ---
        
        # Si la posición sigue abierta, mostramos la señal activa
        if current_position != "FLAT" and last_entry_signal:
            return last_entry_signal, df['Close'].iloc[-1], df
            
        # Si la posición está cerrada (FLAT), mostramos la última señal pero grisada
        elif last_entry_signal:
            # Marcamos como cerrada
            last_entry_signal['Tipo'] += " (CERRADA)"
            last_entry_signal['Color'] = "signal-closed"
            last_entry_signal['Icono'] = "⚪"
            return last_entry_signal, df['Close'].iloc[-1], df
            
        return None, df['Close'].iloc[-1], df

    except: return None, 0, None

# --- 3. INTERFAZ ---
st.title("🛡️ Scanner Exacto TV (Clone)")

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
    df_chart = None
    
    for idx, (label, prefix, interval) in enumerate(tasks):
        with cols[idx]:
            with st.spinner(f"{label}..."):
                signal, price, df_res = get_strategy_signal(ticker, interval)
                if interval == "1mo": df_chart = df_res # Guardamos mensual para graficar
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
        
    # GRÁFICO DE VERIFICACIÓN (Solo Mensual para ver la discrepancia)
    if df_chart is not None:
        st.subheader("Gráfico Mensual (Verificación Visual)")
        
        # Filtramos últimos años
        chart_data = df_chart.tail(100)
        
        fig = go.Figure()
        
        # Velas HA
        fig.add_trace(go.Candlestick(
            x=chart_data.index,
            open=chart_data['HA_Open'], high=chart_data['HA_High'],
            low=chart_data['HA_Low'], close=chart_data['HA_Close'],
            name='Heikin Ashi'
        ))
        
        # Histograma MACD
        colors = np.where(chart_data['Hist'] < 0, 'red', 'green')
        fig.add_trace(go.Bar(
            x=chart_data.index, y=chart_data['Hist'],
            marker_color=colors, name='MACD Hist'
        ))

        fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
