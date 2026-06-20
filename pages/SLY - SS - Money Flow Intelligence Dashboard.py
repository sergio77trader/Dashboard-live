import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import plotly.express as px
import time
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# CONFIGURACIÓN INSTITUCIONAL SLY
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | MASTER INTELLIGENCE", page_icon="🦅")

# PROCESAMIENTO DE LISTA MAESTRA PARA RECONOCIMIENTO ByMA
RAW_TICKERS_STR = "BIL, SPY, QQQ, ARKK, BOTZ, DBC, GLD, BND, VWO, VNQ, HYG, VEA, EMB, AAPL, AMZN, TSLA, MSFT, META, NVDA, GOOGL, ARGT, MELI, GLOB, TTWO, RKLB, HOOD, HOG, MSTR, COIN, SWK, INTC, AMD, DIS, GME, ABNB, AMC, KO, DIA, F, ADBE, MO, C, COST, DE, DOCU, GE, ETSY, HAL, CRM, HSBC, IBM, JD, JNJ, LMT, MA, MCD, NFLX, NKE, PYPL, PEP, PBR, SHOP, SNAP, SONY, SPOT, SBUX, TGT, UL, WMT, SMCI, JPM, WFC, AVGO, MU, LLY, UNH, V, QCOM, HD, BAC, GGAL, BABA, YPF, PAM, XOM, AMAT, GS, ACN, MARA, SNOW, ORCL, UBER, DELL, LRCX, CVX, CSCO, CRWD, CVNA, BA, VRT, HUBS, MRK, PLTR, NEE, CAT, PFE, LIN, CMG, GM, BKNG, PG, MRVL, LOW, TXN, ADI, MS, DAL, AMGN, T, LCID, ABBV, NOW, UPS, LEN, BMY, ENPH, SOUN, INTU, SPGI, CMCSA, DHR, AXP, DHI, RTX, BK, CME, PANW, KLAC, BLK, ICE, MDLZ, MRNA, VOO, VTI, VUG, VTV, IWF, IJH, IJR, VIG, VGT, XLK, VO, IWM, TLT, VB, SCHX, XLF, XLV, SCHF, MUB, XLE, XLI, XLY, VHT, SOXX, PHO, XLRE, SCHH, IYR, ICF, DUOL, LUV, AFRM, ITA, SH, IEF, VGIT, GOVT, SGOV, IBIT, EETH, SATL, RMAX, COMP, AGNT, OPAD, OPEN, SSO, SCHD, EWJ, EWZ, EWW, ECH, INDA, EWT, EWS, ENZL, EWA, DGRO, PINS, ZM, ULTA, PM, SCHW, MMM, FDX, CVS, PSX, DASH, KMB, MSI, MNST, TMO, EA, TMUS, ABT, BX, VZ, ISRG, DDOG, MCHI, BSV, IFS, BAP, BVN, TQQQ, SOXL, TMF, SPXL, UPRO, TECL, YINN, SQQQ, FAS, TNA, LABU, SPXS, SOXS, MCO, CL, MAR, KDP, UNP, TEAM, GEHC, SOFI, CCL, NET, WST, MKC, GDDY, HPE, MDB, WBD, KHC, EBAY, HLT, FISV, EEM, AAL, JMIA, BP, BB, BBD, SVXY, REK, VIST, ADM, TSM, RIOT, TLRY, NOC, CGC, GD, IIPR, SYM, NU, ANET, OXY, O, ASML, VEGI, OKLO, PFF, RDDT, SPYD, HSY, PTON, DJT, BITX, KODK, VIXY, RACE, LULU, HMC, FWONK, TS, TX, HIMS, ITUB, ABEV, BIDU, GRWG, HYFM, MANU, FAZ, FNGU, MSFU, AAPU, FBL, LOMA, DLTR, DUK, GPRK, NEM, SO, QBTS, RGTI, BITI, PCAR, NVO, UMAC, AXON, XYZ, PDD, NTES, SOS, RCAT, BN, VALE, ARM, QSI, TM, WM, URTH, BBAR, IRS, BIOX, EDN, SUPV, XP, BBAI, DAPP, TEM, KULR, INBS, TBX, EAT, LMND, UUUU, GDX, ASTS, RCL, APP, PAGS, TTT, UNCY, PL, NIO, CONY, CLOV, JOBY, UGL, TBF, BYND, TWLO, MMSI, LODE, TBT, CEG, UUP, OTLY, SHY, IEI, TLH, IREN, NWTG, FLIN, OSCR, ALAB, AMZY, APLY, AVY, BG, BIIB, BMA, CELH, CEPU, CRESY, DOW, DPZ, EWY, FXI, FXY, HON, HUT, IGPT, LAES, ONON, PYPY, SEDG, SLB, SNA, STLA, STZ, TTEK, URBN, VSCO, AAP, YBIT, ADP, HERO, ABSI, PDBA, MAGS, B, SMMT, SETH, SLV, PATH, AIQ, SHEL, TGS, PSQ, MKL, XLP, XPEV, DXYZ, MSTY, CRCL, PLBY, FIG, AOM, OWNB, BKR, SPYG, USO, APLD, ASPN, AUR, BITO, BKCH, BLDR, BLOK, CDNS, COO, DAVA, EIX, EL, ELF, EVTL, FEZ, FSLR, GAUZ, GPN, HDV, HELO, BMRN, VXUS, URA, ACWI, NVDL, GRAB, GTLB, VT, SPMO, QQQM, IONQ, TSLL, AMZU, SBET, JEPQ, JEPI, QYLD, TXRH, ABCL, AOK, VBR, IAU, IEO, ZETA, KBH, OMC, RYDE, SVCO, POOL, VYM, ANF, TMDX, MTUM, BMNR, TMQ, BNKK, VEEE, QNRX, HRZN"
CLEAN_TICKERS = [t.strip() for t in RAW_TICKERS_STR.split(",")]

# ─────────────────────────────────────────────
# DATABASE CLASIFICADA POR SECTORES
# ─────────────────────────────────────────────
ASSET_DATABASE = {
    "Índices & ETFs Core": ["Benchmarks Globales", ["SPY", "QQQ", "DIA", "IWM", "VOO", "VTI", "VUG", "VTV", "IWF"]],
    "Tecnología (Semiconductores)": ["Hardware & Chips", ["NVDA", "AMD", "AVGO", "SMCI", "INTC", "MU", "TSM", "ASML", "KLAC", "LRCX", "AMAT", "ARM"]],
    "Tecnología (Software & SaaS)": ["Cloud & AI", ["MSFT", "ORCL", "CRM", "ADBE", "SNOW", "NOW", "PLTR", "DOCU", "TEAM", "WDAY"]],
    "Big Tech (Mag 7 & Social)": ["Mega Caps", ["AAPL", "AMZN", "META", "GOOGL", "NFLX", "TSLA"]],
    "Financiero (Bancos & Pagos)": ["Banks & Fintech", ["JPM", "BAC", "WFC", "GS", "MS", "C", "V", "MA", "PYPL", "AXP", "HOOD", "SQ"]],
    "Energía & Oil": ["Energy Sector", ["XOM", "CVX", "PBR", "SLB", "HAL", "OXY", "PSX", "VIST", "YPF", "XLE"]],
    "Argentina (ADRs & Locals)": ["ByMA Favorites", ["GGAL", "YPF", "PAM", "BMA", "TGS", "CEPU", "EDN", "MELI", "GLOB", "LOMA", "CRESY", "TX", "BBAR", "IRS", "SUPV"]],
    "Crypto & Blockchain": ["Digital Assets Proxy", ["BTC-USD", "MSTR", "COIN", "MARA", "RIOT", "IBIT", "BITX", "IREN", "CLSK"]],
    "Consumo & Retail": ["Retail & Staples", ["WMT", "COST", "KO", "PEP", "MCD", "SBUX", "NKE", "TGT", "PG", "PM", "HD", "LOW"]],
    "Salud & BioTech": ["Healthcare", ["LLY", "UNH", "JNJ", "ABBV", "MRK", "PFE", "AMGN", "BMY", "DHR", "TMO"]],
    "Industrial & Aeroespacial": ["Industrials", ["GE", "CAT", "HON", "BA", "LMT", "RTX", "DE", "UNP", "UPS", "FDX"]],
    "Emergentes & China": ["International Flow", ["EEM", "BABA", "JD", "BIDU", "PDD", "NTES", "FXI", "EWZ", "VALE", "ITUB", "BBD"]],
    "Renta Fija (Bonos & Tasas)": ["Fixed Income", ["BIL", "BND", "TLT", "SHY", "IEF", "GOVT", "SGOV", "HYG", "MUB"]],
    "Commodities & Real Estate": ["Hard Assets", ["GLD", "SLV", "DBC", "VNQ", "XLRE", "IYR", "PHO", "NEM", "GOLD", "PAAS"]]
}

st.markdown("""
<style>
    .stApp { background-color: #0B0E11; color: #EAECEF; }
    .report-card { background-color: #1E2329; padding: 15px; border-radius: 10px; border-left: 5px solid #F0B90B; margin-bottom: 10px; }
    .verdict-title { color: #F0B90B; font-weight: bold; font-size: 1.2em; }
    .stDataFrame { font-size: 12px; font-family: 'Roboto Mono', monospace; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# MOTORES TÉCNICOS SLY
# ─────────────────────────────────────────────
def run_sly_engine(df):
    if df.empty or len(df) < 35: return 0, 0, None
    macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
    hist = macd['MACDh_12_26_9']
    ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    ha_open = np.zeros(len(df))
    ha_open[0] = (df['Open'].iloc[0] + df['Close'].iloc[0]) / 2
    for i in range(1, len(df)): ha_open[i] = (ha_open[i-1] + ha_close.iloc[i-1]) / 2
    ha_dir = np.where(ha_close > ha_open, 1, -1)
    state, entry_px, entry_tm = 0, 0.0, None
    for i in range(1, len(df)):
        h, h_prev, hd, hd_prev = hist.iloc[i], hist.iloc[i-1], ha_dir[i], ha_dir[i-1]
        if (hd == 1 and hd_prev == -1 and h < 0 and h > h_prev): state, entry_px, entry_tm = 1, df['Close'].iloc[i], df.index[i]
        elif (hd == -1 and hd_prev == 1 and h > 0 and h < h_prev): state, entry_px, entry_tm = -1, df['Close'].iloc[i], df.index[i]
        elif state != 0:
            if (state == 1 and h < h_prev) or (state == -1 and h > h_prev): state = 0
    return state, entry_px, entry_tm

def analyze_asset(symbol, category):
    row = {"Categoría": category, "Activo": symbol}
    row["ByMA"] = "✅" if symbol.upper() in CLEAN_TICKERS else "❌"
    for tf, config in MACRO_CONFIG.items():
        try:
            df = yf.download(symbol, interval=config['int'], period=config['per'], progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if tf == "1D" and not df.empty: row["Precio"] = f"{df['Close'].iloc[-1]:,.2f}"
            st_val, px_in, tm_in = run_sly_engine(df)
            if st_val != 0:
                pnl = (df['Close'].iloc[-1] - px_in) / px_in * 100 if st_val == 1 else (px_in - df['Close'].iloc[-1]) / px_in * 100
                row[f"{tf} Signal"] = "LONG 🟢" if st_val == 1 else "SHORT 🔴"
                row[f"{tf} PnL"] = f"{pnl:.2f}%"
            else: row[f"{tf} Signal"] = "FUERA ⚪"
        except: row[f"{tf} Signal"] = "ERR"
    return row

# ─────────────────────────────────────────────
# UI - MONEY FLOW & TRAYECTORIA
# ─────────────────────────────────────────────
st.title("🦅 SLY MASTER FLOW & SECTORIAL AUDITOR")
MACRO_CONFIG = {"1D": {"int": "1d", "per": "2y"}, "1S": {"int": "1wk", "per": "5y"}, "1M": {"int": "1mo", "per": "max"}}

with st.sidebar:
    lookback = st.selectbox("Ventana Flujo:", ["1 Mes", "3 Meses", "YTD"], index=0)
    markets_sel = st.multiselect("Filtros Dashboard:", ["XLK", "XLF", "XLE", "XLV", "XLI", "XLP", "XLB", "XLU", "XLY", "XLC", "XLRE", "SPY", "QQQ", "BTC-USD", "GLD"], default=["SPY", "QQQ", "XLK", "XLE"])

if markets_sel:
    today = datetime.now()
    dates = {"1 Mes": 30, "3 Meses": 90, "YTD": (today - datetime(today.year, 1, 1)).days}
    df_f = yf.download(markets_sel, start=today - timedelta(days=dates[lookback]), progress=False)
    
    if not df_f.empty:
        c, v = df_f['Close'].ffill().bfill(), df_f['Volume'].ffill().fillna(0)
        ret = ((c.iloc[-1] / c.iloc[0].replace(0, np.nan)) - 1) * 100
        rv = v.iloc[-5:].mean() / v.mean().replace(0, np.nan)
        score = (ret * rv).dropna()
        stats_df = pd.DataFrame({"Ret %": ret, "RVOL": rv, "Score": score}).sort_values("Score", ascending=False)

        st.subheader("🕵️ Veredicto Forense")
        v1, v2 = st.columns(2)
        with v1: st.markdown(f"<div class='report-card'><div class='verdict-title'>🚀 TOP FLOW</div>{stats_df.index[0]}</div>", unsafe_allow_html=True)
        with v2: st.markdown(f"<div class='report-card'><div class='verdict-title'>⚠️ TOP DUMP</div>{stats_df.index[-1]}</div>", unsafe_allow_html=True)

        c1, c2 = st.columns([2, 1])
        with c1: st.plotly_chart(px.scatter(stats_df, x="Ret %", y="RVOL", size=stats_df["Score"].abs().clip(lower=5), color="Score", text=stats_df.index, template="plotly_dark"), use_container_width=True)
        with c2: st.dataframe(stats_df.style.background_gradient(cmap='RdYlGn', subset=['Score']), use_container_width=True)
        
        st.subheader("📈 Trayectoria Acumulada")
        st.line_chart((c / c.iloc[0] - 1) * 100)

# ─────────────────────────────────────────────
# UI - AUDITORÍA SECTORIAL (MASTER DB)
# ─────────────────────────────────────────────
st.divider()
st.header("🔍 Auditoría Sectorial (Master List)")
sector_sel = st.selectbox("Seleccione Sector para auditar componentes:", list(ASSET_DATABASE.keys()))

if st.button(f"🔎 ESCANEAR SECTOR: {sector_sel}"):
    tickers = ASSET_DATABASE[sector_sel][1]
    res = []
    prog = st.progress(0)
    for i, t in enumerate(tickers):
        prog.progress((i+1)/len(tickers), text=f"Auditando: {t}")
        res.append(analyze_asset(t, sector_sel))
    
    df_res = pd.DataFrame(res)
    def style_sig(v):
        if "LONG" in str(v): return 'background-color: #1B5E20; color: white;'
        if "SHORT" in str(v): return 'background-color: #B71C1C; color: white;'
        return ''
    st.dataframe(df_res[["ByMA", "Activo", "Precio", "1D Signal", "1D PnL", "1S Signal", "1S PnL", "1M Signal", "1M PnL"]].style.applymap(style_sig), use_container_width=True)
