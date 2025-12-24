import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Stock Matrix: Robusto")

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

# --- MATEMÁTICA EXACTA (RSI Wilder) ---
def calculate_rsi(series, period=14):
    if len(series) < period: return 50.0
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

def calculate_heikin_ashi_daily(df):
    """Calcula el color de la vela HA Diaria actual"""
    if df.empty: return 0
    ha_open = [df['Open'].iloc[0]]
    ha_close = [(df['Open'].iloc[0] + df['High'].iloc[0] + df['Low'].iloc[0] + df['Close'].iloc[0]) / 4]
    
    for i in range(1, len(df)):
        current_close = (df['Open'].iloc[i] + df['High'].iloc[i] + df['Low'].iloc[i] + df['Close'].iloc[i]) / 4
        current_open = (ha_open[-1] + ha_close[-1]) / 2
        ha_close.append(current_close)
        ha_open.append(current_open)
        
    last_c = ha_close[-1]
    last_o = ha_open[-1]
    return 1 if last_c > last_o else -1

# --- CONSTRUCTOR DE VELAS (Resampling) ---
def resample_candles(df_base, hours):
    """
    Toma datos de 1 Hora y construye velas de X horas.
    df_base debe tener 'Open', 'High', 'Low', 'Close'
    """
    if df_base.empty: return pd.DataFrame()
    
    rule = f"{hours}h"
    agg_dict = {'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'}
    
    df_resampled = df_base.resample(rule).agg(agg_dict).dropna()
    return df_resampled

# --- MOTOR DE DATOS (Más Robusto) ---
@st.cache_data(ttl=1800) # Cache de 30 min
def fetch_all_data(tickers):
    data_d = {}
    data_h = {}
    
    # 1. Descarga Diaria (5 años) - Una por una para manejar errores
    for t in tickers:
        try:
            df = yf.download(t, period="5y", interval="1d", progress=False, auto_adjust=True, timeout=10)
            if not df.empty: data_d[t] = df
        except: pass
    
    # 2. Descarga Horaria (730 días) - Una por una
    for t in tickers:
        try:
            df = yf.download(t, period="730d", interval="1h", group_by='ticker', progress=False, auto_adjust=True, timeout=10)
            if not df.empty:
                # Si descarga un solo ticker, yfinance no crea MultiIndex
                if len(tickers) == 1: data_h[t] = df
                else:
                    if t in df.columns.levels[0]: data_h[t] = df[t]
                    else: data_h[t] = df # Fallback
        except: pass
            
    return data_d, data_h

def process_tickers(tickers):
    df_daily_dict, df_hourly_dict = fetch_all_data(tickers)
    
    results = []
    prog = st.progress(0)
    
    # Manejamos los tickers que no se pudieron descargar
    download_failures = []
    
    for i, t in enumerate(tickers):
        try:
            d_df = df_daily_dict.get(t) # Usamos .get() para no fallar si falta el ticker
            h_df = df_hourly_dict.get(t)
            
            if d_df is None or d_df.empty or h_df is None or h_df.empty:
                download_failures.append(t)
                continue # Saltar este ticker y seguir

            # --- CÁLCULOS MULTI-TF ---
            
            # 1. Semanal
            w_df = d_df['Close'].resample('W-FRI').last().dropna()
            rsi_w = calculate_rsi(w_df)
            
            # 2. Diario
            rsi_d = calculate_rsi(d_df['Close'])
            ha_color = calculate_heikin_ashi_daily(d_df)
            
            # 3. Intradía (Resampleo)
            h8_df = resample_candles(h_df, 8)
            h4_df = resample_candles(h_df, 4)
            h2_df = resample_candles(h_df, 2)
            
            rsi_8h = calculate_rsi(h8_df['Close']) if not h8_df.empty else 50.0
            rsi_4h = calculate_rsi(h4_df['Close']) if not h4_df.empty else 50.0
            rsi_2h = calculate_rsi(h2_df['Close']) if not h2_df.empty else 50.0
            
            # 4. 1 Hora
            rsi_1h = calculate_rsi(h_df['Close'])
            
            # --- ESTRATEGIA ---
            all_rsis = [rsi_w, rsi_d, rsi_8h, rsi_4h, rsi_2h, rsi_1h]
            all_rsis = [x for x in all_rsis if not np.isnan(x)]
            
            if not all_rsis: continue

            is_overbought = any(r > 70 for r in all_rsis)
            is_oversold = any(r < 30 for r in all_rsis)
            
            signal = "NEUTRO"
            score = 0 
            
            if is_overbought and ha_color == -1:
                signal = "🔴 SHORT"
                score = -1
            elif is_oversold and ha_color == 1:
                signal = "🟢 LONG"
                score = 1
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
                "RSI_8H": rsi_8h,
                "RSI_4H": rsi_4h,
                "RSI_2H": rsi_2h,
                "RSI_1H": rsi_1h,
                "Score": score
            })
            
        except Exception: pass
        prog.progress((i+1)/len(tickers))
        
    prog.empty()
    
    if download_failures:
        st.error(f"⚠️ No se pudieron descargar datos para: {', '.join(download_failures)}. Intentando de nuevo en el próximo lote.")
        
    return results

# --- INTERFAZ ---
st.title("📊 Stock Matrix: Multi-TF Robusto")
st.markdown("Monitor de RSI en: **Semanal, Diario, 8H, 4H, 2H, 1H**")

if 'stock_results_v3' not in st.session_state:
    st.session_state['stock_results_v3'] = []

with st.sidebar:
    st.header("Configuración")
    st.info(f"Base de Datos: {len(TICKERS)} Acciones")
    
    batch_size = st.slider("Tamaño de Lote", 10, 100, 50)
    batches = [TICKERS[i:i + batch_size] for i in range(0, len(TICKERS), batch_size)]
    batch_labels = [f"Lote {i+1}: {b[0]} ... {b[-1]}" for i, b in enumerate(batches)]
    sel_batch = st.selectbox("Seleccionar Lote:", range(len(batches)), format_func=lambda x: batch_labels[x])
    
    if st.button("🔄 ESCANEAR LOTE (ACUMULAR)", type="primary"):
        targets = batches[sel_batch]
        new_results = process_tickers(targets)
        
        if new_results:
            current_data = st.session_state['stock_results_v3']
            tickers_to_update = [x['Ticker'] for x in new_results]
            data_kept = [row for row in current_data if row['Ticker'] not in tickers_to_update]
            st.session_state['stock_results_v3'] = data_kept + new_results
            st.success(f"Se actualizaron {len(new_results)} activos.")
        else:
            st.warning("No se encontraron datos válidos en este lote.")

    if st.button("🗑️ Limpiar Todo"):
        st.session_state['stock_results_v3'] = []
        st.rerun()

# --- RESULTADOS ---
if st.session_state['stock_results_v3']:
    df = pd.DataFrame(st.session_state['stock_results_v3'])
    
    priority = {"🟢 LONG": 4, "🔴 SHORT": 4, "⚠️ Techo (Esperar HA Rojo)": 2, "⚠️ Piso (Esperar HA Verde)": 2, "NEUTRO": 1}
    df['Prio'] = df['Señal'].map(priority).fillna(1)
    df = df.sort_values(by='Prio', ascending=False)
    
    def style_rsi(val):
        if pd.isna(val): return ''
        if val >= 70: return 'color: #ff4b4b; font-weight: bold;'
        if val <= 30: return 'color: #00c853; font-weight: bold;'
        return 'color: #aaa;'
    
    def style_signal(val):
        if "LONG" in val: return 'background-color: rgba(0, 200, 83, 0.2); color: #00c853; font-weight: bold;'
        if "SHORT" in val: return 'background-color: rgba(255, 75, 75, 0.2); color: #ff4b4b; font-weight: bold;'
        if "⚠️" in val: return 'color: orange; font-weight: bold;'
        return ''
    
    c1, c2, c3 = st.columns(3)
    longs = len(df[df['Señal'].str.contains("LONG", na=False)])
    shorts = len(df[df['Señal'].str.contains("SHORT", na=False)])
    alerts = len(df[df['Señal'].str.contains("⚠️", na=False)])
    
    c1.metric("Oportunidades LONG", longs)
    c2.metric("Oportunidades SHORT", shorts)
    c3.metric("En Observación", alerts)
    
    st.dataframe(
        df.style.map(style_rsi, subset=['RSI_W', 'RSI_D', 'RSI_8H', 'RSI_4H', 'RSI_2H', 'RSI_1H'])
                .map(style_signal, subset=['Señal']),
        column_config={
            "Ticker": "Activo",
            "Precio": st.column_config.NumberColumn(format="$%.2f"),
            "HA_D": st.column_config.TextColumn("Vela D", help="1=Verde, -1=Roja"),
            "RSI_W": st.column_config.NumberColumn("Semanal", format="%.0f"),
            "RSI_D": st.column_config.NumberColumn("Diario", format="%.0f"),
            "RSI_8H": st.column_config.NumberColumn("8H", format="%.0f"),
            "RSI_4H": st.column_config.NumberColumn("4H", format="%.0f"),
            "RSI_2H": st.column_config.NumberColumn("2H", format="%.0f"),
            "RSI_1H": st.column_config.NumberColumn("1H", format="%.0f"),
        },
        use_container_width=True,
        hide_index=True,
        height=600
    )

else:
    st.info("👈 Selecciona un lote y pulsa ESCANEAR.")
