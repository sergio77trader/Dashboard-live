import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURACIÓN DEL SISTEMA
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | OMNI-FILTER MATRIX")

st.markdown("""
<style>
    .stDataFrame { font-size: 11px; font-family: 'Roboto Mono', monospace; }
    h1 { color: #00897B; font-weight: 800; border-bottom: 2px solid #00897B; }
    .vol-info { background-color: #E1F5FE; padding: 10px; border-left: 5px solid #0288D1; border-radius: 5px; margin-bottom: 20px; color: #01579B; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

if "sniper_results" not in st.session_state:
    st.session_state["sniper_results"] = []

MACRO_CONFIG = {
    "1D": {"int": "1d", "per": "2y"},
    "1S": {"int": "1wk", "per": "5y"},
    "1M": {"int": "1mo", "per": "max"}
}

# ─────────────────────────────────────────────
# BÓVEDA DE ACTIVOS COMPLETA
# ─────────────────────────────────────────────
RAW_TICKERS = "BIL, SPY, QQQ, ARKK, BOTZ, DBC, GLD, BND, VWO, VNQ, HYG, VEA, EMB, AAPL, AMZN, TSLA, MSFT, META, NVDA, GOOGL, ARGT, MELI, GLOB, TTWO, RKLB, HOOD, HOG, MSTR, COIN, SWK, INTC, AMD, DIS, GME, ABNB, AMC, KO, DIA, F, ADBE, MO, C, COST, DE, DOCU, GE, ETSY, HAL, CRM, HSBC, IBM, JD, JNJ, LMT, MA, MCD, NFLX, NKE, PYPL, PEP, PBR, SHOP, SNAP, SONY, SPOT, SBUX, TGT, UL, WMT, SMCI, JPM, WFC, AVGO, MU, LLY, UNH, V, QCOM, HD, BAC, GGAL, BABA, YPF, PAM, XOM, AMAT, GS, ACN, MARA, SNOW, ORCL, UBER, DELL, LRCX, CVX, CSCO, CRWD, CVNA, BA, VRT, HUBS, MRK, PLTR, NEE, CAT, PFE, LIN, CMG, GM, BKNG, PG, MRVL, LOW, TXN, ADI, MS, DAL, AMGN, T, LCID, ABBV, NOW, UPS, LEN, BMY, ENPH, SOUN, INTU, SPGI, CMCSA, DHR, AXP, DHI, RTX, BK, CME, PANW, KLAC, BLK, ICE, MDLZ, MRNA, VOO, VTI, VUG, VTV, IWF, IJH, IJR, VIG, VGT, XLK, VO, IWM, TLT, VB, SCHX, XLF, XLV, SCHF, MUB, XLE, XLI, XLY, VHT, SOXX, PHO, XLRE, SCHH, IYR, ICF, DUOL, LUV, AFRM, ITA, SH, IEF, VGIT, GOVT, SGOV, IBIT, EETH, SATL, RMAX, COMP, AGNT, OPAD, OPEN, SSO, SCHD, EWJ, EWZ, EWW, ECH, INDA, EWT, EWS, ENZL, EWA, DGRO, PINS, ZM, ULTA, PM, SCHW, MMM, FDX, CVS, PSX, DASH, KMB, MSI, MNST, TMO, EA, TMUS, ABT, BX, VZ, ISRG, DDOG, MCHI, BSV, IFS, BAP, BVN, TQQQ, SOXL, TMF, SPXL, UPRO, TECL, YINN, SQQQ, FAS, TNA, LABU, SPXS, SOXS, MCO, CL, MAR, KDP, UNP, TEAM, GEHC, SOFI, CCL, NET, WST, MKC, GDDY, HPE, MDB, WBD, KHC, EBAY, HLT, FISV, EEM, AAL, JMIA, BP, BB, BBD, SVXY, REK, VIST, ADM, TSM, RIOT, TLRY, NOC, CGC, GD, IIPR, SYM, NU, ANET, OXY, O, ASML, VEGI, OKLO, PFF, RDDT, SPYD, HSY, PTON, DJT, BITX, KODK, VIXY, RACE, LULU, HMC, FWONK, TS, TX, HIMS, ITUB, ABEV, BIDU, GRWG, HYFM, MANU, FAZ, FNGU, MSFU, AAPU, FBL, LOMA, DLTR, DUK, GPRK, NEM, SO, QBTS, RGTI, BITI, PCAR, NVO, UMAC, AXON, XYZ, PDD, NTES, SOS, RCAT, BN, VALE, ARM, QSI, TM, WM, URTH, BBAR, IRS, BIOX, EDN, SUPV, XP, BBAI, DAPP, TEM, KULR, INBS, TBX, EAT, LMND, UUUU, GDX, ASTS, RCL, APP, PAGS, TTT, UNCY, PL, NIO, CONY, CLOV, JOBY, UGL, TBF, BYND, TWLO, MMSI, LODE, TBT, CEG, UUP, OTLY, SHY, IEI, TLH, IREN, NWTG, FLIN, OSCR, ALAB, AMZY, APLY, AVY, BG, BIIB, BMA, CELH, CEPU, CRESY, DOW, DPZ, EWY, FXI, FXY, HON, HUT, IGPT, LAES, ONON, PYPY, SEDG, SLB, SNA, STLA, STZ, TTEK, URBN, VSCO, AAP, YBIT, ADP, HERO, ABSI, PDBA, MAGS, B, SMMT, SETH, SLV, PATH, AIQ, SHEL, TGS, PSQ, MKL, XLP, XPEV, DXYZ, MSTY, CRCL, PLBY, FIG, AOM, OWNB, BKR, SPYG, USO, APLD, ASPN, AUR, BITO, BKCH, BLDR, BLOK, CDNS, COO, DAVA, EIX, EL, ELF, EVTL, FEZ, FSLR, GAUZ, GPN, HDV, HELO, BMRN, VXUS, URA, ACWI, NVDL, GRAB, GTLB, VT, SPMO, QQQM, IONQ, TSLL, AMZU, SBET, JEPQ, JEPI, QYLD, TXRH, ABCL, AOK, VBR, IAU, IEO, ZETA, KBH, OMC, RYDE, SVCO, POOL, VYM, ANF, TMDX, MTUM, BMNR, TMQ, BNKK, VEEE, QNRX, HRZN"
MASTER_TICKERS = sorted(list(set([t.strip() for t in RAW_TICKERS.split(",") if t.strip()])))

# ─────────────────────────────────────────────
# MOTOR TÉCNICO
# ─────────────────────────────────────────────
def run_sly_engine(df):
    if df.empty or len(df) < 35: return 0, 0, None
    macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
    if macd is None or macd.empty: return 0, 0, None
    hist = macd['MACDh_12_26_9']
    ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    ha_open = np.zeros(len(df)); ha_open[0] = (df['Open'].iloc[0] + df['Close'].iloc[0]) / 2
    for i in range(1, len(df)): ha_open[i] = (ha_open[i-1] + ha_close.iloc[i-1]) / 2
    ha_dir = np.where(ha_close > ha_open, 1, -1)
    state, entry_px, entry_tm = 0, 0.0, None
    for i in range(1, len(df)):
        h, h_prev, hd, hd_prev = hist.iloc[i], hist.iloc[i-1], ha_dir[i], ha_dir[i-1]
        if hd == 1 and hd_prev == -1 and h < 0 and h > h_prev: state, entry_px, entry_tm = 1, df['Close'].iloc[i], df.index[i]
        elif hd == -1 and hd_prev == 1 and h > 0 and h < h_prev: state, entry_px, entry_tm = -1, df['Close'].iloc[i], df.index[i]
        elif state != 0:
            if (state == 1 and h < h_prev) or (state == -1 and h > h_prev): state = 0
    return state, entry_px, entry_tm

def run_vfd_engine(df):
    if df.empty or len(df) < 21: return "Normal"
    v_avg = df['Volume'].rolling(21).mean()
    v_std = df['Volume'].rolling(21).std()
    z_score = (df['Volume'] - v_avg) / v_std
    last_z = z_score.iloc[-1]
    c, h, l = df['Close'].iloc[-1], df['High'].iloc[-1], df['Low'].iloc[-1]
    rng = h - l
    mfp = ((c - l) - (h - c)) / rng if rng != 0 else 0
    if last_z > 2.0: return "ALPHA IN 💎" if mfp > 0 else "ALPHA OUT 🔥"
    elif last_z > 1.5: return "HIGH FLOW ⚠️"
    return "Normal"

# NUEVA FUNCIÓN: INERTIA FILTER (EMAs)
def run_inertia_engine(df):
    if df.empty or len(df) < 260: return "No Data"
    ema52 = ta.ema(df['Close'], length=52)
    ema260 = ta.ema(df['Close'], length=260)
    
    last_p = df['Close'].iloc[-1]
    last_e52 = ema52.iloc[-1]
    last_e260 = ema260.iloc[-1]
    
    if last_p > last_e52 and last_e52 > last_e260:
        return "BULLISH 📈"
    elif last_p < last_e52 and last_e52 < last_e260:
        return "BEARISH 📉"
    else:
        return "NEUTRAL ↔️"

def analyze_triple_cycle(symbol):
    row = {"Activo": symbol, "Precio": 0.0}
    for tf, config in MACRO_CONFIG.items():
        try:
            df = yf.download(symbol, interval=config['int'], period=config['per'], progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if df.empty or len(df) < 35: continue
            
            if tf == "1D": row["Precio"] = float(df['Close'].iloc[-1])
            
            # --- FILTRO DE INERCIA (NUEVO) ---
            if tf in ["1S", "1M"]:
                row[f"{tf} Inercia"] = run_inertia_engine(df)
            
            if tf in ["1S", "1M"]:
                row[f"{tf} VFD"] = run_vfd_engine(df)

            if tf in ["1S", "1M"]:
                rsi = ta.rsi(df['Close'], length=14)
                if rsi is not None and len(rsi) >= 2:
                    curr_rsi = rsi.iloc[-1]
                    prev_rsi = rsi.iloc[-2]
                    trend = "Subiendo" if curr_rsi > prev_rsi else "Bajando"
                    row[f"{tf} RSI"] = f"{curr_rsi:.1f} {trend}"

            if tf == "1S":
                for l in [2, 3, 4, 6, 21, 42]:
                    if len(df) >= (l * 2):
                        curr = df['Volume'].tail(l).sum()
                        prev = df['Volume'].iloc[-(l*2):-l].sum()
                        row[f"Vol {l}v(S)%"] = round(((curr-prev)/prev*100), 2) if prev > 0 else 0.0
                    else:
                        row[f"Vol {l}v(S)%"] = 0.0
            
            st_val, px_in, tm_in = run_sly_engine(df)
            pnl = ((df['Close'].iloc[-1]-px_in)/px_in*100) if st_val == 1 else ((px_in-df['Close'].iloc[-1])/px_in*100) if st_val == -1 else 0.0
            row[f"{tf} Signal"] = "LONG 🟢" if st_val == 1 else "SHORT 🔴" if st_val == -1 else "FUERA ⚪"
            row[f"{tf} Fecha"] = tm_in.strftime("%Y-%m-%d") if tm_in else "-"
            row[f"{tf} PnL%"] = round(pnl, 2)
        except: pass
    return row

# ─────────────────────────────────────────────
# RENDERIZADO (Solo cambios en Estilo y Columnas)
# ─────────────────────────────────────────────
st.title("🛡️ SLY OMNI-FILTER MATRIX V48.3")

with st.sidebar:
    st.header("⚙️ Configuración")
    b_size = st.selectbox("Tamaño Lote:", [10, 25, 50, 100], index=1)
    batches = [MASTER_TICKERS[i:i+b_size] for i in range(0, len(MASTER_TICKERS), b_size)]
    sel_batch = st.selectbox("Seleccionar Lote:", range(len(batches)), format_func=lambda x: f"Lote {x+1}")
    if st.button("🚀 INICIAR ESCANEO", type="primary"):
        results = []
        prog = st.progress(0)
        targets = batches[sel_batch]
        for idx, sym in enumerate(targets):
            prog.progress((idx+1)/len(targets), text=f"Analizando: {sym}")
            results.append(analyze_triple_cycle(sym))
        current = {x["Activo"]: x for x in st.session_state["sniper_results"]}
        for r in results: current[r["Activo"]] = r
        st.session_state["sniper_results"] = list(current.values())
        st.rerun()
    if st.button("Limpiar Memoria"): st.session_state["sniper_results"] = []; st.rerun()

if st.session_state["sniper_results"]:
    df = pd.DataFrame(st.session_state["sniper_results"])

    def style_matrix(v):
        v_str = str(v)
        if "BULLISH" in v_str or "LONG" in v_str or "ALPHA IN" in v_str: return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
        if "BEARISH" in v_str or "SHORT" in v_str or "ALPHA OUT" in v_str: return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
        if "NEUTRAL" in v_str or "HIGH FLOW" in v_str: return 'background-color: #FFF9C4; color: #F57F17; font-weight: bold;'
        if "Subiendo" in v_str: return 'color: #2E7D32; font-weight: bold;'
        if "Bajando" in v_str: return 'color: #C62828; font-weight: bold;'
        return ''

    cols_order = [
        "Activo", "Precio", 
        "1D Signal", "1D Fecha", "1D PnL%",
        "1S Signal", "1S Inercia", "1S VFD", "1S Fecha", "1S PnL%", "1S RSI",
        "1M Signal", "1M Inercia", "1M VFD", "1M Fecha", "1M PnL%", "1M RSI",
        "Vol 2v(S)%", "Vol 21v(S)%", "Vol 42v(S)%"
    ]
    
    final_cols = [c for c in cols_order if c in df.columns]
    st.dataframe(df[final_cols].style.map(style_matrix), use_container_width=True, height=800)
else:
    st.info("👈 Inicie el escaneo.")
