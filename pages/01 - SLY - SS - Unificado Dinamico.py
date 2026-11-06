import time
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
 
# ─────────────────────────────────────────────
# CONFIGURACIÓN INSTITUCIONAL - LIGHT THEME
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | MONITOR UNIFICADO V57")
 
st.markdown("""
<style>
    .stApp { background-color: #FFFFFF; color: #1C1E21; }
    .stDataFrame { font-size: 11px; font-family: 'Roboto Mono', monospace; }
    h1 { color: #004D40; font-weight: 800; border-bottom: 3px solid #004D40; }
    .stProgress > div > div > div > div { background-color: #004D40; }
    .sector-box { background-color: #F1F8E9; padding: 15px; border-radius: 8px; border-left: 5px solid #2E7D32; margin-bottom: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .sector-title { font-weight: bold; color: #1B5E20; font-size: 1.1em; }
</style>
""", unsafe_allow_html=True)
 
for _k, _v in {"u_results": {}, "u_errors": {}}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v
 
# ─────────────────────────────────────────────
# MAPEO SECTORIAL (copiado del V56)
# ─────────────────────────────────────────────
SECTOR_MAP = {
    "ÍNDICES/ETFs": ["SPY", "QQQ", "DIA", "IWM", "VTI", "VOO", "VEA", "VWO", "EEM", "XLK", "XLF", "XLE", "XLV", "XLI", "XLP", "XLB", "XLU", "XLY", "XLC", "XLRE", "ARKK", "BITO", "IBIT"],
    "TECNOLOGÍA": ["AAPL", "MSFT", "NVDA", "GOOGL", "META", "AVGO", "AMD", "INTC", "QCOM", "TXN", "MU", "ADI", "AMAT", "LRCX", "KLAC", "ASML", "SNOW", "PLTR", "NOW", "CRM", "ADBE", "ORCL", "DELL", "SMCI"],
    "FINANCIERO": ["JPM", "BAC", "WFC", "GS", "MS", "C", "V", "MA", "AXP", "BLK", "SPGI", "CME", "ICE", "PYPL", "SQ", "HOOD"],
    "ENERGÍA/OIL": ["XOM", "CVX", "PBR", "SLB", "COP", "OXY", "HAL", "BKR", "VIST", "YPF", "TGS", "PAM"],
    "ARGENTINA (ADRs)": ["GGAL", "BMA", "BFR", "SUPV", "PAM", "PAMP", "EDN", "CEPU", "CRESY", "IRS", "LOMA", "MELI", "GLOB", "TX"],
    "CRIPTO/BLOCKCHAIN": ["BTC-USD", "ETH-USD", "MSTR", "COIN", "MARA", "RIOT", "BITX", "BITI", "IREN", "CLSK", "HUT"],
    "CONSUMO/RETAIL": ["AMZN", "TSLA", "WMT", "COST", "KO", "PEP", "MCD", "NKE", "SBUX", "TGT", "PG", "PM", "HD", "LOW", "EL", "MDLZ"],
    "SALUD/BIO": ["LLY", "UNH", "JNJ", "ABBV", "MRK", "PFE", "AMGN", "TMO", "DHR", "BMY", "ISRG", "ABT"],
    "INDUSTRIAL/AÉREO": ["GE", "CAT", "BA", "HON", "RTX", "LMT", "DE", "UNP", "UPS", "FDX", "DAL", "AAL"]
}
 
 
def get_sector(ticker):
    for sector, members in SECTOR_MAP.items():
        if ticker.upper() in members:
            return sector
    return "OTROS / SMALL CAPS"
 
 
# ─────────────────────────────────────────────
# LISTA DE ACCIONES (copiada del V56)
# ─────────────────────────────────────────────
RAW_TICKERS = "BIL, SPY, QQQ, ARKK, BOTZ, DBC, GLD, BND, VWO, VNQ, HYG, VEA, EMB, AAPL, AMZN, TSLA, MSFT, META, NVDA, GOOGL, ARGT, MELI, GLOB, TTWO, RKLB, HOOD, HOG, MSTR, COIN, SWK, INTC, AMD, DIS, GME, ABNB, AMC, KO, DIA, F, ADBE, MO, C, COST, DE, DOCU, GE, ETSY, HAL, CRM, HSBC, IBM, JD, JNJ, LMT, MA, MCD, NFLX, NKE, PYPL, PEP, PBR, SHOP, SNAP, SONY, SPOT, SBUX, TGT, UL, WMT, SMCI, JPM, WFC, AVGO, MU, LLY, UNH, V, QCOM, HD, BAC, GGAL, BABA, YPF, PAM, XOM, AMAT, GS, ACN, MARA, SNOW, ORCL, UBER, DELL, LRCX, CVX, CSCO, CRWD, CVNA, BA, VRT, HUBS, MRK, PLTR, NEE, CAT, PFE, LIN, CMG, GM, BKNG, PG, MRVL, LOW, TXN, ADI, MS, DAL, AMGN, T, LCID, ABBV, NOW, UPS, LEN, BMY, ENPH, SOUN, INTU, SPGI, CMCSA, DHR, AXP, DHI, RTX, BK, CME, PANW, KLAC, BLK, ICE, MDLZ, MRNA, VOO, VTI, VUG, VTV, IWF, IJH, IJR, VIG, VGT, XLK, VO, IWM, TLT, VB, SCHX, XLF, XLV, SCHF, MUB, XLE, XLI, XLY, VHT, SOXX, PHO, XLRE, SCHH, IYR, ICF, DUOL, LUV, AFRM, ITA, SH, IEF, VGIT, GOVT, SGOV, IBIT, EETH, SATL, RMAX, COMP, AGNT, OPAD, OPEN, SSO, SCHD, EWJ, EWZ, EWW, ECH, INDA, EWT, EWS, ENZL, EWA, DGRO, PINS, ZM, ULTA, PM, SCHW, MMM, FDX, CVS, PSX, DASH, KMB, MSI, MNST, TMO, EA, TMUS, ABT, BX, VZ, ISRG, DDOG, MCHI, BSV, IFS, BAP, BVN, TQQQ, SOXL, TMF, SPXL, UPRO, TECL, YINN, SQQQ, FAS, TNA, LABU, SPXS, SOXS, MCO, CL, MAR, KDP, UNP, TEAM, GEHC, SOFI, CCL, NET, WST, MKC, GDDY, HPE, MDB, WBD, KHC, EBAY, HLT, FISV, EEM, AAL, JMIA, BP, BB, BBD, SVXY, REK, VIST, ADM, TSM, RIOT, TLRY, NOC, CGC, GD, IIPR, SYM, NU, ANET, OXY, O, ASML, VEGI, OKLO, PFF, RDDT, SPYD, HSY, PTON, DJT, BITX, KODK, VIXY, RACE, LULU, HMC, FWONK, TS, TX, HIMS, ITUB, ABEV, BIDU, GRWG, HYFM, MANU, FAZ, FNGU, MSFU, AAPU, FBL, LOMA, DLTR, DUK, GPRK, NEM, SO, QBTS, RGTI, BITI, PCAR, NVO, UMAC, AXON, XYZ, PDD, NTES, SOS, RCAT, BN, VALE, ARM, QSI, TM, WM, URTH, BBAR, IRS, BIOX, EDN, SUPV, XP, BBAI, DAPP, TEM, KULR, INBS, TBX, EAT, LMND, UUUU, GDX, ASTS, RCL, APP, PAGS, TTT, UNCY, PL, NIO, CONY, CLOV, JOBY, UGL, TBF, BYND, TWLO, MMSI, LODE, TBT, CEG, UUP, OTLY, SHY, IEI, TLH, IREN, NWTG, FLIN, OSCR, ALAB, AMZY, APLY, AVY, BG, BIIB, BMA, CELH, CEPU, CRESY, DOW, DPZ, EWY, FXI, FXY, HON, HUT, IGPT, LAES, ONON, PYPY, SEDG, SLB, SNA, STLA, STZ, TTEK, URBN, VSCO, AAP, YBIT, ADP, HERO, ABSI, PDBA, MAGS, B, SMMT, SETH, SLV, PATH, AIQ, SHEL, TGS, PSQ, MKL, XLP, XPEV, DXYZ, MSTY, CRCL, PLBY, FIG, AOM, OWNB, BKR, SPYG, USO, APLD, ASPN, AUR, BITO, BKCH, BLDR, BLOK, CDNS, COO, DAVA, EIX, EL, ELF, EVTL, FEZ, FSLR, GAUZ, GPN, HDV, HELO, BMRN, VXUS, URA, ACWI, NVDL, GRAB, GTLB, VT, SPMO, QQQM, IONQ, TSLL, AMZU, SBET, JEPQ, JEPI, QYLD, TXRH, ABCL, AOK, VBR, IAU, IEO, ZETA, KBH, OMC, RYDE, SVCO, POOL, VYM, ANF, TMDX, MTUM, BMNR, TMQ, BNKK, VEEE, QNRX, HRZN"
TICKERS = sorted(list(set([t.strip() for t in RAW_TICKERS.split(",") if t.strip()])))
 
# ─────────────────────────────────────────────
# PARÁMETROS
# ─────────────────────────────────────────────
# etiqueta -> (intervalo yfinance, período a descargar)
TF_OPTIONS = {"1 HS": ("1h", "730d"), "1 DIA": ("1d", "10y"), "1 SEMANA": ("1wk", "max")}
TF_SEC = {"1h": 3600, "1d": 86400, "1wk": 604800}
# temporalidad macro según la del análisis (igual que el MACD macro del indicador)
MACRO_TF = {"1h": ("1wk", "5y", "semanal"), "1d": ("1wk", "5y", "semanal"), "1wk": ("1mo", "10y", "mensual")}
MIN_BARS = 270                          # la EMA 260 necesita historial
ROWS, VA_PCT, MAX_PROF = 40, 0.70, 300  # perfil de volumen (igual que el Pine)
POC_TOL = 0.3                           # % para considerar "EN EL POC"
REC_OPCIONES = ["LONG FUERTE", "LONG", "VIGILAR", "SALIR", "ESPERAR"]
 
 
def fmt_px(x):
    return f"{x:.6g}"
 
 
# ─────────────────────────────────────────────
# MOTORES TÉCNICOS (réplica del indicador SLY_UNIFICADO)
# ─────────────────────────────────────────────
def dema(s, length):
    e1 = s.ewm(span=length, adjust=False).mean()
    e2 = e1.ewm(span=length, adjust=False).mean()
    return 2 * e1 - e2
 
 
def rma(s, n):
    return s.ewm(alpha=1 / n, adjust=False).mean()
 
 
def rsi_calc(close, n=14):
    d = close.diff()
    up, dn = d.clip(lower=0), -d.clip(upper=0)
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
    """Heikin Ashi recursivo (igual que el Pine). True = vela verde."""
    o, h, l, c = (df[k].astype(float).to_numpy() for k in ("open", "high", "low", "close"))
    hac = (o + h + l + c) / 4
    hao = np.zeros(len(df))
    hao[0] = (o[0] + c[0]) / 2
    for i in range(1, len(df)):
        hao[i] = (hao[i - 1] + hac[i - 1]) / 2
    return hac > hao
 
 
def macd_alerts(hist):
    """Giro alcista (LONG) y giro bajista (SALIR) del histograma del MACD PRO."""
    h = hist.to_numpy()
    h1, h2 = np.roll(h, 1), np.roll(h, 2)
    h1[:1] = np.nan
    h2[:2] = np.nan
    with np.errstate(invalid="ignore"):
        long_a = ((h > 0) & (h1 <= 0)) | ((h > h1) & (h1 < h2) & (h < 0))
        short_a = ((h < 0) & (h1 >= 0)) | ((h < h1) & (h1 > h2) & (h > 0))
    return long_a, short_a
 
 
# ----- Volumen: perfil anclado al último pivote de precio -----
def pivot_len(tf):
    s = TF_SEC[tf]
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
        zona, zkey = "SOBRE VAH 🟢", "SOBRE_VAH"
    elif close < pr["val"]:
        zona, zkey = "BAJO VAL 🔴", "BAJO_VAL"
    elif abs(close - pr["poc"]) / close * 100 <= POC_TOL:
        zona, zkey = "EN EL POC 🟠", "EN_POC"
    elif close > pr["poc"]:
        zona, zkey = "Entre POC y VAH", "POC_VAH"
    else:
        zona, zkey = "Entre VAL y POC", "VAL_POC"
    dist = lambda x: f"{fmt_px(x)} ({(x / close - 1) * 100:+.1f}%)"
    return {"zona": zona, "zkey": zkey, "delta": pr["delta"],
            "poc": dist(pr["poc"]), "vah": dist(pr["vah"]), "val": dist(pr["val"]),
            "vol": f"Δ {pr['delta']:+.0f}% · RVOL {rvol:+.1f} ({n_prof} velas)"}
 
 
def recomendar(d, a_favor, edad, veredicto, r_up, r_over, ha_g, adx_v, di_plus,
               zkey, delta, macro, con_macro):
    """
    Recomendación de reglas SLY (no es asesoramiento financiero). Suma puntos a favor de una señal LONG vigente:
      tendencia EMA a favor +2 · señal fresca (≤3 velas) +1 / vieja (>10) -1 · MACD manteniendo fuerza +1 ·
      RSI subiendo +1 (-1 si está en sobrecompra) · Heikin Ashi verde +1 ·
      ADX con +DI: ≥25 +2, 20-25 +1, rango -1; -DI -1 · zona de volumen a favor +1 / en contra -1 ·
      delta compra-venta positivo +1 · MACD macro alcista +1 / bajista -1.
    Devuelve (texto, clave, puntaje, máximo).
    """
    if d == "-":
        return "ESPERAR ⚪ (sin señal)", "ESPERAR", 0, 0
    if veredicto.startswith("CERRAR"):
        return "SALIR 🟠 (el MACD perdió el cero)", "SALIR", 0, 0
    items = [
        (2 if a_favor else 0, 2),
        (1 if edad <= 3 else -1 if edad > 10 else 0, 1),
        (1 if veredicto.startswith("MANTENER") else 0, 1),
        (1 if r_up else 0, 1),
        (-1 if r_over else 0, 0),
        (1 if ha_g else 0, 1),
        ((2 if adx_v >= 25 else 1 if adx_v >= 20 else -1) if di_plus else -1, 2),
        ({"SOBRE_VAH": 1, "POC_VAH": 1, "EN_POC": 0, "VAL_POC": 0, "BAJO_VAL": -1}.get(zkey, 0), 1),
        (1 if delta > 0 else 0, 1),
    ]
    if con_macro and (macro.startswith("Alcista") or macro.startswith("Bajista")):
        items.append((1 if macro.startswith("Alcista") else -1, 1))
    score = sum(p for p, _ in items)
    mx = sum(m for _, m in items)
    ratio = score / mx if mx else 0
    if ratio >= 0.40:
        key = "LONG FUERTE" if (ratio >= 0.65 and a_favor) else "LONG"
    else:
        key = "VIGILAR"
    icono = {"LONG FUERTE": "🟢🟢", "LONG": "🟢", "VIGILAR": "🟡"}[key]
    texto = f"{key if key != 'VIGILAR' else 'VIGILAR LONG'} {icono} ({score}/{mx})" + ("" if a_favor else " · REBOTE")
    return texto, key, score, mx
 
 
# ─────────────────────────────────────────────
# DATOS (yfinance, igual que el V56)
# ─────────────────────────────────────────────
def limpiar(df):
    """Normaliza el DataFrame de yfinance: columnas en minúscula y 'vol'."""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns=lambda c: str(c).lower()).rename(columns={"volume": "vol"})
    if "vol" not in df.columns:
        df["vol"] = 0.0
    df = df[["open", "high", "low", "close", "vol"]].dropna(subset=["open", "high", "low", "close"])
    df["vol"] = df["vol"].fillna(0)
    return df
 
 
def recortar(df, tf, solo_cerradas):
    """Quita la última vela si todavía se está formando."""
    if not solo_cerradas or df.empty:
        return df
    delta = pd.Timedelta(seconds=TF_SEC[tf])
    last = df.index[-1]
    now = pd.Timestamp.now(tz=last.tz) if last.tzinfo else pd.Timestamp.now()
    return df.iloc[:-1] if last + delta > now else df
 
 
def macd_macro(sym, interval, period):
    """Informativo: MACD de la temporalidad mayor (EMA 12/26/9, como el ta.macd del Pine)."""
    try:
        m = limpiar(yf.download(sym, interval=interval, period=period, progress=False))
        if len(m) < 35:
            return "Sin data"
        c = m["close"].astype(float)
        macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
        return "Alcista 🟢" if macd.iloc[-1] > macd.ewm(span=9, adjust=False).mean().iloc[-1] else "Bajista 🔴"
    except Exception:
        return "N/A"
 
 
# ─────────────────────────────────────────────
# ANÁLISIS DE UN ACTIVO
# ─────────────────────────────────────────────
def analizar_df(df, tf, f_rsi, f_ha, f_macro, f_trend, macro_txt):
    n = len(df)
    if n < MIN_BARS:
        raise ValueError(f"Historial insuficiente: {n} velas (se necesitan ≥{MIN_BARS} para la EMA 260)")
    close = df["close"].astype(float)
 
    # Tendencia (EMA 52 vs EMA 260)
    bull = (close.ewm(span=52, adjust=False).mean() > close.ewm(span=260, adjust=False).mean()).to_numpy()
 
    # MACD PRO (señal)
    macd = dema(close, 12) - dema(close, 26)
    hist = macd - macd.ewm(span=9, adjust=False).mean()
    long_a, short_a = macd_alerts(hist)
    h_now, h_prev = hist.iloc[-1], hist.iloc[-2]
 
    # RSI PRO
    rsi = dema(rsi_calc(close, 14), 5)
    r_now, r_prev = rsi.iloc[-1], rsi.iloc[-2]
    basis, sd = rsi.rolling(20).mean().iloc[-1], rsi.rolling(20).std().iloc[-1]
    r_over = bool(r_now > basis + 2 * sd)
    r_under = bool(r_now < basis - 2 * sd)
    ext = " · sobrecompra" if r_over else " · sobreventa" if r_under else ""
    rsi_txt = f"{r_now:.1f} {'▲ GANA fuerza' if r_now > r_prev else '▼ PIERDE fuerza'} · {'sobre' if r_now > 50 else 'bajo'} 50{ext}"
 
    # Heikin Ashi
    ha = heikin_green(df)
    cambio = np.flatnonzero(ha[1:] != ha[:-1])
    ha_bars = (n - 1 - (cambio[-1] + 1)) if len(cambio) else n - 1
    ha_txt = f"{'VERDE 🟢' if ha[-1] else 'ROJA 🔴'} · hace {ha_bars} vela{'' if ha_bars == 1 else 's'}"
 
    # Señal LONG (filtros opcionales) y SALIR
    ok = np.ones(n, dtype=bool)
    if f_rsi:
        ok &= (rsi > rsi.shift(1)).to_numpy()
    if f_ha:
        ok &= ha
    if f_trend:
        ok &= bull
    if f_macro and not macro_txt.startswith("Alcista"):
        ok &= False
    long_sig = long_a & ok
    iL = int(np.flatnonzero(long_sig)[-1]) if long_sig.any() else None
    iS = int(np.flatnonzero(short_a)[-1]) if short_a.any() else None
    vigente = iL is not None and (iS is None or iL > iS)
 
    estado, senal, veredicto, pnl, edad, ultima = "SIN SEÑAL ⚪", "Sin señal", "-", "-", 9999, "-"
    if iL is not None:
        ultima = df.index[iL].strftime("%Y-%m-%d %H:%M") if tf == "1h" else df.index[iL].strftime("%Y-%m-%d")
    if vigente:
        edad = n - 1 - iL
        estado = "VIGENTE 🟢"
        senal = "LONG 🟢 NUEVA (esta vela)" if edad == 0 else f"LONG 🟢 hace {edad} vela{'' if edad == 1 else 's'}"
        pnl = f"{(float(close.iloc[-1]) / float(close.iloc[iL]) - 1) * 100:+.2f}%"
        veredicto = "CERRAR 🔴" if (h_prev > 0 and h_now <= 0) else "MANTENER 🟢" if h_now > h_prev else "PIERDE FUERZA 🟡"
    elif iL is not None:
        estado = "CERRADA 🔴"
        senal = f"SALIR 🔴 hace {n - 1 - iS} vela{'' if n - 1 - iS == 1 else 's'}"
 
    # MACD (estado)
    if h_now > 0:
        macd_txt = "Positivo · gana fuerza ▲" if h_now > h_prev else "Positivo · PIERDE fuerza ▼"
    else:
        macd_txt = "Negativo · cae con fuerza ▼" if h_now < h_prev else "Negativo · se recupera ▲"
 
    # ADX (temporalidad de análisis)
    pdi, mdi, adx = adx_calc(df)
    a, a_prev = float(adx.iloc[-1]), float(adx.iloc[-2])
    estado_adx = "Rango" if a < 20 else "Naciente" if a < 25 else "Tendencia" if a < 40 else "Tendencia fuerte"
    di_plus = bool(pdi.iloc[-1] > mdi.iloc[-1])
    adx_txt = f"{a:.1f}{'↑' if a > a_prev else '↓'} {'+DI' if di_plus else '-DI'} {estado_adx}"
 
    # Volumen (POC / VAH / VAL)
    vol = info_volumen(df, tf) or {"zona": "s/d", "zkey": "", "delta": 0.0, "poc": "-", "vah": "-", "val": "-", "vol": "-"}
 
    # Recomendación
    a_favor = bool(bull[iL]) if vigente else True
    rec_txt, rec_key, score, mx = recomendar(
        "LONG" if vigente else "-", a_favor, edad, veredicto, bool(r_now > r_prev), r_over, bool(ha[-1]),
        a, di_plus, vol["zkey"], float(vol["delta"]), macro_txt, macro_txt != "-")
 
    return {
        "Recomendación": rec_txt, "Estado": estado, "Señal": senal, "Veredicto": veredicto, "PnL Real": pnl,
        "Tendencia EMA": "ALCISTA 🟢 (52 > 260)" if bull[-1] else "BAJISTA 🔴 (52 < 260)",
        "MACD": macd_txt, "RSI": rsi_txt, "Heikin Ashi": ha_txt, "MACD macro": macro_txt,
        "Precio vs volumen": vol["zona"], "POC": vol["poc"], "VAH": vol["vah"], "VAL": vol["val"],
        "Volumen": vol["vol"], "ADX": adx_txt, "Última Señal": ultima, "Precio": round(float(close.iloc[-1]), 2),
        "_edad": edad, "_rec": rec_key, "_score": score, "_mx": mx,
    }
 
 
def analizar(sym, tf_lbl, solo_cerradas, con_macro, f_rsi, f_ha, f_macro, f_trend):
    interval, period = TF_OPTIONS[tf_lbl]
    raw = yf.download(sym, interval=interval, period=period, progress=False)
    if raw is None or raw.empty:
        raise ValueError("Sin datos en yfinance")
    df = recortar(limpiar(raw), interval, solo_cerradas)
    macro_txt = "-"
    if con_macro or f_macro:
        m_int, m_per, _ = MACRO_TF[interval]
        macro_txt = macd_macro(sym, m_int, m_per)
    res = analizar_df(df, interval, f_rsi, f_ha, f_macro, f_trend, macro_txt)
    res.update({"Activo": sym, "Sector": get_sector(sym), "TF": tf_lbl})
    return res
 
 
# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
st.title("🛡️ SLY | MONITOR UNIFICADO V57")
 
with st.sidebar:
    st.header("⚙️ Radar Ops")
    tf_lbl = st.selectbox("Temporalidad de análisis:", list(TF_OPTIONS.keys()), index=2)
    solo_cerradas = st.checkbox("Usar solo velas cerradas", value=True,
                                help="Evita señales de una vela que todavía se está formando. En 1 DIA y 1 SEMANA la vela actual se descarta hasta que cierra.")
    con_macro = st.checkbox("Incluir MACD macro (1 descarga extra por activo)", value=True,
                            help="1 HS y 1 DIA usan el MACD semanal; 1 SEMANA usa el mensual.")
    st.subheader("Filtros opcionales de la señal")
    f_rsi = st.checkbox("Exigir RSI ganando fuerza", value=False)
    f_ha = st.checkbox("Exigir vela Heikin Ashi verde", value=False)
    f_trend = st.checkbox("Exigir tendencia alcista (EMA 52 > EMA 260)", value=False)
    f_macro = st.checkbox("Exigir MACD macro alcista", value=False,
                          help="Se evalúa con el estado macro actual del activo.")
 
    st.subheader("Lotes")
    batch_size = st.number_input("Acciones por Lote:", 10, 200, 100)
    total_lotes = (len(TICKERS) - 1) // int(batch_size) + 1
    batch_idx = st.selectbox("Lote:", range(total_lotes), format_func=lambda x: f"Lote {x + 1}")
    st.caption(f"{len(TICKERS)} acciones en la lista")
 
    if st.button("🚀 ACTUALIZAR Y ACUMULAR", type="primary", use_container_width=True):
        subset = TICKERS[batch_idx * int(batch_size): (batch_idx + 1) * int(batch_size)]
        prog = st.progress(0)
        for i, sym in enumerate(subset):
            prog.progress((i + 1) / len(subset), text=f"Auditando {tf_lbl}: {sym}")
            try:
                st.session_state["u_results"][(sym, tf_lbl)] = analizar(
                    sym, tf_lbl, solo_cerradas, con_macro, f_rsi, f_ha, f_macro, f_trend)
                st.session_state["u_errors"].pop((sym, tf_lbl), None)
            except Exception as e:
                st.session_state["u_errors"][(sym, tf_lbl)] = f"{sym} [{tf_lbl}]: {type(e).__name__}: {str(e)[:100]}"
        prog.empty()
        st.rerun()
 
    if st.button("🗑️ Limpiar Memoria"):
        st.session_state["u_results"] = {}
        st.session_state["u_errors"] = {}
        st.rerun()
 
# ─────────────────────────────────────────────
# RESULTADOS
# ─────────────────────────────────────────────
res = [r for (s, t), r in st.session_state["u_results"].items() if t == tf_lbl]
errs = [m for (s, t), m in st.session_state["u_errors"].items() if t == tf_lbl]
 
if res:
    c1, c2 = st.columns(2)
    solo_vig = c1.checkbox("Solo con señal vigente", value=True)
    max_edad = c2.number_input("Antigüedad máxima de la señal (velas)", 0, 500, 10)
    rec_sel = st.multiselect("Recomendación", REC_OPCIONES, default=REC_OPCIONES,
                             help="Puntaje de reglas SLY (tendencia, señal, MACD, RSI, Heikin Ashi, ADX, volumen). "
                                  "Es una guía para ordenar, no asesoramiento financiero.")
 
    dfa = pd.DataFrame(res)
    vig = dfa[dfa["Estado"] == "VIGENTE 🟢"]
 
    st.subheader(f"📊 RESUMEN DE EXPOSICIÓN (VIGENTES · {tf_lbl})")
    m1, m2 = st.columns(2)
    m1.metric("Analizadas (acumuladas)", len(dfa))
    m2.metric("Con señal LONG vigente", len(vig))
    if not vig.empty:
        resumen = vig.groupby("Sector")["Activo"].apply(list).reset_index()
        cols = st.columns(3)
        for idx, row in resumen.iterrows():
            with cols[idx % 3]:
                st.markdown(f"<div class='sector-box'><div class='sector-title'>{row['Sector']}: {len(row['Activo'])}</div>"
                            f"<div style='font-size: 0.85em;'>{', '.join(row['Activo'])}</div></div>", unsafe_allow_html=True)
    else:
        st.warning("Sin señales LONG vigentes en la temporalidad analizada.")
 
    show = dfa.copy()
    if solo_vig:
        show = show[(show["Estado"] == "VIGENTE 🟢") & (show["_edad"] <= max_edad)]
    show = show[show["_rec"].isin(rec_sel)]
    show = show.assign(_ratio=show["_score"] / show["_mx"].replace(0, np.nan)).sort_values(
        by=["_ratio", "_edad", "Activo"], ascending=[False, True, True], na_position="last")
 
    cols_order = ["Activo", "Recomendación", "Sector", "Estado", "Señal", "Veredicto", "PnL Real", "Tendencia EMA", "MACD",
                  "RSI", "Heikin Ashi", "MACD macro", "Precio vs volumen", "POC", "VAH", "VAL", "Volumen", "ADX",
                  "Última Señal", "Precio", "TF"]
    if (show["MACD macro"] == "-").all():
        cols_order.remove("MACD macro")
    show = show[cols_order]
 
    def color_cells(val):
        s = str(val)
        if s.startswith("LONG FUERTE"):
            return "background-color: #81C784; color: #0B3D0B; font-weight: bold;"
        if s.startswith("SALIR 🟠"):
            return "background-color: #FFCC80; color: #E65100; font-weight: bold;"
        if s.startswith("VIGILAR") or "PIERDE" in s:
            return "background-color: #FFF9C4; color: #827717; font-weight: bold;"
        if s.startswith("ESPERAR"):
            return "color: #9E9E9E;"
        if "EN EL POC" in s:
            return "background-color: #FFE0B2; color: #E65100; font-weight: bold;"
        if (s.startswith("LONG") or "VIGENTE" in s or "MANTENER" in s or "ALCISTA" in s or s.startswith("Alcista")
                or "VERDE" in s or "GANA" in s or "SOBRE VAH" in s or "se recupera" in s):
            return "background-color: #C8E6C9; color: #1B5E20; font-weight: bold;"
        if (s.startswith("SALIR") or "CERRADA" in s or "CERRAR" in s or "BAJISTA" in s or s.startswith("Bajista")
                or "ROJA" in s or "BAJO VAL" in s or "cae con" in s):
            return "background-color: #FFCDD2; color: #B71C1C; font-weight: bold;"
        return ""
 
    st.subheader(f"📋 Matriz de Señales ({tf_lbl})")
    if show.empty:
        st.info("Ninguna acción analizada cumple el filtro. Probá subir la antigüedad máxima o desmarcar 'Solo con señal vigente'.")
    else:
        sub = [c for c in ["Recomendación", "Estado", "Señal", "Veredicto", "Tendencia EMA", "MACD", "RSI", "Heikin Ashi",
                           "MACD macro", "Precio vs volumen"] if c in show.columns]
        st.dataframe(show.style.map(color_cells, subset=sub), use_container_width=True, height=600, hide_index=True)
else:
    st.info("Elegí la temporalidad y cargá lotes para iniciar el análisis.")
 
if errs:
    with st.expander(f"⚠️ {len(errs)} acciones con error (sin datos, historial insuficiente o falla de descarga)"):
        st.write("\n\n".join(errs))
