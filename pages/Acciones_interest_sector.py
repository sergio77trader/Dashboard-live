import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import re

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SystemaTrader - Options Screener Pro")

# --- BASE DE DATOS ---
CEDEAR_SET = {
    'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'TSLA', 'META', 'AMD', 'INTC', 'QCOM',
    'KO', 'PEP', 'WMT', 'PG', 'COST', 'MCD', 'SBUX', 'DIS', 'NKE',
    'XOM', 'CVX', 'SLB', 'PBR', 'VIST',
    'JPM', 'BAC', 'C', 'WFC', 'GS', 'V', 'MA', 'BRK-B',
    'GGAL', 'BMA', 'YPF', 'PAMP', 'TGS', 'CEPU', 'EDN', 'BFR', 'SUPV', 'CRESY', 'IRS', 'TEO', 'LOMA', 'DESP', 'GLOB', 'MELI', 'BIOX'
}

STOCK_GROUPS = {
    '🇦🇷 Argentina (ADRs en USA)': ['GGAL', 'YPF', 'BMA', 'PAMP', 'TGS', 'CEPU', 'EDN', 'BFR', 'SUPV', 'CRESY', 'IRS', 'TEO', 'LOMA', 'DESP', 'VIST', 'GLOB', 'MELI', 'BIOX'],
    '🇺🇸 Big Tech (Magnificent 7)': ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'TSLA', 'META'],
    '🇺🇸 High Volatility & AI': ['AMD', 'PLTR', 'COIN', 'MSTR', 'ARM', 'SMCI', 'TSM', 'AVGO'],
    '🇺🇸 Blue Chips (Dow Jones)': ['KO', 'MCD', 'JPM', 'DIS', 'BA', 'CAT', 'XOM', 'CVX', 'WMT']
}

# --- FUNCIONES AUXILIARES ---
def get_sentiment_label(ratio):
    if ratio is None: return "⚪ SIN DATA"
    if ratio < 0.7: return "🚀 ALCISTA"
    elif ratio > 1.0: return "🐻 BAJISTA"
    else: return "⚖️ NEUTRAL"

def generate_links(ticker, has_cedear):
    yahoo_link = f"https://finance.yahoo.com/quote/{ticker}/options"
    symbol = f"BCBA%3A{ticker}" if has_cedear else ticker
    tv_link = f"https://es.tradingview.com/chart/?symbol={symbol}"
    return yahoo_link, tv_link

# --- MOTOR DE ANÁLISIS V3.0 (TOLERANTE A FALLOS) ---
@st.cache_data(ttl=900)
def analyze_options_chain(ticker):
    # Estructura base de retorno (por si falla todo, devolvemos esto)
    base_data = {
        'Ticker': ticker, 'Price': 0.0, 'Max_Pain': 0.0, 'PC_Ratio': None,
        'Call_OI': 0, 'Put_OI': 0, 'Expiration': 'N/A', 'Has_Cedear': ticker in CEDEAR_SET,
        'Calls_DF': pd.DataFrame(), 'Puts_DF': pd.DataFrame(), 'Has_Options': False, 'Status': 'Error'
    }

    try:
        tk = yf.Ticker(ticker)
        
        # 1. OBTENER PRECIO (Intento robusto)
        current_price = 0.0
        try:
            if hasattr(tk, 'fast_info') and tk.fast_info.last_price:
                current_price = float(tk.fast_info.last_price)
        except: pass
        
        if current_price == 0:
            hist = tk.history(period="5d") # Buscamos 5 días por si es finde largo
            if not hist.empty:
                current_price = hist['Close'].iloc[-1]
        
        # Si no hay precio, el activo no existe o Yahoo está caído para él
        if current_price == 0:
            base_data['Status'] = 'Sin Precio'
            return base_data

        base_data['Price'] = current_price
        base_data['Status'] = 'Sin Opciones' # Asumimos esto hasta demostrar lo contrario

        # 2. BUSCAR OPCIONES (Iterando vencimientos)
        try:
            exps = tk.options
        except:
            exps = []
            
        if not exps:
            return base_data # Devolvemos solo precio
        
        # BUCLE INTELIGENTE: Buscamos en los primeros 3 vencimientos
        # (A veces el primero está vacío para acciones ilíquidas)
        found_data = False
        target_date = None
        calls, puts = pd.DataFrame(), pd.DataFrame()

        for date in exps[:3]: # Miramos las próximas 3 fechas
            try:
                opts = tk.option_chain(date)
                c, p = opts.calls, opts.puts
                # Solo aceptamos si hay algo de Open Interest acumulado
                if (not c.empty or not p.empty):
                    calls, puts = c, p
                    target_date = date
                    found_data = True
                    break # Encontramos datos, salimos del bucle
            except:
                continue
        
        if not found_data:
            return base_data # Devolvemos solo precio

        #
