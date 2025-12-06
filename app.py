import streamlit as st
import ccxt
import pandas as pd

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="SystemaTrader Monitor", layout="wide")

st.title("🦅 SYSTEMATRADER: LIVE MONITOR")
st.markdown("### Datos Institucionales | Fuente: Binance Futures")

# --- FUNCIONES DE BACKEND ---
@st.cache_data(ttl=60) # Cache para no saturar la API (actualiza cada 60seg)
def obtener_datos():
    exchange = ccxt.binanceusdm({'enableRateLimit': True})
    
    # Buscamos Top Monedas por Volumen
    tickers = exchange.fetch_tickers()
    data = []
    
    # Barra de progreso visual
    my_bar = st.progress(0, text="Escaneando mercado...")
    
    for symbol, ticker in tickers.items():
        if '/USDT' in symbol and 'PERP' not in symbol:
            data.append({
                'Symbol': symbol,
                'Volumen (24h)': ticker['quoteVolume'],
                'Precio': ticker['last'],
                'Cambio 24h %': ticker['percentage']
            })
    
    df = pd.DataFrame(data)
    df = df.sort_values(by='Volumen (24h)', ascending=False).head(10) # Top 10
    top_symbols = df['Symbol'].tolist()
    
    my_bar.progress(50, text="Extrayendo Datos Forenses (OI & Funding)...")
    
    # Extracción Profunda
    final_data = []
    for sym in top_symbols:
        try:
            # Open Interest
            ticker_data = exchange.fetch_ticker(sym)
            oi_contracts = ticker_data.get('openInterest', 0)
            price = ticker_data.get('last', 0)
            oi_usdt = oi_contracts * price
            
            # Funding
            funding_info = exchange.fetch_funding_rate(sym)
            funding = funding_info['fundingRate'] * 100
            
            final_data.append({
                'Ticker': sym,
                'Precio ($)': f"{price:,.4f}",
                'OI (Millones $)': f"${oi_usdt/1_000_000:,.2f}M",
                'Funding Rate (%)': f"{funding:+.4f}%",
                'Volumen 24h ($)': f"${ticker_data['quoteVolume']/1_000_000:,.0f}M"
            })
        except:
            continue
            
    my_bar.empty() # Limpiar barra
    return pd.DataFrame(final_data)

# --- INTERFAZ DE USUARIO ---
if st.button('🔄 ACTUALIZAR AHORA'):
    st.cache_data.clear() # Forzar recarga

try:
    df_final = obtener_datos()
    
    # Métricas Rápidas (Ejemplo con BTC si está en la lista)
    btc_row = df_final[df_final['Ticker'] == 'BTC/USDT']
    if not btc_row.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("BTC Precio", btc_row.iloc[0]['Precio ($)'])
        col2.metric("BTC Funding", btc_row.iloc[0]['Funding Rate (%)'])
        col3.metric("BTC Open Interest", btc_row.iloc[0]['OI (Millones $)'])

    # Tabla Principal
    st.subheader("Radar de Liquidez (Top 10)")
    st.table(df_final)

except Exception as e:
    st.error(f"Error de conexión: {e}")

st.caption("SystemaTrader Architecture v1.0 | Serverless Deployment")
