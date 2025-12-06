import streamlit as st
import ccxt
import pandas as pd

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="SystemaTrader Monitor", layout="wide")
st.title("🦅 SYSTEMATRADER: LIVE MONITOR")
st.markdown("### Datos Institucionales | Fuente: KuCoin Futures")

# --- MOTOR DE DATOS (KUCOIN) ---
@st.cache_data(ttl=60)
def obtener_datos_kucoin():
    # Usamos KuCoin Futures (Suele permitir acceso desde servidores US)
    exchange = ccxt.kucoinfutures()
    
    try:
        # 1. Cargar Mercados
        exchange.load_markets()
        
        # 2. Obtener Tickers (Precios y Volumen)
        tickers = exchange.fetch_tickers()
        data = []
        
        # Barra de progreso
        my_bar = st.progress(0, text="Escaneando KuCoin Futures...")
        
        # Filtramos pares USDT
        for symbol, ticker in tickers.items():
            if '/USDT' in symbol:
                vol = ticker.get('quoteVolume')
                if vol is None:
                    vol = 0
                
                data.append({
                    'Symbol': symbol,
                    'Volumen': vol,
                    'Precio': ticker['last'],
                    'Cambio %': ticker['percentage']
                })
        
        # Top 10 por Volumen
        df = pd.DataFrame(data)
        df = df.sort_values(by='Volumen', ascending=False).head(10)
        top_symbols = df['Symbol'].tolist()
        
        my_bar.progress(50, text="Extrayendo Funding & Open Interest...")
        
        # 3. Datos Forenses
        final_data = []
        for sym in top_symbols:
            try:
                # Funding Rate
                funding_dict = exchange.fetch_funding_rate(sym)
                funding = funding_dict['fundingRate'] * 100
                
                # Open Interest (Intentamos obtenerlo, si falla ponemos N/A)
                # Nota: Algunas APIs limitan esto sin Key, pero probamos
                oi_str = "N/A"
                try:
                    oi_dict = exchange.fetch_open_interest(sym)
                    if oi_dict and 'openInterestValue' in oi_dict:
                         oi_val = float(oi_dict['openInterestValue'])
                         oi_str = f"${oi_val/1_000_000:,.2f}M"
                except:
                    pass

                # Recuperar datos previos
                row_prev = df[df['Symbol'] == sym].iloc[0]
                
                final_data.append({
                    'Ticker': sym,
                    'Precio ($)': f"{row_prev['Precio']:,.4f}",
                    'Funding Rate (%)': f"{funding:+.4f}%",
                    'Volumen 24h ($)': f"${row_prev['Volumen']/1_000_000:,.0f}M",
                    'Open Interest': oi_str
                })
                
            except Exception as e:
                continue
        
        my_bar.empty()
        return pd.DataFrame(final_data)

    except Exception as e:
        st.error(f"Error de conexión con el Exchange: {e}")
        return pd.DataFrame()

# --- INTERFAZ VISUAL ---
if st.button('🔄 ACTUALIZAR DATOS'):
    st.cache_data.clear()

# Ejecución Principal
df_resultado = obtener_datos_kucoin()

if not df_resultado.empty:
    # Métricas del Líder (Top 1)
    top_coin = df_resultado.iloc[0]
    col1, col2, col3 = st.columns(3)
    col1.metric(f"{top_coin['Ticker']} Precio", top_coin['Precio ($)'])
    col2.metric("Funding Rate", top_coin['Funding Rate (%)'])
    col3.metric("Volumen 24h", top_coin['Volumen 24h ($)'])
    
    st.subheader("Radar de Mercado (KuCoin Futures)")
    st.dataframe(df_resultado, use_container_width=True, hide_index=True)
else:
    st.warning("Esperando datos... Si esto persiste, intenta recargar la página.")

st.caption("SystemaTrader Architecture v3.0 | KuCoin Protocol")
