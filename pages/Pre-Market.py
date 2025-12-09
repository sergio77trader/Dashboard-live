import streamlit as st
import yfinance as yf
import pandas as pd
import time

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SystemaTrader - Pre-Market Monitor")

# --- BASE DE DATOS MAESTRA (TODOS LOS CEDEARS/ADRs LÍQUIDOS) ---
MARKET_DATA = {
    "🇦🇷 Argentina (ADRs)": [
        "GGAL", "YPF", "BMA", "PAMP", "TGS", "CEPU", "EDN", "BFR", "SUPV", 
        "CRESY", "IRS", "TEO", "LOMA", "DESP", "VIST", "GLOB", "MELI", "BIOX"
    ],
    "🇺🇸 Big Tech & AI": [
        "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "NFLX", "AMD", "INTC", 
        "QCOM", "AVGO", "TSM", "CRM", "ORCL", "IBM", "CSCO", "ADBE", "PLTR", 
        "ARM", "SMCI", "TXN", "ADI", "MU"
    ],
    "🏦 Financiero & Pagos": [
        "JPM", "BAC", "C", "WFC", "GS", "MS", "V", "MA", "AXP", "BRK-B", 
        "PYPL", "SQ", "COIN", "BLK"
    ],
    "🛒 Consumo Masivo & Retail": [
        "KO", "PEP", "MCD", "SBUX", "DIS", "NKE", "WMT", "COST", "TGT", "HD", 
        "PG", "CL", "MO", "JD", "BABA", "BIDU"
    ],
    "🛢️ Energía & Industria": [
        "XOM", "CVX", "SLB", "OXY", "BA", "CAT", "MMM", "GE", "DE", "F", "GM", 
        "LMT", "RTX", "HES", "VLO"
    ],
    "💊 Salud & Pharma": [
        "JNJ", "PFE", "MRK", "LLY", "ABBV", "UNH", "BMY", "AZN", "TMO"
    ],
    "🇧🇷 Brasil & Emergentes": [
        "PBR", "VALE", "ITUB", "BBD", "ERJ", "EEM"
    ],
    "🌎 ETFs (Índices)": [
        "SPY", "QQQ", "IWM", "DIA", "XLE", "XLF", "ARKK", "EWZ", "GLD", "SLV"
    ]
}

# Generamos la lista completa plana y sin duplicados
ALL_TICKERS = sorted(list(set([item for sublist in MARKET_DATA.values() for item in sublist])))

# --- ESTILOS DE COLOR ---
def color_change(val):
    if isinstance(val, (float, int)):
        if val > 0: return 'color: #00FF00; font-weight: bold' # Verde Neón
        elif val < 0: return 'color: #FF4500; font-weight: bold' # Rojo Fuerte
    return ''

# --- MOTOR DE DATOS EN VIVO (PRE-MARKET) ---
# Cache corta de 1 minuto para no saturar pero mantener frescura
@st.cache_data(ttl=60)
def get_live_data(ticker_list):
    data = []
    
    # Barra de progreso
    prog = st.progress(0, text="Conectando con NYSE/NASDAQ (Live/Pre-Market)...")
    total = len(ticker_list)
    
    # Creamos objeto Tickers para optimizar la inicialización
    tickers_obj = yf.Tickers(" ".join(ticker_list))
    
    for i, t in enumerate(ticker_list):
        try:
            # fast_info accede a la data en tiempo real sin descargar histórico
            info = tickers_obj.tickers[t].fast_info
            
            # last_price: Precio actual (incluye Pre-Market si el mercado está cerrado)
            last_price = info.last_price
            # previous_close: Cierre de la sesión anterior
            prev_close = info.previous_close
            
            if last_price and prev_close:
                change = last_price - prev_close
                pct_change = ((last_price - prev_close) / prev_close) * 100
                
                data.append({
                    "Symbol": t,
                    "Precio Vivo ($)": last_price,
                    "Cierre Ayer ($)": prev_close,
                    "Cambio ($)": change,
                    "% Var": pct_change
                })
        except:
            # Si falla un ticker puntual, lo saltamos y seguimos
            pass
        
        # Actualizamos la barra cada 3 activos para que sea visualmente fluido
        if i % 3 == 0: 
            prog.progress((i + 1) / total)
            
    prog.empty()
    return pd.DataFrame(data)

# --- INTERFAZ ---
st.title("🚀 SystemaTrader: Pre-Market Monitor")
st.caption("Detecta Gaps y Movimientos en Tiempo Real (Datos de Mercado de Origen)")

col_btn, col_info = st.columns([1, 3])
with col_btn:
    if st.button("⚡ ESCANEAR AHORA", type="primary"):
        st.cache_data.clear()
        st.rerun()
with col_info:
    st.info("Nota: Este escáner revisa precio por precio. El escaneo total puede tardar unos 45 segundos.")

# --- PESTAÑAS ---
tab1, tab2 = st.tabs(["📺 Tablero Resumen", "🌎 Mercado Total (Todos)"])

# === PESTAÑA 1: RESUMEN ===
with tab1:
    col1, col2 = st.columns(2)
    
    # ARGENTINA
    with col1:
        st.subheader("🇦🇷 Argentina (ADRs)")
        df_arg = get_live_data(MARKET_DATA["🇦🇷 Argentina (ADRs)"])
        
        if not df_arg.empty:
            st.dataframe(
                df_arg.style.map(color_change, subset=['Cambio ($)', '% Var']),
                column_config={
                    "Symbol": st.column_config.TextColumn("Activo", width="small"),
                    "Precio Vivo ($)": st.column_config.NumberColumn("Precio (Live)", format="$%.2f"),
                    "Cierre Ayer ($)": st.column_config.NumberColumn("Cierre Ayer", format="$%.2f"),
                    "Cambio ($)": st.column_config.NumberColumn("Dif", format="%.2f"),
                    "% Var": st.column_config.NumberColumn("Var %", format="%.2f%%")
                },
                use_container_width=True, hide_index=True, height=600
            )

    # EEUU
    with col2:
        st.subheader("🇺🇸 Wall Street (Selección)")
        # Selección estratégica
        usa_sel = MARKET_DATA["🇺🇸 Big Tech & AI"][:10] + ["MELI", "TSLA", "KO", "XOM"]
        df_usa = get_live_data(usa_sel)
        
        if not df_usa.empty:
            st.dataframe(
                df_usa.style.map(color_change, subset=['Cambio ($)', '% Var']),
                column_config={
                    "Symbol": st.column_config.TextColumn("Activo", width="small"),
                    "Precio Vivo ($)": st.column_config.NumberColumn("Precio (Live)", format="$%.2f"),
                    "Cierre Ayer ($)": st.column_config.NumberColumn("Cierre Ayer", format="$%.2f"),
                    "Cambio ($)": st.column_config.NumberColumn("Dif", format="%.2f"),
                    "% Var": st.column_config.NumberColumn("Var %", format="%.2f%%")
                },
                use_container_width=True, hide_index=True, height=600
            )

# === PESTAÑA 2: TODO EL MERCADO ===
with tab2:
    c_sel, c_kpi = st.columns([3, 1])
    with c_sel:
        sector = st.selectbox("Seleccionar Sector:", ["TODOS (Puede tardar 1 min)"] + list(MARKET_DATA.keys()))
    
    # Lógica de Selección
    if "TODOS" in sector:
        target = ALL_TICKERS # Lista completa de ~135 activos
    else:
        target = MARKET_DATA[sector]
    
    if st.button("🔎 Analizar Sector en Vivo"):
        with st.spinner(f"Escaneando {len(target)} activos en tiempo real..."):
            df_all = get_live_data(target)
        
        if not df_all.empty:
            # Ordenar por Mayor Variación (Volatilidad Pre-Market)
            df_all = df_all.sort_values("% Var", ascending=False)
            
            best = df_all.iloc[0]
            worst = df_all.iloc[-1]
            
            with c_kpi:
                st.metric("Total Activos", len(df_all))
            
            # KPI Cards
            c1, c2 = st.columns(2)
            c1.success(f"🚀 Top Gainer: {best['Symbol']} ({best['% Var']:.2f}%)")
            c2.error(f"🐻 Top Loser: {worst['Symbol']} ({worst['% Var']:.2f}%)")
            
            st.dataframe(
                df_all.style.map(color_change, subset=['Cambio ($)', '% Var']),
                column_config={
                    "Symbol": "Activo",
                    "Precio Vivo ($)": st.column_config.NumberColumn(format="$%.2f"),
                    "Cierre Ayer ($)": st.column_config.NumberColumn(format="$%.2f"),
                    "Cambio ($)": st.column_config.NumberColumn(format="%.2f"),
                    "% Var": st.column_config.NumberColumn("Var %", format="%.2f%%")
                },
                use_container_width=True, hide_index=True, height=800
            )
