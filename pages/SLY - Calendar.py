import streamlit as st
import pandas as pd
from datetime import datetime

# Configuración de la página
st.set_page_config(page_title="Calendario Contable de Inversiones", layout="wide")

st.title("📊 Monitor de Balances y Dividendos")
st.write(f"Fecha actual de análisis: **17 de mayo de 2026**")

# Base de datos con las nuevas definiciones
# Cierre: Mes donde termina el trimestre contable
# Presentación: Mes donde se publica el balance (generalmente 1 mes después del cierre)
data = [
    {
        "Ticker": "KO", 
        "Empresa": "Coca-Cola", 
        "Cierres": "Mar/Jun/Sep/Dic", 
        "Meses Presentación": "Abr/Jul/Oct/Feb", 
        "Próximo Cierre": "Junio 2026", 
        "Próxima Presentación": "Julio 2026", 
        "Próximo Pago": "Julio 2026"
    },
    {
        "Ticker": "AAPL", 
        "Empresa": "Apple", 
        "Cierres": "Mar/Jun/Sep/Dic", 
        "Meses Presentación": "May/Ago/Nov/Feb", 
        "Próximo Cierre": "Junio 2026", 
        "Próxima Presentación": "Agosto 2026", 
        "Próximo Pago": "Agosto 2026"
    },
    {
        "Ticker": "MSFT", 
        "Empresa": "Microsoft", 
        "Cierres": "Mar/Jun/Sep/Dic", 
        "Meses Presentación": "Abr/Jul/Oct/Ene", 
        "Próximo Cierre": "Junio 2026", 
        "Próxima Presentación": "Julio 2026", 
        "Próximo Pago": "Junio 2026"
    },
    {
        "Ticker": "O", 
        "Empresa": "Realty Income", 
        "Cierres": "Mensual", 
        "Meses Presentación": "Feb/May/Ago/Nov", 
        "Próximo Cierre": "Mayo 2026", 
        "Próxima Presentación": "Agosto 2026", 
        "Próximo Pago": "Junio 2026"
    },
    {
        "Ticker": "ALUA", 
        "Empresa": "Aluar", 
        "Cierres": "Mar/Jun/Sep/Dic", 
        "Meses Presentación": "May/Ago/Nov/Mar", 
        "Próximo Cierre": "Junio 2026", 
        "Próxima Presentación": "Agosto 2026", 
        "Próximo Pago": "Variable"
    },
    {
        "Ticker": "TXAR", 
        "Empresa": "Ternium Arg.", 
        "Cierres": "Mar/Jun/Sep/Dic", 
        "Meses Presentación": "May/Ago/Nov/Feb", 
        "Próximo Cierre": "Junio 2026", 
        "Próxima Presentación": "Agosto 2026", 
        "Próximo Pago": "Junio 2026"
    },
    {
        "Ticker": "GGAL", 
        "Empresa": "Bco. Galicia", 
        "Cierres": "Mar/Jun/Sep/Dic", 
        "Meses Presentación": "May/Ago/Nov/Mar", 
        "Próximo Cierre": "Junio 2026", 
        "Próxima Presentación": "Agosto 2026", 
        "Próximo Pago": "Mayo/Junio 2026"
    },
]

df = pd.DataFrame(data)

# Sidebar con filtros
st.sidebar.header("Opciones de Visualización")
ticker_search = st.sidebar.text_input("Buscar por Ticker (ej: AAPL):").upper()

if ticker_search:
    df = df[df["Ticker"].str.contains(ticker_search)]

# Mostrar Tabla Principal
st.subheader("Calendario Detallado")
st.dataframe(
    df,
    column_config={
        "Ticker": st.column_config.TextColumn("Ticker"),
        "Cierres": st.column_config.TextColumn("📅 Meses de Cierre"),
        "Meses Presentación": st.column_config.TextColumn("📢 Meses de Presentación"),
        "Próximo Cierre": st.column_config.TextColumn("⏳ Próximo Cierre de Balance", help="Mes en que termina el periodo contable"),
        "Próxima Presentación": st.column_config.TextColumn("🚀 Próxima Presentación", help="Mes en que se anuncian los resultados"),
        "Próximo Pago": st.column_config.TextColumn("💰 Próximo Pago Div.", help="Mes estimado de cobro de dividendos"),
    },
    hide_index=True,
    use_container_width=True
)

# Sección de ayuda educativa
with st.expander("🎓 ¿Cómo entender estas columnas?"):
    st.markdown("""
    *   **Cierre de Balance (Periodo):** Es cuando la empresa termina de contar sus ganancias del trimestre. Es la "foto" contable.
    *   **Presentación (Earnings):** Ocurre generalmente **un mes después** del cierre. Es cuando el precio de la acción se mueve por la noticia.
    *   **Pago de Dividendos:** Suele ocurrir poco después de la presentación. 
    *   *Ejemplo de Apple (AAPL):* Cierra en **Junio**, presenta la noticia en **Agosto** y te paga el dividendo en **Agosto**.
    """)

st.warning("⚠️ Los datos de empresas argentinas (Merval) pueden variar según lo que decida la Asamblea de Accionistas cada año.")
