"""
SLY | PATRÓN BASE → RUPTURA — escáner e historial de acierto, por lotes (KuCoin / Bybit / OKX spot).

Requisitos:  pip install streamlit ccxt pandas numpy plotly
Ejecutar:    streamlit run sly_patron_base_ruptura.py

Qué hace
  1) Baja las velas SEMANALES de cada cripto (por lotes, acumulando) y las guarda en un archivo local.
  2) Define el patrón que vimos en QNT, INIT, ONE, MAGIC, ICNT, JCT, AIN, EVAA, ELSA, HANA:
       BASE  = caída fuerte desde el máximo de 52 semanas + volatilidad semanal baja + todavía no despegó.
       SEÑAL = la semana siguiente a una BASE, con volumen que se dispara (RVOL) y una vela verde fuerte.
  3) Revisa TODO el historial de TODAS las monedas cargadas: cada vez que apareció una SEÑAL, mide qué pasó
     en las semanas siguientes (máxima suba, retorno a N semanas, peor caída) y lo compara contra el azar
     (todas las semanas de todas las monedas). Así se ve si el patrón tiene ventaja o no.
  4) Muestra las candidatas de hoy (en base / señal nueva), la lista de eventos y un gráfico por moneda.

Límites: no usa interés abierto ni liquidaciones. Es estadística sobre un universo chico (el que cargues);
las semanas consecutivas no son independientes; las monedas que desaparecieron del exchange no están
(sesgo de supervivencia). La última vela semanal (abierta) se excluye por defecto. No es una recomendación.
"""
import os
import pickle
import time

import ccxt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(layout="wide", page_title="SLY | PATRÓN BASE → RUPTURA")
st.markdown("""
<style>
    .stApp { background-color: #FFFFFF; color: #1C1E21; }
    .stDataFrame { font-size: 11px; font-family: 'Roboto Mono', monospace; }
    h1 { color: #4A148C; font-weight: 800; border-bottom: 3px solid #4A148C; }
    .stProgress > div > div > div > div { background-color: #4A148C; }
</style>
""", unsafe_allow_html=True)

CACHE_FILE = "sly_patron_cache.pkl"
EXCHANGES = {"KuCoin (spot)": "kucoin", "Bybit (spot)": "bybit", "OKX (spot)": "okx"}
STABLES = {"USDC", "USDT", "DAI", "TUSD", "FDUSD", "USDE", "PYUSD", "USDD", "BUSD", "PAX", "EUR", "EURT", "USD1"}
BAD_SUFFIX = ("3L", "3S", "5L", "5S", "UP", "DOWN", "BULL", "BEAR")


def cargar_cache():
    try:
        with open(CACHE_FILE, "rb") as f:
            return pickle.load(f)
    except Exception:
        return {}


def guardar_cache(data):
    try:
        with open(CACHE_FILE, "wb") as f:
            pickle.dump(data, f)
    except Exception:
        pass


if "pb_data" not in st.session_state:
    st.session_state["pb_data"] = cargar_cache()      # {(ex_id, sym): DataFrame semanal}
if "pb_errors" not in st.session_state:
    st.session_state["pb_errors"] = {}
if "pb_list" not in st.session_state:
    st.session_state["pb_list"] = None


# ─────────────────────────────────────────────
# DATOS
# ─────────────────────────────────────────────
@st.cache_resource
def get_ex(ex_id):
    return getattr(ccxt, ex_id)({"enableRateLimit": True})


def fetch_symbols(ex_id):
    """Pares spot /USDT ordenados por volumen 24 h (el Lote 1 es el más líquido)."""
    ex = get_ex(ex_id)
    markets = ex.load_markets()
    filas = []
    for s, m in markets.items():
        if m.get("quote") != "USDT" or not m.get("spot") or not m.get("active", True) or ":" in s:
            continue
        base = m.get("base", "")
        if base in STABLES or base.upper().endswith(BAD_SUFFIX):
            continue
        filas.append([s, 0.0])
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
    return [f[0] for f in filas]


def fetch_semanal(ex, ex_id, sym):
    raw = ex.fetch_ohlcv(sym, timeframe="1w", limit=1500 if ex_id == "kucoin" else 1000)
    if not raw:
        raise ValueError("Sin velas semanales")
    d = pd.DataFrame(raw, columns=["time", "open", "high", "low", "close", "vol"])
    d["time"] = pd.to_datetime(d["time"], unit="ms")
    d = d.drop_duplicates("time").sort_values("time").reset_index(drop=True)
    d = d.dropna(subset=["open", "high", "low", "close"])
    d = d[(d["close"] > 0) & (d["low"] > 0)].reset_index(drop=True)
    d["vol"] = d["vol"].fillna(0.0)
    return d


# ─────────────────────────────────────────────
# MOTOR: BASE, SEÑAL Y RESULTADOS POSTERIORES
# ─────────────────────────────────────────────
def rsi_wilder(close, n=14):
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def features(df, p):
    """
    df: velas semanales (time, open, high, low, close, vol). p: parámetros.
    Todo lo que decide BASE/SEÑAL usa solo datos hasta esa semana. Los fwd_* miran hacia adelante y
    SOLO sirven para medir resultados pasados.
    """
    d = df.reset_index(drop=True).copy()
    H, N = int(p["H"]), int(p["N"])
    d["hi52"] = d["high"].rolling(52, min_periods=26).max()
    d["dd"] = 1 - d["close"] / d["hi52"]                                   # caída vs máximo de 52 semanas
    d["atr"] = ((d["high"] - d["low"]) / d["close"]).rolling(N).mean()     # volatilidad semanal media
    d["ret1"] = d["close"] / d["close"].shift(1) - 1
    d["ret4p"] = d["close"] / d["close"].shift(4) - 1
    d["rvol"] = d["vol"] / d["vol"].shift(1).rolling(10).mean().replace(0, np.nan)
    d["rsi"] = rsi_wilder(d["close"])
    d["valid"] = np.arange(len(d)) >= int(p["min_hist"])
    base = (d["dd"] >= p["dd"]) & (d["atr"] <= p["atr"]) & (d["ret4p"] <= p["ret4p"]) & d["valid"]
    d["base"] = base.fillna(False).astype(bool)
    prev = d["base"].shift(1).fillna(False).astype(bool)
    raw = prev & (d["rvol"] >= p["rvol"]) & (d["ret1"] >= p["ret1"]) & d["valid"]
    raw = raw.fillna(False).to_numpy()
    sig = np.zeros(len(d), dtype=bool)
    last = -10 ** 9
    for i in np.flatnonzero(raw):                      # un solo evento por episodio (separados ≥ gap semanas)
        if i - last >= int(p["gap"]):
            sig[i] = True
            last = i
    d["sig"] = sig
    fh = pd.concat([d["high"].shift(-k) for k in range(1, H + 1)], axis=1).max(axis=1, skipna=False)
    fl = pd.concat([d["low"].shift(-k) for k in range(1, H + 1)], axis=1).min(axis=1, skipna=False)
    d["fwd_gain"] = fh / d["close"] - 1                # máxima suba posible dentro de H semanas
    d["fwd_dd"] = fl / d["close"] - 1                  # peor caída dentro de H semanas
    d["fwd_ret"] = d["close"].shift(-H) / d["close"] - 1
    return d


def semanas_en_base(base_arr):
    n = 0
    for b in base_arr[::-1]:
        if not b:
            break
        n += 1
    return n


def procesar(data, p, solo_cerradas, ex_id):
    """Devuelve (todas las semanas concatenadas, tabla de candidatas de hoy)."""
    frames, cands = [], []
    for (e, sym), df in data.items():
        if e != ex_id:
            continue
        d0 = df.iloc[:-1] if (solo_cerradas and len(df) > 1) else df
        if len(d0) < int(p["min_hist"]) + 2:
            continue
        d = features(d0, p)
        d["sym"] = sym
        frames.append(d)
        u = d.iloc[-1]
        sig_idx = np.flatnonzero(d["sig"].to_numpy())
        desde = (len(d) - 1 - sig_idx[-1]) if len(sig_idx) else None
        if u["sig"]:
            estado = "SEÑAL NUEVA 🚀"
        elif desde is not None and desde <= int(p["H"]):
            estado = f"EN SEGUIMIENTO (señal hace {desde} sem)"
        elif u["base"]:
            estado = "EN BASE 🟣"
        else:
            continue
        cands.append({"Activo": sym.replace("/USDT", ""), "Estado": estado, "Precio": float(u["close"]),
                      "Caída vs máx 52s %": round(float(u["dd"]) * 100, 1) if pd.notna(u["dd"]) else None,
                      "Volatilidad sem. %": round(float(u["atr"]) * 100, 1) if pd.notna(u["atr"]) else None,
                      "RVOL última sem": round(float(u["rvol"]), 2) if pd.notna(u["rvol"]) else None,
                      "Var. última sem %": round(float(u["ret1"]) * 100, 1) if pd.notna(u["ret1"]) else None,
                      "RSI": round(float(u["rsi"]), 1) if pd.notna(u["rsi"]) else None,
                      "Semanas en base": semanas_en_base(d["base"].to_numpy()),
                      "Historial (sem)": len(d)})
    allf = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return allf, pd.DataFrame(cands)


def resumen(allf, p):
    """Compara la señal contra la base sola y contra el azar (todas las semanas)."""
    if allf.empty:
        return pd.DataFrame()
    ok = allf["fwd_gain"].notna() & allf["valid"]
    filas = []
    for nombre, mask in (("Todas las semanas (azar)", ok),
                         ("Solo estar en BASE", ok & allf["base"]),
                         ("SEÑAL (base + volumen + vela verde)", ok & allf["sig"])):
        g = allf[mask]
        n = len(g)
        if n == 0:
            filas.append({"Grupo": nombre, "Casos": 0})
            continue
        filas.append({"Grupo": nombre, "Casos": n,
                      f"% que sube ≥{p['gain']:.0f}% en {p['H']} sem": round((g["fwd_gain"] >= p["gain"] / 100).mean() * 100, 1),
                      "Mediana máx. suba %": round(g["fwd_gain"].median() * 100, 1),
                      f"Mediana retorno a {p['H']} sem %": round(g["fwd_ret"].median() * 100, 1),
                      f"% que cierra en positivo a {p['H']} sem": round((g["fwd_ret"] > 0).mean() * 100, 1),
                      "Mediana peor caída %": round(g["fwd_dd"].median() * 100, 1)})
    return pd.DataFrame(filas)


def figura_moneda(d, sym):
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=d["time"], open=d["open"], high=d["high"], low=d["low"], close=d["close"], name=sym,
                                 increasing_line_color="#2E7D32", decreasing_line_color="#C62828"))
    b = d[d["base"]]
    if len(b):
        fig.add_trace(go.Scatter(x=b["time"], y=b["low"] * 0.9, mode="markers", name="En base",
                                 marker=dict(color="#7E57C2", size=6, symbol="circle")))
    s = d[d["sig"]]
    if len(s):
        fig.add_trace(go.Scatter(x=s["time"], y=s["low"] * 0.8, mode="markers", name="Señal",
                                 marker=dict(color="#F9A825", size=13, symbol="triangle-up", line=dict(color="#000", width=1))))
    fig.update_layout(height=520, margin=dict(l=0, r=0, t=30, b=0), plot_bgcolor="white", xaxis_rangeslider_visible=False,
                      yaxis=dict(type="log", title="Precio (escala log)"), title=f"{sym}: semanal · violeta = en base · triángulo = señal",
                      legend=dict(orientation="h", y=-0.1))
    return fig


# ═════════════════════════════════════════════
# INTERFAZ
# ═════════════════════════════════════════════
st.title("🔎 SLY | PATRÓN BASE → RUPTURA")
st.caption("Busca criptos en base (caída fuerte + volatilidad baja) y mide, con el historial de las monedas que cargues, "
           "qué tan seguido el volumen que se dispara terminó en una suba. Estadística, no recomendación.")

with st.sidebar:
    st.header("⚙️ Datos")
    ex_lbl = st.selectbox("Exchange:", list(EXCHANGES.keys()))
    ex_id = EXCHANGES[ex_lbl]
    if st.button("📡 Sincronizar mercado"):
        try:
            st.session_state["pb_list"] = (ex_id, fetch_symbols(ex_id))
        except Exception as e:
            st.error(f"No se pudo leer el mercado: {type(e).__name__}: {str(e)[:300]}")
    lst = st.session_state["pb_list"]
    if lst and lst[0] == ex_id:
        symbols = lst[1]
        lote_size = st.number_input("Tamaño de lote:", 10, 100, 40)
        total_lotes = (len(symbols) - 1) // int(lote_size) + 1
        batch_idx = st.selectbox("Lote (más líquidos primero):", range(total_lotes), format_func=lambda x: f"Lote {x + 1}")
        st.caption(f"{len(symbols)} pares · 1 pedido por moneda")
        if st.button("🚀 DESCARGAR Y ACUMULAR", type="primary", use_container_width=True):
            ex = get_ex(ex_id)
            subset = symbols[batch_idx * int(lote_size):(batch_idx + 1) * int(lote_size)]
            prog = st.progress(0)
            for i, sym in enumerate(subset):
                prog.progress((i + 1) / len(subset), text=f"Descargando {sym}")
                try:
                    st.session_state["pb_data"][(ex_id, sym)] = fetch_semanal(ex, ex_id, sym)
                    st.session_state["pb_errors"].pop((ex_id, sym), None)
                except Exception as e:
                    st.session_state["pb_errors"][(ex_id, sym)] = f"{sym}: {type(e).__name__}: {str(e)[:200]}"
                time.sleep(0.05)
            prog.empty()
            guardar_cache(st.session_state["pb_data"])
            st.rerun()
    elif lst:
        st.info("Cambiaste de exchange: sincronizá de nuevo.")
    if st.button("🗑️ Limpiar memoria y archivo"):
        st.session_state["pb_data"], st.session_state["pb_errors"] = {}, {}
        guardar_cache({})
        st.rerun()

    st.header("🎛️ Definición del patrón")
    solo_cerradas = st.checkbox("Solo velas semanales cerradas", value=True)
    dd = st.slider("Caída mínima vs máximo de 52 sem (%)", 30, 95, 70, 5)
    N = st.slider("Semanas para medir la volatilidad", 4, 16, 8)
    atr = st.slider("Volatilidad semanal máxima (%)", 3, 40, 15)
    ret4p = st.slider("Suba máxima de las últimas 4 sem para estar 'en base' (%)", 0, 100, 25, 5)
    rvol = st.slider("Volumen de la semana ≥ X veces el promedio de 10 sem", 1.5, 15.0, 3.0, 0.5)
    ret1 = st.slider("Vela de disparo: suba semanal mínima (%)", 0, 100, 10, 5)
    st.header("📏 Medición")
    H = st.selectbox("Horizonte (semanas)", [2, 4, 8, 12], index=1)
    gain = st.slider("Éxito = suba máxima ≥ (%)", 10, 100, 20, 5)
    gap = st.slider("Separación mínima entre señales de una moneda (sem)", 2, 26, 8)
    min_hist = st.slider("Historial mínimo de la moneda (sem)", 26, 104, 52)

P = {"dd": dd / 100, "N": N, "atr": atr / 100, "ret4p": ret4p / 100, "rvol": rvol, "ret1": ret1 / 100,
     "H": H, "gain": gain, "gap": gap, "min_hist": min_hist}

datos = {k: v for k, v in st.session_state["pb_data"].items() if k[0] == ex_id}
if not datos:
    st.info("👈 Sincronizá el mercado y descargá un lote (el Lote 1 son los más líquidos). Podés acumular varios lotes: "
            "mientras más monedas, más confiable la estadística. Los datos se guardan en un archivo local.")
    st.stop()

allf, cands = procesar(st.session_state["pb_data"], P, solo_cerradas, ex_id)
if allf.empty:
    st.warning("Ninguna moneda cargada tiene historial suficiente con el mínimo elegido.")
    st.stop()

n_sig = int(allf[allf["valid"]]["sig"].sum())
m1, m2, m3, m4 = st.columns(4)
m1.metric("Monedas analizadas", allf["sym"].nunique())
m2.metric("Semanas-moneda", f"{int(allf['valid'].sum()):,}")
m3.metric("Señales históricas", n_sig)
m4.metric("Candidatas hoy", len(cands))

tab_est, tab_hoy, tab_ev, tab_graf = st.tabs(["📊 ¿Sirve el patrón?", "🎯 Candidatas hoy", "📋 Eventos históricos", "📈 Gráfico por moneda"])

with tab_est:
    rs = resumen(allf, P)
    st.dataframe(rs, use_container_width=True, hide_index=True)
    col_ok = f"% que sube ≥{P['gain']:.0f}% en {P['H']} sem"
    if col_ok in rs.columns and len(rs) == 3 and rs.loc[2, "Casos"] and rs.loc[0, col_ok]:
        base_pct, sig_pct = rs.loc[0, col_ok], rs.loc[2, col_ok]
        lift = sig_pct / base_pct if base_pct else np.nan
        st.metric("Ventaja de la señal sobre el azar", f"x{lift:.2f}", f"{sig_pct:.1f}% vs {base_pct:.1f}%")
        if rs.loc[2, "Casos"] < 30:
            st.warning(f"Solo {int(rs.loc[2, 'Casos'])} señales: muy pocas para concluir. Cargá más lotes o aflojá los parámetros.")
        st.caption("Si 'ventaja' es cercana a x1, el patrón no mejora al azar. Si 'cierra en positivo' es bajo aunque la máxima suba sea alta, "
                   "la suba suele devolverse (tipo pump & dump): mirá también la mediana de retorno y la peor caída.")
    ev_h = allf[allf["sig"] & allf["fwd_gain"].notna() & allf["valid"]]
    if len(ev_h):
        fig = go.Figure(go.Histogram(x=ev_h["fwd_ret"] * 100, nbinsx=30, marker_color="#7E57C2"))
        fig.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0), plot_bgcolor="white",
                          title=f"Retorno a {P['H']} semanas desde la vela de señal (%)", xaxis_title="%", yaxis_title="Casos")
        st.plotly_chart(fig, use_container_width=True)

with tab_hoy:
    if cands.empty:
        st.info("Hoy ninguna moneda cargada cumple la base ni tiene señal reciente con estos parámetros.")
    else:
        cands["_o"] = cands["Estado"].map(lambda s: 0 if s.startswith("SEÑAL") else (1 if s.startswith("EN SEG") else 2))
        cands = cands.sort_values(["_o", "Semanas en base"], ascending=[True, False]).drop(columns="_o")
        st.dataframe(cands, use_container_width=True, hide_index=True, height=480)
        st.caption("EN BASE = caída fuerte + volatilidad baja y todavía sin despegar. SEÑAL NUEVA = la última semana cerrada disparó volumen y subió. "
                   "Son candidatas para vigilar; no hay garantía de ruptura.")

with tab_ev:
    ev = allf[allf["sig"] & allf["valid"]].copy()
    if ev.empty:
        st.info("Sin señales históricas con estos parámetros.")
    else:
        ev["Fecha"] = ev["time"].dt.strftime("%d/%m/%Y")
        ev["Resultado"] = np.where(ev["fwd_gain"].isna(), "en curso",
                                   np.where(ev["fwd_gain"] >= P["gain"] / 100, "✅ éxito", "❌ no llegó"))
        t = pd.DataFrame({"Activo": ev["sym"].str.replace("/USDT", "", regex=False), "Fecha": ev["Fecha"], "Precio": ev["close"],
                          "Caída vs máx 52s %": (ev["dd"] * 100).round(1), "RVOL": ev["rvol"].round(1),
                          "Vela de señal %": (ev["ret1"] * 100).round(1), "Máx. suba %": (ev["fwd_gain"] * 100).round(1),
                          f"Retorno {P['H']} sem %": (ev["fwd_ret"] * 100).round(1), "Peor caída %": (ev["fwd_dd"] * 100).round(1),
                          "Resultado": ev["Resultado"], "_t": ev["time"]})
        st.dataframe(t.sort_values("_t", ascending=False).drop(columns="_t"), use_container_width=True, hide_index=True, height=520)

with tab_graf:
    opciones = sorted(allf["sym"].unique())
    pick = st.selectbox("Moneda:", opciones, index=0)
    st.plotly_chart(figura_moneda(allf[allf["sym"] == pick].reset_index(drop=True), pick), use_container_width=True)

errs = [m for (e, s), m in st.session_state["pb_errors"].items() if e == ex_id]
if errs:
    with st.expander(f"⚠️ {len(errs)} monedas con error"):
        st.write("\n\n".join(errs))
