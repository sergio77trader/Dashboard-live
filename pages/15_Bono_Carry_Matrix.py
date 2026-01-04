import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import date, datetime
import urllib3

# Desactivar advertencias de SSL (Necesario para APIs argentinas)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SystemaTrader: Carry Trade Matrix")

# --- BASE DE DATOS ESTATICA (FECHAS Y PAGOS) ---
# Esto debe actualizarse si salen nuevos bonos
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
        # APIs Públicas de Data912 (Suelen usarse en FinTwitter Arg)
        meps = requests.get('https://data912.com/live/mep', verify=False, timeout=10).json()
        notes = requests.get('https://data912.com/live/arg_notes', verify=False, timeout=10).json()
        bonds = requests.get('https://data912.com/live/arg_bonds', verify=False, timeout=10).json()
        
        mep_val = pd.DataFrame(meps).close.median()
        df_assets = pd.DataFrame(notes + bonds)
        return mep_val, df_assets
    except Exception as e:
        st.error(f"Error conectando a Data912: {e}")
        return None, None

def calculate_carry(mep, df):
    # Filtrar solo los que tenemos en nuestra lista maestra
    carry = df.loc[df.symbol.isin(TICKERS_DATE.keys())].set_index('symbol').copy()
    
    # Cálculos
    carry['bond_price'] = carry['c'].round(2)
    carry['payoff'] = carry.index.map(PAYOFF)
    carry['expiration'] = carry.index.map(TICKERS_DATE)
    carry['days_to_exp'] = (pd.to_datetime(carry.expiration).dt.date - date.today()).apply(lambda x: x.days)
    
    # Tasas
    carry['tem'] = ((carry['payoff'] / carry['c'])) ** (1/(carry['days_to_exp']/30)) - 1
    carry['tna'] = ((carry['payoff'] / carry['c']) - 1) / carry['days_to_exp'] * 365
    carry['tea'] = ((carry['payoff'] / carry['c'])) ** (365/carry['days_to_exp']) - 1
    
    # Breakeven (¿A cuánto tiene que ir el dólar para salir empatado?)
    carry['MEP_BREAKEVEN'] = mep * (carry['payoff'] / carry['c'])
    carry['buffer_deval'] = (carry['MEP_BREAKEVEN'] / mep) - 1 # Colchón de devaluación
    
    return carry.sort_values('days_to_exp')

# --- INTERFAZ ---
st.title("💸 SystemaTrader: Carry Trade Matrix (ARG)")
st.markdown("Arbitraje de Tasas: Pesos vs Dólar MEP")

if st.button("🔄 ACTUALIZAR DATOS", type="primary"):
    st.cache_data.clear()
    st.rerun()

mep_now, df_raw = fetch_market_data()

if df_raw is not None:
    st.metric("Dólar MEP Referencia", f"${mep_now:,.2f}")
    
    df_calc = calculate_carry(mep_now, df_raw)
    
    # --- PESTAÑAS ---
    tab1, tab2, tab3 = st.tabs(["📊 Matriz de Tasas", "🛡️ Cobertura (Breakeven)", "📈 Escenarios"])
    
    # TAB 1: RENDIMIENTOS
    with tab1:
        st.subheader("Rendimiento en Pesos (Tasa Fija)")
        st.dataframe(
            df_calc[['bond_price', 'days_to_exp', 'tna', 'tem', 'tea']],
            column_config={
                "bond_price": st.column_config.NumberColumn("Precio", format="$%.2f"),
                "days_to_exp": st.column_config.NumberColumn("Días Vto."),
                "tna": st.column_config.NumberColumn("TNA", format="%.2f%%"),
                "tem": st.column_config.NumberColumn("TEM (Mensual)", format="%.2f%%"),
                "tea": st.column_config.NumberColumn("TEA (Anual)", format="%.2f%%"),
            },
            use_container_width=True,
            height=600
        )
    
    # TAB 2: BREAKEVEN Y COBERTURA
    with tab2:
        st.subheader("¿Cuánto aguanta el Dólar?")
        st.markdown("La columna **'Buffer Deval'** indica cuánto puede subir el dólar desde hoy hasta el vencimiento sin que pierdas dinero contra quedarte en dólares.")
        
        # Gráfico de Barras de Buffer
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_calc.index,
            y=df_calc['buffer_deval'] * 100,
            marker_color=df_calc['buffer_deval'],
            text=df_calc['buffer_deval'].apply(lambda x: f"{x:.1%}"),
            textposition='auto'
        ))
        fig.update_layout(title="Colchón de Devaluación (%)", template="plotly_dark", yaxis_title="% Cobertura")
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            df_calc[['bond_price', 'MEP_BREAKEVEN', 'buffer_deval']],
            column_config={
                "MEP_BREAKEVEN": st.column_config.NumberColumn("MEP de Salida (Equilibrio)", format="$%.2f"),
                "buffer_deval": st.column_config.ProgressColumn("Colchón Devaluatorio", format="%.2f%%", min_value=0, max_value=1)
            },
            use_container_width=True
        )

    # TAB 3: ESCENARIOS (SENSITIVITY)
    with tab3:
        st.subheader("Matriz de Retorno en USD")
        st.write("Si el dólar a la salida está en X precio, ¿Cuánto gano/pierdo en %?")
        
        # Crear escenarios dinámicos basados en el MEP actual
        scenarios = [mep_now * (1 + i/100) for i in [0, 5, 10, 20, 30]] # 0%, 5%, 10%... suba
        
        sim_data = pd.DataFrame(index=df_calc.index)
        
        for s_price in scenarios:
            col_name = f"MEP ${s_price:.0f}"
            # Retorno en USD = (Payoff / Precio Bono) / (MEP Salida / MEP Entrada) - 1
            # Simplificado: (Payoff en USD al final) / (Inversion en USD hoy)
            usd_in = df_calc['bond_price'] / mep_now
            usd_out = df_calc['payoff'] / s_price
            sim_data[col_name] = (usd_out / usd_in) - 1

        # Estilo de colores para la tabla de simulación
        def style_ret(val):
            color = '#00FF00' if val > 0 else '#FF4500'
            return f'color: {color}'

        st.dataframe(
            sim_data.style.map(style_ret).format("{:.1%}"),
            use_container_width=True,
            height=600
        )
        st.caption("Nota: Columnas indican el precio del Dólar MEP al momento del vencimiento.")

else:
    st.warning("No se pudieron cargar los datos de Data912. Intenta más tarde.")
