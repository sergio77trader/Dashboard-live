"""
SLY | Scanner Smart Money + SS (KuCoin, por lotes)
==================================================
Réplica en Python del script de TradingView "SLY | Smart Money + SS (confluencia)".

SEÑAL LONG  (todas a la vez):
  1) Régimen alcista: EMA 52 > EMA 260.
  2) Zona alcista (Order Block verde o FVG alcista) tocada y que aguanta, en esta vela o en las últimas N.
  3) Gatillo SS: la vela Heikin Ashi VIRA a verde + MACD (DEMA) acelera + RSI (DEMA) sube.
SEÑAL SHORT: espejo (EMA 52 <= 260, zona roja, HA vira a rojo, MACD desacelera, RSI baja).

Ejecutar:  streamlit run sly_scanner_sm_ss.py
Requisitos: streamlit pandas numpy requests matplotlib
Es un scanner de señales: NO es un backtest y no dice si la estrategia es rentable.
"""
import math
import time
import zlib

import numpy as np
import pandas as pd
import requests
import streamlit as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

TF = {"1h": ("1hour", 3600), "4h": ("4hour", 14400), "1d": ("1day", 86400)}
STABLES = {"USDC", "TUSD", "DAI", "FDUSD", "USDP", "USDD", "BUSD", "EUR", "EURT", "PYUSD", "USDE", "USD1", "USDJ"}
BASE = "https://api.kucoin.com"


# ───────────────────────────── Datos (KuCoin) ─────────────────────────────
def kucoin_universo(min_vol_usd=500_000, top=100):
    r = requests.get(BASE + "/api/v1/market/allTickers", timeout=20)
    r.raise_for_status()
    j = r.json()
    if str(j.get("code")) != "200000":
        raise RuntimeError("KuCoin: %s" % j.get("msg"))
    rows = []
    for t in j["data"]["ticker"]:
        sym = t.get("symbol", "")
        if not sym.endswith("-USDT"):
            continue
        base = sym[:-5]
        if base in STABLES or base.endswith(("3L", "3S", "UP", "DOWN")):
            continue
        try:
            v = float(t.get("volValue") or 0)
        except ValueError:
            continue
        if v >= min_vol_usd:
            rows.append((sym, v))
    rows.sort(key=lambda x: -x[1])
    return [s for s, _ in rows[:top]]


def kucoin_velas(sym, tf, n_velas=1500):
    typ, step = TF[tf]
    end = int(time.time())
    start = end - step * n_velas
    for intento in range(3):
        r = requests.get(BASE + "/api/v1/market/candles", params=dict(symbol=sym, type=typ, startAt=start, endAt=end), timeout=20)
        if r.status_code == 429:
            time.sleep(1.5 * (intento + 1))
            continue
        r.raise_for_status()
        break
    j = r.json()
    if str(j.get("code")) != "200000":
        raise RuntimeError("KuCoin %s: %s" % (sym, j.get("msg")))
    d = j["data"]
    if not d:
        raise ValueError("sin velas")
    # [tiempo(s), apertura, cierre, máximo, mínimo, volumen, turnover]  (más nueva primero)
    df = pd.DataFrame([[int(x[0]), float(x[1]), float(x[3]), float(x[4]), float(x[2]), float(x[5])] for x in d],
                      columns=["t", "open", "high", "low", "close", "volume"])
    df["t"] = pd.to_datetime(df["t"], unit="s")
    df = df.drop_duplicates("t").set_index("t").sort_index()
    df = df[df.index + pd.Timedelta(seconds=step) <= pd.Timestamp.utcnow().tz_localize(None)]   # sin la vela en curso
    return df


def demo_universo(n=40):
    return ["DEMO%02d-USDT" % i for i in range(n)]


def demo_velas(sym, tf, n_velas=1500):
    rng = np.random.default_rng(zlib.crc32(sym.encode()))
    step = TF[tf][1]
    sig = 0.012 * math.sqrt(step / 14400)
    reg = np.cumsum(rng.normal(0, 0.15, n_velas))           # deriva lenta que cambia -> fases alcistas y bajistas
    ret = rng.normal(0, sig, n_velas) + 0.0012 * np.tanh(reg) * math.sqrt(step / 14400)
    c = 100 * np.exp(np.cumsum(ret))
    o = np.r_[c[0], c[:-1]]
    hi = np.maximum(o, c) * (1 + np.abs(rng.normal(0, sig * 0.5, n_velas)))
    lo = np.minimum(o, c) * (1 - np.abs(rng.normal(0, sig * 0.5, n_velas)))
    idx = pd.date_range(end=pd.Timestamp.utcnow().tz_localize(None).floor("h"), periods=n_velas, freq="%ds" % step)
    return pd.DataFrame({"open": o, "high": hi, "low": lo, "close": c, "volume": 1.0}, index=idx)


# ───────────────────────────── Indicadores ─────────────────────────────
def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def rma(s, n):
    return s.ewm(alpha=1.0 / n, adjust=False).mean()


def dema(s, n):
    e1 = ema(s, n)
    return 2 * e1 - ema(e1, n)


def rsi(c, n=14):
    d = c.diff()
    up, dn = rma(d.clip(lower=0), n), rma((-d).clip(lower=0), n)
    r = 100 - 100 / (1 + up / dn.replace(0, np.nan))
    return r.where(dn > 0, 100.0).fillna(50.0)


def atr(df, n=14):
    pc = df["close"].shift()
    tr = pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()], axis=1).max(axis=1)
    return rma(tr, n)


def heikin_ashi(df):
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    hc = (o + h + l + c) / 4
    ho = np.empty(len(df))
    ho[0] = (o[0] + c[0]) / 2
    for i in range(1, len(df)):
        ho[i] = (ho[i - 1] + hc[i - 1]) / 2
    return hc > ho


# ───────────────────────────── Smart Money (réplica del Pine) ─────────────────────────────
def _ob(o, h, l, c, i, origin, bull):
    """Order Block como en el Pine: extremo desde `origin` hasta hoy y vela contraria más cercana (hasta 5 velas atrás)."""
    span = min(i - origin, 100)
    ext, k = (1e18 if bull else -1e18), 0
    for j in range(0, span + 1):
        if i - j < 0:
            break
        v = l[i - j] if bull else h[i - j]
        if (v < ext) if bull else (v > ext):
            ext, k = v, j
    pick = k
    for j in range(k, k + 6):
        if i - j < 0:
            break
        if (c[i - j] < o[i - j]) if bull else (c[i - j] > o[i - j]):
            pick = j
            break
    q = i - pick
    return float(h[q]), float(l[q])


def analizar(df, n=5, zone_win=3, max_zones=6, min_fvg_atr=0.3, usar_ob=True, usar_fvg=True,
             ema_f=52, ema_s=260, macd_f=12, macd_s=26, macd_sig=9, rsi_len=14, rsi_sm=5, stop_buf=0.1):
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    N = len(df)
    A = atr(df).to_numpy(float)
    cs = df["close"]
    e52, e260 = ema(cs, ema_f), ema(cs, ema_s)
    macd = dema(cs, macd_f) - dema(cs, macd_s)
    hist = (macd - ema(macd, macd_sig)).to_numpy(float)
    rs = dema(rsi(cs, rsi_len), rsi_sm).to_numpy(float)
    ha_g = heikin_ashi(df)
    bull_reg = (e52 > e260).to_numpy()

    rmh = pd.Series(h).rolling(2 * n + 1).max().to_numpy()
    rml = pd.Series(l).rolling(2 * n + 1).min().to_numpy()
    lsh = lsl = np.nan
    lshb = lslb = -1
    shb = slb = True
    zonas = {"ob_bull": [], "ob_bear": [], "fvg_bull": [], "fvg_bear": []}
    muertas = []
    t_bull, t_bear = np.zeros(N, bool), np.zeros(N, bool)
    bot_bull, top_bear = np.full(N, np.nan), np.full(N, np.nan)
    tocadas = [None] * N

    for i in range(N):
        if i >= 2 * n:
            if h[i - n] == rmh[i]:
                lsh, lshb, shb = h[i - n], i - n, False
            if l[i - n] == rml[i]:
                lsl, lslb, slb = l[i - n], i - n, False
        bull_break = (not shb) and c[i] > lsh
        bear_break = (not slb) and c[i] < lsl
        if bull_break:
            if usar_ob and lslb >= 0:
                t, b = _ob(o, h, l, c, i, lslb, True)
                zonas["ob_bull"].append(dict(k="OB", lado="alcista", top=t, bot=b, lv=b, born=i, died=None))
            shb = True
        if bear_break:
            if usar_ob and lshb >= 0:
                t, b = _ob(o, h, l, c, i, lshb, False)
                zonas["ob_bear"].append(dict(k="OB", lado="bajista", top=t, bot=b, lv=t, born=i, died=None))
            slb = True
        if usar_fvg and i >= 2 and np.isfinite(A[i]):
            if l[i] > h[i - 2] and (l[i] - h[i - 2]) > min_fvg_atr * A[i]:
                zonas["fvg_bull"].append(dict(k="FVG", lado="alcista", top=float(l[i]), bot=float(h[i - 2]), lv=float(h[i - 2]), born=i, died=None))
            if h[i] < l[i - 2] and (l[i - 2] - h[i]) > min_fvg_atr * A[i]:
                zonas["fvg_bear"].append(dict(k="FVG", lado="bajista", top=float(l[i - 2]), bot=float(h[i]), lv=float(l[i - 2]), born=i, died=None))
        # toques (zona ya existente, no creada en esta vela, y que AGUANTA)
        tl = []
        for key in ("ob_bull", "fvg_bull"):
            for z in zonas[key]:
                if z["born"] < i and l[i] <= z["top"] and h[i] >= z["bot"] and c[i] >= z["bot"]:
                    t_bull[i] = True
                    bot_bull[i] = z["bot"] if np.isnan(bot_bull[i]) else min(bot_bull[i], z["bot"])
                    tl.append(z)
        for key in ("ob_bear", "fvg_bear"):
            for z in zonas[key]:
                if z["born"] < i and l[i] <= z["top"] and h[i] >= z["bot"] and c[i] <= z["top"]:
                    t_bear[i] = True
                    top_bear[i] = z["top"] if np.isnan(top_bear[i]) else max(top_bear[i], z["top"])
                    tl.append(z)
        tocadas[i] = tl or None
        # mitigación y tope de zonas activas
        for key, bull in (("ob_bull", True), ("fvg_bull", True), ("ob_bear", False), ("fvg_bear", False)):
            vivas = []
            for z in zonas[key]:
                if (c[i] < z["lv"]) if bull else (c[i] > z["lv"]):
                    z["died"] = i
                    muertas.append(z)
                else:
                    vivas.append(z)
            while len(vivas) > max_zones:
                z = vivas.pop(0)
                z["died"] = i
                muertas.append(z)
            zonas[key] = vivas

    s_hg, s_ha = pd.Series(ha_g), pd.Series(~ha_g)
    flip_g = (s_hg & ~s_hg.shift(1, fill_value=False)).to_numpy()
    flip_r = (s_ha & ~s_ha.shift(1, fill_value=False)).to_numpy()
    hs, rss = pd.Series(hist), pd.Series(rs)
    mac_up, mac_dn = (hs > hs.shift()).to_numpy(), (hs < hs.shift()).to_numpy()
    rsi_up, rsi_dn = (rss > rss.shift()).to_numpy(), (rss < rss.shift()).to_numpy()
    long_c = bull_reg & flip_g & mac_up & rsi_up
    short_c = (~bull_reg) & flip_r & mac_dn & rsi_dn
    rec_b = pd.Series(t_bull).rolling(zone_win, min_periods=1).max().to_numpy() > 0
    rec_r = pd.Series(t_bear).rolling(zone_win, min_periods=1).max().to_numpy() > 0
    botlow = pd.Series(bot_bull).rolling(zone_win, min_periods=1).min().to_numpy()
    tophigh = pd.Series(top_bear).rolling(zone_win, min_periods=1).max().to_numpy()
    long_ok, short_ok = long_c & rec_b, short_c & rec_r
    stop_l = np.where(np.isfinite(botlow) & (botlow - stop_buf * A < c), botlow - stop_buf * A, np.nan)
    stop_s = np.where(np.isfinite(tophigh) & (tophigh + stop_buf * A > c), tophigh + stop_buf * A, np.nan)
    return dict(df=df, e52=e52.to_numpy(), e260=e260.to_numpy(), ha_g=ha_g, bull_reg=bull_reg, long_ok=long_ok, short_ok=short_ok,
                long_c=long_c, short_c=short_c, rec_b=rec_b, rec_r=rec_r, stop_l=stop_l, stop_s=stop_s, tocadas=tocadas,
                zonas_vivas=[z for k in zonas for z in zonas[k]], zonas_muertas=muertas, hist=hist, rs=rs, atr=A,
                zone_win=zone_win)


def senales(res, ventana=3):
    """Señales en las últimas `ventana` velas cerradas (la última vela es la más reciente)."""
    df, N = res["df"], len(res["df"])
    out = []
    for i in range(max(0, N - ventana), N):
        for lado, ok, stop in (("LONG", res["long_ok"], res["stop_l"]), ("SHORT", res["short_ok"], res["stop_s"])):
            if ok[i]:
                zs = {}
                for j in range(max(0, i - res["zone_win"] + 1), i + 1):
                    for z in (res["tocadas"][j] or []):
                        if (lado == "LONG") == (z["lado"] == "alcista"):
                            zs[(z["k"], round(z["top"], 10), round(z["bot"], 10))] = z
                zl = sorted(zs.values(), key=lambda z: -z["born"])
                px = float(df["close"].iloc[i])
                st_ = float(stop[i]) if np.isfinite(stop[i]) else None
                out.append(dict(lado=lado, i=i, hace=N - 1 - i, hora=df.index[i], precio=px, stop=st_,
                                dist_stop=abs(px - st_) / px * 100 if st_ else None,
                                zona=", ".join("%s %s [%.6g–%.6g]" % (z["k"], z["lado"], z["bot"], z["top"]) for z in zl[:2])))
    return out


def estado(res):
    i = len(res["df"]) - 1
    return dict(regimen="ALCISTA" if res["bull_reg"][i] else "BAJISTA", ha="verde" if res["ha_g"][i] else "roja",
                zona_alcista=bool(res["rec_b"][i]), zona_bajista=bool(res["rec_r"][i]))


# ───────────────────────────── Gráfico ─────────────────────────────
def grafico(res, sym, sigs, tf, vis=160):
    df, N = res["df"], len(res["df"])
    a = max(0, N - vis)
    x = np.arange(a, N)
    d = df.iloc[a:N]
    fig, ax = plt.subplots(figsize=(11, 5.2))
    fig.patch.set_facecolor("#111111")
    ax.set_facecolor("#111111")
    for k in ("top", "right", "left", "bottom"):
        ax.spines[k].set_color("#333333")
    ax.tick_params(colors="#aaaaaa")
    # zonas (vivas, o muertas que se solapan con la ventana)
    todas = list(res["zonas_vivas"]) + [z for z in res["zonas_muertas"] if (z["died"] or 0) >= a]
    for z in todas:
        x0, x1 = max(z["born"], a), (z["died"] if z["died"] is not None else N - 1)
        if x1 < a or x0 > N - 1:
            continue
        col = ("#00c896" if z["k"] == "OB" else "#1abc9c") if z["lado"] == "alcista" else ("#ff4d6d" if z["k"] == "OB" else "#ff9f43")
        ax.add_patch(Rectangle((x0 - 0.5, z["bot"]), x1 - x0 + 1, z["top"] - z["bot"], facecolor=col, alpha=0.22, edgecolor=col, lw=0.8))
    # velas coloreadas por Heikin Ashi (como el barcolor del Pine)
    for xi, (o_, h_, l_, c_, g) in zip(x, zip(d["open"], d["high"], d["low"], d["close"], res["ha_g"][a:N])):
        col = "#00ffbb" if g else "#ff0055"
        ax.vlines(xi, l_, h_, color=col, lw=0.8)
        ax.add_patch(Rectangle((xi - 0.3, min(o_, c_)), 0.6, max(abs(c_ - o_), 1e-12), facecolor=col, edgecolor=col))
    ax.plot(x, res["e52"][a:N], color="#00ffbb", lw=1.6, label="EMA 52")
    ax.plot(x, res["e260"][a:N], color="#2962ff", lw=1.6, label="EMA 260")
    rng = (d["high"].max() - d["low"].min()) or 1
    for s in sigs:
        if s["i"] < a:
            continue
        if s["lado"] == "LONG":
            ax.scatter(s["i"], d["low"].iloc[s["i"] - a] - rng * 0.03, marker="^", s=130, color="#00ff66", zorder=5)
        else:
            ax.scatter(s["i"], d["high"].iloc[s["i"] - a] + rng * 0.03, marker="v", s=130, color="#ff3355", zorder=5)
        if s["stop"]:
            ax.hlines(s["stop"], s["i"], N - 1 + 3, colors="#ff5555", linestyles="dashed", lw=1.1)
    ax.set_xlim(a - 1, N + 4)
    ax.set_ylim(d["low"].min() - rng * 0.06, d["high"].max() + rng * 0.06)
    step = max(1, (N - a) // 8)
    ticks = list(range(a, N, step))
    ax.set_xticks(ticks)
    ax.set_xticklabels([df.index[t].strftime("%d/%m %Hh") for t in ticks], fontsize=8)
    ax.set_title("%s · %s" % (sym, tf), color="white", fontsize=11)
    ax.legend(loc="upper left", facecolor="#111111", labelcolor="white", fontsize=8, framealpha=0.6)
    fig.tight_layout()
    return fig


# ───────────────────────────── App ─────────────────────────────
def main():
    st.set_page_config(page_title="SLY Scanner SM + SS", layout="wide")
    st.title("SLY · Scanner Smart Money + SS")
    st.caption("Señal = régimen (EMA 52/260) + zona Smart Money a favor + gatillo SS (HA vira + MACD + RSI). Datos: KuCoin spot. "
               "Es un scanner, no un backtest: no garantiza rentabilidad.")
    S = st.session_state
    with st.sidebar:
        st.header("Datos")
        fuente = st.selectbox("Fuente", ["KuCoin", "Demo (sintético)"])
        tf = st.selectbox("Temporalidad", ["4h", "1h", "1d"], index=0)
        n_velas = st.slider("Velas por par", 600, 1500, 1500, 100, help="La EMA 260 necesita historia: no bajes de ~1000 si podés.")
        st.header("Lotes")
        top = st.number_input("Universo: top N pares por volumen", 10, 600, 100, 10)
        min_vol = st.number_input("Volumen 24h mínimo (USD)", 0, 100_000_000, 500_000, 100_000)
        lote = st.slider("Pares por lote", 5, 50, 20, 5)
        manual = st.text_area("O pegá tus pares (uno por línea, ej. BTC-USDT)", "")
        st.header("Señal")
        ventana = st.slider("Señal vigente: últimas N velas cerradas", 1, 10, 3)
        zone_win = st.slider("Tolerancia de zona (velas)", 1, 6, 3)
        usar_fvg = st.checkbox("Incluir FVG además de Order Blocks", True)
        with st.expander("Parámetros avanzados"):
            piv = st.number_input("Pivote (swing)", 2, 15, 5)
            maxz = st.number_input("Máx. zonas activas por tipo", 1, 20, 6)
            fvg_min = st.number_input("FVG mínimo (x ATR)", 0.0, 3.0, 0.3, 0.1)
            buf = st.number_input("Colchón del stop (x ATR)", 0.0, 2.0, 0.1, 0.05)

    firma = (fuente, tf, n_velas, int(top), int(min_vol), manual.strip(), lote)
    if S.get("firma") != firma:
        S.firma, S.pos, S.res, S.err, S.univ = firma, 0, {}, {}, None
    if S.univ is None:
        try:
            if manual.strip():
                S.univ = [x.strip().upper().replace("/", "-") for x in manual.splitlines() if x.strip()]
            elif fuente.startswith("Demo"):
                S.univ = demo_universo(int(top) if top < 60 else 40)
            else:
                S.univ = kucoin_universo(min_vol, int(top))
        except Exception as e:
            st.error("No pude traer el universo de KuCoin: %s" % e)
            S.univ = []
    univ = S.univ
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Universo", len(univ))
    c2.metric("Analizados", S.pos)
    c3.metric("Errores", len(S.err))
    b1, b2, b3 = st.columns(3)
    sig_lote = b1.button("Analizar siguiente lote", type="primary", disabled=S.pos >= len(univ))
    todo = b2.button("Analizar todos los lotes", disabled=S.pos >= len(univ))
    if b3.button("Reiniciar"):
        S.pos, S.res, S.err = 0, {}, {}
        st.rerun()

    params = dict(n=int(piv), zone_win=int(zone_win), max_zones=int(maxz), min_fvg_atr=float(fvg_min), usar_fvg=usar_fvg, stop_buf=float(buf))
    if sig_lote or todo:
        barra = st.progress(0.0, text="Analizando...")
        while S.pos < len(univ):
            lote_syms = univ[S.pos:S.pos + lote]
            for j, sym in enumerate(lote_syms):
                try:
                    df = demo_velas(sym, tf, n_velas) if fuente.startswith("Demo") else kucoin_velas(sym, tf, n_velas)
                    if len(df) < 400:
                        raise ValueError("pocas velas (%d)" % len(df))
                    S.res[sym] = analizar(df, **params)
                except Exception as e:
                    S.err[sym] = str(e)[:120]
                if not fuente.startswith("Demo"):
                    time.sleep(0.12)
                barra.progress((j + 1) / len(lote_syms), text="%s (%d/%d)" % (sym, S.pos + j + 1, len(univ)))
            S.pos += len(lote_syms)
            if not todo:
                break
        barra.empty()
        st.rerun()

    filas, por_par = [], {}
    for sym, res in S.res.items():
        sg = senales(res, ventana)
        por_par[sym] = sg
        for s in sg:
            filas.append(dict(Par=sym, Lado=s["lado"], Hace_velas=s["hace"], Hora=s["hora"].strftime("%d/%m %H:%M"), Precio_ref=s["precio"],
                              Stop=s["stop"], Dist_stop_pct=round(s["dist_stop"], 2) if s["dist_stop"] else None, Zona=s["zona"]))
    c4.metric("Con señal", len({f["Par"] for f in filas}))
    if not S.res:
        st.info("Apretá **Analizar siguiente lote** para empezar.")
        return
    if filas:
        tabla = pd.DataFrame(filas).sort_values(["Hace_velas", "Par"]).reset_index(drop=True)
        st.subheader("Señales vigentes (últimas %d velas cerradas)" % ventana)
        st.dataframe(tabla, use_container_width=True)
        opciones = ["%s · %s · hace %d" % (r.Par, r.Lado, r.Hace_velas) for r in tabla.itertuples()]
        elegido = st.selectbox("Ver gráfico", opciones)
        sym = elegido.split(" · ")[0]
        st.pyplot(grafico(S.res[sym], sym, por_par[sym], tf))
        st.caption("Triángulo = vela de señal. Línea punteada = stop más allá de la zona. Velas pintadas con el color Heikin Ashi. "
                   "Entrada real: apertura de la vela siguiente a la señal. Zonas: verde/turquesa alcistas, rojo/naranja bajistas.")
    else:
        st.warning("Sin señales vigentes en los pares analizados. Es normal: la estrategia exige régimen + zona + HA + MACD + RSI a la vez.")
    with st.expander("Estado de todos los pares analizados"):
        est = [dict(Par=s, **estado(r)) for s, r in S.res.items()]
        st.dataframe(pd.DataFrame(est), use_container_width=True)
    if S.err:
        with st.expander("Pares con error (%d)" % len(S.err)):
            st.dataframe(pd.DataFrame(sorted(S.err.items()), columns=["Par", "Error"]), use_container_width=True)


if __name__ == "__main__":
    main()
