import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Crypto Matrix: KuCoin Edition")

# --- ESTILOS ---
st.markdown("""
<style>
    div[data-testid="stMetric"], .metric-card {
        background-color: #0e1117; border: 1px solid #333;
        padding: 10px; border-radius: 8px; text-align: center;
    }
    .bull { background-color: #0f3d0f; color: #4caf50; padding: 5px; border-radius: 5px; font-weight: bold; }
    .bear { background-color: #3d0f0f; color: #f44336; padding: 5px; border-radius: 5px; font-weight: bold; }
    .exit { color: #ff9800; font-weight: bold; }
    .neutral { color: #888; }
</style>
""", unsafe_allow_html=True)

# --- LISTA DE MONEDAS ---
TOP_COINS = ['BTC', 'ETH']
ALTCOINS = sorted([
    'SOL', 'BNB', 'XRP', 'ADA', 'AVAX', 'DOGE', 'SHIB', 'DOT',
    'LINK', 'TRX', 'MATIC', 'LTC', 'BCH', 'NEAR', 'UNI', 'ICP', 'FIL', 'APT',
    'INJ', 'LDO', 'OP', 'ARB', 'TIA', 'SEI', 'SUI', 'RNDR', 'FET', 'WLD',
    'PEPE', 'BONK', 'WIF', 'FLOKI', 'ORDI', 'SATS', 'GALA', 'SAND', 'MANA',
    'AXS', 'AAVE', 'SNX', 'MKR', 'CRV', 'DYDX', 'JUP', 'PYTH', 'ENA', 'RUNE',
    'FTM', 'ATOM', 'ALGO', 'VET', 'EGLD', 'STX', 'IMX', 'KAS', 'TAO'
])
COINS = TOP_COINS + [c for c in ALTCOINS if c not in TOP_COINS]

# --- MOTOR DE DATOS (KUCOIN) ---
def get_kucoin_data(symbol, k_interval):
    url = "https://api.kucoin.com/api/v1/market/candles"
    target = f"{symbol}-USDT"
    
    # Pedimos suficientes velas
    limit = 600 if k_interval == '1week' else 200
    
    params = {'symbol': target, 'type': k_interval, 'limit': limit}
    
    try:
        r = requests.get(url, params=params, timeout=5).json()
        if r['code'] == '200000':
            data = r['data']
            df = pd.DataFrame(data, columns=['Time','Open','Close','High','Low','Vol','Turn'])
            df = df.astype(float)
            df['Time'] = pd.to_datetime(df['Time'], unit='s')
            df = df.sort_values('Time', ascending=True).reset_index(drop=True)
            return df
        else: return None
    except Exception: return None

def resample_to_monthly(df_weekly):
    if df_weekly is None or df_weekly.empty: return pd.DataFrame()
    df = df_weekly.copy()
    df.set_index('Time', inplace=True)
    
    logic = {'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Vol': 'sum'}
    
    try: df_monthly = df.resample('ME').agg(logic).dropna()
    except: df_monthly = df.resample('M').agg(logic).dropna()
        
    df_monthly = df_monthly.reset_index()
    return df_monthly

# --- CÁLCULOS ---
def calculate_heikin_ashi(df):
    df_ha = df.copy()
    df_ha['HA_Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    
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

def analyze_dataframe(df):
    # --- CORRECCIÓN DEL ERROR ---
    # Si no hay datos suficientes, devolvemos estructura completa con valores neutros
    if df is None or len(df) < 30: 
        return {
            "Señal": "Insuf. Datos", 
            "Score": 0,
            "Precio": 0,
            "HA": "Neutro",      # Clave que faltaba
            "Hist": 0,           # Clave que faltaba
            "Hist_Dir": "-"      # Clave que faltaba
        }
    
    df_ha = calculate_heikin_ashi(df)
    hist = calculate_macd(df)
    
    curr_color = df_ha['Color'].iloc[-1]
    prev_color = df_ha['Color'].iloc[-2]
    curr_hist = hist.iloc[-1]
    prev_hist = hist.iloc[-2]
    
    ha_flip_green = (prev_color == -1) and (curr_color == 1)
    ha_flip_red   = (prev_color == 1) and (curr_color == -1)
    hist_subiendo = curr_hist > prev_hist
    hist_bajando  = curr_hist < prev_hist
    
    signal = "NEUTRO"
    
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

# --- UI ---
st.title("🛡️ Crypto Matrix: KuCoin Data (Native)")
st.markdown("Monitor de Estrategia HA + MACD Momentum usando datos directos de KuCoin.")

with st.sidebar:
    st.header("Selector")
    selected_coin = st.selectbox("Elige Criptomoneda:", COINS)
    st.markdown("---")
    if st.button("ANALIZAR MATRIZ"):
        st.session_state['run_kucoin'] = True

if st.session_state.get('run_kucoin', False):
    
    # Configuración de Timeframes
    tfs_config = [
        ("15 Min", "15min"),
        ("1 Hora", "1hour"),
        ("2 Horas", "2hour"),
        ("4 Horas", "4hour"),
        ("12 Horas", "12hour"),
        ("Diario", "1day"),
        ("Semanal", "1week"),
        ("Mensual", "1week") 
    ]
    
    results = []
    prog = st.progress(0)
    
    for i, (label, api_code) in enumerate(tfs_config):
        df = get_kucoin_data(selected_coin, api_code)
        
        # Proceso Especial para Mensual
        if label == "Mensual": df = resample_to_monthly(df)
            
        # Análisis Seguro
        res = analyze_dataframe(df)
        
        # Icono visual seguro
        ha_icon = "⚪"
        if res['HA'] == "Verde": ha_icon = "🟢"
        elif res['HA'] == "Rojo": ha_icon = "🔴"
        
        # Formato Histograma
        hist_fmt = f"{res['Hist']:.4f} {res['Hist_Dir']}" if res['Hist'] != 0 else "-"
        
        results.append({
            "Temporalidad": label,
            "Diagnóstico": res['Señal'],
            "Vela HA": ha_icon,
            "MACD Hist": hist_fmt,
            "Precio": res['Precio'] if res['Precio'] > 0 else "-"
        })
            
        prog.progress((i+1)/len(tfs_config))
        time.sleep(0.05) 
    
    prog.empty()
    
    df_res = pd.DataFrame(results)
    
    def color_row(val):
        if "ENTRADA LONG" in str(val): return "background-color: #0f3d0f; color: #4caf50; font-weight: bold"
        if "ENTRADA SHORT" in str(val): return "background-color: #3d0f0f; color: #f44336; font-weight: bold"
        if "SALIDA" in str(val): return "color: orange; font-weight: bold"
        return ""

    st.subheader(f"Matriz de Decisión: {selected_coin}")
    
    # Precio actual (intenta sacar del 15m o el primero valido)
    try:
        curr_p = df_res[df_res['Precio'] != "-"]['Precio'].iloc[0]
        st.metric(label=f"Precio {selected_coin}/USDT", value=f"${curr_p:,.4f}")
    except: pass
    
    st.dataframe(
        df_res.style.applymap(color_row, subset=['Diagnóstico']),
        column_config={
            "Precio": st.column_config.NumberColumn(format="$%.4f")
        },
        use_container_width=True,
        hide_index=True,
        height=400
    )
    
    st.info("""
    **Datos Nativos KuCoin:**
    *   ✅ 2 Horas, 4 Horas y 12 Horas son datos reales del exchange.
    *   ✅ Mensual se construye matemáticamente desde los datos semanales.
    *   ⚪ Si aparece en blanco, faltan datos históricos para esa temporalidad.
    """)
