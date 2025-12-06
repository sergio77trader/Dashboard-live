import streamlit as st
import ccxt
import pandas as pd
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="SystemaTrader Monitor", layout="wide")

st.title("🦅 SYSTEMATRADER: LIVE MONITOR")
st.markdown("### Datos Institucionales | Fuente: Bybit Futures (Derivados)")

# --- FUNCIONES DE BACKEND (MOTOR BYBIT) ---
@st.cache_data(ttl=60)
def obtener_datos():
    # Inicializamos Bybit en modo Swap (Perpetuos)
    exchange = ccxt.bybit({
        'enableRateLimit': True,
        'options': {
            'defaultType': 'swap',  # Forzar contratos perpetuos
        }
    })
    
    my_bar = st.progress(0, text="Conectando a Bybit...")
    
    # 1. Cargar Mercados
    markets = exchange.load_markets()
    
    # 2. Obtener Tickers (Precios y Volumen 24h)
    tickers = exchange.fetch_tickers()
    
    data = []
    
    # Filtramos solo pares USDT que sean Perpetuos (Linear)
    for symbol, ticker in tickers.items():
        try:
            # La nomenclatura de Bybit suele ser BTC/USDT:USDT
            if '/USDT' in symbol and ticker['quoteVolume'] is not None:
                data.append({
                    'Symbol': symbol,
                    'Volumen (24h)': ticker['quoteVolume'], # Volumen en USDT
                    'Precio': ticker['last'],
                    'Cambio 24h %': ticker['percentage']
                })
        except:
            continue
    
    # Ordenar por volumen y tomar Top 10
    df = pd.DataFrame(data)
    df = df.sort_values(by='Volumen (24h)', ascending=False).head(10)
    top_symbols = df['Symbol'].tolist()
    
    my_bar.progress(50, text="Extrayendo Datos Forenses (OI & Funding)...")
    
    # 3. Extracción Profunda (OI + Funding)
    final_data = []
    for sym in top_symbols:
        try:
            # Open Interest
            # Bybit entrega el OI en el ticker o via fetch_open_interest
            oi_data = exchange.fetch_open_interest(sym)
            oi_value = oi_data['openInterestValue'] # Valor en USDT directo
            
            # Funding Rate
            funding_info = exchange.fetch_funding_rate(sym)
            funding = funding_info['fundingRate'] * 100
            
            # Limpiamos el nombre del simbolo (Quitar :USDT)
            clean_name = sym.split(':')[0]
            
            # Buscamos precio y volumen del paso anterior
            row_prev = df[df['Symbol'] == sym].iloc[0]
            
            final_data.append({
                'Ticker': clean_name,
                'Precio ($)': f"{row_prev['Precio']:,.4f}",
                'OI (Millones $)': f"${oi_value/1_000_000:,.2f}M",
                'Funding Rate (%)': f"{funding:+.4f}%",
                'Volumen 24h ($)': f"${row_prev['Volumen (24h)']/1_000_000:,.0f}M"
            })
            time.sleep(0.1) # Pequeña pausa para no saturar
        except Exception as e:
            # st.write(f"Error en {sym}: {e}") # Debug off
            continue
            
    my_bar.empty()
    return pd.DataFrame(final_data)

# --- INTERFAZ DE USUARIO ---
if st.button('🔄 ACTUALIZAR AHORA'):
    st.cache_data.clear()

try:
    df_final = obtener_datos()
    
    if not df_final.empty:
        # Métricas Rápidas (BTC)
        btc_row = df_final[df_final['Ticker'] == 'BTC/USDT']
        if not btc_row.empty:
            col1, col2, col3 = st.columns(3)
            col1.metric("BTC Precio", btc_row.iloc[0]['Precio ($)'])
            col2.metric("BTC Funding", btc_row.iloc[0]['Funding Rate (%)'])
            col3.metric("BTC Open Interest", btc_row.iloc[0]['OI (Millones $)'])

        # Tabla Principal
        st.subheader("Radar de Liquidez (Top 10 Bybit)")
        
        # Estilo visual para la tabla
        st.dataframe(df_final, use_container_width=True, hide_index=True)
    else:
        st.warning("No se pudieron cargar datos. Intenta recargar.")

except Exception as e:
    st.error(f"Error Crítico: {e}")
    st.info("Nota: Si persiste el error, Bybit también podría estar bloqueando la IP de Streamlit Cloud.")

st.caption("SystemaTrader Architecture v2.0 | Bypass Protocol Active")

except Exception as e:
    st.error(f"Error de conexión: {e}")

st.caption("SystemaTrader Architecture v1.0 | Serverless Deployment")
