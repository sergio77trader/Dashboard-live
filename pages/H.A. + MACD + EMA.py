import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime, timedelta

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SystemaTrader: MNQ Sniper Matrix")
st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 14px; }
    .stProgress > div > div > div > div { background-color: #2962FF; }
</style>
""", unsafe_allow_html=True)

# --- CONFIGURACIÓN DE TEMPORALIDADES Y CRIPTOS ---
symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']  # Ajustá tus cripto
timeframes = ['5m', '15m', '1h', '4h']
rsi_period = 14
macd_fast = 12
macd_slow = 26
macd_signal = 9

# --- INICIALIZAR API EXCHANGE ---
exchange = ccxt.binance({'enableRateLimit': True})

# --- FUNCIÓN PARA TRAER DATOS HISTÓRICOS ---
def fetch_ohlcv(symbol, timeframe, limit=100):
    data = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

# --- FUNCIÓN PARA CALCULAR RSI ---
def calculate_rsi(df, period):
    df['RSI'] = ta.rsi(df['close'], length=period)
    return df

# --- FUNCIÓN PARA CALCULAR MACD ---
def calculate_macd(df, fast, slow, signal):
    macd = ta.macd(df['close'], fast=fast, slow=slow, signal=signal)
    df['MACD'] = macd['MACD_12_26_9']
    df['MACD_signal'] = macd['MACDs_12_26_9']
    return df

# --- FUNCIÓN PARA CALCULAR HEIKIN-ASHI ---
def heikin_ashi(df):
    ha_df = df.copy()
    ha_df['HA_close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    ha_df['HA_open'] = ((df['open'].shift(1) + df['close'].shift(1)) / 2).fillna(df['open'])
    ha_df['HA_high'] = df[['high','HA_open','HA_close']].max(axis=1)
    ha_df['HA_low'] = df[['low','HA_open','HA_close']].min(axis=1)
    ha_df['HA_color'] = np.where(ha_df['HA_close'] > ha_df['HA_open'], 'verde', 'rojo')
    return ha_df

# --- CALCULAR SEÑALES POR CRIPTO Y TIMEFRAME ---
results = []

for symbol in symbols:
    symbol_data = {'Cripto': symbol}
    for tf in timeframes:
        df = fetch_ohlcv(symbol, tf)
        df = calculate_rsi(df, rsi_period)
        df = calculate_macd(df, macd_fast, macd_slow, macd_signal)
        df = heikin_ashi(df)
        
        # Últimos valores
        rsi_val = df['RSI'].iloc[-1]
        macd_val = df['MACD'].iloc[-1]
        macd_sig = df['MACD_signal'].iloc[-1]
        ha_color = df['HA_color'].iloc[-1]
        
        # Guardar en diccionario
        symbol_data[f'RSI_{tf}'] = rsi_val
        symbol_data[f'MACD_{tf}'] = macd_val
        symbol_data[f'MACD_signal_{tf}'] = macd_sig
        symbol_data[f'HA_{tf}'] = ha_color
        
    # --- LÓGICA DE ESTRATEGIA ---
    # Simple ejemplo con última temporalidad de 1h (podés cambiar)
    tf_check = '1h'
    macd_up = symbol_data[f'MACD_{tf_check}'] > symbol_data[f'MACD_signal_{tf_check}']
    rsi_up = symbol_data[f'RSI_{tf_check}'] > 50
    ha_green = symbol_data[f'HA_{tf_check}'] == 'verde'
    
    macd_down = symbol_data[f'MACD_{tf_check}'] < symbol_data[f'MACD_signal_{tf_check}']
    rsi_down = symbol_data[f'RSI_{tf_check}'] < 50
    ha_red = symbol_data[f'HA_{tf_check}'] == 'rojo'
    
    if macd_up and rsi_up and ha_green:
        strategy_signal = "Compra fuerte"
    elif macd_up or rsi_up:
        strategy_signal = "Compra"
    elif macd_down and rsi_down and ha_red:
        strategy_signal = "Vender fuerte"
    elif macd_down or rsi_down:
        strategy_signal = "Vender"
    else:
        strategy_signal = "Esperar"
        
    symbol_data['Estrategia'] = strategy_signal
    
    results.append(symbol_data)

# --- CREAR DATAFRAME Y TABLA ---
df_results = pd.DataFrame(results)

# --- RANKING OPCIONAL (ej. por RSI 1h) ---
df_results['Ranking'] = df_results['RSI_1h'].rank(ascending=False)

# --- MOSTRAR EN STREAMLIT ---
st.title("SystemaTrader: Sniper Matrix")
st.dataframe(df_results.style.background_gradient(subset=[col for col in df_results.columns if 'RSI' in col], cmap='RdYlGn'))
