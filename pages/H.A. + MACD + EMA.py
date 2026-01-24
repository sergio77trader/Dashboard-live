import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime

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
        return pd.DataFrame(valid).sort_values('vol', ascending=False)['symbol'].tolist()
    except:
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
        last_date = df['dt'].iloc[-2]

        for i in range(1, len(df)):
            hist, prev_hist = df['HIST'].iloc[i], df['HIST'].iloc[i-1]
            ha_color = df['HA_Color'].iloc[i]
            date = df['dt'].iloc[i]

            if position == "NEUTRO":
                if ha_color == 1 and hist > prev_hist:
                    position = "LONG"
                    last_date = date
                elif ha_color == -1 and hist < prev_hist:
                    position = "SHORT"
                    last_date = date

        # RSI
        rsi_val = df['RSI'].iloc[-1]
        rsi_state = "RSI↑" if rsi_val > 55 else "RSI↓" if rsi_val < 45 else "RSI="

        # --- NUEVO: MACD HIST (última vela cerrada)
        hist_now = df['HIST'].iloc[-2]
        hist_prev = df['HIST'].iloc[-3]
        hist_state = "Alcista" if hist_now > hist_prev else "Bajista"

        # --- NUEVO: CRUCE MACD (última vela cerrada)
        macd_now = df['MACD'].iloc[-2]
        macd_prev = df['MACD'].iloc[-3]
        sig_now = df['SIGNAL'].iloc[-2]
        sig_prev = df['SIGNAL'].iloc[-3]

        cruce = "-"
        hora_cruce = "-"

        if macd_prev < sig_prev and macd_now > sig_now:
            cruce = "Alcista"
            hora_cruce = (df['dt'].iloc[-2] - pd.Timedelta(hours=3)).strftime('%H:%M')
        elif macd_prev > sig_prev and macd_now < sig_now:
            cruce = "Bajista"
            hora_cruce = (df['dt'].iloc[-2] - pd.Timedelta(hours=3)).strftime('%H:%M')

        return position, last_date, rsi_state, round(rsi_val,1), hist_state, cruce, hora_cruce

    except:
        return None

# --- RECOMENDACIÓN MACD ---
def macd_recommendation(row):
    alcistas = sum(row.get(f"MACD HIST {tf}") == "Alcista" for tf in TIMEFRAMES)
    bajistas = sum(row.get(f"MACD HIST {tf}") == "Bajista" for tf in TIMEFRAMES)

    cruces_alc = any(row.get(f"CRUCE MACD {tf}") == "Alcista" for tf in ['1m','5m','15m'])
    cruces_baj = any(row.get(f"CRUCE MACD {tf}") == "Bajista" for tf in ['1m','5m','15m'])

    if alcistas >= 5 and cruces_alc:
        return "🔥 Momentum Alcista Fuerte"
    if bajistas >= 5 and cruces_baj:
        return "🩸 Momentum Bajista Fuerte"

    return "⚖️ MACD Mixto / Esperar"

# --- RECOMENDACIÓN FINAL ---
def final_recommendation(row):
    est = row.get("Estrategia","")
    macd = row.get("Recomendación MACD","")

    if "COMPRA FUERTE" in est and "Alcista Fuerte" in macd:
        return "🚀 COMPRA MUY FUERTE"
    if "VENTA FUERTE" in est and "Bajista Fuerte" in macd:
        return "💀 VENTA MUY FUERTE"
    if "COMPRA" in est and "Mixto" in macd:
        return "⚠️ COMPRA CON CUIDADO"
    if "VENTA" in est and "Mixto" in macd:
        return "⚠️ VENTA CON CUIDADO"

    return "🧊 ESPERAR"

# --- ESCANEO ---
def scan_batch(targets):
    ex = get_exchange()
    results = []
    prog = st.progress(0)

    for idx, sym in enumerate(targets):
        clean = sym.replace(':USDT','').replace('/USDT','')
        prog.progress(idx/len(targets))

        try:
            price = ex.fetch_ticker(sym)['last']
        except:
            continue

        row = {'Activo': clean}

        for label, tf in TIMEFRAMES.items():
            res = analyze_ticker_tf(sym, tf, ex, price)
            if res:
                state, date, rsi_state, rsi_val, hist_state, cruce, hora_cruce = res
                icon = "🟢" if state=="LONG" else "🔴" if state=="SHORT" else "⚪"

                row[f"{label} HA-MACD"] = f"{icon} {state} | {rsi_state} ({rsi_val})"
                row[f"{label} ALERTA"] = (date - pd.Timedelta(hours=3)).strftime('%H:%M')
                row[f"MACD HIST {label}"] = hist_state
                row[f"CRUCE MACD {label}"] = cruce
                row[f"HORA CRUCE {label}"] = hora_cruce
            else:
                row[f"{label} HA-MACD"] = "-"
                row[f"{label} ALERTA"] = "-"
                row[f"MACD HIST {label}"] = "-"
                row[f"CRUCE MACD {label}"] = "-"
                row[f"HORA CRUCE {label}"] = "-"

        row["Recomendación MACD"] = macd_recommendation(row)
        row["Recomendación Final"] = final_recommendation(row)

        results.append(row)
        time.sleep(0.1)

    prog.empty()
    return results
