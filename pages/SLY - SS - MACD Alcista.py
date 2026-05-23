import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from datetime import datetime
import calendar

# 1. CONFIGURACIÓN DE LA APP
st.set_page_config(page_title="Escáner MACD Estratégico", layout="wide")

st.title("🔍 Escáner de Momentum con Filtros de PnL y Ciclos")
st.write("Analizando la calidad de los cruces MACD y su rendimiento desde la señal.")

# 2. LISTA MAESTRA
MASTER_TICKERS = sorted([
    'GGAL', 'YPF', 'BMA', 'PAMP', 'TGS', 'CEPU', 'EDN', 'BFR', 'SUPV', 'CRESY', 'IRS', 'TEO', 'LOMA', 'DESP', 'VIST', 'GLOB', 'MELI', 'BIOX', 'TX',
    'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NFLX', 'CRM', 'ORCL', 'ADBE', 'IBM', 'CSCO', 'PLTR', 'SNOW', 'SHOP', 'SPOT', 'UBER', 'ABNB', 'AMD', 'INTC', 'QCOM', 'AVGO', 'TXN', 'MU', 'ADI', 'AMAT', 'ARM', 'SMCI', 'TSM', 'ASML', 'LRCX',
    'JPM', 'BAC', 'C', 'WFC', 'GS', 'MS', 'V', 'MA', 'AXP', 'BRK-B', 'PYPL', 'SQ', 'COIN', 'BLK', 'USB', 'NU', 'KO', 'PEP', 'MCD', 'SBUX', 'DIS', 'NKE', 'WMT', 'COST', 'TGT', 'HD', 'LOW', 'PG', 'CL', 'MO', 'PM', 'KMB', 'EL',
    'JNJ', 'PFE', 'MRK', 'LLY', 'ABBV', 'UNH', 'BMY', 'AMGN', 'GILD', 'AZN', 'NVO', 'NVS', 'CVS', 'BA', 'CAT', 'DE', 'GE', 'MMM', 'LMT', 'RTX', 'HON', 'UNP', 'UPS', 'FDX', 'XOM', 'CVX', 'SLB', 'OXY', 'HAL', 'BP', 'SHEL', 'TTE', 'PBR', 'VLO', 'VALE', 'ITUB', 'BBD', 'ERJ', 'ABEV', 'GGB', 'SID', 'NBR', 'GOLD', 'NEM', 'PAAS', 'FCX', 'SCCO', 'RIO', 'BHP', 'ALB', 'SQM',
    'SPY', 'QQQ', 'IWM', 'DIA', 'EEM', 'EWZ', 'FXI', 'XLE', 'XLF', 'XLK', 'XLV', 'XLI', 'XLP', 'XLU', 'XLY', 'ARKK', 'SMH', 'TAN', 'GLD', 'SLV', 'GDX'
])

# 3. SIDEBAR
st.sidebar.header("1. Configurar Escaneo")
temp = st.sidebar.radio("Temporalidad:", ["Semanal", "Mensual"])
intervalo = "1wk" if temp == "Semanal" else "1mo"
periodo_data = "5y" if temp == "Semanal" else "max"

# 4. FUNCIÓN DE ANÁLISIS MEJORADA
def analizar_ticker(ticker):
    try:
        df = yf.download(ticker, period=periodo_data, interval=intervalo, progress=False)
        if df.empty or len(df) < 35: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        # Indicador
        macd_data = ta.macd(df['Close'], fast=12, slow=26, signal=9)
        df = pd.concat([df, macd_data], axis=1)
        
        m_col, s_col = 'MACD_12_26_9', 'MACDs_12_26_9'
        df['Cruce_Alcista'] = (df[m_col] > df[s_col]) & (df[m_col].shift(1) <= df[s_col].shift(1))
        
        df_cruces = df[df['Cruce_Alcista'] == True].copy()
        
        if len(df_cruces) >= 2:
            u_cruce = df_cruces.iloc[-1]
            p_cruce = df_cruces.iloc[-2]
            
            # Condición de Momentum Ascendente
            piso_ascendente = u_cruce[m_col] > p_cruce[m_col]
            
            # Precio al momento de la señal y actual
            precio_señal = u_cruce['Close']
            precio_actual = df['Close'].iloc[-1]
            pnl = ((precio_actual / precio_señal) - 1) * 100
            
            # Ubicación respecto a 0
            ubicacion = "Sobre 0 (Continuación)" if u_cruce[m_col] > 0 else "Bajo 0 (Recuperación)"
            
            return {
                "Ticker": ticker,
                "Ascendente": piso_ascendente,
                "Mes": calendar.month_name[u_cruce.name.month],
                "Zona": ubicacion,
                "PnL %": round(pnl, 2),
                "Valor Cruce": round(u_cruce[m_col], 3),
                "Precio Señal": round(precio_señal, 2),
                "Precio Actual": round(precio_actual, 2),
                "Fecha Señal": u_cruce.name.date()
            }
    except: return None
    return None

# 5. BOTÓN DE ESCANEO Y PERSISTENCIA
if 'resultados_brutos' not in st.session_state:
    st.session_state.resultados_brutos = None

if st.sidebar.button("🚀 Iniciar Gran Escaneo"):
    with st.spinner("Analizando 150+ activos..."):
        data_lista = []
        progreso = st.progress(0)
        for i, t in enumerate(MASTER_TICKERS):
            res = analizar_ticker(t)
            if res: data_lista.append(res)
            progreso.progress((i + 1) / len(MASTER_TICKERS))
        st.session_state.resultados_brutos = pd.DataFrame(data_lista)
        st.success("Escaneo completado.")

# 6. FILTROS INTERACTIVOS (Solo si hay datos)
if st.session_state.resultados_brutos is not None:
    df_res = st.session_state.resultados_brutos.copy()

    st.divider()
    st.subheader("🎯 Refinar Resultados")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        meses_disp = ["Todos"] + sorted(df_res["Mes"].unique().tolist())
        filtro_mes = st.selectbox("Filtrar por Mes de la Señal:", meses_disp)
    with c2:
        zona_disp = ["Todas"] + df_res["Zona"].unique().tolist()
        filtro_zona = st.selectbox("Filtrar por Zona (Sobre/Bajo 0):", zona_disp)
    with c3:
        solo_asc = st.checkbox("Solo Pisos Ascendentes (Fuerza Progresiva)", value=True)

    # Aplicar filtros
    if filtro_mes != "Todos":
        df_res = df_res[df_res["Mes"] == filtro_mes]
    if filtro_zona != "Todas":
        df_res = df_res[df_res["Zona"] == filtro_zona]
    if solo_asc:
        df_res = df_res[df_res["Ascendente"] == True]

    # 7. VISUALIZACIÓN
    st.write(f"Mostrando **{len(df_res)}** activos que coinciden con los filtros.")
    
    # Formatear tabla para visualización
    st.dataframe(
        df_res.drop(columns=["Ascendente"]).sort_values(by="PnL %", ascending=False),
        column_config={
            "PnL %": st.column_config.NumberColumn("PnL desde Señal", format="%.2f%%"),
            "Valor Cruce": st.column_config.NumberColumn("Nivel MACD"),
            "Fecha Señal": st.column_config.DateColumn("Fecha"),
        },
        hide_index=True,
        use_container_width=True
    )

    # 8. ANÁLISIS DE RENDIMIENTO
    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("Promedio PnL de la lista filtrada", f"{round(df_res['PnL %'].mean(), 2)}%")
    with col_b:
        best_ticker = df_res.loc[df_res['PnL %'].idxmax()] if not df_res.empty else None
        if best_ticker is not None:
            st.metric(f"Mejor Rendimiento: {best_ticker['Ticker']}", f"{best_ticker['PnL %']}%")

# 9. EXPLICACIÓN DE CONCEPTOS
st.sidebar.divider()
st.sidebar.subheader("Diccionario Técnico")
st.sidebar.write("""
- **Bajo 0 (Recuperación):** El cruce ocurre mientras la tendencia previa era bajista. Son los cruces con mayor potencial de recorrido (suelos).
- **Sobre 0 (Continuación):** El cruce ocurre en tendencia alcista. Indica una "pausa que terminó" para seguir subiendo.
- **PnL desde Señal:** Cuánto varió el precio desde que el MACD confirmó el cruce hasta el último precio de hoy.
- **Piso Ascendente:** El indicador tiene más fuerza ahora que en su señal anterior.
""")
