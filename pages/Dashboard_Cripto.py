import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import time
import numpy as np

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SystemaTrader - Pro Dashboard")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 18px; }
    .stProgress > div > div > div > div { background-color: #00CC96; }
</style>
""", unsafe_allow_html=True)

# --- FUNCIONES TÉCNICAS ---
def get_rsi(df, length=14):
    """Calcula RSI seguro, evitando NaNs"""
    if df.empty or len(df) < length: return 50.0
    try:
        rsi_series = df.ta.rsi(length=length)
        if rsi_series is None or rsi_series.empty: return 50.0
        
        val = rsi_series.iloc[-1]
        # Si el valor es NaN (Not a Number), devolvemos 50 (Neutro)
        if pd.isna(val) or np.isinf(val): return 50.0
        return float(val)
    except: return 50.0

# --- FACTORY DE CONEXIÓN ---
def get_exchange(name):
    opts = {'enableRateLimit': True, 'timeout': 30000}
    if name == 'Gate.io':
        return ccxt.gate(dict(opts, **{'options': {'defaultType': 'swap'}}))
    elif name == 'MEXC':
        return ccxt.mexc(dict(opts, **{'options': {'defaultType': 'swap'}}))
    elif name == 'KuCoin':
        return ccxt.kucoinfutures(opts)
    return None

@st.cache_data(ttl=300)
def get_top_pairs(exchange_name):
    try:
        exchange = get_exchange(exchange_name)
        markets = exchange.load_markets()
        tickers = exchange.fetch_tickers()
        valid = []
        
        for s in tickers:
            # Filtro defensivo
            if '/USDT' in s:
                vol = tickers[s].get('quoteVolume', 0)
                if vol is None: vol = 0
                valid.append({'symbol': s, 'volume': vol})
        
        df = pd.DataFrame(valid)
        if df.empty: return []
        
        df = df.sort_values('volume', ascending=False).head(15)
        return df['symbol'].tolist()
    except:
        return ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT', 'BNB/USDT:USDT', 'XRP/USDT:USDT']

def fetch_data(symbols, exchange_name):
    exchange = get_exchange(exchange_name)
    data_rows = []
    total = len(symbols)
    bar = st.progress(0, text=f"Leyendo datos de {exchange_name}...")
    
    for i, symbol in enumerate(symbols):
        display = symbol.split(':')[0]
        bar.progress((i)/total, text=f"Analizando {display}...")
        
        try:
            # 1. Velas RSI
            k_15m = exchange.fetch_ohlcv(symbol, '15m', limit=30)
            rsi_15m = get_rsi(pd.DataFrame(k_15m, columns=['t','o','h','l','c','v']))
            
            k_1h = exchange.fetch_ohlcv(symbol, '1h', limit=30)
            df_1h = pd.DataFrame(k_1h, columns=['t','o','h','l','c','v'])
            rsi_1h = get_rsi(df_1h)
            
            # Obtener precio de forma segura
            price_now = 0.0
            if not df_1h.empty:
                price_now = float(df_1h['c'].iloc[-1])
            
            k_4h = exchange.fetch_ohlcv(symbol, '4h', limit=30)
            rsi_4h = get_rsi(pd.DataFrame(k_4h, columns=['t','o','h','l','c','v']))
            
            # 2. Funding
            funding = 0.0
            try:
                f_data = exchange.fetch_funding_rate(symbol)
                if f_data and 'fundingRate' in f_data and f_data['fundingRate'] is not None:
                    funding = float(f_data['fundingRate']) * 100
            except: pass
            
            # 3. OI
            oi_usd = 0.0
            try:
                oi = exchange.fetch_open_interest(symbol)
                if 'openInterestValue' in oi and oi['openInterestValue']:
                    oi_usd = float(oi['openInterestValue'])
                elif 'openInterestAmount' in oi and oi['openInterestAmount']:
                     oi_usd = float(oi['openInterestAmount']) * price_now
                elif 'openInterest' in oi and oi['openInterest']:
                     oi_usd = float(oi['openInterest']) * price_now
            except: pass

            # 4. Cambio 24h
            chg = 0.0
            vol = 0.0
            try:
                tick = exchange.fetch_ticker(symbol)
                if tick:
                    chg = float(tick.get('percentage', 0) or 0)
                    vol = float(tick.get('quoteVolume', 0) or 0)
                    if abs(chg) < 1: chg = chg * 100 
            except: pass

            row = {
                'Symbol': display,
                'Precio': price_now,
                'Chg 24h': chg / 100,
                'Volumen': vol,
                'RSI 15m': rsi_15m,
                'RSI 1H': rsi_1h,
                'RSI 4H': rsi_4h,
                'Funding': funding / 100,
                'OI ($)': oi_usd
            }
            data_rows.append(row)
            
        except Exception:
            continue
            
    bar.empty()
    return pd.DataFrame(data_rows)

# --- INTERFAZ ---
st.title("💠 SystemaTrader: Pro Dashboard")

with st.sidebar:
    st.header("Fuente de Datos")
    # KuCoin suele ser bueno, pero si falla prueba Gate.io
    SOURCE = st.selectbox("Exchange:", ["KuCoin", "Gate.io", "MEXC"])
    
    if st.button("🔄 RECARGAR", type="primary"):
        st.cache_data.clear()
        st.rerun()

    st.info(f"Conectado a: **{SOURCE}**")

try:
    with st.spinner(f"Conectando satélite a {SOURCE}..."):
        top_symbols = get_top_pairs(SOURCE)
        
    if not top_symbols:
        st.error(f"Error conectando a {SOURCE}. Prueba cambiar a Gate.io o MEXC en el menú.")
    else:
        df = fetch_data(top_symbols, SOURCE)

        if not df.empty:
            # --- LIMPIEZA CRÍTICA (SANITIZACIÓN) ---
            # Esto evita el error "Out of range float / nan"
            # Reemplazamos cualquier NaN o Infinito por 0
            df = df.fillna(0)
            df = df.replace([np.inf, -np.inf], 0)

            st.dataframe(
                df,
                column_config={
                    "Symbol": st.column_config.TextColumn("Activo", width="small"),
                    "Precio": st.column_config.NumberColumn("Precio", format="$%.4f"),
                    "Chg 24h": st.column_config.NumberColumn("24h %", format="%.2f%%"),
                    "Volumen": st.column_config.ProgressColumn("Volumen", format="$%.0f", min_value=0, max_value=float(df['Volumen'].max())),
                    "RSI 15m": st.column_config.NumberColumn("RSI 15m", format="%.0f"),
                    "RSI 1H": st.column_config.NumberColumn("RSI 1H", format="%.0f"),
                    "RSI 4H": st.column_config.NumberColumn("RSI 4H", format="%.0f"),
                    "Funding": st.column_config.NumberColumn("Funding", format="%.4f%%"),
                    "OI ($)": st.column_config.NumberColumn("Open Int. ($)", format="$%.0f")
                },
                use_container_width=True,
                hide_index=True,
                height=750
            )
            
            c1, c2, c3 = st.columns(3)
            c1.info("💡 **RSI:** >70 (Sobrecompra) | <30 (Sobreventa)")
            c2.warning("⚡ **Funding:** Negativo = Posible Short Squeeze")
            c3.success(f"📡 Fuente: {SOURCE}")
            
        else:
            st.error("No llegaron datos válidos. Intenta recargar.")

except Exception as e:
    st.error(f"Error del Sistema: {e}")
