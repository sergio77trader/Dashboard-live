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
st.set_page_config(layout="wide", page_title="STOCKS SNIPER | SYSTEMATRADER")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 14px; }
    .stDataFrame { font-size: 12px; border: 1px solid #333; }
    h1 { color: #2962FF; font-weight: 800; }
    .stExpander { border: 2px solid #2962FF !important; border-radius: 8px !important; }
</style>
""", unsafe_allow_html=True)

if "sniper_results" not in st.session_state:
    st.session_state["sniper_results"] = []

# Mapeo SEGURO de Timeframes para Yahoo Finance
TIMEFRAMES = {
    "1m": {"int": "1m", "per": "5d"},
    "5m": {"int": "5m", "per": "30d"},
    "15m": {"int": "15m", "per": "30d"},
    "30m": {"int": "30m", "per": "30d"},
    "1H": {"int": "60m", "per": "730d"},
    "4H": {"int": "60m", "per": "730d"}, # Yahoo no tiene 4h nativo, se usa 1h estable
    "1D": {"int": "1d", "per": "max"}
}

MASTER_TICKERS = sorted([
    'GGAL', 'YPF', 'BMA', 'PAMP', 'TGS', 'CEPU', 'EDN', 'BFR', 'SUPV', 'CRESY', 'IRS', 'TEO', 'LOMA', 'DESP', 'VIST', 'GLOB', 'MELI', 'BIOX', 'TX',
    'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NFLX',
    'CRM', 'ORCL', 'ADBE', 'IBM', 'CSCO', 'PLTR', 'SNOW', 'SHOP', 'SPOT', 'UBER', 'ABNB', 'SAP', 'INTU', 'NOW',
    'AMD', 'INTC', 'QCOM', 'AVGO', 'TXN', 'MU', 'ADI', 'AMAT', 'ARM', 'SMCI', 'TSM', 'ASML', 'LRCX', 'HPQ', 'DELL',
    'JPM', 'BAC', 'C', 'WFC', 'GS', 'MS', 'V', 'MA', 'AXP', 'BRK-B', 'PYPL', 'SQ', 'COIN', 'BLK', 'USB', 'NU',
    'KO', 'PEP', 'MCD', 'SBUX', 'DIS', 'NKE', 'WMT', 'COST', 'TGT', 'HD', 'LOW', 'PG', 'CL', 'MO', 'PM', 'KMB', 'EL',
    'JNJ', 'PFE', 'MRK', 'LLY', 'ABBV', 'UNH', 'BMY', 'AMGN', 'GILD', 'AZN', 'NVO', 'NVS', 'CVS',
    'BA', 'CAT', 'DE', 'GE', 'MMM', 'LMT', 'RTX', 'HON', 'UNP', 'UPS', 'FDX', 'LUV', 'DAL',
    'F', 'GM', 'TM', 'HMC', 'STLA', 'RACE',
    'XOM', 'CVX', 'SLB', 'OXY', 'HAL', 'BP', 'SHEL', 'TTE', 'PBR', 'VLO',
    'VZ', 'T', 'TMUS', 'VOD',
    'BABA', 'JD', 'BIDU', 'NIO', 'PDD', 'TCEHY', 'TCOM', 'BEKE', 'XPEV', 'LI', 'SONY',
    'VALE', 'ITUB', 'BBD', 'ERJ', 'ABEV', 'GGB', 'SID', 'NBR',
    'GOLD', 'NEM', 'PAAS', 'FCX', 'SCCO', 'RIO', 'BHP', 'ALB', 'SQM',
    'SPY', 'QQQ', 'IWM', 'DIA', 'EEM', 'EWZ', 'FXI', 'XLE', 'XLF', 'XLK', 'XLV', 'XLI', 'XLP', 'XLU', 'XLY', 'ARKK', 'SMH', 'TAN', 'GLD', 'SLV', 'GDX'
])

# ─────────────────────────────────────────────
# MANUAL OPERATIVO
# ─────────────────────────────────────────────
with st.expander("📘 MANUAL DE LÓGICA Y COLUMNAS"):
    st.info("Referencia técnica de las métricas institucionales del SNIPER para Stocks.")
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.markdown("""
        ### 🎯 LÓGICA DE MANDO (VEREDICTO)
        *   **🔥 COMPRA/VENTA FUERTE:** Confluencia masiva de 5+ temporalidades alineadas con el sesgo **1D MACD 0**.
        *   **💎 GIRO/REBOTE:** Cuando **1m, 5m y 15m H.A./MACD** están en **LONG**, pero el sesgo **1D MACD 0** es **BAJO 0**.
        *   **⚖️ RANGO:** Sin dirección clara. **NO OPERAR.**
        """)
    with col_m2:
        st.markdown("""
        ### 📊 INDICADORES
        *   **TF H.A./MACD:** Gatillo Heikin Ashi + MACD Hist + RSI.
        *   **TF Hist.:** Dirección de fuerza (**SUBIENDO / BAJANDO**).
        *   **Volumen USD:** Se calcula sobre la última vela operativa.
        """)

# ─────────────────────────────────────────────
# CÁLCULOS TÉCNICOS
# ─────────────────────────────────────────────
def calculate_heikin_ashi(df):
    df = df.copy()
    df["HA_Close"] = (df["Open"] + df["High"] + df["Low"] + df["Close"]) / 4
    ha_open = [df["Open"].iloc[0]]
    for i in range(1, len(df)):
        ha_open.append((ha_open[-1] + df["HA_Close"].iloc[i-1]) / 2)
    df["HA_Open"], df["HA_Color"] = ha_open, np.where(df["HA_Close"] > ha_open, 1, -1)
    return df

def analyze_stock_tf(symbol, label, config):
    try:
        # Descarga de datos única por TF
        df = yf.download(symbol, interval=config['int'], period=config['per'], progress=False, auto_adjust=True)
        
        # Limpieza de MultiIndex si existe
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        if df.empty or len(df) < 35: return None

        macd = ta.macd(df["Close"])
        df["Hist"], df["MACD"], df["Signal"] = macd["MACDh_12_26_9"], macd["MACD_12_26_9"], macd["MACDs_12_26_9"]
        df["RSI"] = ta.rsi(df["Close"], length=14)
        df = calculate_heikin_ashi(df)

        position, last_date = "NEUTRO", df.index[-1]
        for i in range(1, len(df)):
            h, ph, hc, d = df["Hist"].iloc[i], df["Hist"].iloc[i-1], df["HA_Color"].iloc[i], df.index[i]
            if position == "LONG" and h < ph: position = "NEUTRO"
            elif position == "SHORT" and h > ph: position = "NEUTRO"
            if position == "NEUTRO":
                if hc == 1 and h > ph: position, last_date = "LONG", d
                elif hc == -1 and h < ph: position, last_date = "SHORT", d

        rsi_val = round(df["RSI"].iloc[-1], 1)
        rsi_state = "RSI↑" if rsi_val > 55 else "RSI↓" if rsi_val < 45 else "RSI="
        df["cross"] = np.sign(df["MACD"] - df["Signal"]).diff().ne(0)
        cross_time = df[df["cross"]].index[-1].strftime("%H:%M") if not df[df["cross"]].empty else "--:--"

        return {
            "signal": f"{'🟢' if position=='LONG' else '🔴' if position=='SHORT' else '⚪'} {position} | {rsi_state}",
            "signal_time": last_date.strftime("%H:%M"),
            "m0": "SOBRE 0" if df["MACD"].iloc[-1] > 0 else "BAJO 0",
            "h_dir": "SUBIENDO" if df["Hist"].iloc[-1] > df["Hist"].iloc[-2] else "BAJANDO",
            "cross_time": cross_time,
            "last_price": df["Close"].iloc[-1],
            "vol_usd": df["Close"].iloc[-1] * df["Volume"].iloc[-1]
        }
    except: return None

def get_verdict(row):
    bulls = sum(1 for tf in TIMEFRAMES if "LONG" in str(row.get(f"{tf} H.A./MACD","")))
    bears = sum(1 for tf in TIMEFRAMES if "SHORT" in str(row.get(f"{tf} H.A./MACD","")))
    bias_1d = str(row.get("1D MACD 0", ""))
    micro_bull = all("LONG" in str(row.get(f"{tf} H.A./MACD","")) for tf in ["1m", "5m", "15m"])
    micro_bear = all("SHORT" in str(row.get(f"{tf} H.A./MACD","")) for tf in ["1m", "5m", "15m"])

    if bulls >= 5 and "SOBRE 0" in bias_1d: return "🔥 COMPRA FUERTE", "MTF BULLISH SYNC"
    if bears >= 5 and "BAJO 0" in bias_1d: return "🩸 VENTA FUERTE", "MTF BEARISH SYNC"
    if micro_bull and "BAJO 0" in bias_1d: return "💎 GIRO/REBOTE", "FAST RECOVERY"
    if micro_bear and "SOBRE 0" in bias_1d: return "📉 RETROCESO", "CORRECTION START"
    return "⚖️ RANGO", "NO TREND"

def get_macd_rec(row):
    sub = sum(1 for tf in ["15m", "1H", "4H"] if "SUBIENDO" in str(row.get(f"{tf} Hist.", "")))
    return "📈 MOMENTUM ALCISTA" if sub >= 2 else "📉 MOMENTUM BAJISTA"

# ─────────────────────────────────────────────
# MOTOR DE ESCANEO
# ─────────────────────────────────────────────
def scan_stocks(targets, acc):
    results = []
    prog = st.progress(0)
    for idx, sym in enumerate(targets):
        prog.progress((idx+1)/len(targets), text=f"Analizando {sym}")
        try:
            row = {"Activo": sym}
            valid_any = False
            for label, config in TIMEFRAMES.items():
                res = analyze_stock_tf(sym, label, config)
                if res:
                    valid_any = True
                    row[f"{label} H.A./MACD"], row[f"{label} Hora Señal"] = res["signal"], res["signal_time"]
                    row[f"{label} MACD 0"], row[f"{label} Hist."], row[f"{label} Cruce MACD"] = res["m0"], res["h_dir"], res["cross_time"]
                    row["Precio"] = f"{res['last_price']:.2f}"
                else:
                    for c in ["H.A./MACD","Hora Señal","MACD 0","Hist.","Cruce MACD"]: row[f"{label} {c}"] = "-"
            
            if valid_any:
                row["VEREDICTO"], row["ESTRATEGIA"] = get_verdict(row)
                row["MACD REC."] = get_macd_rec(row)
                results.append(row)
            time.sleep(0.2)
        except: continue
    prog.empty()
    if acc:
        curr = {x["Activo"]: x for x in st.session_state["sniper_results"]}
        for r in results: curr[r["Activo"]] = r
        return list(curr.values())
    return results

def style_matrix(df):
    def apply_color(val):
        v = str(val).upper()
        if any(x in v for x in ["LONG", "SOBRE 0", "SUBIENDO", "COMPRA", "ALCISTA"]): return 'background-color: #d4edda; color: #155724;'
        if any(x in v for x in ["SHORT", "BAJO 0", "BAJANDO", "VENTA", "BAJISTA"]): return 'background-color: #f8d7da; color: #721c24;'
        if "GIRO" in v: return 'background-color: #fff3cd; color: #856404;'
        return ''
    return df.style.applymap(apply_color)

# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("🎯 Stock Sniper")
    # Tickers que cumplen con el volumen (Simulado o real tras primer scan)
    b_size = st.selectbox("Lote de escaneo:", [10, 20, 50], index=0)
    batches = [MASTER_TICKERS[i:i+b_size] for i in range(0, len(MASTER_TICKERS), b_size)]
    sel = st.selectbox("Seleccionar Lote:", range(len(batches)))
    acc = st.checkbox("Acumular Resultados", value=True)
    
    if st.button("🚀 INICIAR ESCANEO", type="primary"):
        st.session_state["sniper_results"] = scan_stocks(batches[sel], acc)
    
    st.divider()
    if st.session_state["sniper_results"]:
        df_temp = pd.DataFrame(st.session_state["sniper_results"])
        f_ver = st.multiselect("Veredicto:", options=df_temp["VEREDICTO"].unique(), default=df_temp["VEREDICTO"].unique())
        f_est = st.multiselect("Estrategia:", options=df_temp["ESTRATEGIA"].unique(), default=df_temp["ESTRATEGIA"].unique())
        
        with st.sidebar.expander("📉 Momentum Hist."):
            f_hist_val = st.multiselect("Filtro Global Hist.:", options=["SUBIENDO", "BAJANDO", "-"], default=["SUBIENDO", "BAJANDO", "-"])

    if st.button("Limpiar Memoria"):
        st.session_state["sniper_results"] = []; st.rerun()

# ─────────────────────────────────────────────
# TABLA FINAL
# ─────────────────────────────────────────────
if st.session_state["sniper_results"]:
    df_f = pd.DataFrame(st.session_state["sniper_results"])
    df_f = df_f[df_f["VEREDICTO"].isin(f_ver) & df_f["ESTRATEGIA"].isin(f_est)]
    
    # Filtro de Histogramas
    hist_cols = [c for c in df_f.columns if "Hist." in c]
    for col in hist_cols:
        df_f = df_f[df_f[col].isin(f_hist_val)]
    
    prio = ["Activo", "VEREDICTO", "ESTRATEGIA", "MACD REC.", "Precio"]
    df_f = df_f[prio + [c for c in df_f.columns if c not in prio]]
    st.dataframe(style_matrix(df_f), use_container_width=True, height=800)
else:
    st.info("👈 Seleccione un lote y presione INICIAR ESCANEO.")
