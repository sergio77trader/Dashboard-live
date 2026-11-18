"""
SLY | DELTA + MACD + RSI  (KuCoin spot, por lotes)

LONG  : divergencia ALCISTA del delta (CVD) vigente + histograma MACD subiendo
        (acercándose a 0 desde abajo o alejándose de 0 hacia arriba) + RSI PRO subiendo.
SHORT : divergencia BAJISTA del delta vigente + histograma MACD bajando
        (acercándose a 0 desde arriba o alejándose de 0 hacia abajo) + RSI PRO bajando.

Delta: aproximado con velas de un timeframe menor (signo de la vela x volumen), igual idea que el
indicador "SLY | CVD PRO" pero con menos resolución (15m en vez de 1m) para poder escanear cientos de pares.
"""
import time
import numpy as np
import pandas as pd
import streamlit as st
import ccxt

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
TF_OPTIONS = {"30 MIN": "30m", "1 HS": "1h", "4 HS": "4h", "1 DIA": "1d", "1 SEMANA": "1w", "1 MES": "1M"}
TF_MS = {"30m": 1_800_000, "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000, "1w": 604_800_000, "1M": 2_592_000_000}  # 1M aprox. (solo para estimar)
LTF = {"30m": "5m", "1h": "5m", "4h": "15m", "1d": "1h", "1w": "1d", "1M": "1d"}          # timeframe menor para el delta
LTF_FINA = {"30m": "1m", "1h": "1m", "4h": "5m", "1d": "15m", "1w": "1h", "1M": "4h"}   # precisión "fina"
N_DELTA_FINA = {"30m": 100, "1h": 100, "4h": 100, "1d": 100, "1w": 52, "1M": 24}      # menos velas = menos consultas
LTF_MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "1h": 3_600_000, "4h": 14_400_000}

N_IND = 320          # velas del timeframe para MACD/RSI (calentamiento)
N_DELTA_D = {"1w": 100, "1M": 48}   # velas sobre las que se arma el CVD (por defecto 150)
MIN_VELAS_D = {"1w": 60, "1M": 30}  # historial mínimo (por defecto 150)
PIV_D = {"1M": (3, 3)}              # pivotes izq/der (por defecto 5/5; en mensual 3/3 para que haya divergencias)
MAX_GAP = 60
MIN_COBERTURA = 0.8  # % mínimo de velas con delta disponible

CRYPTO_SECTORS = {
    "LEADER": ["BTC/USDT", "ETH/USDT"],
    "LAYER 1": ["SOL/USDT", "ADA/USDT", "DOT/USDT", "AVAX/USDT", "MATIC/USDT", "NEAR/USDT", "FTM/USDT", "ALGO/USDT"],
    "DEFI/L2": ["ARB/USDT", "OP/USDT", "LINK/USDT", "UNI/USDT", "AAVE/USDT", "LDO/USDT"],
    "AI/DEPIN": ["RNDR/USDT", "FET/USDT", "FIL/USDT", "THETA/USDT"],
    "MEMES": ["DOGE/USDT", "SHIB/USDT", "PEPE/USDT", "BONK/USDT", "FLOKI/USDT"],
    "EXCHANGE": ["BNB/USDT", "KCS/USDT", "OKB/USDT"],
}


def get_sector(sym):
    for sec, m in CRYPTO_SECTORS.items():
        if sym.upper() in m:
            return sec
    return "ALTCOINS / OTROS"


# ─────────────────────────────────────────────
# MOTOR
# ─────────────────────────────────────────────
def dema(s, n):
    e1 = s.ewm(span=n, adjust=False).mean()
    e2 = e1.ewm(span=n, adjust=False).mean()
    return 2 * e1 - e2


def rsi_wilder(c, n=14):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50)


def indicadores(df):
    """MACD DEMA 12/26/9 y RSI PRO (RSI14 suavizado con DEMA 5), igual que los Pine."""
    out = df.copy()
    macd = dema(out.c, 12) - dema(out.c, 26)
    out["hist"] = macd - macd.ewm(span=9, adjust=False).mean()
    out["rsi"] = dema(rsi_wilder(out.c, 14), 5)
    return out


def pivotes(arr, l, r, alto=True):
    """Índices p confirmados (p = i - r) donde arr[p] es el único extremo de la ventana [p-l, p+r]."""
    res = []
    for p in range(l, len(arr) - r):
        w = arr[p - l:p + r + 1]
        ext = w.max() if alto else w.min()
        if arr[p] == ext and (w == ext).sum() == 1:
            res.append(p)
    return res


def divergencias(h, l, cvd, PV_L=5, PV_R=5):
    """Divergencias regulares precio vs CVD. Devuelve [(indice_confirmacion, 'ALCISTA'|'BAJISTA')]."""
    ev = []
    prev = None
    for p in pivotes(cvd, PV_L, PV_R, True):
        if prev and p - prev[0] <= MAX_GAP and h[p] > prev[1] and cvd[p] < prev[2]:
            ev.append((p + PV_R, "BAJISTA"))
        prev = (p, h[p], cvd[p])
    prev = None
    for p in pivotes(cvd, PV_L, PV_R, False):
        if prev and p - prev[0] <= MAX_GAP and l[p] < prev[1] and cvd[p] > prev[2]:
            ev.append((p + PV_R, "ALCISTA"))
        prev = (p, l[p], cvd[p])
    return sorted(ev)


def delta_por_vela(low_df, t_ms, index):
    """Delta por vela del timeframe: suma(signo(c-o) x volumen) de las velas menores que caen en cada vela
    (se asignan por hora de apertura, sirve también para semanal y mensual). NaN si no hay datos."""
    d = low_df.copy()
    d["dl"] = np.where(d.c >= d.o, d.v, -d.v)
    pos = np.searchsorted(t_ms, d.t.values, side="right") - 1
    d = d[pos >= 0]
    d["bin"] = t_ms[pos[pos >= 0]]
    s = d.groupby("bin").dl.sum()
    return pd.Series(s.reindex(t_ms).values, index=index)


def fin_vela(t_ms, tf):
    """Hora de cierre de una vela (mensual con calendario real)."""
    if tf == "1M":
        return int((pd.Timestamp(t_ms, unit="ms") + pd.DateOffset(months=1)).timestamp() * 1000)
    return t_ms + TF_MS[tf]


def bajar(ex, sym, tf, desde_ms, hasta_ms):
    ms = TF_MS.get(tf) or LTF_MS[tf]
    out, since = [], desde_ms
    while since < hasta_ms:
        b = ex.fetch_ohlcv(sym, tf, since=since, limit=1000)
        if not b:
            break
        out += b
        nxt = b[-1][0] + ms
        if nxt <= since:
            break
        since = nxt
        if len(b) < 2:
            break
    d = pd.DataFrame(out, columns=["t", "o", "h", "l", "c", "v"]).drop_duplicates("t").sort_values("t")
    return d.reset_index(drop=True)


def semanal_desde_diario(d):
    """Velas semanales ancladas al LUNES 00:00 UTC (como TradingView), armadas con velas diarias.
    Las velas '1w' de la API de KuCoin abren los jueves y no coinciden con las del gráfico."""
    dia = 86_400_000
    d = d.copy()
    d["t"] = d.t - (((d.t // dia) + 3) % 7) * dia          # el día 0 de epoch fue jueves
    g = d.groupby("t")
    return pd.DataFrame({"o": g.o.first(), "h": g.h.max(), "l": g.l.min(), "c": g.c.last(), "v": g.v.sum()}).reset_index()


def analizar(ex, sym, tf, solo_cerradas, ventana, fina=False):
    """Devuelve dict con la fila de resultados o lanza Exception con el motivo."""
    ms = TF_MS[tf]
    ahora = ex.milliseconds()
    if tf == "1w":
        df = semanal_desde_diario(bajar(ex, sym, "1d", ahora - (N_IND + 1) * 7 * 86_400_000, ahora))
    else:
        raw = ex.fetch_ohlcv(sym, tf, limit=N_IND)
        df = pd.DataFrame(raw, columns=["t", "o", "h", "l", "c", "v"]).drop_duplicates("t")
    px_now = float(df.c.iloc[-1]) if len(df) else float("nan")   # precio actual (vela en curso)
    if solo_cerradas and len(df) and fin_vela(int(df.t.iloc[-1]), tf) > ahora:
        df = df.iloc[:-1]
    df = df.reset_index(drop=True)
    min_v = MIN_VELAS_D.get(tf, 150)
    if len(df) < min_v:
        raise ValueError(f"Historial insuficiente: {len(df)} velas (se necesitan ≥{min_v})")

    df.index = pd.to_datetime(df.t, unit="ms", utc=True)
    ind = indicadores(df)

    # Delta sobre las últimas N_DELTA velas
    w = ind.iloc[-(N_DELTA_FINA[tf] if fina else N_DELTA_D.get(tf, 150)):]
    ltf = LTF_FINA[tf] if fina else LTF[tf]
    low = bajar(ex, sym, ltf, int(w.t.iloc[0]), fin_vela(int(w.t.iloc[-1]), tf))
    if low.empty:
        raise ValueError("Sin velas del timeframe menor para calcular delta")
    dl = delta_por_vela(low, w.t.values, w.index)
    cobertura = dl.notna().mean()
    if cobertura < MIN_COBERTURA:
        raise ValueError(f"Delta incompleto ({cobertura:.0%} de velas con datos)")
    cvd = dl.fillna(0).cumsum().values
    pl_, pr_ = PIV_D.get(tf, (5, 5))
    ev = divergencias(w.h.values, w.l.values, cvd, pl_, pr_)

    hist, rsi = ind["hist"].values, ind["rsi"].values
    macd_up = hist[-1] > hist[-2]
    rsi_up = rsi[-1] > rsi[-2]
    if hist[-1] > 0:
        macd_txt = "Alejándose de 0 ↑ GANANDO FUERZA 📈" if macd_up else "Acercándose a 0 desde arriba ↓ PERDIENDO FUERZA 📉"
    else:
        macd_txt = "Acercándose a 0 desde abajo ↑ GANANDO FUERZA 📈" if macd_up else "Alejándose de 0 ↓ PERDIENDO FUERZA 📉"
    rsi_txt = f"{rsi[-1]:.1f} {'SUBIENDO 🟢' if rsi_up else 'BAJANDO 🔴'}"

    div_txt, div_fecha, edad, div_tipo = "-", "-", None, None
    if ev:
        i, div_tipo = ev[-1]
        edad = len(w) - 1 - i
        div_txt = f"{div_tipo} (hace {edad} velas)"
        div_fecha = w.index[i].tz_convert("America/Argentina/Tucuman").strftime("%d/%m/%y %H:%M")

    vigente = div_tipo is not None and edad <= ventana
    estado = "SIN SEÑAL ⚪"
    if vigente and div_tipo == "ALCISTA":
        estado = "LONG 🟢" if (macd_up and rsi_up) else "VIGILAR LONG 🟡"
    elif vigente and div_tipo == "BAJISTA":
        estado = "SHORT 🔴" if (not macd_up and not rsi_up) else "VIGILAR SHORT 🟡"

    faltan = []
    if estado.startswith("VIGILAR"):
        quiere_up = div_tipo == "ALCISTA"
        if macd_up != quiere_up:
            faltan.append("MACD")
        if rsi_up != quiere_up:
            faltan.append("RSI")
    return {
        "Activo": sym.replace("/USDT", ""),
        "Sector": get_sector(sym),
        "Estado": estado,
        "Precio": f"{px_now:.6g}",
        "Divergencia delta": div_txt,
        "Fecha divergencia": div_fecha,
        "MACD": macd_txt,
        "RSI PRO": rsi_txt,
        "Delta última vela": "COMPRADOR" if dl.iloc[-1] > 0 else ("VENDEDOR" if dl.iloc[-1] < 0 else "-"),
        "Motivo": ("Falta: " + " y ".join(faltan)) if faltan else "OK",
    }


# ===== UI =====
st.set_page_config(layout="wide", page_title="SLY | DELTA + MACD + RSI")
st.markdown("""
<style>
 .stApp { background-color:#FFFFFF; color:#1C1E21; }
 h1 { color:#E65100; font-weight:800; border-bottom:3px solid #E65100; }
 .stProgress > div > div > div > div { background-color:#E65100; }
</style>""", unsafe_allow_html=True)

if "res_delta" not in st.session_state:
    st.session_state["res_delta"] = {}


@st.cache_resource
def get_exchange():
    return ccxt.kucoin({"enableRateLimit": True})


def fetch_symbols():
    try:
        ex = get_exchange()
        mk = ex.load_markets()
        s = [x for x in mk if "/USDT" in x and mk[x]["active"]]
        s = [x for x in s if not any(k in x for k in ["3L", "3S", "USDC", "DAI", "PAX", "TUSD"])]
        return sorted(x for x in s if ":" not in x)
    except Exception:
        return []


st.title("🛡️ SLY | DELTA + MACD + RSI")
st.caption("LONG: divergencia alcista del delta + MACD subiendo + RSI subiendo. SHORT: lo inverso. "
           "Horario en Argentina. El delta es una aproximación con velas de un timeframe menor.")

with st.sidebar:
    st.header("⚙️ Configuración")
    tf_label = st.selectbox("Temporalidad:", list(TF_OPTIONS.keys()), index=2)
    tf = TF_OPTIONS[tf_label]
    fina = st.radio("Precisión del delta", ["Estándar (rápida)", "Fina (más lenta)"], index=0,
                    help="El delta de cada vela de la temporalidad elegida se arma sumando compras y ventas de velas más chicas. "
                         "Fina usa velas más chicas: más exacto, pero más consultas a KuCoin por par.") .startswith("Fina")
    st.caption(f"Delta de cada vela de {tf_label}, calculado con velas de {LTF_FINA[tf] if fina else LTF[tf]}.")
    solo_cerradas = st.checkbox("Solo velas cerradas", value=True)
    ventana = st.slider("Divergencia vigente hasta (velas)", 1, 30, 10,
                        help="La divergencia se confirma 5 velas después del pivote. Cuanto más vieja, menos vale.")

    if st.button("📡 Sincronizar Mercado KuCoin"):
        st.session_state["lista"] = fetch_symbols()
        st.rerun()

    if "lista" in st.session_state:
        st.subheader("Ejecución")
        lote = st.number_input("Tamaño de lote:", 10, 100, 40)
        n_lotes = (len(st.session_state["lista"]) // lote) + 1
        idx = st.selectbox("Lote:", range(n_lotes), format_func=lambda x: f"Lote {x + 1}")
        if st.button("🚀 ACTUALIZAR Y ACUMULAR", type="primary"):
            ex = get_exchange()
            sub = st.session_state["lista"][idx * lote:(idx + 1) * lote]
            prog = st.progress(0)
            for k, sym in enumerate(sub):
                prog.progress((k + 1) / len(sub), text=f"{tf_label}: {sym}")
                try:
                    r = analizar(ex, sym, tf, solo_cerradas, ventana, fina)
                except Exception as e:
                    r = {"Activo": sym.replace("/USDT", ""), "Sector": get_sector(sym), "Estado": "SIN CÁLCULO ⚪",
                         "Precio": "-", "Divergencia delta": "-", "Fecha divergencia": "-", "MACD": "-",
                         "RSI PRO": "-", "Delta última vela": "-", "Motivo": f"{type(e).__name__}: {e}"}
                r["Temporalidad"] = tf_label
                st.session_state["res_delta"][f"{sym}|{tf_label}"] = r
                time.sleep(0.05)
            st.rerun()
    if st.button("🗑️ Limpiar memoria"):
        st.session_state["res_delta"] = {}
        st.rerun()

res = st.session_state["res_delta"]
if res:
    full = pd.DataFrame(res.values())
    cols = ["Activo", "Sector", "Temporalidad", "Estado", "Precio", "Divergencia delta", "Fecha divergencia",
            "MACD", "RSI PRO", "Delta última vela", "Motivo"]
    full = full[[c for c in cols if c in full.columns]]

    f1, f2, f3 = st.columns([2, 2, 3])
    ver = f1.selectbox("Mostrar", ["Todo", "Solo LONG/SHORT", "LONG/SHORT + VIGILAR", "Solo LONG", "Solo SHORT"])
    tfs = f2.multiselect("Temporalidad", sorted(full["Temporalidad"].unique()), default=sorted(full["Temporalidad"].unique()))
    secs = f3.multiselect("Sector", sorted(full["Sector"].unique()), default=sorted(full["Sector"].unique()))
    v = full[full["Temporalidad"].isin(tfs) & full["Sector"].isin(secs)]
    if ver == "Solo LONG/SHORT":
        v = v[v.Estado.str.startswith(("LONG", "SHORT"))]
    elif ver == "LONG/SHORT + VIGILAR":
        v = v[v.Estado.str.startswith(("LONG", "SHORT", "VIGILAR"))]
    elif ver == "Solo LONG":
        v = v[v.Estado.str.startswith("LONG")]
    elif ver == "Solo SHORT":
        v = v[v.Estado.str.startswith("SHORT")]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Analizadas", len(full))
    m2.metric("LONG", int(full.Estado.str.startswith("LONG").sum()))
    m3.metric("SHORT", int(full.Estado.str.startswith("SHORT").sum()))
    m4.metric("Sin cálculo", int(full.Estado.str.startswith("SIN C").sum()))

    orden = {"L": 0, "S": 1, "V": 2, "SIN SEÑAL": 3}
    v = v.assign(_o=v.Estado.map(lambda s: 0 if s.startswith("LONG") else 1 if s.startswith("SHORT")
                                  else 2 if s.startswith("VIGILAR") else 3 if s.startswith("SIN SE") else 4))
    v = v.sort_values(["_o", "Activo"]).drop(columns="_o")

    def color(val):
        s = str(val)
        if s.startswith("LONG") or "GANANDO" in s or "SUBIENDO" in s or s == "COMPRADOR" or s.startswith("ALCISTA"):
            return "background-color:#C8E6C9;color:#1B5E20;font-weight:bold;"
        if s.startswith("SHORT") or "PERDIENDO" in s or "BAJANDO" in s or s == "VENDEDOR" or s.startswith("BAJISTA"):
            return "background-color:#FFCDD2;color:#B71C1C;font-weight:bold;"
        if s.startswith("VIGILAR"):
            return "background-color:#FFF9C4;color:#827717;font-weight:bold;"
        return ""

    sty = v.style
    sty = (sty.map if hasattr(sty, "map") else sty.applymap)(color)
    st.dataframe(sty, use_container_width=True, height=620, hide_index=True)
else:
    st.info("👈 Sincronizá el mercado, elegí un lote y tocá ACTUALIZAR Y ACUMULAR.")
