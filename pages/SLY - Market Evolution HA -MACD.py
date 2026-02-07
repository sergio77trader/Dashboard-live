import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURACIÓN DEL SISTEMA
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SYSTEMATRADER | MACD EVOLUTION MATRIX")

st.markdown("""
<style>
    .stDataFrame { font-size: 11px; font-family: 'Roboto Mono', monospace; }
    h1 { color: #2962FF; font-weight: 800; border-bottom: 2px solid #2962FF; }
    h2 { color: #00E676; border-left: 5px solid #00E676; padding-left: 10px; }
    .stProgress > div > div > div > div { background-color: #2962FF; }
</style>
""", unsafe_allow_html=True)

if "sniper_results" not in st.session_state:
    st.session_state["sniper_results"] = []

# CONFIGURACIÓN DE DESCARGA
MACRO_CONFIG = {
    "1D": {"int": "1d", "per": "2y"},
    "1S": {"int": "1wk", "per": "5y"},
    "1M": {"int": "1mo", "per": "max"}
}

# ─────────────────────────────────────────────
# BÓVEDA DE ACTIVOS Y DETALLES DE COMPOSICIÓN
# ─────────────────────────────────────────────
ASSET_DATABASE = {
    "GLD": ["Metales / Refugio", "Oro físico (Gold Trust)"],
    "SLV": ["Metales / Riesgo", "Plata física (Silver Trust)"],
    "CPER": ["Metales / Industrial", "Futuros de Cobre (Termómetro Económico)"],
    "PPLT": ["Metales / Industrial", "Platino físico"],
    "XLK": ["Sector / Tech", "Tecnología: Apple, Microsoft, Nvidia"],
    "XLF": ["Sector / Finanzas", "Bancos y Seguros: JPM, Berkshire, Visa"],
    "XLE": ["Sector / Energía", "Petróleo y Gas: Exxon, Chevron"],
    "XLV": ["Sector / Salud", "Farmacéuticas: Eli Lilly, UnitedHealth"],
    "XLI": ["Sector / Industrial", "Maquinaria y Transporte: Caterpillar, GE"],
    "XLP": ["Sector / Consumo Básico", "Necesidades: Walmart, P&G, Coca-Cola"],
    "XLU": ["Sector / Utilities", "Energía Eléctrica y Agua"],
    "XLY": ["Sector / Consumo Disc.", "Lujo y Amazon, Tesla, McDonald's"],
    "XLB": ["Sector / Materiales", "Químicas y Minería"],
    "XLC": ["Sector / Comunicaciones", "Google, Meta, Netflix"],
    "XLRE": ["Sector / Real Estate", "Bienes Raíces y Alquileres"],
    "BTC-USD": ["Crypto / BTC", "Bitcoin (Reserva de valor digital)"],
    "ETH-USD": ["Crypto / Alt", "Ethereum (Contratos inteligentes)"],
    "SOL-USD": ["Crypto / Alt", "Solana (Alta velocidad)"],
    "SPY": ["Índice / S&P500", "500 empresas más grandes de EE.UU."],
    "QQQ": ["Índice / Nasdaq", "100 empresas tecnológicas líderes"],
    "EEM": ["Índice / Emergentes", "Mercados emergentes (Asia/Latam)"],
    "EWZ": ["Índice / Brasil", "Empresas líderes de Brasil (Ibovespa)"],
    "FXI": ["Índice / China", "Empresas chinas de gran capitalización"],
    "ARKK": ["Índice / Innovación", "Tecnología disruptiva y genómica"],
    "DX-Y.NYB": ["Macro / Dollar Index", "Valor del Dólar vs Canasta Global"],
    "TLT": ["Macro / Tesoro 20Y", "Bonos del Tesoro de EE.UU. a largo plazo"],
    "USO": ["Macro / Petróleo", "Petróleo Crudo WTI"],
    "VNQ": ["Macro / Real Estate", "Fideicomisos de inversión inmobiliaria"],
    "HYG": ["Macro / Junk Bonds", "Bonos corporativos de alto rendimiento"]
}

TICKERS_LIST = list(ASSET_DATABASE.keys())

# ─────────────────────────────────────────────
# MOTOR TÉCNICO SLY RECURSIVO
# ─────────────────────────────────────────────
def run_sly_engine(df):
    if df.empty or len(df) < 35: return 0, 0, None
    macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
    if macd is None: return 0, 0, None
    hist = macd['MACDh_12_26_9']
    ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    ha_open = np.zeros(len(df))
    ha_open[0] = (df['Open'].iloc[0] + df['Close'].iloc[0]) / 2
    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i-1] + ha_close.iloc[i-1]) / 2
    ha_dir = np.where(ha_close > ha_open, 1, -1)
    state, entry_px, entry_tm = 0, 0.0, None
    for i in range(1, len(df)):
        h, h_prev = hist.iloc[i], hist.iloc[i-1]
        hd, hd_prev = ha_dir[i], ha_dir[i-1]
        longC = (hd == 1 and hd_prev == -1 and h < 0 and h > h_prev)
        shrtC = (hd == -1 and hd_prev == 1 and h > 0 and h < h_prev)
        if longC: state, entry_px, entry_tm = 1, df['Close'].iloc[i], df.index[i]
        elif shrtC: state, entry_px, entry_tm = -1, df['Close'].iloc[i], df.index[i]
        elif state != 0:
            if (state == 1 and h < h_prev) or (state == -1 and h > h_prev): state = 0
    return state, entry_px, entry_tm

# ─────────────────────────────────────────────
# ANALIZADOR
# ─────────────────────────────────────────────
def analyze_asset(symbol):
    row = {"Categoría": ASSET_DATABASE[symbol][0], "Activo": symbol, "Composición": ASSET_DATABASE[symbol][1]}
    current_price = None
    for tf_key, config in MACRO_CONFIG.items():
        try:
            df = yf.download(symbol, interval=config['int'], period=config['per'], progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if df.empty: continue
            if tf_key == "1D": current_price = df['Close'].iloc[-1]
            st_val, px_in, tm_in = run_sly_engine(df)
            if st_val != 0:
                pnl = (df['Close'].iloc[-1] - px_in) / px_in * 100 if st_val == 1 else (px_in - df['Close'].iloc[-1]) / px_in * 100
                row[f"{tf_key} Signal"] = "LONG 🟢" if st_val == 1 else "SHORT 🔴"
                row[f"{tf_key} Fecha"] = tm_in.strftime("%d/%m/%y")
                row[f"{tf_key} PnL"] = f"{pnl:.2f}%"
            else:
                row[f"{tf_key} Signal"] = "FUERA ⚪"
                row[f"{tf_key} Fecha"] = "-"
                row[f"{tf_key} PnL"] = "-"
        except: row[f"{tf_key} Signal"] = "ERR"
    row["Precio"] = f"{current_price:,.2f}" if current_price else "-"
    return row

def style_macro(df):
    def apply_color(val):
        if "LONG" in str(val): return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
        if "SHORT" in str(val): return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
        if "%" in str(val):
            try:
                v = float(val.replace("%",""))
                return f'color: {"#2E7D32" if v >= 0 else "#C62828"}; font-weight: bold;'
            except: return ''
        return ''
    return df.style.applymap(apply_color)

# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
st.title("🦅 GLOBAL MACRO EVOLUTION MATRIX")

with st.sidebar:
    st.header("⚙️ Radar Control")
    if st.button("🚀 ACTUALIZAR TODO EL MERCADO", type="primary", use_container_width=True):
        results = []
        prog = st.progress(0)
        for idx, sym in enumerate(TICKERS_LIST):
            prog.progress((idx+1)/len(TICKERS_LIST), text=f"Sincronizando: {sym}")
            results.append(analyze_asset(sym))
            time.sleep(0.1)
        st.session_state["sniper_results"] = results
        st.rerun()
    if st.button("Limpiar"):
        st.session_state["sniper_results"] = []
        st.rerun()

# TABLA PRINCIPAL
if st.session_state["sniper_results"]:
    df_f = pd.DataFrame(st.session_state["sniper_results"])
    df_f = df_f.sort_values(["Categoría", "Activo"])
    
    # Seleccionar columnas para la tabla principal (Ocultamos composición para no saturar)
    main_cols = ["Categoría", "Activo", "Precio", "1D Signal", "1D Fecha", "1D PnL", "1S Signal", "1S Fecha", "1S PnL", "1M Signal", "1M Fecha", "1M PnL"]
    st.dataframe(style_macro(df_f[main_cols]), use_container_width=True, height=600)

    # ─────────────────────────────────────────────
    # NUEVA SECCIÓN: DEEP DIVE (ANÁLISIS INDIVIDUAL)
    # ─────────────────────────────────────────────
    st.divider()
    st.header("🔍 Módulo de Análisis Individual (Deep Dive)")
    
    selected_ticker = st.selectbox("Seleccione un activo para ver su composición y señales detalladas:", TICKERS_LIST)
    
    if selected_ticker:
        # Filtrar el dataframe de resultados para el activo seleccionado
        df_single = df_f[df_f["Activo"] == selected_ticker]
        
        if not df_single.empty:
            # Reordenar para resaltar la composición
            detail_cols = ["Activo", "Composición", "Precio", "1D Signal", "1D Fecha", "1D PnL", "1S Signal", "1S Fecha", "1S PnL", "1M Signal", "1M Fecha", "1M PnL"]
            st.dataframe(style_macro(df_single[detail_cols]), use_container_width=True)
        else:
            st.warning(f"Los datos de {selected_ticker} aún no han sido escaneados. Pulse 'Actualizar' arriba.")

else:
    st.info("Pulse 'ACTUALIZAR TODO EL MERCADO' para procesar los activos.")
