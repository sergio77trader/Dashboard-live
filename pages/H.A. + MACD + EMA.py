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
st.set_page_config(layout="wide", page_title="SystemaTrader: MNQ Sniper Matrix V5")
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
        return (
            pd.DataFrame(valid)
            .sort_values('vol', ascending=False)['symbol']
            .tolist()
        )
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
# ANÁLISIS POR TF (EXTENDIDO CON MACD)
# ─────────────────────────────────────────────
def analyze_ticker_tf(symbol, tf_code, exchange, current_price):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=150)
        if not ohlcv or len(ohlcv) < 60:
            return None

        ohlcv[-1][4] = current_price

        df = pd.DataFrame(
            ohlcv, columns=['time','open','high','low','close','vol']
        )
        df['dt'] = pd.to_datetime(df['time'], unit='ms')

        # RSI
        df['RSI'] = ta.rsi(df['close'], length=14)

        # MACD ROBUSTO
        macd_df = ta.macd(df['close'], fast=12, slow=26, signal=9)
        if macd_df is None or macd_df.isna().all().all():
            return None

        df = pd.concat([df, macd_df], axis=1)
        df.rename(columns={
            'MACD_12_26_9': 'MACD',
            'MACDs_12_26_9': 'SIGNAL',
            'MACDh_12_26_9': 'HIST'
        }, inplace=True)

        df = calculate_heikin_ashi(df)

        # ───── Estado principal (TU lógica intacta)
        position = "NEUTRO"
        last_date = df['dt'].iloc[-1]

        for i in range(1, len(df)):
            hist, prev_hist = df['HIST'].iloc[i], df['HIST'].iloc[i-1]
            ha_color = df['HA_Color'].iloc[i]
            date = df['dt'].iloc[i]

            if position == "LONG" and hist < prev_hist:
                position = "NEUTRO"
            elif position == "SHORT" and hist > prev_hist:
                position = "NEUTRO"

            if position == "NEUTRO":
                if ha_color == 1 and hist > prev_hist:
                    position = "LONG"
                    last_date = date
                elif ha_color == -1 and hist < prev_hist:
                    position = "SHORT"
                    last_date = date

        # RSI estado
        rsi_val = round(df['RSI'].iloc[-1], 1)
        if rsi_val > 55:
            rsi_state = "RSI↑"
        elif rsi_val < 45:
            rsi_state = "RSI↓"
        else:
            rsi_state = "RSI="

        # ───── MACD INFO NUEVA
        hist_now = df['HIST'].iloc[-1]
        hist_prev = df['HIST'].iloc[-2]
        hist_dir = "📈 Hist ↑" if hist_now > hist_prev else "📉 Hist ↓"

        cross_type = "—"
        cross_time = pd.NaT

        for i in range(len(df)-2, 0, -1):
            if df['MACD'].iloc[i-1] < df['SIGNAL'].iloc[i-1] and df['MACD'].iloc[i] > df['SIGNAL'].iloc[i]:
                cross_type = "🟢 Cruce ↑"
                cross_time = df['dt'].iloc[i]
                break
            if df['MACD'].iloc[i-1] > df['SIGNAL'].iloc[i-1] and df['MACD'].iloc[i] < df['SIGNAL'].iloc[i]:
                cross_type = "🔴 Cruce ↓"
                cross_time = df['dt'].iloc[i]
                break

        macd_text = f"{hist_dir} | {cross_type}"

        return (
            position,
            last_date,
            rsi_state,
            rsi_val,
            macd_text,
            cross_time
        )

    except:
        return None

# ─────────────────────────────────────────────
# RECOMENDACIÓN MACD GLOBAL
# ─────────────────────────────────────────────
def macd_recommendation(row):
    bull = sum("📈" in str(row.get(f"{tf}_macd")) for tf in TIMEFRAMES)
    bear = sum("📉" in str(row.get(f"{tf}_macd")) for tf in TIMEFRAMES)

    if bull >= 5:
        return "🚀 MACD ALCISTA MULTI-TF"
    if bear >= 5:
        return "🩸 MACD BAJISTA MULTI-TF"
    return "⚖️ MACD MIXTO / ESPERAR"

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

        try:
            price = ex.fetch_ticker(sym)['last']
        except:
            continue

        row = {'Activo': clean}

        for label, tf in TIMEFRAMES.items():
            res = analyze_ticker_tf(sym, tf, ex, price)
            if res:
                state, date, rsi_state, rsi_val, macd_txt, macd_time = res

                row[f"{label}_state"] = state
                row[f"{label}_rsi"] = rsi_val
                row[f"{label}_rsi_state"] = rsi_state
                row[f"{label}_datetime"] = date
                row[f"{label}_macd"] = macd_txt
                row[f"{label}_macd_time"] = macd_time
            else:
                row[f"{label}_state"] = "NEUTRO"
                row[f"{label}_rsi"] = np.nan
                row[f"{label}_rsi_state"] = "-"
                row[f"{label}_datetime"] = pd.NaT
                row[f"{label}_macd"] = "—"
                row[f"{label}_macd_time"] = pd.NaT

        row['MACD Estrategia'] = macd_recommendation(row)
        results.append(row)
        time.sleep(0.05)

    prog.empty()
    return results

# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
st.title("🎯 SystemaTrader: MNQ Sniper Matrix V5")

with st.sidebar:
    st.header("Configuración")
    all_symbols = get_active_pairs()
    BATCH_SIZE = st.selectbox("Tamaño lote", [10,20,30,50], index=1)

    batches = [all_symbols[i:i+BATCH_SIZE] for i in range(0, len(all_symbols), BATCH_SIZE)]
    sel = st.selectbox("Lote", range(len(batches)))

    if st.button("🚀 ESCANEAR"):
        st.session_state['sniper_results'] = scan_batch(batches[sel])

# ─────────────────────────────────────────────
# TABLA FINAL
# ─────────────────────────────────────────────
if st.session_state['sniper_results']:
    df = pd.DataFrame(st.session_state['sniper_results'])

    columnas = ['Activo', 'MACD Estrategia']
    for tf in TIMEFRAMES:
        columnas.append(f"{tf}_macd")

columnas_existentes = [c for c in columnas if c in df.columns]

st.data_editor(
    df[columnas_existentes],
    use_container_width=True,
    height=800,
    disabled=True
)
else:
    st.info("Seleccioná un lote y escaneá.")
