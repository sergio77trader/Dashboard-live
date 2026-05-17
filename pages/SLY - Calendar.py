import streamlit as st
import pandas as pd

# Configuración de la página
st.set_page_config(page_title="Calendario de Inversiones Pro", layout="wide")

st.title("📊 Monitor de Balances y Dividendos")
st.write("Fecha de análisis: **17 de Mayo de 2026**")

# Base de datos corregida y completa
data = [
    {
        "Ticker": "KO", 
        "Empresa": "Coca-Cola", 
        "Meses Cierre": "Mar/Jun/Sep/Dic", 
        "Meses Presentación": "Abr/Jul/Oct/Feb", 
        "Todos los Pagos": "Abr/Jul/Oct/Dic", 
        "Próximo Cierre": "Junio 2026", 
        "Próxima Presentación": "Julio 2026", 
        "Próximo Pago": "Julio 2026"
    },
    {
        "Ticker": "AAPL", 
        "Empresa": "Apple", 
        "Meses Cierre": "Mar/Jun/Sep/Dic", 
        "Meses Presentación": "May/Ago/Nov/Feb", 
        "Todos los Pagos": "Feb/May/Ago/Nov", 
        "Próximo Cierre": "Junio 2026", 
        "Próxima Presentación": "Agosto 2026", 
        "Próximo Pago": "Agosto 2026"
    },
    {
        "Ticker": "MSFT", 
        "Empresa": "Microsoft", 
        "Meses Cierre": "Mar/Jun/Sep/Dic", 
        "Meses Presentación": "Abr/Jul/Oct/Ene", 
        "Todos los Pagos": "Mar/Jun/Sep/Dic", 
        "Próximo Cierre": "Junio 2026", 
        "Próxima Presentación": "Julio 2026", 
        "Próximo Pago": "Junio 2026"
    },
    {
        "Ticker": "MO", 
        "Empresa": "Altria Group", 
        "Meses Cierre": "Mar/Jun/Sep/Dic", 
        "Meses Presentación": "Abr/Jul/Oct/Feb", 
        "Todos los Pagos": "Ene/Abr/Jul/Oct", 
        "Próximo Cierre": "Junio 2026", 
        "Próxima Presentación": "Julio 2026", 
        "Próximo Pago": "Julio 2026"
    },
    {
        "Ticker": "O", 
        "Empresa": "Realty Income", 
        "Meses Cierre": "Mensual", 
        "Meses Presentación": "Feb/May/Ago/Nov", 
        "Todos los Pagos": "Todos los meses", 
        "Próximo Cierre": "Mayo 2026", 
        "Próxima Presentación": "Agosto 2026", 
        "Próximo Pago": "Junio 2026"
    },
    {
        "Ticker": "JNJ", 
        "Empresa": "Johnson & Johnson", 
        "Meses Cierre": "Mar/Jun/Sep/Dic", 
        "Meses Presentación": "Abr/Jul/Oct/Ene", 
        "Todos los Pagos": "Mar/Jun/Sep/Dic", 
        "Próximo Cierre": "Junio 2026", 
        "Próxima Presentación": "Julio 2026", 
        "Próximo Pago": "Junio 2026"
    },
    {
        "Ticker": "ALUA", 
        "Empresa": "Aluar", 
        "Meses Cierre": "Mar/Jun/Sep/Dic", 
        "Meses Presentación": "May/Ago/Nov/Mar", 
        "Todos los Pagos": "Variable (May/Nov)", 
        "Próximo Cierre": "Junio 2026", 
        "Próxima Presentación": "Agosto 2026", 
        "Próximo Pago": "Noviembre 2026"
    },
    {
        "Ticker": "TXAR", 
        "Empresa": "Ternium Arg.", 
        "Cierres": "Mar/Jun/Sep/Dic", 
        "Meses Presentación": "May/Ago/Nov/Feb", 
        "Todos los Pagos": "Mayo/Junio", 
        "Próximo Cierre": "Junio 2026", 
        "Próxima Presentación": "Agosto 2026", 
        "Próximo Pago": "Junio 2026"
    },
]

df = pd.DataFrame(data)

# Mostrar Tabla
st.dataframe(
    df,
    column_config={
        "Ticker": st.column_config.TextColumn("Ticker"),
        "Meses Cierre": st.column_config.TextColumn("📅 Meses de Cierre"),
        "Meses Presentación": st.column_config.TextColumn("📢 Meses Presentación"),
        "Todos los Pagos": st.column_config.TextColumn("💰 Ciclo Completo Pagos"),
        "Próximo Cierre": st.column_config.TextColumn("⌛ Próximo Cierre"),
        "Próxima Presentación": st.column_config.TextColumn("🚀 Próxima Presentación"),
        "Próximo Pago": st.column_config.TextColumn("💵 Próximo Pago"),
    },
    hide_index=True,
    use_container_width=True
)

st.info("""
**Nota sobre KO (Coca-Cola):** 
Presenta balance en Julio y paga dividendo ese mismo mes. 
Luego cierra balance en Septiembre, lo presenta en Octubre y **paga en Octubre**. 
(En Septiembre suele ser la fecha 'Ex-dividend', pero el dinero entra en Octubre).
""")
