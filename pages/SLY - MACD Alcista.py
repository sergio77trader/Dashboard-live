import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from datetime import datetime

# 1. CONFIGURACIÓN DE LA APP
st.set_page_config(page_title="Escáner MACD Pro - 150 Activos", layout="wide")

st.title("🔍 Escáner de Momentum: Cruces MACD Ascendentes")
st.write("Analizando cambios de tendencia de alta convicción en temporalidades largas.")

# 2. LISTA MAESTRA DE TICKERS
MASTER_TICKERS = sorted([
    'GGAL', 'YPF', 'BMA', 'PAMP', 'TGS', 'CEPU', 'EDN', 'BFR', 'SUPV', 'CRESY', 'IRS', 'TEO', 'LOMA', 'DESP', 'VIST', 'GLOB', 'MELI', 'BIOX', 'TX',
    'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NFLX', 'CRM', 'ORCL', 'ADBE', 'IBM', 'CSCO', 'PLTR', 'SNOW', 'SHOP', 'SPOT', 'UBER', 'ABNB', 'AMD', 'INTC', 'QCOM', 'AVGO', 'TXN', 'MU', 'ADI', 'AMAT', 'ARM', 'SMCI', 'TSM', 'ASML', 'LRCX',
    'JPM', 'BAC', 'C', 'WFC', 'GS', 'MS', 'V', 'MA', 'AXP', 'BRK-B', 'PYPL', 'SQ', 'COIN', 'BLK', 'USB', 'NU', 'KO', 'PEP', 'MCD', 'SBUX', 'DIS', 'NKE', 'WMT', 'COST', 'TGT', 'HD', 'LOW', 'PG', 'CL', 'MO', 'PM', 'KMB', 'EL',
    'JNJ', 'PFE', 'MRK', 'LLY', 'ABBV', 'UNH', 'BMY', 'AMGN', 'GILD', 'AZN', 'NVO', 'NVS', 'CVS', 'BA', 'CAT', 'DE', 'GE', 'MMM', 'LMT', 'RTX', 'HON', 'UNP', 'UPS', 'FDX', 'XOM', 'CVX', 'SLB', 'OXY', 'HAL', 'BP', 'SHEL', 'TTE', 'PBR', 'VLO', 'VALE', 'ITUB', 'BBD', 'ERJ', 'ABEV', 'GGB', 'SID', 'NBR', 'GOLD', 'NEM', 'PAAS', 'FCX', 'SCCO', 'RIO', 'BHP', 'ALB', 'SQM',
    'SPY', 'QQQ', 'IWM', 'DIA', 'EEM', 'EWZ', 'FXI', 'XLE', 'XLF', 'XLK', 'XLV', 'XLI', 'XLP', 'XLU', 'XLY', 'ARKK', 'SMH', 'TAN', 'GLD', 'SLV', 'GDX'
])

# 3. SIDEBAR - CONTROLES
st.sidebar.header("Parámetros del Escáner")
temp = st.sidebar.radio("Selecciona Temporalidad:", ["Semanal", "Mensual"])

# Ajuste de configuración según temporalidad
if temp == "Semanal":
    intervalo = "1wk"
    periodo_data = "5y"  # Necesitamos historia para comparar 2 cruces
else:
    intervalo = "1mo"
    periodo_data = "max"

# 4. MOTOR DE ANÁLISIS
def escanear_momentum(ticker):
    try:
        # Descarga
        df = yf.download(ticker, period=periodo_data, interval=intervalo, progress=False)
        if df.empty or len(df) < 35: return None

        # Limpiar columnas
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Cálculo de MACD (12, 26, 9)
        macd_output = ta.macd(df['Close'], fast=12, slow=26, signal=9)
        df = pd.concat([df, macd_output], axis=1)
        
        macd_col = 'MACD_12_26_9'
        signal_col = 'MACDs_12_26_9'

        # Detectar Cruces Alcistas
        # MACD hoy > Signal hoy Y MACD ayer <= Signal ayer
        df['Cruce_Alcista'] = (df[macd_col] > df[signal_col]) & (df[macd_col].shift(1) <= df[signal_col].shift(1))
        
        # Obtener los últimos dos cruces
        df_cruces = df[df['Cruce_Alcista'] == True].copy()
        
        if len(df_cruces) >= 2:
            ultimo = df_cruces.iloc[-1]
            anterior = df_cruces.iloc[-2]
            
            val_u = ultimo[macd_col]
            val_a = anterior[macd_col]
            
            cumple = val_u > val_a
            
            return {
                "Ticker": ticker,
                "Resultado": "🚀 CUMPLE" if cumple else "Bajo Momentum",
                "Valor Cruce Actual": round(val_u, 3),
                "Valor Cruce Anterior": round(val_a, 3),
                "Precio": round(df['Close'].iloc[-1], 2),
                "Fecha Últ. Cruce": ultimo.name.strftime('%Y-%m-%d')
            }
    except:
        return None
    return None

# 5. EJECUCIÓN
if st.button(f"🚀 Iniciar Escaneo Maestro ({temp})"):
    st.write(f"Escaneando {len(MASTER_TICKERS)} activos... esto puede demorar un minuto.")
    
    resultados = []
    barra = st.progress(0)
    
    for i, t in enumerate(MASTER_TICKERS):
        res = escanear_momentum(t)
        if res:
            resultados.append(res)
        barra.progress((i + 1) / len(MASTER_TICKERS))
    
    if resultados:
        full_df = pd.DataFrame(resultados)
        
        # Filtramos solo los que cumplen tu condición
        final_df = full_df[full_df["Resultado"] == "🚀 CUMPLE"].sort_values(by="Valor Cruce Actual", ascending=False)
        
        st.subheader(f"✅ Resultados: Cruces con Pisos Ascendentes ({temp})")
        if not final_df.empty:
            st.success(f"Se encontraron {len(final_df)} activos que cumplen tu criterio.")
            st.dataframe(final_df, use_container_width=True, hide_index=True)
            
            # Análisis detallado del primer ticker de la lista
            st.divider()
            t_top = final_df['Ticker'].iloc[0]
            st.write(f"### Ejemplo Técnico: {t_top}")
            c1, c2 = st.columns(2)
            with c1:
                st.write("Gráfico de Precio (6 meses)")
                st.line_chart(yf.download(t_top, period="2y" if temp == "Semanal" else "10y", interval=intervalo)['Close'])
            with c2:
                st.metric("Nivel MACD Actual", final_df['Valor Cruce Actual'].iloc[0])
                st.metric("Nivel MACD Anterior", final_df['Valor Cruce Anterior'].iloc[0])
                st.write("Si el nivel actual es mayor al anterior, la 'potencia' de compra está aumentando.")
        else:
            st.warning("Ningún activo cumple la condición de pisos ascendentes en el MACD en este momento.")
        
        with st.expander("Ver lista completa analizada"):
            st.dataframe(full_df)
    else:
        st.error("No se pudieron procesar los datos.")

# 6. EDUCACIÓN TÉCNICA
st.sidebar.divider()
st.sidebar.subheader("¿Qué estoy buscando?")
st.sidebar.info("""
Estás buscando **Divergencias de Momentum**. 

- **En Semanal:** Ideal para detectar el inicio de una tendencia que durará varios meses. 
- **En Mensual:** Detecta cambios en el ciclo macroeconómico.

**Criterio:** El cruce alcista actual debe ocurrir en un nivel del MACD más alto que el cruce anterior. Esto indica que el interés comprador está apareciendo con mucha más fuerza que la vez pasada.
""")
