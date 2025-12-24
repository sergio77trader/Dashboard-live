import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
import plotly.graph_objects as go

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Stock Matrix: RSI + HA (Acumulativo)")

# --- ESTILOS VISUALES ---
st.markdown("""
<style>
    div[data-testid="stMetric"], .metric-card {
        background-color: #0e1117; border: 1px solid #303030;
        padding: 10px; border-radius: 8px; text-align: center;
    }
    .rsi-hot { color: #ff4b4b; font-weight: bold; }
    .rsi-cold { color: #00c853; font-weight: bold; }
    .rsi-neutral { color: #888; }
</style>
""", unsafe_allow_html=True)

# --- BASE DE DATOS (Tus Tickers) ---
TICKERS = sorted([
    'GGAL', 'YPF', 'BMA', 'PAMP', 'TGS', 'CEPU', 'EDN', 'BFR', 'SUPV', 'CRESY', 'IRS', 'TEO', 'LOMA', 'DESP', 'VIST', 'GLOB', 'MELI', 'BIOX', 'TX',
    'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NFLX',
    'CRM', 'ORCL', 'ADBE', 'IBM', 'CSCO', 'PLTR', 'SNOW', 'SHOP', 'SPOT', 'UBER', 'ABNB', 'SAP', 'INTU', 'NOW',
    'AMD', 'INTC', 'QCOM', 'AVGO', 'TXN', 'MU', 'ADI', 'AMAT', 'ARM', 'SMCI', 'TSM', 'ASML', 'LRCX', 'HPQ', 'DELL',
    'JPM', 'BAC', 'C', 'WFC', 'GS', 'MS', 'V', 'MA', 'AXP', 'BRK-B', 'PYPL', 'SQ', 'COIN', 'BLK', 'USB', 'NU',
    'KO', 'PEP', 'MCD', 'SBUX', 'DIS', 'NKE', 'WMT', 'COST', 'TGT', 'HD', 'LOW', 'PG', 'CL', 'MO', 'PM', 'KMB', 'EL',
    'JNJ', 'PFE', 'MRK', 'LLY', 'ABBV', 'UNH', 'BMY', 'AMGN', 'GILD', 'AZN', 'NVO', 'NVS', 'CVS',
    'BA', 'CAT', 'DE', 'GE', 'MMM', 'LMT', 'RTX', 'HON', 'UNP', 'UPS', 'FDX', 'LUV', 'DAL',
    'F', 'GM', 'TM', 'HMC', 'STLA', 'RACE',
    'XOM', 'CVX', 'SLB', 'OXY', 'HAL', 'BP', 'SHEL', 'TTE', 'PBR', 'VLO',
    'VZ', 'T', 'TMUS', 'VOD',
    'BABA', 'JD', 'BIDU', 'NIO', 'PDD', 'TCEHY', 'TCOM', 'BEKE', 'XPEV', 'LI', 'SONY',
    'VALE', 'ITUB', 'BBD', 'ERJ', 'ABEV', 'GGB', 'SID', 'NBR',
    'GOLD', 'NEM', 'PAAS', 'FCX', 'SCCO', 'RIO', 'BHP', 'ALB', 'SQM',
    'SPY', 'QQQ', 'IWM', 'DIA', 'EEM', 'EWZ', 'FXI', 'XLE', 'XLF', 'XLK', 'XLV', 'XLI', 'XLP', 'XLU', 'XLY', 'ARKK', 'SMH', 'TAN', 'GLD', 'SLV', 'GDX'
])

# --- FUNCIONES DE CÁLCULO ---

def calculate_rsi(series, period=14):
    if len(series) < period: return 50.0
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

def calculate_heikin_ashi_daily(df):
    """Calcula el color de la vela HA Diaria actual"""
    if df.empty: return 0
    
    # Cierre HA actual
    ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    
    # Apertura HA actual (Aprox para escáner rápido)
    ha_open = (df['Open'].shift(1) + df['Close'].shift(1)) / 2
    
    last_c = ha_close.iloc[-1]
    last_o = ha_open.iloc[-1]
    
    # Color: 1 Verde, -1 Rojo
    color = 1 if last_c > last_o else -1
    return color

# --- MOTOR DE DATOS ---

@st.cache_data(ttl=1800) 
def fetch_all_data(tickers):
    # Descarga optimizada
    try:
        # 1. Datos Diarios (2 años para cálculos robustos)
        df_d = yf.download(tickers, period="2y", interval="1d", group_by='ticker', progress=False, auto_adjust=True)
        
        # 2. Datos Intradía (1 Hora - 3 meses)
        df_h = yf.download(tickers, period="3mo", interval="1h", group_by='ticker', progress=False, auto_adjust=True)
        
        return df_d, df_h
    except Exception as e:
        return None, None

def process_tickers(tickers):
    df_daily_all, df_hourly_all = fetch_all_data(tickers)
    
    if df_daily_all is None: return []
    
    results = []
    prog = st.progress(0)
    
    for i, t in enumerate(tickers):
        try:
            # Extraer DF individual
            if len(tickers) > 1:
                d_df = df_daily_all[t].dropna()
                h_df = df_hourly_all[t].dropna()
            else:
                d_df = df_daily_all.dropna()
                h_df = df_hourly_all.dropna()
                
            if d_df.empty or h_df.empty: continue
            
            # --- 1. RSI SEMANAL ---
            w_df = d_df['Close'].resample('W-FRI').last()
            rsi_w = calculate_rsi(w_df)
            
            # --- 2. RSI DIARIO & HEIKIN ASHI ---
            rsi_d = calculate_rsi(d_df['Close'])
            ha_color = calculate_heikin_ashi_daily(d_df)
            
            # --- 3. RSI 4 HORAS (Sintético) ---
            h4_df = h_df['Close'].resample('4h').last().dropna()
            rsi_4h = calculate_rsi(h4_df)
            
            # --- 4. RSI 1 HORA ---
            rsi_1h = calculate_rsi(h_df['Close'])
            
            # --- ESTRATEGIA ---
            all_rsis = [rsi_w, rsi_d, rsi_4h, rsi_1h]
            is_overbought = any(r > 70 for r in all_rsis)
            is_oversold = any(r < 30 for r in all_rsis)
            
            signal = "NEUTRO"
            score = 0 
            
            # VENTA
            if is_overbought and ha_color == -1:
                signal = "🔴 SHORT"
                score = -1
            # COMPRA
            elif is_oversold and ha_color == 1:
                signal = "🟢 LONG"
                score = 1
            # ALERTAS
            elif is_overbought and ha_color == 1:
                signal = "⚠️ Techo (Esperar HA Rojo)"
                score = 0.5
            elif is_oversold and ha_color == -1:
                signal = "⚠️ Piso (Esperar HA Verde)"
                score = 0.5

            results.append({
                "Ticker": t,
                "Precio": d_df['Close'].iloc[-1],
                "Señal": signal,
                "HA_D": ha_color,
                "RSI_W": rsi_w,
                "RSI_D": rsi_d,
                "RSI_4H": rsi_4h,
                "RSI_1H": rsi_1h,
                "Score": score
            })
            
        except Exception: pass
        prog.progress((i+1)/len(tickers))
        
    prog.empty()
    return results

# --- INTERFAZ ---
st.title("📊 Stock Matrix: RSI Multi-TF + HA (Acumulativo)")

# Inicializar Estado si no existe
if 'stock_results' not in st.session_state:
    st.session_state['stock_results'] = []

with st.sidebar:
    st.header("Configuración")
    st.info(f"Base de Datos: {len(TICKERS)} Acciones")
    
    batch_size = st.slider("Tamaño de Lote", 10, 100, 50)
    batches = [TICKERS[i:i + batch_size] for i in range(0, len(TICKERS), batch_size)]
    batch_labels = [f"Lote {i+1}: {b[0]} ... {b[-1]}" for i, b in enumerate(batches)]
    sel_batch = st.selectbox("Seleccionar Lote:", range(len(batches)), format_func=lambda x: batch_labels[x])
    
    if st.button("🔄 ESCANEAR LOTE (ACUMULAR)", type="primary"):
        targets = batches[sel_batch]
        
        # 1. Escanear nuevos datos
        new_results = process_tickers(targets)
        
        if new_results:
            # 2. Obtener lista actual y eliminar los que se van a actualizar (para no duplicar)
            current_data = st.session_state['stock_results']
            tickers_to_update = [x['Ticker'] for x in new_results]
            
            # Filtramos los viejos que coincidan con los nuevos
            data_kept = [row for row in current_data if row['Ticker'] not in tickers_to_update]
            
            # 3. Sumar los nuevos
            st.session_state['stock_results'] = data_kept + new_results
            st.success(f"Se actualizaron {len(new_results)} activos.")
        else:
            st.warning("No se encontraron datos para este lote.")

    if st.button("🗑️ Limpiar Todo"):
        st.session_state['stock_results'] = []
        st.rerun()

# --- RESULTADOS ---
if st.session_state['stock_results']:
    df = pd.DataFrame(st.session_state['stock_results'])
    
    # Ordenar por prioridad de señal
    priority = {"🟢 LONG": 4, "🔴 SHORT": 4, "⚠️ Techo (Esperar HA Rojo)": 2, "⚠️ Piso (Esperar HA Verde)": 2, "NEUTRO": 1}
    df['Prio'] = df['Señal'].map(priority).fillna(1)
    df = df.sort_values(by='Prio', ascending=False)
    
    # ESTILOS
    def style_rsi(val):
        if val >= 70: return 'color: #ff4b4b; font-weight: bold;'
        if val <= 30: return 'color: #00c853; font-weight: bold;'
        return 'color: #aaa;'
    
    def style_signal(val):
        if "LONG" in val: return 'background-color: rgba(0, 200, 83, 0.2); color: #00c853; font-weight: bold;'
        if "SHORT" in val: return 'background-color: rgba(255, 75, 75, 0.2); color: #ff4b4b; font-weight: bold;'
        if "⚠️" in val: return 'color: orange; font-weight: bold;'
        return ''
    
    # KPIs
    c1, c2, c3 = st.columns(3)
    longs = len(df[df['Señal'].str.contains("LONG", na=False)])
    shorts = len(df[df['Señal'].str.contains("SHORT", na=False)])
    alerts = len(df[df['Señal'].str.contains("⚠️", na=False)])
    
    c1.metric("Oportunidades LONG", longs)
    c2.metric("Oportunidades SHORT", shorts)
    c3.metric("En Observación", alerts)
    
    st.divider()

    st.dataframe(
        df.style.map(style_rsi, subset=['RSI_W', 'RSI_D', 'RSI_4H', 'RSI_1H'])
                .map(style_signal, subset=['Señal']),
        column_config={
            "Ticker": "Activo",
            "Precio": st.column_config.NumberColumn(format="$%.2f"),
            "HA_D": st.column_config.TextColumn("Vela D", help="1=Verde, -1=Rojo"),
            "RSI_W": st.column_config.NumberColumn("Semanal", format="%.0f"),
            "RSI_D": st.column_config.NumberColumn("Diario", format="%.0f"),
            "RSI_4H": st.column_config.NumberColumn("4 Horas", format="%.0f"),
            "RSI_1H": st.column_config.NumberColumn("1 Hora", format="%.0f"),
        },
        use_container_width=True,
        hide_index=True,
        height=600
    )

else:
    st.info("👈 Selecciona un lote y pulsa ESCANEAR para comenzar a acumular datos.")
