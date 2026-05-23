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
st.set_page_config(layout="wide", page_title="SLY | MEGA MATRIX V48")

st.markdown("""
<style>
    .stDataFrame { font-size: 10px; font-family: 'Roboto Mono', monospace; }
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

RAW_TICKERS = "BIL, SPY, QQQ, ARKK, BOTZ, DBC, GLD, BND, VWO, VNQ, HYG, VEA, EMB, AAPL, AMZN, TSLA, MSFT, META, NVDA, GOOGL, ARGT, MELI, GLOB, TTWO, RKLB, HOOD, HOG, MSTR, COIN, SWK, INTC, AMD, DIS, GME, ABNB, AMC, KO, DIA, F, ADBE, MO, C, COST, DE, DOCU, GE, ETSY, HAL, CRM, HSBC, IBM, JD, JNJ, LMT, MA, MCD, NFLX, NKE, PYPL, PEP, PBR, SHOP, SNAP, SONY, SPOT, SBUX, TGT, UL, WMT, SMCI, JPM, WFC, AVGO, MU, LLY, UNH, V, QCOM, HD, BAC, GGAL, BABA, YPF, PAM, XOM, AMAT, GS, ACN, MARA, SNOW, ORCL, UBER, DELL, LRCX, CVX, CSCO, CRWD, CVNA, BA, VRT, HUBS, MRK, PLTR, NEE, CAT, PFE, LIN, CMG, GM, BKNG, PG, MRVL, LOW, TXN, ADI, MS, DAL, AMGN, T, LCID, ABBV, NOW, UPS, LEN, BMY, ENPH, SOUN, INTU, SPGI, CMCSA, DHR, AXP, DHI, RTX, BK, CME, PANW, KLAC, BLK, ICE, MDLZ, MRNA, VOO, VTI, VUG, VTV, IWF, IJH, IJR, VIG, VGT, XLK, VO, IWM, TLT, VB, SCHX, XLF, XLV, SCHF, MUB, XLE, XLI, XLY, VHT, SOXX, PHO, XLRE, SCHH, IYR, ICF, DUOL, LUV, AFRM, ITA, SH, IEF, VGIT, GOVT, SGOV, IBIT, EETH, SATL, RMAX, COMP, AGNT, OPAD, OPEN, SSO, SCHD, EWJ, EWZ, EWW, ECH, INDA, EWT, EWS, ENZL, EWA, DGRO, PINS, ZM, ULTA, PM, SCHW, MMM, FDX, CVS, PSX, DASH, KMB, MSI, MNST, TMO, EA, TMUS, ABT, BX, VZ, ISRG, DDOG, MCHI, BSV, IFS, BAP, BVN, TQQQ, SOXL, TMF, SPXL, UPRO, TECL, YINN, SQQQ, FAS, TNA, LABU, SPXS, SOXS, MCO, CL, MAR, KDP, UNP, TEAM, GEHC, SOFI, CCL, NET, WST, MKC, GDDY, HPE, MDB, WBD, KHC, EBAY, HLT, FISV, EEM, AAL, JMIA, BP, BB, BBD, SVXY, REK, VIST, ADM, TSM, RIOT, TLRY, NOC, CGC, GD, IIPR, SYM, NU, ANET, OXY, O, ASML, VEGI, OKLO, PFF, RDDT, SPYD, HSY, PTON, DJT, BITX, KODK, VIXY, RACE, LULU, HMC, FWONK, TS, TX, HIMS, ITUB, ABEV, BIDU, GRWG, HYFM, MANU, FAZ, FNGU, MSFU, AAPU, FBL, LOMA, DLTR, DUK, GPRK, NEM, SO, QBTS, RGTI, BITI, PCAR, NVO, UMAC, AXON, XYZ, PDD, NTES, SOS, RCAT, BN, VALE, ARM, QSI, TM, WM, URTH, BBAR, IRS, BIOX, EDN, SUPV, XP, BBAI, DAPP, TEM, KULR, INBS, TBX, EAT, LMND, UUUU, GDX, ASTS, RCL, APP, PAGS, TTT, UNCY, PL, NIO, CONY, CLOV, JOBY, UGL, TBF, BYND, TWLO, MMSI, LODE, TBT, CEG, UUP, OTLY, SHY, IEI, TLH, IREN, NWTG, FLIN, OSCR, ALAB, AMZY, APLY, AVY, BG, BIIB, BMA, CELH, CEPU, CRESY, DOW, DPZ, EWY, FXI, FXY, HON, HUT, IGPT, LAES, ONON, PYPY, SEDG, SLB, SNA, STLA, STZ, TTEK, URBN, VSCO, AAP, YBIT, ADP, HERO, ABSI, PDBA, MAGS, B, SMMT, SETH, SLV, PATH, AIQ, SHEL, TGS, PSQ, MKL, XLP, XPEV, DXYZ, MSTY, CRCL, PLBY, FIG, AOM, OWNB, BKR, SPYG, USO, APLD, ASPN, AUR, BITO, BKCH, BLDR, BLOK, CDNS, COO, DAVA, EIX, EL, ELF, EVTL, FEZ, FSLR, GAUZ, GPN, HDV, HELO, BMRN, VXUS, URA, ACWI, NVDL, GRAB, GTLB, VT, SPMO, QQQM, IONQ, TSLL, AMZU, SBET, JEPQ, JEPI, QYLD, TXRH, ABCL, AOK, VBR, IAU, IEO, ZETA, KBH, OMC, RYDE, SVCO, POOL, VYM, ANF, TMDX, MTUM, BMNR, TMQ, BNKK, VEEE, QNRX, HRZN"
MASTER_TICKERS = sorted(list(set([t.strip() for t in RAW_TICKERS.split(",") if t.strip()])))

# ─────────────────────────────────────────────
# MOTOR DE DINÁMICA DE HISTOGRAMA
# ─────────────────────────────────────────────
def get_hist_dynamics(current, previous):
    if current > previous:
        return "↗️ Acelerando" if current > 0 else "↗️ Recuperando (A 0)"
    else:
        return "↘️ Cayendo (A 0)" if current > 0 else "↘️ Acelerando"

# ─────────────────────────────────────────────
# MOTOR TÉCNICO
# ─────────────────────────────────────────────
def run_sly_engine_detailed(df, offset_current=False):
    if df.empty or len(df) < 35: return 0, 0, None, "S/D"
    macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
    if macd is None or macd.empty: return 0, 0, None, "S/D"
    hist = macd['MACDh_12_26_9']
    
    # Lógica de Offset para Semanal
    idx = -2 if offset_current else -1
    prev_idx = idx - 1
    
    dynamic = get_hist_dynamics(hist.iloc[idx], hist.iloc[prev_idx])
    
    ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    ha_open = np.zeros(len(df)); ha_open[0] = (df['Open'].iloc[0] + df['Close'].iloc[0]) / 2
    for i in range(1, len(df)): ha_open[i] = (ha_open[i-1] + ha_close.iloc[i-1]) / 2
    ha_dir = np.where(ha_close > ha_open, 1, -1)
    
    state, entry_px, entry_tm = 0, 0.0, None
    for i in range(1, len(df) + (idx + 1)):
        h, h_prev, hd, hd_prev = hist.iloc[i], hist.iloc[i-1], ha_dir[i], ha_dir[i-1]
        if hd == 1 and hd_prev == -1 and h < 0 and h > h_prev: state, entry_px, entry_tm = 1, df['Close'].iloc[i], df.index[i]
        elif hd == -1 and hd_prev == 1 and h > 0 and h < h_prev: state, entry_px, entry_tm = -1, df['Close'].iloc[i], df.index[i]
        elif state != 0:
            if (state == 1 and h < h_prev) or (state == -1 and h > h_prev): state = 0
            
    return state, entry_px, entry_tm, dynamic

def analyze_asset_v48(symbol):
    row = {"Activo": symbol, "Precio": 0.0, "Sector": "S/D", "País": "S/D"}
    # Obtener Sector y País (Caché implícito por símbolo)
    try:
        info = yf.Ticker(symbol).info
        row["Sector"] = info.get('sector', 'ETF/Indice')
        row["País"] = info.get('country', 'Global')
    except: pass

    for tf, config in MACRO_CONFIG.items():
        try:
            df = yf.download(symbol, interval=config['int'], period=config['per'], progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if df.empty or len(df) < 35: continue
            
            if tf == "1D": row["Precio"] = float(df['Close'].iloc[-1])
            if tf == "1S":
                for l in [2, 4, 21, 42]:
                    curr, prev = df['Volume'].tail(l).sum(), df['Volume'].iloc[-(l*2):-l].sum()
                    row[f"Vol {l}v(S)%"] = round(((curr-prev)/prev*100), 2) if prev > 0 else 0.0
            
            # Aplicar offset en Semanal
            st_val, px_in, tm_in, dynamic = run_sly_engine_detailed(df, offset_current=(tf == "1S"))
            
            pnl = ((df['Close'].iloc[-1]-px_in)/px_in*100) if st_val == 1 else ((px_in-df['Close'].iloc[-1])/px_in*100) if st_val == -1 else 0.0
            row[f"{tf} Signal"] = "LONG 🟢" if st_val == 1 else "SHORT 🔴" if st_val == -1 else "FUERA ⚪"
            row[f"{tf} Hist."] = dynamic
            row[f"{tf} PnL%"] = round(pnl, 2)
        except: pass
    return row

# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────
st.title("🛡️ SLY OMNI-FILTER V48.0")
st.markdown('<div class="vol-info">🔍 SECTOR & PAÍS | MACD DINÁMICO (Semanal offset t-1)</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Configuración")
    b_size = st.selectbox("Lote:", [10, 25, 50, 100], index=1)
    batches = [MASTER_TICKERS[i:i+b_size] for i in range(0, len(MASTER_TICKERS), b_size)]
    sel_batch = st.selectbox("Lote Actual:", range(len(batches)), format_func=lambda x: f"Lote {x+1}")
    
    if st.button("🚀 ESCANEAR", type="primary", use_container_width=True):
        results = []
        prog = st.progress(0)
        targets = batches[sel_batch]
        for idx, sym in enumerate(targets):
            prog.progress((idx+1)/len(targets), text=f"Analizando: {sym}")
            results.append(analyze_asset_v48(sym))
        
        current = {x["Activo"]: x for x in st.session_state["sniper_results"]}
        for r in results: current[r["Activo"]] = r
        st.session_state["sniper_results"] = list(current.values())
        st.rerun()

    if st.session_state["sniper_results"]:
        st.divider()
        f_sig = st.multiselect("Filtro Señal 1D:", ["LONG 🟢", "SHORT 🔴", "FUERA ⚪"], default=["LONG 🟢", "SHORT 🔴", "FUERA ⚪"])
        
    if st.button("Limpiar Memoria"):
        st.session_state["sniper_results"] = []; st.rerun()

# ─────────────────────────────────────────────
# RENDERIZADO
# ─────────────────────────────────────────────
if st.session_state["sniper_results"]:
    df = pd.DataFrame(st.session_state["sniper_results"])
    df = df[df["1D Signal"].isin(f_sig)]

    def style_matrix(v):
        v_str = str(v)
        if "LONG" in v_str or "Acelerando" in v_str or "Recuperando" in v_str: return 'color: #2E7D32; font-weight: bold;'
        if "SHORT" in v_str or "Cayendo" in v_str: return 'color: #C62828; font-weight: bold;'
        return ''

    st.dataframe(
        df.style.map(style_matrix),
        use_container_width=True,
        height=800,
        column_config={
            "Precio": st.column_config.NumberColumn(format="$%.2f"),
            "1D PnL%": st.column_config.NumberColumn(format="%.2f%%"),
            "1S PnL%": st.column_config.NumberColumn(format="%.2f%%"),
            "1M PnL%": st.column_config.NumberColumn(format="%.2f%%")
        }
    )
else:
    st.info("👈 Inicie el escaneo.")
