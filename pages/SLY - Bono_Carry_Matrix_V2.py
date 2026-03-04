import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import date
import urllib3
import re

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(layout="wide", page_title="SystemaTrader: Carry Matrix AUTO")

st.title("💸 SystemaTrader: Carry Trade Matrix AUTO")
st.markdown("### Letras y Bonos Detectados Automáticamente (S y T)")

# ---------------------------------------------------
# FETCH MARKET DATA
# ---------------------------------------------------
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


# ---------------------------------------------------
# PARSER REAL DE VENCIMIENTO DESDE TICKER
# ---------------------------------------------------
def parse_expiration(symbol):

    MONTH_MAP = {
        "A":1, "B":2, "C":3, "D":4, "E":5, "F":6,
        "G":7, "H":8, "J":9, "K":10, "L":11, "M":12,
        "N":11, "O":10, "S":9, "Y":5
    }

    match = re.search(r'(\d{1,2})([A-Z])(\d)', str(symbol))
    if match:
        try:
            day = int(match.group(1))
            month_letter = match.group(2)
            year = 2000 + int(match.group(3))
            month = MONTH_MAP.get(month_letter)

            if month:
                return date(year, month, day)
        except:
            return None

    return None


# ---------------------------------------------------
# CALCULATE CARRY (VERSIÓN REAL AUTOMÁTICA)
# ---------------------------------------------------
def calculate_carry(mep, df):

    # Detectar automáticamente S y T
    carry = df[df['symbol'].str.match(r'^(S|T)', na=False)].copy()

    if carry.empty:
        return pd.DataFrame()

    carry = carry[['symbol', 'c']].drop_duplicates()
    carry['bond_price'] = pd.to_numeric(carry['c'], errors='coerce')
    carry = carry.dropna(subset=['bond_price'])

    # Parsear vencimiento real
    carry['expiration'] = carry['symbol'].apply(parse_expiration)
    carry = carry[carry['expiration'].notna()]

    today = date.today()
    carry['days_to_exp'] = (
        pd.to_datetime(carry['expiration']).dt.date - today
    ).apply(lambda x: x.days)

    carry = carry[carry['days_to_exp'] > 0]

    # Letras bullet → VN 100
    carry['payoff'] = 100

    # Tasas EXACTAS como tu modelo original
    carry['tem'] = ((carry['payoff'] / carry['bond_price']) ** (1/(carry['days_to_exp']/30))) - 1
    carry['tna'] = ((carry['payoff'] / carry['bond_price']) - 1) / carry['days_to_exp'] * 365
    carry['tea'] = ((carry['payoff'] / carry['bond_price']) ** (365/carry['days_to_exp'])) - 1

    # Breakeven
    carry['MEP_BREAKEVEN'] = mep * (carry['payoff'] / carry['bond_price'])
    carry['buffer_deval'] = (carry['MEP_BREAKEVEN'] / mep) - 1

    return carry.sort_values("days_to_exp")


# ---------------------------------------------------
# UI
# ---------------------------------------------------
if st.button("🔄 ACTUALIZAR DATOS", type="primary"):
    st.cache_data.clear()
    st.rerun()

mep_now, df_raw = fetch_market_data()

if mep_now is None or df_raw is None or df_raw.empty:
    st.error("⚠️ Error de conexión con mercado.")
    st.stop()

st.metric("Dólar MEP Referencia", f"${mep_now:,.2f}")

df_calc = calculate_carry(mep_now, df_raw)

if df_calc.empty:
    st.warning("No se detectaron bonos válidos.")
    st.stop()

tab1, tab2, tab3 = st.tabs([
    "📊 Matriz de Tasas",
    "🛡️ Cobertura (Breakeven)",
    "📈 Escenarios"
])

# ---------------------------------------------------
# TAB 1
# ---------------------------------------------------
with tab1:
    st.subheader("Rendimiento en Pesos")

    st.dataframe(
        df_calc[['symbol','bond_price','days_to_exp','tna','tem','tea']],
        use_container_width=True,
        height=600
    )

# ---------------------------------------------------
# TAB 2
# ---------------------------------------------------
with tab2:
    st.subheader("Curva de Cobertura Cambiaria")

    fig = go.Figure()

    fig.add_hline(
        y=mep_now,
        line_dash="dash",
        line_color="red",
        annotation_text=f"MEP Hoy ${mep_now:.0f}"
    )

    fig.add_trace(go.Scatter(
        x=df_calc['symbol'],
        y=df_calc['MEP_BREAKEVEN'],
        mode='lines+markers',
        name='MEP Equilibrio'
    ))

    fig.update_layout(
        template="plotly_dark",
        height=500,
        yaxis_title="Precio Dólar ($)"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        df_calc[['symbol','bond_price','MEP_BREAKEVEN','buffer_deval']],
        use_container_width=True
    )

# ---------------------------------------------------
# TAB 3
# ---------------------------------------------------
with tab3:
    st.subheader("Simulación Retorno USD")

    scenarios_pct = [0,5,10,15,20]
    sim_data = pd.DataFrame(index=df_calc['symbol'])

    for pct in scenarios_pct:
        mep_future = mep_now * (1 + pct/100)

        usd_in = df_calc['bond_price'] / mep_now
        usd_out = 100 / mep_future

        sim_data[f"+{pct}%"] = (usd_out / usd_in) - 1

    st.dataframe(
        sim_data.style.format("{:.2%}"),
        use_container_width=True,
        height=600
    )
