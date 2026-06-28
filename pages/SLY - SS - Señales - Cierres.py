import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# CONFIGURACIÓN INSTITUCIONAL
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | SIGNAL TRACKER")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #EAECEF; }
    .stDataFrame { font-size: 11px; font-family: 'Roboto Mono', monospace; }
    h1 { color: #2962FF; font-weight: 800; border-bottom: 2px solid #2962FF; }
    .status-active { background-color: #1B5E20; color: white; padding: 2px 5px; border-radius: 4px; font-weight: bold; }
    .status-closed { background-color: #B71C1C; color: white; padding: 2px 5px; border-radius: 4px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# MOTOR DE CÁLCULO ZERO-LAG (DEMA)
# ─────────────────────────────────────────────
def get_sly_indicators(df):
    # DEMA Function
    def dema(s, length):
        ema1 = s.ewm(span=length, adjust=False).mean()
        ema2 = ema1.ewm(span=length, adjust=False).mean()
        return 2 * ema1 - ema2

    # Zero-Lag MACD
    fast_ma = dema(df['Close'], 12)
    slow_ma = dema(df['Close'], 26)
    df['macd_line'] = fast_ma - slow_ma
    df['signal_line'] = df['macd_line'].ewm(span=9, adjust=False).mean()
    df['hist'] = df['macd_line'] - df['signal_line']

    # RSI PRO (DEMA Smoothed)
    df['rsi_raw'] = ta.rsi(df['Close'], length=14)
    df['rsi_smooth'] = dema(df['rsi_raw'].fillna(50), 5)

    # Heikin Ashi Recursivo Manual
    ha_close = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    ha_open = np.zeros(len(df))
    ha_open[0] = (df['Open'].iloc[0] + df['Close'].iloc[0]) / 2
    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i-1] + ha_close.iloc[i-1]) / 2
    df['ha_c'] = ha_close
    df['ha_o'] = ha_open
    df['ha_color'] = np.where(df['ha_c'] > df['ha_o'], "Verde", "Rojo")
    
    # EMAs de Régimen
    df['ema52'] = ta.ema(df['Close'], 52)
    df['ema260'] = ta.ema(df['Close'], 260)
    
    return df

# ─────────────────────────────────────────────
# MÁQUINA DE ESTADOS (Búsqueda de Señales)
# ─────────────────────────────────────────────
def find_last_signal(df, enable_bearish_longs=True):
    """
    Escanea el historial para encontrar la última señal LONG
    y determinar si sigue vigente o se cerró.
    """
    last_entry_date = None
    last_entry_px = 0
    is_active = False
    verdict = "-"
    
    # Recorremos desde el inicio para mantener la persistencia de la señal
    for i in range(1, len(df)):
        # Condiciones de Entrada (LONG)
        trend_bull = df['ema52'].iloc[i] > df['ema260'].iloc[i]
        # Si no es tendencia alcista, solo entra si enable_bearish_longs es True (Rebote)
        authorized = trend_bull or enable_bearish_longs
        
        ha_flip = df['ha_color'].iloc[i] == "Verde" and df['ha_color'].iloc[i-1] == "Rojo"
        macd_accel = df['hist'].iloc[i] > df['hist'].iloc[i-1]
        rsi_rising = df['rsi_smooth'].iloc[i] > df['rsi_smooth'].iloc[i-1]
        rsi_discount = df['rsi_smooth'].iloc[i] < 50
        
        entry_trigger = authorized and ha_flip and macd_accel and rsi_rising and rsi_discount
        
        # Condiciones de Salida
        exit_trigger = (df['ha_color'].iloc[i] == "Rojo" and 
                        df['hist'].iloc[i] < df['hist'].iloc[i-1] and 
                        df['rsi_smooth'].iloc[i] < df['rsi_smooth'].iloc[i-1])

        if not is_active and entry_trigger:
            is_active = True
            last_entry_date = df.index[i]
            last_entry_px = df['Close'].iloc[i]
        
        elif is_active and exit_trigger:
            is_active = False
            # No reseteamos la fecha para que GitHub muestre cuándo fue la última vez que operó

    # Veredicto de la vela actual (Solo si está activo)
    if is_active:
        curr_h = df['hist'].iloc[-1]
        prev_h = df['hist'].iloc[-2]
        if prev_h > 0 and curr_h <= 0: verdict = "CERRAR OPERACIÓN 🔴"
        elif curr_h > prev_h: verdict = "MANTENER 🟢"
        else: verdict = "PIERDE FUERZA 🟡"

    return last_entry_date, is_active, verdict

# ─────────────────────────────────────────────
# PROCESAMIENTO STREAMLIT
# ─────────────────────────────────────────────
RAW_TICKERS = "BIL, SPY, QQQ, ARKK, BOTZ, DBC, GLD, BND, VWO, VNQ, HYG, VEA, EMB, AAPL, AMZN, TSLA, MSFT, META, NVDA, GOOGL, ARGT, MELI, GLOB, TTWO, RKLB, HOOD, HOG, MSTR, COIN, SWK, INTC, AMD, DIS, GME, ABNB, AMC, KO, DIA, F, ADBE, MO, C, COST, DE, DOCU, GE, ETSY, HAL, CRM, HSBC, IBM, JD, JNJ, LMT, MA, MCD, NFLX, NKE, PYPL, PEP, PBR, SHOP, SNAP, SONY, SPOT, SBUX, TGT, UL, WMT, SMCI, JPM, WFC, AVGO, MU, LLY, UNH, V, QCOM, HD, BAC, GGAL, BABA, YPF, PAM, XOM, AMAT, GS, ACN, MARA, SNOW, ORCL, UBER, DELL, LRCX, CVX, CSCO, CRWD, CVNA, BA, VRT, HUBS, MRK, PLTR, NEE, CAT, PFE, LIN, CMG, GM, BKNG, PG, MRVL, LOW, TXN, ADI, MS, DAL, AMGN, T, LCID, ABBV, NOW, UPS, LEN, BMY, ENPH, SOUN, INTU, SPGI, CMCSA, DHR, AXP, DHI, RTX, BK, CME, PANW, KLAC, BLK, ICE, MDLZ, MRNA, VOO, VTI, VUG, VTV, IWF, IJH, IJR, VIG, VGT, XLK, VO, IWM, TLT, VB, SCHX, XLF, XLV, SCHF, MUB, XLE, XLI, XLY, VHT, SOXX, PHO, XLRE, SCHH, IYR, ICF, DUOL, LUV, AFRM, ITA, SH, IEF, VGIT, GOVT, SGOV, IBIT, EETH, SATL, RMAX, COMP, AGNT, OPAD, OPEN, SSO, SCHD, EWJ, EWZ, EWW, ECH, INDA, EWT, EWS, ENZL, EWA, DGRO, PINS, ZM, ULTA, PM, SCHW, MMM, FDX, CVS, PSX, DASH, KMB, MSI, MNST, TMO, EA, TMUS, ABT, BX, VZ, ISRG, DDOG, MCHI, BSV, IFS, BAP, BVN, TQQQ, SOXL, TMF, SPXL, UPRO, TECL, YINN, SQQQ, FAS, TNA, LABU, SPXS, SOXS, MCO, CL, MAR, KDP, UNP, TEAM, GEHC, SOFI, CCL, NET, WST, MKC, GDDY, HPE, MDB, WBD, KHC, EBAY, HLT, FISV, EEM, AAL, JMIA, BP, BB, BBD, SVXY, REK, VIST, ADM, TSM, RIOT, TLRY, NOC, CGC, GD, IIPR, SYM, NU, ANET, OXY, O, ASML, VEGI, OKLO, PFF, RDDT, SPYD, HSY, PTON, DJT, BITX, KODK, VIXY, RACE, LULU, HMC, FWONK, TS, TX, HIMS, ITUB, ABEV, BIDU, GRWG, HYFM, MANU, FAZ, FNGU, MSFU, AAPU, FBL, LOMA, DLTR, DUK, GPRK, NEM, SO, QBTS, RGTI, BITI, PCAR, NVO, UMAC, AXON, XYZ, PDD, NTES, SOS, RCAT, BN, VALE, ARM, QSI, TM, WM, URTH, BBAR, IRS, BIOX, EDN, SUPV, XP, BBAI, DAPP, TEM, KULR, INBS, TBX, EAT, LMND, UUUU, GDX, ASTS, RCL, APP, PAGS, TTT, UNCY, PL, NIO, CONY, CLOV, JOBY, UGL, TBF, BYND, TWLO, MMSI, LODE, TBT, CEG, UUP, OTLY, SHY, IEI, TLH, IREN, NWTG, FLIN, OSCR, ALAB, AMZY, APLY, AVY, BG, BIIB, BMA, CELH, CEPU, CRESY, DOW, DPZ, EWY, FXI, FXY, HON, HUT, IGPT, LAES, ONON, PYPY, SEDG, SLB, SNA, STLA, STZ, TTEK, URBN, VSCO, AAP, YBIT, ADP, HERO, ABSI, PDBA, MAGS, B, SMMT, SETH, SLV, PATH, AIQ, SHEL, TGS, PSQ, MKL, XLP, XPEV, DXYZ, MSTY, CRCL, PLBY, FIG, AOM, OWNB, BKR, SPYG, USO, APLD, ASPN, AUR, BITO, BKCH, BLDR, BLOK, CDNS, COO, DAVA, EIX, EL, ELF, EVTL, FEZ, FSLR, GAUZ, GPN, HDV, HELO, BMRN, VXUS, URA, ACWI, NVDL, GRAB, GTLB, VT, SPMO, QQQM, IONQ, TSLL, AMZU, SBET, JEPQ, JEPI, QYLD, TXRH, ABCL, AOK, VBR, IAU, IEO, ZETA, KBH, OMC, RYDE, SVCO, POOL, VYM, ANF, TMDX, MTUM, BMNR, TMQ, BNKK, VEEE, QNRX, HRZN"
TICKERS = sorted([t.strip() for t in RAW_TICKERS.split(",")])

st.title("🛡️ SLY | SIGNAL STATE TRACKER")

with st.sidebar:
    st.header("⚙️ Radar Ops")
    batch_idx = st.number_input("Lote de 50 activos:", 0, len(TICKERS)//50, 0)
    bear_longs = st.checkbox("Habilitar Rebotistas (EMA 52 < 260)", value=True)
    
    if st.button("🚀 ACTUALIZAR SEÑALES", type="primary"):
        results = []
        subset = TICKERS[batch_idx*50 : (batch_idx+1)*50]
        prog = st.progress(0)
        
        for i, sym in enumerate(subset):
            try:
                prog.progress((i+1)/len(subset), text=f"Auditando: {sym}")
                data = yf.download(sym, interval="1wk", period="5y", progress=False)
                if data.empty: continue
                
                data = get_sly_indicators(data)
                sig_date, vigente, verd = find_last_signal(data, bear_longs)
                
                results.append({
                    "Activo": sym,
                    "Última Señal": sig_date.strftime('%Y-%m-%d') if sig_date else "-",
                    "Estado": "VIGENTE 🟢" if vigente else "CERRADA 🔴",
                    "Veredicto": verd,
                    "Precio": round(data['Close'].iloc[-1], 2),
                    "RSI": round(data['rsi_smooth'].iloc[-1], 1),
                    "Régimen": "ALCISTA" if data['ema52'].iloc[-1] > data['ema260'].iloc[-1] else "BAJISTA"
                })
            except: continue
        
        st.session_state["matrix"] = results

if "matrix" in st.session_state:
    df_res = pd.DataFrame(st.session_state["matrix"])
    
    def color_cells(val):
        if "VIGENTE" in str(val) or "MANTENER" in str(val) or "ALCISTA" in str(val): return 'background-color: #1B5E20; color: white;'
        if "CERRADA" in str(val) or "CERRAR" in str(val) or "BAJISTA" in str(val): return 'background-color: #B71C1C; color: white;'
        if "PIERDE" in str(val): return 'background-color: #FFCC00; color: black;'
        return ''

    st.dataframe(df_res.style.map(color_cells), use_container_width=True, height=800)
else:
    st.info("👈 Seleccione un lote y presione ACTUALIZAR para auditar las señales.")
