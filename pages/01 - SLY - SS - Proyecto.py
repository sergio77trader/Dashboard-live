import streamlit as st
import types
# -*- coding: utf-8 -*-
"""
PROYECTO RETIRO | motor de backtest para cripto (perpetuos) con apalancamiento y liquidación
=====================================================================================
Qué incluye
  * Descarga de velas públicas (Binance USD-M o OKX) con caché en disco, o CSV propio.
  * Motor de backtest que simula: entrada en la apertura de la vela siguiente a la señal, stop por ATR,
    objetivo/trailing opcional, comisiones (taker), slippage, funding, margen aislado, precio de
    liquidación, tamaño por riesgo (% del capital por operación), tope de apalancamiento y notional mínimo.
  * Tres estrategias de ejemplo (tendencia Donchian, cruce de EMAs con ADX, rebote RSI en tendencia).
  * Validación honesta: optimiza SOLO en el tramo de diseño (in-sample) y evalúa en un tramo que el
    optimizador nunca vio (out-of-sample), más Monte Carlo sobre las operaciones.
  * Calculadora de posición (tamaño, apalancamiento efectivo, precio de liquidación).

LIMITES (leer)
  * Un backtest NO garantiza resultados futuros. Un buen resultado in-sample suele ser sobreajuste.
  * Se asume ejecución perfecta al precio de apertura +/- slippage; no modela huecos de liquidez, caídas
    del exchange ni liquidación parcial. Las liquidaciones reales pueden costar más que el margen.
  * Si dos niveles (stop y objetivo) se tocan en la misma vela, se asume el stop (conservador).
"""
import itertools
import math
import os
import time

import numpy as np
import pandas as pd

TF_HOURS = {"15m": 0.25, "30m": 0.5, "1h": 1.0, "2h": 2.0, "4h": 4.0, "6h": 6.0, "12h": 12.0, "1d": 24.0}


class BloqueoRegional(Exception):
    pass


# ---------------------------------------------------------------------------
# Datos
# ---------------------------------------------------------------------------
def _okx_inst(symbol):
    base = symbol[:-4] if symbol.endswith("USDT") else symbol
    return base + "-USDT-SWAP"


def fetch_binance(symbol, tf, start_ms, requests_mod=None):
    import requests as rq
    rq = requests_mod or rq
    url, out, t = "https://fapi.binance.com/fapi/v1/klines", [], int(start_ms)
    while True:
        r = rq.get(url, params=dict(symbol=symbol, interval=tf, startTime=t, limit=1500), timeout=20)
        if r.status_code in (403, 451):
            raise BloqueoRegional("Binance bloqueó el acceso desde esta conexión (HTTP %d)." % r.status_code)
        r.raise_for_status()
        k = r.json()
        if not k:
            break
        out += k
        t = k[-1][0] + 1
        if len(k) < 1500:
            break
        time.sleep(0.15)
    df = pd.DataFrame([x[:6] for x in out], columns=["t", "open", "high", "low", "close", "volume"])
    return _fin(df)[:-1]       # sin la vela en curso


def fetch_okx(symbol, tf, start_ms, requests_mod=None):
    import requests as rq
    rq = requests_mod or rq
    bar = {"1h": "1H", "2h": "2H", "4h": "4H", "6h": "6H", "12h": "12H", "1d": "1D", "15m": "15m", "30m": "30m"}[tf]
    url, out, after = "https://www.okx.com/api/v5/market/history-candles", [], None
    while True:
        prm = dict(instId=_okx_inst(symbol), bar=bar, limit=100)
        if after:
            prm["after"] = after
        r = rq.get(url, params=prm, timeout=20)
        if r.status_code in (403, 451):
            raise BloqueoRegional("OKX bloqueó el acceso desde esta conexión (HTTP %d)." % r.status_code)
        r.raise_for_status()
        j = r.json()
        if str(j.get("code")) != "0":
            raise RuntimeError("OKX: %s" % j.get("msg"))
        k = j["data"]
        if not k:
            break
        out += [x for x in k if str(x[8]) == "1"]
        after = k[-1][0]
        if int(k[-1][0]) <= start_ms or len(k) < 100:
            break
        time.sleep(0.12)
    df = pd.DataFrame([x[:6] for x in out], columns=["t", "open", "high", "low", "close", "volume"])
    df = _fin(df)
    return df[df.index >= pd.to_datetime(start_ms, unit="ms")]


def fetch_kucoin(symbol, tf, start_ms, requests_mod=None):
    """KuCoin spot (API pública, sin clave). Pagina en ventanas de 1500 velas."""
    import requests as rq
    rq = requests_mod or rq
    typ = {"15m": "15min", "30m": "30min", "1h": "1hour", "2h": "2hour", "4h": "4hour", "6h": "6hour", "12h": "12hour", "1d": "1day"}[tf]
    sym = (symbol[:-4] + "-USDT") if symbol.endswith("USDT") else symbol
    step = int(TF_HOURS[tf] * 3600)
    t, now, out = int(start_ms / 1000), int(time.time()), []
    while t < now:
        e = min(t + step * 1500, now)
        r = rq.get("https://api.kucoin.com/api/v1/market/candles",
                   params=dict(symbol=sym, type=typ, startAt=t, endAt=e), timeout=20)
        if r.status_code in (403, 451):
            raise BloqueoRegional("KuCoin bloqueó el acceso desde esta conexión (HTTP %d)." % r.status_code)
        r.raise_for_status()
        j = r.json()
        if str(j.get("code")) != "200000":
            raise RuntimeError("KuCoin: %s" % j.get("msg"))
        # [time(s), open, close, high, low, volume, turnover]
        out += [[int(x[0]) * 1000, x[1], x[3], x[4], x[2], x[5]] for x in j["data"]]
        t = e
        time.sleep(0.2)
    df = pd.DataFrame(out, columns=["t", "open", "high", "low", "close", "volume"])
    return _fin(df)[:-1]


def _fin(df):
    df = df.copy()
    df["t"] = pd.to_datetime(pd.to_numeric(df["t"]), unit="ms")
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.drop_duplicates("t").set_index("t").sort_index().dropna(subset=["close"])


def load_data(source, symbol, tf, years=4, cache_dir="data_retiro", fetchers=None, max_age_h=12):
    """source: 'binance' | 'okx'. Usa caché en disco (CSV) si es reciente."""
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, "%s_%s_%s_%dy.csv" % (source, symbol, tf, years))
    if os.path.exists(path) and (time.time() - os.path.getmtime(path)) / 3600 < max_age_h:
        return pd.read_csv(path, index_col=0, parse_dates=True)
    start = int((pd.Timestamp.utcnow() - pd.Timedelta(days=365 * years)).timestamp() * 1000)
    f = (fetchers or {"binance": fetch_binance, "okx": fetch_okx, "kucoin": fetch_kucoin})[source]
    df = f(symbol, tf, start)
    if len(df) < 300:
        raise ValueError("Pocas velas descargadas (%d)" % len(df))
    df.to_csv(path)
    return df


def synthetic(n=20000, tf="4h", seed=1, tendencia=0.0, vol_anual=0.8, s0=30000.0):
    """Datos sintéticos para probar el sistema. tendencia>0 agrega autocorrelación (momentum)."""
    rng = np.random.default_rng(seed)
    h = TF_HOURS[tf]
    sig = vol_anual / math.sqrt(24 * 365 / h)
    vol = sig * np.exp(rng.normal(0, 0.25, n).cumsum() * 0.05)       # volatilidad que cambia
    e = rng.normal(0, 1, n) * vol
    r = np.zeros(n)
    for i in range(1, n):
        r[i] = tendencia * r[i - 1] + e[i]
    c = s0 * np.exp(np.cumsum(r))
    o = np.r_[c[0], c[:-1]]
    rng2 = np.random.default_rng(seed + 1)
    hi = np.maximum(o, c) * (1 + np.abs(rng2.normal(0, sig * 0.4, n)))
    lo = np.minimum(o, c) * (1 - np.abs(rng2.normal(0, sig * 0.4, n)))
    idx = pd.date_range(end=pd.Timestamp.today().floor("h"), periods=n, freq="%dh" % max(int(h), 1) if h >= 1 else "15min")
    return pd.DataFrame({"open": o, "high": hi, "low": lo, "close": c, "volume": rng2.uniform(1e3, 1e4, n)}, index=idx)


# ---------------------------------------------------------------------------
# Indicadores
# ---------------------------------------------------------------------------
def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def rma(s, n):
    return s.ewm(alpha=1.0 / n, adjust=False).mean()


def tr_f(h, l, c):
    return pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)


def atr_f(df, n=14):
    return rma(tr_f(df["high"], df["low"], df["close"]), n)


def rsi_f(c, n=14):
    d = c.diff()
    up, dn = rma(d.clip(lower=0), n), rma((-d).clip(lower=0), n)
    r = 100 - 100 / (1 + up / dn.replace(0, np.nan))
    return r.where(dn > 0, 100.0).fillna(50.0)


def adx_f(df, n=14):
    h, l, c = df["high"], df["low"], df["close"]
    up, dn = h.diff(), -l.diff()
    plus = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=h.index)
    minus = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=h.index)
    atr = rma(tr_f(h, l, c), n)
    pdi, mdi = 100 * rma(plus, n) / atr, 100 * rma(minus, n) / atr
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return rma(dx.fillna(0), n)


# ---------------------------------------------------------------------------
# Estrategias: devuelven señales calculadas SOLO con datos hasta el cierre de cada vela
# ---------------------------------------------------------------------------
def _pack(df, enter, xl, xs, stop_mult, tgt_mult=None, trail_mult=None, max_bars=None, atr_len=14):
    return dict(enter=np.asarray(enter, dtype=int), exit_long=np.asarray(xl, dtype=bool),
                exit_short=np.asarray(xs, dtype=bool), atr=atr_f(df, atr_len).to_numpy(float),
                stop_mult=float(stop_mult), tgt_mult=tgt_mult, trail_mult=trail_mult, max_bars=max_bars)


def strat_donchian(df, N=55, M=20, stop_mult=2.5, regime=True, shorts=True):
    c, h, l = df["close"], df["high"], df["low"]
    hiN, loN = h.rolling(N).max().shift(1), l.rolling(N).min().shift(1)
    hiM, loM = h.rolling(M).max().shift(1), l.rolling(M).min().shift(1)
    reg = ema(c, 200)
    up = (c > hiN) & ((c > reg) | (not regime))
    dn = (c < loN) & ((c < reg) | (not regime)) & bool(shorts)
    enter = np.where(up, 1, np.where(dn, -1, 0))
    return _pack(df, enter, c < loM, c > hiM, stop_mult)


def strat_ema_adx(df, fast=20, slow=100, adx_thr=22, stop_mult=3.0, regime=True, shorts=True):
    c = df["close"]
    ef, es, reg, adx = ema(c, fast), ema(c, slow), ema(c, 200), adx_f(df)
    cu = (ef > es) & (ef.shift() <= es.shift())
    cd = (ef < es) & (ef.shift() >= es.shift())
    up = cu & (adx > adx_thr) & ((c > reg) | (not regime))
    dn = cd & (adx > adx_thr) & ((c < reg) | (not regime)) & bool(shorts)
    enter = np.where(up, 1, np.where(dn, -1, 0))
    return _pack(df, enter, ef < es, ef > es, stop_mult)


def strat_rsi_dip(df, rsi_len=14, lo=30, exit_rsi=55, stop_mult=2.5, max_bars=30, shorts=False):
    c = df["close"]
    r, reg = rsi_f(c, rsi_len), ema(c, 200)
    up = (r < lo) & (c > reg)
    dn = (r > 100 - lo) & (c < reg) & bool(shorts)
    enter = np.where(up, 1, np.where(dn, -1, 0))
    return _pack(df, enter, r > exit_rsi, r < 100 - exit_rsi, stop_mult, max_bars=max_bars)


def _ha(df):
    """Heikin Ashi recursivo igual que el Pine: haOpen[0]=(o+c)/2, luego (haOpen[1]+haClose[1])/2."""
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    hc = (o + h + l + c) / 4
    ho = np.empty(len(df))
    ho[0] = (o[0] + c[0]) / 2
    for i in range(1, len(df)):
        ho[i] = (ho[i - 1] + hc[i - 1]) / 2
    return hc, ho


def _dema(s, n):
    e1 = ema(s, n)
    return 2 * e1 - ema(e1, n)


def strat_sly_ss(df, ema_fast=52, ema_slow=260, bear_longs=True, fast=12, slow=26, sig=9,
                 rsi_len=14, smooth=5, stop_mult=3.0):
    """Port de 'SLY - ESTRATEGIA - SS' (solo largos). Entrada: HA vira a verde + hist MACD(DEMA) sube + RSI(DEMA) sube.
    Salida: HA rojo + hist baja + RSI baja. Se agrega un stop ATR (el original no tiene), necesario para dimensionar y liquidar."""
    c = df["close"]
    hc, ho = _ha(df)
    green = pd.Series(hc > ho, index=df.index)
    macd = _dema(c, fast) - _dema(c, slow)
    hist = macd - ema(macd, sig)
    rs = _dema(rsi_f(c, rsi_len), smooth)
    bull = ema(c, ema_fast) > ema(c, ema_slow)
    auth = bull | bool(bear_longs)
    flip = green & ~green.shift(1, fill_value=False)
    entry = auth & flip & (hist > hist.shift()) & (rs > rs.shift())
    exit_ = (~green) & (hist < hist.shift()) & (rs < rs.shift())
    return _pack(df, np.where(entry, 1, 0), exit_, np.zeros(len(df), bool), stop_mult)


def strat_supertrend(df, period=10, mult=3.0, stop_mult=3.0, regime=True, shorts=True):
    """Supertrend: sigue la tendencia con bandas de ATR; cambia de lado cuando el precio las cruza."""
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    a = atr_f(df, period).to_numpy(float)
    hl2 = (h + l) / 2
    ub, lb = hl2 + mult * a, hl2 - mult * a
    n = len(c)
    d = np.ones(n, int)
    fu, fl = ub.copy(), lb.copy()
    for i in range(1, n):
        if not np.isfinite(a[i]):
            continue
        fu[i] = ub[i] if (ub[i] < fu[i - 1] or c[i - 1] > fu[i - 1]) else fu[i - 1]
        fl[i] = lb[i] if (lb[i] > fl[i - 1] or c[i - 1] < fl[i - 1]) else fl[i - 1]
        d[i] = 1 if c[i] > fu[i - 1] else (-1 if c[i] < fl[i - 1] else d[i - 1])
    d = pd.Series(d, index=df.index)
    reg = ema(df["close"], 200)
    up = (d == 1) & (d.shift() == -1) & ((df["close"] > reg) | (not regime))
    dn = (d == -1) & (d.shift() == 1) & ((df["close"] < reg) | (not regime)) & bool(shorts)
    return _pack(df, np.where(up, 1, np.where(dn, -1, 0)), d == -1, d == 1, stop_mult)


def strat_squeeze(df, bb_len=20, bb_k=2.0, ventana=120, pct=20, recien=6, stop_mult=2.5, regime=True, shorts=False):
    """Squeeze de volatilidad: tras una compresión (ancho de Bollinger entre los más bajos de `ventana` velas),
    entra cuando el precio rompe la banda. Sale al volver a la media."""
    c = df["close"]
    m = c.rolling(bb_len).mean()
    sd = c.rolling(bb_len).std(ddof=0)
    up_b, lo_b = m + bb_k * sd, m - bb_k * sd
    bw = (up_b - lo_b) / m
    rank = bw.rolling(ventana).apply(lambda x: (x[:-1] < x[-1]).mean() * 100, raw=True)
    sq = (rank <= pct).astype(float).rolling(recien).max() > 0
    reg = ema(c, 200)
    up = (c > up_b) & sq.shift(1, fill_value=False) & ((c > reg) | (not regime))
    dn = (c < lo_b) & sq.shift(1, fill_value=False) & ((c < reg) | (not regime)) & bool(shorts)
    return _pack(df, np.where(up, 1, np.where(dn, -1, 0)), c < m, c > m, stop_mult)


def strat_tsmom(df, lookback=180, z_thr=0.5, stop_mult=3.0, regime=True, shorts=False):
    """Momentum de serie temporal: entra cuando el retorno de las últimas `lookback` velas, medido en
    unidades de volatilidad (z), cruza `z_thr`. Sale cuando el momentum se da vuelta (z < 0). Opera poco."""
    c = df["close"]
    r = np.log(c).diff()
    z = np.log(c / c.shift(lookback)) / (r.rolling(lookback).std() * math.sqrt(lookback))
    reg = ema(c, 200)
    up = (z > z_thr) & (z.shift() <= z_thr) & ((c > reg) | (not regime))
    dn = (z < -z_thr) & (z.shift() >= -z_thr) & ((c < reg) | (not regime)) & bool(shorts)
    return _pack(df, np.where(up, 1, np.where(dn, -1, 0)), z < 0, z > 0, stop_mult)


STRATS = {
    "Tendencia Donchian (Turtle)": dict(
        fn=strat_donchian, defaults=dict(N=55, M=20, stop_mult=2.5, regime=True, shorts=True),
        grid=dict(N=[20, 40, 55, 80], M=[10, 20], stop_mult=[2.0, 3.0], regime=[True, False])),
    "Cruce de EMAs + ADX": dict(
        fn=strat_ema_adx, defaults=dict(fast=20, slow=100, adx_thr=22, stop_mult=3.0, regime=True, shorts=True),
        grid=dict(fast=[10, 20, 30], slow=[50, 100], adx_thr=[18, 25], stop_mult=[2.5, 3.5])),
    "SLY SS (HA + MACD + RSI DEMA)": dict(
        fn=strat_sly_ss, defaults=dict(ema_fast=52, ema_slow=260, bear_longs=True, fast=12, slow=26, sig=9, rsi_len=14, smooth=5, stop_mult=3.0),
        grid=dict(ema_fast=[34, 52], bear_longs=[True, False], smooth=[3, 5], stop_mult=[2.0, 3.0, 5.0])),
    "Supertrend": dict(
        fn=strat_supertrend, defaults=dict(period=10, mult=3.0, stop_mult=3.0, regime=True, shorts=True),
        grid=dict(period=[7, 10, 14], mult=[2.0, 3.0, 4.0], stop_mult=[2.5, 4.0], regime=[True, False])),
    "Squeeze de volatilidad (Bollinger)": dict(
        fn=strat_squeeze, defaults=dict(bb_len=20, bb_k=2.0, ventana=120, pct=20, recien=6, stop_mult=2.5, regime=True, shorts=False),
        grid=dict(bb_len=[20, 30], pct=[15, 30], recien=[3, 8], stop_mult=[2.0, 3.0], regime=[True, False])),
    "Momentum de tendencia (TSMOM)": dict(
        fn=strat_tsmom, defaults=dict(lookback=180, z_thr=0.5, stop_mult=3.0, regime=True, shorts=False),
        grid=dict(lookback=[90, 180, 360], z_thr=[0.0, 0.5, 1.0], stop_mult=[2.5, 4.0], regime=[True, False])),
    "Rebote RSI en tendencia": dict(
        fn=strat_rsi_dip, defaults=dict(rsi_len=14, lo=30, exit_rsi=55, stop_mult=2.5, max_bars=30, shorts=False),
        grid=dict(rsi_len=[7, 14], lo=[25, 30, 35], exit_rsi=[50, 60], stop_mult=[2.0, 3.0])),
}


# ---------------------------------------------------------------------------
# Calculadora de posición
# ---------------------------------------------------------------------------
def liq_price(entry, side, lev, maint=0.005):
    """Precio de liquidación (margen aislado). side: +1 largo, -1 corto."""
    return entry * (1 - side * (1.0 / lev - maint))


def calc_posicion(capital, riesgo_pct, entrada, stop, lev_max=5.0, fee=0.0005, maint=0.005, min_notional=5.0):
    side = 1 if stop < entrada else -1
    dist = abs(entrada - stop)
    riesgo_usd = capital * riesgo_pct / 100.0
    qty = riesgo_usd / dist
    notional = qty * entrada
    topeado = False
    if notional > capital * lev_max:
        notional, topeado = capital * lev_max, True
        qty = notional / entrada
    liq = liq_price(entrada, side, lev_max, maint)
    out = dict(lado="LARGO" if side == 1 else "CORTO", qty=qty, notional=notional, margen=notional / lev_max,
               lev_efectivo=notional / capital, liq=liq, dist_stop_pct=dist / entrada * 100,
               dist_liq_pct=abs(entrada - liq) / entrada * 100, perdida_stop=qty * dist,
               comision_ida_vuelta=2 * notional * fee, topeado=topeado, avisos=[])
    if notional < min_notional:
        out["avisos"].append("El notional (USD %.2f) es menor al mínimo habitual (~USD %.0f): no se puede abrir." % (notional, min_notional))
    if (side == 1 and liq >= stop) or (side == -1 and liq <= stop):
        out["avisos"].append("¡El precio de liquidación queda ANTES del stop! Bajá el apalancamiento o achicá el tamaño.")
    if topeado:
        out["avisos"].append("El tamaño quedó limitado por el apalancamiento máximo: arriesgás menos que lo pedido.")
    if out["comision_ida_vuelta"] > 0.25 * out["perdida_stop"]:
        out["avisos"].append("Las comisiones son más del 25%% de lo que arriesgás: con stops tan cortos los costos se comen la ventaja.")
    return out


# ---------------------------------------------------------------------------
# Motor de backtest
# ---------------------------------------------------------------------------
CFG0 = dict(capital=100.0, risk_pct=2.0, max_lev=5.0, fee=0.0005, slip=0.0002, funding_8h=0.0001,
            maint=0.005, min_notional=5.0, bar_hours=4.0, dd_stop=None)


def backtest(df, sig, cfg, i0=0, i1=None):
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    n = len(df)
    i1 = n if i1 is None else i1
    enter, xl, xs, atr = sig["enter"], sig["exit_long"], sig["exit_short"], sig["atr"]
    smult, tmult, trail, maxb = sig["stop_mult"], sig.get("tgt_mult"), sig.get("trail_mult"), sig.get("max_bars")
    fee, slip, L, maint = cfg["fee"], cfg["slip"], cfg["max_lev"], cfg["maint"]
    fund = cfg["funding_8h"] * cfg["bar_hours"] / 8.0
    risk = cfg["risk_pct"] / 100.0
    cash = float(cfg["capital"])
    eq = np.full(n, np.nan)
    pos, qty, entry, stop, tgt, liq, margin, notional = 0, 0.0, 0.0, 0.0, None, 0.0, 0.0, 0.0
    ent_i, risk_amt, eq0, fee_in, fund_paid = 0, 0.0, 0.0, 0.0, 0.0
    trades, skipped, liqs, fees_total, peak, halted = [], 0, 0, 0.0, cash, None

    def cerrar(i, px, motivo, liquidado=False):
        nonlocal cash, pos, fees_total, fund_paid, liqs
        if liquidado:
            cash -= margin
            pnl = -(margin) - fee_in - fund_paid
            liqs += 1
        else:
            gross = pos * (px - entry) * qty
            fee_out = qty * px * fee
            cash += gross - fee_out
            fees_total += fee_out
            pnl = gross - fee_out - fee_in - fund_paid
        trades.append(dict(entrada=df.index[ent_i], salida=df.index[i], lado="LARGO" if pos == 1 else "CORTO",
                           precio_entrada=entry, precio_salida=px, qty=qty, notional=notional, pnl=pnl,
                           ret=pnl / eq0 if eq0 > 0 else 0.0, R=pnl / risk_amt if risk_amt > 0 else 0.0,
                           velas=i - ent_i, motivo=motivo))
        pos = 0

    for i in range(i0, i1):
        # ---- 1) gap en la apertura contra la posición
        if pos != 0:
            if (pos == 1 and o[i] <= liq) or (pos == -1 and o[i] >= liq):
                cerrar(i, liq, "liquidación", True)
            elif (pos == 1 and o[i] <= stop) or (pos == -1 and o[i] >= stop):
                cerrar(i, o[i] * (1 - pos * slip), "stop (gap)")
        # ---- 2) salidas por señal / tiempo en la apertura
        prev = i - 1
        if pos != 0 and prev >= 0:
            rev = enter[prev] == -pos
            sal = (pos == 1 and xl[prev]) or (pos == -1 and xs[prev])
            tmo = maxb is not None and (i - ent_i) >= maxb
            if sal or tmo or rev:
                cerrar(i, o[i] * (1 - pos * slip), "reversa" if rev and not (sal or tmo) else ("tiempo" if tmo and not sal else "señal de salida"))
        # ---- 3) entrada en la apertura
        if pos == 0 and prev >= 0 and enter[prev] != 0 and halted is None:
            side = int(enter[prev])
            a = atr[prev]
            if np.isfinite(a) and a > 0 and cash > 0:
                px = o[i] * (1 + side * slip)
                sd = smult * a
                # apalancamiento efectivo: la liquidación debe quedar al menos 20% más lejos que el stop
                Lu = max(1.0, min(L, 1.0 / (1.2 * sd / px + maint)))
                q = cash * risk / sd
                nt = q * px
                if nt > cash * Lu:
                    nt = cash * Lu
                    q = nt / px
                if nt < cfg["min_notional"]:
                    skipped += 1
                else:
                    pos, qty, entry, notional = side, q, px, nt
                    margin = nt / Lu
                    stop = px - side * sd
                    tgt = px + side * tmult * a if tmult else None
                    liq = liq_price(px, side, Lu, maint)
                    fee_in = nt * fee
                    cash -= fee_in
                    fees_total += fee_in
                    ent_i, eq0, risk_amt, fund_paid = i, cash + fee_in, cash * risk, 0.0
        # ---- 4) intravela: stop / liquidación / objetivo
        if pos != 0:
            if pos == 1:
                disp = max(stop, liq)
                if l[i] <= disp:
                    if stop >= liq:
                        cerrar(i, stop * (1 - slip), "stop")
                    else:
                        cerrar(i, liq, "liquidación", True)
                elif tgt is not None and h[i] >= tgt:
                    cerrar(i, tgt * (1 - slip), "objetivo")
            else:
                disp = min(stop, liq)
                if h[i] >= disp:
                    if stop <= liq:
                        cerrar(i, stop * (1 + slip), "stop")
                    else:
                        cerrar(i, liq, "liquidación", True)
                elif tgt is not None and l[i] <= tgt:
                    cerrar(i, tgt * (1 + slip), "objetivo")
        # ---- 5) cierre de vela: funding, trailing, equity
        if pos != 0:
            fp = pos * notional * fund
            cash -= fp
            fund_paid += fp
            if trail:
                if pos == 1:
                    stop = max(stop, h[i] - trail * atr[i])
                else:
                    stop = min(stop, l[i] + trail * atr[i])
            eq[i] = cash + pos * (c[i] - entry) * qty
        else:
            eq[i] = cash
        peak = max(peak, eq[i])
        if halted is None:
            if eq[i] < cfg["min_notional"] / L:
                halted = "capital agotado"
            elif cfg.get("dd_stop") and eq[i] <= peak * (1 - cfg["dd_stop"]) and pos == 0:
                halted = "freno por drawdown"
    if pos != 0:
        cerrar(i1 - 1, c[i1 - 1], "fin de datos")
        eq[i1 - 1] = cash
    s = pd.Series(eq, index=df.index).iloc[i0:i1].ffill()
    tr = pd.DataFrame(trades)
    return dict(equity=s, trades=tr, stats=estadisticas(s, tr, cfg, df, i0, i1, skipped, liqs, fees_total, halted))


def estadisticas(eq, tr, cfg, df, i0, i1, skipped, liqs, fees, halted):
    cap = cfg["capital"]
    fin = float(eq.iloc[-1])
    anios = max((eq.index[-1] - eq.index[0]).total_seconds() / (365.25 * 86400), 1e-9)
    dd = (1 - eq / eq.cummax()).max()
    ret = eq.pct_change().dropna()
    ppy = 24 * 365 / cfg["bar_hours"]
    sharpe = float(ret.mean() / ret.std() * math.sqrt(ppy)) if len(ret) > 2 and ret.std() > 0 else np.nan
    bh = float(df["close"].iloc[i1 - 1] / df["open"].iloc[i0] - 1)
    st = dict(capital_final=fin, retorno_pct=(fin / cap - 1) * 100, cagr_pct=((fin / cap) ** (1 / anios) - 1) * 100 if fin > 0 else -100.0,
              max_dd_pct=float(dd * 100), sharpe=sharpe, operaciones=len(tr), liquidaciones=liqs, omitidas=skipped,
              comisiones=fees, buy_hold_pct=bh * 100, anios=anios, freno=halted or "")
    if len(tr):
        g, p = tr.loc[tr["pnl"] > 0, "pnl"].sum(), -tr.loc[tr["pnl"] < 0, "pnl"].sum()
        st.update(aciertos_pct=float((tr["pnl"] > 0).mean() * 100), profit_factor=float(g / p) if p > 0 else np.inf,
                  R_medio=float(tr["R"].mean()), tiempo_mercado_pct=float(tr["velas"].sum() / max(len(eq), 1) * 100))
    else:
        st.update(aciertos_pct=np.nan, profit_factor=np.nan, R_medio=np.nan, tiempo_mercado_pct=0.0)
    return st


# ---------------------------------------------------------------------------
# Validación: in-sample / out-of-sample + Monte Carlo
# ---------------------------------------------------------------------------
def _score(st):
    if st["operaciones"] < 20 or not np.isfinite(st["retorno_pct"]):
        return -np.inf
    return st["cagr_pct"] / max(st["max_dd_pct"], 5.0)


def grid_search(df, name, cfg, i0, i1, grid=None, base=None):
    spec = STRATS[name]
    grid = grid or spec["grid"]
    keys = list(grid)
    rows = []
    for vals in itertools.product(*[grid[k] for k in keys]):
        prm = dict(spec["defaults"])
        prm.update(dict(zip(keys, vals)))
        res = backtest(df, spec["fn"](df, **prm), cfg, i0, i1)
        st = res["stats"]
        rows.append(dict(params=prm, score=_score(st), **{k: st[k] for k in ("retorno_pct", "cagr_pct", "max_dd_pct", "operaciones", "profit_factor", "liquidaciones")}))
    return pd.DataFrame(rows).sort_values("score", ascending=False).reset_index(drop=True)


def monte_carlo(rets, capital, n_trades=100, paths=3000, seed=0):
    rets = np.asarray(rets, float)
    if len(rets) < 10:
        return None
    rng = np.random.default_rng(seed)
    r = rng.choice(rets, size=(paths, n_trades), replace=True)
    eq = np.cumprod(1 + np.clip(r, -1, None), axis=1)
    pk = np.maximum.accumulate(eq, axis=1)
    dd = (1 - eq / pk).max(axis=1)
    fin = eq[:, -1] * capital
    return dict(mediana=float(np.median(fin)), p10=float(np.percentile(fin, 10)), p90=float(np.percentile(fin, 90)),
                p_perdida=float((fin < capital).mean()), p_mitad=float((fin < capital * 0.5).mean()),
                p_dd50=float((dd > 0.5).mean()), dd_mediano=float(np.median(dd) * 100), n_trades=n_trades)


def validar(df, name, cfg, split=0.7, top=5):
    n = len(df)
    cut = int(n * split)
    warm = 300                                       # velas de calentamiento para los indicadores
    tabla = grid_search(df, name, cfg, warm, cut)
    mejor = tabla.iloc[0]
    spec = STRATS[name]
    sig = spec["fn"](df, **mejor["params"])
    oos = backtest(df, sig, cfg, cut, n)
    ins = backtest(df, sig, cfg, warm, cut)
    # cómo le fue en OOS a las mejores 5 combinaciones de IS (¿es robusto o solo suerte?)
    top_oos = []
    for _, r in tabla.head(top).iterrows():
        s = backtest(df, spec["fn"](df, **r["params"]), cfg, cut, n)["stats"]
        top_oos.append(dict(params=r["params"], is_retorno=r["retorno_pct"], oos_retorno=s["retorno_pct"], oos_pf=s["profit_factor"], oos_dd=s["max_dd_pct"], oos_ops=s["operaciones"]))
    cfg2 = dict(cfg, fee=cfg["fee"] * 2, slip=cfg["slip"] * 2)
    oos2 = backtest(df, sig, cfg2, cut, n)["stats"]
    mc = monte_carlo(oos["trades"]["ret"].to_numpy() if len(oos["trades"]) else [], cfg["capital"])
    anual = oos["equity"].resample("YE").last().pct_change().dropna() * 100 if len(oos["equity"]) > 50 else pd.Series(dtype=float)
    return dict(tabla=tabla, mejor=mejor["params"], ins=ins, oos=oos, top_oos=pd.DataFrame(top_oos), mc=mc,
                combinaciones=len(tabla), corte=df.index[cut], anual=anual, split=split,
                veredicto=veredicto(oos["stats"], mc, pd.DataFrame(top_oos), len(tabla), oos2))


def veredicto(st, mc, top_oos, ncomb, st_costos2=None):
    chk = []
    chk.append(("Operaciones fuera de muestra ≥ 40", st["operaciones"] >= 40, "%d operaciones" % st["operaciones"]))
    chk.append(("Retorno fuera de muestra positivo", st["retorno_pct"] > 0, "%+.1f%%" % st["retorno_pct"]))
    pf = st["profit_factor"]
    chk.append(("Profit factor fuera de muestra ≥ 1,3", bool(np.isfinite(pf) and pf >= 1.3), "%.2f" % pf if np.isfinite(pf) else "n/d"))
    chk.append(("Caída máxima fuera de muestra ≤ 40%", st["max_dd_pct"] <= 40, "%.0f%%" % st["max_dd_pct"]))
    chk.append(("Sin liquidaciones", st["liquidaciones"] == 0, "%d" % st["liquidaciones"]))
    if st_costos2 is not None:
        chk.append(("Sigue ganando con costos x2 (comisión y slippage)", st_costos2["retorno_pct"] > 0, "%+.1f%%" % st_costos2["retorno_pct"]))
    if len(top_oos):
        pos = int((top_oos["oos_retorno"] > 0).sum())
        chk.append(("Robusto: ≥ 3 de las 5 mejores combinaciones ganan fuera de muestra", pos >= 3, "%d de %d" % (pos, len(top_oos))))
    if mc:
        chk.append(("Monte Carlo: probabilidad de perder capital ≤ 25%", mc["p_perdida"] <= 0.25, "%.0f%%" % (mc["p_perdida"] * 100)))
        chk.append(("Monte Carlo: probabilidad de caída > 50% ≤ 15%", mc["p_dd50"] <= 0.15, "%.0f%%" % (mc["p_dd50"] * 100)))
    ok = sum(1 for _, b, _ in chk if b)
    if ok == len(chk):
        txt = "PASA las pruebas: hay indicios de ventaja, pero NO es una garantía. Siguiente paso: 2-3 meses en demo."
    elif ok >= len(chk) - 2:
        txt = "DUDOSA: pasa algunas pruebas y falla otras. No la uses con dinero real todavía."
    else:
        txt = "NO PASA: no hay evidencia de ventaja fuera de muestra. Probablemente el buen resultado en el diseño era sobreajuste."
    return dict(checks=chk, ok=ok, total=len(chk), texto=txt, combinaciones=ncomb)


R = types.SimpleNamespace(**{k: v for k, v in globals().items() if not k.startswith("__")})

# -*- coding: utf-8 -*-
"""PROYECTO RETIRO | Laboratorio de backtest cripto con apalancamiento. Ejecutar: streamlit run retiro_app.py"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

st.set_page_config(page_title="Proyecto Retiro", layout="wide")
st.title("Proyecto Retiro · Laboratorio de backtest")
st.caption("Herramienta de investigación. Un backtest no garantiza nada: con apalancamiento se puede perder todo el capital.")

SIMBOLOS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT"]
with st.sidebar:
    st.header("Datos")
    fuente = st.selectbox("Fuente", ["okx", "kucoin", "binance", "demo (sintético)"])
    simbolo = st.selectbox("Par", SIMBOLOS)
    tf = st.selectbox("Temporalidad", ["1h", "2h", "4h", "6h", "12h", "1d"], index=2)
    years = st.slider("Años de historia", 1, 6, 4)
    st.header("Capital y riesgo")
    capital = st.number_input("Capital (USD)", 20.0, 1e7, 100.0, 10.0)
    risk = st.slider("Riesgo por operación (% del capital)", 0.25, 10.0, 2.0, 0.25)
    lev = st.slider("Apalancamiento máximo", 1.0, 20.0, 5.0, 0.5)
    dd_on = st.checkbox("Freno por drawdown", False)
    dd = st.slider("Frenar al caer (%)", 10, 80, 40) / 100 if dd_on else None
    st.header("Costos")
    fee = st.number_input("Comisión taker (%)", 0.0, 0.5, 0.05, 0.01) / 100
    slip = st.number_input("Slippage (%)", 0.0, 0.5, 0.02, 0.01) / 100
    fund = st.number_input("Funding cada 8h (%)", -0.05, 0.1, 0.01, 0.005) / 100

cfg = dict(R.CFG0, capital=capital, risk_pct=risk, max_lev=lev, fee=fee, slip=slip, funding_8h=fund,
           bar_hours=R.TF_HOURS[tf], dd_stop=dd)


@st.cache_data(show_spinner=False, ttl=3600)
def datos(fuente, simbolo, tf, years):
    if fuente.startswith("demo"):
        return R.synthetic(int(24 * 365 * years / R.TF_HOURS[tf]), tf, seed=sum(map(ord, simbolo)), tendencia=0.1), ""
    orden = [fuente] + [x for x in ("okx", "kucoin", "binance") if x != fuente]
    err = []
    for f in orden:
        try:
            return R.load_data(f, simbolo, tf, years), ("" if f == fuente else "Se usó %s porque %s falló." % (f, fuente))
        except Exception as e:
            err.append("%s: %s" % (f, e))
    raise RuntimeError(" | ".join(err))


t1, t2, t3, t4 = st.tabs(["Calculadora", "Backtest", "Validación (la prueba de verdad)", "Multi-par"])

with t1:
    st.subheader("¿Cuánto comprar y dónde está mi liquidación?")
    c1, c2, c3 = st.columns(3)
    ent = c1.number_input("Precio de entrada", 0.0001, 1e9, 60000.0)
    stp = c2.number_input("Stop", 0.0001, 1e9, 57000.0)
    c3.write("")
    p = R.calc_posicion(capital, risk, ent, stp, lev, fee, cfg["maint"], cfg["min_notional"])
    a, b, c, d = st.columns(4)
    a.metric("Lado", p["lado"]); b.metric("Tamaño (USD)", "%.2f" % p["notional"]); c.metric("Margen", "%.2f" % p["margen"])
    d.metric("Apalanc. efectivo", "x%.2f" % p["lev_efectivo"])
    a, b, c, d = st.columns(4)
    a.metric("Pérdida si toca stop", "USD %.2f" % p["perdida_stop"]); b.metric("Distancia al stop", "%.2f%%" % p["dist_stop_pct"])
    c.metric("Precio de liquidación", "%.4f" % p["liq"]); d.metric("Distancia a liquidación", "%.1f%%" % p["dist_liq_pct"])
    st.write("Comisiones ida y vuelta: USD %.3f" % p["comision_ida_vuelta"])
    for w in p["avisos"]:
        st.warning(w)

with t2:
    nombre = st.selectbox("Estrategia", list(R.STRATS), key="e2")
    spec = R.STRATS[nombre]
    prm = {}
    cols = st.columns(len(spec["defaults"]))
    for col, (k, v) in zip(cols, spec["defaults"].items()):
        if isinstance(v, bool):
            prm[k] = col.checkbox(k, v, key="b" + k)
        elif isinstance(v, int):
            prm[k] = int(col.number_input(k, 1, 500, v, key="b" + k))
        else:
            prm[k] = float(col.number_input(k, 0.5, 10.0, float(v), 0.5, key="b" + k))
    if st.button("Correr backtest", type="primary"):
        try:
            with st.spinner("Descargando y simulando..."):
                df, aviso = datos(fuente, simbolo, tf, years)
                res = R.backtest(df, spec["fn"](df, **prm), cfg, 300)
            if aviso:
                st.info(aviso)
            s = res["stats"]
            m = st.columns(6)
            m[0].metric("Capital final", "%.2f" % s["capital_final"], "%+.1f%%" % s["retorno_pct"])
            m[1].metric("Caída máx.", "%.0f%%" % s["max_dd_pct"]); m[2].metric("Operaciones", s["operaciones"])
            m[3].metric("Profit factor", "%.2f" % s["profit_factor"] if np.isfinite(s["profit_factor"]) else "n/d")
            m[4].metric("Liquidaciones", s["liquidaciones"]); m[5].metric("Buy & hold", "%+.0f%%" % s["buy_hold_pct"])
            if s["freno"]:
                st.warning("Simulación detenida: " + s["freno"])
            fig, ax = plt.subplots(2, 1, figsize=(10, 6), sharex=True, gridspec_kw=dict(height_ratios=[3, 1]))
            eq = res["equity"]
            ax[0].plot(eq.index, eq.values, label="Estrategia")
            bh = capital * df["close"].reindex(eq.index) / df["open"].iloc[300]
            ax[0].plot(bh.index, bh.values, label="Comprar y mantener (x1)", alpha=.6)
            ax[0].set_yscale("log"); ax[0].legend(); ax[0].set_ylabel("USD (log)")
            ax[1].fill_between(eq.index, -(1 - eq / eq.cummax()) * 100, color="tab:red", alpha=.5); ax[1].set_ylabel("Drawdown %")
            st.pyplot(fig)
            if len(res["trades"]):
                st.dataframe(res["trades"].round(4), use_container_width=True)
        except Exception as e:
            st.error("No se pudo correr: %s" % e)

with t3:
    st.write("Optimiza **solo** el 70% inicial y juzga con el 30% final, que el optimizador nunca vio. Si no pasa acá, no sirve.")
    nombre3 = st.selectbox("Estrategia", list(R.STRATS), key="e3")
    if st.button("Validar", type="primary"):
        try:
            with st.spinner("Optimizando y validando..."):
                df, aviso = datos(fuente, simbolo, tf, years)
                v = R.validar(df, nombre3, cfg)
            if aviso:
                st.info(aviso)
            vd = v["veredicto"]
            (st.success if vd["ok"] == vd["total"] else st.warning if vd["ok"] >= vd["total"] - 2 else st.error)(
                "%s  (%d de %d pruebas)" % (vd["texto"], vd["ok"], vd["total"]))
            st.table(pd.DataFrame([(a, "OK" if b else "FALLA", c) for a, b, c in vd["checks"]], columns=["Prueba", "Resultado", "Dato"]))
            st.write("Mejores parámetros (diseño): `%s` · combinaciones probadas: %d · corte: %s" % (v["mejor"], v["combinaciones"], v["corte"].date()))
            c1, c2 = st.columns(2)
            c1.write("**Diseño (in-sample)**"); c1.json({k: (round(x, 2) if isinstance(x, float) else x) for k, x in v["ins"]["stats"].items()})
            c2.write("**Fuera de muestra**"); c2.json({k: (round(x, 2) if isinstance(x, float) else x) for k, x in v["oos"]["stats"].items()})
            fig, ax = plt.subplots(figsize=(10, 3.5))
            ax.plot(v["ins"]["equity"], label="Diseño"); ax.plot(v["oos"]["equity"], label="Fuera de muestra"); ax.legend(); ax.set_yscale("log")
            st.pyplot(fig)
            st.write("**¿Las 5 mejores combinaciones sobreviven fuera de muestra?**")
            st.dataframe(v["top_oos"].round(2), use_container_width=True)
            if v["mc"]:
                m = v["mc"]
                st.write("**Monte Carlo (100 operaciones, 3000 caminos):** mediana USD %.0f · p10 %.0f · p90 %.0f · prob. perder capital %.0f%% · prob. caída >50%% %.0f%%"
                         % (m["mediana"], m["p10"], m["p90"], m["p_perdida"] * 100, m["p_dd50"] * 100))
            st.caption("Ojo: cuantas más estrategias/pares pruebes, más probable que alguno pase por casualidad. Exigí que pase en varios pares.")
        except Exception as e:
            st.error("No se pudo validar: %s" % e)

with t4:
    st.write("Corre la validación de una estrategia en varios pares. Si solo pasa en uno, probablemente fue casualidad.")
    nombre4 = st.selectbox("Estrategia", list(R.STRATS), key="e4")
    elegidos = st.multiselect("Pares", SIMBOLOS, default=SIMBOLOS)
    if st.button("Validar en todos los pares", type="primary") and elegidos:
        filas, barra = [], st.progress(0.0)
        for j, sym in enumerate(elegidos):
            try:
                df, _ = datos(fuente, sym, tf, years)
                v = R.validar(df, nombre4, cfg)
                s, vd = v["oos"]["stats"], v["veredicto"]
                filas.append(dict(Par=sym, Veredicto=vd["texto"].split(":")[0], Pruebas="%d/%d" % (vd["ok"], vd["total"]),
                                  Operaciones=s["operaciones"], Retorno_pct=round(s["retorno_pct"], 1),
                                  Profit_factor=round(s["profit_factor"], 2) if np.isfinite(s["profit_factor"]) else None,
                                  Caida_max_pct=round(s["max_dd_pct"], 1), Buy_hold_pct=round(s["buy_hold_pct"], 1)))
            except Exception as e:
                filas.append(dict(Par=sym, Veredicto="ERROR: %s" % e))
            barra.progress((j + 1) / len(elegidos))
        tabla = pd.DataFrame(filas)
        st.dataframe(tabla, use_container_width=True)
        okn = sum(1 for f in filas if f.get("Veredicto") == "PASA")
        dud = sum(1 for f in filas if f.get("Veredicto") == "DUDOSA")
        msg = "%d pares PASAN, %d DUDOSOS, de %d probados." % (okn, dud, len(filas))
        if okn >= max(2, len(filas) * 0.5):
            st.success(msg + " Pasa en la mayoría: es una señal más fuerte que un solo par.")
        elif okn >= 1:
            st.warning(msg + " Pasa solo en algunos: puede ser casualidad o depender del activo.")
        else:
            st.error(msg + " No hay ventaja consistente.")
