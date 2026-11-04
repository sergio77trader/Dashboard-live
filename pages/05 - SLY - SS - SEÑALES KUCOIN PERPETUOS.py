import time
import numpy as np
import pandas as pd
import streamlit as st
import ccxt
 
# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | SEÑAL UNIFICADA KUCOIN")
 
st.markdown("""
<style>
    .stApp { background-color: #FFFFFF; color: #1C1E21; }
    .stDataFrame { font-size: 11px; font-family: 'Roboto Mono', monospace; }
    h1 { color: #E65100; font-weight: 800; border-bottom: 3px solid #E65100; }
    .stProgress > div > div > div > div { background-color: #E65100; }
    .sector-box { background-color: #FFF3E0; padding: 12px; border-radius: 8px; border-left: 5px solid #E64A19; margin-bottom: 10px; }
    .sector-title { font-weight: bold; color: #BF360C; font-size: 1.05em; }
</style>
""", unsafe_allow_html=True)
 
for k, v in {"u_results": {}, "u_errors": {}, "u_list": [], "u_market": None}.items():
    if k not in st.session_state:
        st.session_state[k] = v
 
TF_OPTIONS = {"15 MIN": "15m", "30 MIN": "30m", "1 HS": "1h", "4 HS": "4h", "1 DIA": "1d", "1 SEMANA": "1w"}
TF_MS = {"15m": 900_000, "30m": 1_800_000, "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000, "1w": 604_800_000}
MARKETS = {"Perpetuos USDT (KuCoin Futuros)": "futures", "Spot USDT (KuCoin)": "spot"}
STABLES = {"USDC", "USDT", "DAI", "TUSD", "FDUSD", "USDE", "PYUSD", "USDD", "BUSD", "PAX"}
MIN_BARS = 270          # EMA 260 necesita historial
ROWS, VA_PCT, MAX_PROF = 40, 0.70, 300   # perfil de volumen (igual que el Pine)
POC_TOL = 0.3           # % para considerar "EN EL POC"
 
CRYPTO_SECTORS = {
    "LEADER": ["BTC", "ETH"],
    "LAYER 1": ["SOL", "ADA", "DOT", "AVAX", "MATIC", "POL", "NEAR", "FTM", "ALGO", "SUI", "APT", "TON", "ATOM"],
    "DEFI/L2": ["ARB", "OP", "LINK", "UNI", "AAVE", "LDO", "MKR", "INJ"],
    "AI/DEPIN": ["RNDR", "RENDER", "FET", "FIL", "THETA", "TAO", "AGIX"],
    "MEMES": ["DOGE", "SHIB", "PEPE", "BONK", "FLOKI", "WIF"],
    "EXCHANGE": ["BNB", "KCS", "OKB"],
}
 
 
def get_sector(base):
    for sector, members in CRYPTO_SECTORS.items():
        if base.upper() in members:
            return sector
    return "ALTCOINS / OTROS"
 
 
def fmt_px(x):
    return f"{x:.6g}"
 
 
# ─────────────────────────────────────────────
# MOTORES TÉCNICOS SLY
# ─────────────────────────────────────────────
def dema(s, length):
    e1 = s.ewm(span=length, adjust=False).mean()
    e2 = e1.ewm(span=length, adjust=False).mean()
    return 2 * e1 - e2
 
 
def rma(s, n):
    return s.ewm(alpha=1 / n, adjust=False).mean()
 
 
def rsi_calc(close, n=14):
    d = close.diff()
    up = d.clip(lower=0)
    dn = -d.clip(upper=0)
    rs = rma(up, n) / rma(dn, n).replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50)
 
 
def adx_calc(df, n=14, sm=14):
    """ADX de Wilder (igual que ta.dmi). Devuelve (+DI, -DI, ADX)."""
    h, l, c = df["high"].astype(float), df["low"].astype(float), df["close"].astype(float)
    up, dn = h.diff(), -l.diff()
    plus = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=df.index)
    minus = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=df.index)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = rma(tr, n).replace(0, np.nan)
    pdi = 100 * rma(plus, n) / atr
    mdi = 100 * rma(minus, n) / atr
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return pdi, mdi, rma(dx.fillna(0), sm)
 
 
def heikin_green(df):
    """Heikin Ashi recursivo (igual que el Pine). Devuelve array booleano: True = vela verde."""
    o, h, l, c = (df[k].astype(float).to_numpy() for k in ("open", "high", "low", "close"))
    hac = (o + h + l + c) / 4
    hao = np.zeros(len(df))
    hao[0] = (o[0] + c[0]) / 2
    for i in range(1, len(df)):
        hao[i] = (hao[i - 1] + hac[i - 1]) / 2
    return hac > hao
 
 
def macd_alerts(hist):
    """Giro alcista / bajista del histograma (script 1, MACD PRO)."""
    h = hist.to_numpy()
    h1 = np.roll(h, 1)
    h2 = np.roll(h, 2)
    h1[:1] = np.nan
    h2[:2] = np.nan
    with np.errstate(invalid="ignore"):
        long_a = ((h > 0) & (h1 <= 0)) | ((h > h1) & (h1 < h2) & (h < 0))
        short_a = ((h < 0) & (h1 >= 0)) | ((h < h1) & (h1 > h2) & (h > 0))
    return long_a, short_a
 
 
# ----- Volumen: perfil anclado al último pivote de precio -----
def pivot_len(tf):
    s = TF_MS[tf] / 1000
    return 15 if s <= 300 else 10 if s < 86_400 else 8 if s < 604_800 else 5
 
 
def ultimos_pivotes(high, low, ln):
    n = len(high)
    ph_b = pl_b = None
    for p in range(ln, n - ln):
        if high[p] >= high[p - ln: p + ln + 1].max():
            ph_b = p
        if low[p] <= low[p - ln: p + ln + 1].min():
            pl_b = p
    return ph_b, pl_b
 
 
def perfil(h, l, c, v, rows=ROWS, va_pct=VA_PCT):
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
    return {"poc": pmn + (pidx + 0.5) * lh, "vah": pmn + (hi_i + 1) * lh, "val": pmn + lo_i * lh,
            "delta": (2 * buy - tot) / tot * 100 if tot > 0 else 0.0}
 
 
def info_volumen(df, tf):
    h = df["high"].astype(float).to_numpy()
    l = df["low"].astype(float).to_numpy()
    c = df["close"].astype(float).to_numpy()
    v = df["vol"].astype(float).to_numpy()
    n, close = len(df), c[-1]
    ph_b, pl_b = ultimos_pivotes(h, l, pivot_len(tf))
    piv = [x for x in (ph_b, pl_b) if x is not None]
    n_prof = max(10, min(MAX_PROF, n - max(piv) if piv else 100))
    pr = perfil(h[-n_prof:], l[-n_prof:], c[-n_prof:], v[-n_prof:])
    if not pr:
        return None
    sma = pd.Series(v).rolling(20).mean().iloc[-1]
    std = pd.Series(v).rolling(20).std().iloc[-1]
    rvol = (v[-1] - sma) / std if std and std > 0 else 0.0
    if close > pr["vah"]:
        zona = "SOBRE VAH 🟢"
    elif close < pr["val"]:
        zona = "BAJO VAL 🔴"
    elif abs(close - pr["poc"]) / close * 100 <= POC_TOL:
        zona = "EN EL POC 🟠"
    elif close > pr["poc"]:
        zona = "Entre POC y VAH"
    else:
        zona = "Entre VAL y POC"
    dist = lambda x: f"{fmt_px(x)} ({(x / close - 1) * 100:+.1f}%)"
    return {"zona": zona, "poc": dist(pr["poc"]), "vah": dist(pr["vah"]), "val": dist(pr["val"]),
            "vol": f"Δ {pr['delta']:+.0f}% · RVOL {rvol:+.1f} ({n_prof} velas)"}
 
 
# ─────────────────────────────────────────────
# KUCOIN: CONECTIVIDAD, UNIVERSO Y VELAS
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange(kind):
    if kind == "futures":
        return ccxt.kucoinfutures({"enableRateLimit": True})
    return ccxt.kucoin({"enableRateLimit": True})
 
 
def fetch_symbols(kind):
    """Lista de símbolos ordenada por volumen 24h (el Lote 1 son los más líquidos)."""
    ex = get_exchange(kind)
    markets = ex.load_markets()
    filas = []
    for sym, m in markets.items():
        if m.get("quote") != "USDT" or not m.get("active", True):
            continue
        base = m.get("base", "")
        if base in STABLES or base.endswith(("3L", "3S", "5L", "5S")):
            continue
        if kind == "futures" and not (m.get("swap") and m.get("linear")):
            continue
        if kind == "spot" and not (m.get("spot") and ":" not in sym):
            continue
        filas.append([sym, 0.0])
    try:
        tk = ex.fetch_tickers()
        for f in filas:
            t = tk.get(f[0]) or {}
            qv = t.get("quoteVolume")
            if qv is None and t.get("baseVolume") and t.get("last"):
                qv = t["baseVolume"] * t["last"]
            f[1] = float(qv or 0.0)
        filas.sort(key=lambda x: -x[1])
    except Exception:
        filas.sort(key=lambda x: x[0])
    return [f[0] for f in filas], {f[0]: f[1] for f in filas}
 
 
def fetch_ohlcv_df(ex, sym, tf, bars, per_call):
    ms = TF_MS[tf]
    ahora = ex.milliseconds()
    since = ahora - bars * ms
    out = []
    for _ in range(15):
        chunk = ex.fetch_ohlcv(sym, timeframe=tf, since=since, limit=per_call)
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
    if solo_cerradas and len(df) and df["time"].iloc[-1] + TF_MS[tf] > time.time() * 1000:
        df = df.iloc[:-1]
    return df.reset_index(drop=True)
 
 
# ─────────────────────────────────────────────
# ANÁLISIS DE UN ACTIVO
# ─────────────────────────────────────────────
def edad_txt(e, tf):
    horas = e * TF_MS[tf] / 3_600_000
    t = f"{horas:.0f} h" if horas < 48 else f"{horas / 24:.0f} d"
    return f"hace {e} vela{'' if e == 1 else 's'} ({t})"
 
 
def macd_semanal(ex, sym, per_call):
    """Informativo: MACD semanal alcista o bajista (MACD estándar, como el Pine)."""
    try:
        w = fetch_ohlcv_df(ex, sym, "1w", 120, per_call)["close"].astype(float)
        m = w.ewm(span=12, adjust=False).mean() - w.ewm(span=26, adjust=False).mean()
        return "Alcista 🟢" if m.iloc[-1] > m.ewm(span=9, adjust=False).mean().iloc[-1] else "Bajista 🔴"
    except Exception:
        return "N/A"
 
 
def analizar(ex, kind, sym, tf, solo_cerradas, contra_tendencia, con_semanal, qv):
    per_call = 200 if kind == "futures" else 1000
    df = recortar(fetch_ohlcv_df(ex, sym, tf, 800, per_call), tf, solo_cerradas)
    if len(df) < MIN_BARS:
        raise ValueError(f"Historial insuficiente: {len(df)} velas (se necesitan ≥{MIN_BARS} para la EMA 260)")
 
    close = df["close"].astype(float)
    n = len(df)
 
    # Tendencia (EMA 52 vs EMA 260)
    ema52 = close.ewm(span=52, adjust=False).mean()
    ema260 = close.ewm(span=260, adjust=False).mean()
    bull = (ema52 > ema260).to_numpy()
    tendencia = "LONG 🟢" if bull[-1] else "SHORT 🔴"
 
    # MACD PRO (señal)
    macd = dema(close, 12) - dema(close, 26)
    hist = macd - macd.ewm(span=9, adjust=False).mean()
    long_a, short_a = macd_alerts(hist)
    h_now, h_prev = hist.iloc[-1], hist.iloc[-2]
 
    long_entry = long_a & (bull | contra_tendencia)
    short_entry = short_a & ((~bull) | contra_tendencia)
    iL = int(np.flatnonzero(long_entry)[-1]) if long_entry.any() else None
    iS = int(np.flatnonzero(short_entry)[-1]) if short_entry.any() else None
    vig = None
    if iL is not None and not short_a[iL + 1:].any():
        vig = ("LONG", iL)
    if iS is not None and not long_a[iS + 1:].any():
        vig = ("SHORT", iS)
 
    senal, veredicto, pnl, edad, direccion = "Sin señal", "-", "-", 9999, "-"
    if vig:
        direccion, idx = vig
        edad = n - 1 - idx
        a_favor = (direccion == "LONG") == bool(bull[idx])
        senal = f"{direccion} {'🟢' if direccion == 'LONG' else '🔴'} {edad_txt(edad, tf)}" + ("" if a_favor else " · REBOTE")
        px0, px1 = float(close.iloc[idx]), float(close.iloc[-1])
        ret = (px1 / px0 - 1) * 100 * (1 if direccion == "LONG" else -1)
        pnl = f"{ret:+.2f}%"
        if direccion == "LONG":
            veredicto = "CERRAR 🔴" if (h_prev > 0 and h_now <= 0) else "MANTENER 🟢" if h_now > h_prev else "PIERDE FUERZA 🟡"
        else:
            veredicto = "CERRAR 🔴" if (h_prev < 0 and h_now >= 0) else "MANTENER 🟢" if h_now < h_prev else "PIERDE FUERZA 🟡"
 
    # Estado MACD
    if h_now > 0:
        macd_txt = "Positivo · gana fuerza ▲" if h_now > h_prev else "Positivo · PIERDE fuerza ▼"
    else:
        macd_txt = "Negativo · cae con fuerza ▼" if h_now < h_prev else "Negativo · se recupera ▲"
 
    # RSI PRO
    rsi = dema(rsi_calc(close, 14), 5)
    r_now, r_prev = rsi.iloc[-1], rsi.iloc[-2]
    basis, sd = rsi.rolling(20).mean().iloc[-1], rsi.rolling(20).std().iloc[-1]
    ext = " · sobrecompra" if r_now > basis + 2 * sd else " · sobreventa" if r_now < basis - 2 * sd else ""
    rsi_txt = f"{r_now:.1f} {'▲ GANA fuerza' if r_now > r_prev else '▼ PIERDE fuerza'} · {'sobre' if r_now > 50 else 'bajo'} 50{ext}"
 
    # Heikin Ashi
    ha = heikin_green(df)
    cambio = np.flatnonzero(ha[1:] != ha[:-1])
    ha_bars = (n - 1 - (cambio[-1] + 1)) if len(cambio) else n - 1
    ha_txt = f"{'VERDE 🟢' if ha[-1] else 'ROJA 🔴'} · hace {ha_bars} vela{'' if ha_bars == 1 else 's'}"
 
    # ADX (temporalidad de análisis)
    pdi, mdi, adx = adx_calc(df)
    a, a_prev = adx.iloc[-1], adx.iloc[-2]
    estado = "Rango" if a < 20 else "Naciente" if a < 25 else "Tendencia" if a < 40 else "Tendencia fuerte"
    adx_txt = f"{a:.1f}{'↑' if a > a_prev else '↓'} {'+DI' if pdi.iloc[-1] > mdi.iloc[-1] else '-DI'} {estado}"
 
    # Volumen
    vol = info_volumen(df, tf) or {"zona": "s/d", "poc": "-", "vah": "-", "val": "-", "vol": "-"}
 
    base = sym.split("/")[0]
    return {
        "Activo": base, "Sector": get_sector(base), "Tendencia": tendencia,
        "Señal": senal, "Veredicto": veredicto, "PnL": pnl,
        "MACD": macd_txt, "RSI": rsi_txt, "Heikin Ashi": ha_txt,
        "MACD 1w": macd_semanal(ex, sym, per_call) if con_semanal else "-",
        "Precio vs volumen": vol["zona"], "POC": vol["poc"], "VAH": vol["vah"], "VAL": vol["val"],
        "Volumen": vol["vol"], "ADX": adx_txt,
        "Precio": fmt_px(float(close.iloc[-1])), "Vol 24h (M)": round(qv / 1e6, 1),
        "TF": tf, "_dir": direccion, "_edad": edad,
    }
 
 
# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
st.title("🛡️ SLY | SEÑAL UNIFICADA KUCOIN")
 
with st.sidebar:
    st.header("⚙️ Configuración")
 
    st.subheader("1. Mercado y tiempo")
    mercado_lbl = st.selectbox("Mercado:", list(MARKETS.keys()), index=0)
    kind = MARKETS[mercado_lbl]
    tf_lbl = st.selectbox("Temporalidad de análisis:", list(TF_OPTIONS.keys()), index=3)
    tf = TF_OPTIONS[tf_lbl]
    solo_cerradas = st.checkbox("Usar solo velas cerradas", value=True)
    contra = st.checkbox("Habilitar señales contra tendencia (rebotes)", value=False,
                         help="Apagado: en tendencia LONG (EMA 52 > EMA 260) solo busca largos y en tendencia SHORT solo cortos. "
                              "Encendido: también toma el giro del MACD contra la tendencia y lo marca como REBOTE.")
    con_semanal = st.checkbox("Incluir MACD semanal (1 pedido extra por activo)", value=False)
 
    if st.button("📡 Sincronizar Mercado KuCoin"):
        try:
            lst, vols = fetch_symbols(kind)
            st.session_state["u_list"], st.session_state["u_vols"] = lst, vols
            st.session_state["u_market"] = kind
        except Exception as e:
            st.error(f"No se pudo leer el mercado: {type(e).__name__}: {str(e)[:150]}")
        st.rerun()
 
    if st.session_state["u_list"] and st.session_state["u_market"] == kind:
        st.subheader("2. Ejecución por lotes")
        lote_size = st.number_input("Tamaño de Lote:", 10, 100, 30)
        total_lotes = (len(st.session_state["u_list"]) - 1) // lote_size + 1
        batch_idx = st.selectbox("Seleccionar Lote:", range(total_lotes), format_func=lambda x: f"Lote {x + 1}")
        st.caption(f"{len(st.session_state['u_list'])} activos · ordenados por volumen 24h")
 
        if st.button("🚀 ACTUALIZAR Y ACUMULAR", type="primary"):
            ex = get_exchange(kind)
            subset = st.session_state["u_list"][batch_idx * lote_size:(batch_idx + 1) * lote_size]
            prog = st.progress(0)
            for i, sym in enumerate(subset):
                prog.progress((i + 1) / len(subset), text=f"Auditando {tf_lbl}: {sym}")
                try:
                    res = analizar(ex, kind, sym, tf, solo_cerradas, contra, con_semanal,
                                   st.session_state.get("u_vols", {}).get(sym, 0.0))
                    st.session_state["u_results"][(sym, tf)] = res
                    st.session_state["u_errors"].pop((sym, tf), None)
                except Exception as e:
                    st.session_state["u_errors"][(sym, tf)] = f"{sym} [{tf_lbl}]: {type(e).__name__}: {str(e)[:100]}"
                time.sleep(0.05)
            prog.empty()
            st.rerun()
    elif st.session_state["u_list"]:
        st.info("Cambiaste de mercado: presioná Sincronizar de nuevo.")
 
    if st.button("🗑️ Limpiar Memoria"):
        st.session_state["u_results"] = {}
        st.session_state["u_errors"] = {}
        st.rerun()
 
# ─────────────────────────────────────────────
# RESULTADOS
# ─────────────────────────────────────────────
res = [r for (s, t), r in st.session_state["u_results"].items() if t == tf]
errs = [m for (s, t), m in st.session_state["u_errors"].items() if t == tf]
 
if res:
    f1, f2, f3 = st.columns(3)
    solo_vig = f1.checkbox("Solo con señal vigente", value=True)
    max_edad = f2.number_input("Antigüedad máxima de la señal (velas)", 0, 500, 10)
    dir_sel = f3.radio("Dirección", ["Todas", "LONG", "SHORT"], horizontal=True)
 
    dfa = pd.DataFrame(res)
    vig = dfa[dfa["_dir"] != "-"]
    st.subheader(f"📊 RESUMEN DE EXPOSICIÓN ({tf_lbl})")
    m1, m2, m3 = st.columns(3)
    m1.metric("Analizados (acumulados)", len(dfa))
    m2.metric("LONG vigentes", int((vig["_dir"] == "LONG").sum()))
    m3.metric("SHORT vigentes", int((vig["_dir"] == "SHORT").sum()))
 
    if not vig.empty:
        resumen = vig.groupby("Sector")["Activo"].apply(list).reset_index()
        cols = st.columns(3)
        for idx, row in resumen.iterrows():
            with cols[idx % 3]:
                st.markdown(f"""<div class="sector-box"><div class="sector-title">{row['Sector']}: {len(row['Activo'])}</div>
                <div style='font-size:0.85em;'>{', '.join(row['Activo'])}</div></div>""", unsafe_allow_html=True)
 
    show = dfa.copy()
    if solo_vig:
        show = show[(show["_dir"] != "-") & (show["_edad"] <= max_edad)]
    if dir_sel != "Todas":
        show = show[show["_dir"] == dir_sel]
    show = show.sort_values(by=["_edad", "Vol 24h (M)"], ascending=[True, False])
 
    cols_order = ["Activo", "Sector", "Tendencia", "Señal", "Veredicto", "PnL", "MACD", "RSI", "Heikin Ashi", "MACD 1w",
                  "Precio vs volumen", "POC", "VAH", "VAL", "Volumen", "ADX", "Precio", "Vol 24h (M)", "TF"]
    if not con_semanal and (show["MACD 1w"] == "-").all():
        cols_order.remove("MACD 1w")
    show = show[cols_order]
 
    def color_cells(val):
        s = str(val)
        if s.startswith("LONG") or "VERDE" in s or "GANA" in s or "gana" in s or "MANTENER" in s or "SOBRE VAH" in s or s.startswith("Alcista") or "se recupera" in s:
            return "background-color: #C8E6C9; color: #1B5E20; font-weight: bold;"
        if s.startswith("SHORT") or "ROJA" in s or "CERRAR" in s or "BAJO VAL" in s or s.startswith("Bajista") or "cae con" in s:
            return "background-color: #FFCDD2; color: #B71C1C; font-weight: bold;"
        if "PIERDE" in s:
            return "background-color: #FFF9C4; color: #827717; font-weight: bold;"
        if "EN EL POC" in s:
            return "background-color: #FFE0B2; color: #E65100; font-weight: bold;"
        return ""
 
    st.subheader(f"📋 Matriz de Señales ({tf_lbl})")
    if show.empty:
        st.info("Ningún activo analizado cumple el filtro. Probá subir la antigüedad máxima o desmarcar 'Solo con señal vigente'.")
    else:
        st.dataframe(show.style.map(color_cells,
                                    subset=[c for c in ["Tendencia", "Señal", "Veredicto", "MACD", "RSI", "Heikin Ashi", "MACD 1w", "Precio vs volumen"] if c in show.columns]),
                     use_container_width=True, height=600, hide_index=True)
else:
    st.info("👈 Elegí mercado y temporalidad, sincronizá el mercado y analizá lotes.")
 
if errs:
    with st.expander(f"⚠️ {len(errs)} activos con error"):
        st.write("\n\n".join(errs))
