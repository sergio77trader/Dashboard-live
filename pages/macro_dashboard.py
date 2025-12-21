import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SystemaTrader: Macro Dashboard Ultimate")

# --- ESTILOS CSS ---
st.markdown("""
<style>
    .metric-card {
        background-color: #0e1117; border: 1px solid #303030;
        padding: 10px; border-radius: 8px; text-align: center;
    }
    .bull { color: #00FF00; font-weight: bold; }
    .bear { color: #FF0000; font-weight: bold; }
    .neutral { color: #FFA500; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- BASE DE DATOS DE ACTIVOS ESTRATÉGICOS ---
ASSETS = {
    "📊 ÍNDICES & RIESGO": {
        "S&P 500 (USA)": "SPY",
        "Nasdaq 100 (Tech)": "QQQ",
        "Russell 2000 (PyMEs)": "IWM",
        "Mundo (Ex-USA)": "VXUS",
        "Miedo (VIX)": "^VIX"
    },
    "🟡 COMMODITIES & AGRO": {
        "Oro (Refugio)": "GLD",
        "Plata (Ind/Refugio)": "SLV",
        "Cobre (Economía)": "COPX",
        "Petróleo (Energía)": "USO",
        "Soja (Clave Arg)": "SOYB"
    },
    "🪙 CRIPTO": {
        "Bitcoin": "BTC-USD",
        "Ethereum": "ETH-USD",
        "Solana": "SOL-USD"
    },
    "🇦🇷 ARGENTINA & LATAM": {
        "Argentina ETF": "ARGT",
        "Galicia ADR": "GGAL",
        "YPF ADR": "YPF",
        "Brasil ETF": "EWZ"
    },
    "🇨🇳 ASIA": {
        "China Large-Cap": "FXI",
        "Alibaba": "BABA"
    },
    "💵 TASAS & BONOS": {
        "Dólar Index": "DX-Y.NYB",
        "Bonos 20y+": "TLT"
    }
}

# Aplanar para uso interno
ALL_TICKERS = {name: ticker for cat in ASSETS.values() for name, ticker in cat.items()}
REVERSE_MAP = {v: k for k, v in ALL_TICKERS.items()}

# --- FUNCIONES DE CÁLCULO ---
@st.cache_data(ttl=300)
def get_data(tickers, period):
    if not tickers: return pd.DataFrame()
    # Descargamos
    data = yf.download(tickers, period=period, progress=False, group_by='ticker', auto_adjust=True)
    return data

def analyze_trend(df, ticker, context):
    """
    Genera una recomendación basada en la temporalidad seleccionada.
    """
    try:
        # Extraer serie de precios
        close = df[ticker]['Close'] if isinstance(df.columns, pd.MultiIndex) else df['Close']
        close = close.dropna()
        
        if close.empty: return "Sin Datos", "gray"

        last_price = close.iloc[-1]
        
        # Calcular indicadores básicos
        rsi = ta.rsi(close, length=14).iloc[-1] if len(close) > 14 else 50
        sma_short = close.rolling(20).mean().iloc[-1] if len(close) > 20 else last_price
        sma_long = close.rolling(50).mean().iloc[-1] if len(close) > 50 else last_price
        sma_macro = close.rolling(200).mean().iloc[-1] if len(close) > 200 else last_price

        # LÓGICA DINÁMICA SEGÚN TEMPORALIDAD
        signal = "NEUTRAL"
        color = "neutral"
        reason = ""

        if context == "CORTO PLAZO":
            # Miramos RSI y SMA 20 (Momentum)
            if last_price > sma_short:
                if rsi > 70: 
                    signal = "SOBRECOMPRA"; color = "neutral"; reason = "Tendencia alcista pero extendida (RSI > 70). Cuidado."
                else: 
                    signal = "ALCISTA"; color = "bull"; reason = "Precio sobre media de 20 días. Momentum positivo."
            else:
                if rsi < 30: 
                    signal = "SOBREVENTA"; color = "bull"; reason = "Posible rebote técnico (RSI < 30)."
                else: 
                    signal = "BAJISTA"; color = "bear"; reason = "Precio bajo media de 20 días. Debilidad."

        elif context == "MEDIANO PLAZO":
            # Miramos SMA 50
            if last_price > sma_long:
                signal = "TENDENCIA SANA"; color = "bull"; reason = "Cotiza sobre la media de 50 ruedas."
            else:
                signal = "DÉBIL"; color = "bear"; reason = "Perdió la media de 50 ruedas."

        elif context == "LARGO PLAZO":
            # Miramos SMA 200 (La madre de las tendencias)
            if last_price > sma_macro:
                signal = "BULL MARKET"; color = "bull"; reason = "Estructuralmente Alcista (> SMA 200)."
            else:
                signal = "BEAR MARKET"; color = "bear"; reason = "Estructuralmente Bajista (< SMA 200)."

        return signal, color, reason, rsi

    except Exception as e:
        return "Error", "gray", str(e), 0

# --- SIDEBAR ---
with st.sidebar:
    st.title("🎛️ Centro de Mando")
    
    # Selector de Tiempo Inteligente
    time_options = {
        "1 Mes (Corto Plazo)": "1mo",
        "3 Meses (Corto Plazo)": "3mo",
        "6 Meses (Mediano Plazo)": "6mo",
        "YTD (Año Actual)": "ytd",
        "1 Año (Mediano Plazo)": "1y",
        "5 Años (Largo Plazo)": "5y"
    }
    
    selected_time_label = st.selectbox("Temporalidad de Análisis:", list(time_options.keys()), index=3)
    selected_period = time_options[selected_time_label]
    
    # Determinar contexto para el algoritmo
    if "Mes" in selected_time_label: context = "CORTO PLAZO"
    elif "Año" in selected_time_label or "YTD" in selected_time_label: context = "MEDIANO PLAZO"
    else: context = "LARGO PLAZO" # 5 Años
    
    st.info(f"Modo Análisis: **{context}**")
    
    st.divider()
    
    # Selección de Activos
    st.subheader("Activos a Vigilar")
    selected_tickers = []
    
    # Pre-seleccionados recomendados
    defaults = ['SPY', 'BTC-USD', 'GLD', 'ARGT', '^VIX', 'SOYB']
    
    for cat, items in ASSETS.items():
        with st.expander(cat, expanded=True):
            sel = st.multiselect(
                "Seleccionar:", 
                list(items.values()), 
                format_func=lambda x: REVERSE_MAP[x],
                default=[x for x in list(items.values()) if x in defaults],
                key=cat
            )
            selected_tickers.extend(sel)

# --- APP PRINCIPAL ---
st.title(f"🌍 Tablero Macro Global: Visión {context}")

if selected_tickers:
    # Descarga
    with st.spinner("Conectando con mercados globales..."):
        df_raw = get_data(selected_tickers, selected_period)
    
    if not df_raw.empty:
        # Preparar datos de cierre para gráficos
        df_close = pd.DataFrame()
        for t in selected_tickers:
            try:
                # Manejo robusto de MultiIndex
                if isinstance(df_raw.columns, pd.MultiIndex):
                    df_close[t] = df_raw[t]['Close']
                else:
                    if len(selected_tickers) == 1: df_close[t] = df_raw['Close']
            except: pass
        
        df_close = df_close.dropna()
        
        # 1. TABLA DE RECOMENDACIONES (La joya del script)
        st.subheader("1. Diagnóstico de Tendencia")
        
        analysis_data = []
        for t in selected_tickers:
            name = REVERSE_MAP.get(t, t)
            # Llamamos a la función inteligente
            sig, col, reason, rsi = analyze_trend(df_raw, t, context)
            
            # Formato de cambio
            start = df_close[t].iloc[0]
            end = df_close[t].iloc[-1]
            change = ((end - start) / start) * 100
            
            analysis_data.append({
                "Activo": name,
                "Precio": end,
                "Rendimiento": change,
                "Estado": sig,
                "Análisis Automático": reason,
                "RSI": rsi,
                "Color": col
            })
            
        # Mostrar como Dataframe con estilo
        df_an = pd.DataFrame(analysis_data)
        
        # Función para colorear
        def color_status(val):
            color = 'green' if val in ['ALCISTA', 'TENDENCIA SANA', 'BULL MARKET', 'SOBREVENTA'] else \
                    'red' if val in ['BAJISTA', 'DÉBIL', 'BEAR MARKET'] else 'orange'
            return f'color: {color}; font-weight: bold'

        st.dataframe(
            df_an.style.applymap(color_status, subset=['Estado']),
            column_config={
                "Precio": st.column_config.NumberColumn(format="$%.2f"),
                "Rendimiento": st.column_config.NumberColumn(format="%.2f%%"),
                "RSI": st.column_config.NumberColumn(format="%.0f"),
            },
            use_container_width=True,
            hide_index=True
        )

        st.divider()

        # 2. GRÁFICO COMPARATIVO
        st.subheader("2. Evolución Comparada (%)")
        # Normalizar a %
        df_norm = (df_close / df_close.iloc[0] - 1) * 100
        df_chart = df_norm.reset_index().melt(id_vars='Date', var_name='Ticker', value_name='Rendimiento')
        df_chart['Nombre'] = df_chart['Ticker'].map(REVERSE_MAP)
        
        fig = px.line(df_chart, x='Date', y='Rendimiento', color='Nombre', height=500)
        fig.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.3)
        st.plotly_chart(fig, use_container_width=True)

        # 3. MATRIZ DE CORRELACIÓN
        st.subheader("3. Relaciones de Mercado (Correlación)")
        
        c1, c2 = st.columns([1, 2])
        with c1:
            st.info("""
            **¿Cómo leer esto?**
            * **Rojo (+1):** Se mueven igual.
            * **Azul (-1):** Se mueven opuestos.
            * **Blanco (0):** Sin relación.
            
            *Busca colores AZULES para cubrirte.*
            """)
        with c2:
            corr = df_close.pct_change().corr()
            # Poner nombres reales
            corr.index = [REVERSE_MAP.get(x,x) for x in corr.index]
            corr.columns = [REVERSE_MAP.get(x,x) for x in corr.columns]
            
            fig_corr = px.imshow(corr, text_auto=".2f", color_continuous_scale="RdBu_r", zmin=-1, zmax=1, aspect="auto")
            st.plotly_chart(fig_corr, use_container_width=True)

    else:
        st.error("No se pudieron obtener datos. Intenta con menos activos o revisa la conexión.")

else:
    st.info("👈 Selecciona activos para comenzar el análisis.")
