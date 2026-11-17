"""
SLY | VOLUMEN ANORMAL  (KuCoin / Bybit / OKX spot, por lotes)

Requisitos:  pip install streamlit ccxt pandas numpy plotly
Ejecutar:    streamlit run sly_volumen_anomalo.py

Qué hace
  Busca criptos cuyo volumen de la última vela es anormal frente a su propio comportamiento, y dice QUÉ hizo el precio
  con ese volumen (impulso, absorción, rechazo). Se escanea por lotes y los resultados se acumulan; después se
  puede filtrar por lote, por lectura y por umbrales sin volver a descargar nada.

Medidas (todas contra las 20 velas anteriores, sin contar la actual)
  RVOL           volumen / mediana de las 20 velas anteriores (la mediana no se contamina con picos viejos).
  RVOL horario   volumen / mediana de las últimas 7 velas del MISMO horario (corrige que el volumen cripto cambia
                 según la hora del día). No aplica en diario.
  Z robusto      0,6745 · (vol − mediana) / MAD. Más de 3,5 se considera atípico.
  Percentil      posición del volumen dentro de las últimas 200 velas.
  RVOL 3 velas   promedio de las últimas 3 velas / mediana base: detecta volumen que se sostiene.
  Velas anómalas cuántas de las últimas 6 tuvieron RVOL alto.
  Lectura        combina volumen + rango + cierre: impulso alcista/bajista, absorción (volumen sin movimiento), rechazo.

Configuración: los controles se pueden guardar con 'Guardar como predeterminada' (queda en la dirección de la página y en
un archivo sly_volumen_config.json). Los valores iniciales están en DEFAULTS.

Límites: volumen de una sola plaza (no es el volumen total del mercado); en monedas poco líquidas un RVOL alto puede ser
ruido (por eso hay filtros de volumen mínimo en USDT); no predice dirección. No es una recomendación de inversión.
"""
import json
import time
from datetime import datetime

import ccxt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

st.set_page_config(layout="wide", page_title="SLY | VOLUMEN ANORMAL")
st.markdown("""
<style>
    .stApp { background-color: #FFFFFF; color: #1C1E21; }
    .stDataFrame { font-size: 11px; font-family: 'Roboto Mono', monospace; }
    h1 { color: #00695C; font-weight: 800; border-bottom: 3px solid #00695C; }
    .stProgress > div > div > div > div { background-color: #00695C; }
</style>
""", unsafe_allow_html=True)

TZ = "America/Argentina/Buenos_Aires"
EXCHANGES = {"KuCoin (spot)": "kucoin", "Bybit (spot)": "bybit", "OKX (spot)": "okx"}
TF_MS = {"15m": 900_000, "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}
LIMITS = {"kucoin": 1000, "bybit": 1000, "okx": 300}
N_BASE, N_PCT, K_SEAS, MIN_VELAS = 20, 200, 7, 50
STABLES = {"USDC", "USDT", "DAI", "TUSD", "FDUSD", "USDE", "PYUSD", "USDD", "BUSD", "PAX", "EUR", "EURT", "USD1"}
BAD_SUFFIX = ("3L", "3S", "5L", "5S", "UP", "DOWN", "BULL", "BEAR")


# ─────────────────────────────────────────────
# MOTOR
# ─────────────────────────────────────────────
def lectura(rvol, chg, loc, rr):
    """Qué hizo el precio con ese volumen. rr = rango de la vela / rango típico; loc = dónde cerró dentro del rango (0-1)."""
    if rvol is None or not np.isfinite(rvol) or rvol < 2:
        return "Normal"
    if rr is not None and np.isfinite(rr) and rr < 1.2 or chg == 0:
        return "ABSORCIÓN · volumen sin movimiento ⚠️"
    if chg > 0:
        return "IMPULSO ALCISTA ▲" if loc >= 0.6 else "SUBE PERO CIERRA DÉBIL (rechazo arriba)"
    return "IMPULSO BAJISTA ▼" if loc <= 0.4 else "CAE PERO CIERRA FUERTE (rechazo abajo)"


def calcular(df_raw, tf, solo_cerradas=True, ahora_ms=None):
    """
    df_raw: columnas time(ms), open, high, low, close, vol. Devuelve (métricas, cola para graficar).
    Si solo_cerradas=False, la vela en formación entra con su volumen PROYECTADO (vol / fracción transcurrida, mín. 25%).
    """
    ahora = int(time.time() * 1000) if ahora_ms is None else int(ahora_ms)
    tfm = TF_MS[tf]
    d = df_raw.dropna(subset=["open", "high", "low", "close", "vol"]).reset_index(drop=True).copy()
    d["vol"] = d["vol"].astype(float)
    proyectada = False
    if len(d) and int(d["time"].iloc[-1]) + tfm > ahora:
        if solo_cerradas:
            d = d.iloc[:-1].reset_index(drop=True)
        else:
            frac = max((ahora - int(d["time"].iloc[-1])) / tfm, 0.25)
            d.loc[d.index[-1], "vol"] = d["vol"].iloc[-1] / frac
            proyectada = True
    if len(d) < MIN_VELAS:
        raise ValueError(f"pocas velas ({len(d)}, mín. {MIN_VELAS})")
    d["usdt"] = d["vol"] * (d["open"] + d["high"] + d["low"] + d["close"]) / 4
    vol = d["vol"]
    v = float(vol.iloc[-1])
    base = vol.iloc[-N_BASE - 1:-1]
    med = float(base.median())
    mad = float((base - med).abs().median())
    rvol = v / med if med > 0 else np.nan
    zrob = 0.6745 * (v - med) / mad if mad > 0 else np.nan
    pct = float((vol.iloc[-N_PCT:] <= v).mean() * 100)
    rvol3 = float(vol.iloc[-3:].mean() / med) if med > 0 else np.nan
    # RVOL horario: mismas franjas horarias de días anteriores
    rvol_h = np.nan
    if tf != "1d":
        franja = d["time"] % 86_400_000
        previas = d.loc[(franja == franja.iloc[-1]) & (d.index < len(d) - 1), "vol"].tail(K_SEAS)
        if len(previas) >= 3 and previas.median() > 0:
            rvol_h = v / float(previas.median())
    # serie de RVOL para contar persistencia
    med_s = vol.shift(1).rolling(N_BASE).median()
    rvol_s = (vol / med_s.replace(0, np.nan))
    anom6 = int((rvol_s.iloc[-6:] >= 3).sum())
    # lectura de la vela
    o, h, l, c = (float(d[k].iloc[-1]) for k in ("open", "high", "low", "close"))
    chg = (c / o - 1) * 100 if o > 0 else 0.0
    loc = (c - l) / (h - l) if h > l else 0.5
    rng_pct = ((d["high"] - d["low"]) / d["close"])
    rr = float(rng_pct.iloc[-1] / rng_pct.iloc[-N_BASE - 1:-1].median()) if rng_pct.iloc[-N_BASE - 1:-1].median() > 0 else np.nan
    velas_dia = max(int(86_400_000 // tfm), 1)
    m = {
        "precio": c, "chg": round(chg, 2), "vol_usdt": float(d["usdt"].iloc[-1]),
        "base_usdt": med * float(d["close"].iloc[-N_BASE - 1:-1].mean()),
        "rvol": rvol, "rvol_h": rvol_h, "zrob": zrob, "pct": pct, "rvol3": rvol3, "anom6": anom6,
        "usdt24h": float(d["usdt"].iloc[-velas_dia:].sum()),
        "lectura": lectura(rvol, chg, loc, rr),
        "cierre_ms": int(d["time"].iloc[-1]) + tfm, "proyectada": proyectada,
    }
    cola = d.tail(120).copy()
    cola["med"] = med_s.tail(120).values
    return m, cola


def fetch_symbols(ex_id, orden):
    ex = get_ex(ex_id)
    markets = ex.load_markets()
    filas = []
    for s, mk in markets.items():
        if mk.get("quote") != "USDT" or not mk.get("spot") or not mk.get("active", True) or ":" in s:
            continue
        b = mk.get("base", "")
        if b in STABLES or b.upper().endswith(BAD_SUFFIX):
            continue
        filas.append([s, 0.0])
    if orden.startswith("Volumen"):
        try:
            tk = ex.fetch_tickers()
            for f in filas:
                t = tk.get(f[0]) or {}
                qv = t.get("quoteVolume")
                if qv is None and t.get("baseVolume") and t.get("last"):
                    qv = t["baseVolume"] * t["last"]
                f[1] = float(qv or 0.0)
            filas.sort(key=lambda x: -x[1])
            return [f[0] for f in filas]
        except Exception:
            pass
    return sorted(f[0] for f in filas)


def fetch_ohlcv_df(ex, ex_id, sym, tf):
    raw = ex.fetch_ohlcv(sym, timeframe=tf, limit=LIMITS.get(ex_id, 300))
    if not raw:
        raise ValueError("sin velas")
    d = pd.DataFrame(raw, columns=["time", "open", "high", "low", "close", "vol"])
    return d.drop_duplicates("time").sort_values("time").reset_index(drop=True)


def anomalo(r, thr_rvol, thr_z, min_vol_k, min_base_k):
    ok = (r["rvol"] >= thr_rvol) and (r["vol_usdt"] >= min_vol_k * 1000) and (r["base_usdt"] >= min_base_k * 1000)
    return bool(ok and (np.isnan(r["zrob"]) or r["zrob"] >= thr_z))


def figura(cola, sym, tf, thr_rvol):
    t = pd.to_datetime(cola["time"], unit="ms", utc=True).dt.tz_convert(TZ)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.65, 0.35], vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(x=t, open=cola["open"], high=cola["high"], low=cola["low"], close=cola["close"],
                                 increasing_line_color="#2E7D32", decreasing_line_color="#C62828", name=sym), row=1, col=1)
    col = np.where(cola["close"] >= cola["open"], "#66BB6A", "#EF5350")
    fig.add_trace(go.Bar(x=t, y=cola["vol"], marker_color=col, name="Volumen"), row=2, col=1)
    fig.add_trace(go.Scatter(x=t, y=cola["med"], mode="lines", line=dict(color="#555", width=1), name="Mediana 20"), row=2, col=1)
    fig.add_trace(go.Scatter(x=t, y=cola["med"] * thr_rvol, mode="lines", line=dict(color="#E65100", width=1, dash="dash"),
                             name=f"Umbral ×{thr_rvol:g}"), row=2, col=1)
    fig.update_layout(height=560, margin=dict(l=0, r=0, t=30, b=0), plot_bgcolor="white", xaxis_rangeslider_visible=False,
                      title=f"{sym} · {tf} (hora Argentina)", legend=dict(orientation="h", y=-0.08))
    return fig


# ─────────────────────────────────────────────
# CONFIGURACIÓN GUARDABLE
# ─────────────────────────────────────────────
CFG_FILE = "sly_volumen_config.json"
OPC_MODO = ["Solo cerradas", "Incluir la vela en formación (volumen proyectado)"]
OPC_ORDEN = ["Volumen 24h (más líquidos primero)", "Alfabético"]
DEFAULTS = {"w_ex": "KuCoin (spot)", "w_tf": "1h", "w_modo": OPC_MODO[0], "w_orden": OPC_ORDEN[0], "w_lote": 40,
            "w_rvol": 3.0, "w_z": 3.5, "w_minvol": 25, "w_minbase": 5}
PERFILES = {"Estricto": (4.0, 5.0, 50, 10), "Equilibrado": (3.0, 3.5, 25, 5), "Amplio": (2.5, 3.0, 5, 1)}


def _num(x, lo, hi, paso, default):
    try:
        x = min(max(float(x), lo), hi)
        return round(round(x / paso) * paso, 4)
    except Exception:
        return default


def validar_cfg(cfg):
    """Deja solo valores válidos y dentro del rango de cada control; lo demás vuelve al predeterminado."""
    d = DEFAULTS
    out = dict(d)
    if cfg.get("w_ex") in EXCHANGES:
        out["w_ex"] = cfg["w_ex"]
    if cfg.get("w_tf") in TF_MS:
        out["w_tf"] = cfg["w_tf"]
    if cfg.get("w_modo") in OPC_MODO:
        out["w_modo"] = cfg["w_modo"]
    if cfg.get("w_orden") in OPC_ORDEN:
        out["w_orden"] = cfg["w_orden"]
    out["w_lote"] = int(_num(cfg.get("w_lote", d["w_lote"]), 10, 100, 1, d["w_lote"]))
    out["w_rvol"] = _num(cfg.get("w_rvol", d["w_rvol"]), 1.5, 15.0, 0.5, d["w_rvol"])
    out["w_z"] = _num(cfg.get("w_z", d["w_z"]), 1.0, 10.0, 0.5, d["w_z"])
    out["w_minvol"] = int(_num(cfg.get("w_minvol", d["w_minvol"]), 0, 500, 5, d["w_minvol"]))
    out["w_minbase"] = int(_num(cfg.get("w_minbase", d["w_minbase"]), 0, 100, 1, d["w_minbase"]))
    return out


def cargar_cfg():
    """Prioridad: dirección (URL) > archivo guardado > predeterminados."""
    cfg = {}
    try:
        with open(CFG_FILE, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    try:
        for k in DEFAULTS:
            if k in st.query_params:
                cfg[k] = st.query_params[k]
    except Exception:
        pass
    return validar_cfg(cfg)


def guardar_cfg():
    """Guarda en archivo local (si se puede) y en la dirección de la página. Devuelve (archivo_ok, url_ok)."""
    cfg = validar_cfg({k: st.session_state.get(k, v) for k, v in DEFAULTS.items()})
    ok_file = ok_url = True
    try:
        with open(CFG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        ok_file = False
    try:
        st.query_params.update({k: str(v) for k, v in cfg.items()})
    except Exception:
        ok_url = False
    return ok_file, ok_url


def aplicar_perfil(nombre):
    r, z, mv, mb = PERFILES[nombre]
    st.session_state.update(w_rvol=r, w_z=z, w_minvol=mv, w_minbase=mb)


# ═════════════════════════════════════════════
# INTERFAZ
# ═════════════════════════════════════════════
@st.cache_resource
def get_ex(ex_id):
    return getattr(ccxt, ex_id)({"enableRateLimit": True})


for k, vdef in (("vol_res", {}), ("vol_tail", {}), ("vol_list", None), ("vol_err", {}), ("vol_upd", {})):
    if k not in st.session_state:
        st.session_state[k] = vdef

if "cfg_ok" not in st.session_state:                      # carga única al abrir la página
    for _k, _v in cargar_cfg().items():
        st.session_state[_k] = _v
    st.session_state["cfg_ok"] = True

st.title("📊 SLY | VOLUMEN ANORMAL")

with st.sidebar:
    st.header("⚙️ Datos")
    ex_lbl = st.selectbox("Exchange:", list(EXCHANGES.keys()), key="w_ex")
    ex_id = EXCHANGES[ex_lbl]
    tf = st.selectbox("Temporalidad:", list(TF_MS.keys()), key="w_tf")
    modo = st.radio("Velas:", OPC_MODO, key="w_modo")
    solo_cerradas = modo == OPC_MODO[0]
    orden = st.radio("Orden de los lotes:", OPC_ORDEN, key="w_orden")
    if st.button("📡 Sincronizar mercado"):
        try:
            st.session_state["vol_list"] = (ex_id, orden, fetch_symbols(ex_id, orden))
        except Exception as e:
            st.error(f"No se pudo leer el mercado: {type(e).__name__}: {str(e)[:300]}")

    lst = st.session_state["vol_list"]
    to_scan = None
    if lst and lst[0] == ex_id:
        symbols = lst[2]
        st.caption(f"{len(symbols)} pares · orden: {lst[1]}")
        lote_size = int(st.number_input("Tamaño de lote:", 10, 100, key="w_lote"))
        total = (len(symbols) - 1) // lote_size + 1
        lotes_sel = st.multiselect("Lotes a escanear:", list(range(1, total + 1)), default=[1], format_func=lambda x: f"Lote {x}")
        if st.button("🚀 ESCANEAR LOTES SELECCIONADOS", type="primary", use_container_width=True):
            to_scan = [(s, i // lote_size + 1) for i, s in enumerate(symbols) if (i // lote_size + 1) in lotes_sel]
        cargadas = [k for k in st.session_state["vol_res"] if k[0] == ex_id and k[1] == tf]
        if cargadas and st.button("🔄 Refrescar todas las cargadas", use_container_width=True):
            to_scan = [(k[2], st.session_state["vol_res"][k]["Lote"]) for k in cargadas]
    elif lst:
        st.info("Cambiaste de exchange: sincronizá de nuevo.")
    if st.button("🗑️ Limpiar resultados"):
        for k in ("vol_res", "vol_tail", "vol_err", "vol_upd"):
            st.session_state[k] = {}
        st.rerun()

    st.header("🎛️ Umbrales (no vuelven a descargar)")
    pc = st.columns(3)
    for _c, _n in zip(pc, PERFILES):
        _c.button(_n, on_click=aplicar_perfil, args=(_n,), use_container_width=True)
    thr_rvol = st.slider("RVOL mínimo (× mediana)", 1.5, 15.0, step=0.5, key="w_rvol")
    thr_z = st.slider("Z robusto mínimo", 1.0, 10.0, step=0.5, key="w_z")
    min_vol_k = st.slider("Volumen mínimo de la vela (miles de USDT)", 0, 500, step=5, key="w_minvol")
    min_base_k = st.slider("Volumen base mínimo por vela (miles de USDT)", 0, 100, step=1, key="w_minbase")
    if st.button("💾 Guardar como predeterminada", use_container_width=True):
        ok_f, ok_u = guardar_cfg()
        if ok_u:
            st.success("Guardada en la dirección de esta página: guardala en favoritos y se abre con tu configuración.")
        if ok_f:
            st.info(f"También quedó en el archivo {CFG_FILE}. Si la app está en Streamlit Cloud, ese archivo se borra cuando la app se reinicia.")
        if not (ok_f or ok_u):
            st.warning("No se pudo guardar. Cambiá los valores por defecto en DEFAULTS, al principio de la sección de configuración.")

    if to_scan:
        ex = get_ex(ex_id)
        prog = st.progress(0)
        for i, (sym, lote) in enumerate(to_scan):
            prog.progress((i + 1) / len(to_scan), text=f"Analizando {sym} (lote {lote})")
            key = (ex_id, tf, sym)
            try:
                m, cola = calcular(fetch_ohlcv_df(ex, ex_id, sym, tf), tf, solo_cerradas)
                m["Lote"], m["Activo"] = lote, sym.replace("/USDT", "")
                st.session_state["vol_res"][key] = m
                st.session_state["vol_tail"][key] = cola
                st.session_state["vol_upd"][key] = datetime.now().strftime("%H:%M")
                st.session_state["vol_err"].pop(key, None)
            except Exception as e:
                st.session_state["vol_err"][key] = f"{sym}: {type(e).__name__}: {str(e)[:150]}"
            time.sleep(0.05)
        prog.empty()
        st.rerun()

res = {k: v for k, v in st.session_state["vol_res"].items() if k[0] == ex_id and k[1] == tf}
if not res:
    st.info("👈 Sincronizá el mercado, elegí uno o varios lotes y escaneá. El Lote 1 son los más líquidos. "
            "Podés acumular lotes y filtrar después.")
    st.stop()

rows = []
for k, r in res.items():
    rows.append({
        "Lote": r["Lote"], "Activo": r["Activo"], "Precio": float(f"{r['precio']:.6g}"), "Var vela %": r["chg"],
        "Vol vela (K USDT)": round(r["vol_usdt"] / 1000, 1), "Base (K USDT)": round(r["base_usdt"] / 1000, 1),
        "RVOL": round(r["rvol"], 2) if np.isfinite(r["rvol"]) else np.nan,
        "RVOL horario": round(r["rvol_h"], 2) if np.isfinite(r["rvol_h"]) else np.nan,
        "Z robusto": round(r["zrob"], 1) if np.isfinite(r["zrob"]) else np.nan,
        "Percentil": round(r["pct"]), "RVOL 3v": round(r["rvol3"], 2) if np.isfinite(r["rvol3"]) else np.nan,
        "Anómalas /6": r["anom6"], "Vol 24h (K USDT)": round(r["usdt24h"] / 1000),
        "Lectura": r["lectura"] + (" (proyectada)" if r["proyectada"] else ""),
        "Anómalo": "SÍ 🔥" if anomalo(r, thr_rvol, thr_z, min_vol_k, min_base_k) else "-",
        "Cierre vela": pd.to_datetime(r["cierre_ms"], unit="ms", utc=True).tz_convert(TZ).strftime("%d/%m %H:%M"),
        "Act.": st.session_state["vol_upd"].get(k, "-"),
    })
df = pd.DataFrame(rows)

c1, c2, c3, c4 = st.columns([1.2, 1.6, 1, 1])
lotes_vis = c1.multiselect("Filtrar por lote", sorted(df["Lote"].unique()), default=[], format_func=lambda x: f"Lote {x}")
lect_opts = ["IMPULSO ALCISTA", "IMPULSO BAJISTA", "ABSORCIÓN", "RECHAZO", "Normal"]
lect_sel = c2.multiselect("Lectura", lect_opts)
solo_an = c3.checkbox("Solo anómalos", value=True)
solo_sost = c4.checkbox("Volumen sostenido (≥2 de 6)", value=False)

v = df
if lotes_vis:
    v = v[v["Lote"].isin(lotes_vis)]
if solo_an:
    v = v[v["Anómalo"] != "-"]
if solo_sost:
    v = v[v["Anómalas /6"] >= 2]
if lect_sel:
    def _match(s):
        for o in lect_sel:
            if o == "RECHAZO" and "rechazo" in s:
                return True
            if o != "RECHAZO" and s.startswith(o):
                return True
        return False
    v = v[v["Lectura"].map(_match)]
v = v.sort_values(["Anómalo", "Z robusto", "RVOL"], ascending=[False, False, False], na_position="last")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Criptos escaneadas", len(df))
m2.metric("Anómalas ahora", int((df["Anómalo"] != "-").sum()))
m3.metric("Impulso alcista", int(((df["Anómalo"] != "-") & df["Lectura"].str.startswith("IMPULSO ALCISTA")).sum()))
m4.metric("Absorción", int(((df["Anómalo"] != "-") & df["Lectura"].str.startswith("ABSORCIÓN")).sum()))


def estilo(val):
    s = str(val)
    if s == "SÍ 🔥" or s.startswith("IMPULSO ALCISTA"):
        return "background-color: #C8E6C9; color: #1B5E20; font-weight: bold;"
    if s.startswith("IMPULSO BAJISTA"):
        return "background-color: #FFCDD2; color: #B71C1C; font-weight: bold;"
    if s.startswith("ABSORCIÓN") or "rechazo" in s:
        return "background-color: #FFF9C4; color: #827717; font-weight: bold;"
    return ""


def estilo_chg(val):
    try:
        return "color: #1B5E20; font-weight: bold;" if float(val) > 0 else ("color: #B71C1C; font-weight: bold;" if float(val) < 0 else "")
    except Exception:
        return ""


tab_t, tab_g = st.tabs(["📋 Tabla", "📈 Gráfico"])
with tab_t:
    if v.empty:
        st.info("Ninguna cripto cumple los filtros. Bajá los umbrales o desmarcá 'Solo anómalos'.")
    else:
        sty = v.style
        mapf = sty.map if hasattr(sty, "map") else sty.applymap
        sty = mapf(estilo, subset=["Anómalo", "Lectura"])
        sty = (sty.map if hasattr(sty, "map") else sty.applymap)(estilo_chg, subset=["Var vela %"])
        st.dataframe(sty, use_container_width=True, height=560, hide_index=True)
    st.caption("RVOL = volumen / mediana de las 20 velas anteriores · RVOL horario = contra las últimas 7 velas del mismo horario · "
               "Z robusto > 3,5 = atípico · 'Anómalas /6' = cuántas de las últimas 6 velas tuvieron RVOL ≥ 3. "
               "Volumen de una sola plaza. Estadística, no recomendación.")

with tab_g:
    opciones = v["Activo"].tolist() if not v.empty else df["Activo"].tolist()
    pick = st.selectbox("Cripto:", opciones)
    clave = next((k for k in res if res[k]["Activo"] == pick), None)
    if clave and clave in st.session_state["vol_tail"]:
        st.plotly_chart(figura(st.session_state["vol_tail"][clave], clave[2], tf, thr_rvol), use_container_width=True)

errs = [m for k, m in st.session_state["vol_err"].items() if k[0] == ex_id and k[1] == tf]
if errs:
    with st.expander(f"⚠️ {len(errs)} criptos con error"):
        st.write("\n\n".join(errs))
