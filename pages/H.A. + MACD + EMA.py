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
st.set_page_config(layout="wide", page_title="SystemaTrader: MNQ Sniper Matrix")
st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 14px; }
    .stProgress > div > div > div > div { background-color: #2962FF; }
    .stDataFrame { font-size: 0.8rem; }
</style>
""", unsafe_allow_html=True)

if 'final_results_v12' not in st.session_state:
    st.session_state['final_results_v12'] = []

TIMEFRAMES = {
    '1m': '1m', '5m': '5m', '15m': '15m',
    '30m': '30m', '1H': '1h', '4H': '4h', '1D': '1d'
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
# CÁLCULOS
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
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=200)
        if not ohlcv or len(ohlcv) < 50: return None

        ohlcv[-1][4] = current_price

        df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','vol'])
        df['dt'] = pd.to_datetime(df['time'], unit='ms')

        # MACD
        macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
        df['MACD'] = macd['MACD_12_26_9']
        df['Signal'] = macd['MACDs_12_26_9']
        df['Hist'] = macd['MACDh_12_26_9']
        df['RSI'] = ta.rsi(df['close'], length=14)
        
        df = calculate_heikin_ashi(df)

        # 1. ESTADO ORIGINAL (HA)
        position = "NEUTRO"
        last_date = df['dt'].iloc[-1]

        for i in range(1, len(df)):
            hist = df['Hist'].iloc[i]
            prev_hist = df['Hist'].iloc[i-1]
            ha_color = df['HA_Color'].iloc[i]
            date = df['dt'].iloc[i]

            if position == "LONG" and hist < prev_hist: position = "NEUTRO"
            elif position == "SHORT" and hist > prev_hist: position = "NEUTRO"
            if position == "NEUTRO":
                if ha_color == 1 and hist > prev_hist:
                    position = "LONG"
                    last_date = date
                elif ha_color == -1 and hist < prev_hist:
                    position = "SHORT"
                    last_date = date

        # RSI Estado
        rsi_val = round(df['RSI'].iloc[-1], 1)
        rsi_state = "RSI↑" if rsi_val > 55 else ("RSI↓" if rsi_val < 45 else "RSI=")

        # 2. NUEVO: CRUCE MACD
        df['Cross'] = np.where(df['MACD'] > df['Signal'], 1, -1)
        df['Change'] = df['Cross'].diff() # != 0 es cruce
        
        cross_rows = df[df['Change'] != 0]
        if not cross_rows.empty:
            last_cross = cross_rows.iloc[-1]
            c_type = "ALCISTA" if last_cross['Cross'] == 1 else "BAJISTA"
            c_dt = last_cross['dt'] - pd.Timedelta(hours=3) # Hora Arg
            c_time = c_dt.strftime('%H:%M')
        else:
            c_type = "-"
            c_time = "-"

        return {
            "state": position,
            "date": last_date,
            "rsi_st": rsi_state,
            "rsi_val": rsi_val,
            # Nuevos datos (Solo estos 2)
            "cross_type": c_type,
            "cross_time": c_time
        }

    except: return None

# ─────────────────────────────────────────────
# RECOMENDACIONES
# ─────────────────────────────────────────────
def get_recommendations(row):
    # 1. Tu Estrategia Original
    longs = sum("LONG" in str(row.get(f"{tf} HA-MACD",'')) for tf in TIMEFRAMES)
    shorts = sum("SHORT" in str(row.get(f"{tf} HA-MACD",'')) for tf in TIMEFRAMES)

    # 2. Recomendación MACD (Basada en los cruces nuevos)
    macd_bull = 0
    macd_bear = 0
    for tf in TIMEFRAMES:
        cross = str(row.get(f"{tf} CRUCE", ""))
        if "ALCISTA" in cross: macd_bull += 1
        if "BAJISTA" in cross: macd_bear += 1
        
    strat_macd = "Neutro"
    if macd_bull >= 4: strat_macd = "🚀 Impulso Alcista"
    elif macd_bear >= 4: strat_macd = "📉 Impulso Bajista"
    
    # 3. GLOBAL
    strat_global = "ESPERAR"
    if longs >= 5 and "Alcista" in strat_macd: strat_global = "💎 ALL IN LONG"
    elif shorts >= 5 and "Bajista" in strat_macd: strat_global = "☠️ ALL IN SHORT"
    elif longs >= 4: strat_global = "🟢 LONG"
    elif shorts >= 4: strat_global = "🔴 SHORT"
    
    return strat_macd, strat_global

# ─────────────────────────────────────────────
# ESCANEO
# ─────────────────────────────────────────────
def scan_batch(targets):
    ex = get_exchange()
    results = []
    prog = st.progress(0, text="Escaneando...")
    
    for idx, sym in enumerate(targets):
        clean = sym.replace(':USDT','').replace('/USDT','')
        prog.progress((idx+1)/len(targets), text=f"{clean}")
        
        try: px = ex.fetch_ticker(sym)['last']
        except: px = 0
        
        row = {'Activo': clean}
        
        for label, code in TIMEFRAMES.items():
            res = analyze_ticker_tf(sym, label, code, ex, px)
            if res:
                # 1. COLUMNAS ORIGINALES
                state, date, rsi_st, rsi_v = res['state'], res['date'], res['rsi_st'], res['rsi_val']
                icon = "🟢" if state=="LONG" else "🔴" if state=="SHORT" else "⚪"
                hora = (date - pd.Timedelta(hours=3)).strftime('%H:%M')
                
                row[f"{label} HA-MACD"] = f"{icon} {state} | {rsi_st} ({rsi_v})"
                row[f"{label} ALERTA"] = hora
                
                # 2. COLUMNAS NUEVAS (SOLO ESTAS DOS)
                icon_c = "🐂" if "ALCISTA" in res['cross_type'] else "🐻"
                row[f"{label} CRUCE"] = f"{icon_c} {res['cross_type']}"
                row[f"{label} HORA CRUCE"] = res['cross_time']
            else:
                row[f"{label} HA-MACD"] = "-"
                row[f"{label} ALERTA"] = "-"
                row[f"{label} CRUCE"] = "-"
                row[f"{label} HORA CRUCE"] = "-"
        
        s_macd, s_glob = get_recommendations(row)
        row['RECOM. MACD'] = s_macd
        row['VEREDICTO'] = s_glob
        
        results.append(row)
        time.sleep(0.1)
    
    prog.empty()
    return results

# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
st.title("🎯 SystemaTrader: MNQ Matrix V12 (Clean)")

with st.sidebar:
    st.header("Configuración")
    all_symbols = get_active_pairs()
    BATCH = st.selectbox("Lote", [10, 20, 30, 50], index=0)
    batches = [all_symbols[i:i+BATCH] for i in range(0, len(all_symbols), BATCH)]
    sel = st.selectbox("Seleccionar:", range(len(batches)), format_func=lambda x: f"Lote {x+1}")
    acc = st.checkbox("Acumular", value=True)
    
    if st.button("🚀 ESCANEAR"):
        new = scan_batch(batches[sel])
        if acc: st.session_state['final_results_v12'].extend(new)
        else: st.session_state['final_results_v12'] = new
        
    if st.button("Limpiar"):
        st.session_state['final_results_v12'] = []
        st.rerun()

# ─────────────────────────────────────────────
# TABLA
# ─────────────────────────────────────────────
if st.session_state['final_results_v12']:
    df = pd.DataFrame(st.session_state['final_results_v12'])
    
    # Ordenar Columnas
    cols = ['Activo', 'VEREDICTO', 'RECOM. MACD']
    for tf in ["1m", "5m", "15m", "30m", "1H", "4H", "1D"]:
        cols.append(f"{tf} HA-MACD")
        cols.append(f"{tf} ALERTA")
        cols.append(f"{tf} CRUCE")
        cols.append(f"{tf} HORA CRUCE")
        
    final_cols = [c for c in cols if c in df.columns]
    
    st.dataframe(df[final_cols], use_container_width=True, height=800)
else:
    st.info("👈 Escanea un lote.")
