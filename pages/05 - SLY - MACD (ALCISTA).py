import streamlit as st
import ccxt
import pandas as pd
import numpy as np
 
# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | ESTRUCTURA ALCISTA MULTI-TF")
 
st.markdown("""
<style>
    .stApp { background-color: #FFFFFF; color: #1C1E21; }
    .stDataFrame { font-size: 11px; font-family: 'Roboto Mono', monospace; }
    h1 { color: #E65100; font-weight: 800; border-bottom: 3px solid #E65100; }
    .stProgress > div > div > div > div { background-color: #E65100; }
</style>
""", unsafe_allow_html=True)
 
if "master_results_estructura" not in st.session_state:
    st.session_state["master_results_estructura"] = {}
 
# Temporalidades FIJAS del análisis (KuCoin las entrega nativas, sin resampleo)
TF_MAP = {"1 Hora": "1h", "4 Horas": "4h", "1 Día": "1d", "1 Semana": "1w", "1 Mes": "1M"}
 
# ─────────────────────────────────────────────
# MOTOR TÉCNICO — traducción del indicador Pine
# "SLY - Estructura Alcista (Mínimos y Máximos Crecientes)"
# ─────────────────────────────────────────────
def dema(s, length):
    ema1 = s.ewm(span=length, adjust=False).mean()
    ema2 = ema1.ewm(span=length, adjust=False).mean()
    return 2 * ema1 - ema2
 
def rsi_wilder(close, length=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / length, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)
    rsi = rsi.where(avg_loss != 0, 100.0)
    return rsi
 
def calcular_oscilador(close, modo):
    """Mismo oscilador que el indicador: MACD PRO (línea MACD con DEMA) o RSI PRO (RSI suavizado con DEMA)."""
    if modo == "MACD PRO":
        return dema(close, 12) - dema(close, 26)
    return dema(rsi_wilder(close, 14).fillna(50), 5)
 
def estructura_alcista(osc, left, right, max_age, ventana):
    """
    Réplica barra por barra del indicador Pine "SLY_HH_HL". Cada señal se ubica donde el
    indicador la DIBUJA en el gráfico:
      - MÍN↑ (triángulo verde) y MÁX↑ (círculo amarillo): en la vela del pivote (t - right)
      - BRK (flecha celeste) y PIERDE LÍNEA (X roja): en la vela donde ocurre el cruce
    Devuelve el patrón vigente en la última vela y hace cuántas velas ocurrió la última marca de cada tipo.
    """
    n = len(osc)
    h1 = h2 = l1 = l2 = None
    h2_i = l1_i = l2_i = None
    prev_support = prev_h2 = prev_osc = None
    marca = {"hl": None, "hh": None, "brk": None, "x": None}  # índice de vela de la última marca
    pattern = False
 
    for t in range(n):
        new_ph = new_pl = False
        p = t - right
        if p - left >= 0:
            w = osc[p - left: t + 1]
            if not np.isnan(w).any():
                v = osc[p]
                # ta.pivothigh / ta.pivotlow: pivote si ninguna vela de la ventana lo supera
                # (los empates cuentan y ambos pivotes pueden darse en la misma vela)
                if v >= w.max():
                    new_ph = True
                    h1, h2, h2_i = h2, v, p
                if v <= w.min():
                    new_pl = True
                    l1, l1_i, l2, l2_i = l2, l2_i, v, p
 
        higher_highs = h1 is not None and h2 > h1
        higher_lows = l1 is not None and l2 > l1
        fresh = h2_i is not None and l2_i is not None and (t - min(h2_i, l2_i) <= max_age)
        pattern = bool(higher_highs and higher_lows and fresh)
 
        support = None
        if pattern and l1_i is not None and l2_i != l1_i:
            support = l2 + (l2 - l1) / (l2_i - l1_i) * (t - l2_i)
 
        o = osc[t]
        if pattern:
            if new_pl:
                marca["hl"] = p
            if new_ph:
                marca["hh"] = p
            if prev_osc is not None and prev_h2 is not None and o > h2 and prev_osc <= prev_h2:
                marca["brk"] = t
            if support is not None and prev_support is not None and prev_osc is not None \
                    and o < support and prev_osc >= prev_support:
                marca["x"] = t
 
        prev_support, prev_h2, prev_osc = support, h2, o
 
    edad = {k: (None if v is None else (n - 1) - v) for k, v in marca.items()}
    return {"pattern": pattern, "edad": edad, "ventana": ventana}
 
def _hace(e):
    return "en la última vela" if e == 0 else f"hace {e} vela" + ("" if e == 1 else "s")
 
def texto_estado(r):
    etiquetas = {"x": "PIERDE LÍNEA 🔴", "brk": "BRK 🚀", "hl": "MÍN↑ 🔺", "hh": "MÁX↑ 🟡"}
    eventos = sorted(
        [(e, k) for k, e in r["edad"].items() if e is not None and e < r["ventana"]]
    )
    partes = [f"{etiquetas[k]} {_hace(e)}" for e, k in eventos]
    if r["pattern"]:
        return " · ".join(["ALCISTA 🟢"] + partes)
    return " · ".join(partes) if partes else "Sin señal"
 
def analizar_tf(ex, sym, tf_code, modo, left, right, max_age, ventana, solo_cerradas):
    """Devuelve (texto_para_la_celda, tiene_estructura). Un fallo en una temporalidad no afecta a las demás."""
    try:
        raw = ex.fetch_ohlcv(sym, timeframe=tf_code, limit=1000)
        df = pd.DataFrame(raw, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
        if solo_cerradas and len(df) > 0:
            df = df.iloc[:-1]  # descarta la vela en formación (evita señales que luego desaparecen)
        if len(df) < 60:
            return "Sin historial", False
        osc = calcular_oscilador(df['close'].astype(float), modo).to_numpy()
        r = estructura_alcista(osc, left, right, max_age, ventana)
        return texto_estado(r), r["pattern"]
    except Exception as e:
        return f"Error: {type(e).__name__}", False
 
# ─────────────────────────────────────────────
# CONECTIVIDAD KUCOIN (mismo universo que el monitor cripto: todos los pares spot /USDT)
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
        filtered = [s for s in filtered if ':' not in s]  # sin perpetuos/futuros
        return sorted(filtered)
    except Exception:
        return []
 
st.title("🛡️ SLY | ESTRUCTURA ALCISTA MULTI-TF (1 Hora · 4 Horas · 1 Día · 1 Semana · 1 Mes)")
 
with st.sidebar:
    st.header("⚙️ Configuración")
 
    st.subheader("1. Estructura")
    modo = st.selectbox("Oscilador a analizar:", ["MACD PRO", "RSI PRO"], index=0)
    left = st.number_input("Pivote: velas a la izquierda", 1, 30, 6)
    right = st.number_input("Pivote: velas a la derecha (confirmación)", 1, 30, 6)
    max_age = st.number_input("Vigencia del patrón (velas)", 10, 500, 120)
    ventana = st.number_input("Mostrar señales de las últimas N velas", 1, 100, 10)
    solo_cerradas = st.checkbox("Usar solo velas cerradas", value=True)
 
    st.subheader("2. Mercado")
    if st.button("📡 Sincronizar Mercado KuCoin"):
        st.session_state["crypto_list"] = fetch_symbols()
        st.rerun()
 
    if "crypto_list" in st.session_state:
        st.subheader("3. Ejecución")
        lote_size = st.number_input("Tamaño de Lote:", 10, 100, 30)
        total_lotes = (len(st.session_state["crypto_list"]) // lote_size) + 1
        batch_idx = st.selectbox("Seleccionar Lote:", range(total_lotes), format_func=lambda x: f"Lote {x+1}")
 
        if st.button("🚀 ACTUALIZAR Y ACUMULAR", type="primary"):
            ex = get_exchange()
            subset = st.session_state["crypto_list"][batch_idx * lote_size: (batch_idx + 1) * lote_size]
            prog = st.progress(0)
 
            for i, sym in enumerate(subset):
                prog.progress((i + 1) / len(subset), text=f"Auditando: {sym}")
                fila = {"Activo": sym.replace("/USDT", "")}
                n_alineadas = 0
                for label, code in TF_MAP.items():
                    texto, tiene = analizar_tf(ex, sym, code, modo, int(left), int(right),
                                               int(max_age), int(ventana), solo_cerradas)
                    fila[label] = texto
                    n_alineadas += 1 if tiene else 0
                fila["_n"] = n_alineadas
                st.session_state["master_results_estructura"][sym] = fila
            st.rerun()
 
    if st.button("🗑️ Limpiar Memoria"):
        st.session_state["master_results_estructura"] = {}
        st.rerun()
 
# ─────────────────────────────────────────────
# TABLA
# ─────────────────────────────────────────────
if st.session_state["master_results_estructura"]:
    df_full = pd.DataFrame(st.session_state["master_results_estructura"].values())
    df_full = df_full.sort_values(by=["_n", "Activo"], ascending=[False, True]).drop(columns=["_n"])
    df_full = df_full[["Activo"] + list(TF_MAP.keys())]
 
    def color_cells(val):
        s = str(val)
        if "PIERDE" in s:
            return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
        if "BRK" in s:
            return 'background-color: #2E7D32; color: white; font-weight: bold;'
        if "ALCISTA" in s or "MÍN↑" in s:
            return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
        if "Error" in s or "Sin historial" in s:
            return 'background-color: #FFF3E0; color: #E65100;'
        return 'color: #9E9E9E;'
 
    st.dataframe(df_full.style.map(color_cells, subset=list(TF_MAP.keys())),
                 use_container_width=True, height=600)
else:
    st.info("👈 Sincronice mercado y analice un lote.")
 
