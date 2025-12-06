import streamlit as st
import ccxt
import pandas as pd

# --- CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="SystemaTrader Monitor", layout="wide")
st.title("🦅 SYSTEMATRADER: LIVE MONITOR")
st.markdown("### Datos Institucionales | Fuente: Gate.io Futures")

# --- MOTOR DE DATOS (GATE.IO) ---
@st.cache_data(ttl=60)
def obtener_datos_gate():
    # Inicializamos Gate.io en modo Swap (Perpetuos)
    exchange = ccxt.gate({
        'enableRateLimit': True,
        'options': {
            'defaultType': 'swap', 
        }
    })
    
    try:
        # 1. Cargar Mercados
        exchange.load_markets()
        
        # 2. Obtener todos los Tickers
        tickers = exchange.fetch_tickers()
        data_preliminar = []
        
        my_bar = st.progress(0, text="Escaneando Gate.io...")
        
        # Filtramos pares USDT
        for symbol, ticker in tickers.items():
            # Buscamos solo pares USDT (Swap)
            if '/USDT:USDT' in symbol:
                vol = ticker.get('quoteVolume')
                if vol is None: vol = 0
                
                data_preliminar.append({
                    'Symbol': symbol,
                    'Volumen': vol,
                    'Precio': ticker['last'],
                    'Cambio %': ticker['percentage']
                })
        
        # Ordenamos por Volumen (Top 10)
        df = pd.DataFrame(data_preliminar)
        df = df.sort_values(by='Volumen', ascending=False).head(10)
        top_symbols = df['Symbol'].tolist()
        
        my_bar.progress(50, text="Extrayendo Funding & Open Interest...")
        
        # 3. Extracción Forense (Loop detallado)
        datos_finales = []
        
        for sym in top_symbols:
            try:
                # Funding Rate
                funding_dict = exchange.fetch_funding_rate(sym)
                funding = funding_dict['fundingRate'] * 100
                
                # Open Interest (Gate suele entregarlo en Valor USD directamente o contratos)
                oi_dict = exchange.fetch_open_interest(sym)
                
                # Intentamos sacar el valor en USD
                oi_usd = 0
                if 'openInterestValue' in oi_dict and oi_dict['openInterestValue'] is not None:
                     oi_usd = float(oi_dict['openInterestValue'])
                else:
                    # Cálculo manual si falta el valor directo
                    oi_contracts = float(oi_dict.get('openInterest', 0))
                    precio = float(oi_dict.get('info', {}).get('last', 0)) # O usar precio actual
                    if precio == 0: precio = funding_dict.get('info', {}).get('last_price', 0)
                    oi_usd = oi_contracts * float(precio)

                # Limpieza de nombre (BTC/USDT:USDT -> BTC)
                nombre_limpio = sym.split('/')[0]
                
                # Recuperar datos previos
                row_prev = df[df['Symbol'] == sym].iloc[0]
                
                datos_finales.append({
                    'Ticker': nombre_limpio,
                    'Precio ($)': f"{row_prev['Precio']:,.4f}",
                    'Funding Rate (%)': f"{funding:+.4f}%",
                    'Open Interest ($)': f"${oi_usd/1_000_000:,.2f}M",
                    'Volumen 24h ($)': f"${row_prev['Volumen']/1_000_000:,.0f}M"
                })
                
            except Exception as e:
                # Si falla una moneda, saltamos a la siguiente sin romper todo
                continue
        
        my_bar.empty()
        return pd.DataFrame(datos_finales)

    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return pd.DataFrame()

# --- INTERFAZ ---
if st.button('🔄 ACTUALIZAR'):
    st.cache_data.clear()

df_resultado = obtener_datos_gate()

if not df_resultado.empty:
    # Métricas Top 1
    top = df_resultado.iloc[0]
    c1, c2, c3 = st.columns(3)
    c1.metric("Líder", top['Ticker'])
    c2.metric("Precio", top['Precio ($)'])
    c3.metric("Funding", top['Funding Rate (%)'])
    
    st.subheader("Radar Institucional (Gate.io)")
    st.dataframe(df_resultado, use_container_width=True, hide_index=True)
else:
    st.warning("No se recibieron datos. Intenta recargar.")

st.caption("SystemaTrader Architecture v4.0 | Gate.io Protocol")
