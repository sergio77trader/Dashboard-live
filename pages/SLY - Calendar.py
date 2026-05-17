import streamlit as st
import pandas as pd

st.set_page_config(page_title="Monitor de Inversiones Global", layout="wide")

st.title("📈 Monitor Masivo de Balances y Dividendos")
st.write("Fecha de análisis: **17 de Mayo de 2026**")

# Diccionario de datos ampliado
data = [
    # --- TECNOLOGÍA & SEMICONDUCTORES ---
    {"Ticker": "AAPL", "Sector": "Tecnología", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Agosto 2026"},
    {"Ticker": "MSFT", "Sector": "Tecnología", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "NVDA", "Sector": "Tecnología", "Meses Cierre": "Abr/Jul/Oct/Ene", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Julio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "META", "Sector": "Tecnología", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "GOOGL", "Sector": "Tecnología", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Abr/Jul/Oct/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "AVGO", "Sector": "Tecnología", "Meses Cierre": "Feb/May/Ago/Nov", "Meses Pres.": "Mar/Jun/Sep/Dic", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Junio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "TSM", "Sector": "Tecnología", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Ene/Abr/Jul/Oct", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Julio 2026"},

    # --- CONSUMO MASIVO & RETAIL ---
    {"Ticker": "KO", "Sector": "Consumo", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Abr/Jul/Oct/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "PEP", "Sector": "Consumo", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Ene/Mar/Jun/Sep", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "MCD", "Sector": "Consumo", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "WMT", "Sector": "Consumo", "Meses Cierre": "Abr/Jul/Oct/Ene", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Ene/Abr/May/Ago", "Próx. Cierre": "Julio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Mayo 2026"},
    {"Ticker": "NKE", "Sector": "Consumo", "Meses Cierre": "Feb/May/Ago/Nov", "Meses Pres.": "Mar/Jun/Sep/Dic", "Ciclo Pagos": "Abr/Jul/Oct/Dic", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Junio 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "COST", "Sector": "Consumo", "Meses Cierre": "Nov/Feb/May/Ago", "Meses Pres.": "Dic/Mar/Jun/Sep", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Junio 2026", "Próx. Pago": "Mayo 2026"},
    {"Ticker": "SBUX", "Sector": "Consumo", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Mayo 2026"},

    # --- SALUD & BIOTECNOLOGÍA ---
    {"Ticker": "JNJ", "Sector": "Salud", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "PFE", "Sector": "Salud", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "ABBV", "Sector": "Salud", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Mayo 2026"},
    {"Ticker": "LLY", "Sector": "Salud", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},

    # --- FINANZAS & PAGOS ---
    {"Ticker": "V", "Sector": "Financiero", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "MA", "Sector": "Financiero", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Mayo 2026"},
    {"Ticker": "JPM", "Sector": "Financiero", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Ene/Abr/Jul/Oct", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "BAC", "Sector": "Financiero", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "GS", "Sector": "Financiero", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Mayo 2026"},

    # --- ENERGÍA & RENTA MENSUAL ---
    {"Ticker": "XOM", "Sector": "Energía", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "O", "Sector": "Inmobiliario", "Meses Cierre": "Mensual", "Meses Pres.": "Feb/May/Ago/Nov", "Ciclo Pagos": "MENSUAL", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "MAIN", "Sector": "Financiero", "Meses Cierre": "Mensual", "Meses Pres.": "Feb/May/Ago/Nov", "Ciclo Pagos": "MENSUAL", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},

    # --- PANEL LÍDER MERVAL (ARGENTINA) ---
    {"Ticker": "ALUA", "Sector": "Merval", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "May/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Noviembre 2026"},
    {"Ticker": "BBAR", "Sector": "Merval", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "May/Jun", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "BMA", "Sector": "Merval", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "May/Jun", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "CEPU", "Sector": "Merval", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Variable", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026*"},
    {"Ticker": "COME", "Sector": "Merval", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Anual (Jun)", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "EDN", "Sector": "Merval", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "N/A", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "N/A"},
    {"Ticker": "GGAL", "Sector": "Merval", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Mayo/Junio", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "LOMA", "Sector": "Merval", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "May/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "PAMP", "Sector": "Merval", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Reinvierte", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "N/A"},
    {"Ticker": "SUPV", "Sector": "Merval", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Mayo/Junio", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "TECO2", "Sector": "Merval", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Variable", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026*"},
    {"Ticker": "TGSU2", "Sector": "Merval", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Variable", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Mayo 2026"},
    {"Ticker": "TXAR", "Sector": "Merval", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Mayo/Junio", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "YPFD", "Sector": "Merval", "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Variable", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Julio 2026*"},
]

df = pd.DataFrame(data)

# --- CONFIGURACIÓN DE PANTALLA ---
col_filtro1, col_filtro2 = st.columns([1, 2])

with col_filtro1:
    search = st.text_input("🔍 Buscar por Ticker:").upper()

with col_filtro2:
    sectores = st.multiselect("Filtrar Sectores:", options=sorted(df["Sector"].unique()), default=df["Sector"].unique())

# Aplicar Filtros
df_final = df[df["Sector"].isin(sectores)]
if search:
    df_final = df_final[df_final["Ticker"].str.contains(search)]

# --- VISTA DE TABLA ---
st.dataframe(
    df_final,
    column_config={
        "Ticker": st.column_config.TextColumn("Ticker", width="small"),
        "Sector": st.column_config.TextColumn("Sector"),
        "Meses Cierre": st.column_config.TextColumn("📅 Cierres"),
        "Meses Pres.": st.column_config.TextColumn("📢 Presentación"),
        "Ciclo Pagos": st.column_config.TextColumn("💰 Ciclo Anual"),
        "Próx. Cierre": st.column_config.TextColumn("⌛ Próx. Cierre"),
        "Próx. Pres.": st.column_config.TextColumn("🚀 Próx. Pres."),
        "Próx. Pago": st.column_config.TextColumn("💵 Próx. Pago"),
    },
    hide_index=True,
    use_container_width=True
)

st.markdown("---")
st.info("📌 **Nota para inversores:** Las fechas marcadas con (*) son estimaciones basadas en años anteriores. En el mercado argentino (Merval), los pagos dependen estrictamente de lo que decida la Asamblea Ordinaria de Accionistas.")
