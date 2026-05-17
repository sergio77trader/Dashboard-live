import streamlit as st
import pandas as pd
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="Calendario de Inversiones", layout="wide")

st.title("📊 Monitor de Balances y Dividendos")
st.write(f"Fecha actual: {datetime.now().strftime('%d/%m/%Y')}")

# Creación de la base de datos
data = [
    {"Ticker": "KO", "Empresa": "Coca-Cola", "Tipo": "CEDEAR", "Meses Balance": "Feb/Abr/Jul/Oct", "Meses Div.": "Abr/Jul/Oct/Dic", "Próximo Balance": "Julio 2026", "Próximo Dividendo": "Julio 2026"},
    {"Ticker": "AAPL", "Empresa": "Apple", "Tipo": "CEDEAR", "Meses Balance": "Feb/May/Ago/Nov", "Meses Div.": "Feb/May/Ago/Nov", "Próximo Balance": "Agosto 2026", "Próximo Dividendo": "Agosto 2026"},
    {"Ticker": "MSFT", "Empresa": "Microsoft", "Tipo": "CEDEAR", "Meses Balance": "Ene/Abr/Jul/Oct", "Meses Div.": "Mar/Jun/Sep/Dic", "Próximo Balance": "Julio 2026", "Próximo Dividendo": "Junio 2026"},
    {"Ticker": "MO", "Empresa": "Altria Group", "Tipo": "CEDEAR", "Meses Balance": "Ene/Abr/Jul/Oct", "Meses Div.": "Ene/Abr/Jul/Oct", "Próximo Balance": "Julio 2026", "Próximo Dividendo": "Julio 2026"},
    {"Ticker": "O", "Empresa": "Realty Income", "Tipo": "CEDEAR", "Meses Balance": "Feb/May/Ago/Nov", "Meses Div.": "Mensual", "Próximo Balance": "Agosto 2026", "Próximo Dividendo": "Junio 2026"},
    {"Ticker": "JNJ", "Empresa": "Johnson & Johnson", "Tipo": "CEDEAR", "Meses Balance": "Ene/Abr/Jul/Oct", "Meses Div.": "Mar/Jun/Sep/Dic", "Próximo Balance": "Julio 2026", "Próximo Dividendo": "Junio 2026"},
    {"Ticker": "ALUA", "Empresa": "Aluar", "Tipo": "Merval", "Meses Balance": "Mar/May/Ago/Nov", "Meses Div.": "Variable", "Próximo Balance": "Agosto 2026", "Próximo Dividendo": "Noviembre 2026*"},
    {"Ticker": "TXAR", "Empresa": "Ternium Arg.", "Tipo": "Merval", "Meses Balance": "Feb/May/Ago/Nov", "Meses Div.": "Mayo/Junio", "Próximo Balance": "Agosto 2026", "Próximo Dividendo": "Junio 2026"},
    {"Ticker": "GGAL", "Empresa": "Bco. Galicia", "Tipo": "Merval", "Meses Balance": "Mar/May/Ago/Nov", "Meses Div.": "Mayo/Junio", "Próximo Balance": "Agosto 2026", "Próximo Dividendo": "Mayo/Junio 2026"},
    {"Ticker": "PFE", "Empresa": "Pfizer", "Tipo": "CEDEAR", "Meses Balance": "Ene/May/Ago/Nov", "Meses Div.": "Mar/Jun/Sep/Dic", "Próximo Balance": "Agosto 2026", "Próximo Dividendo": "Junio 2026"},
    {"Ticker": "PEP", "Empresa": "PepsiCo", "Tipo": "CEDEAR", "Meses Balance": "Feb/Abr/Jul/Oct", "Meses Div.": "Ene/Mar/Jun/Sep", "Próximo Balance": "Julio 2026", "Próximo Dividendo": "Junio 2026"},
    {"Ticker": "V", "Empresa": "Visa", "Tipo": "CEDEAR", "Meses Balance": "Ene/Abr/Jul/Oct", "Meses Div.": "Mar/Jun/Sep/Dic", "Próximo Balance": "Julio 2026", "Próximo Dividendo": "Junio 2026"},
]

df = pd.DataFrame(data)

# Filtros en el sidebar
st.sidebar.header("Filtros")
tipo_filtro = st.sidebar.multiselect("Filtrar por Tipo:", options=df["Tipo"].unique(), default=df["Tipo"].unique())
busqueda = st.sidebar.text_input("Buscar Ticker:")

# Aplicar filtros
df_filtrado = df[df["Tipo"].isin(tipo_filtro)]
if busqueda:
    df_filtrado = df_filtrado[df_filtrado["Ticker"].str.contains(busqueda.upper())]

# Mostrar tabla
st.dataframe(
    df_filtrado, 
    column_config={
        "Ticker": st.column_config.TextColumn("Ticker"),
        "Próximo Balance": st.column_config.TextColumn("📅 Próximo Balance"),
        "Próximo Dividendo": st.column_config.TextColumn("💰 Próximo Pago"),
    },
    hide_index=True,
    use_container_width=True
)

st.info("Nota: Las fechas son estimadas basadas en comportamientos históricos. Para acciones argentinas (Merval), los dividendos dependen de la aprobación de la asamblea anual.")

# Opción para ver detalles por Ticker
st.divider()
st.subheader("Análisis por Acción")
opcion = st.selectbox("Selecciona una acción para ver detalle:", df["Ticker"])
detalle = df[df["Ticker"] == opcion].iloc[0]

col1, col2 = st.columns(2)
with col1:
    st.metric("Próximo Balance", detalle["Próximo Balance"])
with col2:
    st.metric("Próximo Dividendo", detalle["Próximo Dividendo"])
