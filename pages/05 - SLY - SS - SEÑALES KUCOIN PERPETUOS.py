import time
import numpy as np
import pandas as pd
import streamlit as st
import ccxt
 
# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | SEÑALES KUCOIN PERPETUOS")
 
st.markdown("""
<style>
    .stApp { background-color: #FFFFFF; color: #1C1E21; }
    .stDataFrame { font-size: 12px; font-family: 'Roboto Mono', monospace; }
    h1 { color: #E65100; font-weight: 800; border-bottom: 3px solid #E65100; }
    .stProgress > div > div > div > div { background-color: #E65100; }
</style>
""", unsafe_allow_html=True)
 
if "kc_perp_results" not in st.session_state:
    st.session_state["kc_perp_results"] = {}
if "kc_perp_meta" not in st.session_state:
    st.session_state["kc_perp_meta"] = {}
 
# Parámetros del indicador SLY_HH_HL (los de por defecto, no se configuran)
LEFT, RIGHT, MAX_AGE = 6, 6, 120
# Perfil de volumen (mismos valores que el script de Pine)
ROWS, VA_PCT, MAX_PROF = 40, 0.70, 300
 
TF_MS = {"15m": 900_000, "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000, "1w": 604_800_000}
TF_LABEL = {"15 Minutos": "15m", "1 Hora": "1h", "4 Horas": "4h", "1 Día": "1d", "1 Semana": "1w"}
STABLES = {"USDC", "USDT", "DAI", "TUSD", "FDUSD", "USDE", "PYUSD", "USDD", "BUSD"}
 
 
# ─────────────────────────────────────────────
# MOTOR TÉCNICO
# ─────────────────────────────────────────────
def dema(s, length):
    ema1 = s.ewm(span=length, adjust=False).mean()
    ema2 = ema1.ewm(span=length, adjust=False).mean()
    return 2 * ema1 - ema2
 
 
def rma(s, n):
    return s.ewm(alpha=1 / n, adjust=False).mean()
 
 
def adx_calc(df, n=14, sm=14):
    """ADX de Wilder (igual que ta.dmi de Pine). Devuelve (+DI, -DI, ADX) como series."""
    h, l, c = df["high"].astype(float), df["low"].astype(float), df["close"].astype(float)
    up = h.diff()
    dn = -l.diff()
    plus = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=df.index)
    minus = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=df.index)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = rma(tr, n).replace(0, np.nan)
    pdi = 100 * rma(plus, n) / atr
    mdi = 100 * rma(minus, n) / atr
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return pdi, mdi, rma(dx.fillna(0), sm)
 
 
def estructura_alcista(osc, left, right, max_age):
    """
    Réplica barra por barra del indicador Pine "SLY_HH_HL" (oscilador: MACD PRO).
    Devuelve el patrón vigente y hace cuántas velas ocurrió la última marca de cada tipo:
      hl = triángulo MÍN↑, hh = máximo creciente, brk = ruptura, x = pierde la línea de mínimos crecientes.
    """
    n = len(osc)
    h1 = h2 = l1 = l2 = None
    h2_i = l1_i = l2_i = None
    prev_support = prev_h2 = prev_osc = None
    marca = {"hl": None, "hh": None, "brk": None, "x": None}
    pattern = False
 
    for t in range(n):
        new_ph = new_pl = False
        p = t - right
        if p - left >= 0:
            w = osc[p - left: t + 1]
            if not np.isnan(w).any():
                v = osc[p]
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
    return {"pattern": pattern, "edad": edad}
 
 
def pivot_len(tf):
    """Largo del pivote de precio automático según temporalidad (igual que los scripts de Pine)."""
    s = TF_MS[tf] / 1000
    return 15 if s <= 300 else 10 if s < 86_400 else 8 if s < 604_800 else 5
 
 
def ultimos_pivotes(high, low, ln):
    """Último pivote de máximo y de mínimo de precio confirmados (índices de vela)."""
    n = len(high)
    ph_b = pl_b = None
    for p in range(ln, n - ln):
        if high[p] >= high[p - ln: p + ln + 1].max():
            ph_b = p
        if low[p] <= low[p - ln: p + ln + 1].min():
            pl_b = p
    return ph_b, pl_b
 
 
def perfil(h, l, c, v, rows=ROWS, va_pct=VA_PCT):
    """Perfil de volumen horizontal: POC, VAH, VAL y delta compra-venta (aprox. por ubicación del cierre)."""
    pmn, pmx = float(l.min()), float(h.max())
    lh = (pmx - pmn) / rows
    if lh <= 0:
        return None
    arr = np.zeros(rows)
    buy = tot = 0.0
    for i in range(len(h)):
        rg = h[i] - l[i]
        br = (c[i] - l[i]) / rg if rg > 0 else 0.5
        lo = min(rows - 1, max(0, int((l[i] - pmn) // lh)))
        hi = min(rows - 1, max(0, int((h[i] - pmn) // lh)))
        arr[lo:hi + 1] += v[i] / (hi - lo + 1)
        buy += v[i] * br
        tot += v[i]
    pidx = int(np.argmax(arr))
    lo_i = hi_i = pidx
    acc, target = arr[pidx], arr.sum() * va_pct
    while acc < target and (lo_i > 0 or hi_i < rows - 1):
        up = arr[hi_i + 1] if hi_i < rows - 1 else -1.0
        dn = arr[lo_i - 1] if lo_i > 0 else -1.0
        if up >= dn:
            hi_i += 1
            acc += up
        else:
            lo_i -= 1
            acc += dn
    return {
        "poc": pmn + (pidx + 0.5) * lh,
        "vah": pmn + (hi_i + 1) * lh,
        "val": pmn + lo_i * lh,
        "delta": (2 * buy - tot) / tot * 100 if tot > 0 else 0.0,
    }
 
 
def info_volumen_fibo(df, tf):
    """Informativo: volumen (perfil anclado al último pivote de precio) y zona de Fibonacci del último swing."""
    h = df["high"].astype(float).to_numpy()
    l = df["low"].astype(float).to_numpy()
    c = df["close"].astype(float).to_numpy()
    v = df["vol"].astype(float).to_numpy()
    n = len(df)
    close = c[-1]
    ph_b, pl_b = ultimos_pivotes(h, l, pivot_len(tf))
 
    # ----- Volumen -----
    vol_txt, poc = "Sin pivote", None
    piv = [x for x in (ph_b, pl_b) if x is not None]
    if piv:
        anchor = max(piv)
        n_prof = max(5, min(MAX_PROF, n - anchor))
        pr = perfil(h[-n_prof:], l[-n_prof:], c[-n_prof:], v[-n_prof:])
        if pr:
            poc = pr["poc"]
            sma = pd.Series(v).rolling(20).mean().iloc[-1]
            std = pd.Series(v).rolling(20).std().iloc[-1]
            z = (v[-1] - sma) / std if std and std > 0 else 0.0
            area = "sobre VAH" if close > pr["vah"] else "bajo VAL" if close < pr["val"] else "dentro del área de valor"
            vol_txt = (f"{'Sobre' if close >= pr['poc'] else 'Bajo'} POC · {area} · "
                       f"Δ {pr['delta']:+.0f}% · RVOL {z:+.1f} ({n_prof} velas)")
            pr_all = pr
        else:
            pr_all = None
    else:
        pr_all = None
 
    # ----- Fibonacci -----
    fib_txt = "Sin swing"
    if ph_b is not None and pl_b is not None:
        hi, lo = float(h[ph_b]), float(l[pl_b])
        if hi > lo:
            fup = ph_b > pl_b
            rg = hi - lo
            ret = (hi - close) / rg if fup else (close - lo) / rg
            fib_txt = f"{'Alza' if fup else 'Baja'} · {'ret' if fup else 'rebote'} {ret * 100:.0f}%"
            if 0.5 <= ret <= 0.618:
                fib_txt += " · ZONA DORADA"
            if pr_all:
                k50 = hi - rg * 0.5 if fup else lo + rg * 0.5
                k618 = hi - rg * 0.618 if fup else lo + rg * 0.618
                tol = close * 0.005
                for nombre, nivel in (("POC", pr_all["poc"]), ("VAH", pr_all["vah"]), ("VAL", pr_all["val"])):
                    if abs(k50 - nivel) <= tol or abs(k618 - nivel) <= tol:
                        fib_txt += f" ≈{nombre}"
    return vol_txt, fib_txt
 
 
def contexto_1d(df1):
    """Informativo: régimen diario (EMA 52 vs 260) y ADX."""
    if len(df1) < 270:
        return "Sin historial 1D"
    close = df1["close"].astype(float)
    e52 = close.ewm(span=52, adjust=False).mean().iloc[-1]
    e260 = close.ewm(span=260, adjust=False).mean().iloc[-1]
    _, _, adx = adx_calc(df1)
    a, a_prev = adx.iloc[-1], adx.iloc[-2]
    estado = "rango" if a < 20 else "naciente" if a < 25 else "tendencia" if a < 40 else "fuerte"
    return f"{'Alcista' if e52 > e260 else 'Bajista'} · ADX {a:.0f}{'↑' if a > a_prev else '↓'} ({estado})"
 
 
def edad_txt(e, tf):
    horas = e * TF_MS[tf] / 3_600_000
    t = f"{horas:.0f} h" if horas < 48 else f"{horas / 24:.0f} d"
    return f"MÍN↑ 🔺 hace {e} vela{'' if e == 1 else 's'} ({t})"
 
 
# ─────────────────────────────────────────────
# KUCOIN FUTUROS PERPETUOS
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    return ccxt.kucoinfutures({"enableRateLimit": True})
 
 
def fetch_universe(top_n):
    """Los N perpetuos lineales USDT de mayor volumen en 24h, sin stablecoins."""
    ex = get_exchange()
    markets = ex.load_markets()
    tickers = ex.fetch_tickers()
    filas = []
    for sym, m in markets.items():
        if not (m.get("swap") and m.get("linear") and m.get("quote") == "USDT" and m.get("active", True)):
            continue
        base = m.get("base", "")
        if base in STABLES:
            continue
        t = tickers.get(sym) or {}
        qv = t.get("quoteVolume")
        if qv is None and t.get("baseVolume") and t.get("last"):
            qv = t["baseVolume"] * t["last"]
        filas.append((sym, base, float(qv or 0.0)))
    filas.sort(key=lambda x: -x[2])
    return filas[:top_n]
 
 
@st.cache_data(ttl=120, show_spinner=False)
def fetch_ohlcv_df(sym, tf, bars=600):
    """Velas con paginación (KuCoin entrega pocas velas por pedido)."""
    ex = get_exchange()
    ms = TF_MS[tf]
    ahora = ex.milliseconds()
    since = ahora - bars * ms
    out = []
    for _ in range(12):
        chunk = ex.fetch_ohlcv(sym, timeframe=tf, since=since, limit=200)
        if not chunk:
            break
        out += chunk
        ultimo = chunk[-1][0]
        if ultimo >= ahora - ms:
            break
        since = ultimo + ms
    df = pd.DataFrame(out, columns=["time", "open", "high", "low", "close", "vol"])
    return df.drop_duplicates("time").sort_values("time").reset_index(drop=True)
 
 
def recortar(df, tf, solo_cerradas):
    """Quita la última vela si todavía no cerró."""
    if solo_cerradas and len(df) and df["time"].iloc[-1] + TF_MS[tf] > time.time() * 1000:
        df = df.iloc[:-1]
    return df.reset_index(drop=True)
 
 
def analizar(sym, tf, max_edad, solo_cerradas):
    df = recortar(fetch_ohlcv_df(sym, tf), tf, solo_cerradas)
    if len(df) < 120:
        return {"estado": "Sin historial"}
    close = df["close"].astype(float)
    osc = (dema(close, 12) - dema(close, 26)).to_numpy()
    r = estructura_alcista(osc, LEFT, RIGHT, MAX_AGE)
    e_hl, e_x = r["edad"]["hl"], r["edad"]["x"]
    # Señal vigente: triángulo reciente y sin que el MACD haya perdido la línea después
    if e_hl is None or e_hl > max_edad or (e_x is not None and e_x < e_hl):
        return {"estado": "sin_senal"}
    vol_txt, fib_txt = info_volumen_fibo(df, tf)
    ctx = contexto_1d(recortar(fetch_ohlcv_df(sym, "1d"), "1d", solo_cerradas))
    return {"estado": "senal", "edad": e_hl, "senal": edad_txt(e_hl, tf),
            "ctx": ctx, "vol": vol_txt, "fib": fib_txt}
 
 
# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
st.title("🛡️ SLY | SEÑALES KUCOIN PERPETUOS (largos)")
 
with st.sidebar:
    st.header("⚙️ Configuración")
    tf_label = st.selectbox("Temporalidad de la señal:", list(TF_LABEL.keys()), index=2)
    tf = TF_LABEL[tf_label]
    top_n = st.number_input("Cantidad de perpetuos (por volumen 24h):", 10, 200, 50, step=10)
    max_edad = st.number_input("Antigüedad máxima de la señal (velas):", 0, 50, 5,
                               help="0 = solo la última vela cerrada.")
    solo_cerradas = st.checkbox("Usar solo velas cerradas", value=True,
                                help="Evita señales de una vela que todavía se está formando.")
 
    if st.button("🚀 ANALIZAR KUCOIN PERPETUOS", type="primary"):
        st.session_state["kc_perp_results"] = {}
        errores, analizados = [], 0
        try:
            universo = fetch_universe(int(top_n))
        except Exception as e:
            universo = []
            st.error(f"No se pudo leer el mercado de KuCoin Futuros: {type(e).__name__}: {str(e)[:120]}")
 
        prog = st.progress(0)
        for i, (sym, base, qv) in enumerate(universo):
            prog.progress((i + 1) / len(universo), text=f"Analizando: {base}")
            try:
                res = analizar(sym, tf, int(max_edad), solo_cerradas)
                analizados += 1
                if res["estado"] == "senal":
                    res["activo"], res["qv"] = base, qv
                    st.session_state["kc_perp_results"][sym] = res
            except Exception as e:
                errores.append(f"{base}: {type(e).__name__} {str(e)[:80]}")
        prog.empty()
        st.session_state["kc_perp_meta"] = {"tf": tf_label, "analizados": analizados,
                                            "universo": len(universo), "errores": errores}
        st.rerun()
 
    if st.button("🗑️ Limpiar"):
        st.session_state["kc_perp_results"] = {}
        st.session_state["kc_perp_meta"] = {}
        st.rerun()
 
# ─────────────────────────────────────────────
# TABLA (solo activos con señal)
# ─────────────────────────────────────────────
meta = st.session_state["kc_perp_meta"]
res = st.session_state["kc_perp_results"]
 
if meta:
    c1, c2, c3 = st.columns(3)
    c1.metric("Temporalidad", meta["tf"])
    c2.metric("Perpetuos analizados", f"{meta['analizados']} / {meta['universo']}")
    c3.metric("Con señal", len(res))
    if meta["errores"]:
        with st.expander(f"⚠️ {len(meta['errores'])} activos con error"):
            st.write("\n".join(meta["errores"]))
 
if res:
    filas = sorted(res.values(), key=lambda r: (r["edad"], -r["qv"]))
    df_t = pd.DataFrame({
        "Activo": [r["activo"] for r in filas],
        f"Señal {meta['tf']}": [r["senal"] for r in filas],
        "Contexto 1D (info)": [r["ctx"] for r in filas],
        "Volumen (info)": [r["vol"] for r in filas],
        "Fibonacci (info)": [r["fib"] for r in filas],
        "Vol 24h (M USDT)": [round(r["qv"] / 1e6, 1) for r in filas],
    })
    col_senal = f"Señal {meta['tf']}"
 
    def color_senal(_):
        return "background-color: #C8E6C9; color: #1B5E20; font-weight: bold;"
 
    def color_ctx(v):
        s = str(v)
        if s.startswith("Alcista"):
            return "color: #1B5E20; font-weight: bold;"
        if s.startswith("Bajista"):
            return "color: #B71C1C; font-weight: bold;"
        return "color: #9E9E9E;"
 
    def color_vol(v):
        s = str(v)
        if s.startswith("Sobre POC"):
            return "color: #1B5E20;"
        if s.startswith("Bajo POC"):
            return "color: #B71C1C;"
        return "color: #9E9E9E;"
 
    def color_fib(v):
        if "ZONA DORADA" in str(v):
            return "background-color: #FFF59D; color: #5D4037; font-weight: bold;"
        return "color: #616161;"
 
    st.dataframe(
        df_t.style.map(color_senal, subset=[col_senal])
                  .map(color_ctx, subset=["Contexto 1D (info)"])
                  .map(color_vol, subset=["Volumen (info)"])
                  .map(color_fib, subset=["Fibonacci (info)"]),
        use_container_width=True, height=600, hide_index=True)
elif meta:
    st.info("Ningún perpetuo tiene señal con esta configuración. Probá subir la antigüedad máxima de la señal.")
else:
    st.info("👈 Elegí la temporalidad y presioná ANALIZAR KUCOIN PERPETUOS.")
