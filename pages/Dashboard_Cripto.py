import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import time
import numpy as np

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SystemaTrader - Deep Matrix")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 16px; }
    .stProgress > div > div > div > div { background-color: #00CC96; }
</style>
""", unsafe_allow_html=True)

# --- FACTORY DE CONEXIÓN ---
def get_exchange(name):
    opts = {'enableRateLimit': True, 'timeout': 30000}
    if name == 'Gate.io':
        return ccxt.gate(dict(opts, **{'options': {'defaultType': 'swap'}}))
    elif name == 'MEXC':
        return ccxt.mexc(dict(opts, **{'options': {'defaultType': 'swap'}}))
    elif name == 'KuCoin':
        return ccxt.kucoinfutures(opts)
    elif name == 'Binance': # Solo funcionará local, no en cloud
        return ccxt.binance(dict(opts, **{'options': {'defaultType': 'future'}}))
    return None

# --- FUNCIONES MATEMÁTICAS ---
def calculate_rsi(df, length=14):
    if df.empty or len(df) < length: return 50.0
    try:
        val = df.ta.rsi(length=length).iloc[-1]
        return float(val) if not pd.isna(val) else 50.0
    except: return 50.0

def get_change_pct(df):
    """Calcula cambio % de la última vela"""
    if df.empty: return 0.0
    try:
        # (Cierre - Apertura) / Apertura
        open_p = df['open'].iloc[-1]
        close_p = df['close'].iloc[-1]
        if open_p == 0: return 0.0
        return ((close_p - open_p) / open_p) * 100
    except: return 0.0

def get_volume_usd(df):
    """Calcula volumen en USD de la última vela"""
    if df.empty: return 0.0
    try:
        # En futuros, vol suele ser en moneda base, multiplicamos por cierre
        vol = df['vol'].iloc[-1]
        close = df['close'].iloc[-1]
        return vol * close
    except: return 0.0

@st.cache_data(ttl=600)
def get_targets(exchange_name, limit=10):
    """Obtiene Top monedas por volumen"""
    try:
        exchange = get_exchange(exchange_name)
        tickers = exchange.fetch_tickers()
        valid = []
        for s in tickers:
            if '/USDT' in s and tickers[s]['quoteVolume']:
                valid.append({'symbol': s, 'vol': tickers[s]['quoteVolume']})
        
        df = pd.DataFrame(valid).sort_values('vol', ascending=False).head(limit)
        return df['symbol'].tolist()
    except:
        return ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT', 'XRP/USDT:USDT', 'BNB/USDT:USDT']

def fetch_deep_data(symbols, exchange_name):
    exchange = get_exchange(exchange_name)
    data_rows = []
    
    # Definimos qué temporalidades necesitamos para qué cosa
    # Estructura: (Label Timeframe, CCXT Code, Calcular RSI?, Calcular Precio?, Calcular Volumen?)
    TASKS = [
        ('15m', '15m', True, False, False),  # Solo RSI
        ('1H',  '1h',  True, True,  True),   # RSI + Precio + Vol
        ('4H',  '4h',  True, True,  True),   # RSI + Precio + Vol
        ('12H', '12h', True, True,  False),  # RSI + Precio (Volumen 12h a veces falla en APIs)
        ('1D',  '1d',  True, True,  True),   # RSI + Precio + Vol
        ('1W',  '1w',  True, False, False)   # Solo RSI
    ]
    
    total_steps = len(symbols)
    bar = st.progress(0, text="Iniciando escaneo profundo...")
    
    for idx, symbol in enumerate(symbols):
        clean_name = symbol.split(':')[0]
        bar.progress((idx)/total_steps, text=f"Escaneando {clean_name} ({idx+1}/{total_steps})...")
        
        row = {'Activo': clean_name}
        
        # Iteramos sobre las temporalidades requeridas
        for label, tf, calc_rsi, calc_price, calc_vol in TASKS:
            try:
                # Descargamos solo las velas necesarias (30 son suficientes para RSI y precio actual)
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=30)
                df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','vol'])
                
                if calc_rsi:
                    row[f'RSI {label}'] = calculate_rsi(df)
                
                if calc_price:
                    row[f'Chg {label} %'] = get_change_pct(df)
                    # Guardamos precio actual solo una vez (usamos el de 1H)
                    if label == '1H':
                        row['Precio'] = df['close'].iloc[-1]
                
                if calc_vol:
                    row[f'Vol {label} ($)'] = get_volume_usd(df)
                    
            except Exception:
                # Si falla una temporalidad, rellenamos con 0 para no romper la tabla
                if calc_rsi: row[f'RSI {label}'] = 50.0
                if calc_price: row[f'Chg {label} %'] = 0.0
                if calc_vol: row[f'Vol {label} ($)'] = 0.0
                if label == '1H' and 'Precio' not in row: row['Precio'] = 0.0
        
        data_rows.append(row)
        # Pausa para evitar baneo
        time.sleep(0.1)
        
    bar.empty()
    return pd.DataFrame(data_rows)

# --- FRONTEND ---
st.title("🧩 SystemaTrader: Deep Matrix")
st.markdown("### Análisis Multi-Timeframe (Precio | Volumen | RSI)")

with st.sidebar:
    st.header("Motor de Datos")
    SOURCE = st.selectbox("Exchange:", ["Gate.io", "MEXC", "KuCoin", "Binance"])
    if SOURCE == "Binance":
        st.warning("⚠️ Binance probablemente fallará en la nube (Error 451). Úsalo solo en local.")
        
    LIMIT = st.slider("Cantidad de Activos:", 5, 20, 10)
    st.caption("Nota: Más activos = Más tiempo de carga (aprox 1s por activo).")
    
    if st.button("🔄 EJECUTAR ANÁLISIS", type="primary"):
        st.cache_data.clear()
        st.rerun()

# --- EJECUCIÓN ---
try:
    with st.spinner(f"Obteniendo Top {LIMIT} activos de {SOURCE}..."):
        targets = get_targets(SOURCE, LIMIT)
        
    if not targets:
        st.error("No se pudo conectar. Cambia de Exchange.")
    else:
        df = fetch_deep_data(targets, SOURCE)
        
        if not df.empty:
            # SANITIZACIÓN (Anti-Crash)
            df = df.fillna(0)
            df = df.replace([np.inf, -np.inf], 0)
            
            # --- TABLA DE PRECIOS Y CAMBIOS ---
            st.subheader("1. Estructura de Precio (%)")
            st.dataframe(
                df[['Activo', 'Precio', 'Chg 1H %', 'Chg 4H %', 'Chg 12H %', 'Chg 1D %']],
                column_config={
                    "Precio": st.column_config.NumberColumn(format="$%.4f"),
                    "Chg 1H %": st.column_config.NumberColumn(format="%.2f%%"),
                    "Chg 4H %": st.column_config.NumberColumn(format="%.2f%%"),
                    "Chg 12H %": st.column_config.NumberColumn(format="%.2f%%"),
                    "Chg 1D %": st.column_config.NumberColumn(format="%.2f%%"),
                },
                use_container_width=True, hide_index=True
            )
            
            st.divider()
            
            # --- TABLA DE RSI MULTI-TF ---
            st.subheader("2. Matriz de Momentum (RSI)")
            
            # Estilo condicional para RSI
            def color_rsi(val):
                color = 'white'
                if val >= 70: color = '#ff4b4b' # Rojo
                elif val <= 30: color = '#00cc96' # Verde
                return f'color: {color}; font-weight: bold'

            # Aplicamos estilo (Pandas Styler no siempre va bien en streamlit interactive, 
            # así que usamos visualización nativa con config)
            st.dataframe(
                df[['Activo', 'RSI 15m', 'RSI 1H', 'RSI 4H', 'RSI 12H', 'RSI 1D', 'RSI 1W']],
                column_config={
                    "RSI 15m": st.column_config.NumberColumn(format="%.1f"),
                    "RSI 1H": st.column_config.NumberColumn(format="%.1f"),
                    "RSI 4H": st.column_config.NumberColumn(format="%.1f"),
                    "RSI 12H": st.column_config.NumberColumn(format="%.1f"),
                    "RSI 1D": st.column_config.NumberColumn(format="%.1f"),
                    "RSI 1W": st.column_config.NumberColumn(format="%.1f"),
                },
                use_container_width=True, hide_index=True
            )
            st.caption("🔴 Sobrecompra (>70) | 🟢 Sobreventa (<30)")
            
            st.divider()
            
            # --- TABLA DE VOLUMEN ---
            st.subheader("3. Flujo de Volumen ($ USD)")
            st.dataframe(
                df[['Activo', 'Vol 1H ($)', 'Vol 4H ($)', 'Vol 1D ($)']],
                column_config={
                    "Vol 1H ($)": st.column_config.ProgressColumn(format="$%.0f", min_value=0, max_value=float(df['Vol 1H ($)'].max())),
                    "Vol 4H ($)": st.column_config.ProgressColumn(format="$%.0f", min_value=0, max_value=float(df['Vol 4H ($)'].max())),
                    "Vol 1D ($)": st.column_config.ProgressColumn(format="$%.0f", min_value=0, max_value=float(df['Vol 1D ($)'].max())),
                },
                use_container_width=True, hide_index=True
            )

        else:
            st.error("No llegaron datos.")

except Exception as e:
    st.error(f"Error de ejecución: {e}")
