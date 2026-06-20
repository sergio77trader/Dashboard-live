import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# CONFIGURACIÓN INSTITUCIONAL SLY
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | MASTER SECTORIAL", page_icon="🦅")

# PROCESAMIENTO DE LISTA MAESTRA
RAW_TICKERS_STR = "BIL, SPY, QQQ, ARKK, BOTZ, DBC, GLD, BND, VWO, VNQ, HYG, VEA, EMB, AAPL, AMZN, TSLA, MSFT, META, NVDA, GOOGL, ARGT, MELI, GLOB, TTWO, RKLB, HOOD, HOG, MSTR, COIN, SWK, INTC, AMD, DIS, GME, ABNB, AMC, KO, DIA, F, ADBE, MO, C, COST, DE, DOCU, GE, ETSY, HAL, CRM, HSBC, IBM, JD, JNJ, LMT, MA, MCD, NFLX, NKE, PYPL, PEP, PBR, SHOP, SNAP, SONY, SPOT, SBUX, TGT, UL, WMT, SMCI, JPM, WFC, AVGO, MU, LLY, UNH, V, QCOM, HD, BAC, GGAL, BABA, YPF, PAM, XOM, AMAT, GS, ACN, MARA, SNOW, ORCL, UBER, DELL, LRCX, CVX, CSCO, CRWD, CVNA, BA, VRT, HUBS, MRK, PLTR, NEE, CAT, PFE, LIN, CMG, GM, BKNG, PG, MRVL, LOW, TXN, ADI, MS, DAL, AMGN, T, LCID, ABBV, NOW, UPS, LEN, BMY, ENPH, SOUN, INTU, SPGI, CMCSA, DHR, AXP, DHI, RTX, BK, CME, PANW, KLAC, BLK, ICE, MDLZ, MRNA, VOO, VTI, VUG, VTV, IWF, IJH, IJR, VIG, VGT, XLK, VO, IWM, TLT, VB, SCHX, XLF, XLV, SCHF, MUB, XLE, XLI, XLY, VHT, SOXX, PHO, XLRE, SCHH, IYR, ICF, DUOL, LUV, AFRM, ITA, SH, IEF, VGIT, GOVT, SGOV, IBIT, EETH, SATL, RMAX, COMP, AGNT, OPAD, OPEN, SSO, SCHD, EWJ, EWZ, EWW, ECH, INDA, EWT, EWS, ENZL, EWA, DGRO, PINS, ZM, ULTA, PM, SCHW, MMM, FDX, CVS, PSX, DASH, KMB, MSI, MNST, TMO, EA, TMUS, ABT, BX, VZ, ISRG, DDOG, MCHI, BSV, IFS, BAP, BVN, TQQQ, SOXL, TMF, SPXL, UPRO, TECL, YINN, SQQQ, FAS, TNA, LABU, SPXS, SOXS, MCO, CL, MAR, KDP, UNP, TEAM, GEHC, SOFI, CCL, NET, WST, MKC, GDDY, HPE, MDB, WBD, KHC, EBAY, HLT, FISV, EEM, AAL, JMIA, BP, BB, BBD, SVXY, REK, VIST, ADM, TSM, RIOT, TLRY, NOC, CGC, GD, IIPR, SYM, NU, ANET, OXY, O, ASML, VEGI, OKLO, PFF, RDDT, SPYD, HSY, PTON, DJT, BITX, KODK, VIXY, RACE, LULU, HMC, FWONK, TS, TX, HIMS, ITUB, ABEV, BIDU, GRWG, HYFM, MANU, FAZ, FNGU, MSFU, AAPU, FBL, LOMA, DLTR, DUK, GPRK, NEM, SO, QBTS, RGTI, BITI, PCAR, NVO, UMAC, AXON, XYZ, PDD, NTES, SOS, RCAT, BN, VALE, ARM, QSI, TM, WM, URTH, BBAR, IRS, BIOX, EDN, SUPV, XP, BBAI, DAPP, TEM, KULR, INBS, TBX, EAT, LMND, UUUU, GDX, ASTS, RCL, APP, PAGS, TTT, UNCY, PL, NIO, CONY, CLOV, JOBY, UGL, TBF, BYND, TWLO, MMSI, LODE, TBT, CEG, UUP, OTLY, SHY, IEI, TLH, IREN, NWTG, FLIN, OSCR, ALAB, AMZY, APLY, AVY, BG, BIIB, BMA, CELH, CEPU, CRESY, DOW, DPZ, EWY, FXI, FXY, HON, HUT, IGPT, LAES, ONON, PYPY, SEDG, SLB, SNA, STLA, STZ, TTEK, URBN, VSCO, AAP, YBIT, ADP, HERO, ABSI, PDBA, MAGS, B, SMMT, SETH, SLV, PATH, AIQ, SHEL, TGS, PSQ, MKL, XLP, XPEV, DXYZ, MSTY, CRCL, PLBY, FIG, AOM, OWNB, BKR, SPYG, USO, APLD, ASPN, AUR, BITO, BKCH, BLDR, BLOK, CDNS, COO, DAVA, EIX, EL, ELF, EVTL, FEZ, FSLR, GAUZ, GPN, HDV, HELO, BMRN, VXUS, URA, ACWI, NVDL, GRAB, GTLB, VT, SPMO, QQQM, IONQ, TSLL, AMZU, SBET, JEPQ, JEPI, QYLD, TXRH, ABCL, AOK, VBR, IAU, IEO, ZETA, KBH, OMC, RYDE, SVCO, POOL, VYM, ANF, TMDX, MTUM, BMNR, TMQ, BNKK, VEEE, QNRX, HRZN"
CLEAN_TICKERS = [t.strip() for t in RAW_TICKERS_STR.split(",")]

# ─────────────────────────────────────────────
# DATABASE MAPEADA POR TICKERS DE SECTOR
# ─────────────────────────────────────────────
ASSET_DATABASE = {
    "XLK (Tecnología)": ["Tech Drivers", ["AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "ADBE", "CRM", "AMD", "INTC", "QCOM", "TXN", "ADI", "MU", "SNOW", "NOW", "PANW", "KLAC", "ASML", "LRCX", "AMAT", "ARM"]],
    "XLF (Financiero)": ["Finance Drivers", ["JPM", "V", "MA", "BAC", "GS", "MS", "WFC", "BLK", "AXP", "C", "CME", "ICE", "SPGI", "SCHW", "HOOD", "SQ", "PYPL"]],
    "XLE (Energía)": ["Energy Drivers", ["XOM", "CVX", "COP", "SLB", "OXY", "PSX", "VLO", "MPC", "HAL", "BKR", "VIST", "YPF", "PBR"]],
    "XLV (Salud)": ["Healthcare Drivers", ["LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "PFE", "AMGN", "GILD", "BMY", "DHR", "ISRG", "VRTX"]],
    "XLI (Industrial)": ["Industrial Drivers", ["GE", "CAT", "UNP", "HON", "RTX", "DE", "LMT", "BA", "UPS", "FDX", "NSC", "LUV", "MMM"]],
    "XLP (Consumo Básico)": ["Staples Drivers", ["PG", "COST", "PEP", "KO", "PM", "WMT", "MO", "MDLZ", "CL", "KMB", "MNST", "UL"]],
    "XLY (Consumo Discrecional)": ["Disc. Drivers", ["AMZN", "TSLA", "HD", "MCD", "NKE", "BKNG", "SBUX", "TJX", "LOW", "LULU", "F", "GM", "CMG"]],
    "XLB (Materiales)": ["Materials Drivers", ["LIN", "SHW", "APD", "FCX", "CTVA", "ECL", "NEM", "ALB", "GOLD", "PAAS", "TX", "VALE"]],
    "XLC (Comunicaciones)": ["Comm. Drivers", ["META", "GOOGL", "NFLX", "DIS", "TMUS", "VZ", "T", "CHTR", "SNAP", "PINS", "TTWO", "EA", "SPOT"]],
    "XLRE (Inmuebles)": ["REITs Drivers", ["PLD", "AMT", "EQIX", "CCI", "WY", "PSA", "VNQ", "IYR", "ICF", "OPEN"]],
    "ARGT (Argentina Focus)": ["ARG ADRs", ["GGAL", "YPF", "BMA", "PAM", "TGS", "CEPU", "EDN", "MELI", "GLOB", "VIST", "LOMA", "CRESY", "BBAR", "IRS", "SUPV"]],
    "IBIT / BITO (Crypto Proxy)": ["Crypto Equities", ["BTC-USD", "MSTR", "COIN", "MARA", "RIOT", "IREN", "CLSK", "BITX", "HUT", "IBIT"]]
}

st.markdown("""
<style>
    .stApp { background-color: #0B0E11; color: #EAECEF; }
    .report-card { background-color: #1E2329; padding: 20px; border-radius: 12px; border-left: 6px solid #F0B90B; margin-bottom: 15px; }
    .verdict-title { color: #F0B90B; font-weight: bold; font-size: 1.3em; margin-bottom: 8px; }
    .highlight-green { color: #00FFAA; font-weight: bold; }
    .highlight-red { color: #FF3B30; font-weight: bold; }
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
    row = {"Cat": category, "Activo": symbol}
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
st.title("🦅 SLY MASTER FLOW & ETF AUDITOR")
MACRO_CONFIG = {"1D": {"int": "1d", "per": "2y"}, "1S": {"int": "1wk", "per": "5y"}, "1M": {"int": "1mo", "per": "max"}}

with st.sidebar:
    lookback = st.selectbox("Ventana Flujo:", ["1 Mes", "3 Meses", "YTD"], index=0)
    markets_sel = st.multiselect("Flow Matrix:", ["SPY", "QQQ", "IWM", "EEM", "XLK", "XLE", "XLF", "XLV", "XLP", "XLB", "XLU", "XLY", "XLC", "XLRE", "BTC-USD", "GLD"], default=["SPY", "QQQ", "XLK", "XLE"])

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
        with v1:
            top_a = stats_df.index[0]
            st.markdown(f"<div class='report-card'><div class='verdict-title'>🚀 LÍDER DE FLUJO</div>{top_a} presenta inyección institucional.</div>", unsafe_allow_html=True)
        with v2:
            worst_a = stats_df.index[-1]
            st.markdown(f"<div class='report-card'><div class='verdict-title'>⚠️ FUGA DE CAPITAL</div>{worst_a} bajo presión de distribución.</div>", unsafe_allow_html=True)

        c1, c2 = st.columns([2, 1])
        with c1:
            fig = px.scatter(stats_df, x="Ret %", y="RVOL", size=stats_df["Score"].abs().clip(lower=5), color="Score", text=stats_df.index, template="plotly_dark")
            fig.add_hline(y=1.0, line_dash="dash", line_color="#888")
            fig.add_vline(x=0, line_dash="dash", line_color="#888")
            st.plotly_chart(fig, use_container_width=True)
        with c2: st.dataframe(stats_df.style.background_gradient(cmap='RdYlGn', subset=['Score']), use_container_width=True)
        
        st.subheader("📈 Trayectoria Acumulada")
        st.line_chart((c / c.iloc[0] - 1) * 100)

# ─────────────────────────────────────────────
# UI - AUDITORÍA POR ETF DE SECTOR
# ─────────────────────────────────────────────
st.divider()
st.header("🔍 Auditoría por Sector ETF")
sector_sel = st.selectbox("Seleccione Sector ETF para auditar:", list(ASSET_DATABASE.keys()))

if st.button(f"🔎 ESCANEAR COMPONENTES DE {sector_sel}"):
    tickers = ASSET_DATABASE[sector_sel][1]
    res = []
    prog = st.progress(0)
    for i, t in enumerate(tickers):
        prog.progress((i+1)/len(tickers), text=f"Procesando: {t}")
        res.append(analyze_asset(t, sector_sel))
    
    df_res = pd.DataFrame(res)
    def style_sig(v):
        if "LONG" in str(v): return 'background-color: #1B5E20; color: white;'
        if "SHORT" in str(v): return 'background-color: #B71C1C; color: white;'
        return ''
    st.dataframe(df_res[["ByMA", "Activo", "Precio", "1D Signal", "1D PnL", "1S Signal", "1S PnL", "1M Signal", "1M PnL"]].style.applymap(style_sig), use_container_width=True)
