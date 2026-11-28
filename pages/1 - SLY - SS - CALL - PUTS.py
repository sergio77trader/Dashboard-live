# -*- coding: utf-8 -*-
"""
SLY | RADAR DE OPCIONES  (Streamlit)
=====================================================================
Para cada acción/ETF de tu lista (la de tu Signal Monitor, por lotes) muestra:
  1) SEÑAL TÉCNICA CALL / PUT (mismo sistema de 5 puntos que el Pine "SLY | Opciones General")
  2) CONTEXTO DE OPCIONES: put/call, volatilidad implícita vs realizada, movimiento esperado,
     strikes con más open interest, actividad inusual, resultados antes del vencimiento
  3) ENTRADA RECOMENDADA: qué contrato, a qué precio límite, cuántos contratos, stop y objetivo
     de referencia sobre la acción, y fecha límite de salida
  4) GRÁFICOS: velas con las entradas históricas y la entrada actual (entrada/stop/objetivo), y
     open interest por strike.

DATOS: yfinance (gratis, con demora). Opciones de EE.UU. de las acciones que respaldan tus CEDEARs.

IMPORTANTE
  * Es una herramienta de CONTEXTO y apoyo a la decisión. No garantiza resultados. La "tasa de
    acierto" histórica se mide sobre la ACCIÓN (no sobre la opción) y con pocas operaciones.
  * Los datos de yfinance son demorados y, en opciones poco líquidas, pueden ser erróneos:
    verificá siempre bid/ask en tu broker antes de operar.
  * Comprar opciones: la pérdida máxima es la prima pagada. Vender opciones puede perder mucho más
    (esta app NO recomienda ventas).

EJECUTAR
    pip install streamlit pandas numpy yfinance matplotlib
    streamlit run sly_opciones_radar.py
"""
import math
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

try:
    import yfinance as yf
except Exception:  # se avisa en pantalla; el modo demo funciona igual
    yf = None

TICKERS = sorted(set([
    "AAL", "AAP", "AAPL", "AAPU", "ABBV", "ABCL", "ABEV", "ABNB", "ABSI", "ABT", "ACN", "ACWI", "ADBE",
    "ADI", "ADM", "ADP", "AFRM", "AGNT", "AIQ", "ALAB", "AMAT", "AMC", "AMD", "AMGN", "AMZN", "AMZU",
    "AMZY", "ANET", "ANF", "AOK", "AOM", "APLD", "APLY", "APP", "ARGT", "ARKK", "ARM", "ASML", "ASPN",
    "ASTS", "AUR", "AVGO", "AVY", "AXON", "AXP", "B", "BA", "BABA", "BAC", "BAP", "BB", "BBAI", "BBAR",
    "BBD", "BG", "BIDU", "BIIB", "BIL", "BIOX", "BITI", "BITO", "BITX", "BK", "BKCH", "BKNG", "BKR",
    "BLDR", "BLK", "BLOK", "BMA", "BMNR", "BMRN", "BMY", "BN", "BND", "BNKK", "BOTZ", "BP", "BSV",
    "BVN", "BX", "BYND", "C", "CAT", "CCL", "CDNS", "CEG", "CELH", "CEPU", "CGC", "CL", "CLOV",
    "CMCSA", "CME", "CMG", "COIN", "COMP", "CONY", "COO", "COST", "CRCL", "CRESY", "CRM", "CRWD",
    "CSCO", "CVNA", "CVS", "CVX", "DAL", "DAPP", "DASH", "DAVA", "DBC", "DDOG", "DE", "DELL", "DGRO",
    "DHI", "DHR", "DIA", "DIS", "DJT", "DLTR", "DOCU", "DOW", "DPZ", "DUK", "DUOL", "DXYZ", "EA",
    "EAT", "EBAY", "ECH", "EDN", "EEM", "EETH", "EIX", "EL", "ELF", "EMB", "ENPH", "ENZL", "ETSY",
    "EVTL", "EWA", "EWJ", "EWS", "EWT", "EWW", "EWY", "EWZ", "F", "FAS", "FAZ", "FBL", "FDX", "FEZ",
    "FIG", "FISV", "FLIN", "FNGU", "FSLR", "FWONK", "FXI", "FXY", "GAUZ", "GD", "GDDY", "GDX", "GE",
    "GEHC", "GGAL", "GLD", "GLOB", "GM", "GME", "GOOGL", "GOVT", "GPN", "GPRK", "GRAB", "GRWG", "GS",
    "GTLB", "HAL", "HD", "HDV", "HELO", "HERO", "HIMS", "HLT", "HMC", "HOG", "HON", "HOOD", "HPE",
    "HRZN", "HSBC", "HSY", "HUBS", "HUT", "HYFM", "HYG", "IAU", "IBIT", "IBM", "ICE", "ICF", "IEF",
    "IEI", "IEO", "IFS", "IGPT", "IIPR", "IJH", "IJR", "INBS", "INDA", "INTC", "INTU", "IONQ", "IREN",
    "IRS", "ISRG", "ITA", "ITUB", "IWF", "IWM", "IYR", "JD", "JEPI", "JEPQ", "JMIA", "JNJ", "JOBY",
    "JPM", "KBH", "KDP", "KHC", "KLAC", "KMB", "KO", "KODK", "KULR", "LABU", "LAES", "LCID", "LEN",
    "LIN", "LLY", "LMND", "LMT", "LODE", "LOMA", "LOW", "LRCX", "LULU", "LUV", "MA", "MAGS", "MANU",
    "MAR", "MARA", "MCD", "MCHI", "MCO", "MDB", "MDLZ", "MELI", "META", "MKC", "MKL", "MMM", "MMSI",
    "MNST", "MO", "MRK", "MRNA", "MRVL", "MS", "MSFT", "MSFU", "MSI", "MSTR", "MSTY", "MTUM", "MU",
    "MUB", "NEE", "NEM", "NET", "NFLX", "NIO", "NKE", "NOC", "NOW", "NTES", "NU", "NVDA", "NVDL",
    "NVO", "NWTG", "O", "OKLO", "OMC", "ONON", "OPAD", "OPEN", "ORCL", "OSCR", "OTLY", "OWNB", "OXY",
    "PAGS", "PAM", "PANW", "PATH", "PBR", "PCAR", "PDBA", "PDD", "PEP", "PFE", "PFF", "PG", "PHO",
    "PINS", "PL", "PLBY", "PLTR", "PM", "POOL", "PSQ", "PSX", "PTON", "PYPL", "PYPY", "QBTS", "QCOM",
    "QNRX", "QQQ", "QQQM", "QSI", "QYLD", "RACE", "RCAT", "RCL", "RDDT", "REK", "RGTI", "RIOT", "RKLB",
    "RMAX", "RTX", "RYDE", "SATL", "SBET", "SBUX", "SCHD", "SCHF", "SCHH", "SCHW", "SCHX", "SEDG",
    "SETH", "SGOV", "SH", "SHEL", "SHOP", "SHY", "SLB", "SLV", "SMCI", "SMMT", "SNA", "SNAP", "SNOW",
    "SO", "SOFI", "SONY", "SOS", "SOUN", "SOXL", "SOXS", "SOXX", "SPGI", "SPMO", "SPOT", "SPXL",
    "SPXS", "SPY", "SPYD", "SPYG", "SQQQ", "SSO", "STLA", "STZ", "SUPV", "SVCO", "SVXY", "SWK", "SYM",
    "T", "TBF", "TBT", "TBX", "TEAM", "TECL", "TEM", "TGS", "TGT", "TLH", "TLRY", "TLT", "TM", "TMDX",
    "TMF", "TMO", "TMQ", "TMUS", "TNA", "TQQQ", "TS", "TSLA", "TSLL", "TSM", "TTEK", "TTT", "TTWO",
    "TWLO", "TX", "TXN", "TXRH", "UBER", "UGL", "UL", "ULTA", "UMAC", "UNCY", "UNH", "UNP", "UPRO",
    "UPS", "URA", "URBN", "URTH", "USO", "UUP", "UUUU", "V", "VALE", "VB", "VBR", "VEA", "VEEE",
    "VEGI", "VGIT", "VGT", "VHT", "VIG", "VIST", "VIXY", "VNQ", "VO", "VOO", "VRT", "VSCO", "VT",
    "VTI", "VTV", "VUG", "VWO", "VXUS", "VYM", "VZ", "WBD", "WFC", "WM", "WMT", "WST", "XLE", "XLF",
    "XLI", "XLK", "XLP", "XLRE", "XLV", "XLY", "XOM", "XP", "XPEV", "XYZ", "YBIT", "YINN", "YPF",
    "ZETA", "ZM"]))

# ---------------------------------------------------------------------------
# Matemática de opciones (Black-Scholes, solo para delta y para el modo demo)
# ---------------------------------------------------------------------------
def _ncdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def bs_price(S, K, T, r, sigma, call=True):
    if T <= 0 or sigma <= 0:
        return max(S - K, 0.0) if call else max(K - S, 0.0)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if call:
        return S * _ncdf(d1) - K * math.exp(-r * T) * _ncdf(d2)
    return K * math.exp(-r * T) * _ncdf(-d2) - S * _ncdf(-d1)


def bs_delta(S, K, T, r, sigma, call=True):
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return np.nan
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    return _ncdf(d1) if call else _ncdf(d1) - 1.0


# ---------------------------------------------------------------------------
# Indicadores y señal (misma lógica que el Pine "SLY | Opciones General")
# ---------------------------------------------------------------------------
def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def rma(s, n):
    return s.ewm(alpha=1.0 / n, adjust=False).mean()


def rsi_f(c, n=14):
    d = c.diff()
    up, dn = rma(d.clip(lower=0), n), rma((-d).clip(lower=0), n)
    rs = up / dn.replace(0, np.nan)
    r = 100 - 100 / (1 + rs)
    r = r.where(dn > 0, 100.0)
    return r.fillna(50.0)


def true_range(h, l, c):
    return pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)


def dmi(h, l, c, n=14):
    up, dn = h.diff(), -l.diff()
    plus = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=h.index)
    minus = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=h.index)
    atr = rma(true_range(h, l, c), n)
    pdi = 100 * rma(plus, n) / atr
    mdi = 100 * rma(minus, n) / atr
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return pdi, mdi, rma(dx.fillna(0), n)


def indicadores(df, spy, p):
    d = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    d["Volume"] = d["Volume"].fillna(0)
    c, h, l, o, v = d["Close"], d["High"], d["Low"], d["Open"], d["Volume"]
    d["ef"], d["es"], d["el"] = ema(c, 20), ema(c, 50), ema(c, 200)
    d["dip"], d["dim"], d["adx"] = dmi(h, l, c, 14)
    d["rsi"] = rsi_f(c, 14)
    d["atr"] = rma(true_range(h, l, c), 14)
    vavg = v.rolling(20).mean()
    vol_hi = (vavg > 0) & (v > vavg * 1.2)
    hi_n = h.rolling(20).max().shift(1)
    lo_n = l.rolling(20).min().shift(1)

    bull = [c > d["el"], d["ef"] > d["es"], (d["adx"] > 18) & (d["dip"] > d["dim"]),
            (d["rsi"] > 55) & (d["rsi"] < 75), (c > hi_n) | (vol_hi & (c > o) & (c > d["ef"]))]
    bear = [c < d["el"], d["ef"] < d["es"], (d["adx"] > 18) & (d["dim"] > d["dip"]),
            (d["rsi"] < 45) & (d["rsi"] > 25), (c < lo_n) | (vol_hi & (c < o) & (c < d["ef"]))]
    d["bull"] = sum(x.astype(int) for x in bull)
    d["bear"] = sum(x.astype(int) for x in bear)

    mk_bull = pd.Series(True, index=d.index)
    mk_bear = pd.Series(True, index=d.index)
    if p["use_mkt"] and spy is not None and len(spy) > 210:
        sc = spy["Close"]
        se = ema(sc, 200)
        mk_bull = (sc.shift(1) > se.shift(1)).reindex(d.index, method="ffill").fillna(False).astype(bool)
        mk_bear = (sc.shift(1) < se.shift(1)).reindex(d.index, method="ffill").fillna(False).astype(bool)
    d["mk_bull"], d["mk_bear"] = mk_bull, mk_bear
    ms = p["min_score"]
    d["call_sig"] = bool(p["allow_call"]) & (d["bull"] >= ms) & (d["bull"] > d["bear"]) & d["mk_bull"]
    d["put_sig"] = bool(p["allow_put"]) & (d["bear"] >= ms) & (d["bear"] > d["bull"]) & d["mk_bear"]
    return d


def simular(d, p):
    """Opera la señal sobre la ACCIÓN: entra en la apertura de la vela siguiente a la señal,
    stop/objetivo por ATR (si ambos se tocan en la misma vela, se asume el stop) y salida por tiempo.
    Devuelve (operaciones, señal_pendiente_en_la_última_vela, operación_abierta)."""
    o, h, l, c = (d[k].to_numpy(float) for k in ("Open", "High", "Low", "Close"))
    atr = d["atr"].to_numpy(float)
    call, put = d["call_sig"].to_numpy(bool), d["put_sig"].to_numpy(bool)
    n = len(d)
    sm, tm, mb, cd = p["stop_mult"], p["tgt_mult"], int(p["max_bars"]), int(p["cooldown"])
    trades, abierta = [], None
    last_exit, i = -10 ** 6, 210
    while i < n - 1:
        if i - last_exit < cd:
            i += 1
            continue
        side = 1 if call[i] else (-1 if put[i] else 0)
        if side == 0 or not np.isfinite(atr[i]) or atr[i] <= 0:
            i += 1
            continue
        ent, px, a = i + 1, o[i + 1], atr[i]
        stop, tgt = px - side * sm * a, px + side * tm * a
        exit_i = exit_px = reason = None
        for j in range(ent, min(ent + mb, n)):
            if side == 1:
                if o[j] <= stop:
                    exit_i, exit_px, reason = j, o[j], "stop"
                elif l[j] <= stop:
                    exit_i, exit_px, reason = j, stop, "stop"
                elif h[j] >= tgt:
                    exit_i, exit_px, reason = j, tgt, "objetivo"
            else:
                if o[j] >= stop:
                    exit_i, exit_px, reason = j, o[j], "stop"
                elif h[j] >= stop:
                    exit_i, exit_px, reason = j, stop, "stop"
                elif l[j] <= tgt:
                    exit_i, exit_px, reason = j, tgt, "objetivo"
            if exit_i is not None:
                break
            if j == ent + mb - 1:
                exit_i, exit_px, reason = j, c[j], "tiempo"
                break
        tr = dict(side=side, sig=i, ent=ent, px=float(px), stop=float(stop), tgt=float(tgt), atr=float(a))
        if exit_i is None:       # sigue abierta al final de los datos
            tr.update(exit=None, exit_px=None, reason="abierta", ret=float(side * (c[-1] / px - 1) * 100))
            abierta = tr
            break
        tr.update(exit=int(exit_i), exit_px=float(exit_px), reason=reason,
                  ret=float(side * (exit_px / px - 1) * 100))
        trades.append(tr)
        last_exit = exit_i
        i = exit_i + 1
    pendiente = 0
    if abierta is None and (n - 1 - last_exit) >= cd and np.isfinite(atr[-1]) and atr[-1] > 0:
        pendiente = 1 if call[-1] else (-1 if put[-1] else 0)
    return trades, pendiente, abierta


# ---------------------------------------------------------------------------
# Opciones: contexto y elección de contrato
# ---------------------------------------------------------------------------
def _num(df, cols):
    out = df.copy()
    for c in cols:
        out[c] = pd.to_numeric(out.get(c, np.nan), errors="coerce")
    out["volume"] = out["volume"].fillna(0)
    out["openInterest"] = out["openInterest"].fillna(0)
    return out


def contexto_opciones(opt, spot, hv20, p):
    cols = ["strike", "lastPrice", "bid", "ask", "volume", "openInterest", "impliedVolatility"]
    calls, puts = _num(opt["calls"], cols), _num(opt["puts"], cols)
    strikes = np.array(sorted(set(calls["strike"].dropna()) | set(puts["strike"].dropna())), float)
    if len(strikes) == 0:
        return None
    k_atm = float(strikes[np.argmin(np.abs(strikes - spot))])

    def mid(row):
        b, a = row.get("bid", np.nan), row.get("ask", np.nan)
        if np.isfinite(b) and np.isfinite(a) and b > 0 and a > 0:
            return (a + b) / 2
        lp = row.get("lastPrice", np.nan)
        return lp if np.isfinite(lp) and lp > 0 else np.nan

    c_atm = calls[calls["strike"] == k_atm]
    p_atm = puts[puts["strike"] == k_atm]
    ivs = [float(x) for x in list(c_atm["impliedVolatility"]) + list(p_atm["impliedVolatility"])
           if np.isfinite(x) and 0.05 < x < 4.0]
    iv_atm = float(np.mean(ivs)) if ivs else np.nan
    mids = []
    if len(c_atm):
        mids.append(mid(c_atm.iloc[0]))
    if len(p_atm):
        mids.append(mid(p_atm.iloc[0]))
    straddle = float(np.nansum(mids)) if len(mids) == 2 and not any(np.isnan(mids)) else np.nan
    em_pct = straddle / spot * 100 if np.isfinite(straddle) else np.nan

    cv, pv = float(calls["volume"].sum()), float(puts["volume"].sum())
    co, po = float(calls["openInterest"].sum()), float(puts["openInterest"].sum())
    pc_vol = pv / cv if cv > 0 else np.nan
    pc_oi = po / co if co > 0 else np.nan

    near = lambda df: df[(df["strike"] >= spot * 0.8) & (df["strike"] <= spot * 1.2)]
    top_c = near(calls).nlargest(3, "openInterest")
    top_p = near(puts).nlargest(3, "openInterest")
    inusual = []
    for lado, df in (("C", calls), ("P", puts)):
        x = df[(df["volume"] >= 300) & (df["openInterest"] > 0) & (df["volume"] >= 3 * df["openInterest"])]
        for _, r in x.nlargest(2, "volume").iterrows():
            inusual.append("%s %g (vol %d vs OI %d)" % (lado, r["strike"], r["volume"], r["openInterest"]))
    iv_hv = iv_atm / hv20 if np.isfinite(iv_atm) and hv20 and hv20 > 0 else np.nan
    return dict(calls=calls, puts=puts, k_atm=k_atm, iv_atm=iv_atm, straddle=straddle, em_pct=em_pct,
                pc_vol=pc_vol, pc_oi=pc_oi, top_c=list(top_c["strike"]), top_p=list(top_p["strike"]),
                inusual=inusual, iv_hv=iv_hv, exp=opt["exp"], dte=int(opt["dte"]))


def elegir_contrato(ctx, lado, spot, p):
    """Contrato líquido con delta más cercano al objetivo. lado: 1=CALL, -1=PUT."""
    df = ctx["calls"] if lado == 1 else ctx["puts"]
    d = df[(df["bid"] > 0) & (df["ask"] > 0) & (df["openInterest"] >= p["min_oi"])
           & (df["impliedVolatility"] > 0.05) & (df["impliedVolatility"] < 4.0)].copy()
    if d.empty:
        return None
    d["mid"] = (d["bid"] + d["ask"]) / 2
    d["spread"] = (d["ask"] - d["bid"]) / d["mid"] * 100
    T = max(ctx["dte"], 1) / 365.0
    d["delta"] = [bs_delta(spot, k, T, p["rf"], s, lado == 1) for k, s in zip(d["strike"], d["impliedVolatility"])]
    d = d[(d["spread"] <= p["max_spread"]) & (d["mid"] >= 0.05)].dropna(subset=["delta"])
    # evita strikes lejanos "baratos": el delta debe quedar cerca del objetivo
    d = d[(d["delta"].abs() >= max(0.15, p["delta_t"] - 0.20)) & (d["delta"].abs() <= p["delta_t"] + 0.25)]
    if d.empty:
        return None
    d["dist"] = (d["delta"].abs() - p["delta_t"]).abs()
    r = d.sort_values(["dist", "openInterest"], ascending=[True, False]).iloc[0]
    return dict(strike=float(r["strike"]), bid=float(r["bid"]), ask=float(r["ask"]), mid=float(r["mid"]),
                spread=float(r["spread"]), delta=float(r["delta"]), iv=float(r["impliedVolatility"]),
                oi=int(r["openInterest"]), vol=int(r["volume"]))


def hv20_de(d):
    r = np.log(d["Close"]).diff().dropna().tail(20)
    return float(r.std() * math.sqrt(252)) if len(r) >= 15 else np.nan


# ---------------------------------------------------------------------------
# Análisis de una acción
# ---------------------------------------------------------------------------
def analizar(sym, raw, spy, p):
    df = raw["hist"]
    if df is None or len(df) < 230:
        return None
    ind = indicadores(df, spy, p)
    trades, pend, abierta = simular(ind, p)
    n = len(ind)
    last = ind.iloc[-1]
    spot, atr = float(last["Close"]), float(last["atr"])
    hv = hv20_de(ind)

    cerradas = [t for t in trades]
    n_tr = len(cerradas)
    win = (sum(1 for t in cerradas if t["ret"] > 0) / n_tr * 100) if n_tr else np.nan
    avg = float(np.mean([t["ret"] for t in cerradas])) if n_tr else np.nan

    estado, lado, activa = "ESPERAR", 0, None
    if abierta is not None:
        estado, lado, activa = "VIGENTE", abierta["side"], abierta
    elif pend != 0:
        estado, lado = "ENTRADA NUEVA", pend
        px = spot
        activa = dict(side=lado, ent=n - 1, px=px, stop=px - lado * p["stop_mult"] * atr,
                      tgt=px + lado * p["tgt_mult"] * atr, atr=atr, reason="nueva")

    ctx, ctr, alertas = None, None, []
    opt = raw.get("opt")
    if opt is not None and (estado != "ESPERAR" or not p["only_signal_opts"]):
        ctx = contexto_opciones(opt, spot, hv, p)
    lado_ctx = lado if lado != 0 else (1 if last["bull"] >= last["bear"] else -1)
    if ctx is not None and estado != "ESPERAR":
        ctr = elegir_contrato(ctx, lado, spot, p)

    earn = raw.get("earn")
    if ctx is not None and earn is not None:
        try:
            e = pd.Timestamp(earn)
            if pd.Timestamp.today().normalize() <= e <= pd.Timestamp(ctx["exp"]):
                alertas.append("resultados el %s (antes del vencimiento)" % e.strftime("%d/%m"))
        except Exception:
            pass
    if ctx is not None:
        if np.isfinite(ctx["iv_hv"]) and ctx["iv_hv"] > p["iv_rich"]:
            alertas.append("opciones caras (IV %.1fx la volatilidad real)" % ctx["iv_hv"])
        if np.isfinite(ctx["pc_oi"]) and ctx["pc_oi"] > 1.5:
            alertas.append("mucha protección comprada (P/C OI %.2f)" % ctx["pc_oi"])
        if np.isfinite(ctx["pc_oi"]) and ctx["pc_oi"] < 0.5:
            alertas.append("euforia en calls (P/C OI %.2f)" % ctx["pc_oi"])
        if ctx["inusual"]:
            alertas.append("actividad inusual: " + ", ".join(ctx["inusual"][:2]))

    rec, conf, plan = "ESPERAR", "-", "Sin confluencia suficiente: esperar."
    pts = int(last["bull"]) if lado >= 0 else int(last["bear"])
    nombre = "CALL" if lado == 1 else "PUT"
    if estado == "VIGENTE":
        dias = n - 1 - abierta["ent"]
        rec, conf = "NO PERSEGUIR (señal %s vigente)" % nombre, "-"
        plan = ("Señal %s vigente desde hace %d velas (rinde %+.1f%% sobre la acción). No entres tarde: "
                "esperá una nueva entrada. Si ya estás dentro, referencia stop %.2f / objetivo %.2f.") % (
                    nombre, dias, abierta["ret"], abierta["stop"], abierta["tgt"])
    elif estado == "ENTRADA NUEVA":
        stop, tgt = activa["stop"], activa["tgt"]
        niveles = "Referencia sobre la acción: entrada ≈ %.2f, stop %.2f (%.1f ATR), objetivo %.2f (%.1f ATR)." % (
            spot, stop, p["stop_mult"], tgt, p["tgt_mult"])
        if ctx is None:
            rec, conf = "SEÑAL %s (sin datos de opciones)" % nombre, "Baja"
            plan = "Hay señal técnica pero no pude leer la cadena de opciones. " + niveles
        elif ctr is None:
            rec, conf = "SEÑAL %s: OPCIÓN ILÍQUIDA" % nombre, "Baja"
            plan = ("Hay señal técnica, pero no hay un contrato líquido (OI ≥ %d y spread ≤ %d%%) en el "
                    "vencimiento %s. Evitá opciones; si querés operarla, hacelo con la acción/CEDEAR. %s") % (
                        p["min_oi"], p["max_spread"], ctx["exp"], niveles)
        else:
            prima = ctr["ask"]
            presup = p["capital"] * p["riesgo"] / 100.0
            nc = int(presup // (prima * 100))
            be = ctr["strike"] + prima if lado == 1 else ctr["strike"] - prima
            sal = (pd.Timestamp(ctx["exp"]) - pd.Timedelta(days=max(7, int(round(ctx["dte"] / 3))))).strftime("%d/%m")
            cara = np.isfinite(ctx["iv_hv"]) and ctx["iv_hv"] > p["iv_rich"]
            earn_in = any("resultados" in a for a in alertas)
            if cara:
                rec = "%s CARO: esperar o usar spread" % nombre
            else:
                rec = "COMPRAR %s" % nombre
            conf = "Alta" if (pts >= 5 and not cara and not earn_in) else ("Baja" if (cara or earn_in) else "Media")
            tam = ("%d contrato(s) ≈ USD %.0f arriesgando como máximo la prima" % (nc, nc * prima * 100)) if nc >= 1 else \
                  ("1 contrato cuesta USD %.0f y supera tu presupuesto de riesgo (USD %.0f)" % (prima * 100, presup))
            plan = ("%s %s vence %s · strike %g · precio límite ≈ %.2f (bid %.2f / ask %.2f, spread %.0f%%) · delta %.2f · "
                    "IV %.0f%% · OI %d · 1 contrato ≈ USD %.0f. Tamaño: %s. Punto de equilibrio al vencimiento: %.2f. "
                    "%s Salir a más tardar el %s (antes de que el tiempo erosione la prima).") % (
                        "COMPRAR" if not cara else "EVALUAR", nombre + " " + sym, ctx["exp"], ctr["strike"], ctr["mid"],
                        ctr["bid"], ctr["ask"], ctr["spread"], ctr["delta"], ctr["iv"] * 100, ctr["oi"], prima * 100,
                        tam, be, niveles, sal)

    fila = {
        "Símbolo": sym, "Estado": estado, "Recomendación": rec, "Confianza": conf,
        "Pts CALL": int(last["bull"]), "Pts PUT": int(last["bear"]), "Precio": spot,
        "ATR %": atr / spot * 100, "IV ATM %": (ctx["iv_atm"] * 100) if ctx else np.nan,
        "HV20 %": hv * 100 if np.isfinite(hv) else np.nan, "IV/HV": ctx["iv_hv"] if ctx else np.nan,
        "Mov. esperado %": ctx["em_pct"] if ctx else np.nan, "P/C vol": ctx["pc_vol"] if ctx else np.nan,
        "P/C OI": ctx["pc_oi"] if ctx else np.nan, "Vence": ctx["exp"] if ctx else "—",
        "DTE": ctx["dte"] if ctx else np.nan, "Strike sug.": ctr["strike"] if ctr else np.nan,
        "Prima (ask)": ctr["ask"] if ctr else np.nan, "Delta": ctr["delta"] if ctr else np.nan,
        "Spread %": ctr["spread"] if ctr else np.nan, "Señales previas": n_tr,
        "% acierto (acción)": win, "Ret. medio % (acción)": avg,
        "Alertas": " · ".join(alertas) if alertas else "",
    }
    return dict(fila=fila, ind=ind, trades=trades, abierta=abierta, activa=activa, ctx=ctx, ctr=ctr,
                plan=plan, lado=lado, estado=estado)


# ---------------------------------------------------------------------------
# Gráficos (matplotlib)
# ---------------------------------------------------------------------------
VERDE, ROJO, GRIS = "#1b8a3a", "#c62828", "#888888"


def fig_precio(sym, res, barras=160, chico=False):
    ind, trades, act = res["ind"], res["trades"], res["activa"]
    n = len(ind)
    a0 = max(0, n - barras)
    w = ind.iloc[a0:]
    x = np.arange(a0, n)
    fig, ax = plt.subplots(figsize=(5.2, 3.0) if chico else (11, 5.2), dpi=100)
    up = (w["Close"] >= w["Open"]).to_numpy()
    cols = np.where(up, VERDE, ROJO)
    ax.vlines(x, w["Low"], w["High"], colors=cols, linewidth=0.8, zorder=2)
    cuerpo = (w["Close"] - w["Open"]).abs().to_numpy()
    cuerpo = np.where(cuerpo == 0, w["Close"].to_numpy() * 1e-4, cuerpo)
    ax.bar(x, cuerpo, bottom=np.minimum(w["Open"], w["Close"]), width=0.65, color=cols, zorder=3)
    ax.plot(x, w["ef"], color="#00acc1", linewidth=1.0, label="EMA 20")
    ax.plot(x, w["es"], color="#fb8c00", linewidth=1.0, label="EMA 50")
    ax.plot(x, w["el"], color="#757575", linewidth=1.6, label="EMA 200")

    todos = list(trades) + ([res["abierta"]] if res["abierta"] else [])
    for t in todos:
        if t["ent"] < a0:
            continue
        cl = VERDE if t["side"] == 1 else ROJO
        ax.scatter([t["ent"]], [t["px"]], marker="^" if t["side"] == 1 else "v", s=60 if not chico else 28,
                   color=cl, edgecolors="black", linewidths=0.6, zorder=6)
        if t.get("exit") is not None and t["exit"] >= a0:
            ok = t["ret"] > 0
            ax.scatter([t["exit"]], [t["exit_px"]], marker="x", s=40 if not chico else 20,
                       color=VERDE if ok else ROJO, zorder=6)
            ax.plot([t["ent"], t["exit"]], [t["px"], t["exit_px"]], color=VERDE if ok else ROJO,
                    linewidth=0.8, linestyle=":", zorder=4)
    if act is not None:
        x0 = max(a0, act["ent"] - 2)
        x1 = n - 1 + max(4, int(barras * 0.06))
        for nivel, cl, txt in ((act["px"], "#1565c0", "entrada"), (act["stop"], ROJO, "stop"), (act["tgt"], VERDE, "objetivo")):
            ax.hlines(nivel, x0, x1, colors=cl, linestyles="--", linewidth=1.1, zorder=5)
            if not chico:
                ax.text(x1, nivel, " %s %.2f" % (txt, nivel), color=cl, va="center", fontsize=8)
        ax.axhspan(min(act["px"], act["stop"]), max(act["px"], act["stop"]), xmin=0, xmax=1, color=ROJO, alpha=0.05, zorder=1)
        ax.axhspan(min(act["px"], act["tgt"]), max(act["px"], act["tgt"]), xmin=0, xmax=1, color=VERDE, alpha=0.05, zorder=1)
        ax.set_xlim(a0 - 1, x1 + (0 if chico else 9))
    else:
        ax.set_xlim(a0 - 1, n + 3)
    lo, hi = w["Low"].min(), w["High"].max()
    if act is not None:
        lo, hi = min(lo, act["stop"], act["tgt"]), max(hi, act["stop"], act["tgt"])
    pad = (hi - lo) * 0.05
    ax.set_ylim(lo - pad, hi + pad)
    idx = list(w.index)
    ticks = np.linspace(a0, n - 1, 6 if not chico else 3).astype(int)
    ax.set_xticks(ticks)
    ax.set_xticklabels([idx[t - a0].strftime("%d/%m/%y") for t in ticks], fontsize=7 if chico else 8)
    ax.tick_params(axis="y", labelsize=7 if chico else 8)
    ax.grid(alpha=0.25)
    nombre = {1: "CALL", -1: "PUT", 0: ""}[res["lado"]]
    ax.set_title("%s · %s %s" % (sym, res["estado"], nombre if res["estado"] != "ESPERAR" else ""),
                 fontsize=9 if chico else 12, loc="left")
    if not chico:
        ax.legend(loc="upper left", fontsize=8, ncol=3, frameon=False)
    fig.tight_layout()
    return fig


def fig_oi(sym, res):
    ctx, ctr = res["ctx"], res["ctr"]
    spot = float(res["ind"]["Close"].iloc[-1])
    fig, ax = plt.subplots(figsize=(11, 3.6), dpi=100)
    c, pt = ctx["calls"], ctx["puts"]
    c = c[(c["strike"] >= spot * 0.75) & (c["strike"] <= spot * 1.25)]
    pt = pt[(pt["strike"] >= spot * 0.75) & (pt["strike"] <= spot * 1.25)]
    ks = np.array(sorted(set(c["strike"]) | set(pt["strike"])), float)
    if len(ks) == 0:
        ax.text(0.5, 0.5, "Sin datos de strikes", ha="center")
        return fig
    paso = np.median(np.diff(ks)) if len(ks) > 1 else 1.0
    ax.bar(c["strike"] - paso * 0.2, c["openInterest"], width=paso * 0.38, color=VERDE, label="OI calls")
    ax.bar(pt["strike"] + paso * 0.2, pt["openInterest"], width=paso * 0.38, color=ROJO, label="OI puts")
    ax.axvline(spot, color="#1565c0", linewidth=1.4, label="precio %.2f" % spot)
    if np.isfinite(ctx["straddle"]):
        ax.axvspan(spot - ctx["straddle"], spot + ctx["straddle"], color="#1565c0", alpha=0.08,
                   label="movimiento esperado ±%.1f%%" % ctx["em_pct"])
    if ctr is not None:
        ax.axvline(ctr["strike"], color="#6a1b9a", linestyle="--", linewidth=1.3, label="strike sugerido %g" % ctr["strike"])
    ax.set_title("%s · open interest por strike · vence %s (%d días)" % (sym, ctx["exp"], ctx["dte"]), fontsize=11, loc="left")
    ax.set_xlabel("Strike", fontsize=8)
    ax.tick_params(labelsize=8)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8, ncol=5, frameon=False, loc="upper center")
    fig.tight_layout()
    return fig


def mostrar(fig):
    st.pyplot(fig)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Datos (yfinance) y modo demo
# ---------------------------------------------------------------------------
def fetch_spy():
    h = yf.Ticker("SPY").history(period="3y", interval="1d", auto_adjust=True)
    h.index = h.index.tz_localize(None)
    return h


def fetch_raw(sym, p):
    tk = yf.Ticker(sym)
    h = tk.history(period="2y", interval="1d", auto_adjust=True)
    if h is None or h.empty:
        raise ValueError("sin historial")
    h.index = h.index.tz_localize(None)
    h = h.dropna(subset=["Close"])
    opt, earn = None, None
    try:
        hoy = pd.Timestamp.today().normalize()
        cand = []
        for e in tk.options:
            dte = (pd.Timestamp(e) - hoy).days
            if dte >= p["min_dte"]:
                cand.append((abs(dte - p["target_dte"]), e, dte))
        if cand:
            _, e, dte = min(cand)
            ch = tk.option_chain(e)
            opt = dict(exp=e, dte=dte, calls=ch.calls, puts=ch.puts)
    except Exception:
        opt = None
    try:
        cal = tk.calendar
        fechas = cal.get("Earnings Date") if isinstance(cal, dict) else None
        if fechas:
            earn = pd.Timestamp(fechas[0])
    except Exception:
        earn = None
    return dict(hist=h, opt=opt, earn=earn, stamp=time.time())


def _gbm(seed, n=520, drift=0.0004, vol=0.017, s0=100.0):
    rng = np.random.default_rng(seed)
    reg = np.where(np.sin(np.linspace(0, rng.uniform(4, 9), n) + rng.uniform(0, 6)) > 0, 1.0, -0.6)
    ret = rng.normal(drift * reg * 3, vol, n)
    c = s0 * np.exp(np.cumsum(ret))
    o = np.r_[c[0], c[:-1]] * (1 + rng.normal(0, 0.002, n))
    hi = np.maximum(o, c) * (1 + np.abs(rng.normal(0, 0.006, n)))
    lo = np.minimum(o, c) * (1 - np.abs(rng.normal(0, 0.006, n)))
    idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=n)
    return pd.DataFrame({"Open": o, "High": hi, "Low": lo, "Close": c, "Volume": rng.uniform(5e5, 5e6, n)}, index=idx)


def demo_spy():
    return _gbm(7, n=700, drift=0.0006, vol=0.009, s0=450.0)


def demo_raw(sym, p):
    seed = abs(hash(sym)) % (2 ** 31)
    h = _gbm(seed, s0=float(np.random.default_rng(seed).uniform(20, 400)))
    rng = np.random.default_rng(seed + 1)
    spot = float(h["Close"].iloc[-1])
    hv = float(np.log(h["Close"]).diff().tail(20).std() * math.sqrt(252))
    dte = int(p["target_dte"])
    T = dte / 365.0
    paso = max(0.5, round(spot * 0.025, 1))
    ks = np.arange(math.floor(spot * 0.7 / paso) * paso, spot * 1.3, paso)
    iv_base = hv * rng.uniform(0.9, 1.7)
    cr, pr = [], []
    for k in ks:
        iv = iv_base * (1 + 0.25 * abs(math.log(k / spot)))
        for lista, call in ((cr, True), (pr, False)):
            m = max(bs_price(spot, k, T, 0.04, iv, call), 0.01)
            liq = rng.uniform(0.3, 1.0) * math.exp(-abs(math.log(k / spot)) * 6)
            sp = m * rng.uniform(0.02, 0.18) / max(liq, 0.15)
            oi = int(rng.uniform(20, 6000) * liq)
            vol = int(oi * rng.uniform(0.02, 0.5) * (4 if rng.random() < 0.03 else 1))
            lista.append(dict(strike=float(k), lastPrice=m, bid=max(m - sp / 2, 0.01), ask=m + sp / 2,
                              volume=vol, openInterest=oi, impliedVolatility=iv))
    exp = (pd.Timestamp.today().normalize() + pd.Timedelta(days=dte)).strftime("%Y-%m-%d")
    earn = (pd.Timestamp.today().normalize() + pd.Timedelta(days=int(rng.integers(3, 80)))) if rng.random() < 0.5 else None
    return dict(hist=h, opt=dict(exp=exp, dte=dte, calls=pd.DataFrame(cr), puts=pd.DataFrame(pr)),
                earn=earn, stamp=time.time())


# ---------------------------------------------------------------------------
# Presentación
# ---------------------------------------------------------------------------
def color_estado(v):
    s = str(v)
    if s == "ENTRADA NUEVA":
        return "background-color:#1b5e20;color:white;font-weight:bold"
    if s == "VIGENTE":
        return "background-color:#fff59d;color:#5d4037;font-weight:bold"
    return "color:#9e9e9e"


def color_rec(v):
    s = str(v)
    if s.startswith("COMPRAR CALL"):
        return "background-color:#c8e6c9;color:#1b5e20;font-weight:bold"
    if s.startswith("COMPRAR PUT"):
        return "background-color:#ffcdd2;color:#b71c1c;font-weight:bold"
    if "CARO" in s or "ILÍQUIDA" in s or "sin datos" in s:
        return "background-color:#ffe0b2;color:#e65100;font-weight:bold"
    return ""


def estilo(df):
    sty = df.style.format({"Precio": "{:,.2f}", "ATR %": "{:.1f}", "IV ATM %": "{:.0f}", "HV20 %": "{:.0f}",
                           "IV/HV": "{:.2f}", "Mov. esperado %": "{:.1f}", "P/C vol": "{:.2f}", "P/C OI": "{:.2f}",
                           "DTE": "{:.0f}", "Strike sug.": "{:g}", "Prima (ask)": "{:.2f}", "Delta": "{:.2f}",
                           "Spread %": "{:.0f}", "% acierto (acción)": "{:.0f}", "Ret. medio % (acción)": "{:+.1f}"},
                          na_rep="—")
    f = getattr(sty, "map", None) or sty.applymap
    sty = f(color_estado, subset=["Estado"])
    f = getattr(sty, "map", None) or sty.applymap
    return f(color_rec, subset=["Recomendación"])


def normalizar(txt):
    return [t.strip().upper() for t in txt.replace("\n", ",").split(",") if t.strip()]


def main():
    st.set_page_config(layout="wide", page_title="SLY | Radar de opciones")
    st.title("SLY | Radar de opciones")
    st.caption("Señal técnica CALL/PUT + contexto de opciones + entrada sugerida y gráficos, para las acciones de tu lista. "
               "Herramienta de contexto: no es una recomendación de inversión ni garantiza resultados. "
               "Comprar opciones: la pérdida máxima es la prima. Datos de yfinance (demorados).")
    ss = st.session_state
    ss.setdefault("raw", {})
    ss.setdefault("err", {})
    ss.setdefault("spy", None)

    demo_env = os.environ.get("SLY_DEMO") == "1"
    with st.sidebar:
        st.header("Lote")
        demo = st.checkbox("Modo demo (datos sintéticos)", value=demo_env,
                           help="Para ver la app sin conexión. Los datos NO son reales.")
        batch_size = st.number_input("Acciones por lote", 5, 200, 40,
                                     help="Cada acción requiere varias consultas (historial + opciones): lotes chicos son más rápidos.")
        total = (len(TICKERS) + batch_size - 1) // batch_size
        lote = st.selectbox("Lote", list(range(total)), format_func=lambda x: "Lote %d" % (x + 1))
        custom = st.text_area("Lista propia (opcional)", placeholder="ORCL, MSTR, QCOM ... Si la completás, reemplaza al lote.")
        solo_sig = st.checkbox("Leer opciones solo si hay señal", value=False,
                               help="Más rápido de analizar, pero no muestra el contexto de opciones de las demás.")
        st.header("Señal (acción)")
        min_score = st.slider("Puntos mínimos (de 5)", 3, 5, 4)
        use_mkt = st.checkbox("Filtrar con el mercado (SPY)", value=True)
        allow_call = st.checkbox("Permitir CALL", value=True)
        allow_put = st.checkbox("Permitir PUT", value=True)
        stop_mult = st.number_input("Stop = ATR x", 0.5, 6.0, 1.5, step=0.1)
        tgt_mult = st.number_input("Objetivo = ATR x", 0.5, 10.0, 3.0, step=0.1)
        max_bars = st.number_input("Horizonte máx. (velas)", 3, 60, 20)
        cooldown = st.number_input("Espera tras cerrar (velas)", 0, 20, 3)
        st.header("Opciones")
        target_dte = st.number_input("Vencimiento objetivo (días)", 14, 120, 35)
        min_dte = st.number_input("Vencimiento mínimo (días)", 7, 60, 14)
        delta_t = st.slider("Delta objetivo", 0.20, 0.70, 0.40, step=0.05)
        min_oi = st.number_input("Open interest mínimo", 0, 5000, 100, step=50)
        max_spread = st.number_input("Spread máximo (% del precio medio)", 2, 60, 15)
        iv_rich = st.number_input("IV 'cara' si IV/HV >", 1.0, 4.0, 1.5, step=0.1)
        rf = st.number_input("Tasa libre de riesgo (%)", 0.0, 12.0, 4.0, step=0.25) / 100.0
        st.header("Riesgo")
        capital = st.number_input("Capital (USD)", 100.0, 10_000_000.0, 10000.0, step=500.0)
        riesgo = st.number_input("Riesgo por operación (%)", 0.1, 5.0, 1.0, step=0.1)
        go = st.button("Analizar lote y acumular", type="primary")
        clear = st.button("Limpiar memoria")

    p = dict(min_score=min_score, use_mkt=use_mkt, allow_call=allow_call, allow_put=allow_put, stop_mult=stop_mult,
             tgt_mult=tgt_mult, max_bars=max_bars, cooldown=cooldown, target_dte=target_dte, min_dte=min_dte,
             delta_t=delta_t, min_oi=min_oi, max_spread=max_spread, iv_rich=iv_rich, rf=rf, capital=capital,
             riesgo=riesgo, only_signal_opts=solo_sig)

    if clear:
        ss["raw"], ss["err"], ss["spy"] = {}, {}, None
    if not demo and yf is None:
        st.error("Falta instalar yfinance: pip install yfinance (o activá el modo demo).")
        st.stop()

    if go:
        lista = normalizar(custom) if custom.strip() else TICKERS[lote * batch_size:(lote + 1) * batch_size]
        barra = st.progress(0.0, text="Descargando…")
        try:
            ss["spy"] = demo_spy() if demo else fetch_spy()
        except Exception as e:
            ss["spy"] = None
            st.warning("No pude leer SPY (filtro de mercado desactivado): %s" % e)
        if demo:
            for i, s in enumerate(lista):
                ss["raw"][s] = demo_raw(s, p)
                barra.progress((i + 1) / len(lista))
        else:
            with ThreadPoolExecutor(max_workers=4) as ex:
                futs = {ex.submit(fetch_raw, s, p): s for s in lista}
                hechos = 0
                for f in as_completed(futs):
                    s = futs[f]
                    try:
                        ss["raw"][s] = f.result()
                        ss["err"].pop(s, None)
                    except Exception as e:
                        ss["err"][s] = str(e)[:100]
                    hechos += 1
                    barra.progress(hechos / len(futs), text="Descargando… %d/%d" % (hechos, len(futs)))
        barra.empty()

    if not ss["raw"]:
        st.info("Elegí un lote en la barra lateral y tocá «Analizar lote y acumular». Podés acumular varios lotes.")
        st.stop()
    if use_mkt and ss.get("spy") is None:
        st.warning("Sin datos de SPY: el filtro de mercado no se aplica.")

    # --- Análisis (se recalcula con los datos guardados cuando cambiás umbrales)
    resultados, omitidas = {}, []
    for s, raw in ss["raw"].items():
        r = analizar(s, raw, ss["spy"], p)
        if r is not None:
            resultados[s] = r
        else:
            omitidas.append(s)
    if not resultados:
        st.warning("No hay datos suficientes (se necesitan al menos 230 velas diarias por acción).")
        st.stop()
    df = pd.DataFrame([r["fila"] for r in resultados.values()])
    orden = {"ENTRADA NUEVA": 0, "VIGENTE": 1, "ESPERAR": 2}
    df["_o"] = df["Estado"].map(orden)
    df["_s"] = df[["Pts CALL", "Pts PUT"]].max(axis=1)
    df = df.sort_values(["_o", "_s", "Símbolo"], ascending=[True, False, True]).reset_index(drop=True)

    nuevas = df[df["Estado"] == "ENTRADA NUEVA"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Acciones analizadas", len(df))
    c2.metric("Entradas nuevas CALL / PUT", "%d / %d" % ((nuevas["Pts CALL"] > nuevas["Pts PUT"]).sum(),
                                                         (nuevas["Pts PUT"] > nuevas["Pts CALL"]).sum()))
    c3.metric("Señales vigentes", int((df["Estado"] == "VIGENTE").sum()))
    c4.metric("Con opciones cargadas", int(df["IV ATM %"].notna().sum()))
    if ss["err"] or omitidas:
        with st.expander("Acciones sin datos suficientes (%d)" % (len(ss["err"]) + len(omitidas))):
            st.write(ss["err"])
            if omitidas:
                st.write("Con menos de 230 velas diarias (se necesitan para la EMA 200): " + ", ".join(omitidas))

    # --- Qué hacer ahora
    st.subheader("Entradas recomendadas ahora")
    if nuevas.empty:
        st.info("Ninguna acción del conjunto tiene entrada nueva hoy. Esperar también es una decisión.")
    for _, r in nuevas.head(15).iterrows():
        res = resultados[r["Símbolo"]]
        with st.expander("%s · %s · confianza %s" % (r["Símbolo"], r["Recomendación"], r["Confianza"]), expanded=False):
            st.markdown("**Acción:** " + res["plan"])
            if r["Alertas"]:
                st.markdown("**Alertas:** " + r["Alertas"])
            mostrar(fig_precio(r["Símbolo"], res, barras=140))

    # --- Tabla
    st.subheader("Tabla completa")
    f1, f2 = st.columns(2)
    est = f1.multiselect("Estado", ["ENTRADA NUEVA", "VIGENTE", "ESPERAR"], default=["ENTRADA NUEVA", "VIGENTE"])
    buscar = f2.text_input("Buscar símbolo", "")
    vista = df[df["Estado"].isin(est)].drop(columns=["_o", "_s"])
    if buscar.strip():
        vista = vista[vista["Símbolo"].isin(normalizar(buscar))]
    try:
        st.dataframe(estilo(vista), width="stretch", hide_index=True, height=520)
    except TypeError:
        st.dataframe(estilo(vista), use_container_width=True, hide_index=True, height=520)
    st.download_button("Descargar CSV", vista.to_csv(index=False).encode("utf-8"), "radar_opciones.csv", "text/csv")

    # --- Detalle con gráficos
    st.subheader("Detalle y gráficos")
    sel = st.selectbox("Acción", df["Símbolo"].tolist())
    res = resultados[sel]
    st.markdown("**%s** → %s (confianza %s)" % (sel, res["fila"]["Recomendación"], res["fila"]["Confianza"]))
    st.markdown("**Acción:** " + res["plan"])
    if res["fila"]["Alertas"]:
        st.markdown("**Alertas:** " + res["fila"]["Alertas"])
    barras = st.slider("Velas a mostrar", 60, 400, 160, step=20)
    mostrar(fig_precio(sel, res, barras=barras))
    if res["ctx"] is not None:
        mostrar(fig_oi(sel, res))
        ctx = res["ctx"]
        st.caption("Strikes con más OI — calls: %s · puts: %s" % (
            ", ".join("%g" % k for k in ctx["top_c"]) or "—", ", ".join("%g" % k for k in ctx["top_p"]) or "—"))
    else:
        st.caption("Esta acción no tiene opciones cargadas (o no cotiza opciones).")

    # --- Galería
    with st.expander("Galería: gráficos de todas las entradas y señales vigentes"):
        cuales = df[df["Estado"].isin(["ENTRADA NUEVA", "VIGENTE"])]["Símbolo"].tolist()
        tope = st.slider("Máximo de gráficos", 3, 30, 12)
        cols = st.columns(3)
        for i, s in enumerate(cuales[:tope]):
            with cols[i % 3]:
                mostrar(fig_precio(s, resultados[s], barras=120, chico=True))
        if not cuales:
            st.write("No hay señales para graficar.")

    with st.expander("Cómo leer esto"):
        st.markdown(
            "- **Puntos CALL/PUT:** 5 condiciones (precio vs EMA200, EMA20 vs EMA50, ADX con dirección, RSI en zona, ruptura o volumen). "
            "Se necesita el mínimo elegido y que el mercado (SPY) acompañe.\n"
            "- **ENTRADA NUEVA:** la señal se dio en la última vela. **VIGENTE:** ya está en marcha; no se persigue.\n"
            "- **IV/HV:** volatilidad implícita de las opciones frente a la volatilidad real de las últimas 20 ruedas. "
            "Arriba de 1,5 las opciones están caras (conviene esperar o usar spreads).\n"
            "- **Movimiento esperado:** lo que el mercado de opciones descuenta hasta el vencimiento (precio del straddle).\n"
            "- **P/C (put/call):** alto = protección comprada (miedo); bajo = euforia. Se usa como contexto, no como señal.\n"
            "- **Strike sugerido:** contrato líquido con delta cercano al objetivo. Verificá bid/ask reales en tu broker.\n"
            "- **% de acierto:** se mide sobre la ACCIÓN con stop/objetivo por ATR, con pocas operaciones: es orientativo.\n"
            "- Las reglas no están validadas con una prueba fuera de muestra: usá el backtest del Pine para eso.")


if __name__ == "__main__":
    main()
