import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# 1. Configuración de la App
st.set_page_config(page_title="Scanner MACD Multi-Timeframe", layout="wide")
st.title("🔍 Escáner MACD: Pisos Ascendentes")
st.write("Buscando cruces alcistas donde el momentum es superior al cruce anterior.")

# 2. Sidebar - Configuración de búsqueda
st.sidebar.header("Configuración")
# Tickers de ejemplo (puedes pegar tus 150 aquí)
tickers_sugeridos = "AAPL, MSFT, NVDA, PBR, BBD, ITUB, GGAL, YPFD, KO, TSLA, MELI, VALE, ALUA, TXAR"
tickers_input = st.sidebar.text_area("Lista de Tickers (separados por coma):", value=tickers_sugeridos)

# Selección de Temporalidad
temporalidad = st.sidebar.selectbox(
    "Selecciona la Temporalidad:",
    options=["Diario", "Semanal", "Mensual"],
    index=1  # Por defecto Semanal
)

# Mapeo de parámetros según temporalidad
config_time = {
    "Diario":  {"interval": "1d",  "period": "1y",   "label": "Días"},
    "Semanal": {"interval": "1wk", "period": "5y",   "label": "Semanas"},
    "Mensual": {"interval": "1mo", "period": "max",  "label": "Meses"}
}

conf = config_time[temporalidad]

# 3. Lógica de Cálculo
def analizar_ticker(ticker, interval, period):
    try:
        # Descarga de datos (ajustamos el periodo para tener suficiente historia)
        df = yf.download(ticker, period=period, interval=interval, progress=False)
        
        if df.empty or len(df) < 35: # Mínimo de velas para MACD
            return None

        # Limpiar datos multi-índice de yfinance si fuera necesario
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Calcular MACD (12, 26, 9)
        # macd = línea rápida, signal = línea lenta, hist = histograma
        macd_df = ta.macd(df['Close'], fast=12, slow=26, signal=9)
        df = pd.concat([df, macd_df], axis=1)
        
        macd_col = 'MACD_12_26_9'
        signal_col = 'MACDs_12_26_9'

        # Identificar Cruces Alcistas (MACD cruza por arriba de la Signal)
        df['Cruce_Alcista'] = (df[macd_col] > df[signal_col]) & (df[macd_col].shift(1) <= df[signal_col].shift(1))
        
        # Filtrar solo los puntos de cruce
        df_cruces = df[df['Cruce_Alcista'] == True].copy()
        
        if len(df_cruces) >= 2:
            ultimo_cruce = df_cruces.iloc[-1]
            penultimo_cruce = df_cruces.iloc[-2]
            
            val_actual = ultimo_cruce[macd_col]
            val_previo = penultimo_cruce[macd_col]
            
            # Condición: Cruce actual > Cruce anterior (Piso ascendente en el indicador)
            cumple = val_actual > val_previo
            
            return {
                "Ticker": ticker,
                "Estado": "✅ CUMPLE" if cumple else "❌ No cumple",
                "Valor Cruce Actual": round(val_actual, 4),
                "Valor Cruce Anterior": round(val_previo, 4),
                "Fecha Últ. Cruce": ultimo_cruce.name.strftime('%d/%m/%Y'),
                "Precio Actual": round(df['Close'].iloc[-1], 2)
            }
    except Exception as e:
        return None
    return None

# 4. Ejecución
if st.button(f"🚀 Escanear Mercado ({temporalidad})"):
    tickers = [t.strip().upper() for t in tickers_input.split(",")]
    resultados = []
    
    progreso = st.progress(0)
    for i, t in enumerate(tickers):
        res = analizar_ticker(t, conf['interval'], conf['period'])
        if res:
            resultados.append(res)
        progreso.progress((i + 1) / len(tickers))
    
    if resultados:
        df_final = pd.DataFrame(resultados)
        
        # Separar los que cumplen
        favoritos = df_final[df_final["Estado"] == "✅ CUMPLE"]
        
        st.subheader(f"📊 Resultados en Temporalidad {temporalidad}")
        
        if not favoritos.empty:
            st.success(f"Se encontraron {len(favoritos)} acciones con momentum ascendente.")
            st.dataframe(favoritos, use_container_width=True, hide_index=True)
            
            # Gráfico de ejemplo de la primera que cumple
            st.divider()
            t_ejemplo = favoritos['Ticker'].iloc[0]
            st.write(f"### Análisis Visual: {t_ejemplo}")
            data_plot = yf.download(t_ejemplo, period=conf['period'], interval=conf['interval'], progress=False)
            st.line_chart(data_plot['Close'])
        else:
            st.warning("No se encontraron acciones con pisos ascendentes en esta temporalidad.")
        
        with st.expander("Ver todos los activos analizados"):
            st.table(df_final)
    else:
        st.error("No se pudieron obtener datos. Revisa la conexión o los Tickers.")

# 5. Explicación Educativa
st.sidebar.divider()
st.sidebar.subheader("¿Qué estoy viendo?")
st.sidebar.write(f"""
Al elegir **{temporalidad}**, el escáner busca que la fuerza del mercado (MACD) 
esté haciendo 'pisos' más altos. 

**¿Por qué es importante?**
- En **Semanal/Mensual**, esto filtra el 'ruido' diario.
- Si el precio está lateral pero el cruce MACD es más alto, hay **acumulación institucional**.
""")
