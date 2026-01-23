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

if 'full_results_v91' not in st.session_state:
    st.session_state['full_results_v91'] = []

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
# MOTORES LÓGICOS
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
        
        macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
        df['MACD'] = macd['MACD_12_26_9']
        df['Signal'] = macd['MACDs_12_26_9']
        df['Hist'] = macd['MACDh_12_26_9']
        
        df = calculate_heikin_ashi(df)
        
        # Lógica HA Original
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

        # Nuevos Datos
        curr_hist = df['Hist'].iloc[-1]
        prev_hist = df['Hist'].iloc[-2]
        hist_trend = "↗️ Sube" if curr_hist > prev_hist else "↘️ Baja"
        
        df['Cross'] = np.where(df['MACD'] > df['Signal'], 1, -1)
        df['Change'] = df['Cross'].diff()
        
        cross_rows = df[df['Change'] != 0]
        if not cross_rows.empty:
            last_cross = cross_rows.iloc[-1]
            c_type = "🐂 BULL" if last_cross['Cross'] == 1 else "🐻 BEAR"
            c_time = (last_cross['dt'] - pd.Timedelta(hours=3)).strftime('%d/%m %H:%M')
        else:
            c_type = "-"
            c_time = "-"

        return {
            f"{tf_label} Estado": position,
            f"{tf_label} Hist": hist_trend,
            f"{tf_label} Cruce": c_type,
            f"{tf_label} Fecha": c_time
        }
    except: return None

# --- RECOMENDACIONES (V7 RESTAURADO) ---
def get_recommendations(row):
    # 1. Estrategia HA
    longs = 0
    shorts = 0
    for tf in TIMEFRAMES:
        if "LONG" in row.get(f"{tf} Estado", ""): longs += 1
        if "SHORT" in row.get(f"{tf} Estado", ""): shorts += 1

    strat_ha = "⚖️ RANGO"
    if longs >= 4: strat_ha = "🔥 COMPRA"
    elif shorts >= 4: strat_ha = "🩸 VENTA"

    # 2. Recomendación MACD
    macd_bull = 0
    macd_bear = 0
    for tf in TIMEFRAMES:
        h = row.get(f"{tf} Hist", "")
        c = row.get(f"{tf} Cruce", "")
        if "Sube" in h: macd_bull += 1
        if "Baja" in h: macd_bear += 1
        if "BULL" in c: macd_bull += 2
        if "BEAR" in c: macd_bear += 2
        
    strat_macd = "Neutro"
    if macd_bull >= 10: strat_macd = "🚀 Alcista"
    elif macd_bear >= 10: strat_macd = "📉 Bajista"
    
    # 3. GLOBAL
    strat_global = "ESPERAR"
    if "COMPRA" in strat_ha and "Alcista" in strat_macd: strat_global = "💎 ALL IN LONG"
    elif "VENTA" in strat_ha and "Bajista" in strat_macd: strat_global = "☠️ ALL IN SHORT"
    elif "COMPRA" in strat_ha: strat_global = "🟢 LONG"
    elif "VENTA" in strat_ha: strat_global = "🔴 SHORT"
    
    return strat_ha, strat_macd, strat_global

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
            if data_tf: row.update(data_tf)
            else:
                row[f"{label} Estado"] = "-"
                row[f"{label} Hist"] = "-"
                row[f"{label} Cruce"] = "-"
                row[f"{label} Fecha"] = "-"
        
        # Calculamos TODAS las recomendaciones
        s_ha, s_macd, s_glob = get_recommendations(row)
        row['Estrategia HA'] = s_ha
        row['Recom. MACD'] = s_macd
        row['VEREDICTO FINAL'] = s_glob
        
        results.append(row)
        time.sleep(0.1)
    
    prog.empty()
    return results

# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
st.title("🎛️ SystemaTrader: MACD Full Detail V9.1")

with st.sidebar:
    st.header("Configuración")
    all_symbols = get_active_pairs()
    
    if all_symbols:
        BATCH = st.selectbox("Lote:", [10, 20, 30, 50], index=0)
        batches = [all_symbols[i:i+BATCH] for i in range(0, len(all_symbols), BATCH)]
        sel_batch = st.selectbox("Seleccionar:", range(len(batches)), format_func=lambda x: f"Lote {x+1}")
        accumulate = st.checkbox("Acumular", value=True)
        
        if st.button("🚀 ESCANEAR", type="primary"):
            target = batches[sel_batch]
            with st.spinner("Procesando..."):
                new_data = scan_batch(target)
                if accumulate: st.session_state['full_results_v91'].extend(new_data)
                else: st.session_state['full_results_v91'] = new_data
    
    if st.button("Limpiar"):
        st.session_state['full_results_v91'] = []
        st.rerun()
    
    st.divider()
    
    # --- FILTRO POR VEREDICTO (NUEVO) ---
    st.subheader("Filtros de Visualización")
    filter_opts = ["💎 ALL IN LONG", "☠️ ALL IN SHORT", "🟢 LONG", "🔴 SHORT", "ESPERAR"]
    selected_filters = st.multiselect("Mostrar solo:", filter_opts, default=filter_opts)

# ─────────────────────────────────────────────
# TABLA
# ─────────────────────────────────────────────
if st.session_state['full_results_v91']:
    df = pd.DataFrame(st.session_state['full_results_v91'])
    
    # Aplicar Filtro
    if selected_filters:
        df = df[df['VEREDICTO FINAL'].isin(selected_filters)]
    
    # Ordenar Columnas (Completo V7)
    cols_show = ['Activo', 'VEREDICTO FINAL', 'Estrategia HA', 'Recom. MACD', 'Precio']
    for tf in ["15m", "1H", "4H", "Diario", "Semanal"]:
        cols_show.extend([f"{tf} Estado", f"{tf} Hist", f"{tf} Cruce", f"{tf} Fecha"])
    
    final_cols = [c for c in cols_show if c in df.columns]
    
    def color_verdict(val):
        if "LONG" in str(val) or "COMPRA" in str(val) or "Alcista" in str(val): 
            return "background-color: #1b3a1b; color: #00ff00; font-weight: bold"
        if "SHORT" in str(val) or "VENTA" in str(val) or "Bajista" in str(val): 
            return "background-color: #3a1b1b; color: #ff0000; font-weight: bold"
        return ""

    # Aplicamos estilo a las 3 columnas de recomendación
    st.dataframe(
        df[final_cols].style.map(color_verdict, subset=['VEREDICTO FINAL', 'Estrategia HA', 'Recom. MACD']),
        column_config={
            "Activo": st.column_config.TextColumn(pinned=True),
            "VEREDICTO FINAL": st.column_config.TextColumn(width="medium"),
            "Precio": st.column_config.NumberColumn(format="$%.4f")
        },
        use_container_width=True,
        height=800
    )
else:
    st.info("👈 Escanea un lote para comenzar.")
