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
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# MEMORIA
# ─────────────────────────────────────────────
if 'sniper_results' not in st.session_state:
    st.session_state['sniper_results'] = []

# ─────────────────────────────────────────────
# TEMPORALIDADES
# ─────────────────────────────────────────────
TIMEFRAMES = {
    '1m': '1m',
    '5m': '5m',
    '15m': '15m',
    '30m': '30m',
    '1H': '1h',
    '4H': '4h',
    '1D': '1d'
}

# ─────────────────────────────────────────────
# CONEXIÓN
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    return ccxt.kucoinfutures({'enableRateLimit': True, 'timeout': 30000})

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
    except:
        return []

# ─────────────────────────────────────────────
# HEIKIN ASHI
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

# ─────────────────────────────────────────────
# ANÁLISIS POR TF (EXTENDIDO)
# ─────────────────────────────────────────────
def analyze_ticker_tf(symbol, tf_code, exchange, current_price):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=120)
        if not ohlcv or len(ohlcv) < 60:
            return None

        ohlcv[-1][4] = current_price

        df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','vol'])
        df['dt'] = pd.to_datetime(df['time'], unit='ms')

        macd = ta.macd(df['close'])
        df['MACD'] = macd['MACD_12_26_9']
        df['SIGNAL'] = macd['MACDs_12_26_9']
        df['HIST'] = macd['MACDh_12_26_9']

        df['RSI'] = ta.rsi(df['close'], length=14)
        df = calculate_heikin_ashi(df)

        position = "NEUTRO"
        last_date = df['dt'].iloc[-1]

        for i in range(1, len(df)):
            if position == "LONG" and df['HIST'].iloc[i] < df['HIST'].iloc[i-1]:
                position = "NEUTRO"
            elif position == "SHORT" and df['HIST'].iloc[i] > df['HIST'].iloc[i-1]:
                position = "NEUTRO"

            if position == "NEUTRO":
                if df['HA_Color'].iloc[i] == 1 and df['HIST'].iloc[i] > df['HIST'].iloc[i-1]:
                    position = "LONG"
                    last_date = df['dt'].iloc[i]
                elif df['HA_Color'].iloc[i] == -1 and df['HIST'].iloc[i] < df['HIST'].iloc[i-1]:
                    position = "SHORT"
                    last_date = df['dt'].iloc[i]

        rsi_val = round(df['RSI'].iloc[-1], 1)
        rsi_state = "RSI↑" if rsi_val > 55 else "RSI↓" if rsi_val < 45 else "RSI="

        hist_dir = "📈 Hist ↑" if df['HIST'].iloc[-1] > df['HIST'].iloc[-2] else "📉 Hist ↓"

        cross_dir, cross_time = "-", pd.NaT
        for i in range(len(df)-1, 0, -1):
            if df['MACD'].iloc[i-1] < df['SIGNAL'].iloc[i-1] and df['MACD'].iloc[i] > df['SIGNAL'].iloc[i]:
                cross_dir, cross_time = "🟢 Cruce ↑", df['dt'].iloc[i]
                break
            if df['MACD'].iloc[i-1] > df['SIGNAL'].iloc[i-1] and df['MACD'].iloc[i] < df['SIGNAL'].iloc[i]:
                cross_dir, cross_time = "🔴 Cruce ↓", df['dt'].iloc[i]
                break

        return position, last_date, rsi_state, rsi_val, hist_dir, cross_dir, cross_time

    except:
        return None

# ─────────────────────────────────────────────
# ESCANEO
# ─────────────────────────────────────────────
def scan_batch(targets):
    ex = get_exchange()
    results = []
    prog = st.progress(0)

    for idx, sym in enumerate(targets):
        prog.progress((idx+1)/len(targets))
        try:
            price = ex.fetch_ticker(sym)['last']
        except:
            continue

        row = {'Activo': sym.replace(':USDT','').replace('/USDT','')}

        for label, tf in TIMEFRAMES.items():
            res = analyze_ticker_tf(sym, tf, ex, price)
            if res:
                state, date, rsi_state, rsi_val, hist, cross, ctime = res
                row[f"{label}_state"] = state
                row[f"{label}_rsi"] = rsi_val
                row[f"{label}_rsi_state"] = rsi_state
                row[f"{label}_datetime"] = date - pd.Timedelta(hours=3)
                row[f"{label}_hist"] = hist
                row[f"{label}_macd_cross"] = cross
                row[f"{label}_macd_time"] = ctime - pd.Timedelta(hours=3) if pd.notna(ctime) else pd.NaT
            else:
                for k in ["state","rsi","rsi_state","datetime","hist","macd_cross","macd_time"]:
                    row[f"{label}_{k}"] = "-"

        results.append(row)
        time.sleep(0.05)

    prog.empty()
    return results

# ─────────────────────────────────────────────
# RECOMENDACIÓN MACD
# ─────────────────────────────────────────────
def macd_bias(row):
    bull = sum(row.get(f"{tf}_hist")=="📈 Hist ↑" or row.get(f"{tf}_macd_cross")=="🟢 Cruce ↑" for tf in TIMEFRAMES)
    bear = sum(row.get(f"{tf}_macd_cross")=="🔴 Cruce ↓" for tf in TIMEFRAMES)
    if bull >= 8: return "🟢 MACD ALCISTA"
    if bear >= 8: return "🔴 MACD BAJISTA"
    return "⚖️ MACD MIXTO"

# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
st.title("🎯 SystemaTrader: MNQ Sniper Matrix V5")

with st.sidebar:
    symbols = get_active_pairs()
    size = st.selectbox("Lote", [10,20,30,50], 1)
    batch = symbols[:size]

    if st.button("🚀 Escanear"):
        st.session_state['sniper_results'].extend(scan_batch(batch))

    if st.button("🧹 Limpiar"):
        st.session_state['sniper_results'] = []
        st.rerun()

# ─────────────────────────────────────────────
# TABLA FINAL
# ─────────────────────────────────────────────
if st.session_state['sniper_results']:
    df = pd.DataFrame(st.session_state['sniper_results'])

    for tf in TIMEFRAMES:
        df[f"{tf} Hist"] = df[f"{tf}_hist"]
        df[f"{tf} MACD Cruce"] = df[f"{tf}_macd_cross"] + " | " + df[f"{tf}_macd_time"].astype(str)

    df["MACD Bias"] = df.apply(macd_bias, axis=1)

    cols = ["Activo","MACD Bias"]
    for tf in TIMEFRAMES:
        cols += [f"{tf} Hist", f"{tf} MACD Cruce"]

    st.data_editor(df[cols], use_container_width=True, height=800, disabled=True)
else:
    st.info("Escaneá un lote para ver resultados.")
