import streamlit as st
import pandas as pd

# Configuración de la página
st.set_page_config(page_title="Monitor de Inversiones 150+", layout="wide")

st.title("🚀 Monitor Global de Inversiones (Panel Masivo)")
st.write("Fecha de análisis: **17 de Mayo de 2026**")

# --- BASE DE DATOS MAESTRA ---
acciones = [
    # --- LOTE 1: TECNOLOGÍA (BIG TECH) ---
    {"Ticker": "AAPL", "Empresa": "Apple", "Sector": "Tecnología", "Yield %": 0.52, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Agosto 2026"},
    {"Ticker": "MSFT", "Empresa": "Microsoft", "Sector": "Tecnología", "Yield %": 0.71, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "NVDA", "Empresa": "NVIDIA", "Sector": "Tecnología", "Yield %": 0.02, "Meses Cierre": "Abr/Jul/Oct/Ene", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Julio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "GOOGL", "Empresa": "Google", "Sector": "Tecnología", "Yield %": 0.45, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Abr/Jul/Oct/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "META", "Empresa": "Meta", "Sector": "Tecnología", "Yield %": 0.40, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "AVGO", "Empresa": "Broadcom", "Sector": "Tecnología", "Yield %": 1.40, "Meses Cierre": "Feb/May/Ago/Nov", "Meses Pres.": "Mar/Jun/Sep/Dic", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Junio 2026", "Próx. Pago": "Junio 2026"},

    # --- LOTE 2: CONSUMO ---
    {"Ticker": "KO", "Empresa": "Coca-Cola", "Sector": "Consumo", "Yield %": 3.10, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Abr/Jul/Oct/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "PEP", "Empresa": "PepsiCo", "Sector": "Consumo", "Yield %": 2.95, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Ene/Mar/Jun/Sep", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "WMT", "Empresa": "Walmart", "Sector": "Consumo", "Yield %": 1.35, "Meses Cierre": "Abr/Jul/Oct/Ene", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Ene/Abr/May/Ago", "Próx. Cierre": "Julio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Mayo 2026"},
    {"Ticker": "MO", "Empresa": "Altria Group", "Sector": "Consumo", "Yield %": 8.40, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Ene/Abr/Jul/Oct", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Julio 2026"},

    # --- LOTE 3: MERVAL (ARGENTINA) ---
    {"Ticker": "ALUA", "Empresa": "Aluar", "Sector": "Merval", "Yield %": 3.20, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "May/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Noviembre 2026"},
    {"Ticker": "GGAL", "Empresa": "Galicia", "Sector": "Merval", "Yield %": 4.50, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Mayo/Junio", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "YPFD", "Empresa": "YPF", "Sector": "Merval", "Yield %": 1.50, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Variable", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Julio 2026*"},
    {"Ticker": "TXAR", "Empresa": "Ternium", "Sector": "Merval", "Yield %": 4.10, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Mayo/Junio", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},

    # --- LOTE 4: FINANCIERO (EE.UU.) ---
    {"Ticker": "JPM", "Empresa": "JP Morgan", "Sector": "Financiero", "Yield %": 2.30, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Ene/Abr/Jul/Oct", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "V", "Empresa": "Visa", "Sector": "Financiero", "Yield %": 0.75, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "MA", "Empresa": "Mastercard", "Sector": "Financiero", "Yield %": 0.60, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Agosto 2026"},
    {"Ticker": "BAC", "Empresa": "Bank of America", "Sector": "Financiero", "Yield %": 2.60, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},

    # --- LOTE 5: RENTA MENSUAL Y REITS ---
    {"Ticker": "O", "Empresa": "Realty Income", "Sector": "Inmobiliario", "Yield %": 5.80, "Meses Cierre": "Mensual", "Meses Pres.": "Fe
