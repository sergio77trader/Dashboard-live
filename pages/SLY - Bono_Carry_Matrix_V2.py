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
st.set_page_config(layout="wide", page_title="SYSTEMATRADER | ARBITRAGE MASTER")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 1.2rem; font-family: 'Roboto Mono', monospace; }
    .stDataFrame { font-size: 0.85rem; font-family: 'Roboto Mono', monospace; }
    h1 { color: #00E676; font-weight: 800; border-bottom: 2px solid #00E676; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [aria-selected="true"] { background-color: #00E676; color: black; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# BÓVEDA DE DATOS: CURVA 2026 - 2027
# ─────────────────────────────────────────────
TICKERS_CONFIG = {
    # LECAPS (S) - Instrumentos de Tasa Fija Mensuales
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
    # BONCAPS (T / TT) - Bonos de Capitalización
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
# MOTOR DE DATOS (UNIFICACIÓN TOTAL)
# ─────────────────────────────────────────────
@st.cache_data(ttl=60)
def fetch_global_data():
    try:
        h = {'User-Agent': 'Mozilla/5.0'}
        # 1. Obtener MEP
        r_mep = requests.get('https://data912.com/live/mep', verify=False, timeout=10, headers=h).json()
        mep = pd.DataFrame(r_mep)['close'].median()
        # 2. Obtener Notas (T) y Bonos (S)
        r_notes = requests.get('https://data912.com/live/arg_notes', verify=False, timeout=10, headers=h).json()
        r_bonds = requests.get('https://data912.com/live/arg_bonds', verify=False, timeout=10, headers=h).json()
        df_full = pd.DataFrame(r_notes + r_bonds)
        return mep, df_full
    except: return None, None

def build_carry_matrix(mep, df):
    if df.empty: return pd.DataFrame()
    
    results = []
    today = date.today()
    
    for ticker_id, info in TICKERS_CONFIG.items():
        # BÚSQUEDA DIFUSA: Buscamos si el ticker está contenido en el símbolo del mercado
        # Esto soluciona que ByMA le agregue textos extras al nombre
        match = df[df['symbol'].str.contains(ticker_id, case=False, na=False)]
        
        if not match.empty:
            price = float(match.iloc[0]['c'])
            days = (info['vto'] - today).days
            
            if days > 0 and price > 0:
                tem = ((info['payoff'] / price) ** (30 / days) - 1)
                tea = ((info['payoff'] / price) ** (365 / days) - 1)
                tna = ((info['payoff'] / price) - 1) / days * 365
                be_mep = mep * (info['payoff'] / price)
                
                results.append({
                    "Ticker": ticker_id,
                    "Nombre Mercado": match.iloc[0]['symbol'],
                    "Precio": price,
                    "Días": days,
                    "Payoff": info['payoff'],
                    "TEM": tem,
                    "TNA": tna,
                    "TEA": tea,
                    "BREAKEVEN": be_mep,
                    "BUFFER": (be_mep / mep) - 1
                })
    
    return pd.DataFrame(results).sort_values("Días")

# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
st.title("💸 SYSTEMATRADER | CARRY TRADE MATRIX")

# Botón superior con KEY única para evitar error de duplicidad
if st.button("🔄 ACTUALIZAR DATOS DEL MERCADO", type="primary", key="btn_up"):
    st.cache_data.clear()
    st.rerun()

mep_val, raw_df = fetch_global_data()

if mep_val and not raw_df.empty:
    st.metric("Dólar MEP Referencia", f"${mep_val:,.2f}")
    
    df_matrix = build_carry_matrix(mep_val, raw_df)
    
    if not df_matrix.empty:
        # PESTAÑAS
        t1, t2, t3 = st.tabs(["📊 Matriz de Tasas", "🛡️ Breakeven MEP", "📈 Escenarios USD"])
        
        with t1:
            st.subheader("Rendimiento Fijo en Pesos (Tasa Efectiva)")
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
            st.subheader("Cobertura Cambiaria (¿Hasta cuánto aguanta el Dólar?)")
            fig = go.Figure()
            fig.add_hline(y=mep_val, line_dash="dash", line_color="red", annotation_text="Dólar Hoy")
            fig.add_trace(go.Scatter(x=df_matrix['Ticker'], y=df_matrix['BREAKEVEN'], mode='lines+markers+text',
                                     text=[f"${x:.0f}" for x in df_matrix['BREAKEVEN']], textposition="top center",
                                     line=dict(color='#00E676', width=3)))
            fig.update_layout(template="plotly_dark", height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(
                df_matrix[['Ticker', 'Precio', 'BREAKEVEN', 'BUFFER']],
                column_config={
                    "BREAKEVEN": st.column_config.NumberColumn("MEP Salida", format="$%.2f"),
                    "BUFFER": st.column_config.NumberColumn("Colchón vs Deval", format="%.2f%%")
                },
                use_container_width=True
            )

        with t3:
            st.subheader("Rendimiento Proyectado en USD")
            st.info("Ganancia neta en moneda dura si el MEP sube hacia el vencimiento.")
            scenarios = [0, 5, 10, 15, 20]
            sim = pd.DataFrame(index=df_matrix['Ticker'])
            for pct in scenarios:
                mep_fut = mep_val * (1 + pct/100)
                # Cálculo: (Monto Final USD / Monto Inicial USD) - 1
                ret_usd = (df_matrix.set_index('Ticker')['Payoff'] / mep_fut) / (df_matrix.set_index('Ticker')['Precio'] / mep_val) - 1
                sim[f"Dólar +{pct}% (${mep_fut:.0f})"] = ret_usd
            
            st.dataframe(sim.style.format("{:.2%}"), use_container_width=True, height=500)

    else:
        st.warning("⚠️ No se encontraron instrumentos S (Lecaps) en el feed. Verifique los nombres del mercado abajo.")
        with st.expander("Tickers detectados hoy en BYMA (Debug)"):
            st.write(raw_df['symbol'].unique())
else:
    st.error("Error de conexión con el feed de datos (Data912).")

# Botón inferior con KEY única
if st.button("🔄 REFRESCAR MATRIX", key="btn_low"):
    st.cache_data.clear()
    st.rerun()
