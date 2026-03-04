import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import date
import urllib3
import numpy as np

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(layout="wide", page_title="SystemaTrader: Carry Auto")

st.title("💸 SystemaTrader: Carry Trade Matrix AUTO")
st.markdown("### Sistema Automático – Detecta todos los bonos S y T")

# -----------------------
# FETCH DATA
# -----------------------
@st.cache_data(ttl=300)
def fetch_market_data():
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


def calculate_carry(mep, df):

    # Detectar bonos S y T automáticamente
    carry = df[df['symbol'].str.match(r'^(S|T)', na=False)].copy()
    if carry.empty:
        return pd.DataFrame()

    carry = carry[['symbol', 'c']].drop_duplicates()
    carry['bond_price'] = carry['c'].astype(float).round(2)

    # -------------------------
    # PARSER REAL DE VENCIMIENTO
    # -------------------------
    MONTH_MAP = {
        "A":1, "B":2, "C":3, "D":4, "E":5, "F":6,
        "G":7, "H":8, "J":9, "K":10, "L":11, "M":12,
        "N":11, "O":10, "S":9, "Y":5
    }

    def parse_expiration(symbol):
        import re
        match = re.search(r'(\d{1,2})([A-Z])(\d)', symbol)
        if match:
            day = int(match.group(1))
            month_letter = match.group(2)
            year = 2000 + int(match.group(3))
            month = MONTH_MAP.get(month_letter)
            if month:
                try:
                    return date(year, month, day)
                except:
                    return None
        return None

    carry['expiration'] = carry['symbol'].apply(parse_expiration)
    carry = carry[carry['expiration'].notna()]

    today = date.today()
    carry['days_to_exp'] = (pd.to_datetime(carry['expiration']).dt.date - today).apply(lambda x: x.days)

    carry = carry[carry['days_to_exp'] > 0]

    # -------------------------
    # PAYOFF REAL
    # Letras pagan VN 100
    # -------------------------
    carry['payoff'] = 100

    # Tasas EXACTAS como tu script
    carry['tem'] = ((carry['payoff'] / carry['bond_price']) ** (1/(carry['days_to_exp']/30))) - 1
    carry['tna'] = ((carry['payoff'] / carry['bond_price']) - 1) / carry['days_to_exp'] * 365
    carry['tea'] = ((carry['payoff'] / carry['bond_price']) ** (365/carry['days_to_exp'])) - 1

    carry['MEP_BREAKEVEN'] = mep * (carry['payoff'] / carry['bond_price'])
    carry['buffer_deval'] = (carry['MEP_BREAKEVEN'] / mep) - 1

    return carry.sort_values("days_to_exp")


# -----------------------
# UI
# -----------------------

if st.button("🔄 ACTUALIZAR DATOS"):
    st.cache_data.clear()
    st.rerun()

mep_now, df_raw = fetch_market_data()

if mep_now is None or df_raw is None or df_raw.empty:
    st.error("Error conexión mercado.")
    st.stop()

st.metric("Dólar MEP Referencia", f"${mep_now:,.2f}")

df_calc = calculate_carry_auto(mep_now, df_raw)

if df_calc.empty:
    st.warning("No se detectaron bonos S o T.")
    st.stop()

tab1, tab2, tab3 = st.tabs([
    "📊 Matriz de Tasas",
    "🛡️ Cobertura",
    "📈 Escenarios"
])

# -----------------------
# TAB 1
# -----------------------
with tab1:
    st.subheader("Rendimiento Automático")

    st.dataframe(
        df_calc[['symbol','bond_price','days_to_exp','tna','tem','tea']],
        use_container_width=True,
        height=600
    )

# -----------------------
# TAB 2
# -----------------------
with tab2:
    st.subheader("Breakeven Dólar")

    fig = go.Figure()

    fig.add_hline(y=mep_now, line_dash="dash", line_color="red")

    fig.add_trace(go.Scatter(
        x=df_calc['symbol'],
        y=df_calc['MEP_BREAKEVEN'],
        mode='lines+markers',
        name='MEP Equilibrio'
    ))

    fig.update_layout(template="plotly_dark", height=500)
    st.plotly_chart(fig, use_container_width=True)

# -----------------------
# TAB 3
# -----------------------
with tab3:

    scenarios_pct = [0,5,10,15,20]
    sim_data = pd.DataFrame(index=df_calc['symbol'])

    for pct in scenarios_pct:
        mep_future = mep_now * (1 + pct/100)

        usd_in = df_calc['bond_price'] / mep_now
        usd_out = 100 / mep_future

        sim_data[f"+{pct}%"] = (usd_out / usd_in) - 1

    st.dataframe(sim_data.style.format("{:.2%}"), use_container_width=True)
