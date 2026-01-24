import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE PÁGINA E INTERFAZ
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SYSTEMATRADER | SNIPER MATRIX V14.0")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 14px; }
    .stDataFrame { font-size: 12px; border: 1px solid #222; }
    h1 { color: #2962FF; font-weight: 800; }
    .stProgress > div > div > div > div { background-color: #2962FF; }
</style>
""", unsafe_allow_html=True)

# Memoria de sesión
if "sniper_results" not in st.session_state:
    st.session_state["sniper_results"] = []

TIMEFRAMES = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1H": "1h", "4H": "4h", "1D": "1d"
}

# ─────────────────────────────────────────────
# MOTOR DE CONEXIÓN (INSTITUCIONAL)
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    return ccxt.kucoinfutures({
        "enableRateLimit": True,
        "timeout": 30000
    })

@st.cache_data(ttl=300)
def get_active_pairs():
    try:
        ex = get_exchange()
        tickers = ex.fetch_tickers()
        valid = []
        for s, t in tickers.items():
            if "/USDT:USDT" in s and t.get("quoteVolume", 0) > 500000:
                valid.append({"symbol": s, "vol": t["quoteVolume"]})
        return pd.DataFrame(valid).sort_values("vol", ascending=False)["symbol"].tolist()
    except:
        return []

# ─────────────────────────────────────────────
# LÓGICA TÉCNICA (HEIKIN ASHI & MACD)
# ─────────────────────────────────────────────
def calculate_heikin_ashi(df):
    df = df.copy()
    df["HA_Close"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
    ha_open = [df["open"].iloc[0]]
    for i in range(1, len(df)):
        ha_open.append((ha_open[-1] + df["HA_Close"].iloc[i-1]) / 2)
    df["HA_Open"] = ha_open
    df["HA_Color"] = np.where(df["HA_Close"] > df["HA_Open"], 1, -1)
    return df

def analyze_ticker_tf(symbol, tf_code, exchange, current_price):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf_code, limit=100)
        if not ohlcv or len(ohlcv) < 50: return None
        
        ohlcv[-1][4] = current_price # Inyectar precio actual
        df = pd.DataFrame(ohlcv, columns=["time", "open", "high", "low", "close", "vol"])
        df["dt"] = pd.to_datetime(df["time"], unit="ms")

        # Indicadores Base
        macd = ta.macd(df["close"])
        df["MACD"] = macd["MACD_12_26_9"]
        df["Signal"] = macd["MACDs_12_26_9"]
        df["Hist"] = macd["MACDh_12_26_9"]
        df["RSI"] = ta.rsi(df["close"], length=14)
        df = calculate_heikin_ashi(df)

        last = df.iloc[-1]
        prev = df.iloc[-2]

        # 1. Señal Sniper (Icono + HA + RSI)
        state = "NEUTRO"
        if last["HA_Color"] == 1 and last["Hist"] > prev["Hist"]: state = "LONG"
        elif last["HA_Color"] == -1 and last["Hist"] < prev["Hist"]: state = "SHORT"
        
        rsi_val = round(last["RSI"], 1)
        rsi_state = "RSI↑" if rsi_val > 55 else "RSI↓" if rsi_val < 45 else "RSI="
        icon = "🟢" if state == "LONG" else "🔴" if state == "SHORT" else "⚪"

        # 2. MACD Meta-Data (Lo que pediste añadir)
        macd_zero = "SOBRE 0" if last["MACD"] > 0 else "BAJO 0"
        hist_dir = "Alcista" if last["Hist"] > prev["Hist"] else "Bajista"
        
        # 3. Cálculo del Cruce (Hora exacta)
        df["cross"] = np.sign(df["MACD"] - df["Signal"]).diff().ne(0)
        crosses = df[df["cross"] == True]
        last_cross_time = (crosses["dt"].iloc[-1] - pd.Timedelta(hours=3)).strftime("%H:%M") if not crosses.empty else "--:--"

        return {
            "main_signal": f"{icon} {state} | {rsi_state} ({rsi_val})",
            "macd_zero": macd_zero,
            "hist_dir": hist_dir,
            "cross_time": last_cross_time
        }
    except: return None

# ─────────────────────────────────────────────
# VEREDICTO ESTRATÉGICO
# ─────────────────────────────────────────────
def get_summary_logic(row):
    # Analizamos la convergencia de señales LONG/SHORT en todos los TFs
    l_count = sum(1 for tf in TIMEFRAMES if "LONG" in str(row.get(f"{tf} Sniper", "")))
    s_count = sum(1 for tf in TIMEFRAMES if "SHORT" in str(row.get(f"{tf} Sniper", "")))
    
    # Sesgo de Temporalidad Mayor (1D)
    bias_1d = str(row.get("1D MACD 0", ""))
    
    if l_count >= 5 and "SOBRE 0" in bias_1d:
        return "🔥 COMPRA FUERTE", "TENDENCIA BULLISH CONFIRMADA"
    if s_count >= 5 and "BAJO 0" in bias_1d:
        return "🩸 VENTA FUERTE", "TENDENCIA BEARISH CONFIRMADA"
    if "LONG" in str(row.get("1m Sniper", "")) and "BAJO 0" in bias_1d:
        return "⚠️ REBOTE", "SCALP RÁPIDO"
    if "SHORT" in str(row.get("1m Sniper", "")) and "SOBRE 0" in bias_1d:
        return "📉 RETROCESO", "BUSCAR ENTRADA"
    
    return "⚖️ RANGO", "SIN CONFLUENCIA CLARA"

# ─────────────────────────────────────────────
# PROCESAMIENTO POR LOTES
# ─────────────────────────────────────────────
def scan_batch(targets):
    ex = get_exchange()
    results = []
    prog = st.progress(0, text="Iniciando Escaneo...")

    for idx, sym in enumerate(targets):
        clean_name = sym.split(":")[0].replace("/USDT", "")
        prog.progress((idx + 1) / len(targets), text=f"Escaneando {clean_name}...")

        try:
            ticker = ex.fetch_ticker(sym)
            price = ticker["last"]
            row = {"Activo": clean_name, "Precio": f"{price:,.4f}"}

            for label, tf_code in TIMEFRAMES.items():
                data = analyze_ticker_tf(sym, tf_code, ex, price)
                if data:
                    row[f"{label} Sniper"] = data["main_signal"]
                    row[f"{label} MACD 0"] = data["macd_zero"]
                    row[f"{label} Hist."] = data["hist_dir"]
                    row[f"{label} Cruce"] = data["cross_time"]
                else:
                    for c in ["Sniper", "MACD 0", "Hist.", "Cruce"]: row[f"{label} {c}"] = "-"

            # Generar Veredicto y Estrategia
            veredicto, estrategia = get_summary_logic(row)
            row["VEREDICTO"] = veredicto
            row["ESTRATEGIA"] = estrategia
            
            results.append(row)
            time.sleep(0.05) # Evitar baneo de IP
        except: continue
    
    prog.empty()
    return results

# ─────────────────────────────────────────────
# INTERFAZ DE USUARIO
# ─────────────────────────────────────────────
st.title("🎯 SNIPER MATRIX V14.0")
st.caption("Grado Institucional | MTF Heikin Ashi + MACD Cross + RSI | KuCoin Futures")

with st.sidebar:
    st.header("Configuración de Radar")
    with st.spinner("Conectando con el Exchange..."):
        all_symbols = get_active_pairs()
    
    if all_symbols:
        batch_size = st.selectbox("Activos por Lote", [10, 15, 20, 30, 50], index=1)
        batches = [all_symbols[i:i+batch_size] for i in range(0, len(all_symbols), batch_size)]
        sel = st.selectbox("Seleccionar Lote", range(len(batches)), format_func=lambda x: f"Lote {x+1} ({len(batches[x])} activos)")
        
        if st.button("🚀 INICIAR ESCANEO", type="primary", use_container_width=True):
            st.session_state["sniper_results"] = scan_batch(batches[sel])

    if st.button("Limpiar Memoria"):
        st.session_state["sniper_results"] = []
        st.rerun()

# Lógica de Color para la Tabla
def style_dataframe(df):
    def apply_color(val):
        v = str(val).upper()
        if any(x in v for x in ["LONG", "SOBRE 0", "ALCISTA", "COMPRA", "RSI↑"]):
            return 'background-color: #d4edda; color: #155724;' # Verde Claro
        if any(x in v for x in ["SHORT", "BAJO 0", "BAJISTA", "VENTA", "RSI↓"]):
            return 'background-color: #f8d7da; color: #721c24;' # Rojo Claro
        if "REBOTE" in v:
            return 'background-color: #fff3cd; color: #856404;' # Amarillo Claro
        return ''
    return df.style.applymap(apply_color)

# Renderizado de Tabla con Seguridad Anti-KeyError
if st.session_state["sniper_results"]:
    df_final = pd.DataFrame(st.session_state["sniper_results"])
    
    # Columnas Críticas al inicio (Seguras)
    cols_priority = ["Activo", "VEREDICTO", "ESTRATEGIA", "Precio"]
    
    # Validar que las columnas existan antes de reordenar
    existing_priority = [c for c in cols_priority if c in df_final.columns]
    other_cols = [c for c in df_final.columns if c not in existing_priority]
    
    df_final = df_final[existing_priority + other_cols]
    
    st.subheader("Matrix de Convergencia Multi-Temporal")
    st.dataframe(style_dataframe(df_final), use_container_width=True, height=800)
else:
    st.info("👈 Selecciona un lote y presiona el botón de escaneo para iniciar.")
