import streamlit as st
import yfinance as yf
import pandas as pd

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SystemaTrader - Global Watchlist")

# --- BASE DE DATOS MAESTRA (CEDEARS + ADRS) ---
# Organizada por sectores para fácil acceso
MARKET_DATA = {
    "🇦🇷 Argentina (ADRs)": [
        "GGAL", "YPF", "BMA", "PAMP", "TGS", "CEPU", "EDN", "BFR", "SUPV", 
        "CRESY", "IRS", "TEO", "LOMA", "DESP", "VIST", "GLOB", "MELI", "BIOX"
    ],
    "🇺🇸 Big Tech (Magnificent 7)": [
        "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "TSLA", "META", "NFLX"
    ],
    "🤖 Semiconductores & AI": [
        "AMD", "INTC", "QCOM", "AVGO", "TSM", "MU", "ARM", "SMCI", "TXN", "ADI"
    ],
    "🏦 Financiero (US)": [
        "JPM", "BAC", "C", "WFC", "GS", "MS", "V", "MA", "AXP", "BRK-B"
    ],
    "🛒 Consumo & Retail": [
        "KO", "PEP", "MCD", "SBUX", "DIS", "NKE", "WMT", "COST", "TGT", "HD"
    ],
    "🛢️ Energía & Industria": [
        "XOM", "CVX", "SLB", "BA", "CAT", "MMM", "GE", "DE", "F", "GM"
    ],
    "🇨🇳 China & Brasil": [
        "BABA", "JD", "BIDU", "PBR", "VALE", "ITUB", "BBD"
    ],
    "🚀 Cripto & Growth": [
        "COIN", "MSTR", "SQ", "PYPL", "UBER", "ABNB", "PLTR", "SHOP", "SNOW"
    ],
    "🌎 ETFs Clave": [
        "SPY", "QQQ", "IWM", "DIA", "EEM", "XLE", "XLF", "ARKK", "EWZ", "GLD", "SLV"
    ]
}

# Creamos una lista plana "ALL" para el escáner total
ALL_TICKERS = sorted(list(set([item for sublist in MARKET_DATA.values() for item in sublist])))

# --- MOTOR DE DATOS ---
@st.cache_data(ttl=60) # Actualiza cada 60 segundos si recargas
def get_quotes(ticker_list):
    if not ticker_list: return pd.DataFrame()
    
    try:
        # Descarga masiva optimizada
        df = yf.download(ticker_list, period="5d", progress=False)['Close']
        
        data = []
        for t in ticker_list:
            try:
                # Manejo de Series vs DataFrame
                if isinstance(df, pd.DataFrame) and t in df.columns:
                    series = df[t].dropna()
                elif isinstance(df, pd.Series) and df.name == t: # Caso de 1 solo ticker
                    series = df.dropna()
                else:
                    # Intento individual si falla el bulk
                    series = yf.Ticker(t).history(period="5d")['Close']
                
                if len(series) >= 2:
                    last_price = float(series.iloc[-1])
                    prev_price = float(series.iloc[-2])
                    
                    change = last_price - prev_price
                    # Cálculo porcentual directo (multiplicado por 100 para formato limpio)
                    pct_change = ((last_price - prev_price) / prev_price) * 100
                    
                    data.append({
                        "Symbol": t,
                        "Precio ($)": last_price,
                        "Cambio ($)": change,
                        "% Var": pct_change # Guardamos el número entero (ej: 1.5, no 0.015)
                    })
            except:
                continue
                
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return pd.DataFrame()

# --- INTERFAZ ---
st.title("📊 SystemaTrader: Global Market Watch")
st.caption("Monitor de Precios en Origen (NYSE/NASDAQ) - Sin efecto CCL")

if st.button("🔄 ACTUALIZAR PRECIOS", type="primary"):
    st.cache_data.clear()
    st.rerun()

# Pestañas para organizar la vista
tab1, tab2 = st.tabs(["📺 Dashboard Resumen", "🌎 Mercado Completo (All)"])

# --- TAB 1: TU VISTA PERSONALIZADA ---
with tab1:
    col1, col2 = st.columns(2)
    
    # IZQUIERDA: ARGENTINA
    with col1:
        st.subheader("🇦🇷 Argentina (ADRs)")
        with st.spinner("Cargando ADRs..."):
            df_arg = get_quotes(MARKET_DATA["🇦🇷 Argentina (ADRs)"])
        
        if not df_arg.empty:
            st.dataframe(
                df_arg,
                column_config={
                    "Symbol": st.column_config.TextColumn("Activo", width="small"),
                    "Precio ($)": st.column_config.NumberColumn("Precio", format="$%.2f"),
                    "Cambio ($)": st.column_config.NumberColumn("Dif", format="$%.2f"),
                    "% Var": st.column_config.NumberColumn("% Var", format="%.2f%%") # Muestra 1.50%
                },
                use_container_width=True, hide_index=True, height=500
            )

    # DERECHA: SELECCIÓN EEUU
    with col2:
        st.subheader("🇺🇸 Wall Street (Selección)")
        # Combinamos un par de listas clave para el resumen
        usa_selection = MARKET_DATA["🏦 Financiero (US)"] + MARKET_DATA["🛢️ Energía & Industria"]
        
        with st.spinner("Cargando USA..."):
            df_usa = get_quotes(usa_selection)
            
        if not df_usa.empty:
            st.dataframe(
                df_usa,
                column_config={
                    "Symbol": st.column_config.TextColumn("Activo", width="small"),
                    "Precio ($)": st.column_config.NumberColumn("Precio", format="$%.2f"),
                    "Cambio ($)": st.column_config.NumberColumn("Dif", format="$%.2f"),
                    "% Var": st.column_config.NumberColumn("% Var", format="%.2f%%")
                },
                use_container_width=True, hide_index=True, height=500
            )

# --- TAB 2: MERCADO TOTAL ---
with tab2:
    st.markdown("### 🔍 Explorador Total de CEDEARs")
    
    # Filtro por Sector
    sector = st.selectbox("Filtrar por Sector:", ["TODOS"] + list(MARKET_DATA.keys()))
    
    target_list = ALL_TICKERS if sector == "TODOS" else MARKET_DATA[sector]
    
    if st.button("🔎 Escanear Sector"):
        with st.spinner(f"Analizando {len(target_list)} activos..."):
            df_all = get_quotes(target_list)
            
        if not df_all.empty:
            # Ordenar por mayor variación (Volatilidad)
            df_all = df_all.sort_values("% Var", ascending=False)
            
            # KPI Cards Rápidas
            best = df_all.iloc[0]
            worst = df_all.iloc[-1]
            c1, c2, c3 = st.columns(3)
            c1.metric("Activos Analizados", len(df_all))
            c2.metric(f"🚀 Mejor: {best['Symbol']}", f"{best['% Var']:.2f}%")
            c3.metric(f"🐻 Peor: {worst['Symbol']}", f"{worst['% Var']:.2f}%")
            
            st.dataframe(
                df_all,
                column_config={
                    "Symbol": "Activo",
                    "Precio ($)": st.column_config.NumberColumn(format="$%.2f"),
                    "Cambio ($)": st.column_config.NumberColumn(format="$%.2f"),
                    "% Var": st.column_config.NumberColumn(format="%.2f%%")
                },
                use_container_width=True, hide_index=True, height=700
            )
