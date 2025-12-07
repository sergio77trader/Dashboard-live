import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import time

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SystemaTrader - Pro Dash")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 18px; }
</style>
""", unsafe_allow_html=True)

# --- FUNCIONES TÉCNICAS ---
def get_rsi(df, length=14):
    """Calcula RSI con manejo de errores"""
    if df.empty or len(df) < length: return 50
    try:
        rsi_series = df.ta.rsi(length=length)
        if rsi_series is None or rsi_series.empty: return 50
        return rsi_series.iloc[-1]
    except: return 50

@st.cache_data(ttl=600)
def get_top_pairs_kucoin():
    """Obtiene Top 15 pares de KuCoin Futures por volumen"""
    try:
        exchange = ccxt.kucoinfutures()
        markets = exchange.load_markets()
        tickers = exchange.fetch_tickers()
        
        valid = []
        for s in tickers:
            # Filtro: USDT, Activo y Swap
            if '/USDT:USDT' in s: 
                vol = tickers[s]['quoteVolume'] if tickers[s]['quoteVolume'] else 0
                valid.append({'symbol': s, 'volume': vol})
        
        # Ordenar y tomar Top 15
        df = pd.DataFrame(valid)
        df = df.sort_values('volume', ascending=False).head(15)
        return df['symbol'].tolist()
    except:
        # Fallback si falla la API
        return ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT', 'XRP/USDT:USDT', 'BNB/USDT:USDT', 'DOGE/USDT:USDT', 'PEPE/USDT:USDT']

def fetch_market_data(symbols):
    exchange = ccxt.kucoinfutures({
        'enableRateLimit': True, 
        'timeout': 30000
    })
    
    data_rows = []
    total = len(symbols)
    bar = st.progress(0, text="Extrayendo datos de KuCoin...")
    
    for i, symbol in enumerate(symbols):
        display_name = symbol.replace(':USDT', '').replace('/USDT', '')
        bar.progress((i)/total, text=f"Analizando {display_name}...")
        
        try:
            # 1. Velas para RSI (15m, 1h, 4h)
            # KuCoin es estricto, pedimos pocas velas
            k_15m = exchange.fetch_ohlcv(symbol, '15m', limit=30)
            rsi_15m = get_rsi(pd.DataFrame(k_15m, columns=['t','o','h','l','c','v']))
            
            k_1h = exchange.fetch_ohlcv(symbol, '1h', limit=30)
            df_1h = pd.DataFrame(k_1h, columns=['t','o','h','l','c','v'])
            rsi_1h = get_rsi(df_1h)
            price_now = df_1h['c'].iloc[-1]
            
            k_4h = exchange.fetch_ohlcv(symbol, '4h', limit=30)
            rsi_4h = get_rsi(pd.DataFrame(k_4h, columns=['t','o','h','l','c','v']))
            
            # 2. Datos Financieros (Funding & OI)
            funding_dict = exchange.fetch_funding_rate(symbol)
            funding_rate = funding_dict['fundingRate'] * 100
            
            # Open Interest
            # KuCoin a veces devuelve value directo, a veces contracts
            oi_dict = exchange.fetch_open_interest(symbol)
            oi_usd = 0
            if 'openInterestValue' in oi_dict:
                oi_usd = float(oi_dict['openInterestValue'])
            else:
                oi_usd = float(oi_dict['openInterest']) * price_now

            # Ticker para cambio 24h
            ticker_info = exchange.fetch_ticker(symbol)
            chg_24h = ticker_info['percentage']
            vol_24h = ticker_info['quoteVolume']

            row = {
                'Symbol': display_name,
                'Precio': price_now,
                'Chg 24h': chg_24h / 100 if abs(chg_24h) > 1 else chg_24h, # Normalizar a decimal
                'Volumen': vol_24h,
                'RSI 15m': rsi_15m,
                'RSI 1H': rsi_1h,
                'RSI 4H': rsi_4h,
                'Funding Rate': funding_rate,
                'Open Interest ($)': oi_usd
            }
            data_rows.append(row)
            
        except Exception:
            continue
            
    bar.empty()
    return pd.DataFrame(data_rows)

# --- FRONTEND ---
st.title("💠 SystemaTrader: Pro Dashboard")
st.markdown("### Inteligencia de Mercado (Motor KuCoin)")

if st.button("🔄 ACTUALIZAR MATRIZ", type="primary"):
    st.cache_data.clear()

# Ejecución
try:
    top_symbols = get_top_pairs_kucoin()
    df = fetch_market_data(top_symbols)

    if not df.empty:
        # Coloreado condicional de RSI
        st.dataframe(
            df,
            column_config={
                "Symbol": st.column_config.TextColumn("Crypto", width="small"),
                "Precio": st.column_config.NumberColumn("Precio", format="$%.4f"),
                "Chg 24h": st.column_config.NumberColumn("Cambio 24h", format="%.2f%%"),
                "Volumen": st.column_config.ProgressColumn("Volumen", format="$%.0f", min_value=0, max_value=df['Volumen'].max()),
                "RSI 15m": st.column_config.NumberColumn("RSI 15m", format="%.1f"),
                "RSI 1H": st.column_config.NumberColumn("RSI 1H", format="%.1f"),
                "RSI 4H": st.column_config.NumberColumn("RSI 4H", format="%.1f"),
                "Funding Rate": st.column_config.NumberColumn("Funding", format="%.4f%%"),
                "Open Interest ($)": st.column_config.NumberColumn("OI ($)", format="$%.0f")
            },
            use_container_width=True,
            hide_index=True,
            height=700
        )
        
        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.info("💡 **RSI:** >70 Sobrecompra | <30 Sobreventa")
        c2.warning("⚡ **Funding:** Negativo = Posible Short Squeeze")
        c3.success("💰 **Open Interest:** Dinero real en juego")
        
    else:
        st.error("Error conectando con KuCoin. Intenta recargar.")

except Exception as e:
    st.error(f"Error Crítico: {e}")
