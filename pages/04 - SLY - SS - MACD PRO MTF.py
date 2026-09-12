import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
 
# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | RSI PRO MULTI-TF")
 
st.markdown("""
<style>
    .stApp { background-color: #FFFFFF; color: #1C1E21; }
    .stDataFrame { font-size: 11px; font-family: 'Roboto Mono', monospace; }
    h1 { color: #E65100; font-weight: 800; border-bottom: 3px solid #E65100; }
    .stProgress > div > div > div > div { background-color: #E65100; }
</style>
""", unsafe_allow_html=True)
 
if "master_results_crypto" not in st.session_state:
    st.session_state["master_results_crypto"] = {}
 
# ─────────────────────────────────────────────
# MOTOR DEMA (idéntico al Pine "SLY - RSI PRO Multi-TF Confluencia")
# ─────────────────────────────────────────────
def dema(s, length):
    ema1 = s.ewm(span=length, adjust=False).mean()
    ema2 = ema1.ewm(span=length, adjust=False).mean()
    return 2 * ema1 - ema2
 
# ─────────────────────────────────────────────
# RSI PRO POR TEMPORALIDAD — 1h/2h/3h/4h fijas.
# Se pide UNA sola vez la vela de 1h por símbolo, y 2h/3h/4h se derivan
# por resampleo con pandas (1 sola llamada a la API por símbolo, no 4) —
# el mismo resultado que el request.security(..., lookahead_off) del Pine.
# ─────────────────────────────────────────────
def resample_ohlcv(df_1h, rule):
    r = df_1h.resample(rule).agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'vol': 'sum'})
    return r.dropna()
 
VOL_TH = 1.5  # mismo default que "Volume Z-Score Threshold" en el Pine
 
def _rsi_pro_estado_tf(df_tf):
    """
    Reproduce f_rsi_pro_data() + color_for() del Pine, tal cual:
    - color = "VERDE" si RSI > 50, "ROJO" si RSI < 50 (posición, no dirección)
    - dirección = "Aumentando" si el RSI subió respecto a la vela anterior, "Bajando" si no
    - vol_alpha = Z-score de volumen (20 velas) > vol_th (igual que en el Pine)
    Devuelve texto, bull/bear (para la confluencia) y vol_alpha.
    None si no hay historial suficiente en esta temporalidad.
    """
    if len(df_tf) < 25:
        return None
    rsi_raw = ta.rsi(df_tf['close'], length=14)
    rsi_smooth = dema(rsi_raw, 5).dropna()
    if len(rsi_smooth) < 2:
        return None
    rsi_now, rsi_prev = rsi_smooth.iloc[-1], rsi_smooth.iloc[-2]
    growing = rsi_now > rsi_prev
 
    color = "VERDE" if rsi_now > 50 else "ROJO"
    direccion = "Aumentando" if growing else "Bajando"
    texto = f"{color} - {direccion}"
 
    es_bull = (rsi_now > 50) and growing
    es_bear = (rsi_now < 50) and (not growing)
 
    # --- Volumen (idéntico a vol_alpha del Pine) ---
    vol_avg = df_tf['vol'].rolling(20).mean()
    vol_std = df_tf['vol'].rolling(20).std()
    vol_std_last = vol_std.iloc[-1]
    if pd.notna(vol_std_last) and vol_std_last != 0:
        vol_z_last = (df_tf['vol'].iloc[-1] - vol_avg.iloc[-1]) / vol_std_last
        vol_alpha = bool(vol_z_last > VOL_TH)
    else:
        vol_alpha = False
 
    return {"texto": texto, "bull": es_bull, "bear": es_bear, "vol_alpha": vol_alpha}
 
def get_rsi_multitf(ex, symbol):
    """Devuelve un dict con el estado de cada TF (1h/2h/3h/4h), o None si falló el fetch."""
    try:
        raw = ex.fetch_ohlcv(symbol, timeframe='1h', limit=1000)
        df_1h = pd.DataFrame(raw, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
        df_1h['time'] = pd.to_datetime(df_1h['time'], unit='ms')
        df_1h.set_index('time', inplace=True)
 
        df_2h = resample_ohlcv(df_1h, '2h')
        df_3h = resample_ohlcv(df_1h, '3h')
        df_4h = resample_ohlcv(df_1h, '4h')
 
        return {
            "1h": _rsi_pro_estado_tf(df_1h),
            "2h": _rsi_pro_estado_tf(df_2h),
            "3h": _rsi_pro_estado_tf(df_3h),
            "4h": _rsi_pro_estado_tf(df_4h),
        }
    except Exception:
        return None
 
# ─────────────────────────────────────────────
# CONECTIVIDAD KUCOIN (tal como en el script de referencia)
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    return ccxt.kucoin({'enableRateLimit': True})
 
def fetch_symbols():
    try:
        ex = get_exchange()
        markets = ex.load_markets()
        symbols = [s for s in markets if '/USDT' in s and markets[s]['active']]
        filtered = [s for s in symbols if not any(x in s for x in ['3L', '3S', 'USDC', 'DAI', 'PAX', 'TUSD'])]
        # Excluir contratos de futuros/perpetuos (símbolos con ":" en ccxt)
        filtered = [s for s in filtered if ':' not in s]
        return sorted(filtered)
    except:
        return []
 
st.title("🛡️ SLY | RSI PRO MULTI-TF (1h / 2h / 3h / 4h)")
 
with st.sidebar:
    st.header("⚙️ Configuración")
 
    if st.button("📡 Sincronizar Mercado KuCoin"):
        st.session_state["crypto_list"] = fetch_symbols()
        st.rerun()
 
    if "crypto_list" in st.session_state:
        st.subheader("Ejecución")
        lote_size = st.number_input("Tamaño de Lote:", 10, 100, 50)
        total_lotes = (len(st.session_state["crypto_list"]) // lote_size) + 1
        batch_idx = st.selectbox("Seleccionar Lote:", range(total_lotes), format_func=lambda x: f"Lote {x+1}")
 
        if st.button("🚀 ACTUALIZAR Y ACUMULAR", type="primary"):
            ex = get_exchange()
            subset = st.session_state["crypto_list"][batch_idx*lote_size : (batch_idx+1)*lote_size]
            prog = st.progress(0)
 
            for i, sym in enumerate(subset):
                try:
                    prog.progress((i+1)/len(subset), text=f"Auditando: {sym}")
                    result = get_rsi_multitf(ex, sym)
 
                    if result is None:
                        st.session_state["master_results_crypto"][sym] = {
                            "Activo": sym.replace("/USDT", ""),
                            "RSI 1hs": "-", "RSI 2hs": "-", "RSI 3hs": "-", "RSI 4hs": "-",
                            "Vol 1hs": "-", "Vol 2hs": "-", "Vol 3hs": "-", "Vol 4hs": "-",
                            "Confluencia RSI": "-", "Confluencia Vol": "-",
                        }
                        continue
 
                    textos = {}
                    vols = {}
                    bull_count = 0
                    bear_count = 0
                    vol_alpha_count = 0
                    validos = 0
                    for tf in ["1h", "2h", "3h", "4h"]:
                        estado = result[tf]
                        if estado is None:
                            textos[tf] = "-"
                            vols[tf] = "-"
                            continue
                        textos[tf] = estado["texto"]
                        vols[tf] = "SÍ 🔊" if estado["vol_alpha"] else "-"
                        validos += 1
                        if estado["bull"]: bull_count += 1
                        if estado["bear"]: bear_count += 1
                        if estado["vol_alpha"]: vol_alpha_count += 1
 
                    # Confluencia RSI: igual que el Pine (confluence_bull/confluence_bear) —
                    # solo dice algo cuando las 4 (válidas) coinciden TOTALMENTE, si no, "-".
                    if validos == 4 and bull_count == 4:
                        confluencia_rsi = "ALCISTA 🚀"
                    elif validos == 4 and bear_count == 4:
                        confluencia_rsi = "BAJISTA ⚠️"
                    else:
                        confluencia_rsi = "-"
 
                    # Confluencia de Volumen: igual que vol_confluence del Pine (2+ de 4)
                    confluencia_vol = f"SÍ ({vol_alpha_count}/4)" if vol_alpha_count >= 2 else "-"
 
                    st.session_state["master_results_crypto"][sym] = {
                        "Activo": sym.replace("/USDT", ""),
                        "RSI 1hs": textos["1h"],
                        "RSI 2hs": textos["2h"],
                        "RSI 3hs": textos["3h"],
                        "RSI 4hs": textos["4h"],
                        "Vol 1hs": vols["1h"],
                        "Vol 2hs": vols["2h"],
                        "Vol 3hs": vols["3h"],
                        "Vol 4hs": vols["4h"],
                        "Confluencia RSI": confluencia_rsi,
                        "Confluencia Vol": confluencia_vol,
                    }
                    time.sleep(0.05)
                except Exception:
                    st.session_state["master_results_crypto"][sym] = {
                        "Activo": sym.replace("/USDT", ""),
                        "RSI 1hs": "-", "RSI 2hs": "-", "RSI 3hs": "-", "RSI 4hs": "-",
                        "Vol 1hs": "-", "Vol 2hs": "-", "Vol 3hs": "-", "Vol 4hs": "-",
                        "Confluencia RSI": "-", "Confluencia Vol": "-",
                    }
                    continue
            st.rerun()
 
    if st.button("🗑️ Limpiar Memoria"):
        st.session_state["master_results_crypto"] = {}
        st.rerun()
 
# ─────────────────────────────────────────────
# TABLA — solo las columnas pedidas
# ─────────────────────────────────────────────
if st.session_state["master_results_crypto"]:
    df_full = pd.DataFrame(st.session_state["master_results_crypto"].values())
    df_full = df_full[["Activo", "RSI 1hs", "RSI 2hs", "RSI 3hs", "RSI 4hs",
                        "Vol 1hs", "Vol 2hs", "Vol 3hs", "Vol 4hs",
                        "Confluencia RSI", "Confluencia Vol"]]
    df_full = df_full.sort_values("Activo")
 
    def color_cells(val):
        str_v = str(val)
        if "ALCISTA 🚀" in str_v:
            return 'background-color: #2E7D32; color: white; font-weight: bold;'
        if "BAJISTA ⚠️" in str_v:
            return 'background-color: #B71C1C; color: white; font-weight: bold;'
        if "VERDE" in str_v:
            return 'background-color: #A5D6A7; color: #1B5E20; font-weight: bold;'
        if "ROJO" in str_v:
            return 'background-color: #EF9A9A; color: #B71C1C; font-weight: bold;'
        if "SÍ 🔊" in str_v or "SÍ (" in str_v:
            return 'background-color: #FFF9C4; color: #827717; font-weight: bold;'
        return ''
 
    st.dataframe(df_full.style.map(color_cells), use_container_width=True, height=600)
else:
    st.info("👈 Sincronice mercado y analice un lote.")
