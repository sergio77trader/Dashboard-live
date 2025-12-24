import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="TV Strategy Clone: Strict Mode")

# --- ESTILOS VISUALES ---
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
    .signal-long { color: #00ff00; font-weight: bold; font-size: 1.4rem; }
    .signal-short { color: #ff3333; font-weight: bold; font-size: 1.4rem; }
    .signal-flat { color: #888; font-weight: bold; font-size: 1.2rem; }
    .price-tag { font-size: 1.1rem; color: white; margin-top: 5px; }
    .date-tag { font-size: 0.9rem; color: #ccc; }
    .profit-tag { font-size: 0.9rem; font-weight: bold; margin-top: 5px; }
    .p-green { color: #00ff00; }
    .p-red { color: #ff0000; }
</style>
""", unsafe_allow_html=True)

# --- 1. MATEMÁTICA EXACTA ---

def calculate_indicators(df, fast=12, slow=26, sig=9):
    # MACD (EMA Standard igual que TV)
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
    
    # Color: 1=Verde, -1=Rojo
    df['HA_Color'] = np.where(df['HA_Close'] > df['HA_Open'], 1, -1)
    
    return df

# --- 2. MOTOR DE SIMULACIÓN DE ESTRATEGIA (EL CEREBRO) ---
def run_simulation(ticker, interval, period):
    try:
        # Descargamos MAX historia (Fundamental para Mensual)
        df = yf.download(ticker, interval=interval, period="max", progress=False, auto_adjust=True)
        if df.empty: return None, 0, []
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        df = calculate_indicators(df)
        
        # Variables de Simulación
        position = "FLAT" # FLAT, LONG, SHORT
        entry_price = 0.0
        entry_date = None
        trades = [] # Historial de trades para depurar
        
        # Bucle Vela por Vela (Simulando el mercado real)
        for i in range(1, len(df)):
            date = df.index[i]
            price = df['Close'].iloc[i]
            
            # Variables actuales
            c_ha = df['HA_Color'].iloc[i]
            c_hist = df['Hist'].iloc[i]
            
            # Variables previas
            p_ha = df['HA_Color'].iloc[i-1]
            p_hist = df['Hist'].iloc[i-1]
            
            # --- LÓGICA DE SALIDAS (STOP MOMENTUM) ---
            # En tu script: exit_long_condition = hist_bajando (c_hist < p_hist)
            
            if position == "LONG":
                # Si el histograma baja, SALIMOS
                if c_hist < p_hist:
                    position = "FLAT"
                    # Registrar Trade Cerrado
                    pnl = ((price - entry_price)/entry_price)*100
                    trades.append({"Tipo": "CIERRE LONG", "Fecha": date, "Precio": price, "PnL": pnl})
            
            elif position == "SHORT":
                # Si el histograma sube, SALIMOS
                if c_hist > p_hist:
                    position = "FLAT"
                    pnl = ((entry_price - price)/entry_price)*100
                    trades.append({"Tipo": "CIERRE SHORT", "Fecha": date, "Precio": price, "PnL": pnl})

            # --- LÓGICA DE ENTRADAS (GATILLOS) ---
            # Solo entramos si estamos FLAT (TradingView por defecto no piramida)
            
            if position == "FLAT":
                
                # LONG: HA cambia a Verde + Hist Negativo + Hist Subiendo
                ha_flip_green = (p_ha == -1 and c_ha == 1)
                hist_setup_long = (c_hist < 0) and (c_hist > p_hist)
                
                if ha_flip_green and hist_setup_long:
                    position = "LONG"
                    entry_date = date
                    entry_price = price
                    trades.append({"Tipo": "ENTRADA LONG", "Fecha": date, "Precio": price, "PnL": 0})
                    
                # SHORT: HA cambia a Rojo + Hist Positivo + Hist Bajando
                ha_flip_red = (p_ha == 1 and c_ha == -1)
                hist_setup_short = (c_hist > 0) and (c_hist < p_hist)
                
                if ha_flip_red and hist_setup_short:
                    position = "SHORT"
                    entry_date = date
                    entry_price = price
                    trades.append({"Tipo": "ENTRADA SHORT", "Fecha": date, "Precio": price, "PnL": 0})
        
        # --- ESTADO FINAL ---
        last_status = {
            "Estado": position,
            "Fecha": entry_date,
            "PrecioEntrada": entry_price
        }
        
        return last_status, df['Close'].iloc[-1], trades

    except Exception as e:
        return None, 0, []

# --- 3. INTERFAZ ---
st.title("🛡️ TV Strategy Clone: Strict Momentum")
st.markdown("Replica la estrategia con **Salidas por Pérdida de Momentum** (Histograma).")

col_in, col_btn = st.columns([3, 1])
with col_in:
    ticker = st.text_input("Ticker:", value="AAPL").upper().strip()
with col_btn:
    st.write("") # Espacio
    st.write("")
    btn = st.button("ANALIZAR", type="primary")

if btn and ticker:
    
    tabs = st.tabs(["DIARIO (1D)", "SEMANAL (1W)", "MENSUAL (1M)"])
    configs = [("1d", "5y", 0), ("1wk", "10y", 1), ("1mo", "max", 2)]
    
    for interval, period, tab_idx in configs:
        with tabs[tab_idx]:
            with st.spinner(f"Simulando estrategia en {interval}..."):
                status, curr_price, history = run_simulation(ticker, interval, period)
                
                if status:
                    # RENDERIZAR TARJETA
                    pos = status['Estado']
                    f_date = status['Fecha'].strftime('%d-%m-%Y') if status['Fecha'] else "-"
                    
                    if pos == "LONG":
                        color_cls = "signal-long"
                        icon = "🟢"
                        pnl = ((curr_price - status['PrecioEntrada']) / status['PrecioEntrada']) * 100
                        pnl_html = f"<div class='profit-tag p-green'>Ganancia: +{pnl:.2f}%</div>"
                    elif pos == "SHORT":
                        color_cls = "signal-short"
                        icon = "🔴"
                        pnl = ((status['PrecioEntrada'] - curr_price) / status['PrecioEntrada']) * 100
                        pnl_html = f"<div class='profit-tag p-green'>Ganancia: +{pnl:.2f}%</div>"
                    else:
                        color_cls = "signal-flat"
                        icon = "⚪"
                        pnl_html = "<div class='profit-tag'>Esperando nueva señal...</div>"
                        f_date = "Sin posición activa"

                    st.markdown(f"""
                    <div class="metric-box">
                        <div style="color:#888;">ESTADO ACTUAL ({interval})</div>
                        <div class="{color_cls}">{icon} {pos}</div>
                        <div class="price-tag">Precio Actual: ${curr_price:.2f}</div>
                        <div class="date-tag">Desde: {f_date}</div>
                        {pnl_html}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # MOSTRAR HISTORIAL DE TRADES (Para verificar tu fecha)
                    st.write("📜 **Últimos 5 movimientos de la estrategia:**")
                    if history:
                        df_hist = pd.DataFrame(history)
                        df_hist['Fecha'] = df_hist['Fecha'].dt.strftime('%Y-%m-%d')
                        st.table(df_hist.tail(5).sort_index(ascending=False))
                    else:
                        st.info("No hubo operaciones en este periodo.")
                        
                else:
                    st.error("Error al obtener datos.")
