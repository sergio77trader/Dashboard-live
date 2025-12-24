import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
import plotly.graph_objects as go

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="RSI Matrix Pro: Ranked")

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

# --- FUNCIÓN DE RANKING (VOLUMEN 24H) ---
@st.cache_data(ttl=3600)
def get_ranked_symbols():
    """
    Descarga todos los pares de KuCoin y los ordena por Volumen en USDT (Importancia).
    """
    url = "https://api.kucoin.com/api/v1/market/allTickers"
    try:
        r = requests.get(url, timeout=10).json()
        if r['code'] == '200000':
            data = r['data']['ticker']
            df = pd.DataFrame(data)
            
            # 1. Filtrar solo pares USDT
            df = df[df['symbol'].str.endswith('-USDT')]
            
            # 2. Convertir volumen a float (volValue es el volumen en dinero)
            df['volValue'] = df['volValue'].astype(float)
            
            # 3. Ordenar de Mayor a Menor Volumen
            df = df.sort_values(by='volValue', ascending=False)
            
            # 4. Limpiar nombres (BTC-USDT -> BTC)
            df['clean_symbol'] = df['symbol'].str.replace('-USDT', '')
            
            # Retornar lista ordenada y diccionario de volumen para mostrar
            sorted_list = df['clean_symbol'].tolist()
            vol_map = df.set_index('clean_symbol')['volValue'].to_dict()
            
            return sorted_list, vol_map
            
    except: 
        # Fallback manual si falla la API
        return ['BTC','ETH','SOL','BNB','XRP','ADA','DOGE','SHIB'], {}

# --- CARGAR MERCADO AL INICIO ---
ALL_COINS, VOL_MAP = get_ranked_symbols()

# --- FUNCIONES DE DATOS (KUCOIN) ---

def get_kucoin_data(symbol, k_interval, limit=100):
    url = "https://api.kucoin.com/api/v1/market/candles"
    target = f"{symbol}-USDT"
    
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
    if df.empty: return 0, 0
    
    ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    
    ha_open_list = [df['Open'].iloc[0]]
    ha_close_list = [ha_close.iloc[0]]
    
    for i in range(1, len(df)):
        ho = (ha_open_list[-1] + ha_close_list[-1]) / 2
        hc = (df['Open'].iloc[i] + df['High'].iloc[i] + df['Low'].iloc[i] + df['Close'].iloc[i]) / 4
        ha_open_list.append(ho)
        ha_close_list.append(hc)
        
    last_c = ha_close_list[-1]
    last_o = ha_open_list[-1]
    
    color = 1 if last_c > last_o else -1
    return color, last_c

# --- MOTOR DE ANÁLISIS ---

def analyze_asset(coin):
    # 1. Diario
    df_d = get_kucoin_data(coin, "1day", 100)
    if df_d.empty: return None
    
    ha_color, ha_price = calculate_heikin_ashi_daily(df_d)
    rsi_d = calculate_rsi(df_d)
    
    # 2. Semanal
    df_w = get_kucoin_data(coin, "1week", 50)
    rsi_w = calculate_rsi(df_w)
    
    # 3. Intradía
    rsi_12h = calculate_rsi(get_kucoin_data(coin, "12hour", 50))
    rsi_8h  = calculate_rsi(get_kucoin_data(coin, "8hour", 50))
    rsi_4h  = calculate_rsi(get_kucoin_data(coin, "4hour", 50))
    rsi_2h  = calculate_rsi(get_kucoin_data(coin, "2hour", 50))
    
    # Lógica
    all_rsis = [rsi_w, rsi_d, rsi_12h, rsi_8h, rsi_4h, rsi_2h]
    all_rsis = [r for r in all_rsis if not np.isnan(r)]
    
    if not all_rsis: return None

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
        
    # Obtener volumen del mapa global
    vol_24h = VOL_MAP.get(coin, 0)

    return {
        "Ticker": coin,
        "Ranking": 0, # Se asignará después
        "Volumen 24h": vol_24h,
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
st.title("⚡ RSI Matrix Pro: Ranked by Volume")
st.markdown("**Orden:** Las criptomonedas se presentan por **Volumen de Negociación ($)**. Lote 1 = Las más importantes.")

# Inicializar memoria
if 'rsi_full_results' not in st.session_state:
    st.session_state['rsi_full_results'] = []

# Sidebar
with st.sidebar:
    st.header("Configuración")
    st.success(f"Mercado KuCoin: {len(ALL_COINS)} Activos Clasificados")
    
    batch_size = st.slider("Tamaño de Lote", 20, 100, 50)
    
    # Crear lotes basados en la lista YA ORDENADA
    batches = [ALL_COINS[i:i + batch_size] for i in range(0, len(ALL_COINS), batch_size)]
    
    # Etiquetas inteligentes para los lotes
    batch_labels = []
    for i, b in enumerate(batches):
        first = b[0]
        last = b[-1]
        label = f"Lote {i+1} (Ranks: {i*batch_size + 1}-{(i+1)*batch_size})"
        batch_labels.append(label)
    
    sel_batch_idx = st.selectbox("Seleccionar Lote (Por Ranking):", range(len(batches)), format_func=lambda x: batch_labels[x])
    
    col1, col2 = st.columns(2)
    scan_btn = col1.button("🔄 ESCANEAR", type="primary")
    clear_btn = col2.button("🗑️ Limpiar")

if scan_btn:
    targets = batches[sel_batch_idx]
    st.toast(f"Analizando {len(targets)} criptos del Top Ranking...", icon="🚀")
    
    # Filtrar duplicados
    existing = [x['Ticker'] for x in st.session_state['rsi_full_results']]
    to_run = [t for t in targets if t not in existing]
    
    new_results = []
    prog = st.progress(0)
    
    for i, coin in enumerate(to_run):
        try:
            res = analyze_asset(coin)
            if res: 
                # Asignar ranking absoluto
                res['Ranking'] = ALL_COINS.index(coin) + 1
                new_results.append(res)
        except: pass
        
        prog.progress((i+1)/len(to_run))
        time.sleep(0.05) 
        
    st.session_state['rsi_full_results'].extend(new_results)
    prog.empty()
    st.success(f"Agregados {len(new_results)} activos.")

if clear_btn:
    st.session_state['rsi_full_results'] = []
    st.rerun()

# --- TABLA DE RESULTADOS ---
if st.session_state['rsi_full_results']:
    df = pd.DataFrame(st.session_state['rsi_full_results'])
    
    # Ordenar por Ranking de Volumen (Default) o por Prioridad de Señal
    sort_mode = st.radio("Ordenar por:", ["🏆 Importancia (Volumen)", "🔥 Oportunidad (Señal)"], horizontal=True)
    
    if sort_mode == "🏆 Importancia (Volumen)":
        df = df.sort_values(by='Ranking', ascending=True)
    else:
        priority = {"🟢 LONG": 4, "🔴 SHORT": 4, "⚠️ Techo (Esperar HA Rojo)": 2, "⚠️ Piso (Esperar HA Verde)": 2, "NEUTRO": 1}
        df['Prio'] = df['Señal'].map(priority).fillna(1)
        df = df.sort_values(by='Prio', ascending=False)
    
    # Estilos
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
        df.style.map(style_rsi, subset=['RSI_W', 'RSI_D', 'RSI_12H', 'RSI_8H', 'RSI_4H', 'RSI_2H'])
                .map(style_signal, subset=['Señal']),
        column_config={
            "Ranking": st.column_config.NumberColumn("#", width="small"),
            "Ticker": "Activo",
            "Volumen 24h": st.column_config.NumberColumn("Volumen ($)", format="$%.0f"),
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
    st.info("👈 Selecciona el Lote 1 (Top Coins) para empezar.")
