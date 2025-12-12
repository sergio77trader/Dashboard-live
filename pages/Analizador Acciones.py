import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
import numpy as np
import time

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Escáner Masivo: HA + ADX", layout="wide")

# --- ESTILOS VISUALES ---
st.markdown("""
<style>
    .stDataFrame { font-size: 0.9rem; }
    div[data-testid="stMetric"], .metric-card {
        background-color: #0e1117; border: 1px solid #303030;
        padding: 10px; border-radius: 8px; text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# --- BASE DE DATOS DE ACTIVOS ---
TICKERS_DB = sorted([
    'GGAL', 'YPF', 'BMA', 'PAMP', 'TGS', 'CEPU', 'EDN', 'BFR', 'SUPV', 'CRESY', 'IRS', 'TEO', 'LOMA', 'DESP', 'VIST', 'GLOB', 'MELI',
    'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NFLX', 'CRM', 'ORCL', 'ADBE', 'IBM', 'CSCO',
    'AMD', 'INTC', 'QCOM', 'AVGO', 'TXN', 'MU',
    'JPM', 'BAC', 'C', 'WFC', 'GS', 'MS', 'V', 'MA',
    'KO', 'PEP', 'MCD', 'SBUX', 'DIS', 'NKE', 'WMT',
    'XOM', 'CVX', 'SLB', 'BA', 'CAT', 'GE',
    'BABA', 'JD', 'BIDU', 'NIO', 'PDD',
    'PBR', 'VALE', 'ITUB', 'BBD', 'ERJ',
    'SPY', 'QQQ', 'IWM', 'DIA', 'EEM', 'EWZ', 'XLE', 'XLF', 'ARKK', 'GLD', 'SLV'
])

# --- FUNCIONES DE CÁLCULO ---

def calculate_heikin_ashi(df):
    """Calcula Heikin Ashi iterativo"""
    df_ha = df.copy()
    df_ha['HA_Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    
    ha_open = [df['Open'].iloc[0]]
    for i in range(1, len(df)):
        prev_open = ha_open[-1]
        prev_close = df_ha['HA_Close'].iloc[i-1]
        ha_open.append((prev_open + prev_close) / 2)
        
    df_ha['HA_Open'] = ha_open
    df_ha['HA_High'] = df_ha[['High', 'HA_Open', 'HA_Close']].max(axis=1)
    df_ha['HA_Low'] = df_ha[['Low', 'HA_Open', 'HA_Close']].min(axis=1)
    
    # 1 Verde, -1 Rojo
    df_ha['Color'] = np.where(df_ha['HA_Close'] > df_ha['HA_Open'], 1, -1)
    return df_ha

@st.cache_data(ttl=3600)
def get_data(ticker, interval, period):
    try:
        df = yf.download(ticker, interval=interval, period=period, progress=False, auto_adjust=True)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except: return None

def analyze_ticker(ticker, interval, period, adx_len, adx_th):
    """
    Analiza un ticker y devuelve:
    1. La ÚLTIMA señal (para la tabla).
    2. El DF completo (para el gráfico).
    3. TODAS las señales históricas (para pintar en el gráfico).
    """
    df = get_data(ticker, interval, period)
    if df is None: return None, None, []

    # 1. Calcular ADX
    df.ta.adx(length=adx_len, append=True)
    adx_col = f"ADX_{adx_len}"
    
    # 2. Calcular HA
    df_ha = calculate_heikin_ashi(df)
    
    # 3. Lógica de Señal
    signals = []
    in_position = False
    
    for i in range(1, len(df_ha)):
        date = df_ha.index[i]
        ha_color = df_ha['Color'].iloc[i]
        adx_val = df_ha[adx_col].iloc[i]
        price = df_ha['Close'].iloc[i]
        
        # Compra
        if not in_position and ha_color == 1 and adx_val > adx_th:
            in_position = True
            signals.append({'Fecha': date, 'Tipo': '🟢 COMPRA', 'Precio': price, 'ADX': adx_val})
            
        # Venta
        elif in_position and ha_color == -1:
            in_position = False
            signals.append({'Fecha': date, 'Tipo': '🔴 VENTA', 'Precio': price, 'ADX': adx_val})
    
    last_signal = signals[-1] if signals else None
    
    return last_signal, df_ha, signals

# --- UI LATERAL ---
with st.sidebar:
    st.header("⚙️ Configuración del Escáner")
    st.info(f"Base de Datos: {len(TICKERS_DB)} Activos")
    
    interval = st.selectbox("Temporalidad", ["1mo", "1wk", "1d", "1h"], index=0)
    period_map = {"1mo": "max", "1wk": "10y", "1d": "5y", "1h": "730d"}
    
    st.divider()
    st.subheader("Estrategia")
    adx_len = st.number_input("Longitud ADX", value=14)
    adx_th = st.number_input("Umbral ADX", value=20)
    
    st.divider()
    
    batch_size = st.slider("Tamaño del Lote", 5, 50, 10)
    batches = [TICKERS_DB[i:i + batch_size] for i in range(0, len(TICKERS_DB), batch_size)]
    batch_labels = [f"Lote {i+1}: {b[0]} ... {b[-1]}" for i, b in enumerate(batches)]
    sel_batch_idx = st.selectbox("Seleccionar Lote:", range(len(batches)), format_func=lambda x: batch_labels[x])
    
    scan_btn = st.button("🚀 ESCANEAR LOTE", type="primary")

# --- APP PRINCIPAL ---
st.title("🛰️ Escáner de Señales: Heikin Ashi + ADX")

if 'scan_results' not in st.session_state:
    st.session_state['scan_results'] = []

if scan_btn:
    targets = batches[sel_batch_idx]
    prog_bar = st.progress(0)
    status_text = st.empty()
    current_results = []
    
    for i, t in enumerate(targets):
        status_text.text(f"Analizando {t}...")
        # Desempaquetamos 3 valores, pero solo usamos el primero para la tabla
        last_sig, _, _ = analyze_ticker(t, interval, period_map[interval], adx_len, adx_th)
        
        if last_sig:
            last_sig['Ticker'] = t
            current_results.append(last_sig)
            
        prog_bar.progress((i + 1) / len(targets))
    
    old_data = st.session_state['scan_results']
    old_data = [x for x in old_data if x['Ticker'] not in targets]
    st.session_state['scan_results'] = old_data + current_results
    
    status_text.empty(); prog_bar.empty()
    st.success("Escaneo Finalizado")

# --- MOSTRAR RESULTADOS ---
if st.session_state['scan_results']:
    
    df_results = pd.DataFrame(st.session_state['scan_results'])
    df_results = df_results.sort_values(by="Fecha", ascending=False)
    df_results['Fecha_Str'] = df_results['Fecha'].dt.strftime('%d-%m-%Y')
    
    # --- TABLA RESUMEN ---
    st.subheader("📋 Bitácora de Últimas Alertas (Resumen)")
    
    c1, c2 = st.columns([1, 4])
    with c1:
        filter_type = st.multiselect("Filtrar:", ["🟢 COMPRA", "🔴 VENTA"], default=["🟢 COMPRA", "🔴 VENTA"])
    
    df_show = df_results[df_results['Tipo'].isin(filter_type)] if filter_type else df_results

    def color_signal(val):
        color = 'green' if 'COMPRA' in val else 'red'
        return f'color: {color}; font-weight: bold'

    st.dataframe(
        df_show[['Ticker', 'Fecha_Str', 'Tipo', 'Precio', 'ADX']],
        column_config={
            "Precio": st.column_config.NumberColumn(format="$%.2f"),
            "ADX": st.column_config.NumberColumn(format="%.2f"),
            "Fecha_Str": "Fecha Alerta"
        },
        use_container_width=True, hide_index=True
    )
    
    st.divider()
    
    # --- VISUALIZADOR DE GRÁFICO (CON HISTORIAL COMPLETO) ---
    st.subheader("📉 Visualizador de Gráfico (Histórico Completo)")
    
    available_tickers = df_show['Ticker'].tolist()
    
    if available_tickers:
        selected_ticker = st.selectbox("Selecciona un activo para ver TODAS las señales:", available_tickers)
        
        if selected_ticker:
            # Recuperar info de la última señal para mostrar datos
            sig_info = df_show[df_show['Ticker'] == selected_ticker].iloc[0]
            
            with st.spinner("Generando gráfico histórico..."):
                # Volvemos a llamar a la función para obtener TODAS las señales y la data
                _, df_chart, all_signals = analyze_ticker(selected_ticker, interval, period_map[interval], adx_len, adx_th)
            
            if df_chart is not None:
                # Filtrado de velas para el gráfico (últimos N periodos)
                chart_limit = 200 if interval != "1mo" else 1000 # Más historia si es mensual
                chart_data = df_chart.tail(chart_limit)
                
                # Crear Figura
                fig = go.Figure()

                # 1. Velas HA
                fig.add_trace(go.Candlestick(
                    x=chart_data.index,
                    open=chart_data['HA_Open'], high=chart_data['HA_High'],
                    low=chart_data['HA_Low'], close=chart_data['HA_Close'],
                    name='Heikin Ashi'
                ))
                
                # 2. Convertir lista de señales a DataFrame para filtrar fácil
                if all_signals:
                    df_sig_hist = pd.DataFrame(all_signals)
                    
                    # Filtrar solo señales que estén dentro del rango visible del gráfico
                    min_date = chart_data.index.min()
                    df_sig_visible = df_sig_hist[df_sig_hist['Fecha'] >= min_date]
                    
                    # Separar Compras y Ventas
                    buys = df_sig_visible[df_sig_visible['Tipo'] == '🟢 COMPRA']
                    sells = df_sig_visible[df_sig_visible['Tipo'] == '🔴 VENTA']
                    
                    # Plotear Compras (Triángulo Verde Arriba)
                    if not buys.empty:
                        fig.add_trace(go.Scatter(
                            x=buys['Fecha'], y=buys['Precio'] * 0.95, # Un poco abajo
                            mode='markers',
                            marker=dict(symbol='triangle-up', size=12, color='blue'),
                            name='Compra',
                            hovertemplate='<b>COMPRA</b><br>Fecha: %{x}<br>Precio: $%{y:.2f}'
                        ))
                        
                    # Plotear Ventas (Triángulo Rojo Abajo)
                    if not sells.empty:
                        fig.add_trace(go.Scatter(
                            x=sells['Fecha'], y=sells['Precio'] * 1.05, # Un poco arriba
                            mode='markers',
                            marker=dict(symbol='triangle-down', size=12, color='orange'),
                            name='Venta',
                            hovertemplate='<b>VENTA</b><br>Fecha: %{x}<br>Precio: $%{y:.2f}'
                        ))

                fig.update_layout(
                    title=f"Historial de Señales: {selected_ticker} ({interval})",
                    xaxis_rangeslider_visible=False,
                    height=600,
                    template="plotly_dark",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Métrica rápida
                st.info(f"Mostrando **{len(df_sig_visible)} señales** en el periodo visible del gráfico.")

    else:
        st.info("No hay activos disponibles.")

else:
    st.info("👈 Selecciona un lote y escanea para ver señales.")
