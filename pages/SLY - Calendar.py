import streamlit as st
import pandas as pd

# 1. Configuración de la página
st.set_page_config(page_title="Monitor de Inversiones Global 150+", layout="wide")

st.title("🏛️ Monitor Maestro de Balances y Dividendos")
st.write("Fecha de análisis: **17 de Mayo de 2026**")

# 2. Base de Datos Masiva (Lotes 1 y 2 - Total 82 acciones)
acciones = [
    # --- TECNOLOGÍA & SEMICONDUCTORES (USA) ---
    {"Ticker": "AAPL", "Empresa": "Apple", "Sector": "Tecnología", "Yield %": 0.52, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Agosto 2026"},
    {"Ticker": "MSFT", "Empresa": "Microsoft", "Sector": "Tecnología", "Yield %": 0.71, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "NVDA", "Empresa": "NVIDIA", "Sector": "Tecnología", "Yield %": 0.02, "Meses Cierre": "Abr/Jul/Oct/Ene", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Julio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "GOOGL", "Empresa": "Alphabet", "Sector": "Tecnología", "Yield %": 0.45, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Abr/Jul/Oct/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "META", "Empresa": "Meta", "Sector": "Tecnología", "Yield %": 0.40, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "AVGO", "Empresa": "Broadcom", "Sector": "Tecnología", "Yield %": 1.40, "Meses Cierre": "Feb/May/Ago/Nov", "Meses Pres.": "Mar/Jun/Sep/Dic", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Junio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "TSM", "Empresa": "Taiwan Semi.", "Sector": "Tecnología", "Yield %": 1.20, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Ene/Abr/Jul/Oct", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "AMZN", "Empresa": "Amazon", "Sector": "Tecnología", "Yield %": 0.00, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Reinvierte", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "N/A"},
    {"Ticker": "TSLA", "Empresa": "Tesla", "Sector": "Automotriz", "Yield %": 0.00, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Reinvierte", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "N/A"},
    {"Ticker": "IBM", "Empresa": "IBM", "Sector": "Tecnología", "Yield %": 3.45, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "CSCO", "Empresa": "Cisco", "Sector": "Tecnología", "Yield %": 2.90, "Meses Cierre": "Ene/Abr/Jul/Oct", "Meses Pres.": "Feb/May/Ago/Nov", "Ciclo Pagos": "Ene/Abr/Jul/Oct", "Próx. Cierre": "Julio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "ORCL", "Empresa": "Oracle", "Sector": "Tecnología", "Yield %": 1.25, "Meses Cierre": "Feb/May/Ago/Nov", "Meses Pres.": "Mar/Jun/Sep/Dic", "Ciclo Pagos": "Ene/Abr/Jul/Oct", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Junio 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "ADBE", "Empresa": "Adobe", "Sector": "Software", "Yield %": 0.00, "Meses Cierre": "Feb/May/Ago/Nov", "Meses Pres.": "Mar/Jun/Sep/Dic", "Ciclo Pagos": "Reinvierte", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Junio 2026", "Próx. Pago": "N/A"},
    {"Ticker": "CRM", "Empresa": "Salesforce", "Sector": "Software", "Yield %": 0.35, "Meses Cierre": "Ene/Abr/Jul/Oct", "Meses Pres.": "Feb/May/Ago/Nov", "Ciclo Pagos": "Abr/Jul/Oct/Dic", "Próx. Cierre": "Julio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Julio 2026"},

    # --- CONSUMO & RETAIL ---
    {"Ticker": "KO", "Empresa": "Coca-Cola", "Sector": "Consumo", "Yield %": 3.10, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Abr/Jul/Oct/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "PEP", "Empresa": "PepsiCo", "Sector": "Consumo", "Yield %": 2.95, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Ene/Mar/Jun/Sep", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "WMT", "Empresa": "Walmart", "Sector": "Consumo", "Yield %": 1.35, "Meses Cierre": "Abr/Jul/Oct/Ene", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Ene/Abr/May/Ago", "Próx. Cierre": "Julio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Agosto 2026"},
    {"Ticker": "SBUX", "Empresa": "Starbucks", "Sector": "Consumo", "Yield %": 2.50, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Agosto 2026"},
    {"Ticker": "NFLX", "Empresa": "Netflix", "Sector": "Entretenimiento", "Yield %": 0.00, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Reinvierte", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "N/A"},
    {"Ticker": "DIS", "Empresa": "Disney", "Sector": "Entretenimiento", "Yield %": 0.85, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Ene/Jul", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "NKE", "Empresa": "Nike", "Sector": "Consumo", "Yield %": 1.65, "Meses Cierre": "Feb/May/Ago/Nov", "Meses Pres.": "Mar/Jun/Sep/Dic", "Ciclo Pagos": "Abr/Jul/Oct/Dic", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Junio 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "MCD", "Empresa": "McDonald's", "Sector": "Consumo", "Yield %": 2.15, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "MO", "Empresa": "Altria Group", "Sector": "Consumo", "Yield %": 8.40, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Ene/Abr/Jul/Oct", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Julio 2026"},

    # --- FINANCIEROS & BANCARIOS (GLOBAL) ---
    {"Ticker": "JPM", "Empresa": "JP Morgan", "Sector": "Financiero", "Yield %": 2.40, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Ene/Abr/Jul/Oct", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "V", "Empresa": "Visa", "Sector": "Financiero", "Yield %": 0.78, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "MA", "Empresa": "Mastercard", "Sector": "Financiero", "Yield %": 0.65, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Agosto 2026"},
    {"Ticker": "PYPL", "Empresa": "PayPal", "Sector": "Fintech", "Yield %": 0.00, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Reinvierte", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "N/A"},
    {"Ticker": "GS", "Empresa": "Goldman Sachs", "Sector": "Financiero", "Yield %": 2.65, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "MS", "Empresa": "Morgan Stanley", "Sector": "Financiero", "Yield %": 3.40, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Agosto 2026"},
    {"Ticker": "PBR", "Empresa": "Petrobras", "Sector": "Energía", "Yield %": 12.8, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Trimestral", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "VALE", "Empresa": "Vale", "Sector": "Minería", "Yield %": 8.20, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Mar/Sep", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Septiembre 2026"},
    {"Ticker": "MELI", "Empresa": "Mercado Libre", "Sector": "E-commerce", "Yield %": 0.00, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Reinvierte", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "N/A"},
    {"Ticker": "O", "Empresa": "Realty Income", "Sector": "Inmobiliario", "Yield %": 5.80, "Meses Cierre": "Mensual", "Meses Pres.": "Feb/May/Ago/Nov", "Ciclo Pagos": "MENSUAL", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},

    # --- PANEL MERVAL (TODO EL PANEL LÍDER + GENERAL) ---
    {"Ticker": "ALUA", "Empresa": "Aluar", "Sector": "Merval", "Yield %": 3.20, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "May/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Noviembre 2026"},
    {"Ticker": "GGAL", "Empresa": "Galicia", "Sector": "Merval", "Yield %": 4.50, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Mayo/Junio", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "YPFD", "Empresa": "YPF", "Sector": "Merval", "Yield %": 1.50, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Variable", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Julio 2026*"},
    {"Ticker": "TXAR", "Empresa": "Ternium", "Sector": "Merval", "Yield %": 4.10, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Mayo/Junio", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "BMA", "Empresa": "Banco Macro", "Sector": "Merval", "Yield %": 4.80, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Mayo/Junio", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "PAMP", "Empresa": "Pampa Energía", "Sector": "Merval", "Yield %": 0.00, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Reinvierte", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "N/A"},
    {"Ticker": "CEPU", "Empresa": "Central Puerto", "Sector": "Merval", "Yield %": 3.90, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Variable", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026*"},
    {"Ticker": "SUPV", "Empresa": "Banco Supervielle", "Sector": "Merval", "Yield %": 3.40, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Mayo/Junio", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "BBAR", "Empresa": "Banco Francés", "Sector": "Merval", "Yield %": 4.10, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Mayo/Junio", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "COME", "Empresa": "Comercial del Plata", "Sector": "Merval", "Yield %": 4.90, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Anual", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "TRAN", "Empresa": "Transener", "Sector": "Merval", "Yield %": 2.10, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Variable", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "EDN", "Empresa": "Edenor", "Sector": "Merval", "Yield %": 0.00, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "N/A", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "N/A"},
    {"Ticker": "IRSA", "Empresa": "IRSA", "Sector": "Merval", "Yield %": 5.20, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Variable", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "CRES", "Empresa": "Cresud", "Sector": "Merval", "Yield %": 4.80, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Variable", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "BYMA", "Empresa": "BYMA", "Sector": "Merval", "Yield %": 2.40, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Trimestral", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "TGSU2", "Empresa": "TGS", "Sector": "Merval", "Yield %": 3.10, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Variable", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "TGNO4", "Empresa": "TGN", "Sector": "Merval", "Yield %": 2.90, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Variable", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "MIRG", "Empresa": "Mirgor", "Sector": "Merval", "Yield %": 1.80, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Anual", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},

    # --- SALUD & INDUSTRIALES (USA) ---
    {"Ticker": "JNJ", "Empresa": "J&J", "Sector": "Salud", "Yield %": 3.05, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "PFE", "Empresa": "Pfizer", "Sector": "Salud", "Yield %": 5.85, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "CAT", "Empresa": "Caterpillar", "Sector": "Industrial", "Yield %": 1.65, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Agosto 2026"},
    {"Ticker": "DE", "Empresa": "John Deere", "Sector": "Industrial", "Yield %": 1.50, "Meses Cierre": "Ene/Abr/Jul/Oct", "Meses Pres.": "Feb/May/Ago/Nov", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Julio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Agosto 2026"},
    {"Ticker": "GE", "Empresa": "General Electric", "Sector": "Industrial", "Yield %": 0.30, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Ene/Abr/Jul/Oct", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "BA", "Empresa": "Boeing", "Sector": "Industrial", "Yield %": 0.00, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Reinvierte", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "N/A"},
    {"Ticker": "XOM", "Empresa": "Exxon Mobil", "Sector": "Energía", "Yield %": 3.30, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "CVX", "Empresa": "Chevron", "Sector": "Energía", "Yield %": 4.10, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "GOLD", "Empresa": "Barrick Gold", "Sector": "Minería", "Yield %": 2.20, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"}
]

# 3. Procesamiento y Filtros
df = pd.DataFrame(acciones)

st.sidebar.header("🔍 Filtros Avanzados")
f_sector = st.sidebar.multiselect("Filtrar por Sector:", options=sorted(df["Sector"].unique()), default=df["Sector"].unique())
f_ticker = st.sidebar.text_input("Buscar por Ticker (ej: AAPL):").upper()
f_yield = st.sidebar.slider("Yield Mínimo (%):", 0.0, 15.0, 0.0)

# Filtrado Dinámico
df_view = df[df["Sector"].isin(f_sector) & (df["Yield %"] >= f_yield)]
if f_ticker:
    df_view = df_view[df_view["Ticker"].str.contains(f_ticker)]

# 4. Mostrar Tabla Principal
st.dataframe(
    df_view.sort_values(by="Ticker"),
    column_config={
        "Yield %": st.column_config.NumberColumn("Yield Anual", format="%.2f%%"),
        "Meses Cierre": st.column_config.TextColumn("📅 Cierre Contable"),
        "Meses Pres.": st.column_config.TextColumn("📢 Reporte Resultados"),
        "Ciclo Pagos": st.column_config.TextColumn("💰 Ciclo de Pagos"),
        "Próx. Cierre": st.column_config.TextColumn("⏳ Próx. Cierre"),
        "Próx. Pres.": st.column_config.TextColumn("🚀 Próx. Reporte"),
        "Próx. Pago": st.column_config.TextColumn("💵 Próx. Pago"),
    },
    hide_index=True,
    use_container_width=True
)

# 5. Pie de página informativo
st.divider()
st.info(f"Mostrando {len(df_view)} de {len(df)} acciones totales.")
st.markdown("""
### 📢 Tips para tu operativa
* **Fecha de Corte:** Recuerda comprar **3 días hábiles antes** del pago para figurar en el libro de accionistas.
* **Merval (*):** Los dividendos en Argentina son estimados. Dependen de lo que vote la Asamblea Ordinaria (marzo/abril).
""")
