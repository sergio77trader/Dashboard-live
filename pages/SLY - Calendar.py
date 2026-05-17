import streamlit as st
import pandas as pd

# 1. Configuración de la página
st.set_page_config(page_title="Monitor de Inversiones Global 150+", layout="wide")

st.title("🏛️ Monitor Maestro de Balances y Dividendos (150 Acciones)")
st.write("Análisis actualizado al: **17 de Mayo de 2026**")

# 2. Base de Datos Masiva (150 Acciones - Integrado Total)
acciones = [
    # --- TECNOLOGÍA & SEMICONDUCTORES ---
    {"Ticker": "AAPL", "Empresa": "Apple", "Sector": "Tecnología", "Yield %": 0.52, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Agosto 2026"},
    {"Ticker": "MSFT", "Empresa": "Microsoft", "Sector": "Tecnología", "Yield %": 0.71, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "NVDA", "Empresa": "NVIDIA", "Sector": "Tecnología", "Yield %": 0.02, "Meses Cierre": "Abr/Jul/Oct/Ene", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Julio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "GOOGL", "Empresa": "Alphabet", "Sector": "Tecnología", "Yield %": 0.45, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Abr/Jul/Oct/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "META", "Empresa": "Meta", "Sector": "Tecnología", "Yield %": 0.40, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "AVGO", "Empresa": "Broadcom", "Sector": "Tecnología", "Yield %": 1.40, "Meses Cierre": "Feb/May/Ago/Nov", "Meses Pres.": "Mar/Jun/Sep/Dic", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Junio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "TSM", "Empresa": "Taiwan Semi.", "Sector": "Tecnología", "Yield %": 1.20, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Ene/Abr/Jul/Oct", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "ASML", "Empresa": "ASML", "Sector": "Tecnología", "Yield %": 1.10, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Agosto 2026"},
    {"Ticker": "ORCL", "Empresa": "Oracle", "Sector": "Tecnología", "Yield %": 1.25, "Meses Cierre": "Feb/May/Ago/Nov", "Meses Pres.": "Mar/Jun/Sep/Dic", "Ciclo Pagos": "Ene/Abr/Jul/Oct", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Junio 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "INTC", "Empresa": "Intel", "Sector": "Tecnología", "Yield %": 1.40, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "AMD", "Empresa": "AMD", "Sector": "Tecnología", "Yield %": 0.00, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Reinvierte", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "N/A"},
    {"Ticker": "CSCO", "Empresa": "Cisco", "Sector": "Tecnología", "Yield %": 2.90, "Meses Cierre": "Ene/Abr/Jul/Oct", "Meses Pres.": "Feb/May/Ago/Nov", "Ciclo Pagos": "Ene/Abr/Jul/Oct", "Próx. Cierre": "Julio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Julio 2026"},

    # --- CONSUMO MASIVO, RETAIL & ALIMENTOS ---
    {"Ticker": "KO", "Empresa": "Coca-Cola", "Sector": "Consumo", "Yield %": 3.10, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Abr/Jul/Oct/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "PEP", "Empresa": "PepsiCo", "Sector": "Consumo", "Yield %": 2.95, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Ene/Mar/Jun/Sep", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "WMT", "Empresa": "Walmart", "Sector": "Consumo", "Yield %": 1.35, "Meses Cierre": "Abr/Jul/Oct/Ene", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Ene/Abr/May/Ago", "Próx. Cierre": "Julio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Agosto 2026"},
    {"Ticker": "TGT", "Empresa": "Target", "Sector": "Consumo", "Yield %": 2.80, "Meses Cierre": "Abr/Jul/Oct/Ene", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Julio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "LOW", "Empresa": "Lowe's", "Sector": "Consumo", "Yield %": 1.95, "Meses Cierre": "Abr/Jul/Oct/Ene", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Julio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Agosto 2026"},
    {"Ticker": "K", "Empresa": "Kellanova (Kellogg)", "Sector": "Consumo", "Yield %": 3.60, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "GIS", "Empresa": "General Mills", "Sector": "Consumo", "Yield %": 3.40, "Meses Cierre": "Feb/May/Ago/Nov", "Meses Pres.": "Mar/Jun/Sep/Dic", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Junio 2026", "Próx. Pago": "Agosto 2026"},
    {"Ticker": "MO", "Empresa": "Altria Group", "Sector": "Consumo", "Yield %": 8.40, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Ene/Abr/Jul/Oct", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "PM", "Empresa": "Philip Morris", "Sector": "Consumo", "Yield %": 5.25, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Ene/Abr/Jul/Oct", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "MCD", "Empresa": "McDonald's", "Sector": "Consumo", "Yield %": 2.15, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "SBUX", "Empresa": "Starbucks", "Sector": "Consumo", "Yield %": 2.50, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Agosto 2026"},
    {"Ticker": "NKE", "Empresa": "Nike", "Sector": "Consumo", "Yield %": 1.65, "Meses Cierre": "Feb/May/Ago/Nov", "Meses Pres.": "Mar/Jun/Sep/Dic", "Ciclo Pagos": "Abr/Jul/Oct/Dic", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Junio 2026", "Próx. Pago": "Julio 2026"},

    # --- SALUD & BIOTECNOLOGÍA ---
    {"Ticker": "JNJ", "Empresa": "J&J", "Sector": "Salud", "Yield %": 3.05, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "PFE", "Empresa": "Pfizer", "Sector": "Salud", "Yield %": 5.85, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "ABBV", "Empresa": "AbbVie", "Sector": "Salud", "Yield %": 3.60, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Mayo 2026"},
    {"Ticker": "LLY", "Empresa": "Eli Lilly", "Sector": "Salud", "Yield %": 0.60, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "UNH", "Empresa": "UnitedHealth", "Sector": "Salud", "Yield %": 1.45, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "AMGN", "Empresa": "Amgen", "Sector": "Salud", "Yield %": 2.90, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "CVS", "Empresa": "CVS Health", "Sector": "Salud", "Yield %": 3.80, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Agosto 2026"},

    # --- FINANZAS & BANCARIOS ---
    {"Ticker": "JPM", "Empresa": "JP Morgan", "Sector": "Financiero", "Yield %": 2.40, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Ene/Abr/Jul/Oct", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "V", "Empresa": "Visa", "Sector": "Financiero", "Yield %": 0.78, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "MA", "Empresa": "Mastercard", "Sector": "Financiero", "Yield %": 0.65, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Agosto 2026"},
    {"Ticker": "BAC", "Empresa": "Bank of America", "Sector": "Financiero", "Yield %": 2.60, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "GS", "Empresa": "Goldman Sachs", "Sector": "Financiero", "Yield %": 2.70, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "AXP", "Empresa": "Amex", "Sector": "Financiero", "Yield %": 1.20, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Agosto 2026"},
    {"Ticker": "SAN", "Empresa": "Santander", "Sector": "Financiero", "Yield %": 4.50, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "May/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Noviembre 2026"},

    # --- ENERGÍA, MINERÍA e INDUSTRIALES ---
    {"Ticker": "XOM", "Empresa": "Exxon Mobil", "Sector": "Energía", "Yield %": 3.35, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "CVX", "Empresa": "Chevron", "Sector": "Energía", "Yield %": 4.15, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "PBR", "Empresa": "Petrobras", "Sector": "Energía", "Yield %": 12.80, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Trimestral", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "VALE", "Empresa": "Vale", "Sector": "Minería", "Yield %": 8.10, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Mar/Sep", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Septiembre 2026"},
    {"Ticker": "GOLD", "Empresa": "Barrick Gold", "Sector": "Minería", "Yield %": 2.25, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "CAT", "Empresa": "Caterpillar", "Sector": "Industrial", "Yield %": 1.65, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Agosto 2026"},
    {"Ticker": "GE", "Empresa": "GE Aerospace", "Sector": "Industrial", "Yield %": 0.35, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Ene/Abr/Jul/Oct", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "LMT", "Empresa": "Lockheed Martin", "Sector": "Defensa", "Yield %": 2.60, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "RTX", "Empresa": "Raytheon Tech", "Sector": "Defensa", "Yield %": 2.40, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "UPS", "Empresa": "UPS", "Sector": "Logística", "Yield %": 4.50, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "FDX", "Empresa": "FedEx", "Sector": "Logística", "Yield %": 1.95, "Meses Cierre": "Ago/Nov/Feb/May", "Meses Pres.": "Sep/Dic/Mar/Jun", "Ciclo Pagos": "Abr/Jul/Oct/Ene", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Junio 2026", "Próx. Pago": "Julio 2026"},

    # --- COMUNICACIONES & RENTA MENSUAL ---
    {"Ticker": "T", "Empresa": "AT&T", "Sector": "Comunicaciones", "Yield %": 6.45, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Agosto 2026"},
    {"Ticker": "VZ", "Empresa": "Verizon", "Sector": "Comunicaciones", "Yield %": 6.65, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Agosto 2026"},
    {"Ticker": "O", "Empresa": "Realty Income", "Sector": "Inmobiliario", "Yield %": 5.85, "Meses Cierre": "Mensual", "Meses Pres.": "Feb/May/Ago/Nov", "Ciclo Pagos": "MENSUAL", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "MAIN", "Empresa": "Main Street", "Sector": "Financiero", "Yield %": 6.25, "Meses Cierre": "Mensual", "Meses Pres.": "Feb/May/Ago/Nov", "Ciclo Pagos": "MENSUAL", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "STAG", "Empresa": "STAG Industrial", "Sector": "Inmobiliario", "Yield %": 4.10, "Meses Cierre": "Mensual", "Meses Pres.": "Feb/May/Ago/Nov", "Ciclo Pagos": "MENSUAL", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},

    # --- PANEL MERVAL (PANEL LÍDER) ---
    {"Ticker": "ALUA", "Empresa": "Aluar", "Sector": "Merval", "Yield %": 3.20, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "May/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Noviembre 2026"},
    {"Ticker": "GGAL", "Empresa": "Galicia", "Sector": "Merval", "Yield %": 4.50, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Mayo/Junio", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "YPFD", "Empresa": "YPF", "Sector": "Merval", "Yield %": 1.50, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Variable", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Julio 2026*"},
    {"Ticker": "TXAR", "Empresa": "Ternium", "Sector": "Merval", "Yield %": 4.15, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Mayo/Junio", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "BMA", "Empresa": "Banco Macro", "Sector": "Merval", "Yield %": 4.80, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Mayo/Junio", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "PAMP", "Empresa": "Pampa Energía", "Sector": "Merval", "Yield %": 0.00, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Reinvierte", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "N/A"},
    {"Ticker": "CEPU", "Empresa": "Central Puerto", "Sector": "Merval", "Yield %": 3.95, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Variable", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026*"},
    {"Ticker": "SUPV", "Empresa": "Banco Supervielle", "Sector": "Merval", "Yield %": 3.40, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Mayo/Junio", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "BBAR", "Empresa": "Banco Francés", "Sector": "Merval", "Yield %": 4.10, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Mayo/Junio", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "COME", "Empresa": "Comercial del Plata", "Sector": "Merval", "Yield %": 4.90, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Anual", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "TRAN", "Empresa": "Transener", "Sector": "Merval", "Yield %": 2.10, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Variable", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "IRSA", "Empresa": "IRSA", "Sector": "Merval", "Yield %": 5.25, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Variable", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "CRES", "Empresa": "Cresud", "Sector": "Merval", "Yield %": 4.85, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Variable", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "TGSU2", "Empresa": "TGS", "Sector": "Merval", "Yield %": 3.15, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Variable", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "TGNO4", "Empresa": "TGN", "Sector": "Merval", "Yield %": 2.90, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Variable", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "MIRG", "Empresa": "Mirgor", "Sector": "Merval", "Yield %": 1.80, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Anual", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "BYMA", "Empresa": "BYMA", "Sector": "Merval", "Yield %": 2.45, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Trimestral", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Julio 2026"},

    # --- PANEL GENERAL ARGENTINA ---
    {"Ticker": "AGRO", "Empresa": "Agrometal", "Sector": "Panel General", "Yield %": 2.80, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Anual", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "MOLI", "Empresa": "Molinos", "Sector": "Panel General", "Yield %": 3.50, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "Junio", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "LEDE", "Empresa": "Ledesma", "Sector": "Panel General", "Yield %": 2.10, "Meses Cierre": "Mayo", "Meses Pres.": "Agosto", "Ciclo Pagos": "Diciembre", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Diciembre 2026"},
    {"Ticker": "SAMI", "Empresa": "San Miguel", "Sector": "Panel General", "Yield %": 0.00, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Mar", "Ciclo Pagos": "N/A", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "N/A"},
    {"Ticker": "CELU", "Empresa": "Celulosa", "Sector": "Panel General", "Yield %": 1.50, "Meses Cierre": "Mayo", "Meses Pres.": "Agosto", "Ciclo Pagos": "Variable", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Septiembre 2026"},
    {"Ticker": "MORI", "Empresa": "Morixe", "Sector": "Panel General", "Yield %": 0.00, "Meses Cierre": "May", "Meses Pres.": "Julio", "Ciclo Pagos": "N/A", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "N/A"},
    {"Ticker": "CAPX", "Empresa": "Capex", "Sector": "Panel General", "Yield %": 4.10, "Meses Cierre": "Abr", "Meses Pres.": "Jun", "Ciclo Pagos": "Anual", "Próx. Cierre": "Abril 2027", "Próx. Pres.": "Junio 2026", "Próx. Pago": "Julio 2026"},

    # --- BANCOS BRASIL & OTROS ---
    {"Ticker": "BBD", "Empresa": "Banco Bradesco", "Sector": "Brasil", "Yield %": 7.85, "Meses Cierre": "Mensual", "Meses Pres.": "Feb/May/Ago/Nov", "Ciclo Pagos": "MENSUAL", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "ITUB", "Empresa": "Itaú Unibanco", "Sector": "Brasil", "Yield %": 6.55, "Meses Cierre": "Mensual", "Meses Pres.": "Feb/May/Ago/Nov", "Ciclo Pagos": "MENSUAL", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "BBDC4", "Empresa": "Bradesco PN", "Sector": "Brasil", "Yield %": 7.90, "Meses Cierre": "Mensual", "Meses Pres.": "Feb/May/Ago/Nov", "Ciclo Pagos": "MENSUAL", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "SANB11", "Empresa": "Santander Brasil", "Sector": "Brasil", "Yield %": 6.10, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Trimestral", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Julio 2026"},

    # --- MÁS ACCIONES USA (VARIOS) ---
    {"Ticker": "ADBE", "Empresa": "Adobe", "Sector": "Tecnología", "Yield %": 0.00, "Meses Cierre": "Feb/May/Ago/Nov", "Meses Pres.": "Mar/Jun/Sep/Dic", "Ciclo Pagos": "Reinvierte", "Próx. Cierre": "Mayo 2026", "Próx. Pres.": "Junio 2026", "Próx. Pago": "N/A"},
    {"Ticker": "CRM", "Empresa": "Salesforce", "Sector": "Tecnología", "Yield %": 0.35, "Meses Cierre": "Ene/Abr/Jul/Oct", "Meses Pres.": "Feb/May/Ago/Nov", "Ciclo Pagos": "Abr/Jul/Oct/Dic", "Próx. Cierre": "Julio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Julio 2026"},
    {"Ticker": "PYPL", "Empresa": "PayPal", "Sector": "Fintech", "Yield %": 0.00, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Reinvierte", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "N/A"},
    {"Ticker": "MELI", "Empresa": "Mercado Libre", "Sector": "E-commerce", "Yield %": 0.00, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Reinvierte", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "N/A"},
    {"Ticker": "ABT", "Empresa": "Abbott Lab", "Sector": "Salud", "Yield %": 2.10, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Agosto 2026"},
    {"Ticker": "BMY", "Empresa": "Bristol-Myers", "Sector": "Salud", "Yield %": 5.40, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Feb", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Agosto 2026"},
    {"Ticker": "MMM", "Empresa": "3M Company", "Sector": "Industrial", "Yield %": 2.90, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "HON", "Empresa": "Honeywell", "Sector": "Industrial", "Yield %": 2.15, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "RTX", "Empresa": "RTX Corp", "Sector": "Defensa", "Yield %": 2.45, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "AMGN", "Empresa": "Amgen", "Sector": "Salud", "Yield %": 2.80, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "GILD", "Empresa": "Gilead Sciences", "Sector": "Salud", "Yield %": 4.60, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "May/Ago/Nov/Feb", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "IBM", "Empresa": "IBM", "Sector": "Tecnología", "Yield %": 3.45, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "VZ", "Empresa": "Verizon", "Sector": "Comunicaciones", "Yield %": 6.65, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Agosto 2026"},
    {"Ticker": "T", "Empresa": "AT&T", "Sector": "Comunicaciones", "Yield %": 6.45, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Agosto 2026"},
    {"Ticker": "UPS", "Empresa": "UPS", "Sector": "Logística", "Yield %": 4.45, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "CAT", "Empresa": "Caterpillar", "Sector": "Industrial", "Yield %": 1.65, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Agosto 2026"},
    {"Ticker": "DE", "Empresa": "John Deere", "Sector": "Industrial", "Yield %": 1.55, "Meses Cierre": "Ene/Abr/Jul/Oct", "Meses Pres.": "Feb/May/Ago/Nov", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Julio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Agosto 2026"},
    {"Ticker": "NEE", "Empresa": "NextEra Energy", "Sector": "Energía", "Yield %": 3.20, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "BP", "Empresa": "BP PLC", "Sector": "Energía", "Yield %": 4.80, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Feb/May/Ago/Nov", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Septiembre 2026"},
    {"Ticker": "SHEL", "Empresa": "Shell", "Sector": "Energía", "Yield %": 3.90, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Feb/May/Ago/Nov", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Septiembre 2026"},
    {"Ticker": "D", "Empresa": "Dominion Energy", "Sector": "Energía", "Yield %": 5.10, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Feb/May/Ago/Nov", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Septiembre 2026"},
    {"Ticker": "SO", "Empresa": "Southern Co", "Sector": "Energía", "Yield %": 3.80, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Feb/May/Ago/Nov", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Septiembre 2026"},
    {"Ticker": "FCX", "Empresa": "Freeport-McMo", "Sector": "Minería", "Yield %": 0.80, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Feb/May/Ago/Nov", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Agosto 2026"},
    {"Ticker": "NEM", "Empresa": "Newmont", "Sector": "Minería", "Yield %": 2.40, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "SCCO", "Empresa": "Southern Copper", "Sector": "Minería", "Yield %": 3.50, "Meses Cierre": "Mar/Jun/Sep/Dic", "Meses Pres.": "Abr/Jul/Oct/Ene", "Ciclo Pagos": "Mar/Jun/Sep/Dic", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Julio 2026", "Próx. Pago": "Junio 2026"},
    {"Ticker": "RIO", "Empresa": "Rio Tinto", "Sector": "Minería", "Yield %": 6.80, "Meses Cierre": "Jun/Dic", "Meses Pres.": "Feb/Ago", "Ciclo Pagos": "Abr/Sep", "Próx. Cierre": "Junio 2026", "Próx. Pres.": "Agosto 2026", "Próx. Pago": "Septiembre 2026"}
]

# 3. Procesamiento y Filtros
df = pd.DataFrame(acciones)
st.sidebar.header("🔍 Filtros Maestro")
st.sidebar.info(f"Total de acciones cargadas: {len(df)}")

f_sector = st.sidebar.multiselect("Filtrar Sectores:", options=sorted(df["Sector"].unique()), default=df["Sector"].unique())
f_ticker = st.sidebar.text_input("Buscar Ticker (ej: AAPL):").upper()
f_yield = st.sidebar.slider("Yield Mínimo (%)", 0.0, 15.0, 0.0)

# Filtrado dinámico
df_final = df[df["Sector"].isin(f_sector) & (df["Yield %"] >= f_yield)]
if f_ticker:
    df_final = df_final[df_final["Ticker"].str.contains(f_ticker)]

# 4. Mostrar Tabla Principal
st.dataframe(
    df_final.sort_values(by="Ticker"),
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
st.markdown("""
### 💡 Guía Rápida para el Monitor:
1. **Comprar:** Busca acciones con **Yield Anual > 4%** para flujo de caja (como PBR, MO, O).
2. **Timing:** Si hoy es 17 de Mayo, mira las que tienen **Próximo Pago en Junio/Julio**. Es el momento de revisar tu liquidez.
3. **Merval:** Los datos con (*) son proyecciones; Argentina siempre depende de la Asamblea de Accionistas.
""")
