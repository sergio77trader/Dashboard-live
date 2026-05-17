import streamlit as st
import pandas as pd

st.set_page_config(page_title="Monitor de Dividendos & Yield", layout="wide")

st.title("💰 Monitor de Dividendos y Rendimiento (Yield)")
st.write("Análisis al: **17 de Mayo de 2026**")

# Datos con la nueva columna de Yield (Rendimiento)
# Nota: Los % son estimados anualizados basados en promedios históricos
data = [
    # --- ALTOS DIVIDENDOS (CASH FLOW) ---
    {"Ticker": "MO", "Sector": "Consumo", "Yield %": 8.5, "Ciclo Pagos": "Ene/Abr/Jul/Oct", "Próx. Pago": "Julio 2026"},
    {"Ticker": "O", "Sector": "Inmobiliario", "Yield %": 5.8, "Ciclo Pagos": "MENSUAL", "Próx. Pago": "Junio 2026"},
    {"Ticker": "MAIN", "Sector": "Financiero", "Yield %": 6.2, "Ciclo Pagos": "MENSUAL", "Próx. Pago": "Junio 2026"},
    {"Ticker": "VZ", "Sector": "Telecom", "Yield %": 6.5, "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Pago": "Agosto 2026"},
    {"Ticker": "PFE", "Sector": "Salud", "Yield %": 5.9, "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Pago": "Junio 2026"},
    
    # --- DIVIDENDOS SEGUROS (ARISTÓCRATAS) ---
    {"Ticker": "KO", "Sector": "Consumo", "Yield %": 3.1, "Ciclo Pagos": "Abr/Jul/Oct/Dic", "Próx. Pago": "Julio 2026"},
    {"Ticker": "PEP", "Sector": "Consumo", "Yield %": 2.9, "Ciclo Pagos": "Ene/Mar/Jun/Sep", "Próx. Pago": "Junio 2026"},
    {"Ticker": "JNJ", "Sector": "Salud", "Yield %": 3.0, "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Pago": "Junio 2026"},
    {"Ticker": "MCD", "Sector": "Consumo", "Yield %": 2.2, "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Pago": "Junio 2026"},
    {"Ticker": "CVX", "Sector": "Energía", "Yield %": 4.1, "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Pago": "Junio 2026"},

    # --- TECNOLÓGICAS (CRECIMIENTO + DIVIDENDO BAJO) ---
    {"Ticker": "AAPL", "Sector": "Tecnología", "Yield %": 0.5, "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Pago": "Agosto 2026"},
    {"Ticker": "MSFT", "Sector": "Tecnología", "Yield %": 0.7, "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Pago": "Junio 2026"},
    {"Ticker": "AVGO", "Sector": "Tecnología", "Yield %": 1.4, "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Pago": "Junio 2026"},
    {"Ticker": "NVDA", "Sector": "Tecnología", "Yield %": 0.02, "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Pago": "Junio 2026"},

    # --- MERVAL (ARGENTINA - MUY VARIABLES) ---
    {"Ticker": "GGAL", "Sector": "Merval", "Yield %": 4.5, "Ciclo Pagos": "May/Jun", "Próx. Pago": "Junio 2026"},
    {"Ticker": "ALUA", "Sector": "Merval", "Yield %": 3.8, "Ciclo Pagos": "May/Nov", "Próx. Pago": "Noviembre 2026"},
    {"Ticker": "TXAR", "Sector": "Merval", "Yield %": 4.2, "Ciclo Pagos": "Mayo/Junio", "Próx. Pago": "Junio 2026"},
]

df = pd.DataFrame(data)

# --- INTERFAZ ---
st.sidebar.header("Filtros")
min_yield = st.sidebar.slider("Rendimiento Mínimo (%)", 0.0, 10.0, 0.0)

df_filtered = df[df["Yield %"] >= min_yield]

# Mostrar tabla con formato de colores para el Yield
st.dataframe(
    df_filtered.sort_values(by="Yield %", ascending=False),
    column_config={
        "Yield %": st.column_config.NumberColumn(
            "Yield Anual %",
            help="Porcentaje de retorno anual solo por dividendos",
            format="%.2f%%",
        ),
        "Próx. Pago": st.column_config.TextColumn("📅 Próximo Pago Estimado"),
    },
    hide_index=True,
    use_container_width=True
)

# --- EXPLICACIÓN EDUCATIVA ---
st.markdown("---")
st.subheader("💡 Guía Rápida para Cobrar Dividendos")
col1, col2 = st.columns(2)

with col1:
    st.info("""
    **¿Cuándo comprar?**
    *   **NO** compres el mismo día del pago.
    *   **SÍ** debes tener la acción en cartera antes de la **Fecha Ex-Dividend**.
    *   En Argentina y CEDEARs, compra al menos **3 días hábiles antes** de la fecha de pago para estar seguro debido al tiempo de liquidación.
    """)

with col2:
    st.warning("""
    **¿Qué es el Yield %?**
    *   Es lo que te paga la empresa en un año dividido el precio de la acción.
    *   **Yield Alto (>7%):** Puede ser una gran oportunidad o una señal de que la acción está cayendo mucho porque la empresa tiene problemas.
    *   **Yield Bajo (<2%):** Típico de empresas que crecen mucho (como Apple o Microsoft) y prefieren reinvertir su dinero.
    """)
