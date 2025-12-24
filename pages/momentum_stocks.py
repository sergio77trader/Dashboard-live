import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Stocks: HA + MACD Momentum")

# --- ESTILOS ---
st.markdown("""
<style>
    div[data-testid="stMetric"], .metric-card {
        background-color: #0e1117; border: 1px solid #303030;
        padding: 10px; border-radius: 8px; text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# --- BASE DE DATOS ACCIONES ---
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

# --- FUNCIONES MATEMÁTICAS ---
def calculate_heikin_ashi(df):
    df_ha = df.copy()
    df_ha['HA_Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    
    # Inicialización
    ha_open = [df['Open'].iloc[0]]
    for i in range(1, len(df)):
        ha_open.append((ha_open[-1] + df_ha['HA_Close'].iloc[i-1]) / 2)
    df_ha['HA_Open'] = ha_open
    
    df_ha['Color'] = np.where(df_ha['HA_Close'] > df_ha['HA_Open'], 1, -1)
    return df_ha

def calculate_macd(df, fast=12, slow=26, signal=9):
    exp1 = df['Close'].ewm(span=fast, adjust=False).mean()
    exp2 = df['Close'].ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    sig = macd.ewm(span=signal, adjust=False).mean()
    hist = macd - sig
    return hist

def resample_data(df, hours):
    logic = {'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}
    return df.resample(f"{hours}h").agg(logic).dropna()

def analyze_timeframe(df):
    if df is None or len(df) < 30: return {"Señal": "Insuf. Datos", "Score": 0}
    
    df_ha = calculate_heikin_ashi(df)
    hist = calculate_macd(df)
    
    # Datos actuales y previos
    curr_color = df_ha['Color'].iloc[-1]
    prev_color = df_ha['Color'].iloc[-2]
    
    curr_hist = hist.iloc[-1]
    prev_hist = hist.iloc[-2]
    
    # Lógica de Cambio
    ha_flip_green = (prev_color == -1) and (curr_color == 1)
    ha_flip_red   = (prev_color == 1) and (curr_color == -1)
    
    hist_subiendo = curr_hist > prev_hist
    hist_bajando  = curr_hist < prev_hist
    
    signal = "NEUTRO"
    
    # ESTRATEGIA
    if ha_flip_green and (curr_hist < 0) and hist_subiendo:
        signal = "🟢 ENTRADA LONG"
    elif ha_flip_red and (curr_hist > 0) and hist_bajando:
        signal = "🔴 ENTRADA SHORT"
    else:
        if curr_color == 1 and hist_bajando: signal = "⚠️ SALIDA LONG"
        elif curr_color == -1 and hist_subiendo: signal = "⚠️ SALIDA SHORT"
        elif curr_color == 1: signal = "🔼 MANTENER LONG"
        elif curr_color == -1: signal = "🔽 MANTENER SHORT"

    return {
        "Señal": signal,
        "Precio": df['Close'].iloc[-1],
        "HA": "Verde" if curr_color == 1 else "Rojo",
        "Hist": curr_hist,
        "Hist_Dir": "↗️" if hist_subiendo else "↘️"
    }

def get_data(ticker, tf_code):
    try:
        # Descarga inteligente según TF
        if tf_code == "15m": df = yf.download(ticker, interval="15m", period="5d", progress=False)
        elif tf_code == "1h": df = yf.download(ticker, interval="1h", period="200d", progress=False)
        elif tf_code in ["2h", "4h", "12h"]:
            df = yf.download(ticker, interval="1h", period="200d", progress=False)
            if not df.empty: df = resample_data(df, int(tf_code.replace("h","")))
        elif tf_code == "1d": df = yf.download(ticker, interval="1d", period="2y", progress=False)
        elif tf_code == "1wk": df = yf.download(ticker, interval="1wk", period="5y", progress=False)
        elif tf_code == "1mo": df = yf.download(ticker, interval="1mo", period="max", progress=False)
        
        if df.empty: return None
        # Limpieza MultiIndex si existe
        if isinstance(df.columns, pd.MultiIndex): 
            df.columns = df.columns.get_level_values(0)
            
        return df
    except: return None

# --- UI ---
st.title("📊 Stock Matrix: HA + MACD Momentum")

with st.sidebar:
    st.header("Selector")
    selected_ticker = st.selectbox("Elige Acción:", TICKERS)
    st.markdown("---")
    if st.button("ANALIZAR MATRIZ"):
        st.session_state['run_stock'] = True

if st.session_state.get('run_stock', False):
    tfs = [("15 Min", "15m"), ("1 Hora", "1h"), ("2 Horas", "2h"), ("4 Horas", "4h"), 
           ("12 Horas", "12h"), ("Diario", "1d"), ("Semanal", "1wk"), ("Mensual", "1mo")]
    
    results = []
    prog = st.progress(0)
    
    for i, (label, code) in enumerate(tfs):
        data = get_data(selected_ticker, code)
        
        # --- CORRECCIÓN AQUÍ ---
        # Verificamos correctamente si el dataframe es válido y no está vacío
        if data is not None and not data.empty:
            res = analyze_timeframe(data)
            results.append({
                "Temporalidad": label,
                "Diagnóstico": res['Señal'],
                "Vela HA": "🟢" if res['HA'] == "Verde" else "🔴",
                "MACD Hist": f"{res['Hist']:.4f} {res['Hist_Dir']}",
                "Precio": res['Precio']
            })
        else:
            results.append({"Temporalidad": label, "Diagnóstico": "Sin Datos"})
            
        prog.progress((i+1)/len(tfs))
    
    prog.empty()
    df_res = pd.DataFrame(results)
    
    def color_row(val):
        if "ENTRADA LONG" in str(val): return "background-color: #0f3d0f; color: #4caf50; font-weight: bold"
        if "ENTRADA SHORT" in str(val): return "background-color: #3d0f0f; color: #f44336; font-weight: bold"
        if "SALIDA" in str(val): return "color: orange; font-weight: bold"
        return ""

    st.subheader(f"Análisis Matricial: {selected_ticker}")
    st.dataframe(
        df_res.style.applymap(color_row, subset=['Diagnóstico']),
        column_config={"Precio": st.column_config.NumberColumn(format="$%.2f")},
        use_container_width=True, hide_index=True, height=400
    )
    
    st.info("Estrategia: Entrar en giro de vela HA + Momentum MACD a favor. Salir si el MACD pierde fuerza.")
