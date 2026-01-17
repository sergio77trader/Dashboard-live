import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SystemaTrader: Sniper Matrix")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 14px; }
    .stProgress > div > div > div > div { background-color: #2962FF; }
</style>
""", unsafe_allow_html=True)

# --- GESTIÓN DE MEMORIA ---
if 'sniper_results' not in st.session_state:
    st.session_state['sniper_results'] = []

# --- TEMPORALIDADES SOLICITADAS ---
TIMEFRAMES = {
    '1m': '1m',
    '5m': '5m',
    '15m': '15m',
    '30m': '30m',
    '1H': '1h',
    '4H': '4h',
    '1D': '1d'
}

# --- CONEXIÓN KUCOIN ---
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

# --- LÓGICA DE ESTRATEGIA (REPLICA EXACTA PINE SCRIPT) ---
def calculate_heikin_ashi(df):
    df_ha = df.copy()
    df_ha['HA_Close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    
    # Cálculo iterativo de HA Open
    ha_open = [df['open'].iloc[0]]
    for i in range(1, len(df)):
        ha_open.append((ha_open[-1] + df_ha['HA_Close'].iloc[i-1]) / 2)
    
    df_ha['HA_Open'] = ha_open
    
    # 1=Verde, -1=Rojo
    df_ha['HA_Color'] = np.where(df_ha['HA_Close'] > df_ha['HA_Open'], 1, -1)
    return df_ha

def analyze_ticker_tf(symbol, tf_code, exchange):
    try:
        # Bajamos 300 velas para que la EMA 200 se calcule bien
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=300)
        if not ohlcv or len(ohlcv) < 200: return None
        
        df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
        df['dt'] = pd.to_datetime(df['time'], unit='ms')
        
        # 1. INDICADORES
        # EMA 200
        df['EMA200'] = ta.ema(df['close'], length=200)
        
        # MACD (12, 26, 9)
        macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
        df['Hist'] = macd['MACDh_12_26_9']
        
        # Heikin Ashi
        df = calculate_heikin_ashi(df)
        
        # 2. SIMULACIÓN DE ESTADO (State Machine)
        # Recorremos para ver el estado actual
        position = "NEUTRO"
        last_date = df['dt'].iloc[-1] # Por defecto
        
        # Optimizamos recorriendo solo las últimas 100 velas (ya con indicadores calculados)
        start_idx = 201 
        if len(df) <= start_idx: start_idx = 0
        
        for i in range(start_idx, len(df)):
            # Datos actuales
            close = df['close'].iloc[i]
            ema = df['EMA200'].iloc[i]
            hist = df['Hist'].iloc[i]
            prev_hist = df['Hist'].iloc[i-1]
            ha_color = df['HA_Color'].iloc[i]
            date = df['dt'].iloc[i]
            
            # Lógica de Gatillo
            ha_verde = (ha_color == 1)
            ha_rojo = (ha_color == -1)
            hist_subiendo = hist > prev_hist
            hist_bajando = hist < prev_hist
            
            # Filtros EMA
            f_ema_long = close > ema
            f_ema_short = close < ema
            
            # --- SALIDAS (Priority) ---
            if position == "LONG" and hist_bajando:
                position = "NEUTRO"
                last_date = date
            
            if position == "SHORT" and hist_subiendo:
                position = "NEUTRO"
                last_date = date
                
            # --- ENTRADAS ---
            if position == "NEUTRO":
                # Long: HA Verde + Hist Sube + Sobre EMA 200
                if ha_verde and hist_subiendo and f_ema_long:
                    position = "LONG"
                    last_date = date
                
                # Short: HA Rojo + Hist Baja + Bajo EMA 200
                elif ha_rojo and hist_bajando and f_ema_short:
                    position = "SHORT"
                    last_date = date
                    
        return position, last_date
        
    except Exception:
        return None

# --- PROCESAMIENTO ---
def scan_batch(targets):
    ex = get_exchange()
    results = []
    prog = st.progress(0, text="Escaneando temporalidades...")
    total = len(targets)
    
    for idx, sym in enumerate(targets):
        clean_name = sym.replace(':USDT', '').replace('/USDT', '')
        prog.progress(idx/total, text=f"Analizando {clean_name}...")
        
        row = {'Activo': clean_name}
        
        # Iteramos las 7 temporalidades
        for label, tf_code in TIMEFRAMES.items():
            res = analyze_ticker_tf(sym, tf_code, ex)
            
            if res:
                state, date_sig = res
                
                # Formateo visual
                icon = "⚪"
                if state == "LONG": icon = "🟢"
                elif state == "SHORT": icon = "🔴"
                
                # Formato de fecha corto
                date_str = date_sig.strftime('%d/%m %H:%M')
                
                # Guardamos string compuesto: "🟢 25/12 14:00"
                row[label] = f"{icon} {state} \n({date_str})"
            else:
                row[label] = "⚠️ Error/Data"
        
        results.append(row)
        time.sleep(0.1) # Breve pausa
        
    prog.empty()
    return results

# --- INTERFAZ ---
st.title("🎯 SystemaTrader: MNQ Sniper Matrix")
st.caption("Estrategia: Heikin Ashi + MACD + EMA200 (Filtrado por Tendencia)")

# Sidebar
with st.sidebar:
    st.header("Configuración")
    
    with st.spinner("Cargando mercado..."):
        all_symbols = get_active_pairs()
    
    if all_symbols:
        st.success(f"Mercado: {len(all_symbols)} activos")
        
        BATCH_SIZE = st.selectbox("Tamaño Lote:", [10, 20, 30], index=0)
        batches = [all_symbols[i:i + BATCH_SIZE] for i in range(0, len(all_symbols), BATCH_SIZE)]
        batch_labels = [f"Lote {i+1} ({b[0].split('/')[0]}...)" for i, b in enumerate(batches)]
        
        sel_batch = st.selectbox("Seleccionar Lote:", range(len(batches)), format_func=lambda x: batch_labels[x])
        accumulate = st.checkbox("Acumular Resultados", value=True)
        
        if st.button("🚀 ESCANEAR LOTE", type="primary"):
            targets = batches[sel_batch]
            with st.spinner("Calculando matrices... esto toma tiempo por la cantidad de TFs..."):
                new_data = scan_batch(targets)
                
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
    
    # Estilo visual
    st.dataframe(
        df,
        column_config={
            "Activo": st.column_config.TextColumn("Crypto", width="small", pinned=True),
            "1m": st.column_config.TextColumn("1 Min", width="medium"),
            "5m": st.column_config.TextColumn("5 Min", width="medium"),
            "15m": st.column_config.TextColumn("15 Min", width="medium"),
            "30m": st.column_config.TextColumn("30 Min", width="medium"),
            "1H": st.column_config.TextColumn("1 Hora", width="medium"),
            "4H": st.column_config.TextColumn("4 Horas", width="medium"),
            "1D": st.column_config.TextColumn("Diario", width="medium"),
        },
        use_container_width=True,
        height=700
    )
else:
    st.info("👈 Selecciona un lote. El escaneo analiza 7 temporalidades por cada moneda.")
