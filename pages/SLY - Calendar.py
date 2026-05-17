import streamlit as st
import pandas as pd

# Configuración de la página
st.set_page_config(page_title="Monitor de Inversiones Pro", layout="wide")

st.title("🏛️ Monitor Maestro de Balances y Dividendos")
st.write("Fecha de análisis: **17 de Mayo de 2026**")

# BASE DE DATOS COMPLETA (Merval + CEDEARs + Yield)
data = [
    # --- TECNOLOGÍA ---
    {"Ticker": "AAPL", "Empresa": "Apple", "Sector": "Tecnología", "Yield %": 0.52, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Agosto 2026"},
    {"Ticker": "MSFT", "Empresa": "Microsoft", "Sector": "Tecnología", "Yield %": 0.71, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "NVDA", "Empresa": "NVIDIA", "Sector": "Tecnología", "Yield %": 0.02, "Meses Cierre": "Abr/Jul/Oct/Ene", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Julio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "GOOGL", "Empresa": "Google", "Sector": "Tecnología", "Yield %": 0.45, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Abr/Jul/Oct/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "AVGO", "Empresa": "Broadcom", "Sector": "Tecnología", "Yield %": 1.41, "Meses Cierre": "Feb/May/Ago/Nov", "Meses Pres.": "Mar/Jun/Sep/Dic", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Junio 2026", "Próx. Pago": "Junio 2026"},

    # --- CONSUMO (DIVIDEND ARISTOCRATS) ---
    {"Ticker": "KO", "Empresa": "Coca-Cola", "Sector": "Consumo", "Yield %": 3.10, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Abr/Jul/Oct/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "PEP", "Empresa": "PepsiCo", "Sector": "Consumo", "Yield %": 2.95, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Ene/Mar/Jun/Sep", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "MCD", "Empresa": "McDonald's", "Sector": "Consumo", "Yield %": 2.15, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "MO", "Empresa": "Altria Group", "Sector": "Consumo", "Yield %": 8.40, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Ene/Abr/Jul/Oct", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "PG", "Empresa": "Procter & Gamble", "Sector": "Consumo", "Yield %": 2.40, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Agosto 2026"},

    # --- SALUD ---
    {"Ticker": "JNJ", "Empresa": "Johnson & Johnson", "Sector": "Salud", "Yield %": 3.05, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "PFE", "Empresa": "Pfizer", "Sector": "Salud", "Yield %": 5.85, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},

    # --- RENTA MENSUAL ---
    {"Ticker": "O", "Empresa": "Realty Income", "Sector": "Inmobiliario", "Yield %": 5.75, "Meses Cierre": "Mensual", "Meses Pres.": "Feb/May/Ago/Nov", "Ciclo Pagos": "MENSUAL", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "MAIN", "Empresa": "Main Street Cap.", "Sector": "Financiero", "Yield %": 6.10, "Meses Cierre": "Mensual", "Meses Pres.": "Feb/May/Ago/Nov", "Ciclo Pagos": "MENSUAL", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},

    # --- PANEL LÍDER MERVAL ---
    {"Ticker": "GGAL", "Empresa": "Grupo Galicia", "Sector": "Merval", "Yield %": 4.50, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Mayo/Junio", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "ALUA", "Empresa": "Aluar", "Sector": "Merval", "Yield %": 3.20, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "May/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Noviembre 2026"},
    {"Ticker": "TXAR", "Empresa": "Ternium Arg.", "Sector": "Merval", "Yield %": 4.10, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Mayo/Junio", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "YPFD", "Empresa": "YPF", "Sector": "Merval", "Yield %": 1.50, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Variable", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Julio 2026*"},
    {"Ticker": "BMA", "Empresa": "Banco Macro", "Sector": "Merval", "Yield %": 4.80, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Mayo/Junio", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "PAMP", "Empresa": "Pampa Energía", "Sector": "Merval", "Yield %": 0.00, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Reinvierte", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "N/A"},
]

df = pd.DataFrame(data)

# --- FILTROS ---
col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    search = st.text_input("🔍 Ticker:").upper()
with col2:
    sectores = st.multiselect("Sector:", options=df["Sector"].unique(), default=df["Sector"].unique())
with col3:
    min_yield = st.number_input("Yield Mínimo %:", value=0.0, step=0.5)

# Aplicar filtros
df_final = df[(df["Sector"].isin(sectores)) & (df["Yield %"] >= min_yield)]
if search:
    df_final = df_final[df_final["Ticker"].str.contains(search)]

# --- TABLA ---
st.dataframe(
    df_final.sort_values(by="Ticker"),
    column_config={
        "Yield %": st.column_config.NumberColumn("Yield Anual", format="%.2f%%"),
        "Meses Cierre": st.column_config.TextColumn("📅 Cierre Período"),
        "Meses Pres.": st.column_config.TextColumn("📢 Presentación"),
        "Ciclo Pagos": st.column_config.TextColumn("💰 Ciclo de Pagos"),
        "Próx. Cierre": st.column_config.TextColumn("⏳ Próx. Cierre"),
        "Próx. Pres.": st.column_config.TextColumn("🚀 Próx. Pres."),
        "Próx. Pago": st.column_config.TextColumn("💵 Próx. Pago"),
    },
    hide_index=True,
    use_container_width=True
)

# --- EXPLICACIÓN TÉCNICA ---
st.divider()
st.subheader("💡 ¿Cuándo comprar para cobrar el dividendo?")

st.markdown("""
Para cobrar un dividendo, **no importa la fecha de pago**, importa la **Fecha Ex-Dividend (Fecha de Corte)**.

1.  **Fecha Ex-Dividend:** Es el día que la acción "corta cupón". Si la comprás ese día o después, **NO cobrás**. 
2.  **Antelación:** Debido a que las operaciones tardan 48hs en liquidarse (T+2), debés comprar la acción al menos **3 días hábiles antes** de la fecha de pago para estar seguro de figurar en el libro de accionistas.
3.  **Ajuste de precio:** Recordá que el día de la fecha de corte, el precio de la acción suele bajar automáticamente el valor del dividendo. Por eso, lo ideal es comprar con **semanas de anticipación** para aprovechar la subida previa al pago.
""")

st.info("Nota: Los valores de Yield % son estimados anualizados. Las fechas de Argentina (*) están sujetas a asamblea.")
