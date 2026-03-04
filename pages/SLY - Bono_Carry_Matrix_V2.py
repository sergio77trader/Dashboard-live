import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import date, datetime, timedelta
import urllib3
import numpy as np

# ─────────────────────────────────────────────
# CONFIGURACIÓN INSTITUCIONAL
# ─────────────────────────────────────────────
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(layout="wide", page_title="SYSTEMATRADER | ARBITRAGE MASTER")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 1.2rem; font-family: 'Roboto Mono', monospace; }
    .stDataFrame { font-size: 0.85rem; font-family: 'Roboto Mono', monospace; }
    h1 { color: #00E676; font-weight: 800; border-bottom: 2px solid #00E676; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #111; border-radius: 4px; color: white; }
    .stTabs [aria-selected="true"] { background-color: #00E676; color: black; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# BÓVEDA DE DATOS: CURVA 2026 - 2027
# ─────────────────────────────────────────────
# Actualización de fechas y payoffs proyectados para el ciclo 2026
TICKERS_CONFIG = {
    # LECAPS (S)
    "S31M6": {"vto": date(2026, 3, 31), "payoff": 103.80},
    "S17A6": {"vto": date(2026, 4, 17), "payoff": 107.45},
    "S29Y6": {"vto": date(2026, 5, 29), "payoff": 111.60},
    "S30J6": {"vto": date(2026, 6, 30), "payoff": 115.35},
    "S31L6": {"vto": date(2026, 7, 31), "payoff": 119.50},
    "S31G6": {"vto": date(2026, 8, 31), "payoff": 124.05},
    "S30S6": {"vto": date(2026, 9, 30), "payoff": 128.40},
    "S30O6": {"vto": date(2026, 10, 30), "payoff": 132.80},
    "S30N6": {"vto": date(2026, 11, 30), "payoff": 137.40},
    "S30D6": {"vto": date(2026, 12, 30), "payoff": 142.20},
    # BONCAPS (T / TT)
    "TTM26": {"vto": date(2026, 3, 16), "payoff": 135.24},
    "TTJ26": {"vto": date(2026, 6, 30), "payoff": 144.63},
    "T30J6": {"vto": date(2026, 6, 30), "payoff": 144.90},
    "TTS26": {"vto": date(2026, 9, 15), "payoff": 152.10},
    "TTD26": {"vto": date(2026, 12, 15), "payoff": 161.14},
    "T15E7": {"vto": date(2027, 1, 15), "payoff": 165.80},
    "T15M7": {"vto": date(2027, 3, 15), "payoff": 172.30},
    "T15J7": {"vto": date(2027, 6, 15), "payoff": 181.50}
}

# ─────────────────────────────────────────────
# MOTOR DE DATOS
# ─────────────────────────────────────────────
@st.cache_data(ttl=60)
def fetch_data():
    try:
        h = {'User-Agent': 'Mozilla/5.0'}
        # MEP
        r_mep = requests.get('https://data912.com/live/mep', verify=False, timeout=10, headers=h).json()
        mep = pd.DataFrame(r_mep)['close'].median()
        # INSTRUMENTOS
        r_notes = requests.get('https://data912.com/live/arg_notes', verify=False, timeout=10, headers=h).json()
        r_bonds = requests.get('https://data912.com/live/arg_bonds', verify=False, timeout=10, headers=h).json()
        df_full = pd.DataFrame(r_notes + r_bonds)
        return mep, df_full
    except: return None, None

def calculate_matrix(mep, df):
    if df.empty: return pd.DataFrame()
    
    # Normalización de Tickers
    df['symbol'] = df['symbol'].str.strip().upper()
    
    results = []
    today = date.today()

    for ticker, info in TICKERS_CONFIG.items():
        # Buscamos el ticker en el feed de mercado
        match = df[df['symbol'] == ticker]
        if not match.empty:
            price = float(match.iloc[0]['c'])
            days = (info['vto'] - today).days
            
            if days > 0 and price > 0:
                # TEM (Mensual)
                tem = ((info['payoff'] / price) ** (30 / days) - 1)
                # TEA (Anualizada)
                tea = ((info['payoff'] / price) ** (365 / days) - 1)
                # TNA
                tna = ((info['payoff'] / price) - 1) / days * 365
                # Breakeven MEP
                be_mep = mep * (info['payoff'] / price)
                # Buffer
                buffer = (be_mep / mep) - 1
                
                results.append({
                    "Ticker": ticker,
                    "Precio": price,
                    "Días Vto": days,
                    "Payoff": info['payoff'],
                    "TEM": tem,
                    "TNA": tna,
                    "TEA": tea,
                    "MEP_BREAKEVEN": be_mep,
                    "BUFFER": buffer
                })
    
    return pd.DataFrame(results).sort_values("Días Vto")

# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
st.title("💸 SYSTEMATRADER | CARRY TRADE 2026")

mep_val, raw_df = fetch_data()

if mep_val and not raw_df.empty:
    st.metric("Dólar MEP Referencia", f"${mep_val:,.2f}")
    
    df_final = calculate_matrix(mep_val, raw_df)
    
    if not df_final.empty:
        # --- LAS 3 SOLAPAS ---
        tab1, tab2, tab3 = st.tabs(["📊 Matriz de Tasas", "🛡️ Breakeven MEP", "📈 Escenarios USD"])
        
        with tab1:
            st.subheader("Rendimiento Fijo en Pesos (Compuesto)")
            st.dataframe(
                df_final[['Ticker', 'Precio', 'Días Vto', 'TEM', 'TNA', 'TEA']],
                column_config={
                    "Precio": st.column_config.NumberColumn(format="$%.2f"),
                    "TEM": st.column_config.NumberColumn(format="%.2f%%"),
                    "TNA": st.column_config.NumberColumn(format="%.2f%%"),
                    "TEA": st.column_config.NumberColumn(format="%.2f%%"),
                },
                use_container_width=True, height=600
            )

        with tab2:
            st.subheader("Análisis de Cobertura Cambiaria")
            fig = go.Figure()
            fig.add_hline(y=mep_val, line_dash="dash", line_color="red", annotation_text="Dólar Hoy")
            fig.add_trace(go.Scatter(x=df_final['Ticker'], y=df_final['MEP_BREAKEVEN'], mode='lines+markers+text',
                                     text=[f"${x:.0f}" for x in df_final['MEP_BREAKEVEN']], textposition="top center",
                                     line=dict(color='#00E676', width=3)))
            fig.update_layout(template="plotly_dark", height=400, yaxis_title="Precio Dólar ($)")
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(
                df_final[['Ticker', 'Precio', 'MEP_BREAKEVEN', 'BUFFER']],
                column_config={
                    "MEP_BREAKEVEN": st.column_config.NumberColumn("MEP Salida", format="$%.2f"),
                    "BUFFER": st.column_config.NumberColumn("Colchón vs Deval", format="%.2f%%")
                },
                use_container_width=True
            )

        with tab3:
            st.subheader("Rendimiento Proyectado en USD")
            st.info("Simulación de ganancia neta en dólares según el precio del MEP al vencimiento.")
            scenarios = [0, 5, 10, 15, 20]
            sim = pd.DataFrame(index=df_final['Ticker'])
            for pct in scenarios:
                mep_fut = mep_val * (1 + pct/100)
                # (Payoff / MEP Futuro) / (Precio / MEP Actual) - 1
                ret_usd = (df_final.set_index('Ticker')['Payoff'] / mep_fut) / (df_final.set_index('Ticker')['Precio'] / mep_val) - 1
                sim[f"MEP +{pct}% (${mep_fut:.0f})"] = ret_usd
            
            st.dataframe(sim.style.format("{:.2%}"), use_container_width=True, height=550)

    else:
        st.warning("No se encontraron instrumentos activos. BYMA puede haber cambiado los nombres de las Lecaps.")
        with st.expander("Audit de Tickers en Mercado (Debug)"):
            st.write(raw_df['symbol'].unique())
else:
    st.error("Error de conexión con el feed de datos (Data912).")

# Botón único con Key para evitar error
if st.button("🔄 ACTUALIZAR MATRIZ", key="main_refresh_button"):
    st.cache_data.clear()
    st.rerun()
