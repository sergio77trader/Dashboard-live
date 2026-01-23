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
    /* Ajuste para que se vean bien tantas columnas */
    .stDataFrame { font-size: 0.8rem; }
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
        return (pd.DataFrame(valid).sort_values('vol', ascending=False)['symbol'].tolist())
    except: return []

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
# ANÁLISIS POR TF (EXPANDIDO)
# ─────────────────────────────────────────────
def analyze_ticker_tf(symbol, tf_code, exchange, current_price):
    try:
        # Bajamos 200 velas para detectar cruces viejos
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=200)
        if not ohlcv or len(ohlcv) < 50: return None

        ohlcv[-1][4] = current_price

        df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','vol'])
        df['dt'] = pd.to_datetime(df['time'], unit='ms')

        # MACD (12, 26, 9)
        macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
        df['MACD'] = macd['MACD_12_26_9']
        df['Signal'] = macd['MACDs_12_26_9']
        df['Hist'] = macd['MACDh_12_26_9']
        df['RSI'] = ta.rsi(df['close'], length=14)
        
        df = calculate_heikin_ashi(df)

        # --- LÓGICA HA ORIGINAL ---
        position = "NEUTRO"
        last_date = df['dt'].iloc[-1]

        for i in range(1, len(df)):
            hist, prev_hist = df['Hist'].iloc[i], df['Hist'].iloc[i-1]
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

        # --- NUEVOS DATOS SOLICITADOS ---
        
        # 1. Histograma (Subiendo/Bajando)
        curr_hist = df['Hist'].iloc[-1]
        prev_hist = df['Hist'].iloc[-2]
        hist_trend = "↗️ Subiendo" if curr_hist > prev_hist else "↘️ Bajando"
        
        # 2. Cruce MACD
        df['Cross'] = np.where(df['MACD'] > df['Signal'], 1, -1)
        df['Change'] = df['Cross'].diff() # != 0 es cruce
        
        # Buscar último cruce
        cross_rows = df[df['Change'] != 0]
        if not cross_rows.empty:
            last_cross = cross_rows.iloc[-1]
            cross_type = "🐂 BULL" if last_cross['Cross'] == 1 else "🐻 BEAR"
            cross_dt = last_cross['dt'] - pd.Timedelta(hours=3) # Hora Arg
            cross_date = cross_dt.strftime('%Y-%m-%d')
            cross_time = cross_dt.strftime('%H:%M')
        else:
            cross_type = "-"
            cross_date = "-"
            cross_time = "-"

        # RSI Estado
        rsi_val = round(df['RSI'].iloc[-1], 1)
        rsi_state = "RSI↑" if rsi_val > 55 else ("RSI↓" if rsi_val < 45 else "RSI=")

        return {
            "state": position,
            "date": last_date,
            "rsi_st": rsi_state,
            "rsi_val": rsi_val,
            # Nuevos
            "hist_trend": hist_trend,
            "cross_type": cross_type,
            "cross_date": cross_date,
            "cross_time": cross_time
        }

    except: return None

# ─────────────────────────────────────────────
# RECOMENDACIONES (EXPANDIDO)
# ─────────────────────────────────────────────
def get_recommendations(row):
    # 1. Estrategia HA (Original)
    longs = sum(row.get(f"{tf}_state") == "LONG" for tf in TIMEFRAMES)
    shorts = sum(row.get(f"{tf}_state") == "SHORT" for tf in TIMEFRAMES)
    
    rsi_bull = row.get("4H_rsi_state") == "RSI↑" or row.get("1D_rsi_state") == "RSI↑"
    rsi_bear = row.get("4H_rsi_state") == "RSI↓" or row.get("1D_rsi_state") == "RSI↓"

    strat_ha = "⚖️ RANGO"
    if longs >= 5 and rsi_bull: strat_ha = "🔥 COMPRA FUERTE"
    elif shorts >= 5 and rsi_bear: strat_ha = "🩸 VENTA FUERTE"

    # 2. Recomendación MACD (Nueva)
    # Basada en Histograma y Cruces
    macd_bull = 0
    macd_bear = 0
    
    for tf in TIMEFRAMES:
        h = row.get(f"{tf}_hist", "")
        c = row.get(f"{tf}_cross", "")
        if "Subiendo" in h: macd_bull += 1
        if "Bajando" in h: macd_bear += 1
        if "BULL" in c: macd_bull += 2
        if "BEAR" in c: macd_bear += 2
        
    strat_macd = "Neutro"
    if macd_bull >= 12: strat_macd = "🚀 Momentum Alcista"
    elif macd_bear >= 12: strat_macd = "📉 Momentum Bajista"
    
    # 3. Recomendación GLOBAL (La Definitiva)
    strat_global = "ESPERAR"
    if "COMPRA" in strat_ha and "Alcista" in strat_macd: strat_global = "💎 ALL IN LONG"
    elif "VENTA" in strat_ha and "Bajista" in strat_macd: strat_global = "☠️ ALL IN SHORT"
    elif "COMPRA" in strat_ha: strat_global = "🟢 LONG (Con cuidado)"
    elif "VENTA" in strat_ha: strat_global = "🔴 SHORT (Con cuidado)"
    
    return strat_ha, strat_macd, strat_global

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

        try: price = ex.fetch_ticker(sym)['last']
        except: continue

        row = {'Activo': clean}

        for label, tf in TIMEFRAMES.items():
            res = analyze_ticker_tf(sym, tf, ex, price)
            if res:
                date_dt = res['date'] - pd.Timedelta(hours=3)
                
                # Datos Originales
                row[f"{label}_state"] = res['state']
                row[f"{label}_rsi"] = res['rsi_val']
                row[f"{label}_rsi_state"] = res['rsi_st']
                row[f"{label}_datetime"] = date_dt
                
                # Datos Nuevos
                row[f"{label}_hist"] = res['hist_trend']
                row[f"{label}_cross"] = res['cross_type']
                row[f"{label}_c_date"] = res['cross_date']
                row[f"{label}_c_time"] = res['cross_time']
            else:
                # Rellenar vacíos
                row[f"{label}_state"] = "NEUTRO"
                row[f"{label}_rsi"] = 0
                row[f"{label}_rsi_state"] = "-"
                row[f"{label}_datetime"] = pd.NaT
                row[f"{label}_hist"] = "-"
                row[f"{label}_cross"] = "-"
                row[f"{label}_c_date"] = "-"
                row[f"{label}_c_time"] = "-"

        # Calcular Recomendaciones
        s_ha, s_macd, s_glob = get_recommendations(row)
        row['Estrategia HA'] = s_ha
        row['Recom. MACD'] = s_macd
        row['VEREDICTO FINAL'] = s_glob
        
        results.append(row)
        time.sleep(0.05)

    prog.empty()
    return results

# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
st.title("🎯 SystemaTrader: MNQ Sniper Matrix V5 (Extended)")

with st.sidebar:
    st.header("Configuración")
    all_symbols = get_active_pairs()
    BATCH_SIZE = st.selectbox("Tamaño lote", [10,20,30,50], index=1)
    batches = [all_symbols[i:i+BATCH_SIZE] for i in range(0, len(all_symbols), BATCH_SIZE)]
    sel = st.selectbox("Lote", range(len(batches)))
    accumulate = st.checkbox("Acumular resultados", value=True)

    if st.button("🚀 ESCANEAR"):
        new = scan_batch(batches[sel])
        if accumulate: st.session_state['sniper_results'].extend(new)
        else: st.session_state['sniper_results'] = new

    if st.button("Limpiar"):
        st.session_state['sniper_results'] = []
        st.rerun()

# ─────────────────────────────────────────────
# TABLA FINAL (ESTRUCTURA MASIVA)
# ─────────────────────────────────────────────
if st.session_state['sniper_results']:
    df = pd.DataFrame(st.session_state['sniper_results'])

    # 1. Preprocesar columnas originales para visualización
    for tf in TIMEFRAMES:
        df[f"{tf} Alerta Fecha"] = df[f"{tf}_datetime"].dt.strftime('%Y-%m-%d')
        df[f"{tf} Alerta Hora"]  = df[f"{tf}_datetime"].dt.strftime('%H:%M')

        df[tf] = (
            df[f"{tf}_state"].map({"LONG":"🟢 LONG","SHORT":"🔴 SHORT","NEUTRO":"⚪ NEUTRO"}) + 
            " | " + df[f"{tf}_rsi_state"] + " (" + df[f"{tf}_rsi"].astype(str) + ")"
        )

    # 2. Armar Lista de Columnas en Orden Lógico
    cols_show = ['Activo', 'VEREDICTO FINAL', 'Estrategia HA', 'Recom. MACD']
    
    for tf in TIMEFRAMES:
        # Bloque por temporalidad
        cols_show.append(tf)                  # Estado + RSI
        cols_show.append(f"{tf} Alerta Fecha")
        cols_show.append(f"{tf} Alerta Hora")
        cols_show.append(f"{tf}_hist")        # Nuevo: Histograma
        cols_show.append(f"{tf}_cross")       # Nuevo: Cruce
        cols_show.append(f"{tf}_c_date")      # Nuevo: Fecha Cruce
        cols_show.append(f"{tf}_c_time")      # Nuevo: Hora Cruce

    # Filtrar existentes
    cols_final = [c for c in cols_show if c in df.columns]

    st.dataframe(
        df[cols_final],
        use_container_width=True,
        height=800,
        column_config={
            "Activo": st.column_config.TextColumn(pinned=True),
            "VEREDICTO FINAL": st.column_config.TextColumn("⭐ VEREDICTO", width="medium"),
        }
    )
else:
    st.info("Seleccioná un lote y escaneá.")
