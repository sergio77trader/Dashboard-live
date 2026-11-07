"""
SLY | CRIPTO MOVERS — escáner de criptomonedas que se están moviendo (volumen + volatilidad) con recomendación.
 
Requisitos:  pip install streamlit ccxt pandas numpy
Ejecutar:    streamlit run sly_cripto_movers.py
 
Qué hace: baja velas de KuCoin (perpetuos o spot) por lotes, mide qué tan "activa" está cada cripto
(volumen relativo, expansión de volatilidad, ruptura, compresión previa, cambio de precio), define su dirección
y arma una recomendación con una referencia de stop y objetivo. Es una guía para ordenar candidatas,
no asesoramiento financiero.
"""
import time
 
import numpy as np
import pandas as pd
import streamlit as st
import ccxt
 
# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | CRIPTO MOVERS")
st.markdown("""
<style>
    .stApp { background-color: #FFFFFF; color: #1C1E21; }
    .stDataFrame { font-size: 11px; font-family: 'Roboto Mono', monospace; }
    h1 { color: #4A148C; font-weight: 800; border-bottom: 3px solid #4A148C; }
    .stProgress > div > div > div > div { background-color: #4A148C; }
    .pick-box { background-color: #F3E5F5; padding: 18px; border-radius: 10px; border-left: 6px solid #6A1B9A; margin-bottom: 12px; }
    .pick-title { font-weight: 800; color: #4A148C; font-size: 1.25em; }
</style>
""", unsafe_allow_html=True)
 
for _k, _v in {"m_results": {}, "m_errors": {}, "m_list": [], "m_vols": {}, "m_market": None}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v
 
TF_OPTIONS = {"15 MIN": "15m", "1 HS": "1h", "4 HS": "4h", "1 DIA": "1d"}
TF_MS = {"15m": 900_000, "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}
MARKETS = {"Perpetuos USDT (KuCoin Futuros)": "futures", "Spot USDT (KuCoin)": "spot"}
STABLES = {"USDC", "USDT", "DAI", "TUSD", "FDUSD", "USDE", "PYUSD", "USDD", "BUSD", "PAX"}
BARS = 200
CRYPTO_SECTORS = {
    "LEADER": ["BTC", "ETH"],
    "LAYER 1": ["SOL", "ADA", "DOT", "AVAX", "MATIC", "POL", "NEAR", "FTM", "ALGO", "SUI", "APT", "TON", "ATOM"],
    "DEFI/L2": ["ARB", "OP", "LINK", "UNI", "AAVE", "LDO", "MKR", "INJ"],
    "AI/DEPIN": ["RNDR", "RENDER", "FET", "FIL", "THETA", "TAO", "AGIX"],
    "MEMES": ["DOGE", "SHIB", "PEPE", "BONK", "FLOKI", "WIF"],
    "EXCHANGE": ["BNB", "KCS", "OKB"],
}
REC_OPCIONES = ["LONG", "SHORT", "TARDÍA", "VIGILAR", "SIN MOVIMIENTO", "BAJISTA (spot)", "EVITAR"]
 
 
def get_sector(base):
    for sector, members in CRYPTO_SECTORS.items():
        if base.upper() in members:
            return sector
    return "ALTCOINS / OTROS"
 
 
def fmt_px(x):
    return f"{x:.6g}"
 
 
# ─────────────────────────────────────────────
# DATOS (KuCoin vía ccxt, por lotes)
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange(kind):
    return ccxt.kucoinfutures({"enableRateLimit": True}) if kind == "futures" else ccxt.kucoin({"enableRateLimit": True})
 
 
def fetch_symbols(kind):
    """Símbolos USDT ordenados por volumen 24h (el Lote 1 son los más líquidos)."""
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
    for _ in range(10):
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
    """Quita la última vela si todavía se está formando."""
    if solo_cerradas and len(df) and df["time"].iloc[-1] + TF_MS[tf] > time.time() * 1000:
        df = df.iloc[:-1]
    return df.reset_index(drop=True)
 
 
# ─────────────────────────────────────────────
# MOTOR: QUÉ TAN "ACTIVA" ESTÁ UNA CRIPTO
# ─────────────────────────────────────────────
def rma(s, n):
    return s.ewm(alpha=1 / n, adjust=False).mean()
 
 
def dema(s, length):
    e1 = s.ewm(span=length, adjust=False).mean()
    e2 = e1.ewm(span=length, adjust=False).mean()
    return 2 * e1 - e2
 
 
def rsi_calc(close, n=14):
    d = close.diff()
    up, dn = d.clip(lower=0), -d.clip(upper=0)
    rs = rma(up, n) / rma(dn, n).replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50)
 
 
def atr_pct(df, n=14):
    """ATR como % del precio (volatilidad de cada vela)."""
    h, l, c = df["high"].astype(float), df["low"].astype(float), df["close"].astype(float)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return rma(tr, n) / c * 100
 
 
def velas_24h(tf):
    return max(1, int(round(86_400_000 / TF_MS[tf])))
 
 
def analizar_mov_df(df, tf, qv):
    """Métricas crudas de movimiento de una cripto. 'df' = velas cerradas (open, high, low, close, vol)."""
    n = len(df)
    if n < 80:
        raise ValueError(f"Historial insuficiente: {n} velas (se necesitan ≥80)")
    c = df["close"].astype(float)
    h = df["high"].astype(float).to_numpy()
    l = df["low"].astype(float).to_numpy()
    v = df["vol"].astype(float).to_numpy()
    cl = c.to_numpy()
    close = float(cl[-1])
 
    k = velas_24h(tf)
    cambio = (close / cl[-1 - k] - 1) * 100
 
    # volumen relativo: promedio de las últimas 3 velas contra el promedio de las 20 anteriores
    base = v[-23:-3].mean()
    rvol = float(v[-3:].mean() / base) if base > 0 else np.nan
 
    # expansión de volatilidad: ATR% de ahora contra su promedio de las 50 velas previas
    ap = atr_pct(df)
    prev = ap.iloc[-51:-1].mean()
    volx = float(ap.iloc[-1] / prev) if prev and prev > 0 else np.nan
    atrp = float(ap.iloc[-1])
 
    # compresión previa (bandas de Bollinger angostas 5 velas atrás) y ruptura reciente (últimas 3 velas)
    sma = c.rolling(20).mean()
    bw = (4 * c.rolling(20).std() / sma * 100).dropna()
    compr = bool((bw.iloc[-100:] <= bw.iloc[-6]).mean() * 100 <= 25) if len(bw) >= 30 else False
    rup, rup_edad = "-", None
    for j in range(1, 4):               # j = 1 es la última vela
        hh = h[-j - 20:-j].max()
        ll = l[-j - 20:-j].min()
        if cl[-j] > hh:
            rup, rup_edad = "ALCISTA", j - 1
            break
        if cl[-j] < ll:
            rup, rup_edad = "BAJISTA", j - 1
            break
 
    # sesgo de dirección
    ema20, ema50 = c.ewm(span=20, adjust=False).mean(), c.ewm(span=50, adjust=False).mean()
    hist = (dema(c, 12) - dema(c, 26)) - (dema(c, 12) - dema(c, 26)).ewm(span=9, adjust=False).mean()
    rsi = float(rsi_calc(c).iloc[-1])
    pts = (1 if cambio > 0.5 else -1 if cambio < -0.5 else 0)
    pts += 2 if rup == "ALCISTA" else -2 if rup == "BAJISTA" else 0
    pts += 1 if ema20.iloc[-1] > ema50.iloc[-1] else -1
    pts += 1 if (hist.iloc[-1] > 0 and hist.iloc[-1] > hist.iloc[-2]) else -1 if (hist.iloc[-1] < 0 and hist.iloc[-1] < hist.iloc[-2]) else 0
    pts += 1 if rsi > 55 else -1 if rsi < 45 else 0
    direccion = "ALCISTA" if pts >= 3 else "BAJISTA" if pts <= -3 else "MIXTO"
 
    # puntaje de movimiento 0-100
    sc = 35 * min((rvol if np.isfinite(rvol) else 0) / 5, 1)
    sc += 25 * min((volx if np.isfinite(volx) else 0) / 3, 1)
    sc += 20 * min(abs(cambio) / 15, 1)
    if rup != "-":
        sc += 15 if (np.isfinite(rvol) and rvol >= 1.5) else 8
        sc += 5 if compr else 0
    score = int(round(min(sc, 100)))
 
    razones = []
    if np.isfinite(rvol):
        razones.append(f"volumen {rvol:.1f}x lo normal")
    if np.isfinite(volx):
        razones.append(f"volatilidad {volx:.1f}x")
    if rup != "-":
        razones.append(f"ruptura {rup.lower()} " + ("(última vela)" if rup_edad == 0 else f"(hace {rup_edad} velas)"))
    if compr:
        razones.append("venía comprimida")
    razones.append(f"{cambio:+.1f}% en {'24 h' if k > 1 else 'la vela'}")
    return {"Cambio %": round(cambio, 2), "RVOL": round(rvol, 2) if np.isfinite(rvol) else np.nan,
            "Vol x": round(volx, 2) if np.isfinite(volx) else np.nan, "ATR %": round(atrp, 2),
            "Ruptura": rup if rup == "-" else f"{rup} ({rup_edad})", "Compresión previa": "Sí" if compr else "No",
            "RSI": round(rsi, 1), "Precio": close, "_dir": direccion, "_dir_pts": int(pts), "_score": score,
            "_atr_abs": atrp * close / 100, "_rsi": rsi, "_cambio": cambio, "_why": " · ".join(razones),
            "Vol 24h (M)": round(qv / 1e6, 2)}
 
 
def recomendar_mov(m, min_qv_m, spot, umbral, btc_cambio=None):
    """Recomendación a partir de métricas ya calculadas (se puede cambiar sin volver a escanear)."""
    score, dire, rsi, cambio = m["_score"], m["_dir"], m["_rsi"], m["_cambio"]
    if m["Vol 24h (M)"] < min_qv_m:
        return "EVITAR ⚫ (poca liquidez)", "EVITAR"
    if score < 40:
        return "SIN MOVIMIENTO ⚪", "SIN MOVIMIENTO"
    if score < umbral:
        return "VIGILAR 🟡 (movimiento moderado)", "VIGILAR"
    if dire == "ALCISTA":
        if cambio > 25 or (rsi > 85 and cambio > 12):
            return "LONG TARDÍO 🟡 (ya extendida)", "TARDÍA"
        cautela = " · cautela: BTC cae" if (btc_cambio is not None and btc_cambio <= -3) else ""
        return f"LONG 🟢{cautela}", "LONG"
    if dire == "BAJISTA":
        if spot:
            return "BAJISTA 🔴 (en spot: evitar)", "BAJISTA (spot)"
        if cambio < -25 or (rsi < 15 and cambio < -12):
            return "SHORT TARDÍO 🟡 (ya extendida)", "TARDÍA"
        return "SHORT 🔴", "SHORT"
    return "MOVIMIENTO SIN DIRECCIÓN 🟡 (esperar)", "VIGILAR"
 
 
def niveles_ref(m, key):
    """Referencia de stop (1,5 ATR) y objetivo (2R) para LONG/SHORT/TARDÍA. Solo orientativa."""
    if key not in ("LONG", "SHORT", "TARDÍA"):
        return "-", "-"
    px, atr = m["Precio"], m["_atr_abs"]
    largo = m["_dir"] == "ALCISTA"
    stop = px - 1.5 * atr if largo else px + 1.5 * atr
    obj = px + 3.0 * atr if largo else px - 3.0 * atr
    return fmt_px(stop), fmt_px(obj)
 
 
def aplicar_reco(dfa, min_qv_m, spot, umbral, btc_cambio=None):
    out = dfa.copy()
    rec = [recomendar_mov(r, min_qv_m, spot, umbral, btc_cambio) for r in out.to_dict("records")]
    out["Recomendación"] = [r[0] for r in rec]
    out["_rec"] = [r[1] for r in rec]
    niv = [niveles_ref(r, k) for r, k in zip(out.to_dict("records"), out["_rec"])]
    out["Stop ref."] = [n[0] for n in niv]
    out["Obj. ref. (2R)"] = [n[1] for n in niv]
    out["Riesgo al stop %"] = [round(1.5 * a, 2) if k in ("LONG", "SHORT", "TARDÍA") else np.nan
                               for a, k in zip(out["ATR %"], out["_rec"])]
    prioridad = {"LONG": 0, "SHORT": 0, "TARDÍA": 1, "VIGILAR": 2, "SIN MOVIMIENTO": 3, "BAJISTA (spot)": 3, "EVITAR": 4}
    out["_prio"] = out["_rec"].map(prioridad)
    return out.sort_values(["_prio", "_score", "Vol 24h (M)"], ascending=[True, False, False]).reset_index(drop=True)
 
 
def analizar(ex, kind, sym, tf, solo_cerradas, qv):
    per_call = 200 if kind == "futures" else 1000
    df = recortar(fetch_ohlcv_df(ex, sym, tf, BARS, per_call), tf, solo_cerradas)
    res = analizar_mov_df(df, tf, qv)
    base = sym.split("/")[0]
    res.update({"Activo": sym.split(":")[0].replace("/USDT", ""), "_sym": sym, "Sector": get_sector(base), "TF": tf})
    return res
 
 
# ═════════════════════════════════════════════
# INTERFAZ
# ═════════════════════════════════════════════
st.title("🚀 SLY | CRIPTO MOVERS")
st.caption("Criptos que se están moviendo con volumen y volatilidad, con una recomendación y una referencia de stop. "
           "Es una guía para ordenar candidatas, no asesoramiento financiero.")
 
with st.sidebar:
    st.header("⚙️ Configuración")
    mercado_lbl = st.selectbox("Mercado:", list(MARKETS.keys()), index=0)
    kind = MARKETS[mercado_lbl]
    tf_lbl = st.selectbox("Temporalidad:", list(TF_OPTIONS.keys()), index=1)
    tf = TF_OPTIONS[tf_lbl]
    solo_cerradas = st.checkbox("Usar solo velas cerradas", value=True,
                                help="Evita medir una vela que todavía se está formando.")
 
    if st.button("📡 Sincronizar mercado KuCoin"):
        try:
            lst, vols = fetch_symbols(kind)
            st.session_state["m_list"], st.session_state["m_vols"], st.session_state["m_market"] = lst, vols, kind
        except Exception as e:
            st.error(f"No se pudo leer el mercado: {type(e).__name__}: {str(e)[:150]}")
        st.rerun()
 
    if st.session_state["m_list"] and st.session_state["m_market"] == kind:
        st.subheader("Lotes (más líquidos primero)")
        lote_size = st.number_input("Tamaño de lote:", 10, 100, 30)
        total_lotes = (len(st.session_state["m_list"]) - 1) // int(lote_size) + 1
        batch_idx = st.selectbox("Lote:", range(total_lotes), format_func=lambda x: f"Lote {x + 1}")
        st.caption(f"{len(st.session_state['m_list'])} activos · ordenados por volumen 24h")
        if st.button("🚀 ESCANEAR Y ACUMULAR", type="primary", use_container_width=True):
            ex = get_exchange(kind)
            subset = st.session_state["m_list"][batch_idx * int(lote_size):(batch_idx + 1) * int(lote_size)]
            prog = st.progress(0)
            for i, sym in enumerate(subset):
                prog.progress((i + 1) / len(subset), text=f"Midiendo {tf_lbl}: {sym}")
                try:
                    st.session_state["m_results"][(sym, tf)] = analizar(
                        ex, kind, sym, tf, solo_cerradas, st.session_state["m_vols"].get(sym, 0.0))
                    st.session_state["m_errors"].pop((sym, tf), None)
                except Exception as e:
                    st.session_state["m_errors"][(sym, tf)] = f"{sym} [{tf_lbl}]: {type(e).__name__}: {str(e)[:100]}"
                time.sleep(0.05)
            prog.empty()
            st.rerun()
    elif st.session_state["m_list"]:
        st.info("Cambiaste de mercado: sincronizá de nuevo.")
 
    if st.button("🗑️ Limpiar memoria"):
        st.session_state["m_results"], st.session_state["m_errors"] = {}, {}
        st.rerun()
 
res = [r for (s, t), r in st.session_state["m_results"].items() if t == tf]
errs = [m for (s, t), m in st.session_state["m_errors"].items() if t == tf]
 
if res:
    f1, f2, f3 = st.columns(3)
    min_qv = f1.number_input("Liquidez mínima (volumen 24h, millones de USDT)", 0.0, 1000.0, 1.0, 0.5,
                             help="Descarta las monedas con poco volumen: son fáciles de manipular y difíciles de vender.")
    umbral = f2.slider("Movimiento mínimo para recomendar (0-100)", 40, 90, 60)
    dir_sel = f3.radio("Dirección", ["Todas", "ALCISTA", "BAJISTA"], horizontal=True)
    rec_sel = st.multiselect("Recomendación", REC_OPCIONES, default=["LONG", "SHORT", "TARDÍA", "VIGILAR"])
 
    dfa = pd.DataFrame(res)
    btc = dfa[dfa["Activo"] == "BTC"]
    btc_cambio = float(btc["_cambio"].iloc[0]) if len(btc) else None
    dfa = aplicar_reco(dfa, min_qv, kind == "spot", umbral, btc_cambio)
 
    # --- Recomendada ---
    candidatas = dfa[dfa["_rec"].isin(["LONG", "SHORT"])]
    st.subheader("⭐ Cripto recomendada")
    if len(candidatas):
        top = candidatas.iloc[0]
        st.markdown(f"""<div class="pick-box"><div class="pick-title">{top['Activo']} — {top['Recomendación']}</div>
        Movimiento <b>{top['_score']}/100</b> · Dirección <b>{top['_dir']}</b> · Precio <b>{fmt_px(top['Precio'])}</b><br>
        <b>Por qué:</b> {top['_why']}.<br>
        <b>Referencia:</b> stop {top['Stop ref.']} (riesgo ≈ {top['Riesgo al stop %']}%) · objetivo 2R {top['Obj. ref. (2R)']}.
        </div>""", unsafe_allow_html=True)
        otras = candidatas.iloc[1:6]
        if len(otras):
            st.caption("Otras candidatas: " + " · ".join(f"{r['Activo']} ({r['_score']}, {r['_dir'].lower()})" for _, r in otras.iterrows()))
    else:
        mejor = dfa[~dfa["_rec"].isin(["EVITAR"])].sort_values("_score", ascending=False).head(1)
        if len(mejor):
            r = mejor.iloc[0]
            st.info(f"Ninguna cumple todas las condiciones para LONG o SHORT con estos filtros. La más activa para vigilar "
                    f"es **{r['Activo']}** (movimiento {r['_score']}/100, {r['_dir'].lower()}): {r['_why']}.")
        else:
            st.info("Ninguna cripto cumple los filtros de liquidez. Probá bajar la liquidez mínima.")
 
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Escaneadas (acumuladas)", len(dfa))
    m2.metric("En movimiento (≥ umbral)", int((dfa["_score"] >= umbral).sum()))
    m3.metric("LONG / SHORT", f"{int((dfa['_rec'] == 'LONG').sum())} / {int((dfa['_rec'] == 'SHORT').sum())}")
    m4.metric("BTC (cambio 24 h)" if btc_cambio is not None else "BTC", f"{btc_cambio:+.1f}%" if btc_cambio is not None else "sin escanear")
    if btc_cambio is not None and btc_cambio <= -3:
        st.warning("BTC está cayendo fuerte: los largos en altcoins tienen más riesgo de lo habitual.")
 
    show = dfa[dfa["_rec"].isin(rec_sel)]
    if dir_sel != "Todas":
        show = show[show["_dir"] == dir_sel]
    cols = ["Activo", "Recomendación", "_score", "_dir", "Cambio %", "RVOL", "Vol x", "ATR %", "Ruptura", "Compresión previa", "RSI",
            "Stop ref.", "Obj. ref. (2R)", "_why", "Sector", "Vol 24h (M)", "Precio"]
    show = show[cols].rename(columns={"_score": "Movimiento", "_dir": "Dirección", "_why": "Por qué"})
 
    def color_cells(val):
        s = str(val)
        if s.startswith("LONG TARD") or s.startswith("SHORT TARD") or s.startswith("VIGILAR") or s.startswith("MOVIMIENTO SIN"):
            return "background-color: #FFF9C4; color: #827717; font-weight: bold;"
        if s.startswith("LONG") or s == "ALCISTA":
            return "background-color: #C8E6C9; color: #1B5E20; font-weight: bold;"
        if s.startswith("SHORT") or s.startswith("BAJISTA"):
            return "background-color: #FFCDD2; color: #B71C1C; font-weight: bold;"
        if s.startswith("EVITAR"):
            return "background-color: #CFD8DC; color: #37474F;"
        if s.startswith("SIN MOV"):
            return "color: #9E9E9E;"
        return ""
 
    st.subheader(f"📋 Ranking de movimiento ({tf_lbl})")
    if show.empty:
        st.info("Nada cumple el filtro. Probá incluir más recomendaciones o bajar el movimiento mínimo.")
    else:
        st.dataframe(show.style.map(color_cells, subset=["Recomendación", "Dirección"]),
                     use_container_width=True, height=560, hide_index=True)
    st.caption("Movimiento (0-100) = volumen relativo (35) + expansión de volatilidad (25) + tamaño del cambio de precio (20) + "
               "ruptura reciente con volumen (hasta 20). Dirección = cambio, ruptura, medias, MACD y RSI. 'Cambio %' es de 24 horas "
               "(en 1 DIA, la última vela). TARDÍA = ya se movió mucho (cambio de más de 25%, o RSI extremo con más de 12%): suele ser tarde para entrar. "
               "Stop = 1,5 ATR; objetivo = 2R: son referencias, no una orden.")
else:
    st.info("👈 Elegí mercado y temporalidad, sincronizá KuCoin y escaneá un lote (el Lote 1 son los más líquidos).")
 
if errs:
    with st.expander(f"⚠️ {len(errs)} activos con error"):
        st.write("\n\n".join(errs))
 
