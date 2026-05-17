import streamlit as st
import pandas as pd

# 1. Configuración de la página
st.set_page_config(page_title="Monitor de Inversiones 150+", layout="wide")

st.title("🏛️ Monitor Maestro de Balances y Dividendos (100 Acciones)")
st.write("Fecha de análisis: **17 de Mayo de 2026**")

# 2. Base de Datos Integrada (Lote 1, 2 y 3 - Total 100 acciones)
acciones = [
    # --- TECNOLOGÍA & SEMICONDUCTORES ---
    {"Ticker": "AAPL", "Empresa": "Apple", "Sector": "Tecnología", "Yield %": 0.52, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Agosto 2026"},
    {"Ticker": "MSFT", "Empresa": "Microsoft", "Sector": "Tecnología", "Yield %": 0.71, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "NVDA", "Empresa": "NVIDIA", "Sector": "Tecnología", "Yield %": 0.02, "Meses Cierre": "Abr/Jul/Oct/Ene", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Julio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "GOOGL", "Empresa": "Alphabet", "Sector": "Tecnología", "Yield %": 0.45, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Abr/Jul/Oct/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "META", "Empresa": "Meta", "Sector": "Tecnología", "Yield %": 0.40, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "AVGO", "Empresa": "Broadcom", "Sector": "Tecnología", "Yield %": 1.40, "Meses Cierre": "Feb/May/Ago/Nov", "Meses Pres.": "Mar/Jun/Sep/Dic", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Junio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "TSM", "Empresa": "Taiwan Semi.", "Sector": "Tecnología", "Yield %": 1.20, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Ene/Abr/Jul/Oct", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "AMZN", "Empresa": "Amazon", "Sector": "Tecnología", "Yield %": 0.00, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Reinvierte", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "N/A"},
    {"Ticker": "NFLX", "Empresa": "Netflix", "Sector": "Tecnología", "Yield %": 0.00, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Reinvierte", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "N/A"},
    {"Ticker": "ASML", "Empresa": "ASML", "Sector": "Tecnología", "Yield %": 1.10, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Agosto 2026"},

    # --- CONSUMO MASIVO & RETAIL ---
    {"Ticker": "KO", "Empresa": "Coca-Cola", "Sector": "Consumo", "Yield %": 3.10, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Abr/Jul/Oct/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "PEP", "Empresa": "PepsiCo", "Sector": "Consumo", "Yield %": 2.95, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Ene/Mar/Jun/Sep", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "WMT", "Empresa": "Walmart", "Sector": "Consumo", "Yield %": 1.35, "Meses Cierre": "Abr/Jul/Oct/Ene", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Ene/Abr/May/Ago", "Próx. Cierre": "Julio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Mayo 2026"},
    {"Ticker": "COST", "Empresa": "Costco", "Sector": "Consumo", "Yield %": 0.55, "Meses Cierre": "Nov/Feb/May/Ago", "Meses Pres.": "Dic/Mar/Jun/Sep", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Junio 2026", "Próx. Pago": "Mayo 2026"},
    {"Ticker": "MCD", "Empresa": "McDonald's", "Sector": "Consumo", "Yield %": 2.15, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "HD", "Empresa": "Home Depot", "Sector": "Consumo", "Yield %": 2.60, "Meses Cierre": "Abr/Jul/Oct/Ene", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Julio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "NKE", "Empresa": "Nike", "Sector": "Consumo", "Yield %": 1.60, "Meses Cierre": "Feb/May/Ago/Nov", "Meses Pres.": "Mar/Jun/Sep/Dic", "Ciclo Pagos": "Abr/Jul/Oct/Dic", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Junio 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "MO", "Empresa": "Altria Group", "Sector": "Consumo", "Yield %": 8.40, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Ene/Abr/Jul/Oct", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "SBUX", "Empresa": "Starbucks", "Sector": "Consumo", "Yield %": 2.50, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Agosto 2026"},

    # --- COMUNICACIONES & ENTRETENIMIENTO ---
    {"Ticker": "T", "Empresa": "AT&T", "Sector": "Comunicaciones", "Yield %": 6.40, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Agosto 2026"},
    {"Ticker": "VZ", "Empresa": "Verizon", "Sector": "Comunicaciones", "Yield %": 6.60, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Agosto 2026"},
    {"Ticker": "DIS", "Empresa": "Disney", "Sector": "Entretenimiento", "Yield %": 0.80, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Ene/Jul", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Julio 2026"},

    # --- FINANCIERO & BANCOS ---
    {"Ticker": "JPM", "Empresa": "JP Morgan", "Sector": "Financiero", "Yield %": 2.35, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Ene/Abr/Jul/Oct", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "V", "Empresa": "Visa", "Sector": "Financiero", "Yield %": 0.75, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "MA", "Empresa": "Mastercard", "Sector": "Financiero", "Yield %": 0.62, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Agosto 2026"},
    {"Ticker": "BAC", "Empresa": "Bank of America", "Sector": "Financiero", "Yield %": 2.50, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "GS", "Empresa": "Goldman Sachs", "Sector": "Financiero", "Yield %": 2.70, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},

    # --- BANCOS BRASIL (CEDEARS) ---
    {"Ticker": "BBD", "Empresa": "Banco Bradesco", "Sector": "Brasil", "Yield %": 7.80, "Meses Cierre": "Mensual", "Meses Pres.": "Feb/May/Ago/Nov", "Ciclo Pagos": "MENSUAL", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "ITUB", "Empresa": "Itaú Unibanco", "Sector": "Brasil", "Yield %": 6.50, "Meses Cierre": "Mensual", "Meses Pres.": "Feb/May/Ago/Nov", "Ciclo Pagos": "MENSUAL", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "PBR", "Empresa": "Petrobras", "Sector": "Energía", "Yield %": 12.80, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Trimestral", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "VALE", "Empresa": "Vale", "Sector": "Minería", "Yield %": 8.10, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Mar/Sep", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Septiembre 2026"},

    # --- ENERGÍA E INDUSTRIALES ---
    {"Ticker": "XOM", "Empresa": "Exxon Mobil", "Sector": "Energía", "Yield %": 3.35, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "CVX", "Empresa": "Chevron", "Sector": "Energía", "Yield %": 4.15, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "CAT", "Empresa": "Caterpillar", "Sector": "Industrial", "Yield %": 1.65, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Agosto 2026"},
    {"Ticker": "GE", "Empresa": "General Electric", "Sector": "Industrial", "Yield %": 0.35, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Ene/Abr/Jul/Oct", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Julio 2026"},

    # --- RENTA MENSUAL & REITS ---
    {"Ticker": "O", "Empresa": "Realty Income", "Sector": "Inmobiliario", "Yield %": 5.85, "Meses Cierre": "Mensual", "Meses Pres.": "Feb/May/Ago/Nov", "Ciclo Pagos": "MENSUAL", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "MAIN", "Empresa": "Main Street", "Sector": "Financiero", "Yield %": 6.25, "Meses Cierre": "Mensual", "Meses Pres.": "Feb/May/Ago/Nov", "Ciclo Pagos": "MENSUAL", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},

    # --- PANEL LÍDER ARGENTINA (MERVAL) ---
    {"Ticker": "ALUA", "Empresa": "Aluar", "Sector": "Merval", "Yield %": 3.20, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "May/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Noviembre 2026"},
    {"Ticker": "GGAL", "Empresa": "Galicia", "Sector": "Merval", "Yield %": 4.50, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Mayo/Junio", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "YPFD", "Empresa": "YPF", "Sector": "Merval", "Yield %": 1.50, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Variable", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Julio 2026*"},
    {"Ticker": "TXAR", "Empresa": "Ternium", "Sector": "Merval", "Yield %": 4.15, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Mayo/Junio", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "BMA", "Empresa": "Banco Macro", "Sector": "Merval", "Yield %": 4.80, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Mayo/Junio", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "PAMP", "Empresa": "Pampa Energía", "Sector": "Merval", "Yield %": 0.00, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Reinvierte", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "N/A"},
    {"Ticker": "CEPU", "Empresa": "Central Puerto", "Sector": "Merval", "Yield %": 3.95, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Variable", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026*"},
    {"Ticker": "LOMA", "Empresa": "Loma Negra", "Sector": "Merval", "Yield %": 6.30, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Variable", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "TRAN", "Empresa": "Transener", "Sector": "Merval", "Yield %": 2.10, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Variable", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "IRSA", "Empresa": "IRSA", "Sector": "Merval", "Yield %": 5.25, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Variable", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "CRES", "Empresa": "Cresud", "Sector": "Merval", "Yield %": 4.85, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Variable", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "TGSU2", "Empresa": "TGS", "Sector": "Merval", "Yield %": 3.15, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Variable", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},

    # --- PANEL GENERAL ARGENTINA (NUEVOS ADICIONALES) ---
    {"Ticker": "MOLI", "Empresa": "Molinos", "Sector": "Panel General", "Yield %": 3.50, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Junio", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "AGRO", "Empresa": "Agrometal", "Sector": "Panel General", "Yield %": 2.80, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Anual", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "MORI", "Empresa": "Morixe", "Sector": "Panel General", "Yield %": 0.00, "Meses Cierre": "May", "Meses Pres.": "Julio", "Ciclo Pagos": "N/A", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "N/A"},
    {"Ticker": "BOLT", "Empresa": "Boldt", "Sector": "Panel General", "Yield %": 1.20, "Meses Cierre": "Oct", "Meses Pres.": "Ene", "Ciclo Pagos": "Variable", "Próx. Cierre": "Octubre 2026", "Próx. Pres.": "Enero 2027", "Próx. Pago": "N/A"},
    {"Ticker": "CAPX", "Empresa": "Capex", "Sector": "Panel General", "Yield %": 4.10, "Meses Cierre": "Abr", "Meses Pres.": "Jun", "Ciclo Pagos": "Anual", "Próx. Cierre": "Abril 2027", "Próx. Pres.": "Junio 2026", "Próx. Pago": "Julio 2026"}
]

# 3. Sidebar y Filtros
df = pd.DataFrame(acciones)
st.sidebar.header("🔍 Filtros de Mercado")
st.sidebar.info(f"Total de acciones cargadas: {len(df)}")

f_sector = st.sidebar.multiselect("Sector:", options=sorted(df["Sector"].unique()), default=df["Sector"].unique())
f_ticker = st.sidebar.text_input("Buscar por Ticker (ej: PBR):").upper()
f_yield = st.sidebar.slider("Yield Mínimo (%):", 0.0, 15.0, 0.0)

# Procesar filtrado
df_filtered = df[df["Sector"].isin(f_sector) & (df["Yield %"] >= f_yield)]
if f_ticker:
    df_filtered = df_filtered[df_filtered["Ticker"].str.contains(f_ticker)]

# 4. Tabla de Visualización
st.dataframe(
    df_filtered.sort_values(by="Ticker"),
    column_config={
        "Yield %": st.column_config.NumberColumn("Yield Anual", format="%.2f%%"),
        "Meses Cierre": st.column_config.TextColumn("📅 Cierre Contable"),
        "Meses Pres.": st.column_config.TextColumn("📢 Reporte Resultados"),
        "Ciclo Pagos": st.column_config.TextColumn("💰 Ciclo de Pagos"),
        "Próx. Cierre": st.column_config.TextColumn("⌛ Próx. Cierre"),
        "Próx. Pres.": st.column_config.TextColumn("🚀 Próx. Reporte"),
        "Próx. Pago": st.column_config.TextColumn("💵 Próx. Pago"),
    },
    hide_index=True,
    use_container_width=True
)

st.divider()
st.info("📌 Consejo: Para maximizar cobros, compra antes de la 'Fecha Ex-Dividend'. En Petrobras (PBR), posicionarse en Abril/Mayo es clave para los pagos de Junio.")
