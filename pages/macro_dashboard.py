import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Global Macro Dashboard")

# --- BASE DE DATOS DE ACTIVOS ---
ASSETS = {
    "🟡 METALES & ENERGÍA": {
        "Oro (Gold Trust)": "GLD",
        "Plata (Silver Trust)": "SLV",
        "Cobre (Miners ETF)": "COPX", # Proxy de Cobre/Bronce
        "Petróleo (US Oil)": "USO",
        "Litio (Lithium ETF)": "LIT"
    },
    "🪙 CRIPTO": {
        "Bitcoin": "BTC-USD",
        "Ethereum": "ETH-USD",
        "Solana": "SOL-USD"
    },
    "🌎 MERCADOS": {
        "🇺🇸 S&P 500": "SPY",
        "🇺🇸 Nasdaq 100": "QQQ",
        "🇦🇷 Argentina (ETF)": "ARGT",
        "🇦🇷 Galicia ADR": "GGAL",
        "🇧🇷 Brasil (ETF)": "EWZ",
        "🇨🇳 China (Large Cap)": "FXI"
    },
    "💵 MONEDAS & BONOS": {
        "Dólar Index": "DX-Y.NYB",
        "Bonos 20y USA": "TLT"
    }
}

# Aplanar diccionario para búsquedas
ALL_TICKERS = {name: ticker for category in ASSETS.values() for name, ticker in category.items()}
REVERSE_MAP = {v: k for k, v in ALL_TICKERS.items()}

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuración")
    
    # Selector de Tiempo
    time_range = st.selectbox(
        "Rango de Tiempo:",
        options=["1 Mes", "3 Meses", "6 Meses", "YTD (Año actual)", "1 Año", "5 Años"],
        index=3
    )
    
    # Mapeo de tiempo a periodos de yfinance
    period_map = {
        "1 Mes": "1mo", "3 Meses": "3mo", "6 Meses": "6mo", 
        "YTD (Año actual)": "ytd", "1 Año": "1y", "5 Años": "5y"
    }
    
    st.divider()
    st.subheader("Selección de Activos")
    
    selected_tickers = []
    for category, items in ASSETS.items():
        st.markdown(f"**{category}**")
        # Por defecto seleccionamos algunos clave
        defaults = [t for n, t in items.items() if t in ['GLD', 'BTC-USD', 'SPY', 'ARGT']]
        sel = st.multiselect(f"Activos {category}", list(items.values()), format_func=lambda x: REVERSE_MAP[x], default=defaults if category in ["🟡 METALES & ENERGÍA", "🪙 CRIPTO", "🌎 MERCADOS"] else [])
        selected_tickers.extend(sel)

# --- FUNCIÓN DE DATOS ---
@st.cache_data(ttl=300) # Cache de 5 minutos
def get_data(tickers, period):
    if not tickers: return pd.DataFrame()
    data = yf.download(tickers, period=period, progress=False, group_by='ticker', auto_adjust=True)
    return data

# --- LÓGICA PRINCIPAL ---
st.title("🌍 Global Macro Dashboard")
st.markdown("Comparativa de rendimiento entre **Materias Primas, Cripto y Mercados Globales**.")

if selected_tickers:
    df_raw = get_data(selected_tickers, period_map[time_range])
    
    if not df_raw.empty:
        # 1. NORMALIZACIÓN DE DATOS (Base 0%)
        # Necesitamos un DF con solo los precios de cierre ("Close")
        df_close = pd.DataFrame()
        
        # Manejo de MultiIndex de Yahoo
        if len(selected_tickers) > 1:
            for t in selected_tickers:
                # Intentamos obtener Close, si falla (datos incompletos), lo saltamos
                try:
                    df_close[t] = df_raw[t]['Close']
                except: pass
        else:
             df_close[selected_tickers[0]] = df_raw['Close']
        
        df_close = df_close.dropna()
        
        if not df_close.empty:
            # Calcular rendimiento porcentual acumulado
            # (Precio Actual / Precio Inicial) - 1
            df_normalized = (df_close / df_close.iloc[0] - 1) * 100
            
            # --- TARJETAS DE RENDIMIENTO ---
            st.subheader("📊 Rendimiento en el periodo seleccionado")
            
            # Crear columnas dinámicas (máx 4 por fila)
            cols = st.columns(4)
            for i, ticker in enumerate(df_close.columns):
                with cols[i % 4]:
                    start_price = df_close[ticker].iloc[0]
                    end_price = df_close[ticker].iloc[-1]
                    change = ((end_price - start_price) / start_price) * 100
                    
                    name = REVERSE_MAP.get(ticker, ticker)
                    
                    st.metric(
                        label=name,
                        value=f"${end_price:,.2f}",
                        delta=f"{change:+.2f}%"
                    )
            
            st.divider()

            # --- GRÁFICO DE LÍNEAS (COMPARATIVA) ---
            st.subheader("📈 Evolución Comparada (%)")
            
            # Convertir a formato largo para Plotly
            df_chart = df_normalized.reset_index().melt(id_vars='Date', var_name='Activo', value_name='Rendimiento %')
            # Poner nombres bonitos
            df_chart['Nombre'] = df_chart['Activo'].map(REVERSE_MAP)
            
            fig = px.line(
                df_chart, x='Date', y='Rendimiento %', color='Nombre',
                hover_data={'Activo': True},
                height=500
            )
            fig.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.5)
            st.plotly_chart(fig, use_container_width=True)
            
            # --- MATRIZ DE CORRELACIÓN ---
            st.divider()
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.subheader("🧩 Correlaciones")
                st.info("""
                **¿Cómo leer esto?**
                * **1.0 (Rojo):** Se mueven idénticos.
                * **-1.0 (Azul):** Se mueven al revés (Cobertura).
                * **0 (Blanco):** No tienen relación.
                
                *Ej: Si Bitcoin tiene correlación alta con Nasdaq, no es refugio, es riesgo.*
                """)
                
            with col2:
                # Calcular correlación sobre retornos diarios (log returns es más preciso pero simple return sirve)
                daily_returns = df_close.pct_change().dropna()
                corr_matrix = daily_returns.corr()
                
                # Reemplazar tickers por nombres reales en la matriz
                corr_matrix.columns = [REVERSE_MAP.get(c, c) for c in corr_matrix.columns]
                corr_matrix.index = [REVERSE_MAP.get(i, i) for i in corr_matrix.index]
                
                fig_corr = px.imshow(
                    corr_matrix, 
                    text_auto=".2f", 
                    aspect="auto",
                    color_continuous_scale="RdBu_r", # Rojo a Azul invertido
                    zmin=-1, zmax=1
                )
                st.plotly_chart(fig_corr, use_container_width=True)

        else:
            st.warning("Datos insuficientes para graficar en este periodo (quizás algún activo es muy nuevo).")
    else:
        st.error("No se pudieron descargar datos. Revisa tu conexión.")
else:
    st.info("👈 Selecciona activos en el menú lateral para comenzar.")
