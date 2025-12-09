import streamlit as st
import yfinance as yf
import pandas as pd
import time

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SystemaTrader - Pre-Market Monitor")

# --- BASE DE DATOS (MERCADO COMPLETO) ---
MARKET_DATA = {
    "🇦🇷 Argentina (ADRs)": [
        "GGAL", "YPF", "BMA", "PAMP", "TGS", "CEPU", "EDN", "BFR", "SUPV", 
        "CRESY", "IRS", "TEO", "LOMA", "DESP", "VIST", "GLOB", "MELI", "BIOX"
    ],
    "🇺🇸 Big Tech & AI": [
        "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "NFLX", "AMD", "INTC", 
        "QCOM", "AVGO", "TSM", "CRM", "ORCL", "IBM", "CSCO", "ADBE", "PLTR"
    ],
    "🏦 Financiero & Pagos": [
        "JPM", "BAC", "C", "WFC", "GS", "MS", "V", "MA", "AXP", "BRK-B", 
        "PYPL", "SQ", "COIN"
    ],
    "🛒 Consumo Masivo & Retail": [
        "KO", "PEP", "MCD", "SBUX", "DIS", "NKE", "WMT", "COST", "TGT", "HD", 
        "PG", "CL", "MO"
    ],
    "🛢️ Energía & Industria": [
        "XOM", "CVX", "SLB", "OXY", "BA", "CAT", "MMM", "GE", "DE", "F", "GM", 
        "LMT", "RTX"
    ],
    "💊 Salud & Pharma": [
        "JNJ", "PFE", "MRK", "LLY", "ABBV", "UNH", "BMY", "AZN"
    ],
    "🇨🇳 China & 🇧🇷 Brasil": [
        "BABA", "JD", "BIDU", "NIO", "PBR", "VALE", "ITUB", "BBD", "ERJ"
    ],
    "🌎 ETFs (Índices)": [
        "SPY", "QQQ", "IWM", "DIA", "EEM", "XLE", "XLF", "ARKK", "EWZ", "GLD", "SLV"
    ]
}

ALL_TICKERS = sorted(list(set([item for sublist in MARKET_DATA.values() for item in sublist])))

# --- ESTILOS DE COLOR ---
def color_change(val):
    if isinstance(val, (float, int)):
        if val > 0: return 'color: #00FF00; font-weight: bold' # Verde
        elif val < 0: return 'color: #FF4500; font-weight: bold' # Rojo
    return ''

# --- MOTOR DE DATOS EN VIVO (PRE-MARKET) ---
# Usamos cache corta (30 seg) para tener datos frescos
@st.cache_data(ttl=30)
def get_live_data(ticker_list):
    data = []
    
    # Creamos barra de progreso porque esta consulta es mas pesada
    prog = st.progress(0, text="Escaneando Pre-Market/Live...")
    total = len(ticker_list)
    
    # Optimizacion: Usamos Tickers (plural) para inicializar objetos, pero fast_info es individual
    tickers_obj = yf.Tickers(" ".join(ticker_list))
    
    for i, t in enumerate(ticker_list):
        try:
            # Usamos fast_info para obtener el precio REAL del momento (incluye pre-market)
            info = tickers_obj.tickers[t].fast_info
            
            # last_price: El último precio operado (puede ser pre-market)
            last_price = info.last_price
            # previous_close: El cierre de ayer
            prev_close = info.previous_close
            
            if last_price and prev_close:
                change = last_price - prev_close
                pct_change = ((last_price - prev_close) / prev_close) * 100
                
                data.append({
                    "Symbol": t,
                    "Precio Vivo ($)": last_price,
                    "Cierre Ayer ($)": prev_close,
                    "Cambio ($)": change,
                    "% Var (Live)": pct_change
                })
        except:
            pass
        
        # Actualizar barra cada 5 items para no saturar UI
        if i % 5 == 0: prog.progress((i + 1) / total)
            
    prog.empty()
    return pd.DataFrame(data)

# --- INTERFAZ ---
st.title("🚀 SystemaTrader: Pre-Market Monitor")
st.caption("Detecta Gaps y Movimientos en Tiempo Real (Comparado con Cierre Anterior)")

col_btn, col_info = st.columns([1, 4])
with col_btn:
    if st.button("⚡ ESCANEAR AHORA", type="primary"):
        st.cache_data.clear()
        st.rerun()
with col_info:
    st.info("Este motor busca el último precio operado. Si el mercado está cerrado, muestra el Pre-Market o Post-Market.")

tab1, tab2 = st.tabs(["📺 Tablero Resumen", "🌎 Escáner Total"])

# === PESTAÑA 1: RESUMEN ===
with tab1:
    col1, col2 = st.columns(2)
    
    # ARGENTINA
    with col1:
        st.subheader("🇦🇷 Argentina (ADRs)")
        df_arg = get_live_data(MARKET_DATA["🇦🇷 Argentina (ADRs)"])
        
        if not df_arg.empty:
            st.dataframe(
                df_arg.style.map(color_change, subset=['Cambio ($)', '% Var (Live)']),
                column_config={
                    "Symbol": st.column_config.TextColumn("Activo", width="small"),
                    "Precio Vivo ($)": st.column_config.NumberColumn("Precio (Live)", format="$%.2f"),
                    "Cierre Ayer ($)": st.column_config.NumberColumn("Cierre Ayer", format="$%.2f"),
                    "Cambio ($)": st.column_config.NumberColumn("Dif", format="%.2f"),
                    "% Var (Live)": st.column_config.NumberColumn("Var %", format="%.2f%%")
                },
                use_container_width=True, hide_index=True, height=600
            )

    # EEUU
    with col2:
        st.subheader("🇺🇸 Wall Street (Selección)")
        # Selección mixta para el resumen
        usa_sel = MARKET_DATA["🇺🇸 Big Tech & AI"][:8] + ["TSLA", "MELI", "VIST", "XOM", "KO"]
        df_usa = get_live_data(usa_sel)
        
        if not df_usa.empty:
            st.dataframe(
                df_usa.style.map(color_change, subset=['Cambio ($)', '% Var (Live)']),
                column_config={
                    "Symbol": st.column_config.TextColumn("Activo", width="small"),
                    "Precio Vivo ($)": st.column_config.NumberColumn("Precio (Live)", format="$%.2f"),
                    "Cierre Ayer ($)": st.column_config.NumberColumn("Cierre Ayer", format="$%.2f"),
                    "Cambio ($)": st.column_config.NumberColumn("Dif", format="%.2f"),
                    "% Var (Live)": st.column_config.NumberColumn("Var %", format="%.2f%%")
                },
                use_container_width=True, hide_index=True, height=600
            )

# === PESTAÑA 2: TODO EL MERCADO ===
with tab2:
    c_sel, c_kpi = st.columns([3, 1])
    with c_sel:
        sector = st.selectbox("Seleccionar Sector:", ["TODOS"] + list(MARKET_DATA.keys()))
    
    target = ALL_TICKERS if sector == "TODOS" else MARKET_DATA[sector]
    
    if st.button("🔎 Analizar Sector en Vivo"):
        # Limitamos "TODOS" a los primeros 50 para no tardar una eternidad en modo live
        if sector == "TODOS":
            st.warning("Analizando los primeros 60 activos por velocidad...")
            target = target[:60]
            
        df_all = get_live_data(target)
        
        if not df_all.empty:
            df_all = df_all.sort_values("% Var (Live)", ascending=False)
            
            best = df_all.iloc[0]
            worst = df_all.iloc[-1]
            
            c1, c2 = st.columns(2)
            c1.success(f"🚀 Top Gainer: {best['Symbol']} ({best['% Var (Live)']:.2f}%)")
            c2.error(f"🐻 Top Loser: {worst['Symbol']} ({worst['% Var (Live)']:.2f}%)")
            
            st.dataframe(
                df_all.style.map(color_change, subset=['Cambio ($)', '% Var (Live)']),
                column_config={
                    "Symbol": "Activo",
                    "Precio Vivo ($)": st.column_config.NumberColumn(format="$%.2f"),
                    "Cierre Ayer ($)": st.column_config.NumberColumn(format="$%.2f"),
                    "Cambio ($)": st.column_config.NumberColumn(format="%.2f"),
                    "% Var (Live)": st.column_config.NumberColumn(format="%.2f%%")
                },
                use_container_width=True, hide_index=True, height=800
            )
