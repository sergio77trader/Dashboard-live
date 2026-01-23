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
# ANÁLISIS POR TF
# ─────────────────────────────────────────────
def analyze_ticker_tf(symbol, tf_code, exchange, current_price):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=100)
        if not ohlcv or len(ohlcv) < 50:
            return None

        ohlcv[-1][4] = current_price

        df = pd.DataFrame(
            ohlcv, columns=['time','open','high','low','close','vol']
        )
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

        rsi_val = round(df['RSI'].iloc[-1], 1)
        if rsi_val > 55:
            rsi_state = "RSI↑"
        elif rsi_val < 45:
            rsi_state = "RSI↓"
        else:
            rsi_state = "RSI="

        return position, last_date, rsi_state, rsi_val

    except:
        return None

# ─────────────────────────────────────────────
# RECOMENDACIÓN FINAL
# ─────────────────────────────────────────────
def get_recommendation(row):
    longs = sum(row.get(f"{tf}_state") == "LONG" for tf in TIMEFRAMES)
    shorts = sum(row.get(f"{tf}_state") == "SHORT" for tf in TIMEFRAMES)

    rsi_htf_bull = (
        row.get("4H_rsi_state") == "RSI↑"
        or row.get("1D_rsi_state") == "RSI↑"
    )
    rsi_htf_bear = (
        row.get("4H_rsi_state") == "RSI↓"
        or row.get("1D_rsi_state") == "RSI↓"
    )

    if longs >= 5 and rsi_htf_bull:
        return "🔥 COMPRA FUERTE"
    if shorts >= 5 and rsi_htf_bear:
        return "🩸 VENTA FUERTE"

    return "⚖️ RANGO / ESPERAR"

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
                state, date, rsi_state, rsi_val = res
                date_dt = date - pd.Timedelta(hours=3)

                row[f"{label}_state"] = state
                row[f"{label}_rsi"] = rsi_val
                row[f"{label}_rsi_state"] = rsi_state
                row[f"{label}_datetime"] = date_dt
                row[f"{label}_hour"] = date_dt.hour
            else:
                row[f"{label}_state"] = "NEUTRO"
                row[f"{label}_rsi"] = np.nan
                row[f"{label}_rsi_state"] = "-"
                row[f"{label}_datetime"] = pd.NaT
                row[f"{label}_hour"] = np.nan

        row['Estrategia'] = get_recommendation(row)
        results.append(row)
        time.sleep(0.05)

    prog.empty()
    return results

# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
st.title("🎯 SystemaTrader: MNQ Sniper Matrix V4")

with st.sidebar:
    st.header("Configuración")

    all_symbols = get_active_pairs()
    BATCH_SIZE = st.selectbox("Tamaño lote", [10,20,30,50], index=1)

    batches = [
        all_symbols[i:i+BATCH_SIZE]
        for i in range(0, len(all_symbols), BATCH_SIZE)
    ]

    sel = st.selectbox("Lote", range(len(batches)))
    accumulate = st.checkbox("Acumular resultados", value=True)

    if st.button("🚀 ESCANEAR"):
        new = scan_batch(batches[sel])
        if accumulate:
            st.session_state['sniper_results'].extend(new)
        else:
            st.session_state['sniper_results'] = new

    if st.button("Limpiar"):
        st.session_state['sniper_results'] = []
        st.rerun()

# ─────────────────────────────────────────────
# TABLA + FILTROS
# ─────────────────────────────────────────────
if st.session_state['sniper_results']:
    df = pd.DataFrame(st.session_state['sniper_results'])

    st.sidebar.subheader("Filtros")
    estr = st.sidebar.multiselect(
        "Estrategia",
        df['Estrategia'].unique().tolist(),
        default=df['Estrategia'].unique().tolist()
    )

    hmin, hmax = st.sidebar.slider("Horario", 0, 23, (0, 23))

    df = df[
        (df['Estrategia'].isin(estr)) &
        (df['1m_hour'] >= hmin) &
        (df['1m_hour'] <= hmax)
    ]

    for tf in TIMEFRAMES:
        df[tf] = (
            df[f"{tf}_state"]
            .map({"LONG":"🟢 LONG","SHORT":"🔴 SHORT","NEUTRO":"⚪ NEUTRO"})
            + " | "
            + df[f"{tf}_rsi_state"]
            + " ("
            + df[f"{tf}_rsi"].astype(str)
            + ")\n("
            + df[f"{tf}_datetime"].dt.strftime('%d/%m %H:%M')
            + ")"
        )

    st.dataframe(
        df[['Activo'] + list(TIMEFRAMES.keys()) + ['Estrategia']],
        use_container_width=True,
        height=800
    )
else:
    st.info("Seleccioná un lote y escaneá.")
