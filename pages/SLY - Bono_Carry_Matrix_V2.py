import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import date, datetime
import urllib3
import numpy as np
import re

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SystemaTrader: Carry Trade Matrix")

# --- ESTILOS CSS ---
st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 1.2rem; }
    .stDataFrame { font-size: 0.9rem; }
</style>
""", unsafe_allow_html=True)

# --- BASE DE DATOS (BONOS CONFIGURADOS MANUALMENTE) ---
TICKERS_DATE = {
    "S16A5": date(2025, 4, 16), "S28A5": date(2025, 4, 28), "S16Y5": date(2025, 5, 16),
    "S30Y5": date(2025, 5, 30), "S18J5": date(2025, 6, 18), "S30J5": date(2025, 6, 30),
    "S31L5": date(2025, 7, 31), "S15G5": date(2025, 8, 15), "S29G5": date(2025, 8, 29),
    "S12S5": date(2025, 9, 12), "S30S5": date(2025, 9, 30), "T17O5": date(2025, 10, 15),
    "S31O5": date(2025, 10, 31), "S10N5": date(2025, 11, 10), "S28N5": date(2025, 11, 28),
    "T15D5": date(2025, 12, 15), "T30E6": date(2026, 1, 30), "T13F6": date(2026, 2, 13),
    "T30J6": date(2026, 6, 30), "T15E7": date(2027, 1, 15), "TTM26": date(2026, 3, 16),
    "TTJ26": date(2026, 6, 30), "TTS26": date(2026, 9, 15), "TTD26": date(2026, 12, 15),
}

PAYOFF = {
    "S16A5": 131.211, "S28A5": 130.813, "S16Y5": 136.861, "S30Y5": 136.331,
    "S18J5": 147.695, "S30J5": 146.607, "S31L5": 147.74, "S15G5": 146.794,
    "S29G5": 157.7, "S12S5": 158.977, "S30S5": 159.734, "T17O5": 158.872,
    "S31O5": 132.821, "S10N5": 122.254, "S28N5": 123.561, "T15D5": 170.838,
    "T30E6": 142.222, "T13F6": 144.966, "T30J6": 144.896, "T15E7": 160.777,
    "TTM26": 135.238, "TTJ26": 144.629, "TTS26": 152.096, "TTD26": 161.144,
}

# --- MOTOR DE DATOS ---
@st.cache_data(ttl=300)
def fetch_market_data():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}

        r_mep = requests.get('https://data912.com/live/mep', verify=False, timeout=5, headers=headers)
        r_notes = requests.get('https://data912.com/live/arg_notes', verify=False, timeout=5, headers=headers)
        r_bonds = requests.get('https://data912.com/live/arg_bonds', verify=False, timeout=5, headers=headers)

        meps = r_mep.json() if r_mep.status_code == 200 else []
        notes = r_notes.json() if r_notes.status_code == 200 else []
        bonds = r_bonds.json() if r_bonds.status_code == 200 else []

        if not meps:
            return None, None

        mep_val = pd.DataFrame(meps)['close'].median()

        full_list = []
        if isinstance(notes, list): full_list += notes
        if isinstance(bonds, list): full_list += bonds

        df_assets = pd.DataFrame(full_list)

        return mep_val, df_assets

    except Exception as e:
        st.error(f"Error en motor de datos: {e}")
        return None, None

def calculate_carry(mep, df):
    carry = df.loc[df.symbol.isin(TICKERS_DATE.keys())].copy()
    if carry.empty:
        return pd.DataFrame()

    carry = carry.set_index('symbol')
    carry['bond_price'] = carry['c'].astype(float).round(2)
    carry['payoff'] = carry.index.map(PAYOFF)
    carry['expiration'] = carry.index.map(TICKERS_DATE)

    today = date.today()
    carry['days_to_exp'] = (pd.to_datetime(carry.expiration).dt.date - today).apply(lambda x: x.days)
    carry = carry[carry['days_to_exp'] > 0]

    carry['tem'] = ((carry['payoff'] / carry['bond_price'])) ** (1/(carry['days_to_exp']/30)) - 1
    carry['tna'] = ((carry['payoff'] / carry['bond_price']) - 1) / carry['days_to_exp'] * 365
    carry['tea'] = ((carry['payoff'] / carry['bond_price'])) ** (365/carry['days_to_exp']) - 1

    carry['MEP_BREAKEVEN'] = mep * (carry['payoff'] / carry['bond_price'])
    carry['buffer_deval'] = (carry['MEP_BREAKEVEN'] / mep) - 1

    return carry.sort_values('days_to_exp')

# --- INTERFAZ ---
st.title("💸 SystemaTrader: Carry Trade Matrix (ARG)")
st.markdown("### Arbitraje de Tasas: Pesos vs Dólar MEP")

if st.button("🔄 ACTUALIZAR DATOS", type="primary"):
    st.cache_data.clear()
    st.rerun()

mep_now, df_raw = fetch_market_data()

if mep_now is not None and df_raw is not None and not df_raw.empty:

    st.metric("Dólar MEP Referencia", f"${mep_now:,.2f}")

    # =========================
    # 🔎 DETECCIÓN AUTOMÁTICA
    # =========================
    all_symbols = sorted(df_raw['symbol'].unique())

    detected_fixed = df_raw[df_raw['symbol'].str.match(r'^(S|T)', na=False)].copy()
    detected_fixed = detected_fixed[['symbol', 'c']].drop_duplicates()

    configured_set = set(TICKERS_DATE.keys())
    market_set = set(detected_fixed['symbol'])

    nuevos_no_configurados = sorted(list(market_set - configured_set))

    # =========================
    # PESTAÑAS
    # =========================
    tab0, tab1, tab2, tab3 = st.tabs([
        "🔎 Mercado Completo",
        "📊 Matriz de Tasas",
        "🛡️ Cobertura",
        "📈 Escenarios"
    ])

    # TAB 0
    with tab0:
        st.subheader("Bonos Detectados (S y T)")
        st.write(f"Total detectados en mercado: {len(detected_fixed)}")
        st.dataframe(detected_fixed.sort_values("symbol"), use_container_width=True)

        st.divider()
        st.subheader("⚠️ Bonos Nuevos NO Configurados en el Sistema")
        st.write(f"Cantidad: {len(nuevos_no_configurados)}")

        if nuevos_no_configurados:
            st.dataframe(pd.DataFrame(nuevos_no_configurados, columns=["symbol"]))
        else:
            st.success("No hay bonos nuevos fuera del sistema.")

    # TAB 1
    with tab1:
        df_calc = calculate_carry(mep_now, df_raw)

        if not df_calc.empty:
            st.subheader("Rendimiento en Pesos (Tasa Fija)")
            st.dataframe(
                df_calc[['bond_price', 'days_to_exp', 'tna', 'tem', 'tea']],
                use_container_width=True,
                height=600
            )
        else:
            st.warning("No hay bonos configurados con datos activos.")

else:
    st.error("⚠️ Error de conexión con el mercado.")
