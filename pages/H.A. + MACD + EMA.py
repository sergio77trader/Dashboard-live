import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime

# =========================
# DEBUG INICIAL
# =========================
st.write("✅ APP CARGADA OK")

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SystemaTrader: MNQ Sniper Matrix")
st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 14px; }
    .stProgress > div > div > div > div { background-color: #2962FF; }
</style>
""", unsafe_allow_html=True)

# --- MEMORIA ---
if 'sniper_results' not in st.session_state:
    st.session_state['sniper_results'] = []

# --- TEMPORALIDADES ---
TIMEFRAMES = {
    '1m': '1m', '5m': '5m', '15m': '15m',
    '30m': '30m', '1H': '1h', '4H': '4h', '1D': '1d'
}

# --- CONEXIÓN ---
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
        df = pd.DataFrame(valid)
        st.write(f"🔍 Pares detectados: {len(df)}")
        return df.sort_values('vol', ascending=False)['symbol'].tolist()
    except Exception as e:
        st.error(f"❌ Error mercado: {e}")
        return []

# --- HEIKIN ASHI ---
def calculate_heikin_ashi(df):
    df_ha = df.copy()
    df_ha['HA_Close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    ha_open = [df['open'].iloc[0]]
    for i in range(1, len(df)):
        ha_open.append((ha_open[-1] + df_ha['HA_Close'].iloc[i-1]) / 2)
    df_ha['HA_Open'] = ha_open
    df_ha['HA_Color'] = np.where(df_ha['HA_Close'] > df_ha['HA_Open'], 1, -1)
    return df_ha

# --- ANALISIS POR TEMPORALIDAD ---
def analyze_ticker_tf(symbol, tf_code, exchange, current_price):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=100)
        if not ohlcv or len(ohlcv) < 50:
            return None

        ohlcv[-1][4] = current_price
        df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','vol'])
        df['dt'] = pd.to_datetime(df['time'], unit='ms')

        macd = ta.macd(df['close'])
        df['Hist'] = macd['MACDh_12_26_9']
        df['RSI'] = ta.rsi(df['close'], length=14)
        df = calculate_heikin_ashi(df)

        position = "NEUTRO"
        last_date = df['dt'].iloc[-1]

        for i in range(1, len(df)):
            hist, prev_hist = df['Hist'].iloc[i], df['Hist'].iloc[i-1]
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

        rsi_val = df['RSI'].iloc[-1]
        if rsi_val > 55:
            rsi_state = "RSI↑"
        elif rsi_val < 45:
            rsi_state = "RSI↓"
        else:
            rsi_state = "RSI="

        return position, last_date, rsi_state, round(rsi_val, 1)

    except Exception as e:
        st.write(f"⚠️ Error {symbol} {tf_code}: {e}")
        return None

# --- RECOMENDACIÓN FINAL ---
def get_recommendation(row):
    longs = sum("LONG" in str(row.get(tf,'')) for tf in TIMEFRAMES)
    shorts = sum("SHORT" in str(row.get(tf,'')) for tf in TIMEFRAMES)

    if longs >= 5:
        return "🔥 COMPRA FUERTE"
    if shorts >= 5:
        return "🩸 VENTA FUERTE"

    return "⚖️ RANGO / ESPERAR"

# --- ESCANEO POR LOTE ---
def scan_batch(targets):
    st.write("🧠 SCAN INICIADO")
    ex = get_exchange()
    results = []

    for sym in targets:
        try:
            price = ex.fetch_ticker(sym)['last']
        except:
            continue

        row = {'Activo': sym.replace(':USDT','').replace('/USDT','')}

        for label, tf in TIMEFRAMES.items():
            res = analyze_ticker_tf(sym, tf, ex, price)
            if res:
                state, date, rsi_state, rsi_val = res
                icon = "🟢" if state=="LONG" else "🔴" if state=="SHORT" else "⚪"
                date = (date - pd.Timedelta(hours=3)).strftime('%d/%m %H:%M')
                row[label] = f"{icon} {state} | {rsi_state} ({rsi_val})\n({date})"
            else:
                row[label] = "-"

        row['Estrategia'] = get_recommendation(row)
        results.append(row)

    st.write(f"📦 Filas generadas: {len(results)}")
    return results

# =========================
# INTERFAZ
# =========================
st.title("🎯 SystemaTrader: MNQ Sniper Matrix V4")
st.caption("Heikin Ashi + MACD + RSI MTF | KuCoin Futures")

with st.sidebar:
    st.header("Configuración")

    all_symbols = get_active_pairs()

    if all_symbols:
        BATCH_SIZE = st.selectbox("Tamaño Lote:", [10, 20, 30, 50], index=1)
        batches = [all_symbols[i:i + BATCH_SIZE] for i in range(0, len(all_symbols), BATCH_SIZE)]
        sel_batch = st.selectbox("Seleccionar Lote:", range(len(batches)))

        accumulate = st.checkbox("Acumular Resultados", value=True)

        if st.button("🚀 ESCANEAR LOTE"):
            data = scan_batch(batches[sel_batch])
            if accumulate:
                st.session_state['sniper_results'].extend(data)
            else:
                st.session_state['sniper_results'] = data

    if st.button("Limpiar"):
        st.session_state['sniper_results'] = []
        st.rerun()

# --- TABLA ---
st.write("📊 RENDER TABLA")

if st.session_state['sniper_results']:
    df = pd.DataFrame(st.session_state['sniper_results'])
    st.dataframe(df, use_container_width=True, height=800)
else:
    st.info("👈 Seleccioná un lote para comenzar el escaneo.")

st.success("✅ FIN DEL SCRIPT ALCANZADO")
