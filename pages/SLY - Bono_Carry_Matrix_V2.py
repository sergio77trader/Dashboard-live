import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import date, datetime
import urllib3
import numpy as np

# ─────────────────────────────────────────────
# CONFIGURACIÓN INSTITUCIONAL
# ─────────────────────────────────────────────
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(layout="wide", page_title="SYSTEMATRADER | ARBITRAGE MASTER V49")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 1.2rem; font-family: 'Roboto Mono', monospace; }
    .stDataFrame { font-size: 0.85rem; font-family: 'Roboto Mono', monospace; }
    h1 { color: #00E676; font-weight: 800; border-bottom: 2px solid #00E676; }
    .stTabs [data-baseweb="tab"] { height: 50px; background-color: #111; color: white; border-radius: 4px; }
    .stTabs [aria-selected="true"] { background-color: #00E676; color: black; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# BÓVEDA DE DATOS: CURVA COMPLETA 2026 - 2027
# ─────────────────────────────────────────────
TICKERS_CONFIG = {
    # LECAPS (S)
    "S31M6": {"vto": date(2026, 3, 31), "payoff": 103.85},
    "S17A6": {"vto": date(2026, 4, 17), "payoff": 107.50},
    "S29Y6": {"vto": date(2026, 5, 29), "payoff": 111.65},
    "S30J6": {"vto": date(2026, 6, 30), "payoff": 115.40},
    "S31L6": {"vto": date(2026, 7, 31), "payoff": 119.55},
    "S31G6": {"vto": date(2026, 8, 31), "payoff": 124.10},
    "S30S6": {"vto": date(2026, 9, 30), "payoff": 128.45},
    "S30O6": {"vto": date(2026, 10, 30), "payoff": 132.85},
    "S30N6": {"vto": date(2026, 11, 30), "payoff": 137.45},
    "S30D6": {"vto": date(2026, 12, 30), "payoff": 142.25},
    # BONCAPS (T / TT)
    "TTM26": {"vto": date(2026, 3, 16), "payoff": 135.24},
    "TTJ26": {"vto": date(2026, 6, 30), "payoff": 144.63},
    "T30J6": {"vto": date(2026, 6, 30), "payoff": 144.90},
    "TTS26": {"vto": date(2026, 9, 15), "payoff": 152.10},
    "TTD26": {"vto": date(2026, 12, 15), "payoff": 161.14},
    "T15E7": {"vto": date(2027, 1, 15), "payoff": 165.80}
}

# ─────────────────────────────────────────────
# MOTOR DE DATOS (TRIANGULACIÓN DE ENDPOINTS)
# ─────────────────────────────────────────────
@st.cache_data(ttl=60)
def fetch_all_arg_data():
    try:
        h = {'User-Agent': 'Mozilla/5.0'}
        # 1. MEP
        r_mep = requests.get('https://data912.com/live/mep', verify=False, timeout=10, headers=h).json()
        mep = pd.DataFrame(r_mep)['close'].median()
        
        # 2. EL TRIPLE ENDPOINT (Bonds + Notes + Letras)
        # Aquí estaba el error: faltaba 'arg_letras' para los tickers "S"
        e1 = requests.get('https://data912.com/live/arg_bonds', verify=False, timeout=10, headers=h).json()
        e2 = requests.get('https://data912.com/live/arg_notes', verify=False, timeout=10, headers=h).json()
        e3 = requests.get('https://data912.com/live/arg_letras', verify=False, timeout=10, headers=h).json()
        
        df_full = pd.DataFrame(e1 + e2 + e3)
        return mep, df_full
    except Exception as e:
        st.error(f"Error de red: {e}")
        return None, None

def process_matrix(mep, df):
    if df.empty: return pd.DataFrame()
    
    # Limpieza de símbolos para matcheo agresivo
    df['symbol'] = df['symbol'].str.replace(" ", "").str.upper()
    
    results = []
    today = date.today()

    for ticker_id, info in TICKERS_CONFIG.items():
        # Buscamos el ticker dentro del nombre (S31M6 debe estar contenido en el nombre del mercado)
        match = df[df['symbol'].str.contains(ticker_id, na=False)]
        
        if not match.empty:
            price = float(match.iloc[0]['c'])
            days = (info['vto'] - today).days
            
            if days > 0 and price > 0:
                results.append({
                    "Ticker": ticker_id,
                    "Precio": price,
                    "Días": days,
                    "Payoff": info['payoff'],
                    "TEM": ((info['payoff'] / price) ** (30 / days) - 1),
                    "TNA": ((info['payoff'] / price) - 1) / days * 365,
                    "TEA": ((info['payoff'] / price) ** (365 / days) - 1),
                    "BREAKEVEN": mep * (info['payoff'] / price),
                    "BUFFER": ((mep * (info['payoff'] / price)) / mep) - 1
                })
    
    return pd.DataFrame(results).sort_values("Días")

# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
st.title("💸 SYSTEMATRADER | CARRY TRADE V49")

mep_ref, raw_market_df = fetch_all_arg_data()

if mep_ref is not None:
    st.metric("Dólar MEP de Referencia", f"${mep_ref:,.2f}")
    
    df_matrix = process_matrix(mep_ref, raw_market_df)
    
    if not df_matrix.empty:
        # --- LAS 3 SOLAPAS SOLICITADAS ---
        t1, t2, t3 = st.tabs(["📊 Matriz de Tasas", "🛡️ Cobertura Breakeven", "📈 Escenarios USD"])
        
        with t1:
            st.subheader("Rendimiento en Pesos (Compuesto)")
            st.dataframe(
                df_matrix[['Ticker', 'Precio', 'Días', 'TEM', 'TNA', 'TEA']],
                column_config={
                    "Precio": st.column_config.NumberColumn(format="$%.2f"),
                    "TEM": st.column_config.NumberColumn("TEM (Mensual)", format="%.2f%%"),
                    "TNA": st.column_config.NumberColumn(format="%.2f%%"),
                    "TEA": st.column_config.NumberColumn("TEA (Anual)", format="%.2f%%"),
                },
                use_container_width=True, height=550
            )

        with t2:
            st.subheader("Protección vs Devaluación")
            fig = go.Figure()
            fig.add_hline(y=mep_ref, line_dash="dash", line_color="red", annotation_text="Dólar Hoy")
            fig.add_trace(go.Scatter(x=df_matrix['Ticker'], y=df_matrix['BREAKEVEN'], mode='lines+markers+text',
                                     text=[f"${x:.0f}" for x in df_matrix['BREAKEVEN']], textposition="top center",
                                     line=dict(color='#00E676', width=3)))
            fig.update_layout(template="plotly_dark", height=400, yaxis_title="Precio MEP de Salida")
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(
                df_matrix[['Ticker', 'Precio', 'BREAKEVEN', 'BUFFER']],
                column_config={
                    "BREAKEVEN": st.column_config.NumberColumn("MEP Equilibrio", format="$%.2f"),
                    "BUFFER": st.column_config.NumberColumn("Colchón vs Deval", format="%.2f%%")
                },
                use_container_width=True
            )

        with t3:
            st.subheader("Simulación de Retorno en USD")
            st.info("Ganancia neta en dólares según el precio del MEP al vencimiento.")
            scenarios = [0, 5, 10, 15, 20]
            sim = pd.DataFrame(index=df_matrix['Ticker'])
            for pct in scenarios:
                mep_fut = mep_ref * (1 + pct/100)
                # (Payoff / MEP Futuro) / (Precio / MEP Actual) - 1
                ret_usd = (df_matrix.set_index('Ticker')['Payoff'] / mep_fut) / (df_matrix.set_index('Ticker')['Precio'] / mep_ref) - 1
                sim[f"MEP +{pct}% (${mep_fut:.0f})"] = ret_usd
            
            st.dataframe(sim.style.format("{:.2%}"), use_container_width=True, height=550)

    else:
        st.warning("⚠️ Sin datos de Lecaps. BYMA puede haber desconectado el feed temporalmente.")
        with st.expander("Audit de Tickers"):
            st.write(raw_market_df['symbol'].unique() if not raw_market_df.empty else "No hay datos")
else:
    st.error("Error crítico de conexión con el feed de datos.")

# Botón de refresco blindado
if st.button("🔄 ACTUALIZAR TODO", key="master_refresh"):
    st.cache_data.clear()
    st.rerun()
