import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Auditoría SystemaTrader: HA + MACD")

# --- ESTILOS CSS ---
st.markdown("""
<style>
    .metric-container {
        background-color: #1e1e1e;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #444;
        text-align: center;
    }
    .bull { color: #00ff00; font-weight: bold; font-size: 1.5rem; }
    .bear { color: #ff0000; font-weight: bold; font-size: 1.5rem; }
    .info-text { font-size: 0.9rem; color: #ccc; margin-top: 5px; }
</style>
""", unsafe_allow_html=True)

# --- BASE DE DATOS ---
TICKERS = sorted([
    'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NFLX',
    'GGAL', 'YPF', 'BMA', 'PAMP', 'SPY', 'QQQ', 'IWM', 'GLD', 'SLV',
    'AMD', 'INTC', 'QCOM', 'KO', 'PEP', 'MCD', 'XOM', 'CVX', 'BABA', 'JD'
])

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
    # Calculamos High y Low de HA para el gráfico
    df['HA_High'] = df[['High', 'HA_Open', 'HA_Close']].max(axis=1)
    df['HA_Low'] = df[['Low', 'HA_Open', 'HA_Close']].min(axis=1)
    
    df['HA_Color'] = np.where(df['HA_Close'] > df['HA_Open'], 1, -1) # 1 Verde, -1 Rojo
    
    return df

# --- 2. BUSCADOR DE SEÑALES ---

def find_signals(ticker, interval, period):
    try:
        df = yf.download(ticker, interval=interval, period=period, progress=False, auto_adjust=True)
        if df.empty: return None, None
        
        # Limpieza MultiIndex
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Asegurar que el índice es Datetime y quitar timezone para evitar líos
        df.index = pd.to_datetime(df.index).tz_localize(None)

        df = calculate_indicators(df)
        
        signals = []
        
        for i in range(1, len(df)):
            date = df.index[i]
            price = df['Close'].iloc[i]
            
            curr_c = df['HA_Color'].iloc[i]
            prev_c = df['HA_Color'].iloc[i-1]
            curr_h = df['Hist'].iloc[i]
            prev_h = df['Hist'].iloc[i-1]
            
            # LONG
            if (prev_c == -1 and curr_c == 1) and (curr_h < 0) and (curr_h > prev_h):
                signals.append({"Tipo": "LONG", "Fecha": date, "Precio": price, "Icon": "🟢", "Color": "blue"})
            
            # SHORT
            elif (prev_c == 1 and curr_c == -1) and (curr_h > 0) and (curr_h < prev_h):
                signals.append({"Tipo": "SHORT", "Fecha": date, "Precio": price, "Icon": "🔴", "Color": "orange"})
                
        return df, signals

    except Exception as e:
        return None, None

# --- 3. INTERFAZ ---

st.title("🛡️ Auditoría de Estrategia: HA + MACD")

# Sidebar
with st.sidebar:
    st.header("Parámetros")
    selected_ticker = st.selectbox("Selecciona Activo:", TICKERS)
    
    interval_map = {
        "Mensual (1 Mes)": "1mo",
        "Semanal (1 Sem)": "1wk",
        "Diario (1 Día)": "1d"
    }
    
    selected_tf_label = st.selectbox("Temporalidad:", list(interval_map.keys()))
    selected_tf_code = interval_map[selected_tf_label]
    
    btn = st.button("ANALIZAR", type="primary")

# Main
if btn:
    with st.spinner(f"Analizando {selected_ticker}..."):
        # Siempre pedimos 'max' para tener la historia completa del MACD
        df, signal_list = find_signals(selected_ticker, selected_tf_code, "max")
        
        if df is not None and signal_list:
            last_signal = signal_list[-1]
            f_date = last_signal['Fecha'].strftime('%d-%m-%Y')
            
            # --- TARJETA ---
            css_class = "bull" if last_signal['Tipo'] == "LONG" else "bear"
            
            st.markdown(f"""
            <div class="metric-container">
                <h3 style="margin:0;">ÚLTIMA SEÑAL DETECTADA</h3>
                <div class="{css_class}">{last_signal['Icon']} {last_signal['Tipo']}</div>
                <div class="info-text">Fecha: <b>{f_date}</b></div>
                <div class="info-text">Precio Señal: <b>${last_signal['Precio']:.2f}</b></div>
                <div class="info-text">Precio Actual: <b>${df['Close'].iloc[-1]:.2f}</b></div>
            </div>
            """, unsafe_allow_html=True)
            
            st.divider()
            
            # --- GRÁFICO ---
            st.subheader(f"Gráfico: {selected_ticker} ({selected_tf_label})")
            
            # Recortar datos para el gráfico (últimos 500 periodos o desde la señal - 50 periodos)
            # Esto evita errores si la señal es muy vieja
            idx_signal = df.index.get_loc(last_signal['Fecha'])
            start_idx = max(0, idx_signal - 50)
            chart_data = df.iloc[start_idx:]
            
            fig = go.Figure()

            # Velas Heikin Ashi (Usamos las columnas que calculamos explícitamente)
            fig.add_trace(go.Candlestick(
                x=chart_data.index,
                open=chart_data['HA_Open'], 
                high=chart_data['HA_High'],
                low=chart_data['HA_Low'], 
                close=chart_data['HA_Close'],
                name='Heikin Ashi'
            ))
            
            # Señales visibles
            visible_signals = [s for s in signal_list if s['Fecha'] >= chart_data.index[0]]
            
            for s in visible_signals:
                fig.add_trace(go.Scatter(
                    x=[s['Fecha']], 
                    y=[s['Precio'] * (0.95 if s['Tipo']=="LONG" else 1.05)],
                    mode='markers+text',
                    marker=dict(symbol="triangle-up" if s['Tipo']=="LONG" else "triangle-down", size=15, color=s['Color']),
                    text=[s['Tipo']],
                    textposition="bottom center" if s['Tipo']=="LONG" else "top center",
                    name=s['Tipo']
                ))

            fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
            
        else:
            st.warning("No se encontraron señales con esta estrategia.")

else:
    st.info("Selecciona un activo y temporalidad para auditar.")
