import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# CONFIGURACIÓN INSTITUCIONAL - LIGHT THEME
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | SIGNAL MONITOR V55")

st.markdown("""
<style>
    .stApp { background-color: #FFFFFF; color: #1C1E21; }
    .stDataFrame { font-size: 11px; font-family: 'Roboto Mono', monospace; }
    h1 { color: #004D40; font-weight: 800; border-bottom: 3px solid #004D40; }
    .stProgress > div > div > div > div { background-color: #004D40; }
    .sector-box { background-color: #F1F8E9; padding: 15px; border-radius: 8px; border-left: 5px solid #2E7D32; margin-bottom: 10px; }
    .sector-title { font-weight: bold; color: #1B5E20; font-size: 1.1em; }
</style>
""", unsafe_allow_html=True)

if "master_results" not in st.session_state:
    st.session_state["master_results"] = {}

# ─────────────────────────────────────────────
# MAPEO SECTORIAL (BÓVEDA DE CLASIFICACIÓN)
# ─────────────────────────────────────────────
SECTOR_MAP = {
    "ÍNDICES/ETFs": ["SPY", "QQQ", "DIA", "IWM", "VTI", "VOO", "VEA", "VWO", "EEM", "EEM", "XLK", "XLF", "XLE", "XLV", "XLI", "XLP", "XLB", "XLU", "XLY", "XLC", "XLRE", "ARKK", "BITO", "IBIT"],
    "TECNOLOGÍA": ["AAPL", "MSFT", "NVDA", "GOOGL", "META", "AVGO", "AMD", "INTC", "QCOM", "TXN", "MU", "ADI", "AMAT", "LRCX", "KLAC", "ASML", "SNOW", "PLTR", "NOW", "CRM", "ADBE", "ORCL", "DELL", "SMCI"],
    "FINANCIERO": ["JPM", "BAC", "WFC", "GS", "MS", "C", "V", "MA", "AXP", "BLK", "SPGI", "CME", "ICE", "PYPL", "SQ", "HOOD"],
    "ENERGÍA/OIL": ["XOM", "CVX", "PBR", "SLB", "COP", "OXY", "HAL", "BKR", "VIST", "YPF", "TGS", "PAM", "TGS"],
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
# MOTOR DE CÁLCULO ZERO-LAG DEMA
# ─────────────────────────────────────────────
def get_sly_indicators(df):
    try:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.dropna(subset=['Close'])

        def dema(s, length):
            ema1 = s.ewm(span=length, adjust=False).mean()
            ema2 = ema1.ewm(span=length, adjust=False).mean()
            return 2 * ema1 - ema2

        df['macd_line'] = dema(df['Close'], 12) - dema(df['Close'], 26)
        df['signal_line'] = df['macd_line'].ewm(span=9, adjust=False).mean()
        df['hist'] = df['macd_line'] - df['signal_line']
        df['rsi_smooth'] = dema(ta.rsi(df['Close'], length=14).fillna(50), 5)

        ha_c = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
        ha_o = np.zeros(len(df))
        ha_o[0] = (df['Open'].iloc[0] + df['Close'].iloc[0]) / 2
        for i in range(1, len(df)): ha_o[i] = (ha_o[i-1] + ha_c.iloc[i-1]) / 2
        df['ha_color'] = np.where(ha_c > ha_o, "Verde", "Rojo")
        
        df['ema52'] = ta.ema(df['Close'], length=52)
        df['ema260'] = ta.ema(df['Close'], length=260)
        return df.dropna(subset=['ema260'])
    except: return pd.DataFrame()

# ─────────────────────────────────────────────
# MÁQUINA DE ESTADOS
# ─────────────────────────────────────────────
def find_last_signal(df, bear_longs):
    if df.empty or len(df) < 2: return None, None, False, "-"
    last_entry_date, last_entry_px, is_active, verdict = None, None, False, "-"
    for i in range(1, len(df)):
        authorized = (df['ema52'].iloc[i] > df['ema260'].iloc[i]) or bear_longs
        ha_flip = df['ha_color'].iloc[i] == "Verde" and df['ha_color'].iloc[i-1] == "Rojo"
        macd_accel = df['hist'].iloc[i] > df['hist'].iloc[i-1]
        rsi_ok = df['rsi_smooth'].iloc[i] > df['rsi_smooth'].iloc[i-1] and df['rsi_smooth'].iloc[i] < 50
        
        if not is_active and (authorized and ha_flip and macd_accel and rsi_ok):
            is_active, last_entry_date, last_entry_px = True, df.index[i], df['Close'].iloc[i]
        elif is_active and (df['ha_color'].iloc[i] == "Rojo" and df['hist'].iloc[i] < df['hist'].iloc[i-1] and df['rsi_smooth'].iloc[i] < df['rsi_smooth'].iloc[i-1]):
            is_active = False

    if is_active:
        c_h, p_h = df['hist'].iloc[-1], df['hist'].iloc[-2]
        if p_h > 0 and c_h <= 0: verdict = "CERRAR OPERACIÓN 🔴"
        elif c_h > p_h: verdict = "MANTENER 🟢"
        else: verdict = "PIERDE FUERZA 🟡"
    return last_entry_date, last_entry_px, is_active, verdict

# ─────────────────────────────────────────────
# INTERFAZ Y BÓVEDA
# ─────────────────────────────────────────────
RAW_TICKERS = "BIL, SPY, QQQ, ARKK, BOTZ, DBC, GLD, BND, VWO, VNQ, HYG, VEA, EMB, AAPL, AMZN, TSLA, MSFT, META, NVDA, GOOGL, ARGT, MELI, GLOB, TTWO, RKLB, HOOD, HOG, MSTR, COIN, SWK, INTC, AMD, DIS, GME, ABNB, AMC, KO, DIA, F, ADBE, MO, C, COST, DE, DOCU, GE, ETSY, HAL, CRM, HSBC, IBM, JD, JNJ, LMT, MA, MCD, NFLX, NKE, PYPL, PEP, PBR, SHOP, SNAP, SONY, SPOT, SBUX, TGT, UL, WMT, SMCI, JPM, WFC, AVGO, MU, LLY, UNH, V, QCOM, HD, BAC, GGAL, BABA, YPF, PAM, XOM, AMAT, GS, ACN, MARA, SNOW, ORCL, UBER, DELL, LRCX, CVX, CSCO, CRWD, CVNA, BA, VRT, HUBS, MRK, PLTR, NEE, CAT, PFE, LIN, CMG, GM, BKNG, PG, MRVL, LOW, TXN, ADI, MS, DAL, AMGN, T, LCID, ABBV, NOW, UPS, LEN, BMY, ENPH, SOUN, INTU, SPGI, CMCSA, DHR, AXP, DHI, RTX, BK, CME, PANW, KLAC, BLK, ICE, MDLZ, MRNA, VOO, VTI, VUG, VTV, IWF, IJH, IJR, VIG, VGT, XLK, VO, IWM, TLT, VB, SCHX, XLF, XLV, SCHF, MUB, XLE, XLI, XLY, VHT, SOXX, PHO, XLRE, SCHH, IYR, ICF, DUOL, LUV, AFRM, ITA, SH, IEF, VGIT, GOVT, SGOV, IBIT, EETH, SATL, RMAX, COMP, AGNT, OPAD, OPEN, SSO, SCHD, EWJ, EWZ, EWW, ECH, INDA, EWT, EWS, ENZL, EWA, DGRO, PINS, ZM, ULTA, PM, SCHW, MMM, FDX, CVS, PSX, DASH, KMB, MSI, MNST, TMO, EA, TMUS, ABT, BX, VZ, ISRG, DDOG, MCHI, BSV, IFS, BAP, BVN, TQQQ, SOXL, TMF, SPXL, UPRO, TECL, YINN, SQQQ, FAS, TNA, LABU, SPXS, SOXS, MCO, CL, MAR, KDP, UNP, TEAM, GEHC, SOFI, CCL, NET, WST, MKC, GDDY, HPE, MDB, WBD, KHC, EBAY, HLT, FISV, EEM, AAL, JMIA, BP, BB, BBD, SVXY, REK, VIST, ADM, TSM, RIOT, TLRY, NOC, CGC, GD, IIPR, SYM, NU, ANET, OXY, O, ASML, VEGI, OKLO, PFF, RDDT, SPYD, HSY, PTON, DJT, BITX, KODK, VIXY, RACE, LULU, HMC, FWONK, TS, TX, HIMS, ITUB, ABEV, BIDU, GRWG, HYFM, MANU, FAZ, FNGU, MSFU, AAPU, FBL, LOMA, DLTR, DUK, GPRK, NEM, SO, QBTS, RGTI, BITI, PCAR, NVO, UMAC, AXON, XYZ, PDD, NTES, SOS, RCAT, BN, VALE, ARM, QSI, TM, WM, URTH, BBAR, IRS, BIOX, EDN, SUPV, XP, BBAI, DAPP, TEM, KULR, INBS, TBX, EAT, LMND, UUUU, GDX, ASTS, RCL, APP, PAGS, TTT, UNCY, PL, NIO, CONY, CLOV, JOBY, UGL, TBF, BYND, TWLO, MMSI, LODE, TBT, CEG, UUP, OTLY, SHY, IEI, TLH, IREN, NWTG, FLIN, OSCR, ALAB, AMZY, APLY, AVY, BG, BIIB, BMA, CELH, CEPU, CRESY, DOW, DPZ, EWY, FXI, FXY, HON, HUT, IGPT, LAES, ONON, PYPY, SEDG, SLB, SNA, STLA, STZ, TTEK, URBN, VSCO, AAP, YBIT, ADP, HERO, ABSI, PDBA, MAGS, B, SMMT, SETH, SLV, PATH, AIQ, SHEL, TGS, PSQ, MKL, XLP, XPEV, DXYZ, MSTY, CRCL, PLBY, FIG, AOM, OWNB, BKR, SPYG, USO, APLD, ASPN, AUR, BITO, BKCH, BLDR, BLOK, CDNS, COO, DAVA, EIX, EL, ELF, EVTL, FEZ, FSLR, GAUZ, GPN, HDV, HELO, BMRN, VXUS, URA, ACWI, NVDL, GRAB, GTLB, VT, SPMO, QQQM, IONQ, TSLL, AMZU, SBET, JEPQ, JEPI, QYLD, TXRH, ABCL, AOK, VBR, IAU, IEO, ZETA, KBH, OMC, RYDE, SVCO, POOL, VYM, ANF, TMDX, MTUM, BMNR, TMQ, BNKK, VEEE, QNRX, HRZN"
TICKERS = sorted(list(set([t.strip() for t in RAW_TICKERS.split(",") if t.strip()])))

st.title("🛡️ SLY | SIGNAL MONITOR V55")

with st.sidebar:
    st.header("⚙️ Radar Ops")
    batch_size = st.number_input("Acciones por Lote:", 10, 200, 100)
    total_lotes = (len(TICKERS) // batch_size) + (1 if len(TICKERS) % batch_size > 0 else 0)
    batch_idx = st.selectbox(f"Lote:", range(total_lotes), format_func=lambda x: f"Lote {x+1}")
    bear_longs = st.checkbox("Bear-Longs", value=True)
    
    if st.button("🚀 ACTUALIZAR Y ACUMULAR", type="primary", use_container_width=True):
        subset = TICKERS[batch_idx*batch_size : (batch_idx+1)*batch_size]
        prog = st.progress(0)
        for i, sym in enumerate(subset):
            try:
                prog.progress((i+1)/len(subset), text=f"Auditando: {sym}")
                data = yf.download(sym, interval="1wk", period="max", progress=False)
                if data.empty: continue
                data = get_sly_indicators(data)
                if data.empty: continue
                
                sig_date, sig_px, vigente, verd = find_last_signal(data, bear_longs)
                
                # Cálculo PnL solo si vigente
                pnl_display = round(((data['Close'].iloc[-1] - sig_px) / sig_px * 100), 2) if (vigente and sig_px) else None
                
                st.session_state["master_results"][sym] = {
                    "Activo": sym, "Sector": get_sector(sym),
                    "Última Señal": sig_date.strftime('%Y-%m-%d') if sig_date else "-",
                    "Estado": "VIGENTE 🟢" if vigente else "CERRADA 🔴",
                    "PnL %": pnl_display, "Veredicto": verd, "Precio": round(data['Close'].iloc[-1], 2),
                    "RSI": round(data['rsi_smooth'].iloc[-1], 1),
                    "Régimen": "ALCISTA" if data['ema52'].iloc[-1] > data['ema260'].iloc[-1] else "BAJISTA"
                }
            except: continue
        st.rerun()

    if st.button("🗑️ Limpiar Memoria"):
        st.session_state["master_results"] = {}; st.rerun()

# ─────────────────────────────────────────────
# MÓDULO DE RESUMEN SECTORIAL
# ─────────────────────────────────────────────
if st.session_state["master_results"]:
    df_full = pd.DataFrame(st.session_state["master_results"].values())
    df_vigentes = df_full[df_full["Estado"] == "VIGENTE 🟢"]

    st.subheader("📊 RESUMEN DE EXPOSICIÓN (POSICIONES VIGENTES)")
    if not df_vigentes.empty:
        # Agrupar por sector
        summary = df_vigentes.groupby("Sector")["Activo"].apply(list).reset_index()
        cols = st.columns(3)
        for idx, row in summary.iterrows():
            with cols[idx % 3]:
                st.markdown(f"""
                <div class="sector-box">
                    <div class="sector-title">{row['Sector']}: {len(row['Activo'])} Activos</div>
                    <div style="font-size: 0.85em;">{", ".join(row['Activo'])}</div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.warning("No hay posiciones VIGENTES en los activos analizados.")

    # ─────────────────────────────────────────────
    # TABLA MAESTRA
    # ─────────────────────────────────────────────
    st.subheader("📋 Matriz Detallada")
    df_res = df_full.sort_values(by=["Estado", "Activo"], ascending=[False, True])
    
    def color_cells(val):
        str_v = str(val)
        if "VIGENTE" in str_v or "MANTENER" in str_v or "ALCISTA" in str_v: return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
        if "CERRADA" in str_v or "CERRAR" in str_v or "BAJISTA" in str_v: return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
        if "PIERDE" in str_v: return 'background-color: #FFF9C4; color: #827717; font-weight: bold;'
        return ''

    st.dataframe(df_res.style.map(color_cells), use_container_width=True, height=600)
else:
    st.info("👈 Cargue lotes para ver el resumen sectorial y la matriz.")
