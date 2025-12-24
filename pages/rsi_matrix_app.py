import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
import plotly.graph_objects as go

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="RSI Matrix Pro")

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

# --- LISTA DE MONEDAS A ANALIZAR ---
RAW_COINS = sorted([
    'BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'AVAX', 'DOGE', 'SHIB', 'DOT',
    'LINK', 'TRX', 'MATIC', 'LTC', 'BCH', 'NEAR', 'UNI', 'ICP', 'FIL', 'APT',
    'INJ', 'LDO', 'OP', 'ARB', 'TIA', 'SEI', 'SUI', 'RNDR', 'FET', 'WLD',
    'PEPE', 'BONK', 'WIF', 'FLOKI', 'ORDI', 'SATS', 'GALA', 'SAND', 'MANA',
    'AXS', 'AAVE', 'SNX', 'MKR', 'CRV', 'DYDX', 'JUP', 'PYTH', 'ENA', 'RUNE',
    'FTM', 'ATOM', 'ALGO', 'VET', 'EGLD', 'STX', 'IMX', 'KAS', 'TAO', 'OM', 'JASMY'
])

# --- FUNCIONES DE DATOS (SOLO KUCOIN) ---

def get_kucoin_data(symbol, k_interval, limit=100):
    """
    Intervalos Kucoin: 1min, 3min, 15min, 30min, 1hour, 2hour, 4hour, 6hour, 8hour, 12hour, 1day, 1week
    """
    url = "https://api.kucoin.com/api/v1/market/candles"
    target = f"{symbol}-USDT"
    
    params = {'symbol': target, 'type': k_interval, 'limit': limit}
    try:
        r = requests.get(url, params=params, timeout=5).json()
        if r['code'] == '200000':
            data = r['data']
            # Kucoin devuelve [time, open, close, high, low, vol, turn]
            df = pd.DataFrame(data, columns=['Time','Open','Close','High','Low','Vol','Turn'])
            df = df.astype(float)
            df['Time'] = pd.to_datetime(df['Time'], unit='s')
            # Ordenar por fecha ascendente para cálculos
            df = df.sort_values('Time', ascending=True).reset_index(drop=True)
            return df
    except: pass
    return pd.DataFrame()

# --- CÁLCULOS MATEMÁTICOS ---

def calculate_rsi(df, period=14):
    if len(df) < period: return 50.0
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

def calculate_heikin_ashi_daily(df):
    """Calcula el color de la vela HA Diaria actual"""
    if df.empty: return 0, 0
    
    # Cálculo iterativo básico para la última vela
    # Aproximación rápida para escáner
    ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    
    # HA Open es el promedio del Open y Close de la vela ANTERIOR (real)
    # Como no tenemos HA anterior calculado, usamos una aproximación con precios normales anteriores
    # Para mayor precisión en HA, se requiere un loop completo desde el inicio del DF
    
    df_ha = df.copy()
    ha_open_list = [df['Open'].iloc[0]]
    ha_close_list = [ha_close.iloc[0]]
    
    for i in range(1, len(df)):
        ho = (ha_open_list[-1] + ha_close_list[-1]) / 2
        hc = (df['Open'].iloc[i] + df['High'].iloc[i] + df['Low'].iloc[i] + df['Close'].iloc[i]) / 4
        ha_open_list.append(ho)
        ha_close_list.append(hc)
        
    last_c = ha_close_list[-1]
    last_o = ha_open_list[-1]
    
    # Color: 1 Verde, -1 Rojo
    color = 1 if last_c > last_o else -1
    return color, last_c

# --- MOTOR DE ANÁLISIS ---

def analyze_asset(coin):
    # 1. Obtener Diario (Base para HA y RSI D)
    df_d = get_kucoin_data(coin, "1day", 100)
    if df_d.empty: return None # Si Kucoin no tiene el dato, saltamos
    
    ha_color, ha_price = calculate_heikin_ashi_daily(df_d)
    rsi_d = calculate_rsi(df_d)
    
    # 2. Obtener Semanal
    df_w = get_kucoin_data(coin, "1week", 50)
    rsi_w = calculate_rsi(df_w)
    
    # 3. Obtener Intradía (Nativos de Kucoin)
    rsi_12h = calculate_rsi(get_kucoin_data(coin, "12hour", 50))
    rsi_8h  = calculate_rsi(get_kucoin_data(coin, "8hour", 50))
    rsi_4h  = calculate_rsi(get_kucoin_data(coin, "4hour", 50))
    rsi_2h  = calculate_rsi(get_kucoin_data(coin, "2hour", 50))
    
    # --- LÓGICA DE ESTRATEGIA ---
    all_rsis = [rsi_w, rsi_d, rsi_12h, rsi_8h, rsi_4h, rsi_2h]
    
    is_overbought = any(r > 70 for r in all_rsis)
    is_oversold = any(r < 30 for r in all_rsis)
    
    signal = "NEUTRO"
    score = 0
    
    # VENTA: Algún RSI > 70 + Vela Diaria ROJA (-1)
    if is_overbought and ha_color == -1:
        signal = "🔴 SHORT"
        score = -1
        
    # COMPRA: Algún RSI < 30 + Vela Diaria VERDE (1)
    elif is_oversold and ha_color == 1:
        signal = "🟢 LONG"
        score = 1
        
    # ALERTAS (Divergencia entre RSI Extremo y Vela)
    elif is_overbought and ha_color == 1:
        signal = "⚠️ Techo (Esperar HA Rojo)"
    elif is_oversold and ha_color == -1:
        signal = "⚠️ Piso (Esperar HA Verde)"

    return {
        "Ticker": coin,
        "Precio": df_d['Close'].iloc[-1],
        "Señal": signal,
        "Score": score,
        "HA_D": ha_color,
        "RSI_W": rsi_w,
        "RSI_D": rsi_d,
        "RSI_12H": rsi_12h,
        "RSI_8H": rsi_8h,
        "RSI_4H": rsi_4h,
        "RSI_2H": rsi_2h
    }

# --- INTERFAZ ---
st.title("⚡ RSI Matrix + Heikin Ashi (KuCoin Direct)")
st.markdown("**Estrategia:** Detectar agotamiento en RSI (Múltiples TF) y disparar cuando la vela diaria Heikin Ashi confirme el giro.")

# Sidebar
with st.sidebar:
    st.header("Configuración")
    st.info(f"Lista de Monedas: {len(RAW_COINS)}")
    
    if st.button("🔄 ESCANEAR MERCADO", type="primary"):
        # Usamos la lista directa sin preguntar a Binance
        valid_coins = RAW_COINS 
        
        st.toast(f"Analizando {len(valid_coins)} pares en KuCoin...", icon="🔎")
        
        results = []
        prog = st.progress(0)
        
        for i, coin in enumerate(valid_coins):
            res = analyze_asset(coin)
            if res: results.append(res)
            prog.progress((i+1)/len(valid_coins))
            # Pequeña pausa para no saturar Kucoin (es generosa, pero por seguridad)
            time.sleep(0.05) 
            
        st.session_state['rsi_results_v2'] = results
        prog.empty()
        st.success("Escaneo Finalizado")

# --- RESULTADOS ---
if 'rsi_results_v2' in st.session_state and st.session_state['rsi_results_v2']:
    df = pd.DataFrame(st.session_state['rsi_results_v2'])
    
    # Ordenar por prioridad
    priority = {"🟢 LONG": 3, "🔴 SHORT": 3, "⚠️ Techo (Esperar HA Rojo)": 2, "⚠️ Piso (Esperar HA Verde)": 2, "NEUTRO": 1}
    df['Prioridad'] = df['Señal'].map(priority).fillna(1)
    df = df.sort_values(by='Prioridad', ascending=False)
    
    # Estilos
    def style_rsi(val):
        if val >= 70: return 'color: #ff4b4b; font-weight: bold;' # Rojo
        if val <= 30: return 'color: #00c853; font-weight: bold;' # Verde
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

    # Tabla
    st.dataframe(
        df.style.map(style_rsi, subset=['RSI_W', 'RSI_D', 'RSI_12H', 'RSI_8H', 'RSI_4H', 'RSI_2H'])
                .map(style_signal, subset=['Señal']),
        column_config={
            "Ticker": "Activo",
            "Precio": st.column_config.NumberColumn(format="$%.4f"),
            "HA_D": st.column_config.TextColumn("Vela D", help="1=Verde, -1=Roja"),
            "RSI_W": st.column_config.NumberColumn("Sem", format="%.0f"),
            "RSI_D": st.column_config.NumberColumn("Día", format="%.0f"),
            "RSI_12H": st.column_config.NumberColumn("12h", format="%.0f"),
            "RSI_8H": st.column_config.NumberColumn("8h", format="%.0f"),
            "RSI_4H": st.column_config.NumberColumn("4h", format="%.0f"),
            "RSI_2H": st.column_config.NumberColumn("2h", format="%.0f"),
        },
        use_container_width=True,
        hide_index=True,
        height=700
    )
    
else:
    st.info("👈 Pulsa el botón para escanear (Sin verificación de Binance).")
    
