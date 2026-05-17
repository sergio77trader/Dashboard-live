import streamlit as st
import pandas as pd

st.set_page_config(page_title="Monitor de Inversiones Market-Wide", layout="wide")

st.title("🏛️ Monitor Global de Balances y Dividendos")
st.write("Estado del mercado al: **17 de Mayo de 2026**")

# Base de Datos Ampliada
data = [
    # --- TECNOLOGÍA (BIG TECH) ---
    {"Ticker": "AAPL", "Sector": "Tecnología", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Agosto 2026"},
    {"Ticker": "MSFT", "Sector": "Tecnología", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "NVDA", "Sector": "Tecnología", "Meses Cierre": "Abr/Jul/Oct/Ene", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Julio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "GOOGL", "Sector": "Tecnología", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Abr/Jul/Oct/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Julio 2026"},
    
    # --- CONSUMO Y DIVIDEND ARISTOCRATS ---
    {"Ticker": "KO", "Sector": "Consumo", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Abr/Jul/Oct/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "PEP", "Sector": "Consumo", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Ene/Mar/Jun/Sep", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "MCD", "Sector": "Consumo", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "WMT", "Sector": "Consumo", "Meses Cierre": "Abr/Jul/Oct/Ene", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Ene/Abr/Mayo/Ago", "Próx. Cierre": "Julio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Mayo 2026"},
    {"Ticker": "PG", "Sector": "Consumo", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Agosto 2026"},

    # --- SALUD ---
    {"Ticker": "JNJ", "Sector": "Salud", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "PFE", "Sector": "Salud", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},

    # --- FINANCIERO Y ENERGÍA (USA) ---
    {"Ticker": "V", "Sector": "Financiero", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "XOM", "Sector": "Energía", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "CVX", "Sector": "Energía", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    
    # --- RENTA MENSUAL ---
    {"Ticker": "O", "Sector": "Inmobiliario", "Meses Cierre": "Mensual", "Meses Pres.": "Feb/May/Ago/Nov", "Ciclo Pagos": "MENSUAL", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "MAIN", "Sector": "Financiero", "Meses Cierre": "Mensual", "Meses Pres.": "Feb/May/Ago/Nov", "Ciclo Pagos": "MENSUAL", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},

    # --- MERVAL (ARGENTINA) ---
    {"Ticker": "GGAL", "Sector": "Merval", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Mayo/Junio", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Mayo/Junio 2026"},
    {"Ticker": "BMA", "Sector": "Merval", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Mayo/Junio", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Mayo/Junio 2026"},
    {"Ticker": "YPFD", "Sector": "Merval", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Variable", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Julio 2026*"},
    {"Ticker": "PAMP", "Sector": "Merval", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Reinvierte", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "N/A"},
    {"Ticker": "TXAR", "Sector": "Merval", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Mayo/Junio", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "ALUA", "Sector": "Merval", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "May/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Noviembre 2026"},
    {"Ticker": "CEPU", "Sector": "Merval", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Variable", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026*"},
]

df = pd.DataFrame(data)

# --- SIDEBAR (Filtros Avanzados) ---
st.sidebar.header("Filtros de Mercado")
sector_select = st.sidebar.multiselect("Filtrar por Sector:", options=df["Sector"].unique(), default=df["Sector"].unique())
search = st.sidebar.text_input("Buscar Ticker:").upper()

# Aplicar filtros
df_filtered = df[df["Sector"].isin(sector_select)]
if search:
    df_filtered = df_filtered[df_filtered["Ticker"].str.contains(search)]

# --- TABLA PRINCIPAL ---
st.dataframe(
    df_filtered,
    column_config={
        "Ticker": st.column_config.TextColumn("Ticker", width="small"),
        "Sector": st.column_config.TextColumn("Sector"),
        "Meses Cierre": st.column_config.TextColumn("📅 Cierres"),
        "Meses Pres.": st.column_config.TextColumn("📢 Presentación"),
        "Ciclo Pagos": st.column_config.TextColumn("💰 Ciclo Anual"),
        "Próx. Cierre": st.column_config.TextColumn("⏳ Próx. Cierre"),
        "Próx. Pres.": st.column_config.TextColumn("🚀 Próx. Presentación"),
        "Próx. Pago": st.column_config.TextColumn("💵 Próx. Pago"),
    },
    hide_index=True,
    use_container_width=True
)

st.success("💡 **Consejo:** Las acciones de 'Renta Mensual' (como O y MAIN) son ideales para flujo de caja constante.")
st.info("⚠️ Los dividendos del Merval marcados con (*) son estimados según asambleas pasadas.")
