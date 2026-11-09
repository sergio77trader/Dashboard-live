"""
SLY | ANALISTAS POR SECTOR — precios objetivo de analistas + señales SLY, organizado por sector.
 
Requisitos:  pip install streamlit yfinance pandas numpy plotly
Ejecutar:    streamlit run sly_analistas_sector.py
 
Qué hace:
  1) Para cada acción (lista y sectores del V56/V57) trae de yfinance el precio objetivo a 1 año de los analistas
     (promedio, máximo, mínimo), la cantidad de analistas y la recomendación, y calcula el % de upside/downside
     contra el precio actual (como el panel "Previsión" de TradingView).
  2) Aplica la lógica SLY del script cripto (MACD DEMA 12/26/9, RSI suavizado, Heikin Ashi, EMA 52/260,
     RSI PRO con Z-score de volumen, Alpha Strike / Agotamiento, MACD mensual) para saber si hay señal VIGENTE.
  3) Todo se acumula por lotes y se organiza por sector, con un cruce "Confluencia" entre señal y upside.
 
Límites: los objetivos vienen de yfinance (no oficial, puede faltar o estar desactualizado) y los analistas
suelen ir retrasados y optimistas. Es contexto, no una recomendación de compra ni de venta.
"""
import time
 
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
 
st.set_page_config(layout="wide", page_title="SLY | ANALISTAS POR SECTOR")
st.markdown("""
<style>
    .stApp { background-color: #FFFFFF; color: #1C1E21; }
    .stDataFrame { font-size: 11px; font-family: 'Roboto Mono', monospace; }
    h1 { color: #0D47A1; font-weight: 800; border-bottom: 3px solid #0D47A1; }
    .stProgress > div > div > div > div { background-color: #0D47A1; }
    .sector-box { background-color: #E3F2FD; padding: 15px; border-radius: 8px; border-left: 5px solid #1565C0; margin-bottom: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .sector-title { font-weight: bold; color: #0D47A1; font-size: 1.1em; }
</style>
""", unsafe_allow_html=True)
 
if "an_res" not in st.session_state:
    st.session_state["an_res"] = {}
if "an_lista" not in st.session_state:
    st.session_state["an_lista"] = None
 
TF_OPTIONS = {"1 HS": ("1h", "730d"), "1 DIA": ("1d", "10y"), "1 SEMANA": ("1wk", "max")}
TF_SEC = {"1h": 3600, "1d": 86400, "1wk": 604800}
RSI_BB_MULT = 2.0
VOL_Z_THRESHOLD = 1.5
 
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
 
SECTOR_YF = {"Technology": "TECNOLOGÍA", "Financial Services": "FINANCIERO", "Energy": "ENERGÍA/OIL",
             "Consumer Cyclical": "CONSUMO/RETAIL", "Consumer Defensive": "CONSUMO/RETAIL", "Healthcare": "SALUD/BIO",
             "Industrials": "INDUSTRIAL/AÉREO", "Communication Services": "COMUNICACIONES/MEDIA",
             "Basic Materials": "MATERIALES", "Utilities": "UTILITIES", "Real Estate": "INMOBILIARIO"}
RECO_ES = {"strong_buy": "COMPRA FUERTE 🟢🟢", "buy": "COMPRA 🟢", "hold": "MANTENER ⚪",
           "underperform": "VENTA DÉBIL 🔴", "sell": "VENTA 🔴🔴"}
 
 
# ─────────────────────────────────────────────
# MOTOR TÉCNICO SLY (misma lógica que el script cripto)
# ─────────────────────────────────────────────
def dema(s, length):
    e1 = s.ewm(span=length, adjust=False).mean()
    e2 = e1.ewm(span=length, adjust=False).mean()
    return 2 * e1 - e2
 
 
def rsi_wilder(close, n=14):
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return 100 - 100 / (1 + rs)
 
 
def limpiar(df):
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
    last = df.index[-1]
    now = pd.Timestamp.now(tz=last.tz) if last.tzinfo else pd.Timestamp.now()
    return df.iloc[:-1] if last + pd.Timedelta(seconds=TF_SEC[tf]) > now else df
 
 
def get_sly_indicators(df):
    """df con columnas open/high/low/close/vol. Devuelve (df_calculado, motivo)."""
    try:
        df = df.rename(columns=lambda c: str(c).capitalize()).copy()
        df = df.dropna(subset=["Close"])
        velas = len(df)
        df["macd_line"] = dema(df["Close"], 12) - dema(df["Close"], 26)
        df["signal_line"] = df["macd_line"].ewm(span=9, adjust=False).mean()
        df["hist"] = df["macd_line"] - df["signal_line"]
        df["rsi_smooth"] = dema(rsi_wilder(df["Close"], 14).fillna(50), 5)
        df["rsi_basis"] = df["rsi_smooth"].rolling(20).mean()
        df["rsi_std"] = df["rsi_smooth"].rolling(20).std()
        df["rsi_upper"] = df["rsi_basis"] + RSI_BB_MULT * df["rsi_std"]
        df["vol_avg"] = df["Vol"].rolling(20).mean()
        df["vol_std"] = df["Vol"].rolling(20).std()
        df["vol_z"] = (df["Vol"] - df["vol_avg"]) / df["vol_std"].replace(0, np.nan)
        df["vol_alpha"] = df["vol_z"] > VOL_Z_THRESHOLD
        now_, prev_ = df["rsi_smooth"], df["rsi_smooth"].shift(1)
        conds = [(now_ > 50) & (now_ > prev_), (now_ > 50) & (now_ <= prev_),
                 (now_ < 50) & (now_ < prev_), (now_ < 50) & (now_ >= prev_)]
        df["rsi_state"] = np.select(conds, ["ALCISTA FUERTE 🟢🟢", "ALCISTA DÉBIL 🟢", "BAJISTA FUERTE 🔴🔴", "BAJISTA DÉBIL 🔴"],
                                    default="NEUTRAL ⚪")
        df["alpha_strike"] = (now_ > 50) & (prev_ <= 50) & df["vol_alpha"]
        df["exhaustion"] = (now_ < df["rsi_upper"]) & (prev_ >= df["rsi_upper"].shift(1))
        ha_c = (df["Open"] + df["High"] + df["Low"] + df["Close"]) / 4
        ha_o = np.zeros(len(df))
        ha_o[0] = (df["Open"].iloc[0] + df["Close"].iloc[0]) / 2
        for i in range(1, len(df)):
            ha_o[i] = (ha_o[i - 1] + ha_c.iloc[i - 1]) / 2
        df["ha_color"] = np.where(ha_c > ha_o, "Verde", "Rojo")
        df["ema52"] = df["Close"].ewm(span=52, adjust=False, min_periods=52).mean()
        df["ema260"] = df["Close"].ewm(span=260, adjust=False, min_periods=260).mean()
        res = df.dropna(subset=["ema260"])
        if res.empty:
            return pd.DataFrame(), f"Historial insuficiente: {velas} velas (se necesitan ≥260 para EMA260)"
        return res, "OK"
    except Exception as e:
        return pd.DataFrame(), f"Error de cálculo: {type(e).__name__}: {e}"
 
 
def macd_mensual_fuerza(sym):
    try:
        m = limpiar(yf.download(sym, interval="1mo", period="10y", progress=False, auto_adjust=True))
        if len(m) < 35:
            return "N/A"
        c = m["close"].astype(float)
        macd = dema(c, 12) - dema(c, 26)
        h = macd - macd.ewm(span=9, adjust=False).mean()
        return "GANANDO FUERZA 📈" if h.iloc[-1] > h.iloc[-2] else "PERDIENDO FUERZA 📉"
    except Exception:
        return "N/A"
 
 
def find_last_signal(df, bear_longs):
    if df.empty or len(df) < 2:
        return None, None, False, "-"
    d, px, activo, veredicto = None, None, False, "-"
    for i in range(1, len(df)):
        autorizado = (df["ema52"].iloc[i] > df["ema260"].iloc[i]) or bear_longs
        ha_flip = df["ha_color"].iloc[i] == "Verde" and df["ha_color"].iloc[i - 1] == "Rojo"
        macd_acel = df["hist"].iloc[i] > df["hist"].iloc[i - 1]
        rsi_ok = df["rsi_smooth"].iloc[i] > df["rsi_smooth"].iloc[i - 1] and df["rsi_smooth"].iloc[i] < 50
        if not activo and (autorizado and ha_flip and macd_acel and rsi_ok):
            activo, d, px = True, df.index[i], df["Close"].iloc[i]
        elif activo and (df["ha_color"].iloc[i] == "Rojo" and df["hist"].iloc[i] < df["hist"].iloc[i - 1]
                         and df["rsi_smooth"].iloc[i] < df["rsi_smooth"].iloc[i - 1]):
            activo = False
    if activo:
        c_h, p_h = df["hist"].iloc[-1], df["hist"].iloc[-2]
        if p_h > 0 and c_h <= 0:
            veredicto = "CERRAR OPERACIÓN 🔴"
        elif c_h > p_h:
            veredicto = "MANTENER 🟢"
        else:
            veredicto = "PIERDE FUERZA 🟡"
    return d, px, activo, veredicto
 
 
def senales_sly(sym, tf_lbl, solo_cerradas, bear_longs, con_mensual):
    """Devuelve el dict de columnas de señal (o lanza ValueError con el motivo)."""
    interval, period = TF_OPTIONS[tf_lbl]
    raw = yf.download(sym, interval=interval, period=period, progress=False, auto_adjust=True)
    if raw is None or raw.empty:
        raise ValueError("Sin datos de precio en yfinance")
    df = recortar(limpiar(raw), interval, solo_cerradas)
    data, motivo = get_sly_indicators(df)
    if data.empty:
        raise ValueError(motivo)
    fecha, px, vigente, verd = find_last_signal(data, bear_longs)
    last = data["Close"].iloc[-1]
    rsi = data["rsi_smooth"].iloc[-1]
    vz = data["vol_z"].iloc[-1]
    fmt = "%d/%m/%Y %H:%M" if interval == "1h" else "%d/%m/%Y"
    return {"Estado": "VIGENTE 🟢" if vigente else "CERRADA 🔴", "Veredicto": verd,
            "PnL Real %": round((last - px) / px * 100, 2) if (vigente and px) else None,
            "Última Señal": fecha.strftime(fmt) if fecha is not None else "-",
            "Zona RSI": "SOBRE 50 🟢" if rsi > 50 else "BAJO 50 🔴", "RSI PRO": data["rsi_state"].iloc[-1],
            "Vol Z-Score": round(float(vz), 2) if pd.notna(vz) else None,
            "Alpha Strike": "SÍ 🚀" if bool(data["alpha_strike"].iloc[-1]) else "-",
            "Agotamiento": "SÍ ⚠️" if bool(data["exhaustion"].iloc[-1]) else "-",
            "Régimen": "ALCISTA" if data["ema52"].iloc[-1] > data["ema260"].iloc[-1] else "BAJISTA",
            "MACD Mensual": macd_mensual_fuerza(sym) if con_mensual else "-"}, float(last)
 
 
# ─────────────────────────────────────────────
# ANALISTAS
# ─────────────────────────────────────────────
def _num(x):
    try:
        v = float(x)
        return v if np.isfinite(v) and v > 0 else None
    except (TypeError, ValueError):
        return None
 
 
def calc_analistas(info, precio_extra=None):
    """info = dict de yfinance (.info). Devuelve las columnas de analistas."""
    info = info or {}
    px = _num(info.get("currentPrice")) or _num(info.get("regularMarketPrice")) or _num(info.get("previousClose")) or _num(precio_extra)
    tm, th, tl, tmed = (_num(info.get(k)) for k in ("targetMeanPrice", "targetHighPrice", "targetLowPrice", "targetMedianPrice"))
    n = info.get("numberOfAnalystOpinions")
    n = int(n) if n is not None and np.isfinite(float(n)) else 0
    up = lambda t: round((t / px - 1) * 100, 2) if (t and px) else None
    disp = round((th - tl) / px * 100, 1) if (th and tl and px) else None
    rk = RECO_ES.get(str(info.get("recommendationKey") or "").lower(), "-")
    rm = _num(info.get("recommendationMean"))
    return {"Precio": round(px, 4) if px else None, "Obj. Prom": tm, "Upside Prom %": up(tm), "Obj. Mediana": tmed,
            "Obj. Máx": th, "Upside Máx %": up(th), "Obj. Mín": tl, "Upside Mín %": up(tl),
            "Dispersión %": disp, "Analistas": n, "Consenso": rk, "Nota (1=compra, 5=venta)": round(rm, 2) if rm else None,
            "Cobertura": "OK" if (tm and px) else "Sin objetivos"}
 
 
def lectura_upside(u):
    if u is None or (isinstance(u, float) and np.isnan(u)):
        return "-"
    if u >= 15:
        return "UPSIDE ALTO ≥15%"
    if u >= 5:
        return "UPSIDE MODERADO"
    if u > -5:
        return "CERCA DEL OBJETIVO"
    return "SOBRE EL OBJETIVO"
 
 
def fetch_analistas(sym):
    t = yf.Ticker(sym)
    info = t.info or {}
    return calc_analistas(info), info.get("sector")
 
 
def resumen_sector(df, min_analistas):
    """Resumen por sector sobre las filas con cobertura suficiente."""
    ok = df[(df["Cobertura"] == "OK") & (df["Analistas"] >= min_analistas)].copy()
    if ok.empty:
        return pd.DataFrame()
    filas = []
    for sec, g in ok.groupby("Sector"):
        mejor = g.sort_values("Upside Prom %", ascending=False).iloc[0]
        vig = int((g["Estado"] == "VIGENTE 🟢").sum()) if "Estado" in g.columns else 0
        filas.append({"Sector": sec, "Acciones": len(g), "Upside mediano %": round(g["Upside Prom %"].median(), 2),
                      "Upside promedio %": round(g["Upside Prom %"].mean(), 2),
                      "% con upside > 0": round((g["Upside Prom %"] > 0).mean() * 100, 0),
                      "Señales vigentes": vig, "Mejor upside": f"{mejor['Activo']} ({mejor['Upside Prom %']:+.1f}%)"})
    return pd.DataFrame(filas).sort_values("Upside mediano %", ascending=False).reset_index(drop=True)
 
 
@st.cache_data(ttl=3600, show_spinner=False)
def historial_2a(sym):
    raw = yf.download(sym, interval="1d", period="2y", progress=False, auto_adjust=True)
    return limpiar(raw)["close"].astype(float) if raw is not None and not raw.empty else pd.Series(dtype=float)
 
 
def figura_abanico(sym, r, hist):
    px = r["Precio"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist.index, y=hist.values, mode="lines", name="Precio", line=dict(color="#1565C0", width=2)))
    if len(hist):
        x0 = hist.index[-1]
        x1 = x0 + pd.Timedelta(days=365)
        fig.add_trace(go.Scatter(x=[x0, x1], y=[px, r["Obj. Máx"]], mode="lines", name=f"Máx {r['Upside Máx %']:+.1f}%",
                                 line=dict(color="#2E7D32", dash="dot")))
        fig.add_trace(go.Scatter(x=[x0, x1], y=[px, r["Obj. Mín"]], mode="lines", name=f"Mín {r['Upside Mín %']:+.1f}%",
                                 line=dict(color="#C62828", dash="dot"), fill="tonexty", fillcolor="rgba(120,120,120,0.10)"))
        fig.add_trace(go.Scatter(x=[x0, x1], y=[px, r["Obj. Prom"]], mode="lines", name=f"Promedio {r['Upside Prom %']:+.1f}%",
                                 line=dict(color="#F9A825", width=2)))
    fig.update_layout(height=430, margin=dict(l=0, r=0, t=30, b=0), plot_bgcolor="white",
                      title=f"{sym}: precio y objetivos a 1 año ({r['Analistas']} analistas)", legend=dict(orientation="h", y=-0.15))
    return fig
 
 
# ═════════════════════════════════════════════
# INTERFAZ
# ═════════════════════════════════════════════
st.title("🎯 SLY | ANALISTAS POR SECTOR")
st.caption("Objetivos de precio de analistas (yfinance) + señales SLY, agrupados por sector. Contexto, no recomendación.")
 
with st.sidebar:
    st.header("⚙️ Configuración")
    st.subheader("1. Universo")
    sectores = ["TODOS"] + list(SECTOR_MAP.keys()) + ["OTROS / SMALL CAPS"]
    sec_sel = st.selectbox("Escanear sector:", sectores)
    excl_etf = st.checkbox("Excluir ETFs/índices (no tienen objetivos)", value=True)
    lista = [t for t in TICKERS if (sec_sel == "TODOS" or get_sector(t) == sec_sel)]
    if excl_etf:
        etfs = set(SECTOR_MAP["ÍNDICES/ETFs"])
        lista = [t for t in lista if t not in etfs]
    lista = sorted(lista, key=lambda t: (get_sector(t), t))
    st.caption(f"{len(lista)} tickers en esta selección")
 
    st.subheader("2. Señales SLY")
    con_senales = st.checkbox("Calcular señales SLY", value=True)
    tf_lbl = st.selectbox("Temporalidad:", list(TF_OPTIONS.keys()), index=1)
    solo_cerradas = st.checkbox("Solo velas cerradas", value=True)
    bear_longs = st.checkbox("Habilitar Bear-Longs", value=True)
    con_mensual = st.checkbox("MACD mensual (1 pedido extra)", value=False)
 
    st.subheader("3. Ejecución")
    lote_size = st.number_input("Tamaño de lote:", 5, 100, 25)
    total_lotes = max(1, (len(lista) - 1) // int(lote_size) + 1)
    batch_idx = st.selectbox("Lote:", range(total_lotes), format_func=lambda x: f"Lote {x + 1}")
    if st.button("🚀 ACTUALIZAR Y ACUMULAR", type="primary", use_container_width=True):
        subset = lista[batch_idx * int(lote_size):(batch_idx + 1) * int(lote_size)]
        prog = st.progress(0)
        for i, sym in enumerate(subset):
            prog.progress((i + 1) / len(subset), text=f"Analizando {sym}")
            fila = {"Activo": sym, "Sector": get_sector(sym), "Motivo": "OK"}
            sector_yf = None
            try:
                a, sector_yf = fetch_analistas(sym)
                fila.update(a)
            except Exception as e:
                fila.update({"Cobertura": "Sin objetivos", "Analistas": 0})
                fila["Motivo"] = f"Analistas: {type(e).__name__}: {str(e)[:120]}"
            if fila["Sector"] == "OTROS / SMALL CAPS" and sector_yf in SECTOR_YF:
                fila["Sector"] = SECTOR_YF[sector_yf]
            if con_senales:
                try:
                    s, last_px = senales_sly(sym, tf_lbl, solo_cerradas, bear_longs, con_mensual)
                    fila.update(s)
                    if fila.get("Precio") is None:
                        fila["Precio"] = round(last_px, 4)
                except Exception as e:
                    fila["Estado"] = "SIN CÁLCULO ⚪"
                    fila["Motivo"] = (fila["Motivo"] + " | " if fila["Motivo"] != "OK" else "") + f"Señales: {str(e)[:120]}"
            st.session_state["an_res"][sym] = fila
            time.sleep(0.1)
        prog.empty()
        st.rerun()
    if st.button("🗑️ Limpiar memoria"):
        st.session_state["an_res"] = {}
        st.rerun()
 
if not st.session_state["an_res"]:
    st.info("👈 Elegí un sector (o TODOS), un lote y tocá ACTUALIZAR Y ACUMULAR.")
    st.stop()
 
df = pd.DataFrame(st.session_state["an_res"].values())
for c in ("Estado", "Veredicto", "Consenso", "Cobertura"):
    if c not in df.columns:
        df[c] = "-"
if "Analistas" not in df.columns:
    df["Analistas"] = 0
for c in ("Upside Prom %", "Upside Máx %", "Upside Mín %", "Precio", "Obj. Prom", "Obj. Máx", "Obj. Mín", "Dispersión %"):
    if c not in df.columns:
        df[c] = np.nan
df["Analistas"] = pd.to_numeric(df["Analistas"], errors="coerce").fillna(0).astype(int)
 
f1, f2, f3, f4 = st.columns(4)
min_an = f1.number_input("Mínimo de analistas", 0, 60, 5)
umbral = f2.number_input("Upside mínimo para confluencia (%)", 0.0, 100.0, 15.0, 1.0)
solo_vig = f3.checkbox("Solo señales VIGENTES", value=False)
solo_cob = f4.checkbox("Solo con objetivos", value=True)
secs_disp = sorted(df["Sector"].unique())
secs_sel = st.multiselect("Sectores a mostrar", secs_disp, default=secs_disp)
 
df["Lectura upside"] = df["Upside Prom %"].map(lectura_upside) if "Upside Prom %" in df.columns else "-"
vig = df["Estado"] == "VIGENTE 🟢"
up_ok = (df.get("Upside Prom %", pd.Series(np.nan, index=df.index)) >= umbral) & (df["Analistas"] >= min_an)
sobre = df.get("Upside Prom %", pd.Series(np.nan, index=df.index)) < 0
df["Confluencia"] = np.select([vig & up_ok, vig & sobre], ["LONG + upside de analistas ✅", "LONG pero precio sobre objetivo ⚠️"], default="-")
 
vista = df[df["Sector"].isin(secs_sel)]
if solo_vig:
    vista = vista[vista["Estado"] == "VIGENTE 🟢"]
if solo_cob:
    vista = vista[(vista["Cobertura"] == "OK") & (vista["Analistas"] >= min_an)]
 
COLS = ["Activo", "Sector", "Precio", "Obj. Prom", "Upside Prom %", "Obj. Máx", "Upside Máx %", "Obj. Mín", "Upside Mín %",
        "Dispersión %", "Analistas", "Consenso", "Nota (1=compra, 5=venta)", "Lectura upside", "Confluencia", "Estado", "Veredicto",
        "PnL Real %", "Última Señal", "Zona RSI", "RSI PRO", "Vol Z-Score", "Alpha Strike", "Agotamiento", "Régimen", "MACD Mensual", "Motivo"]
COLS = [c for c in COLS if c in vista.columns]
 
 
def color_cells(val):
    s = str(val)
    if "ALCISTA FUERTE" in s or "SÍ 🚀" in s or "COMPRA FUERTE" in s or "UPSIDE ALTO" in s or "upside de analistas" in s:
        return "background-color: #A5D6A7; color: #1B5E20; font-weight: bold;"
    if "VIGENTE" in s or "MANTENER 🟢" in s or "ALCISTA" in s or "SOBRE 50" in s or "GANANDO" in s or "COMPRA" in s or "UPSIDE MODERADO" in s:
        return "background-color: #C8E6C9; color: #1B5E20; font-weight: bold;"
    if "BAJISTA FUERTE" in s or "VENTA 🔴🔴" in s:
        return "background-color: #EF9A9A; color: #B71C1C; font-weight: bold;"
    if "CERRADA" in s or "CERRAR" in s or "BAJISTA" in s or "BAJO 50" in s or "PERDIENDO" in s or "VENTA" in s or "SOBRE EL OBJETIVO" in s or "sobre objetivo" in s:
        return "background-color: #FFCDD2; color: #B71C1C; font-weight: bold;"
    if "PIERDE FUERZA" in s or "SÍ ⚠️" in s or "CERCA DEL OBJETIVO" in s:
        return "background-color: #FFF9C4; color: #827717; font-weight: bold;"
    return ""
 
 
def color_up(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ""
    if v >= 15:
        return "color: #1B5E20; font-weight: bold;"
    if v < 0:
        return "color: #B71C1C; font-weight: bold;"
    return ""
 
 
def estilo(d):
    st_ = d.style.map(color_cells)
    ups = [c for c in ("Upside Prom %", "Upside Máx %", "Upside Mín %", "PnL Real %") if c in d.columns]
    if ups:
        st_ = st_.map(color_up, subset=ups)
    return st_
 
 
m1, m2, m3 = st.columns(3)
m1.metric("Acciones acumuladas", len(df))
m2.metric("Con objetivos de analistas", int((df["Cobertura"] == "OK").sum()))
m3.metric("Con confluencia ✅", int((df["Confluencia"] == "LONG + upside de analistas ✅").sum()))
 
tab_sec, tab_mat, tab_det = st.tabs(["🏭 Por sector", "📋 Matriz completa", "🎯 Detalle de una acción"])
 
with tab_sec:
    rs = resumen_sector(df[df["Sector"].isin(secs_sel)], min_an)
    if rs.empty:
        st.warning("Ningún sector tiene acciones con objetivos y el mínimo de analistas elegido.")
    else:
        colores = ["#2E7D32" if v >= 0 else "#C62828" for v in rs["Upside mediano %"]]
        fig = go.Figure(go.Bar(x=rs["Sector"], y=rs["Upside mediano %"], marker_color=colores,
                               text=[f"{v:+.1f}%" for v in rs["Upside mediano %"]], textposition="outside"))
        fig.update_layout(height=340, margin=dict(l=0, r=0, t=30, b=0), plot_bgcolor="white",
                          title="Upside mediano al precio objetivo promedio, por sector", yaxis_title="%")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(rs, use_container_width=True, hide_index=True)
    st.subheader("Acciones por sector")
    for sec in secs_sel:
        g = vista[vista["Sector"] == sec].sort_values("Upside Prom %", ascending=False, na_position="last")
        if g.empty:
            continue
        nvig = int((g["Estado"] == "VIGENTE 🟢").sum())
        with st.expander(f"{sec} — {len(g)} acciones · {nvig} con señal vigente"):
            st.dataframe(estilo(g[COLS]), use_container_width=True, hide_index=True)
 
with tab_mat:
    st.dataframe(estilo(vista[COLS].sort_values(["Sector", "Upside Prom %"], ascending=[True, False], na_position="last")),
                 use_container_width=True, height=600, hide_index=True)
 
with tab_det:
    con_obj = vista[vista["Cobertura"] == "OK"]["Activo"].tolist()
    if not con_obj:
        st.info("No hay acciones con objetivos en la vista actual.")
    else:
        pick = st.selectbox("Acción:", con_obj)
        r = df[df["Activo"] == pick].iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Precio", f"{r['Precio']:.2f}")
        c2.metric("Objetivo promedio", f"{r['Obj. Prom']:.2f}", f"{r['Upside Prom %']:+.1f}%")
        c3.metric("Máximo", f"{r['Obj. Máx']:.2f}", f"{r['Upside Máx %']:+.1f}%")
        c4.metric("Mínimo", f"{r['Obj. Mín']:.2f}", f"{r['Upside Mín %']:+.1f}%")
        st.caption(f"{int(r['Analistas'])} analistas · consenso {r['Consenso']} · dispersión {r['Dispersión %']}% del precio. "
                   "Una dispersión muy grande indica poca coincidencia entre analistas.")
        hist = historial_2a(pick)
        if len(hist):
            st.plotly_chart(figura_abanico(pick, r, hist), use_container_width=True)
 
st.caption("Objetivos y recomendaciones: yfinance (no oficial; pueden faltar o estar atrasados). 'Confluencia' = señal SLY VIGENTE + "
           "upside promedio ≥ umbral con el mínimo de analistas; no es una recomendación de compra.")
 
