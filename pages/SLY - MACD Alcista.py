import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# Configuración
st.set_page_config(page_title="Scanner MACD Pro", layout="wide")
st.title("🔍 Escáner de Cruces MACD (Pisos Ascendentes)")

# Lista de Tickers sugeridos (puedes agregar más de tus 150 acciones)
tickers_default = ["AAPL", "MSFT", "NVDA", "PBR", "GGAL", "YPF", "KO", "TSLA", "MELI", "BBD", "VALE"]

st.sidebar.header("Configuración")
tickers_input = st.sidebar.text_area("Lista de Tickers (separados por coma):", value=",".join(tickers_default))
periodo = st.sidebar.selectbox("Periodo de análisis:", ["6mo", "1y", "2y"], index=0)

def analizar_macd(ticker):
    try:
        # Descargar datos
        df = yf.download(ticker, period=periodo, interval="1d", progress=False)
        if df.empty: return None

        # Calcular MACD (12, 26, 9)
        macd_data = ta.macd(df['Close'].squeeze(), fast=12, slow=26, signal=9)
        df = pd.concat([df, macd_data], axis=1)
        
        # Identificar cruces alcistas (MACD cruza por encima de Signal)
        # Condición: MACD hoy > Signal hoy Y MACD ayer <= Signal ayer
        macd_col = 'MACD_12_26_9'
        signal_col = 'MACDs_12_26_9'
        
        df['Cruce_Alcista'] = (df[macd_col] > df[signal_col]) & (df[macd_col].shift(1) <= df[signal_col].shift(1))
        
        # Obtener los registros donde hubo cruce
        cruces = df[df['Cruce_Alcista'] == True].copy()
        
        if len(cruces) >= 2:
            ultimo_cruce_val = cruces[macd_col].iloc[-1]
            penultimo_cruce_val = cruces[macd_col].iloc[-2]
            fecha_ultimo = cruces.index[-1].strftime('%Y-%m-%d')
            
            # Condición solicitada: Cruce actual más alto que el anterior
            cumple = ultimo_cruce_val > penultimo_cruce_val
            
            return {
                "Ticker": ticker,
                "Cumple": "SÍ" if cumple else "No",
                "Valor Cruce Actual": round(ultimo_cruce_val, 3),
                "Valor Cruce Anterior": round(penultimo_cruce_val, 3),
                "Fecha Último Cruce": fecha_ultimo,
                "Precio Actual": round(df['Close'].iloc[-1], 2)
            }
    except Exception as e:
        return None
    return None

# Ejecutar escáner
if st.button("🚀 Iniciar Escaneo"):
    lista_tickers = [t.strip().upper() for t in tickers_input.split(",")]
    resultados = []
    
    progress_bar = st.progress(0)
    for i, t in enumerate(lista_tickers):
        res = analizar_macd(t)
        if res:
            resultados.append(res)
        progress_bar.progress((i + 1) / len(lista_tickers))
    
    if resultados:
        df_res = pd.DataFrame(resultados)
        
        # Mostrar solo las que cumplen en una tabla destacada
        st.subheader("✅ Acciones con Momentum Ascendente")
        cumplen_df = df_res[df_res["Cumple"] == "SÍ"]
        
        if not cumplen_df.empty:
            st.dataframe(cumplen_df, use_container_width=True, hide_index=True)
            
            # Gráfico de ayuda para el primer ticker que cumple
            st.divider()
            st.subheader(f"Vista Técnica: {cumplen_df['Ticker'].iloc[0]}")
            ticker_plot = cumplen_df['Ticker'].iloc[0]
            data_plot = yf.download(ticker_plot, period="6mo", interval="1d")
            st.line_chart(data_plot['Close'])
            st.write(f"En {ticker_plot}, el MACD está cruzando en niveles de mayor confianza que la vez anterior.")
        else:
            st.warning("Ninguna acción de la lista cumple la condición de pisos ascendentes en el MACD actualmente.")
            
        st.subheader("📊 Todos los resultados")
        st.table(df_res)
    else:
        st.error("No se pudieron obtener datos. Verifica los tickers.")

st.info("""
**Nota:** El valor del cruce es el valor de la línea MACD en el momento del corte. 
Si el valor actual es mayor al anterior (ej: -0.5 es mayor a -1.2), significa que la tendencia bajista perdió fuerza o la alcista se aceleró.
""")
