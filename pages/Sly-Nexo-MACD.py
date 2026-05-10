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
st.set_page_config(layout="wide", page_title="SYSTEMATRADER | MEGA MATRIX V47.2")

st.markdown("""
<style>
    .stDataFrame { font-size: 11px; font-family: 'Roboto Mono', monospace; }
    h1 { color: #00897B; font-weight: 800; border-bottom: 2px solid #00897B; }
    [data-testid="stMetricValue"] { font-size: 14px; }
    .stProgress > div > div > div > div { background-color: #00897B; }
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
# BÓVEDA DE ACTIVOS COMPLETA (~430 TICKERS)
# ─────────────────────────────────────────────
RAW_TICKERS = """
BIL, SPY, QQQ, ARKK, BOTZ, DBC, GLD, BND, VWO, VNQ, HYG, VEA, EMB, AAPL, AMZN, TSLA, MSFT, META, NVDA, GOOGL, ARGT, MELI, GLOB, TTWO, RKLB, HOOD, HOG, MSTR, COIN, SWK, INTC, AMD, DIS, GME, ABNB, AMC, KO, DIA, F, ADBE, MO, C, COST, DE, DOCU, GE, ETSY, HAL, CRM, HSBC, IBM, JD, JNJ, LMT, MA, MCD, NFLX, NKE, PYPL, PEP, PBR, SHOP, SNAP, SONY, SPOT, SBUX, TGT, UL, WMT, SMCI, JPM, WFC, AVGO, MU, LLY, UNH, V, QCOM, HD, BAC, GGAL, BABA, YPF, PAM, XOM, AMAT, GS, ACN, MARA, SNOW, ORCL, UBER, DELL, LRCX, CVX, CSCO, CRWD, CVNA, BA, VRT, HUBS, MRK, PLTR, NEE, CAT, PFE, LIN, CMG, GM, BKNG, PG, MRVL, LOW, TXN, ADI, MS, DAL, AMGN, T, LCID, ABBV, NOW, UPS, LEN, BMY, ENPH, SOUN, INTU, SPGI, CMCSA, DHR, AXP, DHI, RTX, BK, CME, PANW, KLAC, BLK, ICE, MDLZ, MRNA, VOO, VTI, VUG, VTV, IWF, IJH, IJR, VIG, VGT, XLK, VO, IWM, TLT, VB, SCHX, XLF, XLV, SCHF, MUB, XLE, XLI, XLY, VHT, SOXX, PHO, XLRE, SCHH, IYR, ICF, DUOL, LUV, AFRM, ITA, SH, IEF, VGIT, GOVT, SGOV, IBIT, EETH, SATL, RMAX, COMP, AGNT, OPAD, OPEN, SSO, SCHD, EWJ, EWZ, EWW, ECH, INDA, EWT, EWS, ENZL, EWA, DGRO, PINS, ZM, ULTA, PM, SCHW, MMM, FDX, CVS, PSX, DASH, KMB, MSI, MNST, TMO, EA, TMUS, ABT, BX, VZ, ISRG, DDOG, MCHI, BSV, IFS, BAP, BVN, TQQQ, SOXL, TMF, SPXL, UPRO, TECL, YINN, SQQQ, FAS, TNA, LABU, SPXS, SOXS, MCO, CL, MAR, KDP, UNP, TEAM, GEHC, SOFI, CCL, NET, WST, MKC, GDDY, HPE, MDB, WBD, KHC, EBAY, HLT, FISV, EEM, AAL, JMIA, BP, BB, BBD, SVXY, REK, VIST, ADM, TSM, RIOT, TLRY, NOC, CGC, GD, IIPR, SYM, NU, ANET, OXY, O, ASML, VEGI, OKLO, PFF, RDDT, SPYD, HSY, PTON, DJT, BITX, KODK, VIXY, RACE, LULU, HMC, FWONK, TS, TX, HIMS, ITUB, ABEV, BIDU, GRWG, HYFM, MANU, FAZ, FNGU, MSFU, AAPU, FBL, LOMA, DLTR, DUK, GPRK, NEM, SO, QBTS, RGTI, BITI, PCAR, NVO, UMAC, AXON, XYZ, PDD, NTES, SOS, RCAT, BN, VALE, ARM, QSI, TM, WM, URTH, BBAR, IRS, BIOX, EDN, SUPV, XP, BBAI, DAPP, TEM, KULR, INBS, TBX, EAT, LMND, UUUU, GDX, ASTS, RCL, APP, PAGS, TTT, UNCY, PL, NIO, CONY, CLOV, JOBY, UGL, TBF, BYND, TWLO, MMSI, LODE, TBT, CEG, UUP, OTLY, SHY, IEI, TLH, IREN, NWTG, FLIN, OSCR, ALAB, AMZY, APLY, AVY, BG, BIIB, BMA, CELH, CEPU, CRESY, DOW, DPZ, EWY, FXI, FXY, HON, HUT, IGPT, LAES, ONON, PYPY, SEDG, SLB, SNA, STLA, STZ, TTEK, URBN, VSCO, AAP, YBIT, ADP, HERO, ABSI, PDBA, MAGS, B, SMMT, SETH, SLV, PATH, AIQ, SHEL, TGS, PSQ, MKL, XLP, XPEV, DXYZ, MSTY, CRCL, PLBY, FIG, AOM, OWNB, BKR, SPYG, USO, APLD, ASPN, AUR, BITO, BKCH, BLDR, BLOK, CDNS, COO, DAVA, EIX, EL, ELF, EVTL, FEZ, FSLR, GAUZ, GPN, HDV, HELO, BMRN, VXUS, URA, ACWI, NVDL, GRAB, GTLB, VT, SPMO, QQQM, IONQ, TSLL, AMZU, SBET, JEPQ, JEPI, QYLD, TXRH, ABCL, AOK, VBR, IAU, IEO, ZETA, KBH, OMC, RYDE, SVCO, POOL, VYM, ANF, TMDX, MTUM, BMNR, TMQ, BNKK, VEEE, QNRX, HRZN
"""
MASTER_TICKERS = sorted(list(set([t.strip() for t in RAW_TICKERS.split(",") if t.strip()])))

# ─────────────────────────────────────────────
# MOTOR TÉCNICO SLY RECURSIVO
# ─────────────────────────────────────────────
def run_sly_engine(df):
    if df.empty or len(df) < 35: return 0, 0, None
    df = df.copy()
    macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
    if macd is None or macd.empty: return 0, 0, None
    hist = macd['MACDh_12_26_9']
    
    ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    ha_open = np.zeros(len(df))
    ha_open[0] = (df['Open'].iloc[0] + df['Close'].iloc[0]) / 2
    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i-1] + ha_close.iloc[i-1]) / 2
    ha_dir = np.where(ha_close > ha_open, 1, -1)
    
    state, entry_px, entry_tm = 0, 0.0, None
    for i in range(1, len(df)):
        h, h_prev = hist.iloc[i], hist.iloc[i-1]
        hd, hd_prev = ha_dir[i], ha_dir[i-1]
        longC = (hd == 1 and hd_prev == -1 and h < 0 and h > h_prev)
        shrtC = (hd == -1 and hd_prev == 1 and h > 0 and h < h_prev)
        if longC: state, entry_px, entry_tm = 1, df['Close'].iloc[i], df.index[i]
        elif shrtC: state, entry_px, entry_tm = -1, df['Close'].iloc[i], df.index[i]
        elif state != 0:
            if (state == 1 and h < h_prev) or (state == -1 and h > h_prev): state = 0
    return state, entry_px, entry_tm

# ─────────────────────────────────────────────
# ANALIZADOR TRIPLE CICLO
# ─────────────────────────────────────────────
def analyze_triple_cycle(symbol):
    row = {"Activo": symbol}
    current_price = None
    for tf_key, config in MACRO_CONFIG.items():
        try:
            df = yf.download(symbol, interval=config['int'], period=config['per'], progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if df.empty or len(df) < 35:
                row[f"{tf_key} Signal"] = "S/D"
                continue
            if tf_key == "1D": current_price = df['Close'].iloc[-1]
            st_val, px_in, tm_in = run_sly_engine(df)
            if st_val != 0:
                pnl = (df['Close'].iloc[-1] - px_in) / px_in * 100 if st_val == 1 else (px_in - df['Close'].iloc[-1]) / px_in * 100
                row[f"{tf_key} Signal"] = "LONG 🟢" if st_val == 1 else "SHORT 🔴"
                row[f"{tf_key} Fecha"] = tm_in.strftime("%d/%m/%y")
                row[f"{tf_key} PnL"] = f"{pnl:.2f}%"
            else:
                row[f"{tf_key} Signal"] = "FUERA ⚪"
                row[f"{tf_key} Fecha"] = "-"
                row[f"{tf_key} PnL"] = "-"
        except: row[f"{tf_key} Signal"] = "ERR"
    row["Precio"] = f"{current_price:,.2f}" if current_price else "-"
    return row

# ─────────────────────────────────────────────
# INTERFAZ Streamlit
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("🦅 Control Mega Matrix")
    st.info(f"Total Activos en Bóveda: {len(MASTER_TICKERS)}")
    
    b_size = st.selectbox("Tamaño Lote:", [10, 25, 50, 100], index=1)
    batches = [MASTER_TICKERS[i:i+b_size] for i in range(0, len(MASTER_TICKERS), b_size)]
    sel_batch = st.selectbox("Seleccionar Lote:", range(len(batches)), format_func=lambda x: f"Lote {x+1} ({len(batches[x])} activos)")
    
    acc = st.checkbox("Acumular Resultados", value=True)
    
    if st.button("🚀 INICIAR ESCANEO MEGA", type="primary", use_container_width=True):
        results = []
        prog = st.progress(0)
        targets = batches[sel_batch]
        
        for idx, sym in enumerate(targets):
            prog.progress((idx+1)/len(targets), text=f"Analizando {sym}...")
            res = analyze_triple_cycle(sym)
            results.append(res)
            time.sleep(0.01) # Reducción de latencia institucional
            
        if acc:
            current = {x["Activo"]: x for x in st.session_state["sniper_results"]}
            for r in results: current[r["Activo"]] = r
            st.session_state["sniper_results"] = list(current.values())
        else:
            st.session_state["sniper_results"] = results
        st.rerun()

    if st.button("Limpiar Memoria"):
        st.session_state["sniper_results"] = []
        st.rerun()

# ─────────────────────────────────────────────
# TABLA FINAL (ESTILO INSTITUCIONAL)
# ─────────────────────────────────────────────
st.title("🦅 SLY TRIPLE MACRO MATRIX")

if st.session_state["sniper_results"]:
    df_final = pd.DataFrame(st.session_state["sniper_results"])
    cols_order = ["Activo", "Precio", 
                  "1D Signal", "1D Fecha", "1D PnL",
                  "1S Signal", "1S Fecha", "1S PnL",
                  "1M Signal", "1M Fecha", "1M PnL"]
    df_final = df_final[[c for c in cols_order if c in df_final.columns]]

    def style_table(val):
        str_val = str(val)
        if "LONG" in str_val: return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
        if "SHORT" in str_val: return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
        if "%" in str_val:
            try:
                v = float(str_val.replace("%",""))
                return f'color: {"#2E7D32" if v >= 0 else "#C62828"}; font-weight: bold;'
            except: return ''
        return ''

    try:
        st.dataframe(df_final.style.map(style_table), use_container_width=True, height=800)
    except AttributeError:
        st.dataframe(df_final.style.applymap(style_table), use_container_width=True, height=800)
else:
    st.info("👈 Seleccione un lote y presione el botón para iniciar.")
