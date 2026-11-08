"""
SLY | LIQUIDACIONES (PRUEBA) — mapa de liquidaciones ESTIMADO por cripto y cercanía de los cúmulos.
 
Script independiente para probar la idea. No se conecta con tus otros tableros.
 
Requisitos:  pip install streamlit ccxt pandas numpy plotly
Ejecutar:    streamlit run sly_liquidaciones_prueba.py
 
IMPORTANTE: es una ESTIMACIÓN propia (no el dato de Coinglass). Se arma así:
  1) Se toman las velas de 1 hora y el interés abierto (OI) por hora del exchange.
  2) Cada aumento de OI se interpreta como posiciones nuevas abiertas en ese precio.
  3) Se reparten entre largos y cortos (60/40 según el color de la vela) y entre apalancamientos
     10x / 25x / 50x / 100x (40 / 30 / 20 / 10 %).
  4) Se calcula a qué precio se liquidaría cada grupo y se descartan los que ya fueron liquidados
     (el precio pasó por su nivel después de abrir).
  5) Se escala el total al OI actual y se agrupa por nivel de precio.
Los supuestos de reparto son una aproximación: sirve como contexto de dónde puede haber liquidez,
no como dato exacto de posiciones ni como señal de entrada.
"""
import time
 
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import ccxt
 
st.set_page_config(layout="wide", page_title="SLY | LIQUIDACIONES (PRUEBA)")
st.markdown("""
<style>
    .stApp { background-color: #FFFFFF; color: #1C1E21; }
    .stDataFrame { font-size: 11px; font-family: 'Roboto Mono', monospace; }
    h1 { color: #B71C1C; font-weight: 800; border-bottom: 3px solid #B71C1C; }
    .stProgress > div > div > div > div { background-color: #B71C1C; }
</style>
""", unsafe_allow_html=True)
 
for _k, _v in {"l_results": {}, "l_errors": {}, "l_list": [], "l_vols": {}, "l_ex": None}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v
 
EXCHANGES = {"Binance Futuros (USDT-M)": "binanceusdm", "Bybit (perpetuos USDT)": "bybit"}
STABLES = {"USDC", "USDT", "DAI", "TUSD", "FDUSD", "USDE", "PYUSD", "USDD", "BUSD", "PAX"}
LEVS = [10, 25, 50, 100]
PESOS = [0.40, 0.30, 0.20, 0.10]
MMR = 0.005              # margen de mantenimiento aproximado (0,5 %)
RANGO, PASO = 0.15, 0.0025   # se mapea ±15 % alrededor del precio, en pasos de 0,25 %
BARS = 500               # 500 velas de 1 h ≈ 20 días (Binance entrega ~30 días de OI)
HOUR_MS = 3_600_000
 
 
def fmt_px(x):
    return f"{x:.6g}"
 
 
# ─────────────────────────────────────────────
# DATOS
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange(ex_id):
    return getattr(ccxt, ex_id)({"enableRateLimit": True})
 
 
def fetch_symbols(ex_id):
    """Perpetuos USDT ordenados por volumen 24h (el Lote 1 son los más líquidos)."""
    ex = get_exchange(ex_id)
    markets = ex.load_markets()
    filas = []
    for sym, m in markets.items():
        if m.get("quote") != "USDT" or not m.get("active", True) or not (m.get("swap") and m.get("linear")):
            continue
        base = m.get("base", "")
        if base in STABLES or base.endswith(("3L", "3S", "5L", "5S")):
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
 
 
def fetch_velas_oi(ex, ex_id, sym):
    """Velas de 1 h y OI por hora (en USD) del mismo período."""
    ohlcv = ex.fetch_ohlcv(sym, timeframe="1h", limit=BARS)
    df = pd.DataFrame(ohlcv, columns=["time", "open", "high", "low", "close", "vol"])
    lim = 200 if ex_id == "bybit" else 500
    hist = ex.fetch_open_interest_history(sym, timeframe="1h", limit=lim)
    filas = []
    for h in hist:
        val = h.get("openInterestValue")
        if val is None and h.get("openInterestAmount") is not None:
            val = None   # se completa más abajo con el precio
        filas.append({"time": h.get("timestamp"), "amt": h.get("openInterestAmount"), "val": val})
    oi = pd.DataFrame(filas).dropna(subset=["time"])
    if oi.empty:
        raise ValueError("El exchange no devolvió interés abierto para este símbolo")
    oi["time"] = oi["time"].astype("int64")
    df = df.drop_duplicates("time").sort_values("time").reset_index(drop=True)
    if oi["val"].isna().all():            # sin valor en USD: cantidad × precio de cierre de esa hora
        mm = pd.merge_asof(oi.sort_values("time"), df[["time", "close"]], on="time", direction="nearest")
        oi["oi_usd"] = mm["amt"].to_numpy() * mm["close"].to_numpy()
    else:
        oi["oi_usd"] = oi["val"].astype(float)
    return df, oi[["time", "oi_usd"]].sort_values("time").reset_index(drop=True)
 
 
# ─────────────────────────────────────────────
# MOTOR: MAPA DE LIQUIDACIONES ESTIMADO
# ─────────────────────────────────────────────
def estimar_mapa(df, oi, rango=RANGO, paso=PASO):
    """
    df: velas 1 h (time, open, high, low, close). oi: (time, oi_usd).
    Devuelve centros de precio y USD estimados de liquidación de largos (debajo del precio) y de cortos (arriba).
    """
    m = pd.merge_asof(df.sort_values("time"), oi.sort_values("time"), on="time", direction="nearest",
                      tolerance=HOUR_MS).dropna(subset=["oi_usd"]).reset_index(drop=True)
    if len(m) < 48:
        raise ValueError(f"Datos insuficientes: {len(m)} horas con velas e interés abierto (se necesitan ≥48)")
    o, h, l, c = (m[k].astype(float).to_numpy() for k in ("open", "high", "low", "close"))
    oi_usd = m["oi_usd"].astype(float).to_numpy()
    nuevo = np.clip(np.diff(oi_usd, prepend=oi_usd[0]), 0, None)           # posiciones nuevas por hora (USD)
    if nuevo.sum() <= 0:
        raise ValueError("El interés abierto no aumentó en el período: no hay posiciones nuevas que estimar")
    tip = (h + l + c) / 3
    share_largo = np.where(c > o, 0.6, 0.4)
    n = len(m)
    # mínimo / máximo de lo que pasó DESPUÉS de cada hora (para saber si la posición ya fue liquidada)
    fmin = np.full(n, np.inf)
    fmax = np.full(n, -np.inf)
    for t in range(n - 2, -1, -1):
        fmin[t] = min(l[t + 1], fmin[t + 1])
        fmax[t] = max(h[t + 1], fmax[t + 1])
    px_l, w_l, px_s, w_s = [], [], [], []
    for lev, peso in zip(LEVS, PESOS):
        Lp = tip * (1 - 1 / lev + MMR)
        Sp = tip * (1 + 1 / lev - MMR)
        vivo_l = fmin > Lp
        vivo_s = fmax < Sp
        px_l.append(Lp[vivo_l]); w_l.append((nuevo * peso * share_largo)[vivo_l])
        px_s.append(Sp[vivo_s]); w_s.append((nuevo * peso * (1 - share_largo))[vivo_s])
    px_l, w_l, px_s, w_s = (np.concatenate(x) for x in (px_l, w_l, px_s, w_s))
    total = w_l.sum() + w_s.sum()
    if total <= 0:
        raise ValueError("Todas las posiciones estimadas ya habrían sido liquidadas")
    esc = oi_usd[-1] / total                                              # escala al OI actual
    price = float(c[-1])
    edges = price * (1 + np.arange(-rango, rango + paso / 2, paso))
    centros = (edges[:-1] + edges[1:]) / 2
    largos, _ = np.histogram(px_l, bins=edges, weights=w_l * esc)
    cortos, _ = np.histogram(px_s, bins=edges, weights=w_s * esc)
    debajo = centros < price
    return {"price": price, "oi_now": float(oi_usd[-1]), "centros": centros,
            "largos": np.where(debajo, largos, 0.0), "cortos": np.where(~debajo, cortos, 0.0), "horas": n}
 
 
def metricas(mapa, sig=0.5, cerca_pct=5.0):
    """Cúmulo significativo más cercano en cada lado (≥ 50 % del máximo de ese lado) y combustible a ≤ cerca_pct."""
    price, centros = mapa["price"], mapa["centros"]
    pct = (centros / price - 1) * 100
    k = np.array([1, 1, 1]) / 3
    out = {}
    for lado, arr, sentido in (("arr", mapa["cortos"], 1), ("abj", mapa["largos"], -1)):
        s = np.convolve(arr, k, mode="same")
        if s.max() <= 0:
            out[lado] = dict(dist=np.nan, usd=0.0, px=np.nan, mayor_dist=np.nan, mayor_usd=0.0, cerca=0.0)
            continue
        idx = np.flatnonzero(s >= sig * s.max())
        cercano = idx[np.argmin(np.abs(pct[idx]))]
        mayor = int(np.argmax(s))
        dentro = (pct * sentido > 0) & (np.abs(pct) <= cerca_pct)
        out[lado] = dict(dist=float(abs(pct[cercano])), usd=float(s[cercano]), px=float(centros[cercano]),
                         mayor_dist=float(abs(pct[mayor])), mayor_usd=float(s[mayor]), cerca=float(arr[dentro].sum()))
    return out
 
 
def etiqueta_lado(cerca_arr, cerca_abj, razon=1.5):
    if cerca_arr <= 0 and cerca_abj <= 0:
        return "sin datos"
    if cerca_arr > razon * cerca_abj:
        return "Más combustible ARRIBA (cortos)"
    if cerca_abj > razon * cerca_arr:
        return "Más combustible ABAJO (largos)"
    return "Equilibrado"
 
 
def analizar(ex, ex_id, sym, qv):
    df, oi = fetch_velas_oi(ex, ex_id, sym)
    mapa = estimar_mapa(df, oi)
    mt = metricas(mapa)
    a, b = mt["arr"], mt["abj"]
    return {"Activo": sym.split(":")[0].replace("/USDT", ""), "Precio": mapa["price"], "OI (M USD)": round(mapa["oi_now"] / 1e6, 2),
            "Cúmulo ↑ precio": fmt_px(a["px"]) if np.isfinite(a["px"]) else "-", "Cúmulo ↑ %": round(a["dist"], 2),
            "Cúmulo ↑ (M USD)": round(a["usd"] / 1e6, 3), "Cúmulo ↓ precio": fmt_px(b["px"]) if np.isfinite(b["px"]) else "-",
            "Cúmulo ↓ %": round(b["dist"], 2), "Cúmulo ↓ (M USD)": round(b["usd"] / 1e6, 3),
            "Cortos ≤5% (M USD)": round(a["cerca"] / 1e6, 3), "Largos ≤5% (M USD)": round(b["cerca"] / 1e6, 3),
            "Lectura": etiqueta_lado(a["cerca"], b["cerca"]), "Vol 24h (M)": round(qv / 1e6, 1),
            "_mapa": mapa, "_min": float(np.nanmin([a["dist"], b["dist"]])), "_sym": sym}
 
 
def figura_mapa(r):
    mp = r["_mapa"]
    x, price = mp["centros"], mp["price"]
    c_cortos = np.cumsum(mp["cortos"])                       # de cerca del precio hacia arriba
    c_largos = np.cumsum(mp["largos"][::-1])[::-1]           # de cerca del precio hacia abajo
    fig = go.Figure()
    fig.add_trace(go.Bar(x=x, y=mp["largos"] / 1e6, name="Liquidación de largos (estimada)", marker_color="#E53935"))
    fig.add_trace(go.Bar(x=x, y=mp["cortos"] / 1e6, name="Liquidación de cortos (estimada)", marker_color="#43A047"))
    fig.add_trace(go.Scatter(x=x[x < price], y=c_largos[x < price] / 1e6, mode="lines", name="Acumulado largos",
                             line=dict(color="#B71C1C", width=2), yaxis="y2"))
    fig.add_trace(go.Scatter(x=x[x >= price], y=c_cortos[x >= price] / 1e6, mode="lines", name="Acumulado cortos",
                             line=dict(color="#1B5E20", width=2), yaxis="y2"))
    fig.add_vline(x=price, line_dash="dash", line_color="#1565C0", annotation_text=f"Precio {fmt_px(price)}")
    fig.update_layout(height=470, barmode="overlay", margin=dict(l=0, r=0, t=30, b=0), plot_bgcolor="white",
                      yaxis=dict(title="USD estimados por nivel (M)"),
                      yaxis2=dict(title="Acumulado (M)", overlaying="y", side="right", showgrid=False),
                      xaxis=dict(title="Precio"), legend=dict(orientation="h", y=-0.2))
    return fig
 
 
# ═════════════════════════════════════════════
# INTERFAZ
# ═════════════════════════════════════════════
st.title("🧨 SLY | LIQUIDACIONES (PRUEBA)")
st.caption("Mapa de liquidaciones ESTIMADO por cripto y qué tan cerca están los cúmulos. Es una aproximación propia con "
           "interés abierto y precios, no el dato de Coinglass ni posiciones reales.")
 
with st.sidebar:
    st.header("⚙️ Configuración")
    ex_lbl = st.selectbox("Exchange:", list(EXCHANGES.keys()))
    ex_id = EXCHANGES[ex_lbl]
    if st.button("📡 Sincronizar mercado"):
        try:
            lst, vols = fetch_symbols(ex_id)
            st.session_state["l_list"], st.session_state["l_vols"], st.session_state["l_ex"] = lst, vols, ex_id
            if not lst:
                st.error("El exchange respondió pero no devolvió perpetuos USDT.")
            else:
                st.rerun()
        except Exception as e:
            st.error(f"No se pudo leer el mercado: {type(e).__name__}: {str(e)[:400]}")
    if st.button("🩺 Diagnóstico (probar BTC)"):
        ex = get_exchange(ex_id)
        pasos = [("Cargar mercados", lambda: len(ex.load_markets())),
                 ("Velas 1h BTC", lambda: len(ex.fetch_ohlcv("BTC/USDT:USDT", timeframe="1h", limit=5))),
                 ("Interés abierto BTC", lambda: len(ex.fetch_open_interest_history("BTC/USDT:USDT", timeframe="1h", limit=5))),
                 ("Análisis completo BTC", lambda: analizar(ex, ex_id, "BTC/USDT:USDT", 0.0)["Lectura"])]
        for nombre, fn in pasos:
            try:
                st.success(f"✅ {nombre}: {fn()}")
            except Exception as e:
                st.error(f"❌ {nombre}: {type(e).__name__}: {str(e)[:500]}")
                break
    if st.session_state["l_list"] and st.session_state["l_ex"] == ex_id:
        st.subheader("Lotes (más líquidos primero)")
        lote_size = st.number_input("Tamaño de lote:", 5, 50, 15)
        total_lotes = (len(st.session_state["l_list"]) - 1) // int(lote_size) + 1
        batch_idx = st.selectbox("Lote:", range(total_lotes), format_func=lambda x: f"Lote {x + 1}")
        st.caption(f"{len(st.session_state['l_list'])} perpetuos · 2 pedidos por activo, así que los lotes son más lentos")
        if st.button("🚀 ESCANEAR Y ACUMULAR", type="primary", use_container_width=True):
            ex = get_exchange(ex_id)
            subset = st.session_state["l_list"][batch_idx * int(lote_size):(batch_idx + 1) * int(lote_size)]
            prog = st.progress(0)
            for i, sym in enumerate(subset):
                prog.progress((i + 1) / len(subset), text=f"Estimando {sym}")
                try:
                    st.session_state["l_results"][(sym, ex_id)] = analizar(ex, ex_id, sym, st.session_state["l_vols"].get(sym, 0.0))
                    st.session_state["l_errors"].pop((sym, ex_id), None)
                except Exception as e:
                    st.session_state["l_errors"][(sym, ex_id)] = f"{sym}: {type(e).__name__}: {str(e)[:300]}"
                time.sleep(0.05)
            prog.empty()
            st.rerun()
    elif st.session_state["l_list"]:
        st.info("Cambiaste de exchange: sincronizá de nuevo.")
    if st.button("🗑️ Limpiar memoria"):
        st.session_state["l_results"], st.session_state["l_errors"] = {}, {}
        st.rerun()
 
res = [r for (s, e), r in st.session_state["l_results"].items() if e == ex_id]
errs = [m for (s, e), m in st.session_state["l_errors"].items() if e == ex_id]
 
if res:
    f1, f2, f3 = st.columns(3)
    max_d = f1.slider("Cúmulo a menos de (%)", 0.5, 15.0, 5.0, 0.5)
    min_vol = f2.number_input("Volumen 24h mínimo (M USDT)", 0.0, 1000.0, 5.0, 1.0)
    lado = f3.radio("Lectura", ["Todas", "ARRIBA (cortos)", "ABAJO (largos)"], horizontal=True)
    dfa = pd.DataFrame(res)
    show = dfa[(dfa["_min"] <= max_d) & (dfa["Vol 24h (M)"] >= min_vol)]
    if lado != "Todas":
        show = show[show["Lectura"].str.contains("ARRIBA" if lado.startswith("ARRIBA") else "ABAJO")]
    show = show.sort_values("_min")
    cols = ["Activo", "Precio", "Lectura", "Cúmulo ↑ precio", "Cúmulo ↑ %", "Cúmulo ↑ (M USD)", "Cúmulo ↓ precio", "Cúmulo ↓ %",
            "Cúmulo ↓ (M USD)", "Cortos ≤5% (M USD)", "Largos ≤5% (M USD)", "OI (M USD)", "Vol 24h (M)"]
    m1, m2 = st.columns(2)
    m1.metric("Estimadas (acumuladas)", len(dfa))
    m2.metric(f"Con un cúmulo a menos de {max_d:.1f}%", len(show))
    st.subheader("📋 Cercanía de los cúmulos de liquidación")
    if show.empty:
        st.info("Ninguna cumple el filtro. Probá subir la distancia o bajar el volumen mínimo.")
    else:
        st.dataframe(show[cols], use_container_width=True, height=420, hide_index=True)
        pick = st.selectbox("Ver el mapa de:", list(show["Activo"]))
        st.plotly_chart(figura_mapa(dfa[dfa["Activo"] == pick].iloc[0]), use_container_width=True)
    st.caption("Cúmulo ↑ / ↓: el nivel más cercano al precio con al menos la mitad del tamaño del mayor de ese lado, y su distancia en %. "
               "'≤5%' suma el combustible estimado dentro de ±5% del precio. Supuestos: largos/cortos 60/40 según el color de la vela y "
               "apalancamientos 10x/25x/50x/100x con pesos 40/30/20/10. Es una estimación, no un dato real de posiciones.")
else:
    st.info("👈 Sincronizá el mercado y escaneá un lote (el Lote 1 son los más líquidos).")
if errs:
    with st.expander(f"⚠️ {len(errs)} activos con error"):
        st.write("\n\n".join(errs))
