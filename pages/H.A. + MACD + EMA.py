import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SystemaTrader: MACD Deep Dive")
st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 14px; }
    .stProgress > div > div > div > div { background-color: #2962FF; }
</style>
""", unsafe_allow_html=True)

if 'deep_results' not in st.session_state:
    st.session_state['deep_results'] = []

# Seleccionamos TFs clave para no saturar la pantalla con 50 columnas
TIMEFRAMES = {
    '15m': '15m',
    '1H': '1h',
    '4H': '4h',
    '1D': '1d'
}

# ─────────────────────────────────────────────
# CONEXIÓN
# ─────────────────────────────────────────────
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

# ─────────────────────────────────────────────
# CÁLCULOS MATEMÁTICOS
# ─────────────────────────────────────────────
def calculate_heikin_ashi(df):
    df = df.copy()
    df['HA_Close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    ha_open = [df['open'].iloc[0]]
    for i in range(1, len(df)):
        ha_open.append((ha_open[-1] + df['HA_Close'].iloc[i-1]) / 2)
    df['HA_Open'] = ha_open
    df['HA_Color'] = np.where(df['HA_Close'] > df['HA_Open'], 1, -1)
    return df

def analyze_ticker_tf(symbol, tf_code, exchange, current_price):
    try:
        # Bajamos suficiente historial para encontrar cruces pasados
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=200)
        if not ohlcv or len(ohlcv) < 50: return None

        # Actualizar última vela con precio real
        ohlcv[-1][4] = current_price

        df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','vol'])
        df['dt'] = pd.to_datetime(df['time'], unit='ms')

        # 1. MACD
        macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
        df['MACD_Line'] = macd['MACD_12_26_9']
        df['Signal_Line'] = macd['MACDs_12_26_9']
        df['Hist'] = macd['MACDh_12_26_9']

        # 2. Heikin Ashi
        df = calculate_heikin_ashi(df)

        # 3. Lógica de Estado (Position)
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

        # 4. Lógica Profunda MACD
        curr_hist = df['Hist'].iloc[-1]
        prev_hist = df['Hist'].iloc[-2]
        
        # Momentum: ¿Crece o Decrece?
        mom_type = "Fortaleciendo" if abs(curr_hist) > abs(prev_hist) else "Debilitando"
        if curr_hist > 0 and curr_hist > prev_hist: mom_icon = "🟢 Crece"
        elif curr_hist > 0 and curr_hist < prev_hist: mom_icon = "🟡 Cae"
        elif curr_hist < 0 and curr_hist < prev_hist: mom_icon = "🔴 Crece" # Crece a la baja
        else: mom_icon = "🟠 Cae" # Cae la baja (Rebote)

        # Cruce de Líneas (Cross)
        # Detectamos cuándo fue la última vez que MACD cruzó Signal
        df['Cross'] = np.where(df['MACD_Line'] > df['Signal_Line'], 1, -1)
        df['Crossover'] = df['Cross'].diff() # != 0 es un cruce
        
        # Buscar último cruce
        last_cross_idx = df[df['Crossover'] != 0].index[-1]
        last_cross_val = df['Cross'].iloc[last_cross_idx]
        last_cross_time = df['dt'].iloc[last_cross_idx]
        
        cross_state = "BULLISH 🐂" if df['MACD_Line'].iloc[-1] > df['Signal_Line'].iloc[-1] else "BEARISH 🐻"
        cross_time_str = (last_cross_time - pd.Timedelta(hours=3)).strftime('%d/%m %H:%M')

        return {
            "pos": position,
            "mom": mom_icon,
            "cross_st": cross_state,
            "cross_tm": cross_time_str
        }

    except: return None

# ─────────────────────────────────────────────
# MOTOR DE RECOMENDACIÓN (IA SIMULADA)
# ─────────────────────────────────────────────
def get_recommendation(row):
    # Puntos
    bull_score = 0
    bear_score = 0
    
    # Pesos
    weights = {'15m': 1, '1H': 2, '4H': 3, '1D': 4}
    
    for tf, w in weights.items():
        # Leer estado del cruce
        cross = row.get(f"{tf} Cruce", "")
        mom = row.get(f"{tf} Mom", "")
        
        if "BULLISH" in cross: 
            bull_score += w
            if "🟢" in mom: bull_score += 0.5 # Bonus por momentum
            
        if "BEARISH" in cross: 
            bear_score += w
            if "🔴" in mom: bear_score += 0.5
            
    # Diagnóstico
    total = bull_score + bear_score
    if total == 0: return "⚖️ NEUTRO"
    
    bull_pct = bull_score / total
    
    if bull_pct > 0.85: return "🚀 COMPRA FUERTE"
    if bull_pct > 0.60: return "🟢 ALCISTA"
    if bull_pct < 0.15: return "🩸 VENTA FUERTE"
    if bull_pct < 0.40: return "🔴 BAJISTA"
    
    # Casos especiales
    if "BULLISH" in row.get("1D Cruce", "") and "BEARISH" in row.get("15m Cruce", ""):
        return "📉 DIP (Compra en retroceso)"
        
    if "BEARISH" in row.get("1D Cruce", "") and "BULLISH" in row.get("15m Cruce", ""):
        return "⚠️ REBOTE (Venta en subida)"

    return "⚖️ RANGO / INDECISIÓN"

# ─────────────────────────────────────────────
# BUCLE DE ESCANEO
# ─────────────────────────────────────────────
def scan_batch(targets):
    ex = get_exchange()
    results = []
    prog = st.progress(0, text="Iniciando Deep Dive...")
    
    for idx, sym in enumerate(targets):
        clean = sym.replace(':USDT','').replace('/USDT','')
        prog.progress((idx+1)/len(targets), text=f"Analizando MACD: {clean}")
        
        try:
            price = ex.fetch_ticker(sym)['last']
        except: price = 0
            
        row = {'Activo': clean, 'Precio': price}
        
        for label, tf in TIMEFRAMES.items():
            res = analyze_ticker_tf(sym, tf, ex, price)
            if res:
                # Guardamos columnas planas para la tabla
                row[f"{label} Est"] = res['pos']
                row[f"{label} Mom"] = res['mom']
                row[f"{label} Cruce"] = res['cross_st']
                row[f"{label} Fecha"] = res['cross_tm']
            else:
                row[f"{label} Est"] = "-"
                row[f"{label} Mom"] = "-"
                row[f"{label} Cruce"] = "-"
                row[f"{label} Fecha"] = "-"

        # Recomendación final
        row['OBSERVACIÓN IA'] = get_recommendation(row)
        results.append(row)
        time.sleep(0.1)
        
    prog.empty()
    return results

# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
st.title("🔬 SystemaTrader: MACD Deep Dive")
st.caption("Análisis Forense de Momentum y Cruces en Múltiples Temporalidades")

with st.sidebar:
    st.header("Configuración")
    all_symbols = get_active_pairs()
    BATCH_SIZE = st.selectbox("Tamaño Lote", [10, 20, 30], index=0)
    batches = [all_symbols[i:i+BATCH_SIZE] for i in range(0, len(all_symbols), BATCH_SIZE)]
    sel = st.selectbox("Lote", range(len(batches)))
    
    accumulate = st.checkbox("Acumular", value=True)
    
    if st.button("🚀 EJECUTAR ESCANEO"):
        new = scan_batch(batches[sel])
        if accumulate:
            st.session_state['deep_results'].extend(new)
        else:
            st.session_state['deep_results'] = new
            
    if st.button("Limpiar"):
        st.session_state['deep_results'] = []
        st.rerun()

# ─────────────────────────────────────────────
# TABLA FINAL
# ─────────────────────────────────────────────
if st.session_state['deep_results']:
    df = pd.DataFrame(st.session_state['deep_results'])
    
    # 1. Columna de Recomendación primero
    cols = ['Activo', 'OBSERVACIÓN IA', 'Precio']
    # 2. Agregar columnas dinámicas de TFs
    for tf in TIMEFRAMES:
        cols.extend([f"{tf} Est", f"{tf} Mom", f"{tf} Cruce", f"{tf} Fecha"])
    
    # Verificar existencia
    final_cols = [c for c in cols if c in df.columns]
    
    st.dataframe(
        df[final_cols],
        column_config={
            "Activo": st.column_config.TextColumn("Crypto", pinned=True),
            "OBSERVACIÓN IA": st.column_config.TextColumn("Diagnóstico", width="medium"),
            "Precio": st.column_config.NumberColumn(format="$%.4f"),
            # Configuración repetitiva para cada TF para que se vea lindo
            "15m Est": st.column_config.TextColumn("15m HA"),
            "15m Mom": st.column_config.TextColumn("15m Hist"),
            "15m Cruce": st.column_config.TextColumn("15m Cross"),
            "15m Fecha": st.column_config.TextColumn("15m Time"),
            # (Streamlit aplica config por defecto si no especifico todos, pero funciona igual)
        },
        use_container_width=True,
        height=800
    )
else:
    st.info("Selecciona un lote para el análisis profundo.")
