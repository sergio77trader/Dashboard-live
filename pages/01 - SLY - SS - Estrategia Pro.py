"""
SLY | RADAR DE DERIVADOS  (Streamlit)
=====================================================================
Lee datos PUBLICOS de futuros perpetuos de Binance u OKX (sin API key; si Binance bloquea la IP, pasa a OKX) y, por moneda,
te dice qué hacer: LONG / SHORT / EVITAR LONGS / ESPERAR REBOTE / ESPERAR,
con una referencia de stop y tamaño de posición.

DATOS (Binance USD-M Futures u OKX perpetuos lineales, endpoints públicos):
  - Funding rate actual e historial  -> cuán apiñados están longs o shorts
  - Open interest (historial ~30 d)  -> si entra o sale dinero apalancado
  - Ratio long/short de cuentas      -> sentimiento
  - Flujo agresivo (taker buy/sell)  -> quién pega más fuerte
  - Prima/base mark vs index         -> demanda de apalancamiento
  - Velas                            -> tendencia (EMA50), ATR para el stop

LOGICA (resumen): cada moneda suma puntos LONG y puntos SHORT según la
confluencia de esas señales y de la tendencia. Hay "anulaciones" de seguridad:
longs apiñados, shorts apiñados y posible capitulación.

IMPORTANTE
  * Es una herramienta de CONTEXTO y apoyo a la decisión. NO garantiza resultados
    y que estas reglas den ventaja NO está probado: validalas antes de operar.
  * El historial de OI/ratios de Binance es de ~30 días.
  * Las liquidaciones no tienen historial público por API (no están acá).

EJECUTAR
    pip install streamlit pandas numpy requests
    streamlit run sly_radar_derivados.py
"""
import math
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
import requests
import streamlit as st
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE = "https://fapi.binance.com"
PERIOD_H = {"1h": 1, "2h": 2, "4h": 4, "6h": 6, "12h": 12, "1d": 24}
TTL_RAW = 300          # segundos que se reutilizan los datos descargados
EXCLUIR_BASES = {"USDC", "BTCDOM", "DEFI", "FDUSD"}


# ---------------------------------------------------------------------------
# Acceso a la API
# ---------------------------------------------------------------------------
class BloqueoRegional(Exception):
    pass


def _crear_sesion():
    s = requests.Session()
    retry = Retry(total=3, backoff_factor=0.8,
                  status_forcelist=(429, 500, 502, 503, 504),
                  allowed_methods=("GET",))
    s.mount("https://", HTTPAdapter(max_retries=retry, pool_maxsize=16))
    s.headers.update({"User-Agent": "sly-radar/1.0"})
    return s


SESION = _crear_sesion()


def api(path, params=None):
    r = SESION.get(BASE + path, params=params, timeout=15)
    if r.status_code in (403, 451):
        raise BloqueoRegional(
            "Binance bloqueó el acceso desde esta conexión (HTTP %d). "
            "Probá sin VPN o desde otra red." % r.status_code)
    r.raise_for_status()
    return r.json()


OKX = "https://www.okx.com"
OKX_BAR = {"1h": "1H", "2h": "2H", "4h": "4H", "6h": "6H", "12h": "12H", "1d": "1D"}
_okx_lock = threading.Lock()
_okx_ultimo = [0.0]


def _okx_espera(gap):
    """Separa las llamadas a OKX (los endpoints 'rubik' tienen límite estricto)."""
    with _okx_lock:
        dt = time.time() - _okx_ultimo[0]
        if dt < gap:
            time.sleep(gap - dt)
        _okx_ultimo[0] = time.time()


def api_okx(path, params=None, gap=0.0):
    if gap:
        _okx_espera(gap)
    r = SESION.get(OKX + path, params=params, timeout=15)
    if r.status_code in (403, 451):
        raise BloqueoRegional(
            "OKX bloqueó el acceso desde esta conexión (HTTP %d)." % r.status_code)
    r.raise_for_status()
    j = r.json()
    if str(j.get("code")) != "0":
        raise RuntimeError("OKX: %s" % j.get("msg"))
    return j["data"]


def okx_inst(sym):
    """BTCUSDT -> BTC-USDT-SWAP"""
    return sym[:-4] + "-USDT-SWAP"


def _df(lista, cols_num, tcol):
    df = pd.DataFrame(lista)
    if df.empty:
        return df
    for c in cols_num:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["t"] = pd.to_datetime(pd.to_numeric(df[tcol], errors="coerce"), unit="ms")
    return df.set_index("t").sort_index()


# ---------------------------------------------------------------------------
# Modo demo (datos sintéticos, para ver la app sin conexión)
# ---------------------------------------------------------------------------
DEMO_BASES = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "AVAX", "LINK",
              "DOT", "NEAR", "ARB", "OP", "INJ", "SUI", "APT"]


def demo_universo():
    rng = np.random.default_rng(1)
    filas = []
    for i, b in enumerate(DEMO_BASES):
        filas.append({"symbol": b + "USDT", "base": b,
                      "lastPrice": float(rng.uniform(0.5, 3000)),
                      "priceChangePercent": float(rng.normal(0, 3)),
                      "quoteVolume": float(rng.uniform(5e7, 5e9) / (1 + i * 0.2))})
    return pd.DataFrame(filas).sort_values("quoteVolume", ascending=False).reset_index(drop=True)


def demo_premium(symbols):
    rng = np.random.default_rng(2)
    filas = []
    for s in symbols:
        mark = float(rng.uniform(0.5, 3000))
        filas.append({"symbol": s, "markPrice": mark,
                      "indexPrice": mark * (1 + float(rng.normal(0, 0.0008))),
                      "lastFundingRate": float(rng.normal(0.00008, 0.00012))})
    return pd.DataFrame(filas).set_index("symbol")


def demo_raw(sym, period):
    seed = abs(hash(sym)) % (2 ** 32)
    rng = np.random.default_rng(seed)
    n = 220
    h = PERIOD_H[period]
    idx = pd.date_range(end=pd.Timestamp.utcnow().tz_localize(None).floor("h"), periods=n, freq="%dh" % h)
    ret = rng.normal(0.0002, 0.012 * math.sqrt(h), n)
    c = 100 * np.exp(np.cumsum(ret))
    o = np.r_[c[0], c[:-1]]
    hi = np.maximum(o, c) * (1 + np.abs(rng.normal(0, 0.004, n)))
    lo = np.minimum(o, c) * (1 - np.abs(rng.normal(0, 0.004, n)))
    k = pd.DataFrame({"o": o, "h": hi, "l": lo, "c": c, "v": rng.uniform(1e3, 1e4, n)}, index=idx)
    m = 180
    idx2 = idx[-m:]
    oi = pd.DataFrame({"sumOpenInterestValue": 1e8 * np.exp(np.cumsum(rng.normal(0, 0.01, m))),
                       "sumOpenInterest": 1e6 * np.ones(m)}, index=idx2)
    ls = pd.DataFrame({"longShortRatio": np.clip(1.5 + np.cumsum(rng.normal(0, 0.05, m)), 0.4, 3.5),
                       "longAccount": 0.6, "shortAccount": 0.4}, index=idx2)
    buy = rng.uniform(1e3, 2e3, m)
    sell = rng.uniform(1e3, 2e3, m)
    tk = pd.DataFrame({"buySellRatio": buy / sell, "buyVol": buy, "sellVol": sell}, index=idx2)
    fidx = pd.date_range(end=idx[-1], periods=100, freq="8h")
    fr = pd.DataFrame({"fundingRate": rng.normal(0.00006, 0.0001, 100)}, index=fidx)
    return {"k": k, "oi": oi, "ls": ls, "tk": tk, "fr": fr}


def demo_btc():
    rng = np.random.default_rng(3)
    c = 30000 * np.exp(np.cumsum(rng.normal(0.0008, 0.02, 250)))
    return bool(c[-1] > pd.Series(c).rolling(200).mean().iloc[-1]), float(c[-1])


# ---------------------------------------------------------------------------
# Descarga
# ---------------------------------------------------------------------------
def _universo_binance():
    info = api("/fapi/v1/exchangeInfo")
    perp = {s["symbol"]: s["baseAsset"] for s in info["symbols"]
            if s.get("contractType") == "PERPETUAL" and s.get("quoteAsset") == "USDT"
            and s.get("status") == "TRADING"}
    tick = pd.DataFrame(api("/fapi/v1/ticker/24hr"))
    tick = tick[tick["symbol"].isin(perp)].copy()
    for c in ("lastPrice", "priceChangePercent", "quoteVolume"):
        tick[c] = pd.to_numeric(tick[c], errors="coerce")
    tick["base"] = tick["symbol"].map(perp)
    return tick


def _universo_okx():
    inst = api_okx("/api/v5/public/instruments", {"instType": "SWAP"})
    perp = {}
    for i in inst:
        if i.get("settleCcy") == "USDT" and i.get("ctType") == "linear" and i.get("state") == "live":
            base = i["instId"].split("-")[0]
            perp[i["instId"]] = base
    tk = pd.DataFrame(api_okx("/api/v5/market/tickers", {"instType": "SWAP"}))
    tk = tk[tk["instId"].isin(perp)].copy()
    for c in ("last", "open24h", "volCcy24h"):
        tk[c] = pd.to_numeric(tk[c], errors="coerce")
    tk["base"] = tk["instId"].map(perp)
    tk["symbol"] = tk["base"] + "USDT"
    tk["lastPrice"] = tk["last"]
    tk["priceChangePercent"] = (tk["last"] / tk["open24h"] - 1) * 100
    tk["quoteVolume"] = tk["volCcy24h"] * tk["last"]   # volCcy24h está en moneda base
    return tk[["symbol", "base", "lastPrice", "priceChangePercent", "quoteVolume"]]


@st.cache_data(ttl=600, show_spinner=False)
def listar_universo(fuente="binance", demo=False):
    if demo:
        return demo_universo()
    tick = _universo_binance() if fuente == "binance" else _universo_okx()
    tick = tick[~tick["base"].isin(EXCLUIR_BASES)]
    tick = tick.dropna(subset=["quoteVolume"]).drop_duplicates("symbol")
    return tick.sort_values("quoteVolume", ascending=False).reset_index(drop=True)


@st.cache_data(ttl=60, show_spinner=False)
def cargar_premium(symbols_tuple, fuente="binance", demo=False):
    if demo:
        return demo_premium(symbols_tuple)
    if fuente == "binance":
        df = pd.DataFrame(api("/fapi/v1/premiumIndex"))
        for c in ("markPrice", "indexPrice", "lastFundingRate"):
            df[c] = pd.to_numeric(df[c], errors="coerce")
        return df.set_index("symbol")
    mk = pd.DataFrame(api_okx("/api/v5/public/mark-price", {"instType": "SWAP"}))
    ix = pd.DataFrame(api_okx("/api/v5/market/index-tickers", {"quoteCcy": "USDT"}))
    mk["symbol"] = mk["instId"].str.split("-").str[0] + "USDT"
    mk = mk[mk["instId"].str.endswith("-USDT-SWAP")]
    mk["markPrice"] = pd.to_numeric(mk["markPx"], errors="coerce")
    ix["symbol"] = ix["instId"].str.split("-").str[0] + "USDT"
    ix["indexPrice"] = pd.to_numeric(ix["idxPx"], errors="coerce")
    df = mk[["symbol", "markPrice"]].drop_duplicates("symbol").merge(
        ix[["symbol", "indexPrice"]].drop_duplicates("symbol"), on="symbol", how="left")
    df["lastFundingRate"] = np.nan      # en OKX el funding se pide por instrumento (raw["fund_now"])
    return df.set_index("symbol")


@st.cache_data(ttl=600, show_spinner=False)
def regimen_btc(fuente="binance", demo=False):
    """BTC sobre su SMA 200 diaria (cierre de la vela diaria anterior)."""
    if demo:
        return demo_btc()
    if fuente == "binance":
        k = api("/fapi/v1/klines", {"symbol": "BTCUSDT", "interval": "1d", "limit": 260})
        c = pd.Series([float(x[4]) for x in k])
        c = c.iloc[:-1]  # sin la vela en curso
    else:
        k = api_okx("/api/v5/market/candles", {"instId": "BTC-USDT-SWAP", "bar": "1D", "limit": 300})
        k = [x for x in k if str(x[8]) == "1"]            # solo velas confirmadas
        c = pd.Series([float(x[4]) for x in reversed(k)])  # OKX entrega la más nueva primero
    return bool(c.iloc[-1] > c.rolling(200).mean().iloc[-1]), float(c.iloc[-1])


def bajar_moneda(sym, period):
    k = pd.DataFrame(api("/fapi/v1/klines", {"symbol": sym, "interval": period, "limit": 220}))
    k = k.iloc[:, :6]
    k.columns = ["t", "o", "h", "l", "c", "v"]
    for c in ("o", "h", "l", "c", "v"):
        k[c] = pd.to_numeric(k[c], errors="coerce")
    k["t"] = pd.to_datetime(k["t"], unit="ms")
    k = k.set_index("t").sort_index()
    p = {"symbol": sym, "period": period, "limit": 200}
    oi = _df(api("/futures/data/openInterestHist", p), ["sumOpenInterest", "sumOpenInterestValue"], "timestamp")
    ls = _df(api("/futures/data/globalLongShortAccountRatio", p), ["longShortRatio", "longAccount", "shortAccount"], "timestamp")
    tk = _df(api("/futures/data/takerlongshortRatio", p), ["buySellRatio", "buyVol", "sellVol"], "timestamp")
    fr = _df(api("/fapi/v1/fundingRate", {"symbol": sym, "limit": 100}), ["fundingRate"], "fundingTime")
    return {"k": k, "oi": oi, "ls": ls, "tk": tk, "fr": fr}


def _rubik(path, params, cols, resample_h):
    """Serie de OKX 'rubik' (OI, long/short, taker). Opcional: si falla devuelve vacío."""
    try:
        rows = api_okx(path, params, gap=0.45)
        df = pd.DataFrame(rows).iloc[:, :len(cols) + 1]
        df.columns = ["ts"] + cols
        for c in cols:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df["t"] = pd.to_datetime(pd.to_numeric(df["ts"], errors="coerce"), unit="ms")
        df = df.drop(columns="ts").set_index("t").sort_index()
        if resample_h and 1 < resample_h < 24:
            rs = df.resample("%dh" % resample_h)
            df = rs.sum(min_count=1) if "buyVol" in cols else rs.last()
        return df.dropna(how="all")
    except BloqueoRegional:
        raise
    except Exception:
        return pd.DataFrame()


def bajar_moneda_okx(sym, period):
    inst = okx_inst(sym)
    ccy = sym[:-4]
    h = PERIOD_H[period]
    rows = api_okx("/api/v5/market/candles", {"instId": inst, "bar": OKX_BAR[period], "limit": 220})
    k = pd.DataFrame([r[:6] for r in rows], columns=["t", "o", "h", "l", "c", "v"])
    for c in ("o", "h", "l", "c", "v"):
        k[c] = pd.to_numeric(k[c], errors="coerce")
    k["t"] = pd.to_datetime(pd.to_numeric(k["t"], errors="coerce"), unit="ms")
    k = k.set_index("t").sort_index()

    fr = _df(api_okx("/api/v5/public/funding-rate-history", {"instId": inst, "limit": 100}),
             ["fundingRate"], "fundingTime")
    fn = api_okx("/api/v5/public/funding-rate", {"instId": inst})
    fund_now = float(fn[0]["fundingRate"]) if fn else np.nan

    rp = "1D" if h >= 24 else "1H"
    rh = h if rp == "1H" else None
    oi = _rubik("/api/v5/rubik/stat/contracts/open-interest-volume", {"ccy": ccy, "period": rp},
                ["oiUsd", "volUsd"], rh)
    if not oi.empty:
        oi["sumOpenInterestValue"] = oi["oiUsd"]
        oi["sumOpenInterest"] = oi["oiUsd"]
    ls = _rubik("/api/v5/rubik/stat/contracts/long-short-account-ratio", {"ccy": ccy, "period": rp},
                ["longShortRatio"], rh)
    tk = _rubik("/api/v5/rubik/stat/taker-volume", {"ccy": ccy, "instType": "CONTRACTS", "period": rp},
                ["sellVol", "buyVol"], rh)   # OKX entrega primero ventas y luego compras
    if not tk.empty:
        tk["buySellRatio"] = tk["buyVol"] / tk["sellVol"].replace(0, np.nan)
    return {"k": k, "oi": oi, "ls": ls, "tk": tk, "fr": fr, "fund_now": fund_now}


def bajar_todo(symbols, period, fuente="binance", demo=False, progreso=None):
    raw, errores = {}, {}
    if demo:
        for i, s in enumerate(symbols):
            raw[s] = demo_raw(s, period)
            if progreso:
                progreso((i + 1) / len(symbols))
        return raw, errores
    fn = bajar_moneda if fuente == "binance" else bajar_moneda_okx
    workers = 6 if fuente == "binance" else 3
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fn, s, period): s for s in symbols}
        hechos = 0
        for f in as_completed(futs):
            s = futs[f]
            try:
                raw[s] = f.result()
            except BloqueoRegional:
                for g in futs:
                    g.cancel()
                raise
            except Exception as e:  # moneda sin datos (recién listada, etc.)
                errores[s] = str(e)[:120]
            hechos += 1
            if progreso:
                progreso(hechos / len(futs))
    return raw, errores


# ---------------------------------------------------------------------------
# Métricas y reglas
# ---------------------------------------------------------------------------
def pct_rank(serie, valor):
    s = pd.Series(serie).dropna()
    if len(s) < 10 or pd.isna(valor):
        return np.nan
    return float((s <= valor).mean() * 100)


def metricas(raw, prem, p):
    k = raw["k"]
    if len(k) < 60:
        return None
    lb = max(1, int(round(p["lookback_h"] / PERIOD_H[p["period"]])))
    c = k["c"]
    if len(c) <= lb:
        return None
    px_chg = (c.iloc[-1] / c.iloc[-1 - lb] - 1) * 100
    ema = c.ewm(span=50, adjust=False).mean()
    above = bool(c.iloc[-1] > ema.iloc[-1])
    tr = pd.concat([k["h"] - k["l"], (k["h"] - c.shift()).abs(), (k["l"] - c.shift()).abs()], axis=1).max(axis=1)
    atr = float(tr.ewm(alpha=1 / 14, adjust=False).mean().iloc[-1])

    oi_chg = np.nan
    if not raw["oi"].empty:
        oi = raw["oi"]["sumOpenInterestValue"].dropna()
        if len(oi) > lb and oi.iloc[-1 - lb] > 0:
            oi_chg = (oi.iloc[-1] / oi.iloc[-1 - lb] - 1) * 100

    ls_last, ls_pct = np.nan, np.nan
    if not raw["ls"].empty:
        ls = raw["ls"]["longShortRatio"].dropna()
        if len(ls):
            ls_last = float(ls.iloc[-1])
            ls_pct = pct_rank(ls, ls_last)

    tk_ratio = np.nan
    if not raw["tk"].empty:
        w = raw["tk"].tail(lb)
        if w["sellVol"].sum() > 0:
            tk_ratio = float(w["buyVol"].sum() / w["sellVol"].sum())

    fund_now = raw.get("fund_now")
    if fund_now is None or pd.isna(fund_now):
        fund_now = float(prem["lastFundingRate"]) if prem is not None else np.nan
    interval_h = 8.0
    fund_pct = np.nan
    if not raw["fr"].empty:
        fr = raw["fr"]["fundingRate"].dropna()
        if len(fr) >= 3:
            dif = pd.Series(raw["fr"].index).diff().dropna().median()
            if pd.notna(dif) and dif.total_seconds() > 0:
                interval_h = float(np.clip(dif.total_seconds() / 3600.0, 1, 24))
        fund_pct = pct_rank(fr, fund_now)
    fund_ann = fund_now * (24.0 / interval_h) * 365 * 100 if not pd.isna(fund_now) else np.nan

    basis = np.nan
    if prem is not None and float(prem["indexPrice"]) > 0:
        basis = (float(prem["markPrice"]) / float(prem["indexPrice"]) - 1) * 100

    return {"precio": float(c.iloc[-1]), "px_chg": float(px_chg), "above": above, "atr": atr,
            "oi_chg": oi_chg, "ls": ls_last, "ls_pct": ls_pct, "taker": tk_ratio,
            "fund": fund_now * 100 if not pd.isna(fund_now) else np.nan,
            "fund_ann": fund_ann, "fund_pct": fund_pct, "basis": basis}


def decidir(m, p, btc_bull):
    """Devuelve (recomendación, confianza, puntos_long, puntos_short, razones)."""
    px, oi, fp, lp, tk = m["px_chg"], m["oi_chg"], m["fund_pct"], m["ls_pct"], m["taker"]
    px_up, px_dn = px >= p["px_th"], px <= -p["px_th"]
    oi_up = (not pd.isna(oi)) and oi >= p["oi_th"]
    oi_dn = (not pd.isna(oi)) and oi <= -p["oi_th"]
    crowd_long = (not pd.isna(fp)) and fp >= p["f_hi"]
    crowd_short = (not pd.isna(fp)) and fp <= p["f_lo"]

    L = S = 0
    rl, rs = [], []

    if m["above"]:
        L += 1; rl.append("precio sobre su EMA50")
    else:
        S += 1; rs.append("precio bajo su EMA50")

    if px_up and oi_up:
        L += 1; rl.append("sube con open interest creciente (entra dinero nuevo)")
    if px_dn and oi_up:
        S += 1; rs.append("cae con open interest creciente (entran shorts nuevos)")

    if not pd.isna(tk):
        if tk >= p["tk_bull"]:
            L += 1; rl.append("compras agresivas dominan (taker %.2f)" % tk)
        elif tk <= p["tk_bear"]:
            S += 1; rs.append("ventas agresivas dominan (taker %.2f)" % tk)

    if crowd_long:
        L -= 1; rl.append("(-1) funding alto: longs apiñados")
        if not px_up:
            S += 1; rs.append("longs apiñados sin respaldo del precio")
    if crowd_short:
        S -= 1; rs.append("(-1) funding muy bajo: shorts apiñados")
        if not px_dn:
            L += 1; rl.append("shorts apiñados y el precio no cae")

    if not pd.isna(lp):
        if lp >= p["ls_hi"]:
            S += 1; rs.append("cuentas muy largas (contrario)")
        elif lp <= p["ls_lo"]:
            L += 1; rl.append("cuentas muy cortas (contrario)")

    if btc_bull:
        L += 1; rl.append("régimen de BTC alcista")
    else:
        S += 1; rs.append("régimen de BTC bajista")

    if crowd_short and oi_up and not px_dn:
        L += 1; rl.append("posible short squeeze")
    if crowd_long and (px_dn or oi_dn):
        S += 1; rs.append("longs apiñados empezando a ceder")

    capitulacion = (px <= -2 * p["px_th"]) and (not pd.isna(oi)) and (oi <= -2 * p["oi_th"]) \
        and (not pd.isna(tk)) and tk <= p["tk_bear"]
    evitar_longs = crowd_long and oi_up and not px_up

    razones = []
    if capitulacion:
        rec, conf = "ESPERAR REBOTE", "Media"
        razones = ["caída fuerte con open interest desplomándose y ventas agresivas: posible capitulación; "
                   "no shortear el piso, esperar una vela de confirmación"]
    elif evitar_longs:
        rec, conf = "EVITAR LONGS", "Media"
        razones = ["funding alto con open interest creciente y precio sin subir: longs apiñados, riesgo de caída "
                   "por liquidaciones"]
    elif L >= p["min_pts"] and L - S >= 2:
        rec, conf = "LONG", ("Alta" if L >= p["min_pts"] + 1 else "Media")
        razones = rl
    elif S >= p["min_pts"] and S - L >= 2:
        if crowd_short:
            rec, conf = "ESPERAR", "Baja"
            razones = ["señal bajista, pero los shorts están apiñados: riesgo de squeeze"]
        elif p["solo_long"]:
            rec, conf = "EVITAR / SALIR", ("Alta" if S >= p["min_pts"] + 1 else "Media")
            razones = rs
        else:
            rec, conf = "SHORT", ("Alta" if S >= p["min_pts"] + 1 else "Media")
            razones = rs
    else:
        rec, conf = "ESPERAR", "Baja"
        razones = ["sin confluencia suficiente (LONG %d, SHORT %d)" % (L, S)]
    return rec, conf, max(L, 0), max(S, 0), razones


def plan(rec, m, p):
    """Texto de acción con referencia de stop y tamaño."""
    px, atr = m["precio"], m["atr"]
    if rec in ("LONG", "SHORT") and atr > 0:
        d = p["stop_mult"] * atr
        stop = px - d if rec == "LONG" else px + d
        qty = (p["capital"] * p["riesgo"] / 100.0) / d
        if qty * px > p["capital"] * p["max_lev"]:
            qty = p["capital"] * p["max_lev"] / px
        accion = "COMPRAR (LONG)" if rec == "LONG" else "VENDER EN CORTO (SHORT)"
        return ("%s · referencia %.6g · stop %.6g (%.1f ATR) · tamaño %.6g unidades (≈ %.0f USDT) "
                "arriesgando %.1f%% de %.0f USDT") % (accion, px, stop, p["stop_mult"], qty, qty * px,
                                                        p["riesgo"], p["capital"])
    if rec == "EVITAR LONGS":
        return "No abrir longs nuevos. Si estás largo: subí el stop o reducí tamaño."
    if rec == "EVITAR / SALIR":
        return "No comprar. Si estás largo en esta moneda, considerá reducir o salir."
    if rec == "ESPERAR REBOTE":
        return "No shortear después de una caída tan fuerte. Esperá un cierre de vela alcista antes de considerar un long."
    return "Sin ventaja clara. Esperar."


# ---------------------------------------------------------------------------
# Presentación
# ---------------------------------------------------------------------------
def color_rec(v):
    if v == "LONG":
        return "background-color:#1b5e20;color:white;font-weight:bold"
    if v == "SHORT":
        return "background-color:#b71c1c;color:white;font-weight:bold"
    if v in ("EVITAR LONGS", "EVITAR / SALIR"):
        return "background-color:#e65100;color:white;font-weight:bold"
    if v == "ESPERAR REBOTE":
        return "background-color:#0d47a1;color:white;font-weight:bold"
    return "color:#9e9e9e"


def estilo(df):
    sty = df.style.format({"Precio": "{:,.6g}", "Δ precio %": "{:+.2f}", "Funding %": "{:+.4f}",
                           "Funding anual %": "{:+.1f}", "Funding pct": "{:.0f}", "OI Δ %": "{:+.1f}",
                           "L/S": "{:.2f}", "L/S pct": "{:.0f}", "Taker": "{:.2f}", "Base %": "{:+.3f}",
                           "Vol 24h (M USDT)": "{:,.0f}"}, na_rep="—")
    f = getattr(sty, "map", None) or sty.applymap
    return f(color_rec, subset=["Recomendación"])


def normalizar(txt):
    out = []
    for t in txt.replace("\n", ",").split(","):
        t = t.strip().upper().replace("/", "").replace(":USDT", "").replace("-", "")
        if not t:
            continue
        out.append(t if t.endswith("USDT") else t + "USDT")
    return out


def main():
    st.set_page_config(page_title="SLY | Radar de derivados", layout="wide")
    st.title("SLY | Radar de derivados")
    st.caption("Funding, open interest, ratio long/short, flujo agresivo y base de futuros perpetuos (Binance u OKX). "
               "Herramienta de contexto: no es una recomendación de inversión ni garantiza resultados.")

    demo_env = os.environ.get("SLY_DEMO") == "1"
    with st.sidebar:
        st.header("Configuración")
        demo = st.checkbox("Modo demo (datos sintéticos)", value=demo_env,
                           help="Para ver cómo funciona la app sin conexión. Los datos NO son reales.")
        fuente_sel = st.selectbox("Fuente de datos", ["Automática (Binance → OKX)", "Binance", "OKX"],
                                  help="Binance bloquea las IP de EE.UU. (HTTP 451), típicas de Streamlit Cloud. "
                                       "En Automática la app pasa sola a OKX si Binance la rechaza.")
        period = st.selectbox("Temporalidad", list(PERIOD_H.keys()), index=2)
        lookback_h = st.number_input("Ventana de análisis (horas)", 4, 240, 24, step=4,
                                     help="Para medir cambios de precio, open interest y flujo.")
        top_n = st.slider("Cantidad de monedas (por volumen 24h)", 5, 80, 30)
        min_vol = st.number_input("Volumen 24h mínimo (M USDT)", 0, 5000, 50, step=10)
        custom = st.text_area("Lista propia (opcional)",
                              placeholder="ETH, SOL, BTC/USDT ... Si la completás, reemplaza al ranking por volumen.")
        st.subheader("Umbrales")
        px_th = st.number_input("Movimiento de precio relevante (%)", 0.2, 10.0, 1.0, step=0.1)
        oi_th = st.number_input("Cambio de open interest relevante (%)", 0.5, 20.0, 2.0, step=0.5)
        f_hi = st.slider("Funding 'alto' (percentil)", 60, 99, 85)
        f_lo = st.slider("Funding 'bajo' (percentil)", 1, 40, 15)
        ls_hi = st.slider("Cuentas muy largas (percentil)", 60, 99, 85)
        ls_lo = st.slider("Cuentas muy cortas (percentil)", 1, 40, 15)
        tk_bull = st.number_input("Taker alcista (>=)", 1.0, 1.5, 1.05, step=0.01)
        tk_bear = st.number_input("Taker bajista (<=)", 0.6, 1.0, 0.95, step=0.01)
        min_pts = st.slider("Puntos mínimos para señal", 3, 6, 4)
        st.subheader("Riesgo")
        capital = st.number_input("Capital (USDT)", 10.0, 10_000_000.0, 1000.0, step=100.0)
        riesgo = st.number_input("Riesgo por operación (%)", 0.1, 5.0, 1.0, step=0.1)
        stop_mult = st.number_input("Stop = ATR x", 0.5, 6.0, 2.0, step=0.1)
        max_lev = st.number_input("Apalancamiento máximo", 0.5, 10.0, 1.0, step=0.5)
        solo_long = st.checkbox("Opero solo LONG (spot)", value=False,
                                help="Las señales SHORT se muestran como 'EVITAR / SALIR'.")
        refrescar = st.button("Actualizar datos ahora")

    p = dict(period=period, lookback_h=lookback_h, px_th=px_th, oi_th=oi_th, f_hi=f_hi, f_lo=f_lo,
             ls_hi=ls_hi, ls_lo=ls_lo, tk_bull=tk_bull, tk_bear=tk_bear, min_pts=min_pts,
             capital=capital, riesgo=riesgo, stop_mult=stop_mult, max_lev=max_lev, solo_long=solo_long)

    # --- Universo (con cambio automático de fuente)
    ss = st.session_state
    if refrescar:
        ss.pop("binance_bloqueado", None)
    if demo:
        orden = ["binance"]
    elif fuente_sel == "Binance":
        orden = ["binance"]
    elif fuente_sel == "OKX":
        orden = ["okx"]
    else:
        orden = ["okx"] if ss.get("binance_bloqueado") else ["binance", "okx"]
    uni, fuente, ultimo_error = None, None, None
    for f in orden:
        try:
            uni = listar_universo(f, demo)
            fuente = f
            break
        except BloqueoRegional as e:
            ultimo_error = e
            if f == "binance":
                ss["binance_bloqueado"] = True
        except Exception as e:
            ultimo_error = e
    if uni is None:
        st.error("No pude obtener datos: %s" % ultimo_error)
        if isinstance(ultimo_error, BloqueoRegional):
            st.info("Probá con otra fuente en la barra lateral, o ejecutá la app en tu PC (`streamlit run "
                    "sly_radar_derivados.py`) desde tu conexión de Argentina.")
        st.stop()
    NOMBRE = {"binance": "Binance", "okx": "OKX"}[fuente]
    if demo:
        st.warning("MODO DEMO: datos sintéticos, no reales.")
    elif fuente_sel.startswith("Autom") and fuente == "okx":
        st.info("Binance rechazó la conexión (probablemente por la ubicación del servidor): "
                "uso datos de OKX automáticamente.")
    if fuente == "okx" and not demo:
        st.caption("Fuente: OKX (perpetuos lineales USDT). Open interest, long/short y taker vienen de las "
                   "estadísticas agregadas por moneda de OKX; el historial puede diferir del de Binance.")

    if custom.strip():
        pedidos = normalizar(custom)
        validos = [s for s in pedidos if s in set(uni["symbol"])]
        faltan = [s for s in pedidos if s not in validos]
        if faltan:
            st.warning("No encontré perpetuos USDT en %s para: " % NOMBRE + ", ".join(faltan))
        symbols = validos
    else:
        symbols = uni[uni["quoteVolume"] >= min_vol * 1e6]["symbol"].head(top_n).tolist()
    if not symbols:
        st.warning("No hay monedas para analizar con esos filtros.")
        st.stop()

    # --- Descarga (se reutiliza unos minutos)
    clave = (tuple(symbols), period, demo, fuente)
    vencido = time.time() - ss.get("raw_ts", 0) > TTL_RAW
    if refrescar or ss.get("raw_key") != clave or vencido:
        barra = st.progress(0.0, text="Descargando datos de derivados…")
        try:
            raw, errores = bajar_todo(symbols, period, fuente, demo, lambda x: barra.progress(min(x, 1.0)))
        except BloqueoRegional as e:
            barra.empty()
            st.error(str(e))
            st.stop()
        barra.empty()
        cargar_premium.clear()
        ss.update(raw=raw, raw_err=errores, raw_key=clave, raw_ts=time.time())
    raw, errores = ss["raw"], ss.get("raw_err", {})

    try:
        prem = cargar_premium(tuple(symbols), fuente, demo)
        btc_bull, btc_px = regimen_btc(fuente, demo)
    except Exception as e:
        st.error("No pude leer funding/base actuales: %s" % e)
        st.stop()

    # --- Cálculo
    filas, detalle = [], {}
    vol_map = uni.set_index("symbol")["quoteVolume"].to_dict()
    for s in symbols:
        if s not in raw or s not in prem.index:
            continue
        m = metricas(raw[s], prem.loc[s], p)
        if m is None:
            continue
        rec, conf, L, S, razones = decidir(m, p, btc_bull)
        detalle[s] = (m, rec, conf, L, S, razones)
        filas.append({"Símbolo": s.replace("USDT", ""), "Precio": m["precio"], "Δ precio %": m["px_chg"],
                      "Funding %": m["fund"], "Funding anual %": m["fund_ann"], "Funding pct": m["fund_pct"],
                      "OI Δ %": m["oi_chg"], "L/S": m["ls"], "L/S pct": m["ls_pct"], "Taker": m["taker"],
                      "Base %": m["basis"], "Vol 24h (M USDT)": vol_map.get(s, np.nan) / 1e6,
                      "Tendencia": "▲ sobre EMA50" if m["above"] else "▼ bajo EMA50",
                      "Pts LONG": L, "Pts SHORT": S, "Recomendación": rec, "Confianza": conf, "_sym": s})
    if not filas:
        st.warning("No se pudieron calcular métricas (datos insuficientes).")
        st.stop()
    df = pd.DataFrame(filas)
    orden = {"LONG": 0, "SHORT": 1, "EVITAR LONGS": 2, "EVITAR / SALIR": 2, "ESPERAR REBOTE": 3, "ESPERAR": 4}
    df["_o"] = df["Recomendación"].map(orden).fillna(5)
    df["_f"] = df[["Pts LONG", "Pts SHORT"]].max(axis=1)
    df = df.sort_values(["_o", "_f"], ascending=[True, False]).reset_index(drop=True)

    # --- Resumen del mercado
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Régimen de BTC (SMA200 diaria)", "ALCISTA" if btc_bull else "BAJISTA", "%.0f USDT" % btc_px)
    c2.metric("Funding mediano (percentil)", "%.0f" % df["Funding pct"].median())
    c3.metric("OI Δ mediano", "%+.1f%%" % df["OI Δ %"].median())
    c4.metric("Señales LONG / SHORT", "%d / %d" % ((df["Recomendación"] == "LONG").sum(),
                                                  (df["Recomendación"] == "SHORT").sum()))
    if errores:
        with st.expander("Monedas sin datos suficientes (%d)" % len(errores)):
            st.write(errores)

    # --- Qué hacer ahora
    st.subheader("Qué hacer ahora")
    accionables = df[df["Recomendación"].isin(["LONG", "SHORT", "EVITAR LONGS", "EVITAR / SALIR", "ESPERAR REBOTE"])]
    if accionables.empty:
        st.info("Ninguna moneda tiene confluencia suficiente ahora. Esperar también es una decisión.")
    for _, r in accionables.head(10).iterrows():
        m, rec, conf, L, S, razones = detalle[r["_sym"]]
        with st.expander("%s · %s · confianza %s" % (r["Símbolo"], rec, conf), expanded=rec in ("LONG", "SHORT")):
            st.markdown("**Acción:** " + plan(rec, m, p))
            st.markdown("**Por qué:** " + "; ".join(razones))

    # --- Tabla
    st.subheader("Tabla completa")
    filtro = st.multiselect("Filtrar recomendación", sorted(df["Recomendación"].unique()),
                            default=sorted(df["Recomendación"].unique()))
    vista = df[df["Recomendación"].isin(filtro)].drop(columns=["_sym", "_o", "_f"])
    try:
        st.dataframe(estilo(vista), width="stretch", hide_index=True)
    except TypeError:  # versiones anteriores de Streamlit
        st.dataframe(estilo(vista), use_container_width=True, hide_index=True)
    st.download_button("Descargar CSV", vista.to_csv(index=False).encode("utf-8"),
                       "radar_derivados.csv", "text/csv")

    # --- Detalle por moneda
    st.subheader("Detalle por moneda")
    sel = st.selectbox("Moneda", df["_sym"].tolist(), format_func=lambda x: x.replace("USDT", ""))
    m, rec, conf, L, S, razones = detalle[sel]
    st.markdown("**%s** → %s (confianza %s) · puntos LONG %d / SHORT %d" % (sel, rec, conf, L, S))
    st.markdown("**Acción:** " + plan(rec, m, p))
    st.markdown("**Por qué:** " + "; ".join(razones))
    r = raw[sel]
    g1, g2 = st.columns(2)
    g1.caption("Precio (cierre)")
    g1.line_chart(r["k"]["c"])
    if not r["oi"].empty:
        g2.caption("Open interest (USDT)")
        g2.line_chart(r["oi"]["sumOpenInterestValue"])
    g3, g4, g5 = st.columns(3)
    if not r["fr"].empty:
        g3.caption("Funding rate (historial)")
        g3.line_chart(r["fr"]["fundingRate"] * 100)
    if not r["ls"].empty:
        g4.caption("Ratio long/short de cuentas")
        g4.line_chart(r["ls"]["longShortRatio"])
    if not r["tk"].empty:
        g5.caption("Taker buy/sell ratio")
        g5.line_chart(r["tk"]["buySellRatio"])

    with st.expander("Cómo leer esto"):
        st.markdown(
            "- **Funding percentil alto**: los longs pagan mucho comparado con su historial reciente (longs apiñados). "
            "Bajo: shorts apiñados.\n"
            "- **OI Δ**: sube = entra dinero apalancado; baja = se cierran posiciones.\n"
            "- **Precio y OI**: sube+OI sube = tendencia sana; sube+OI baja = cierre de shorts (débil); "
            "cae+OI sube = entran shorts; cae+OI baja = liquidación de longs (posible capitulación).\n"
            "- **Taker**: >1 dominan compras agresivas, <1 ventas agresivas.\n"
            "- **Base**: mark vs index; muy positiva indica demanda de apalancamiento largo.\n"
            "- **Pts LONG / SHORT**: suma de confluencias. Se exige un mínimo y una diferencia de 2 puntos.\n"
            "- **Stop y tamaño** son una referencia con ATR y riesgo fijo; ajustalos a tu plan.\n"
            "- Las reglas NO están probadas con historial: usalas como contexto, validalas y no operes con plata "
            "que no puedas perder.")


if __name__ == "__main__":
    main()
