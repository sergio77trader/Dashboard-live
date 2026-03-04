import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import date, datetime
import urllib3
import numpy as np

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE SEGURIDAD Y PÁGINA
# ─────────────────────────────────────────────
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(layout="wide", page_title="SYSTEMATRADER | ARBITRAGE MATRIX")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 1.2rem; font-family: 'Roboto Mono', monospace; }
    .stDataFrame { font-size: 0.85rem; font-family: 'Roboto Mono', monospace; }
    h1 { color: #00E676; font-weight: 800; border-bottom: 2px solid #00E676; }
    h3 { color: #2962FF; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# BÓVEDA DE DATOS DE BONOS (TOTALIDAD DE LA CURVA)
# ─────────────────────────────────────────────
TICKERS_DATE = {
    "S31M5": date(2025, 3, 31), "S16A5": date(2025, 4, 16), "S28A5": date(2025, 4, 28),
    "S16Y5": date(2025, 5, 16), "S30Y5": date(2025, 5, 30), "S18J5": date(2025, 6, 18),
    "S30J5": date(2025, 6, 30), "S31L5": date(2025, 7, 31), "S15G5": date(2025, 8, 15),
    "S29G5": date(2025, 8, 29), "S12S5": date(2025, 9, 12), "S30S5": date(2025, 9, 30),
    "T17O5": date(2025, 10, 15), "S31O5": date(2025, 10, 31), "S10N5": date(2025, 11, 10),
    "S28N5": date(2025, 11, 28), "T15D5": date(2025, 12, 15), "T30E6": date(2026, 1, 30),
    "T13F6": date(2026, 2, 13), "TTM26": date(2026, 3, 16), "TTJ26": date(2026, 6, 30),
    "T30J6": date(2026, 6, 30), "TTS26": date(2026, 9, 15), "TTD26": date(2026, 12, 15)
}

PAYOFF = {
    "S31M5": 127.35, "S16A5": 131.211, "S28A5": 130.813, "S16Y5": 136.861,
    "S30Y5": 136.331, "S18J5": 147.695, "S30J5": 146.607, "S31L5": 147.74,
    "S15G5": 146.794, "S29G5": 157.70, "S12S5": 158.977, "S30S5": 159.734,
    "T17O5": 158.872, "S31O5": 132.821, "S10N5": 122.254, "S28N5": 123.561,
    "T15D5": 170.838, "T30E6": 142.222, "T13F6": 144.966, "TTM26": 135.238,
    "TTJ26": 144.629, "T30J6": 144.896, "TTS26": 152.096, "TTD26": 161.144
}

# ─────────────────────────────────────────────
# MOTOR DE DATOS (DATA912 BRIDGE)
# ─────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_market_data():
    try:
        h = {'User-Agent': 'Mozilla/5.0'}
        r_mep = requests.get('https://data912.com/live/mep', verify=False, timeout=10, headers=h).json()
        r_notes = requests.get('https://data912.com/live/arg_notes', verify=False, timeout=10, headers=h).json()
        r_bonds = requests.get('https://data912.com/live/arg_bonds', verify=False, timeout=10, headers=h).json()
        
        mep = pd.DataFrame(r_mep)['close'].median()
        df_full = pd.DataFrame(r_notes + r_bonds)
        return mep, df_full
    except Exception as e:
        st.error(f"Falla crítica de conexión: {e}")
        return None, None

def calculate_arbitrage_metrics(mep, df):
    if df.empty or 'symbol' not in df.columns: return pd.DataFrame()
    
    # Filtrado por activos vigentes
    df = df[df['symbol'].isin(TICKERS_DATE.keys())].copy()
    if df.empty: return pd.DataFrame()
    
    df = df.set_index('symbol')
    df['bond_price'] = df['c'].astype(float)
    df['payoff'] = df.index.map(PAYOFF)
    df['expiration'] = df.index.map(TICKERS_DATE)
    
    # Duration (Días corridos)
    today = date.today()
    df['days_to_exp'] = (pd.to_datetime(df['expiration']).dt.date - today).apply(lambda x: x.days)
    df = df[df['days_to_exp'] > 0] # Eliminar vencidos del radar
    
    # Tasas Institucionales (Interés Compuesto)
    df['tem'] = ((df['payoff'] / df['bond_price']) ** (30 / df['days_to_exp']) - 1)
    df['tna'] = ((df['payoff'] / df['bond_price']) - 1) / df['days_to_exp'] * 365
    df['tea'] = ((df['payoff'] / df['bond_price']) ** (365 / df['days_to_exp']) - 1)
    
    # Métricas de Cobertura
    df['MEP_BREAKEVEN'] = mep * (df['payoff'] / df['bond_price'])
    df['buffer_deval'] = (df['MEP_BREAKEVEN'] / mep) - 1
    
    return df.sort_values('days_to_exp')

# ─────────────────────────────────────────────
# INTERFAZ SNIPER
# ─────────────────────────────────────────────
st.title("💸 SYSTEMATRADER | ARG CARRY MATRIX")
st.markdown("### Arbitraje de Tasas: Pesos (Lecaps/Boncaps) vs Dólar MEP")

mep_now, df_raw = fetch_market_data()

if mep_now:
    st.metric("Dólar MEP de Referencia", f"${mep_now:,.2f}")
    df_calc = calculate_arbitrage_metrics(mep_now, df_raw)
    
    if not df_calc.empty:
        # Pestañas de Análisis
        t1, t2, t3 = st.tabs(["📊 Matriz de Tasas", "🛡️ Cobertura Cambiaria", "📈 Proyección USD"])
        
        with t1:
            st.subheader("Rendimiento Fijo en Pesos")
            st.dataframe(
                df_calc[['bond_price', 'days_to_exp', 'tna', 'tem', 'tea']],
                column_config={
                    "bond_price": st.column_config.NumberColumn("Precio ($)", format="%.2f"),
                    "days_to_exp": st.column_config.NumberColumn("Días Vto."),
                    "tna": st.column_config.NumberColumn("TNA", format="%.2f%%"),
                    "tem": st.column_config.NumberColumn("TEM", format="%.2f%%"),
                    "tea": st.column_config.NumberColumn("TEA", format="%.2f%%"),
                },
                use_container_width=True, height=550
            )
        
        with t2:
            st.subheader("¿A qué precio del Dólar perdés dinero?")
            fig = go.Figure()
            fig.add_hline(y=mep_now, line_dash="dash", line_color="red", annotation_text="MEP Hoy")
            fig.add_trace(go.Scatter(x=df_calc.index, y=df_calc['MEP_BREAKEVEN'], mode='lines+markers+text',
                                     text=[f"${x:.0f}" for x in df_calc['MEP_BREAKEVEN']], textposition="top center",
                                     line=dict(color='#00E676', width=3), name="MEP Equilibrio"))
            fig.update_layout(template="plotly_dark", height=450, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(
                df_calc[['bond_price', 'MEP_BREAKEVEN', 'buffer_deval']],
                column_config={
                    "MEP_BREAKEVEN": st.column_config.NumberColumn("MEP Salida (Equilibrio)", format="$%.2f"),
                    "buffer_deval": st.column_config.NumberColumn("Colchón vs Deval", format="%.2f%%")
                },
                use_container_width=True
            )
            
        with t3:
            st.subheader("Rendimiento Neto en Dólares")
            st.write("Escenarios de retorno directo en USD según variación del MEP al vencimiento.")
            scenarios = [0, 5, 10, 15, 20]
            sim = pd.DataFrame(index=df_calc.index)
            for pct in scenarios:
                mep_fut = mep_now * (1 + pct/100)
                usd_ret = (df_calc['payoff'] / mep_fut) / (df_calc['bond_price'] / mep_now) - 1
                sim[f"MEP +{pct}% (${mep_fut:.0f})"] = usd_ret
            
            st.dataframe(sim.style.format("{:.2%}"), use_container_width=True, height=550)

    else:
        st.warning("No se detectaron instrumentos vigentes en la base de datos.")
else:
    st.error("No se pudo sincronizar con el mercado.")

if st.button("🔄 ACTUALIZAR"):
    st.cache_data.clear()
    st.rerun()
