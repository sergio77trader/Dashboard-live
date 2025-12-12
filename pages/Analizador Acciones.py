import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
import numpy as np
import time

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Scanner Masivo: HA + ADX (Fixed)")

# --- ESTILOS VISUALES ---
st.markdown("""
<style>
    div[data-testid="stMetric"], .metric-card {
        background-color: #0e1117; border: 1px solid #303030;
        padding: 10px; border-radius: 8px; text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# --- BASE DE DATOS MAESTRA ---
TICKERS_DB = sorted([
    'GGAL', 'YPF', 'BMA', 'PAMP', 'TGS', 'CEPU', 'EDN', 'BFR', 'SUPV', 'CRESY', 'IRS', 'TEO', 'LOMA', 'DESP', 'VIST', 'GLOB', 'MELI', 'BIOX',
    'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NFLX', 'CRM', 'ORCL', 'ADBE', 'IBM', 'CSCO', 'PLTR',
    'AMD', 'INTC', 'QCOM', 'AVGO', 'TXN', 'MU', 'ADI', 'AMAT', 'ARM', 'SMCI', 'TSM', 'ASML',
    'JPM', 'BAC', 'C', 'WFC', 'GS', 'MS', 'V', 'MA', 'AXP', 'BRK-B', 'PYPL', 'SQ', 'COIN',
    'KO', 'PEP', 'MCD', 'SBUX', 'DIS', 'NKE', 'WMT', 'COST', 'TGT', 'HD', 'PG',
    'XOM', 'CVX', 'SLB', 'BA', 'CAT', 'DE', 'GE', 'MMM', 'LMT', 'F', 'GM',
    'PBR', 'VALE', 'ITUB', 'BBD', 'ERJ', 'BABA', 'JD', 'BIDU', 'NIO', 'GOLD', 'NEM', 'FCX',
    'SPY', 'QQQ', 'IWM', 'DIA', 'EEM', 'EWZ', 'XLE', 'XLF', 'XLK', 'XLV', 'ARKK', 'GLD', 'SLV', 'GDX'
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
    df_ha['Color'] = np.where(df_ha['HA_Close'] > df_ha['HA_Open'], 1, -1)
    return df_ha

def get_last_signal(ticker, interval_main, interval_filter, adx_len, th_micro, th_macro):
    """Analiza y devuelve la última señal"""
    try:
        period_map = {"1mo": "max", "1wk": "10y", "1d": "5y", "1h": "730d"}
        
        # 1. Descargar
        df_main = yf.download(ticker, interval=interval_main, period=period_map[interval_main], progress=False, auto_adjust=True)
        df_filter = yf.download(ticker, interval=interval_filter, period="max", progress=False, auto_adjust=True)
        
        if df_main.empty or df_filter.empty: return None
        
        # Limpieza MultiIndex
        if isinstance(df_main.columns, pd.MultiIndex): df_main.columns = df_main.columns.get_level_values(0)
        if isinstance(df_filter.columns, pd.MultiIndex): df_filter.columns = df_filter.columns.get_level_values(0)

        # 2. Indicadores
        df_main.ta.adx(length=adx_len, append=True)
        df_main = calculate_heikin_ashi(df_main)
        col_adx_main = f"ADX_{adx_len}"
        
        df_filter.ta.adx(length=adx_len, append=True)
        col_adx_filter = f"ADX_{adx_len}"
        
        # 3. Sincronizar
        adx_filter_aligned = df_filter[col_adx_filter].reindex(df_main.index, method='ffill')
        df_main['ADX_Filter_Val'] = adx_filter_aligned

        # 4. Buscar última señal
        last_signal = None
        in_position = False
        
        buy_cond = (df_main['Color'] == 1) & (df_main[col_adx_main] > th_micro) & (df_main['ADX_Filter_Val'] > th_macro)
        sell_cond = (df_main['Color'] == -1)
        
        for i in range(1, len(df_main)):
            date = df_main.index[i]
            price = df_main['Close'].iloc[i]
            
            if not in_position and buy_cond.iloc[i]:
                in_position = True
                last_signal = {
                    "Ticker": ticker, "Fecha": date, "Tipo": "🟢 COMPRA",
                    "Precio": price, "ADX Gatillo": df_main[col_adx_main].iloc[i],
                    "ADX Filtro": df_main['ADX_Filter_Val'].iloc[i], "Estado Actual": "ABIERTA"
                }
            elif in_position and sell_cond.iloc[i]:
                in_position = False
                last_signal = {
                    "Ticker": ticker, "Fecha": date, "Tipo": "🔴 VENTA",
                    "Precio": price, "ADX Gatillo": df_main[col_adx_main].iloc[i],
                    "ADX Filtro": df_main['ADX_Filter_Val'].iloc[i], "Estado Actual": "CERRADA"
                }
                
        return last_signal

    except Exception as e: return None

# --- FUNCIÓN PARA GRAFICAR ---
def plot_ticker_chart(ticker, signal_date, signal_type, interval):
    """Grafica el activo seleccionado y marca la señal"""
    try:
        # Descargamos data para el gráfico
        period_map = {"1mo": "max", "1wk": "5y", "1d": "2y", "1h": "6mo"}
        df = yf.download(ticker, interval=interval, period=period_map.get(interval, "2y"), progress=False, auto_adjust=True)
        
        if df.empty:
            st.error("No se pudieron cargar los datos del gráfico.")
            return

        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # Calculamos HA para visualización
        df_ha = calculate_heikin_ashi(df)
        
        # Filtrar últimas velas para que se vea bien
        chart_data = df_ha.tail(100) if len(df_ha) > 100 else df_ha

        # Crear Figura
        fig = go.Figure()

        # Velas HA
        fig.add_trace(go.Candlestick(
            x=chart_data.index,
            open=chart_data['HA_Open'], high=chart_data['HA_High'],
            low=chart_data['HA_Low'], close=chart_data['HA_Close'],
            name='Heikin Ashi'
        ))

        # Añadir marcador de señal
        # Convertimos signal_date a timestamp si es string (o ya viene como ts)
        sig_dt = pd.to_datetime(signal_date)
        
        # Ajuste de fecha para mensual (Yahoo a veces pone 1er dia del mes, a veces ultimo)
        # Intentamos encontrar la fecha más cercana en el índice
        if not chart_data.empty:
            if sig_dt in chart_data.index:
                actual_date = sig_dt
            else:
                # Buscamos el índice más cercano (útil para mensual)
                actual_date = chart_data.index[chart_data.index.get_indexer([sig_dt], method='nearest')[0]]

            y_pos = chart_data.loc[actual_date]['Low'] * 0.95 if "COMPRA" in signal_type else chart_data.loc[actual_date]['High'] * 1.05
            symbol = "triangle-up" if "COMPRA" in signal_type else "triangle-down"
            color = "#00FF00" if "COMPRA" in signal_type else "#FF0000"
            
            fig.add_trace(go.Scatter(
                x=[actual_date], y=[y_pos],
                mode='markers+text',
                marker=dict(symbol=symbol, size=15, color=color),
                text=[signal_type], textposition="bottom center" if "COMPRA" in signal_type else "top center",
                name='Señal'
            ))

        fig.update_layout(
            title=f"Gráfico {ticker} ({interval}) - Heikin Ashi",
            xaxis_rangeslider_visible=False,
            template="plotly_dark",
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error al graficar: {e}")

# --- UI LATERAL ---
with st.sidebar:
    st.header("⚙️ Configuración")
    st.info(f"DB: {len(TICKERS_DB)} Activos")
    
    int_main = st.selectbox("Temporalidad Gráfico", ["1mo", "1wk", "1d"], index=0)
    int_filter = st.selectbox("Temporalidad Filtro", ["1mo", "1wk", "1d"], index=0) 
    
    st.subheader("ADX")
    p_len = st.number_input("Longitud", value=14)
    p_micro = st.number_input("Umbral Gatillo", value=25)
    p_macro = st.number_input("Umbral Filtro", value=20)
    
    st.divider()
    
    batch_size = st.slider("Lote", 5, 50, 10)
    batches = [TICKERS_DB[i:i + batch_size] for i in range(0, len(TICKERS_DB), batch_size)]
    batch_labels = [f"Lote {i+1}: {b[0]} ... {b[-1]}" for i, b in enumerate(batches)]
    sel_batch = st.selectbox("Seleccionar Lote:", range(len(batches)), format_func=lambda x: batch_labels[x])
    
    run_btn = st.button("🚀 ESCANEAR LOTE", type="primary")
    
    if st.button("🗑️ Limpiar"):
        st.session_state['scan_results'] = []
        st.rerun()

# --- APP PRINCIPAL ---
st.title("🛰️ Escáner Masivo: HA + ADX")

if 'scan_results' not in st.session_state: st.session_state['scan_results'] = []

if run_btn:
    targets = batches[sel_batch]
    prog_bar = st.progress(0)
    status = st.empty()
    new_data = []
    
    for i, t in enumerate(targets):
        status.text(f"Analizando {t}...")
        signal_data = get_last_signal(t, int_main, int_filter, p_len, p_micro, p_macro)
        if signal_data: new_data.append(signal_data)
        prog_bar.progress((i + 1) / len(targets))
    
    current_tickers = [x['Ticker'] for x in st.session_state['scan_results']]
    for item in new_data:
        if item['Ticker'] not in current_tickers:
            st.session_state['scan_results'].append(item)
    
    status.empty(); prog_bar.empty(); st.rerun()

# --- RESULTADOS ---
if st.session_state['scan_results']:
    df = pd.DataFrame(st.session_state['scan_results'])
    
    c1, c2 = st.columns([1, 3])
    with c1:
        f_type = st.multiselect("Filtrar Tipo:", ["🟢 COMPRA", "🔴 VENTA"], default=["🟢 COMPRA", "🔴 VENTA"])
    
    if f_type: df_show = df[df['Tipo'].isin(f_type)]
    else: df_show = df
    
    df_show = df_show.sort_values("Fecha", ascending=False)
    
    # === CORRECCIÓN DEL ERROR ===
    # Creamos la columna Fecha_Str en el dataframe principal para que esté disponible
    # tanto para la tabla como para el selector del gráfico
    df_show['Fecha_Str'] = df_show['Fecha'].dt.strftime('%Y-%m-%d')
    
    # Tabla
    st.subheader(f"Bitácora ({len(df_show)})")
    
    def highlight_signal(val):
        return f'background-color: {"#d4edda" if "COMPRA" in str(val) else "#f8d7da"}; color: black; font-weight: bold'

    st.dataframe(
        df_show.style.applymap(highlight_signal, subset=['Tipo']),
        column_config={
            "Ticker": "Activo", "Fecha_Str": "Fecha Señal", "Precio": st.column_config.NumberColumn(format="$%.2f"),
            "ADX Gatillo": st.column_config.NumberColumn(format="%.1f"), "ADX Filtro": st.column_config.NumberColumn(format="%.1f")
        },
        use_container_width=True, hide_index=True
    )
    
    st.divider()
    
    # --- VISUALIZADOR DE GRÁFICO ---
    st.subheader("📉 Visualizador de Gráfico")
    
    available_tickers = df_show['Ticker'].tolist()
    
    if available_tickers:
        col_sel, col_info = st.columns([1, 3])
        
        with col_sel:
            selected_ticker = st.selectbox("Selecciona un activo para ver:", available_tickers)
        
        if selected_ticker:
            # Obtener datos de la señal seleccionada
            sig_info = df_show[df_show['Ticker'] == selected_ticker].iloc[0]
            
            with col_info:
                # Ahora 'Fecha_Str' existe en df_show, así que no dará error
                st.info(f"**{selected_ticker}** | Señal: {sig_info['Tipo']} el {sig_info['Fecha_Str']} a ${sig_info['Precio']:.2f}")
            
            # Graficar
            plot_ticker_chart(selected_ticker, sig_info['Fecha'], sig_info['Tipo'], int_main)
    else:
        st.info("No hay activos visibles en la tabla para graficar.")
    
else:
    st.info("👈 Selecciona un lote y escanea para ver señales.")
