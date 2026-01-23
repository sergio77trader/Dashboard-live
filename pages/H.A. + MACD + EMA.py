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
st.set_page_config(layout="wide", page_title="SystemaTrader: The Monolith")
st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 14px; }
    .stProgress > div > div > div > div { background-color: #2962FF; }
    .stDataFrame { font-size: 0.8rem; }
</style>
""", unsafe_allow_html=True)

if 'monolith_results' not in st.session_state:
    st.session_state['monolith_results'] = []

TIMEFRAMES = {
    '15m': '15m',
    '1H': '1h',
    '4H': '4h',
    'Diario': '1d',
    'Semanal': '1w'
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

def analyze_tf_data(symbol, tf_label, tf_code, exchange):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=200)
        if not ohlcv or len(ohlcv) < 50: return None
        
        df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
        df['dt'] = pd.to_datetime(df['time'], unit='ms')
        
        # INDICADORES
        macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
        df['MACD'] = macd['MACD_12_26_9']
        df['Signal'] = macd['MACDs_12_26_9']
        df['Hist'] = macd['MACDh_12_26_9']
        df['RSI'] = ta.rsi(df['close'], length=14)
        
        df = calculate_heikin_ashi(df)
        
        # 1. ESTADO ESTRATEGIA (TU ORIGINAL)
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

        # 2. RSI
        rsi_val = round(df['RSI'].iloc[-1], 1)

        # 3. HISTOGRAMA (NUEVO)
        curr_hist = df['Hist'].iloc[-1]
        prev_hist = df['Hist'].iloc[-2]
        hist_trend = "↗️ Sube" if curr_hist > prev_hist else "↘️ Baja"

        # 4. CRUCE MACD (NUEVO)
        df['Cross'] = np.where(df['MACD'] > df['Signal'], 1, -1)
        df['Change'] = df['Cross'].diff()
        
        cross_rows = df[df['Change'] != 0]
        if not cross_rows.empty:
            last_cross = cross_rows.iloc[-1]
            c_type = "🐂 GOLDEN" if last_cross['Cross'] == 1 else "🐻 DEATH"
            dt_arg = last_cross['dt'] - pd.Timedelta(hours=3)
            c_date = dt_arg.strftime('%Y-%m-%d')
            c_time = dt_arg.strftime('%H:%M')
        else:
            c_type = "-"
            c_date = "-"
            c_time = "-"

        # RETORNO DE TODO POR SEPARADO
        return {
            f"{tf_label} Estado": position,
            f"{tf_label} RSI": rsi_val,
            f"{tf_label} Hist": hist_trend,
            f"{tf_label} Cruce": c_type,
            f"{tf_label} Fecha": c_date,
            f"{tf_label} Hora": c_time
        }
    except: return None

def get_verdict(row):
    score = 0
    # Usamos el Estado Original para el veredicto
    for tf in TIMEFRAMES:
        st = row.get(f"{tf} Estado", "")
        if "LONG" in st: score += 1
        if "SHORT" in st: score -= 1
    
    if score >= 4: return "🔥 COMPRA FUERTE"
    if score <= -4: return "🩸 VENTA FUERTE"
    if score > 0: return "🟢 ALCISTA"
    if score < 0: return "🔴 BAJISTA"
    return "⚖️ RANGO"

def scan_batch(targets):
    ex = get_exchange()
    results = []
    prog = st.progress(0, text="Escaneando...")
    
    for idx, sym in enumerate(targets):
        clean_name = sym.replace(':USDT', '').replace('/USDT', '')
        prog.progress(idx/len(targets), text=f"Analizando {clean_name}...")
        
        try: px = ex.fetch_ticker(sym)['last']
        except: px = 0
        
        row = {'Activo': clean_name, 'Precio': px}
        
        for label, code in TIMEFRAMES.items():
            data_tf = analyze_tf_data(sym, label, code, ex)
            if data_tf: 
                row.update(data_tf)
            else:
                # Rellenar vacíos para que la tabla no se rompa
                for k in ["Estado", "RSI", "Hist", "Cruce", "Fecha", "Hora"]:
                    row[f"{label} {k}"] = "-"
        
        row['VEREDICTO'] = get_verdict(row)
        results.append(row)
        time.sleep(0.1)
    
    prog.empty()
    return results

# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
st.title("🎛️ SystemaTrader: The Monolith Matrix (V11)")

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
            with st.spinner("Generando matriz completa..."):
                new_data = scan_batch(target)
                if accumulate: st.session_state['monolith_results'].extend(new_data)
                else: st.session_state['monolith_results'] = new_data
    
    if st.button("Limpiar"):
        st.session_state['monolith_results'] = []
        st.rerun()
    
    st.divider()
    st.subheader("Filtros")
    f_opts = ["🔥 COMPRA FUERTE", "🩸 VENTA FUERTE", "🟢 ALCISTA", "🔴 BAJISTA", "⚖️ RANGO"]
    sel_filt = st.multiselect("Filtrar por Veredicto:", f_opts, default=f_opts)

# ─────────────────────────────────────────────
# TABLA
# ─────────────────────────────────────────────
if st.session_state['monolith_results']:
    df = pd.DataFrame(st.session_state['monolith_results'])
    
    # Filtro
    if sel_filt:
        df = df[df['VEREDICTO'].isin(sel_filt)]
    
    # Definición de Columnas (Orden Estricto)
    cols = ['Activo', 'VEREDICTO', 'Precio']
    # Bucle para generar las 30 columnas de datos (5 TFs * 6 Datos)
    for tf in ["15m", "1H", "4H", "Diario", "Semanal"]:
        cols.append(f"{tf} Estado")
        cols.append(f"{tf} RSI")
        cols.append(f"{tf} Hist")
        cols.append(f"{tf} Cruce")
        cols.append(f"{tf} Fecha")
        cols.append(f"{tf} Hora")
        
    final_cols = [c for c in cols if c in df.columns]
    
    # Función de Estilo (Colores Claros/Legibles)
    def style_universal(val):
        s = str(val)
        # Verde Claro
        if any(x in s for x in ["LONG", "Sube", "GOLDEN", "COMPRA", "ALCISTA", "BULL"]):
            return "background-color: #d4edda; color: #155724; font-weight: bold"
        # Rojo Claro
        if any(x in s for x in ["SHORT", "Baja", "DEATH", "VENTA", "BAJISTA", "BEAR"]):
            return "background-color: #f8d7da; color: #721c24; font-weight: bold"
        return ""

    st.dataframe(
        df[final_cols].style.map(style_universal),
        column_config={
            "Activo": st.column_config.TextColumn(pinned=True),
            "Precio": st.column_config.NumberColumn(format="$%.4f")
        },
        use_container_width=True,
        height=800
    )
else:
    st.info("👈 Escanea un lote para ver la Matriz Completa.")
