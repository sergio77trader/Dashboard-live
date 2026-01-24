import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURACIÓN Y ESTILO
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SNIPER MATRIX V13.0 - SystemaTrader")

# CSS personalizado para forzar visibilidad y limpieza
st.markdown("""
<style>
    .reportview-container .main .block-container { max-width: 95%; }
    .stDataFrame { border: 1px solid #333; }
    h1 { color: #2962FF; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

if "sniper_results" not in st.session_state:
    st.session_state["sniper_results"] = []

TIMEFRAMES = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1H": "1h", "4H": "4h", "1D": "1d"
}

# ─────────────────────────────────────────────
# MOTOR DE DATOS (CONEXIÓN)
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    return ccxt.kucoinfutures({"enableRateLimit": True, "timeout": 30000})

@st.cache_data(ttl=300)
def get_active_pairs():
    try:
        ex = get_exchange()
        tickers = ex.fetch_tickers()
        return [s for s in tickers if "/USDT:USDT" in s and tickers[s].get("quoteVolume", 0) > 1000000]
    except: return []

# ─────────────────────────────────────────────
# LÓGICA DE INDICADORES
# ─────────────────────────────────────────────
def calculate_heikin_ashi(df):
    df = df.copy()
    df["HA_Close"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
    ha_open = [df["open"].iloc[0]]
    for i in range(1, len(df)):
        ha_open.append((ha_open[-1] + df["HA_Close"].iloc[i-1]) / 2)
    df["HA_Open"] = ha_open
    df["HA_Color"] = np.where(df["HA_Close"] > df["HA_Open"], "Verde", "Rojo")
    return df

def analyze_ticker_tf(symbol, tf_code, exchange, current_price):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=100)
        if not ohlcv or len(ohlcv) < 50: return None
        
        ohlcv[-1][4] = current_price
        df = pd.DataFrame(ohlcv, columns=["time", "open", "high", "low", "close", "vol"])
        df["dt"] = pd.to_datetime(df["time"], unit="ms")

        # MACD (12, 26, 9)
        macd_df = ta.macd(df["close"])
        df["MACD"] = macd_df["MACD_12_26_9"]
        df["Signal"] = macd_df["MACDs_12_26_9"]
        df["Hist"] = macd_df["MACDh_12_26_9"]
        
        df = calculate_heikin_ashi(df)
        
        # Últimos valores
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        
        # 1. Estado MACD vs 0
        macd_zero = "SOBRE 0" if last_row["MACD"] > 0 else "BAJO 0"
        
        # 2. Histograma Dirección
        hist_dir = "Alcista" if last_row["Hist"] > prev_row["Hist"] else "Bajista"
        
        # 3. Cruce MACD (Hora)
        # Buscamos el último cruce entre MACD y Signal
        df["cross"] = np.sign(df["MACD"] - df["Signal"]).diff().ne(0)
        cross_idx = df[df["cross"] == True].index
        last_cross_time = df.loc[cross_idx[-1], "dt"].strftime("%H:%M") if len(cross_idx) > 0 else "--:--"
        
        # 4. Señal Sniper (HA + MACD Hist)
        state = "NEUTRO"
        if last_row["HA_Color"] == "Verde" and last_row["Hist"] > prev_row["Hist"]:
            state = "LONG"
        elif last_row["HA_Color"] == "Rojo" and last_row["Hist"] < prev_row["Hist"]:
            state = "SHORT"

        return {
            "state": state,
            "macd_zero": macd_zero,
            "hist_dir": hist_dir,
            "cross_time": last_cross_time,
            "ha_color": last_row["HA_Color"]
        }
    except: return None

# ─────────────────────────────────────────────
# LÓGICA DE VEREDICTO (INTELIGENCIA CENTRAL)
# ─────────────────────────────────────────────
def get_verdict(row):
    # Pesos: 1D y 4H mandan en el sesgo
    htf_bias = "BULL" if "SOBRE 0" in str(row.get("1D | MACD 0", "")) else "BEAR"
    
    longs = sum(1 for tf in TIMEFRAMES if "LONG" in str(row.get(f"{tf} | Sniper", "")))
    shorts = sum(1 for tf in TIMEFRAMES if "SHORT" in str(row.get(f"{tf} | Sniper", "")))
    
    if longs >= 5 and htf_bias == "BULL": return "🔥 COMPRA INSTITUCIONAL"
    if shorts >= 5 and htf_bias == "BEAR": return "🩸 DISTRIBUCIÓN MASIVA"
    if htf_bias == "BEAR" and "LONG" in str(row.get("1m | Sniper", "")): return "⚠️ REBOTE TÉCNICO"
    if htf_bias == "BULL" and "SHORT" in str(row.get("1m | Sniper", "")): return "📉 DIP DE CARGA"
    
    return "⚖️ CONSOLIDACIÓN"

# ─────────────────────────────────────────────
# MOTOR DE ESCANEO
# ─────────────────────────────────────────────
def scan_batch(targets):
    ex = get_exchange()
    results = []
    prog = st.progress(0, text="Sincronizando Matrix...")

    for idx, sym in enumerate(targets):
        clean = sym.replace(":USDT", "").replace("/USDT", "")
        prog.progress((idx + 1) / len(targets), text=f"Analizando {clean}...")

        try:
            price = ex.fetch_ticker(sym)["last"]
            row = {"Activo": clean, "Precio": f"{price:,.4f}"}
            
            for label, tf_code in TIMEFRAMES.items():
                res = analyze_ticker_tf(sym, tf_code, ex, price)
                if res:
                    row[f"{label} | Sniper"] = res["state"]
                    row[f"{label} | MACD 0"] = res["macd_zero"]
                    row[f"{label} | Hist"] = res["hist_dir"]
                    row[f"{label} | Cruce"] = res["cross_time"]
                else:
                    for c in ["Sniper", "MACD 0", "Hist", "Cruce"]: row[f"{label} | {c}"] = "-"
            
            row["Veredicto"] = get_verdict(row)
            results.append(row)
            time.sleep(0.05) # Rate limit preventer
        except: continue

    prog.empty()
    return results

# ─────────────────────────────────────────────
# INTERFAZ Y ESTILADO DE TABLA
# ─────────────────────────────────────────────
st.title("🎯 SNIPER MATRIX V13.0")
st.caption("Grado Institucional | Heikin Ashi | MACD Fractal | KuCoin Futures")

with st.sidebar:
    st.header("Terminal de Control")
    all_symbols = get_active_pairs()
    if all_symbols:
        batch_size = st.number_input("Activos por Lote", 5, 50, 15)
        batches = [all_symbols[i:i+batch_size] for i in range(0, len(all_symbols), batch_size)]
        sel = st.selectbox("Seleccionar Sector/Lote", range(len(batches)))
        
        if st.button("🚀 INICIAR ESCANEO", type="primary", use_container_width=True):
            st.session_state["sniper_results"] = scan_batch(batches[sel])
    
    if st.button("Limpiar Memoria"):
        st.session_state["sniper_results"] = []
        st.rerun()

# LÓGICA DE COLOR (PANDAS STYLER)
def style_matrix(df):
    def color_logic(val):
        # Colores claros para legibilidad
        if any(x in str(val) for x in ["LONG", "SOBRE 0", "Alcista", "COMPRA"]):
            return 'background-color: #d4edda; color: #155724;' # Verde claro
        if any(x in str(val) for x in ["SHORT", "BAJO 0", "Bajista", "VENTA", "DISTRIBUCIÓN"]):
            return 'background-color: #f8d7da; color: #721c24;' # Rojo claro
        if "REBOTE" in str(val):
            return 'background-color: #fff3cd; color: #856404;' # Amarillo/Ocre
        return ''

    return df.style.applymap(color_logic)

if st.session_state["sniper_results"]:
    df_final = pd.DataFrame(st.session_state["sniper_results"])
    
    # Reordenar: Activo y Veredicto al inicio
    cols = ["Activo", "Veredicto", "Precio"] + [c for c in df_final.columns if c not in ["Activo", "Veredicto", "Precio"]]
    df_final = df_final[cols]
    
    st.subheader("Análisis de Convergencia Multi-Temporal")
    st.dataframe(style_matrix(df_final), use_container_width=True, height=700)
else:
    st.info("Sistema a la espera de inicialización. Seleccione un lote en la barra lateral.")
