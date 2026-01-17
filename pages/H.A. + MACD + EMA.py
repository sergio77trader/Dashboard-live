import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SystemaTrader: MNQ Sniper Matrix")
st.markdown("""<style>.stProgress > div > div > div > div { background-color: #2962FF; }</style>""", unsafe_allow_html=True)

if 'sniper_results' not in st.session_state:
    st.session_state['sniper_results'] = []

TIMEFRAMES = {
    '1m': '1m', '5m': '5m', '15m': '15m',
    '30m': '30m', '1H': '1h', '4H': '4h', '1D': '1d'
}

@st.cache_resource
def get_exchange():
    return ccxt.kucoinfutures({'enableRateLimit': True})

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

def analyze_ticker_tf(symbol, tf_code, exchange):
    try:
        # 1. Bajamos historial
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=100)
        if not ohlcv: return None
        
        # 2. TRUCO DE TIEMPO REAL: Obtener precio actual
        ticker = exchange.fetch_ticker(symbol)
        current_price = ticker['last']
        
        # 3. Reemplazar el cierre de la última vela con el precio actual
        # Esto simula lo que ves en TV (la vela moviéndose)
        ohlcv[-1][4] = current_price 
        
        df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
        df['dt'] = pd.to_datetime(df['time'], unit='ms')
        
        # 4. Calcular Indicadores con el precio actualizado
        macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
        df['Hist'] = macd['MACDh_12_26_9']
        df = calculate_heikin_ashi(df)
        
        # 5. Máquina de Estados
        position = "NEUTRO"
        last_date = df['dt'].iloc[-1]
        
        for i in range(1, len(df)):
            hist = df['Hist'].iloc[i]
            prev_hist = df['Hist'].iloc[i-1]
            ha_color = df['HA_Color'].iloc[i]
            date = df['dt'].iloc[i]
            
            # Señales Puras
            if position == "LONG" and hist < prev_hist:
                position = "NEUTRO"
                last_date = date
            elif position == "SHORT" and hist > prev_hist:
                position = "NEUTRO"
                last_date = date
            
            if position == "NEUTRO":
                if ha_color == 1 and hist > prev_hist:
                    position = "LONG"
                    last_date = date
                elif ha_color == -1 and hist < prev_hist:
                    position = "SHORT"
                    last_date = date
                    
        return position, last_date
        
    except Exception: return None

# --- BUCLE ---
def scan_batch(targets):
    ex = get_exchange()
    results = []
    prog = st.progress(0, text="Escaneando en vivo...")
    
    for idx, sym in enumerate(targets):
        clean_name = sym.replace(':USDT', '').replace('/USDT', '')
        prog.progress(idx/len(targets), text=f"Analizando {clean_name}...")
        
        row = {'Activo': clean_name}
        for label, tf_code in TIMEFRAMES.items():
            res = analyze_ticker_tf(sym, tf_code, ex)
            if res:
                state, date_sig = res
                icon = "🟢" if state == "LONG" else "🔴" if state == "SHORT" else "⚪"
                
                # Ajuste horario manual (-3h para Arg)
                # date_sig viene en UTC. Restamos 3 horas.
                date_arg = date_sig - pd.Timedelta(hours=3)
                
                date_str = date_arg.strftime('%H:%M') if date_arg.date() == datetime.now().date() else date_arg.strftime('%d/%m')
                row[label] = f"{icon} {state} ({date_str})"
            else:
                row[label] = "-"
        
        results.append(row)
        time.sleep(0.1) 
        
    prog.empty()
    return results

# --- INTERFAZ ---
st.title("🎯 SystemaTrader: MNQ Sniper (Real-Time Patch)")

with st.sidebar:
    if st.button("🚀 ESCANEAR LOTE", type="primary"):
        with st.spinner("Conectando..."):
            all_symbols = get_active_pairs()
            # Tomamos primeros 10 para probar rápido
            new_data = scan_batch(all_symbols[:10]) 
            st.session_state['sniper_results'] = new_data

if st.session_state['sniper_results']:
    st.dataframe(pd.DataFrame(st.session_state['sniper_results']), use_container_width=True)
