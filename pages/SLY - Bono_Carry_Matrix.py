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

st.set_page_config(layout="wide", page_title="SystemaTrader: Carry Trade Matrix")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 1.2rem; font-family: 'Roboto Mono', monospace; }
    .stDataFrame { font-size: 0.9rem; }
    h1 { color: #00E676; font-weight: 800; border-bottom: 2px solid #00E676; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# BASE DE DATOS DE BONOS (LECAPS & BONCAPS)
# ─────────────────────────────────────────────
TICKERS_DATE = {
    "S31M5": date(2025, 3, 31), "S16A5": date(2025, 4, 16), "S28A5": date(2025, 4, 28), 
    "S16Y5": date(2025, 5, 16), "S30Y5": date(2025, 5, 30), "S18J5": date(2025, 6, 18), 
    "S30J5": date(2025, 6, 30), "S31L5": date(2025, 7, 31), "S15G5": date(2025, 8, 15), 
    "S29G5": date(2025, 8, 29), "S12S5": date(2025, 9, 12), "S30S5": date(2025, 9, 30), 
    "T17O5": date(2025, 10, 15), "S31O5": date(2025, 10, 31), "S10N5": date(2025, 11, 10), 
    "S28N5": date(2025, 11, 28), "T15D5": date(2025, 12, 15), "T30E6": date(2026, 1, 30), 
    "T13F6": date(2026, 2, 13), "T30J6": date(2026, 6, 30), "T15E7": date(2027, 1, 15), 
    "TTM26": date(2026, 3, 16), "TTJ26": date(2026, 6, 30), "TTS26": date(2026, 9, 15), 
    "TTD26": date(2026, 12, 15),
}

PAYOFF = {
    "S31M5": 127.35, "S16A5": 131.211, "S28A5": 130.813, "S16Y5": 136.861, 
    "S30Y5": 136.331, "S18J5": 147.695, "S30J5": 146.607, "S31L5": 147.74, 
    "S15G5": 146.794, "S29G5": 157.7, "S12S5": 158.977, "S30S5": 159.734, 
    "T17O5": 158.872, "S31O5": 132.821, "S10N5": 122.254, "S28N5": 123.561, 
    "T15D5": 170.838, "T30E6": 142.222, "T13F6": 144.966, "T30J6": 144.896, 
    "T15E7": 160.777, "TTM26": 135.238, "TTJ26": 144.629, "TTS26": 152.096, 
    "TTD26": 161.144,
}

# ─────────────────────────────────────────────
# MOTOR DE DATOS
# ─────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_market_data():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        # Peticiones
        r_mep = requests.get('https://data912.com/live/mep', verify=False, timeout=10, headers=headers)
        r_notes = requests.get('https://data912.com/live/arg_notes', verify=False, timeout=10, headers=headers)
        r_bonds = requests.get('https://data912.com/live/arg_bonds', verify=False, timeout=10, headers=headers)

        if r_mep.status_code != 200: return None, None

        mep_val = pd.DataFrame(r_mep.json())['close'].median()
        
        full_list = []
        if r_notes.status_code == 200: full_list += r_notes.json()
        if r_bonds.status_code == 200: full_list += r_bonds.json()
        
        return mep_val, pd.DataFrame(full_list)
    except Exception as e:
        st.error(f"Fallo de Conexión: {e}")
        return None, None

def calculate_carry(mep, df):
    if df.empty or 'symbol' not in df.columns: return pd.DataFrame()

    # Filtrar por base de datos
    carry = df.loc[df.symbol.isin(TICKERS_DATE.keys())].copy()
    if carry.empty: return pd.DataFrame()

    carry = carry.set_index('symbol')
    carry['bond_price'] = carry['c'].astype(float)
    carry['payoff'] = carry.index.map(PAYOFF)
    carry['expiration'] = carry.index.map(TICKERS_DATE)

    # Días al vencimiento
    today = date.today()
    carry['days_to_exp'] = (pd.to_datetime(carry.expiration).dt.date - today).apply(lambda x: x.days)
    carry = carry[carry['days_to_exp'] > 0] # Eliminar vencidos

    # Tasas
    carry['tem'] = ((carry['payoff'] / carry['bond_price']) ** (30 / carry['days_to_exp']) - 1)
    carry['tna'] = ((carry['payoff'] / carry['bond_price']) - 1) / carry['days_to_exp'] * 365
    carry['tea'] = ((carry['payoff'] / carry['bond_price']) ** (365 / carry['days_to_exp']) - 1)

    # Breakeven
    carry['MEP_BREAKEVEN'] = mep * (carry['payoff'] / carry['bond_price'])
    carry['buffer_deval'] = (carry['MEP_BREAKEVEN'] / mep) - 1

    return carry.sort_values('days_to_exp')

# ─────────────────────────────────────────────
# INTERFAZ STREAMLIT
# ─────────────────────────────────────────────
st.title("💸 SYSTEMATRADER | CARRY MATRIX")
st.markdown("### Arbitraje de Tasas: Lecaps/Boncaps vs Dólar MEP")

if st.button("🔄 REFRESCAR MERCADO", type="primary"):
    st.cache_data.clear()
    st.rerun()

mep_now, df_raw = fetch_market_data()

if mep_now and not df_raw.empty:
    st.metric("Dólar MEP Referencia", f"${mep_now:,.2f}")
    
    df_calc = calculate_carry(mep_now, df_raw)
    
    if not df_calc.empty:
        tab1, tab2, tab3 = st.tabs(["📊 Matriz de Tasas", "🛡️ Cobertura (Breakeven)", "📈 Escenarios USD"])
        
        with tab1:
            st.dataframe(
                df_calc[['bond_price', 'days_to_exp', 'tna', 'tem', 'tea']],
                column_config={
                    "bond_price": st.column_config.NumberColumn("Precio ($)", format="%.2f"),
                    "days_to_exp": st.column_config.NumberColumn("Días Vto."),
                    "tna": st.column_config.NumberColumn("TNA", format="%.2f%%"),
                    "tem": st.column_config.NumberColumn("TEM", format="%.2f%%"),
                    "tea": st.column_config.NumberColumn("TEA", format="%.2f%%"),
                },
                use_container_width=True, height=500
            )
        
        with tab2:
            fig = go.Figure()
            fig.add_hline(y=mep_now, line_dash="dash", line_color="red", annotation_text="MEP Actual")
            fig.add_trace(go.Scatter(x=df_calc.index, y=df_calc['MEP_BREAKEVEN'], mode='lines+markers+text',
                                     text=[f"${x:.0f}" for x in df_calc['MEP_BREAKEVEN']], textposition="top center",
                                     line=dict(color='#00E676')))
            fig.update_layout(title="Precio del Dólar donde el Bono rinde 0% en USD", template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(
                df_calc[['bond_price', 'MEP_BREAKEVEN', 'buffer_deval']],
                column_config={
                    "MEP_BREAKEVEN": st.column_config.NumberColumn("MEP Salida (Equilibrio)", format="$%.2f"),
                    "buffer_deval": st.column_config.NumberColumn("Buffer vs Devaluación", format="%.2f%%")
                },
                use_container_width=True
            )

        with tab3:
            scenarios = [0, 5, 10, 15, 20]
            sim_data = pd.DataFrame(index=df_calc.index)
            for pct in scenarios:
                mep_futuro = mep_now * (1 + pct/100)
                usd_in = df_calc['bond_price'] / mep_now
                usd_out = df_calc['payoff'] / mep_futuro
                sim_data[f"MEP +{pct}% (${mep_futuro:.0f})"] = (usd_out / usd_in) - 1

            st.dataframe(sim_data.style.format("{:.2%}"), use_container_width=True)
    else:
        st.warning("No se encontraron bonos activos para los tickers definidos.")
else:
    st.error("⚠️ Error conectando con Data912. Reintente en unos instantes.")

if st.button("🔄 ACTUALIZAR MATRIZ"):
    st.cache_data.clear()
    st.rerun()
