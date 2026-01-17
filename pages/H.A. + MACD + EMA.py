import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime, timedelta

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

# --- TEMPORALIDADES (7 NIVELES) ---
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
        # Ordenamos por volumen para traer lo más líquido primero
        return pd.DataFrame(valid).sort_values('vol', ascending=False)['symbol'].tolist()
    except: return []

# --- LÓGICA DE TRADING ---
def calculate_heikin_ashi(df):
    df_ha = df.copy()
    df_ha['HA_Close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    ha_open = [df['open'].iloc[0]]
    for i in range(1, len(df)):
        ha_open.append((ha_open[-1] + df_ha['HA_Close'].iloc[i-1]) / 2)
    df_ha['HA_Open'] = ha_open
    df_ha['HA_Color'] = np.where(df_ha['HA_Close'] > df_ha['HA_Open'], 1, -1)
    return df_ha

def analyze_ticker_tf(symbol, tf_code, exchange, current_price):
    try:
        # 1. Bajamos historial (100 velas es suficiente y rápido)
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=100)
        if not ohlcv or len(ohlcv) < 50: return None
        
        # 2. PARCHE DE TIEMPO REAL: Forzamos el precio actual en la última vela
        ohlcv[-1][4] = current_price 
        
        df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
        df['dt'] = pd.to_datetime(df['time'], unit='ms')
        
        # 3. Indicadores
        macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
        df['Hist'] = macd['MACDh_12_26_9']
        df = calculate_heikin_ashi(df)
        
        # 4. Máquina de Estados
        position = "NEUTRO"
        last_date = df['dt'].iloc[-1]
        
        for i in range(1, len(df)):
            hist = df['Hist'].iloc[i]
            prev_hist = df['Hist'].iloc[i-1]
            ha_color = df['HA_Color'].iloc[i]
            date = df['dt'].iloc[i]
            
            # Salidas
            if position == "LONG" and hist < prev_hist:
                position = "NEUTRO"
                last_date = date
            elif position == "SHORT" and hist > prev_hist:
                position = "NEUTRO"
                last_date = date
            
            # Entradas
            if position == "NEUTRO":
                if ha_color == 1 and hist > prev_hist:
                    position = "LONG"
                    last_date = date
                elif ha_color == -1 and hist < prev_hist:
                    position = "SHORT"
                    last_date = date
                    
        return position, last_date
        
    except Exception: return None

# --- GENERADOR DE RECOMENDACIÓN ---
def get_recommendation(row_data):
    # Contamos cuántos LONG y SHORT hay en las columnas de TFs
    longs = 0
    shorts = 0
    
    # Pesos (Temporalidades más altas valen más para la tendencia)
    # 1m, 5m, 15m, 30m, 1h, 4h, 1d
    
    # Analizamos los valores crudos guardados en el dict
    for k, v in row_data.items():
        if k in TIMEFRAMES:
            if "LONG" in v: longs += 1
            if "SHORT" in v: shorts += 1
            
    # Lógica de Diagnóstico
    if longs >= 5: return "🔥 COMPRA FUERTE"
    if shorts >= 5: return "🩸 VENTA FUERTE"
    
    # Divergencias (Scalping)
    # Si 1m/5m/15m son contrarios a 4h/1d
    short_tf_bull = "LONG" in row_data.get('1m', '') and "LONG" in row_data.get('5m', '')
    long_tf_bear = "SHORT" in row_data.get('4H', '') or "SHORT" in row_data.get('1D', '')
    
    if short_tf_bull and long_tf_bear: return "⚠️ REBOTE (Scalp)"
    
    short_tf_bear = "SHORT" in row_data.get('1m', '') and "SHORT" in row_data.get('5m', '')
    long_tf_bull = "LONG" in row_data.get('4H', '') or "LONG" in row_data.get('1D', '')
    
    if short_tf_bear and long_tf_bull: return "📉 DIP (Posible Entrada)"
    
    return "⚖️ RANGO / ESPERAR"

# --- BUCLE PRINCIPAL ---
def scan_batch(targets):
    ex = get_exchange()
    results = []
    prog = st.progress(0, text="Iniciando radar...")
    
    for idx, sym in enumerate(targets):
        clean_name = sym.replace(':USDT', '').replace('/USDT', '')
        prog.progress(idx/len(targets), text=f"Analizando {clean_name} ({idx+1}/{len(targets)})...")
        
        row = {'Activo': clean_name}
        
        # Obtenemos el precio actual UNA VEZ para todas las temporalidades (Optimización)
        try:
            ticker_info = ex.fetch_ticker(sym)
            current_price = ticker_info['last']
        except:
            current_price = 0
            
        if current_price > 0:
            for label, tf_code in TIMEFRAMES.items():
                res = analyze_ticker_tf(sym, tf_code, ex, current_price)
                if res:
                    state, date_sig = res
                    icon = "🟢" if state == "LONG" else "🔴" if state == "SHORT" else "⚪"
                    
                    # Ajuste Horario (-3h Argentina)
                    date_arg = date_sig - pd.Timedelta(hours=3)
                    # Formato COMPLETO solicitado
                    date_str = date_arg.strftime('%d/%m %H:%M')
                    
                    row[label] = f"{icon} {state} \n({date_str})"
                else:
                    row[label] = "-"
            
            # Generar Recomendación Final
            row['Estrategia'] = get_recommendation(row)
            results.append(row)
        
        time.sleep(0.1) # Breve respiro
        
    prog.empty()
    return results

# --- INTERFAZ ---
st.title("🎯 SystemaTrader: MNQ Sniper (Matrix V4)")
st.caption("Heikin Ashi + MACD | Análisis Multi-Temporal en Tiempo Real")

with st.sidebar:
    st.header("Configuración")
    
    with st.spinner("Cargando mercado..."):
        all_symbols = get_active_pairs()
    
    if all_symbols:
        st.success(f"Mercado: {len(all_symbols)} activos")
        st.divider()
        
        # Selector de Lote (Max 50)
        BATCH_SIZE = st.selectbox("Tamaño Lote:", [10, 20, 30, 50], index=1)
        batches = [all_symbols[i:i + BATCH_SIZE] for i in range(0, len(all_symbols), BATCH_SIZE)]
        batch_opts = [f"Lote {i+1} ({b[0].split('/')[0]}...)" for i, b in enumerate(batches)]
        sel_batch = st.selectbox("Seleccionar Lote:", range(len(batches)), format_func=lambda x: batch_opts[x])
        
        accumulate = st.checkbox("Acumular Resultados", value=True)
        
        if st.button("🚀 ESCANEAR LOTE", type="primary"):
            target = batches[sel_batch]
            with st.spinner("Procesando matriz fractal..."):
                new_data = scan_batch(target)
                
                if new_data:
                    if accumulate:
                        existing = {x['Activo'] for x in st.session_state['sniper_results']}
                        for item in new_data:
                            if item['Activo'] not in existing:
                                st.session_state['sniper_results'].append(item)
                    else:
                        st.session_state['sniper_results'] = new_data
    else:
        st.error("Error de conexión.")
        
    if st.button("Limpiar"):
        st.session_state['sniper_results'] = []
        st.rerun()

# --- TABLA ---
if st.session_state['sniper_results']:
    df = pd.DataFrame(st.session_state['sniper_results'])
    
    # Colorear la recomendación
    def style_reco(val):
        if "COMPRA FUERTE" in str(val): return "color: #00FF00; font-weight: bold; background-color: rgba(0,255,0,0.1)"
        if "VENTA FUERTE" in str(val): return "color: #FF0000; font-weight: bold; background-color: rgba(255,0,0,0.1)"
        if "DIP" in str(val): return "color: #00FFFF; font-weight: bold" # Cyan
        if "REBOTE" in str(val): return "color: #FFA500; font-weight: bold" # Naranja
        return "color: #888"

    st.dataframe(
        df.style.map(style_reco, subset=['Estrategia']),
        column_config={
            "Activo": st.column_config.TextColumn("Crypto", width="small", pinned=True),
            "Estrategia": st.column_config.TextColumn("Diagnóstico IA", width="medium"), # Nueva columna al principio
            "1m": st.column_config.TextColumn("1 Min", width="medium"),
            "5m": st.column_config.TextColumn("5 Min", width="medium"),
            "15m": st.column_config.TextColumn("15 Min", width="medium"),
            "30m": st.column_config.TextColumn("30 Min", width="medium"),
            "1H": st.column_config.TextColumn("1 Hora", width="medium"),
            "4H": st.column_config.TextColumn("4 Horas", width="medium"),
            "1D": st.column_config.TextColumn("Diario", width="medium"),
        },
        use_container_width=True,
        height=800
    )
else:
    st.info("👈 Selecciona un lote. Escaneo profundo de 7 temporalidades.")
