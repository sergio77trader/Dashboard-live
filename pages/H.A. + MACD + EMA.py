import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SystemaTrader: MACD Full Data")
st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 14px; }
    .stProgress > div > div > div > div { background-color: #2962FF; }
</style>
""", unsafe_allow_html=True)

# --- MEMORIA ---
if 'full_results' not in st.session_state:
    st.session_state['full_results'] = []

# --- TEMPORALIDADES A ANALIZAR ---
TIMEFRAMES = {
    '15m': '15m',
    '1H': '1h',
    '4H': '4h',
    'Diario': '1d',
    'Semanal': '1w'
}

# --- CONEXIÓN KUCOIN ---
@st.cache_resource
def get_exchange():
    return ccxt.kucoinfutures({
        'enableRateLimit': True,
        'timeout': 30000
    })

@st.cache_data(ttl=3600)
def get_active_pairs():
    try:
        ex = get_exchange()
        tickers = ex.fetch_tickers()
        valid = []
        for s in tickers:
            if '/USDT:USDT' in s and tickers[s].get('quoteVolume'):
                valid.append({'symbol': s, 'vol': tickers[s]['quoteVolume']})
        return pd.DataFrame(valid).sort_values('vol', ascending=False)['symbol'].tolist()
    except: return []

# --- LÓGICA DE CÁLCULO ---
def calculate_heikin_ashi(df):
    df_ha = df.copy()
    df_ha['HA_Close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    ha_open = [df['open'].iloc[0]]
    for i in range(1, len(df)):
        ha_open.append((ha_open[-1] + df_ha['HA_Close'].iloc[i-1]) / 2)
    df_ha['HA_Open'] = ha_open
    df_ha['HA_Color'] = np.where(df_ha['HA_Close'] > df_ha['HA_Open'], 1, -1)
    return df_ha

def analyze_tf_data(symbol, tf_label, tf_code, exchange):
    """Devuelve un diccionario con las 4 métricas para esa temporalidad"""
    try:
        # Bajamos 200 velas para detectar cruces viejos si hace falta
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=200)
        if not ohlcv or len(ohlcv) < 50: 
            return None
        
        df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
        df['dt'] = pd.to_datetime(df['time'], unit='ms')
        
        # 1. MACD
        macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
        df['MACD'] = macd['MACD_12_26_9']
        df['Signal'] = macd['MACDs_12_26_9']
        df['Hist'] = macd['MACDh_12_26_9']
        
        # 2. Heikin Ashi
        df = calculate_heikin_ashi(df)
        
        # 3. Estado HA (Tu estrategia)
        position = "NEUTRO"
        for i in range(1, len(df)):
            hist = df['Hist'].iloc[i]
            prev_hist = df['Hist'].iloc[i-1]
            ha_color = df['HA_Color'].iloc[i]
            
            if position == "LONG" and hist < prev_hist: position = "NEUTRO"
            elif position == "SHORT" and hist > prev_hist: position = "NEUTRO"
            
            if position == "NEUTRO":
                if ha_color == 1 and hist > prev_hist: position = "LONG"
                elif ha_color == -1 and hist < prev_hist: position = "SHORT"

        # 4. Histograma vs Anterior
        curr_hist = df['Hist'].iloc[-1]
        prev_hist = df['Hist'].iloc[-2]
        hist_trend = "↗️ Sube" if curr_hist > prev_hist else "↘️ Baja"
        
        # 5. Cruce MACD y Fecha
        df['Cross'] = np.where(df['MACD'] > df['Signal'], 1, -1)
        df['Change'] = df['Cross'].diff() # != 0 es cruce
        
        # Buscar último cruce
        cross_rows = df[df['Change'] != 0]
        if not cross_rows.empty:
            last_cross = cross_rows.iloc[-1]
            c_type = "🐂 GOLDEN" if last_cross['Cross'] == 1 else "🐻 DEATH"
            # Ajuste Hora Arg (-3)
            c_time = (last_cross['dt'] - pd.Timedelta(hours=3)).strftime('%d/%m %H:%M')
        else:
            c_type = "-"
            c_time = "-"

        # RETORNO DE DATOS PLANOS (Prefijos para columnas)
        return {
            f"{tf_label} Estado": position,
            f"{tf_label} Hist": hist_trend,
            f"{tf_label} Cruce": c_type,
            f"{tf_label} Fecha": c_time
        }
        
    except: return None

# --- RECOMENDACIÓN FINAL ---
def get_final_verdict(row):
    score = 0
    # Sumamos puntos por Estados LONG/SHORT en TFs importantes
    if row.get('Diario Estado') == 'LONG': score += 3
    if row.get('Diario Estado') == 'SHORT': score -= 3
    
    if row.get('4H Estado') == 'LONG': score += 2
    if row.get('4H Estado') == 'SHORT': score -= 2
    
    if row.get('1H Estado') == 'LONG': score += 1
    if row.get('1H Estado') == 'SHORT': score -= 1
    
    # Análisis de Histograma 1H (Gatillo)
    hist_1h = row.get('1H Hist', '')
    
    if score >= 4: return "🔥 COMPRA FUERTE"
    if score <= -4: return "🩸 VENTA FUERTE"
    if score > 0 and "Sube" in hist_1h: return "🟢 ALCISTA (Entrando)"
    if score < 0 and "Baja" in hist_1h: return "🔴 BAJISTA (Cayendo)"
    
    return "⚖️ ESPERAR"

# --- BUCLE ESCANEO ---
def scan_batch(targets):
    ex = get_exchange()
    results = []
    prog = st.progress(0, text="Escaneando detalles...")
    
    for idx, sym in enumerate(targets):
        clean_name = sym.replace(':USDT', '').replace('/USDT', '')
        prog.progress(idx/len(targets), text=f"Analizando {clean_name}...")
        
        # Datos base
        try:
            px = ex.fetch_ticker(sym)['last']
        except: px = 0
        
        row = {'Activo': clean_name, 'Precio': px}
        
        # Iterar TFs
        for label, code in TIMEFRAMES.items():
            data_tf = analyze_tf_data(sym, label, code, ex)
            if data_tf:
                row.update(data_tf) # Agrega las 4 columnas de este TF al dict
            else:
                # Rellenar con vacíos si falla
                row[f"{label} Estado"] = "-"
                row[f"{label} Hist"] = "-"
                row[f"{label} Cruce"] = "-"
                row[f"{label} Fecha"] = "-"
        
        # Recomendación
        row['RECOMENDACIÓN'] = get_final_verdict(row)
        results.append(row)
        time.sleep(0.1)
    
    prog.empty()
    return results

# --- INTERFAZ ---
st.title("🎛️ SystemaTrader: MACD Full Detail")

with st.sidebar:
    st.header("Configuración")
    all_symbols = get_active_pairs()
    
    if all_symbols:
        BATCH = st.selectbox("Lote:", [10, 20, 30], index=0)
        batches = [all_symbols[i:i+BATCH] for i in range(0, len(all_symbols), BATCH)]
        sel_batch = st.selectbox("Seleccionar:", range(len(batches)), format_func=lambda x: f"Lote {x+1}")
        
        accumulate = st.checkbox("Acumular", value=True)
        
        if st.button("🚀 ESCANEAR", type="primary"):
            target = batches[sel_batch]
            with st.spinner("Procesando columnas detalladas..."):
                new_data = scan_batch(target)
                if accumulate:
                    st.session_state['full_results'].extend(new_data)
                else:
                    st.session_state['full_results'] = new_data
    
    if st.button("Limpiar"):
        st.session_state['full_results'] = []
        st.rerun()

# --- TABLA ---
if st.session_state['full_results']:
    df = pd.DataFrame(st.session_state['full_results'])
    
    # Orden de columnas lógico
    base_cols = ["Activo", "RECOMENDACIÓN", "Precio"]
    tf_cols = []
    # Ordenamos: 15m -> 1H -> 4H -> Diario -> Semanal
    for tf in ["15m", "1H", "4H", "Diario", "Semanal"]:
        tf_cols.append(f"{tf} Estado")
        tf_cols.append(f"{tf} Hist")
        tf_cols.append(f"{tf} Cruce")
        tf_cols.append(f"{tf} Fecha")
        
    final_cols = base_cols + tf_cols
    # Filtrar solo las que existen en el DF (por si falló alguna carga)
    final_cols = [c for c in final_cols if c in df.columns]
    
    df_show = df[final_cols]
    
    # Estilos
    def color_reco(val):
        if "COMPRA" in str(val): return "background-color: #1b3a1b; color: #00ff00; font-weight: bold"
        if "VENTA" in str(val): return "background-color: #3a1b1b; color: #ff0000; font-weight: bold"
        return ""

    st.dataframe(
        df_show.style.map(color_reco, subset=['RECOMENDACIÓN']),
        use_container_width=True,
        height=800
    )
else:
    st.info("👈 Selecciona un lote. La tabla tendrá muchas columnas (scrollea a la derecha).")
