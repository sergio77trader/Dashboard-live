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
    .stProgress > div > div > div > div { background-color: #2962FF; }
    .stDataFrame { font-size: 0.8rem; }
</style>
""", unsafe_allow_html=True)

if 'sniper_results_v5' not in st.session_state:
    st.session_state['sniper_results_v5'] = []

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
# LÓGICA TÉCNICA
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
        # Bajamos 200 velas para tener historial de cruces
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
        
        # RSI
        df['RSI'] = ta.rsi(df['close'], length=14)
        
        # HA
        df = calculate_heikin_ashi(df)

        # 1. ESTADO DE ESTRATEGIA (HA + MOMENTUM)
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

        # 2. ANÁLISIS DE HISTOGRAMA
        curr_hist = df['Hist'].iloc[-1]
        prev_hist = df['Hist'].iloc[-2]
        hist_trend = "↗ Subiendo" if curr_hist > prev_hist else "↘ Bajando"

        # 3. ANÁLISIS DE CRUCE MACD
        df['Cross'] = np.where(df['MACD'] > df['Signal'], 1, -1)
        df['Change'] = df['Cross'].diff() # != 0 es un cruce
        
        # Buscar el último cruce
        cross_rows = df[df['Change'] != 0]
        if not cross_rows.empty:
            last_cross = cross_rows.iloc[-1]
            c_type = "🐂 BULL" if last_cross['Cross'] == 1 else "🐻 BEAR"
            
            # Ajuste horario (-3h Argentina)
            c_dt = last_cross['dt'] - pd.Timedelta(hours=3)
            c_date = c_dt.strftime('%Y-%m-%d')
            c_time = c_dt.strftime('%H:%M')
        else:
            c_type = "-"
            c_date = "-"
            c_time = "-"

        # RSI Estado
        rsi_val = round(df['RSI'].iloc[-1], 1)
        rsi_state = "RSI↑" if rsi_val > 55 else ("RSI↓" if rsi_val < 45 else "RSI=")

        return {
            "state": position,
            "date": last_date,
            "rsi_st": rsi_state,
            "rsi_val": rsi_val,
            # Nuevos datos
            "hist_trend": hist_trend,
            "cross_type": c_type,
            "cross_date": c_date,
            "cross_time": c_time
        }

    except: return None

# ─────────────────────────────────────────────
# RECOMENDACIÓN IA
# ─────────────────────────────────────────────
def get_final_verdict(row):
    # Puntos por Estrategia HA
    longs = sum(row.get(f"{tf}_state") == "LONG" for tf in TIMEFRAMES)
    shorts = sum(row.get(f"{tf}_state") == "SHORT" for tf in TIMEFRAMES)
    
    # Puntos por Cruces MACD (Momentum Puro)
    macd_bull = 0
    macd_bear = 0
    for tf in TIMEFRAMES:
        cross = row.get(f"{tf}_cross", "")
        if "BULL" in cross: macd_bull += 1
        if "BEAR" in cross: macd_bear += 1

    # Veredicto
    if longs >= 5 and macd_bull >= 5: return "🔥 COMPRA FUERTE (Trend + Mom)"
    if shorts >= 5 and macd_bear >= 5: return "🩸 VENTA FUERTE (Trend + Mom)"
    
    if longs >= 4: return "🟢 ALCISTA (Trend)"
    if shorts >= 4: return "🔴 BAJISTA (Trend)"
    
    if macd_bull >= 5: return "🚀 MOMENTUM ALCISTA (Posible Entrada)"
    if macd_bear >= 5: return "📉 MOMENTUM BAJISTA (Posible Caída)"
    
    return "⚖️ RANGO / INDECISIÓN"

# ─────────────────────────────────────────────
# BUCLE ESCANEO
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

        row['VEREDICTO'] = get_final_verdict(row)
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
        if accumulate: st.session_state['sniper_results_v5'].extend(new)
        else: st.session_state['sniper_results_v5'] = new

    if st.button("Limpiar"):
        st.session_state['sniper_results_v5'] = []
        st.rerun()

    st.divider()
    st.subheader("Filtro IA")
    # Filtro por veredicto
    f_opts = ["🔥 COMPRA FUERTE", "🩸 VENTA FUERTE", "🟢 ALCISTA", "🔴 BAJISTA", "🚀 MOMENTUM ALCISTA", "📉 MOMENTUM BAJISTA", "⚖️ RANGO"]
    # Por defecto mostramos todo, pero el usuario puede filtrar
    sel_filt = st.multiselect("Mostrar solo:", f_opts, default=f_opts)

# ─────────────────────────────────────────────
# TABLA FINAL
# ─────────────────────────────────────────────
if st.session_state['sniper_results_v5']:
    df = pd.DataFrame(st.session_state['sniper_results_v5'])
    
    # Filtrar por veredicto (búsqueda parcial para flexibilidad)
    mask = df['VEREDICTO'].apply(lambda x: any(f in x for f in sel_filt))
    df = df[mask]

    # Preprocesar columnas compuestas para visualización compacta
    for tf in TIMEFRAMES:
        df[f"{tf} Alerta Fecha"] = df[f"{tf}_datetime"].dt.strftime('%Y-%m-%d')
        df[f"{tf} Alerta Hora"]  = df[f"{tf}_datetime"].dt.strftime('%H:%M')
        
        # Columna Estado Original Compacta
        df[tf] = (
            df[f"{tf}_state"].map({"LONG":"🟢","SHORT":"🔴","NEUTRO":"⚪"}) + " " +
            df[f"{tf}_rsi_state"] + "(" + df[f"{tf}_rsi"].astype(str) + ")"
        )

    # Definir Orden de Columnas
    cols_show = ['Activo', 'VEREDICTO']
    for tf in ["1m", "5m", "15m", "30m", "1H", "4H", "1D"]: # Orden lógico
        # Bloque de columnas por TF
        cols_show.append(tf) # Estado Resumido
        cols_show.append(f"{tf}_hist")
        cols_show.append(f"{tf}_cross")
        cols_show.append(f"{tf}_c_date")
        cols_show.append(f"{tf}_c_time")
        # Opcional: Agregar Fecha Alerta Original si se desea
        # cols_show.append(f"{tf} Alerta Hora") 

    # Filtrar columnas existentes
    final_cols = [c for c in cols_show if c in df.columns]

    st.dataframe(
        df[final_cols],
        use_container_width=True,
        height=800,
        column_config={
            "Activo": st.column_config.TextColumn(pinned=True),
            "VEREDICTO": st.column_config.TextColumn(width="medium"),
            # Las columnas dinámicas se ajustan solas
        }
    )
else:
    st.info("Seleccioná un lote y escaneá.")
    
