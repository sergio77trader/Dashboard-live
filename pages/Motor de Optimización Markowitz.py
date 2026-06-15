import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from scipy.optimize import minimize
import plotly.graph_objects as go
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE PÁGINA Y ESTILOS
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | MARKOWITZ OPTIMIZER")

st.markdown("""
<style>
    .reportview-container { background: #0e1117; }
    .main { background: #0e1117; }
    stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #00897B; }
    .stDataFrame { font-family: 'Roboto Mono', monospace; }
    h1 { color: #00897B; border-bottom: 2px solid #00897B; padding-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# BÓVEDA DE ACTIVOS (Tu lista original)
# ─────────────────────────────────────────────
RAW_TICKERS = "BIL, SPY, QQQ, ARKK, BOTZ, DBC, GLD, BND, VWO, VNQ, HYG, VEA, EMB, AAPL, AMZN, TSLA, MSFT, META, NVDA, GOOGL, ARGT, MELI, GLOB, TTWO, RKLB, HOOD, HOG, MSTR, COIN, SWK, INTC, AMD, DIS, GME, ABNB, AMC, KO, DIA, F, ADBE, MO, C, COST, DE, DOCU, GE, ETSY, HAL, CRM, HSBC, IBM, JD, JNJ, LMT, MA, MCD, NFLX, NKE, PYPL, PEP, PBR, SHOP, SNAP, SONY, SPOT, SBUX, TGT, UL, WMT, SMCI, JPM, WFC, AVGO, MU, LLY, UNH, V, QCOM, HD, BAC, GGAL, BABA, YPF, PAM, XOM, AMAT, GS, ACN, MARA, SNOW, ORCL, UBER, DELL, LRCX, CVX, CSCO, CRWD, CVNA, BA, VRT, HUBS, MRK, PLTR, NEE, CAT, PFE, LIN, CMG, GM, BKNG, PG, MRVL, LOW, TXN, ADI, MS, DAL, AMGN, T, LCID, ABBV, NOW, UPS, LEN, BMY, ENPH, SOUN, INTU, SPGI, CMCSA, DHR, AXP, DHI, RTX, BK, CME, PANW, KLAC, BLK, ICE, MDLZ, MRNA, VOO, VTI, VUG, VTV, IWF, IJH, IJR, VIG, VGT, XLK, VO, IWM, TLT, VB, SCHX, XLF, XLV, SCHF, MUB, XLE, XLI, XLY, VHT, SOXX, PHO, XLRE, SCHH, IYR, ICF, DUOL, LUV, AFRM, ITA, SH, IEF, VGIT, GOVT, SGOV, IBIT, EETH, SATL, RMAX, COMP, AGNT, OPAD, OPEN, SSO, SCHD, EWJ, EWZ, EWW, ECH, INDA, EWT, EWS, ENZL, EWA, DGRO, PINS, ZM, ULTA, PM, SCHW, MMM, FDX, CVS, PSX, DASH, KMB, MSI, MNST, TMO, EA, TMUS, ABT, BX, VZ, ISRG, DDOG, MCHI, BSV, IFS, BAP, BVN, TQQQ, SOXL, TMF, SPXL, UPRO, TECL, YINN, SQQQ, FAS, TNA, LABU, SPXS, SOXS, MCO, CL, MAR, KDP, UNP, TEAM, GEHC, SOFI, CCL, NET, WST, MKC, GDDY, HPE, MDB, WBD, KHC, EBAY, HLT, FISV, EEM, AAL, JMIA, BP, BB, BBD, SVXY, REK, VIST, ADM, TSM, RIOT, TLRY, NOC, CGC, GD, IIPR, SYM, NU, ANET, OXY, O, ASML, VEGI, OKLO, PFF, RDDT, SPYD, HSY, PTON, DJT, BITX, KODK, VIXY, RACE, LULU, HMC, FWONK, TS, TX, HIMS, ITUB, ABEV, BIDU, GRWG, HYFM, MANU, FAZ, FNGU, MSFU, AAPU, FBL, LOMA, DLTR, DUK, GPRK, NEM, SO, QBTS, RGTI, BITI, PCAR, NVO, UMAC, AXON, XYZ, PDD, NTES, SOS, RCAT, BN, VALE, ARM, QSI, TM, WM, URTH, BBAR, IRS, BIOX, EDN, SUPV, XP, BBAI, DAPP, TEM, KULR, INBS, TBX, EAT, LMND, UUUU, GDX, ASTS, RCL, APP, PAGS, TTT, UNCY, PL, NIO, CONY, CLOV, JOBY, UGL, TBF, BYND, TWLO, MMSI, LODE, TBT, CEG, UUP, OTLY, SHY, IEI, TLH, IREN, NWTG, FLIN, OSCR, ALAB, AMZY, APLY, AVY, BG, BIIB, BMA, CELH, CEPU, CRESY, DOW, DPZ, EWY, FXI, FXY, HON, HUT, IGPT, LAES, ONON, PYPY, SEDG, SLB, SNA, STLA, STZ, TTEK, URBN, VSCO, AAP, YBIT, ADP, HERO, ABSI, PDBA, MAGS, B, SMMT, SETH, SLV, PATH, AIQ, SHEL, TGS, PSQ, MKL, XLP, XPEV, DXYZ, MSTY, CRCL, PLBY, FIG, AOM, OWNB, BKR, SPYG, USO, APLD, ASPN, AUR, BITO, BKCH, BLDR, BLOK, CDNS, COO, DAVA, EIX, EL, ELF, EVTL, FEZ, FSLR, GAUZ, GPN, HDV, HELO, BMRN, VXUS, URA, ACWI, NVDL, GRAB, GTLB, VT, SPMO, QQQM, IONQ, TSLL, AMZU, SBET, JEPQ, JEPI, QYLD, TXRH, ABCL, AOK, VBR, IAU, IEO, ZETA, KBH, OMC, RYDE, SVCO, POOL, VYM, ANF, TMDX, MTUM, BMNR, TMQ, BNKK, VEEE, QNRX, HRZN"
MASTER_TICKERS = sorted(list(set([t.strip() for t in RAW_TICKERS.split(",") if t.strip()])))

# ─────────────────────────────────────────────
# FUNCIONES MATEMÁTICAS (Mundo Markowitz)
# ─────────────────────────────────────────────

def get_portfolio_perf(weights, mean_returns, cov_matrix):
    """Calcula Retorno y Volatilidad Anualizada."""
    port_return = np.sum(mean_returns * weights)
    port_std = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
    return port_return, port_std

def neg_sharpe_ratio(weights, mean_returns, cov_matrix, risk_free_rate):
    """Función a minimizar para encontrar el máximo Sharpe."""
    p_ret, p_std = get_portfolio_perf(weights, mean_returns, cov_matrix)
    return -(p_ret - risk_free_rate) / p_std

# ─────────────────────────────────────────────
# INTERFAZ DE USUARIO
# ─────────────────────────────────────────────
st.title("🏛️ SLY | MARKOWITZ QUANT LAB")
st.subheader("Optimización Científica de Carteras")

with st.sidebar:
    st.header("⚙️ Parámetros")
    selected_assets = st.multiselect(
        "Selecciona activos de tu bóveda:", 
        MASTER_TICKERS, 
        default=["SPY", "QQQ", "BTC-USD", "GLD", "YPF"]
    )
    
    lookback = st.slider("Años de datos históricos:", 1, 10, 5)
    rf_rate = st.number_input("Tasa Libre de Riesgo (Treasury %):", value=4.5) / 100
    
    st.divider()
    run_button = st.button("🚀 CALCULAR FRONTERA EFICIENTE", type="primary", use_container_width=True)

if run_button:
    if len(selected_assets) < 2:
        st.error("❌ Selecciona al menos 2 activos para calcular la covarianza.")
    else:
        with st.spinner("Descargando datos y resolviendo matriz..."):
            # 1. Descarga de datos
            df = yf.download(selected_assets, period=f"{lookback}y", interval="1d")['Close']
            
            # Limpieza básica
            df = df.dropna()
            returns = df.pct_change().dropna()
            
            # Estadísticas anualizadas (252 días hábiles)
            mean_returns = returns.mean() * 252
            cov_matrix = returns.cov() * 252
            
            # 2. OPTIMIZACIÓN (SciPy)
            num_assets = len(selected_assets)
            args = (mean_returns, cov_matrix, rf_rate)
            constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1}) # Pesos sumen 1
            bounds = tuple((0, 1) for asset in range(num_assets))         # No short selling
            
            # Resolución
            result = minimize(neg_sharpe_ratio, num_assets*[1./num_assets], 
                              args=args, method='SLSQP', bounds=bounds, constraints=constraints)
            
            opt_weights = result.x
            opt_ret, opt_std = get_portfolio_perf(opt_weights, mean_returns, cov_matrix)
            opt_sharpe = (opt_ret - rf_rate) / opt_std

            # 3. SIMULACIÓN DE MONTE CARLO (Nube de carteras)
            num_portfolios = 1500
            p_ret = []
            p_vol = []
            p_shp = []
            
            for _ in range(num_portfolios):
                w = np.random.random(num_assets)
                w /= np.sum(w)
                r, v = get_portfolio_perf(w, mean_returns, cov_matrix)
                p_ret.append(r)
                p_vol.append(v)
                p_shp.append((r - rf_rate) / v)

            # 4. RENDERIZADO DE RESULTADOS
            col1, col2, col3 = st.columns(3)
            col1.metric("Retorno Esperado (Anual)", f"{opt_ret*100:.2f}%")
            col2.metric("Volatilidad (Riesgo)", f"{opt_std*100:.2f}%")
            col3.metric("Max Sharpe Ratio", f"{opt_sharpe:.2f}")

            # Gráfico de Frontera Eficiente
            fig = go.Figure()
            # Nube de puntos
            fig.add_trace(go.Scatter(
                x=p_vol, y=p_ret, mode='markers',
                marker=dict(color=p_shp, colorscale='Viridis', size=5, showscale=True, title="Sharpe"),
                name="Carteras Posibles"
            ))
            # Punto Óptimo
            fig.add_trace(go.Scatter(
                x=[opt_std], y=[opt_ret], mode='markers',
                marker=dict(color='red', size=15, symbol='star', line=dict(width=2, color='white')),
                name="PORTAFOLIO ÓPTIMO"
            ))
            
            fig.update_layout(
                title="Frontera Eficiente de Markowitz",
                xaxis_title="Volatilidad Anualizada (Riesgo)",
                yaxis_title="Retorno Anualizado",
                template="plotly_dark",
                height=600
            )
            st.plotly_chart(fig, use_container_width=True)

            # Tabla de Pesos
            st.subheader("🎯 Composición de la Cartera Óptima")
            weights_df = pd.DataFrame({
                'Ticker': selected_assets,
                'Peso Recomendado': [f"{w*100:.2f}%" for w in opt_weights]
            }).sort_values(by='Peso Recomendado', ascending=False)
            
            st.table(weights_df)

            # Matriz de Correlación
            st.subheader("🔗 Matriz de Correlación (Crucial para Diversificar)")
            corr_matrix = returns.corr()
            st.dataframe(corr_matrix.style.background_gradient(cmap='RdYlGn'))

else:
    st.info("👈 Selecciona los activos de tu bóveda y dale a 'Calcular' para ver la magia de Markowitz.")
