"""
SLY | MAPA DE VÍNCULOS v2 — cómo se mueve una acción cuando se mueve otra.
 
Dos capas de vínculos:
  1) DATOS: correlación y beta medidas con precios reales (yfinance) para TODA tu lista del V56 (≈500 acciones/ETFs),
     más tu cartera y lo que agregues. Es lo que cubre "todas las acciones".
  2) CRITERIO: cadena de negocio armada a mano (proveedor, cliente, factores como tasas o petróleo). Es una guía
     editable, no un dato oficial.
 
Requisitos:  pip install streamlit plotly pandas numpy yfinance
Ejecutar:    streamlit run sly_mapa_vinculos_v2.py
"""
import math
 
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
 
# ─────────────────────────────────────────────
# LISTA Y SECTORES DEL V56
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
 
RAW_TICKERS = "BIL, SPY, QQQ, ARKK, BOTZ, DBC, GLD, BND, VWO, VNQ, HYG, VEA, EMB, AAPL, AMZN, TSLA, MSFT, META, NVDA, GOOGL, ARGT, MELI, GLOB, TTWO, RKLB, HOOD, HOG, MSTR, COIN, SWK, INTC, AMD, DIS, GME, ABNB, AMC, KO, DIA, F, ADBE, MO, C, COST, DE, DOCU, GE, ETSY, HAL, CRM, HSBC, IBM, JD, JNJ, LMT, MA, MCD, NFLX, NKE, PYPL, PEP, PBR, SHOP, SNAP, SONY, SPOT, SBUX, TGT, UL, WMT, SMCI, JPM, WFC, AVGO, MU, LLY, UNH, V, QCOM, HD, BAC, GGAL, BABA, YPF, PAM, XOM, AMAT, GS, ACN, MARA, SNOW, ORCL, UBER, DELL, LRCX, CVX, CSCO, CRWD, CVNA, BA, VRT, HUBS, MRK, PLTR, NEE, CAT, PFE, LIN, CMG, GM, BKNG, PG, MRVL, LOW, TXN, ADI, MS, DAL, AMGN, T, LCID, ABBV, NOW, UPS, LEN, BMY, ENPH, SOUN, INTU, SPGI, CMCSA, DHR, AXP, DHI, RTX, BK, CME, PANW, KLAC, BLK, ICE, MDLZ, MRNA, VOO, VTI, VUG, VTV, IWF, IJH, IJR, VIG, VGT, XLK, VO, IWM, TLT, VB, SCHX, XLF, XLV, SCHF, MUB, XLE, XLI, XLY, VHT, SOXX, PHO, XLRE, SCHH, IYR, ICF, DUOL, LUV, AFRM, ITA, SH, IEF, VGIT, GOVT, SGOV, IBIT, EETH, SATL, RMAX, COMP, AGNT, OPAD, OPEN, SSO, SCHD, EWJ, EWZ, EWW, ECH, INDA, EWT, EWS, ENZL, EWA, DGRO, PINS, ZM, ULTA, PM, SCHW, MMM, FDX, CVS, PSX, DASH, KMB, MSI, MNST, TMO, EA, TMUS, ABT, BX, VZ, ISRG, DDOG, MCHI, BSV, IFS, BAP, BVN, TQQQ, SOXL, TMF, SPXL, UPRO, TECL, YINN, SQQQ, FAS, TNA, LABU, SPXS, SOXS, MCO, CL, MAR, KDP, UNP, TEAM, GEHC, SOFI, CCL, NET, WST, MKC, GDDY, HPE, MDB, WBD, KHC, EBAY, HLT, FISV, EEM, AAL, JMIA, BP, BB, BBD, SVXY, REK, VIST, ADM, TSM, RIOT, TLRY, NOC, CGC, GD, IIPR, SYM, NU, ANET, OXY, O, ASML, VEGI, OKLO, PFF, RDDT, SPYD, HSY, PTON, DJT, BITX, KODK, VIXY, RACE, LULU, HMC, FWONK, TS, TX, HIMS, ITUB, ABEV, BIDU, GRWG, HYFM, MANU, FAZ, FNGU, MSFU, AAPU, FBL, LOMA, DLTR, DUK, GPRK, NEM, SO, QBTS, RGTI, BITI, PCAR, NVO, UMAC, AXON, XYZ, PDD, NTES, SOS, RCAT, BN, VALE, ARM, QSI, TM, WM, URTH, BBAR, IRS, BIOX, EDN, SUPV, XP, BBAI, DAPP, TEM, KULR, INBS, TBX, EAT, LMND, UUUU, GDX, ASTS, RCL, APP, PAGS, TTT, UNCY, PL, NIO, CONY, CLOV, JOBY, UGL, TBF, BYND, TWLO, MMSI, LODE, TBT, CEG, UUP, OTLY, SHY, IEI, TLH, IREN, NWTG, FLIN, OSCR, ALAB, AMZY, APLY, AVY, BG, BIIB, BMA, CELH, CEPU, CRESY, DOW, DPZ, EWY, FXI, FXY, HON, HUT, IGPT, LAES, ONON, PYPY, SEDG, SLB, SNA, STLA, STZ, TTEK, URBN, VSCO, AAP, YBIT, ADP, HERO, ABSI, PDBA, MAGS, B, SMMT, SETH, SLV, PATH, AIQ, SHEL, TGS, PSQ, MKL, XLP, XPEV, DXYZ, MSTY, CRCL, PLBY, FIG, AOM, OWNB, BKR, SPYG, USO, APLD, ASPN, AUR, BITO, BKCH, BLDR, BLOK, CDNS, COO, DAVA, EIX, EL, ELF, EVTL, FEZ, FSLR, GAUZ, GPN, HDV, HELO, BMRN, VXUS, URA, ACWI, NVDL, GRAB, GTLB, VT, SPMO, QQQM, IONQ, TSLL, AMZU, SBET, JEPQ, JEPI, QYLD, TXRH, ABCL, AOK, VBR, IAU, IEO, ZETA, KBH, OMC, RYDE, SVCO, POOL, VYM, ANF, TMDX, MTUM, BMNR, TMQ, BNKK, VEEE, QNRX, HRZN"
 
# ─────────────────────────────────────────────
# MAPA CAUSAL (criterio manual)
# Los nodos "driver" son factores/sectores sin cotización propia (tasas, petróleo, gasto en IA...).
# ─────────────────────────────────────────────
GRUPOS = {
    "IA y centros de datos": "#7E57C2",
    "Energía y metales": "#EF6C00",
    "Cripto": "#F9A825",
    "Consumo y medios": "#26A69A",
    "Salud": "#EC407A",
    "Defensa y aeroespacial": "#546E7A",
    "Japón y autos": "#5C6BC0",
    "Tasas y macro": "#8D6E63",
}
 
NODOS = {
    # IA y centros de datos
    "IA_GASTO": ("IA y centros de datos", "Gasto y sentimiento en IA / centros de datos"),
    "NVDA": ("IA y centros de datos", "Nvidia · chips/GPU para IA"),
    "TSM": ("IA y centros de datos", "TSMC · fabrica los chips de casi todos"),
    "AMD": ("IA y centros de datos", "AMD · chips"),
    "AVGO": ("IA y centros de datos", "Broadcom · chips a medida (TPU de Google) y redes"),
    "ASML": ("IA y centros de datos", "ASML · máquinas para fabricar chips"),
    "MSFT": ("IA y centros de datos", "Microsoft · nube Azure"),
    "AMZN": ("IA y centros de datos", "Amazon · nube AWS"),
    "GOOGL": ("IA y centros de datos", "Alphabet · nube, TPU, publicidad"),
    "META": ("IA y centros de datos", "Meta · publicidad e inversión fuerte en IA"),
    "ORCL": ("IA y centros de datos", "Oracle · nube e infraestructura para IA"),
    "OPENAI": ("IA y centros de datos", "OpenAI (privada) · gran cliente de nube y chips"),
    "QCOM": ("IA y centros de datos", "Qualcomm · chips de celulares y dispositivos"),
    "CRM": ("IA y centros de datos", "Salesforce · software"),
    "ADBE": ("IA y centros de datos", "Adobe · software"),
    "ACN": ("IA y centros de datos", "Accenture · consultoría / integrador"),
    "VST": ("IA y centros de datos", "Vistra · electricidad (demanda de centros de datos)"),
    "NEE": ("IA y centros de datos", "NextEra · energía renovable y utility"),
    # Energía y metales
    "BRENT": ("Energía y metales", "Petróleo Brent"),
    "XOM": ("Energía y metales", "Exxon Mobil"),
    "CVX": ("Energía y metales", "Chevron"),
    "YPF": ("Energía y metales", "YPF"),
    "XLE": ("Energía y metales", "ETF del sector energía de EE.UU."),
    "ORO": ("Energía y metales", "Precio del oro"),
    "PLATA": ("Energía y metales", "Precio de la plata"),
    "GDX": ("Energía y metales", "ETF de mineras de oro"),
    "SLV": ("Energía y metales", "ETF de plata"),
    # Cripto
    "BTC": ("Cripto", "Bitcoin"),
    "MSTR": ("Cripto", "MicroStrategy · empresa que acumula bitcoin (muy apalancada a BTC)"),
    # Consumo y medios
    "CONSUMO": ("Consumo y medios", "Consumo de las familias en EE.UU."),
    "PUBLI": ("Consumo y medios", "Gasto publicitario"),
    "NFLX": ("Consumo y medios", "Netflix"),
    "SPOT": ("Consumo y medios", "Spotify"),
    "UBER": ("Consumo y medios", "Uber"),
    "SBUX": ("Consumo y medios", "Starbucks"),
    "PG": ("Consumo y medios", "Procter & Gamble · consumo masivo"),
    "PEP": ("Consumo y medios", "PepsiCo"),
    "HSY": ("Consumo y medios", "Hershey"),
    "VZ": ("Consumo y medios", "Verizon · telecomunicaciones"),
    "TMUS": ("Consumo y medios", "T-Mobile · telecomunicaciones"),
    # Salud
    "SALUD": ("Salud", "Gasto en salud y cirugías/procedimientos"),
    "ABT": ("Salud", "Abbott · dispositivos y diagnóstico"),
    "MDT": ("Salud", "Medtronic · dispositivos médicos"),
    "ISRG": ("Salud", "Intuitive Surgical · cirugía robótica"),
    "AMGN": ("Salud", "Amgen · biotecnología"),
    "CVS": ("Salud", "CVS Health · farmacias y seguros"),
    # Defensa y aeroespacial
    "DEFENSA": ("Defensa y aeroespacial", "Presupuesto de defensa de EE.UU."),
    "AEROESP": ("Defensa y aeroespacial", "Aeroespacial comercial (aviones y repuestos)"),
    "AEROL": ("Defensa y aeroespacial", "Aerolíneas"),
    "LMT": ("Defensa y aeroespacial", "Lockheed Martin"),
    "RTX": ("Defensa y aeroespacial", "RTX · motores, sensores y misiles"),
    "HON": ("Defensa y aeroespacial", "Honeywell · industrial y aeroespacial"),
    # Japón y autos
    "YEN": ("Japón y autos", "Yen débil (favorece a exportadoras japonesas)"),
    "ARANCEL": ("Japón y autos", "Aranceles de EE.UU. / guerra comercial"),
    "TM": ("Japón y autos", "Toyota"),
    "SONY": ("Japón y autos", "Sony · electrónica, juegos y música"),
    # Tasas y macro
    "TASAS": ("Tasas y macro", "Tasas de interés de EE.UU. (Fed, bono a 10 años)"),
    "DXY": ("Tasas y macro", "Dólar fuerte contra el mundo (índice DXY)"),
    "INFL": ("Tasas y macro", "Inflación de EE.UU."),
    "EWZ": ("Tasas y macro", "ETF de Brasil"),
    "O": ("Tasas y macro", "Realty Income · inmobiliaria que vive de alquileres (sensible a tasas)"),
}
DRIVERS = {"IA_GASTO", "BRENT", "ORO", "PLATA", "BTC", "CONSUMO", "PUBLI", "SALUD", "DEFENSA", "AEROESP",
           "AEROL", "YEN", "ARANCEL", "TASAS", "DXY", "INFL"}
ETIQUETA = {"IA_GASTO": "IA: gasto", "BRENT": "Petróleo", "ORO": "Oro", "PLATA": "Plata", "BTC": "Bitcoin",
            "CONSUMO": "Consumo EEUU", "PUBLI": "Publicidad", "SALUD": "Gasto salud", "DEFENSA": "Defensa EEUU",
            "AEROESP": "Aeroespacial", "AEROL": "Aerolíneas", "YEN": "Yen débil", "ARANCEL": "Aranceles",
            "TASAS": "Tasas EEUU", "DXY": "Dólar fuerte", "INFL": "Inflación EEUU"}
 
# ─────────────────────────────────────────────
# VÍNCULOS  (origen, destino, signo, peso, tipo, confianza)
#   signo  +1: si el origen sube, el destino tiende a subir · -1: tiende a bajar
#   peso   sensibilidad aproximada (1.0 = se mueve igual; >1 = amplifica, p.ej. MSTR vs BTC)
#   confianza: alta (relación clara y estable) · media · baja (hipótesis / correlación)
# ─────────────────────────────────────────────
E = []
 
 
def e(o, d, s, w, tipo, conf):
    E.append((o, d, s, w, tipo, conf))
 
 
# IA
for d, w, c in [("NVDA", .9, "alta"), ("AMD", .6, "media"), ("AVGO", .7, "media"), ("TSM", .6, "alta"),
                ("ASML", .4, "media"), ("ORCL", .6, "media"), ("MSFT", .3, "media"), ("AMZN", .3, "media"),
                ("GOOGL", .3, "media"), ("META", .3, "baja"), ("VST", .6, "media"), ("NEE", .3, "media"),
                ("QCOM", .2, "baja"), ("CRM", .2, "baja"), ("ADBE", .2, "baja"), ("ACN", .2, "baja"),
                ("BTC", .2, "baja")]:
    e("IA_GASTO", d, 1, w, "demanda / sentimiento", c)
e("NVDA", "TSM", 1, .5, "cliente", "alta")
e("TSM", "NVDA", 1, .4, "proveedor", "alta")
e("TSM", "AMD", 1, .4, "proveedor", "alta")
e("TSM", "QCOM", 1, .3, "proveedor", "alta")
e("TSM", "AVGO", 1, .3, "proveedor", "alta")
e("ASML", "TSM", 1, .4, "proveedor de equipos", "alta")
e("TSM", "ASML", 1, .3, "cliente", "alta")
for o, w, c in [("MSFT", .4, "media"), ("AMZN", .4, "media"), ("GOOGL", .3, "media"), ("META", .4, "media"),
                ("ORCL", .5, "media")]:
    e(o, "NVDA", 1, w, "cliente (compra GPUs)", c)
e("GOOGL", "AVGO", 1, .5, "cliente (TPU)", "alta")
e("META", "AVGO", 1, .3, "cliente", "media")
e("OPENAI", "ORCL", 1, .7, "cliente de nube", "media")
e("OPENAI", "MSFT", 1, .4, "socio / cliente de nube", "media")
e("OPENAI", "NVDA", 1, .4, "cliente (GPUs)", "media")
e("NEE", "VST", 1, .2, "pares (utilities)", "baja")
e("CRM", "ADBE", 1, .4, "pares (software)", "media")
e("ACN", "CRM", 1, .4, "implementa sus productos", "media")
e("ACN", "ADBE", 1, .3, "implementa sus productos", "media")
e("MSFT", "CRM", -1, .2, "competidor", "baja")
e("PUBLI", "META", 1, .8, "ingresos por anuncios", "alta")
e("PUBLI", "GOOGL", 1, .8, "ingresos por anuncios", "alta")
# Energía y metales
for d, w, c in [("XOM", .7, "alta"), ("CVX", .7, "alta"), ("YPF", .8, "alta"), ("XLE", .9, "alta")]:
    e("BRENT", d, 1, w, "precio del producto", c)
e("BRENT", "AEROL", -1, .5, "costo de combustible", "alta")
e("BRENT", "INFL", 1, .4, "costos / inflación", "media")
e("BRENT", "EWZ", 1, .3, "exportador de petróleo", "baja")
e("ORO", "GDX", 1, 1.7, "precio del producto (apalancado)", "alta")
e("ORO", "PLATA", 1, .8, "metales preciosos", "media")
e("PLATA", "SLV", 1, 1.0, "precio del producto", "alta")
e("ORO", "SLV", 1, .6, "metales preciosos", "media")
e("DXY", "ORO", -1, .5, "moneda de cotización", "alta")
e("TASAS", "ORO", -1, .4, "costo de oportunidad", "media")
e("DXY", "BRENT", -1, .2, "moneda de cotización", "media")
e("INFL", "ORO", 1, .2, "cobertura", "baja")
# Cripto
e("BTC", "MSTR", 1, 1.3, "tenencia de bitcoin (apalancada)", "alta")
e("TASAS", "BTC", -1, .4, "apetito por riesgo", "media")
e("DXY", "BTC", -1, .3, "dólar / liquidez", "baja")
# Consumo y medios
for d, w, c in [("SBUX", .7, "media"), ("UBER", .6, "media"), ("NFLX", .3, "media"), ("HSY", .3, "media"),
                ("PEP", .3, "media"), ("PG", .2, "media"), ("TMUS", .2, "baja"), ("PUBLI", .6, "media")]:
    e("CONSUMO", d, 1, w, "demanda del consumidor", c)
e("PUBLI", "NFLX", 1, .2, "plan con publicidad", "baja")
e("SPOT", "SONY", 1, .3, "paga regalías (Sony Music)", "media")
e("INFL", "CONSUMO", -1, .5, "poder de compra", "media")
e("TASAS", "VZ", -1, .3, "deuda alta / acción de dividendo", "media")
e("TASAS", "TMUS", -1, .2, "deuda alta", "baja")
# Salud
for d, w, c in [("ABT", .6, "media"), ("MDT", .7, "media"), ("ISRG", .7, "media"), ("AMGN", .3, "baja"),
                ("CVS", .2, "baja")]:
    e("SALUD", d, 1, w, "demanda de procedimientos", c)
e("ISRG", "MDT", 1, .2, "pares (dispositivos)", "baja")
e("MDT", "ABT", 1, .3, "pares (dispositivos)", "media")
e("AMGN", "CVS", 1, .2, "proveedor (CVS vende y administra sus fármacos)", "baja")
# Defensa y aeroespacial
e("DEFENSA", "LMT", 1, .9, "contratos del gobierno", "alta")
e("DEFENSA", "RTX", 1, .6, "contratos del gobierno", "alta")
e("DEFENSA", "HON", 1, .2, "contratos del gobierno", "media")
e("RTX", "LMT", 1, .4, "proveedor (motor y sensores)", "alta")
e("AEROESP", "RTX", 1, .5, "motores y repuestos", "alta")
e("AEROESP", "HON", 1, .5, "aviónica y repuestos", "media")
e("AEROL", "AEROESP", 1, .6, "demanda de aviones y repuestos", "alta")
# Japón y autos
e("YEN", "TM", 1, .6, "exporta y cobra en dólares", "alta")
e("YEN", "SONY", 1, .4, "exporta y cobra en dólares", "media")
e("ARANCEL", "TM", -1, .5, "exporta a EE.UU.", "media")
e("ARANCEL", "SONY", -1, .1, "cadena de suministro", "baja")
e("ARANCEL", "CONSUMO", -1, .3, "precios más altos", "media")
e("ARANCEL", "QCOM", -1, .3, "cadena de suministro", "baja")
e("ARANCEL", "INFL", 1, .3, "precios más altos", "media")
# Tasas y macro
e("TASAS", "O", -1, .7, "valuación por tasa de descuento", "alta")
for d, w, c in [("NEE", .4, "media"), ("ADBE", .4, "media"), ("CRM", .4, "media"), ("META", .3, "baja"),
                ("ORCL", .4, "media"), ("NVDA", .3, "baja"), ("EWZ", .4, "media")]:
    e("TASAS", d, -1, w, "valuación por tasa de descuento", c)
e("DXY", "EWZ", -1, .6, "emergentes sufren con dólar fuerte", "media")
e("INFL", "TASAS", 1, .6, "inflación alta -> tasas altas", "media")
e("DXY", "YEN", 1, .5, "dólar fuerte -> yen débil", "media")
e("TASAS", "DXY", 1, .4, "tasas altas -> dólar fuerte", "media")
 
EDGE_COLS = ["origen", "destino", "signo", "peso", "tipo", "confianza"]
EDGES_DEFAULT = pd.DataFrame(E, columns=EDGE_COLS)
 
# Cartera por defecto: valores en ARS de la captura del 5/11 (editables en la app)
CARTERA_DEFAULT = {
    "ABT": 142020, "ACN": 1092425, "ADBE": 546045, "AMGN": 128800, "CRM": 409500, "CVS": 117260, "EWZ": 133400,
    "GDX": 157080, "GOOGL": 155800, "HON": 89920, "HSY": 70450, "ISRG": 268460, "LMT": 96120, "MDT": 326400,
    "META": 211900, "MSTR": 1142400, "NEE": 163590, "NFLX": 128016, "O": 127925, "ORCL": 514800, "PEP": 474840,
    "PG": 557100, "QCOM": 167930, "RTX": 127900, "SBUX": 102620, "SLV": 130300, "SONY": 194480, "SPOT": 219720,
    "TM": 170240, "TMUS": 156000, "UBER": 172500, "VST": 51100, "VZ": 131950, "XLE": 155175,
}
CARTERA_DF_DEFAULT = pd.DataFrame({"Ticker": list(CARTERA_DEFAULT), "Valor ARS": list(CARTERA_DEFAULT.values())})
 
 
 
def limpiar_edges(df):
    """Normaliza la tabla editable: descarta filas incompletas y fuerza tipos."""
    d = df.copy()
    for c in EDGE_COLS:
        if c not in d.columns:
            d[c] = np.nan
    d["origen"] = d["origen"].astype(str).str.strip().str.upper()
    d["destino"] = d["destino"].astype(str).str.strip().str.upper()
    d["signo"] = pd.to_numeric(d["signo"], errors="coerce")
    d["peso"] = pd.to_numeric(d["peso"], errors="coerce")
    vacio = ["", "NAN", "NONE"]
    d = d.dropna(subset=["origen", "destino"])
    d = d[~d["origen"].isin(vacio) & ~d["destino"].isin(vacio)]
    d = d.dropna(subset=["signo", "peso"])
    d["signo"] = np.where(d["signo"] >= 0, 1, -1)
    d["peso"] = d["peso"].abs()
    d = d[d["origen"] != d["destino"]]
    return d[EDGE_COLS].reset_index(drop=True)
 
 
def limpiar_cartera(df):
    d = df.copy()
    d["Ticker"] = d["Ticker"].astype(str).str.strip().str.upper()
    d["Valor ARS"] = pd.to_numeric(d["Valor ARS"], errors="coerce")
    d = d.dropna(subset=["Ticker", "Valor ARS"])
    d = d[~d["Ticker"].isin(["", "NAN", "NONE"])]
    return d.groupby("Ticker", as_index=False)["Valor ARS"].sum()
 
 
def propagar(edges, origen, shock, profundidad=3, decaimiento=0.7):
    """
    Contagio de un shock (en %) desde 'origen'. Primer salto: efecto = shock × signo × peso. Desde el segundo salto
    se multiplica además por 'decaimiento' en cada paso.
    Se guarda, para cada nodo, el efecto de mayor magnitud entre las rutas encontradas (no se suman rutas,
    para no inflar los números). Aproximación para ordenar ideas, no una predicción.
    """
    adj = {}
    for o, d, s, w in zip(edges["origen"], edges["destino"], edges["signo"], edges["peso"]):
        adj.setdefault(o, []).append((d, s * w))
    best = {origen: float(shock)}
    frontier = {origen: float(shock)}
    for salto in range(int(profundidad)):
        nuevo = {}
        for n, ef in frontier.items():
            for d, k in adj.get(n, []):
                if d == origen:
                    continue
                v = ef * k * (1.0 if salto == 0 else decaimiento)
                if abs(v) > abs(best.get(d, 0.0)) + 1e-9 and abs(v) > abs(nuevo.get(d, 0.0)):
                    nuevo[d] = v
        best.update(nuevo)
        frontier = nuevo
    return best
 
 
def impacto_cartera(efectos, cartera):
    """Impacto en ARS y % de la cartera dado un dict {nodo: % de variación}."""
    d = cartera.copy()
    d["Efecto %"] = d["Ticker"].map(efectos).fillna(0.0)
    d["Impacto ARS"] = d["Valor ARS"] * d["Efecto %"] / 100
    return d
 
 
 
# ─────────────────────────────────────────────
# DATOS DE MERCADO (yfinance) · VÍNCULOS ESTADÍSTICOS
# ─────────────────────────────────────────────
VENTANAS = {"6 meses": 183, "1 año": 365, "2 años": 730}
MIN_OBS = 60                      # mínimo de días en común para calcular un vínculo
CACHE_PRECIOS = "sly_precios_cache.pkl"
CACHE_SECT = "sly_sectores_cache.json"
SECT_ES = {"Technology": "Tecnología", "Healthcare": "Salud", "Financial Services": "Financiero",
           "Consumer Cyclical": "Consumo cíclico", "Consumer Defensive": "Consumo defensivo", "Energy": "Energía",
           "Industrials": "Industriales", "Utilities": "Servicios públicos", "Real Estate": "Inmobiliario",
           "Basic Materials": "Materiales", "Communication Services": "Comunicaciones"}
TICKERS_V56 = sorted(set(t.strip().upper() for t in RAW_TICKERS.split(",") if t.strip()))
PALETA = ["#7E57C2", "#EF6C00", "#26A69A", "#EC407A", "#5C6BC0", "#8D6E63", "#F9A825", "#546E7A", "#00897B",
          "#C0CA33", "#29B6F6", "#AB47BC", "#78909C"]
 
 
def universo(cartera, extra=()):
    """Tu lista del V56 + tus posiciones + los activos del mapa causal + lo que agregues a mano."""
    u = set(TICKERS_V56) | set(cartera["Ticker"]) | {t.strip().upper() for t in extra if t and t.strip()}
    u |= {n for n in NODOS if n not in DRIVERS and n != "OPENAI"}
    return sorted(u)
 
 
def extraer_cierres(raw, tickers):
    """Cierres ajustados desde lo que devuelve yf.download (cubre las distintas formas de columnas)."""
    if raw is None or len(raw) == 0:
        return pd.DataFrame()
    if isinstance(raw.columns, pd.MultiIndex):
        if "Close" in raw.columns.get_level_values(0):
            c = raw["Close"]
        elif "Close" in raw.columns.get_level_values(1):
            c = raw.xs("Close", axis=1, level=1)
        else:
            return pd.DataFrame()
    elif "Close" in raw.columns:
        c = raw[["Close"]].rename(columns={"Close": tickers[0]})
    else:
        return pd.DataFrame()
    if isinstance(c, pd.Series):
        c = c.to_frame(tickers[0])
    idx = pd.to_datetime(c.index)
    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_localize(None)
    c = c.copy()
    c.index = idx.normalize()
    return c.dropna(how="all", axis=1).astype(float)
 
 
def descargar_precios(tickers, lote=100, periodo="2y", progreso=None):
    """Descarga por lotes (como el V56). Devuelve (precios, errores)."""
    import yfinance as yf
    partes, errores = [], []
    for i in range(0, len(tickers), lote):
        sub = tickers[i:i + lote]
        try:
            raw = yf.download(sub, period=periodo, interval="1d", auto_adjust=True, progress=False, threads=True)
            c = extraer_cierres(raw, sub)
            if not c.empty:
                partes.append(c)
        except Exception as ex:
            errores.append(f"Lote que empieza en {sub[0]}: {type(ex).__name__}: {str(ex)[:80]}")
        if progreso:
            progreso(min(1.0, (i + lote) / len(tickers)))
    if not partes:
        return pd.DataFrame(), errores
    df = pd.concat(partes, axis=1)
    df = df.loc[:, ~df.columns.duplicated()].sort_index()
    return df, errores
 
 
def retornos(precios, dias):
    """Retornos diarios de la ventana elegida. Descarta activos con pocos datos y recorta extremos (splits/errores)."""
    if precios is None or precios.empty:
        return pd.DataFrame()
    P = precios.loc[precios.index >= precios.index.max() - pd.Timedelta(days=dias)]
    R = P.pct_change(fill_method=None).iloc[1:]
    R = R.loc[:, R.count() >= MIN_OBS]
    return R.clip(-0.5, 0.5)
 
 
def residualizar(R, mercado="SPY"):
    """Quita el movimiento del mercado (SPY): queda lo propio de cada activo, que es donde se ven los vínculos reales."""
    if mercado not in R.columns:
        return R
    m = R[mercado]
    beta = R.apply(lambda s: s.cov(m)) / m.var()
    ajuste = pd.DataFrame(np.outer(m.fillna(0.0).to_numpy(), beta.to_numpy()), index=R.index, columns=R.columns)
    return R.sub(ajuste).drop(columns=[mercado])
 
 
def calcular_matrices_puro(precios, dias, quitar_mercado):
    R = retornos(precios, dias)
    if R.empty:
        return R, pd.DataFrame(), pd.DataFrame()
    if quitar_mercado:
        R = residualizar(R)
    return R, R.corr(min_periods=MIN_OBS), R.cov(min_periods=MIN_OBS)
 
 
def vinculos_stat(corr, cov, A, n_pos=8, n_neg=3, min_abs=0.15):
    """Los que más se mueven con A (y al revés). Beta = cuánto se mueve B por cada 1% de A."""
    cols = ["Ticker", "Correlación", "Beta"]
    if corr.empty or A not in corr.columns:
        return pd.DataFrame(columns=cols)
    c = corr[A].drop(A).dropna()
    sel = pd.concat([c[c >= min_abs].sort_values(ascending=False).head(n_pos),
                     c[c <= -min_abs].sort_values().head(n_neg)])
    va = cov.loc[A, A]
    return pd.DataFrame({"Ticker": sel.index, "Correlación": sel.values,
                         "Beta": [cov.loc[A, t] / va if va else np.nan for t in sel.index]})
 
 
def tabla_vecinos(A, edges, corr, cov, shock, n_pos=8, n_neg=3):
    """Une vínculos causales (criterio) y estadísticos (datos) de A, con impacto esperado ante 'shock' %."""
    filas = {}
 
    def f(n):
        return filas.setdefault(n, {"Nodo": n, "Rol": [], "Dir": "", "Signo": 0, "Peso": 0.0, "Correlación": np.nan,
                                    "Beta": np.nan, "Impacto %": np.nan, "Fuente": ""})
    for o, d, s, w, t in zip(edges["origen"], edges["destino"], edges["signo"], edges["peso"], edges["tipo"]):
        if o == A:
            x = f(d)
            x["Rol"].append(f"{A} → {d}: {t}")
            x["Dir"], x["Signo"], x["Peso"] = "sale", int(s), float(w)
        elif d == A:
            x = f(o)
            x["Rol"].append(f"{o} → {A}: {t}")
            if not x["Dir"]:
                x["Dir"], x["Signo"], x["Peso"] = "entra", int(s), float(w)
    for _, r in vinculos_stat(corr, cov, A, n_pos, n_neg).iterrows():
        x = f(r["Ticker"])
        if not x["Signo"]:
            x["Signo"] = 1 if r["Correlación"] > 0 else -1
    if not corr.empty and A in corr.columns:
        va = cov.loc[A, A]
        for n, x in filas.items():
            if n in corr.columns and n != A:
                x["Correlación"] = corr.loc[A, n]
                x["Beta"] = cov.loc[A, n] / va if va else np.nan
    for n, x in filas.items():
        if pd.notna(x["Beta"]):
            x["Impacto %"], x["Fuente"] = x["Beta"] * shock, "datos"
        elif x["Dir"] == "sale":
            x["Impacto %"], x["Fuente"] = x["Signo"] * x["Peso"] * shock, "criterio"
    df = pd.DataFrame(list(filas.values()))
    if df.empty:
        return df
    df["Rol"] = df["Rol"].map(lambda r: " · ".join(r))
    df["_causal"] = df["Rol"] != ""
    df["_abs"] = df["Correlación"].abs().fillna(0)
    return df.sort_values(["_causal", "_abs"], ascending=[False, False]).drop(columns=["_abs"]).reset_index(drop=True)
 
 
def efectos_simulador(A, shock, edges, cov, prof=3, decae=0.7):
    """Efecto esperado (%) sobre cada nodo: por datos (beta) cuando hay precios; por criterio causal si no."""
    ef, fuente = {}, {}
    if not cov.empty and A in cov.columns and cov.loc[A, A] > 0:
        b = (cov[A] / cov.loc[A, A]).drop(A).dropna()
        for t, v in b.items():
            ef[t], fuente[t] = float(v) * shock, "datos"
    for n, v in propagar(edges, A, shock, prof, decae).items():
        if n != A and n not in ef:
            ef[n], fuente[n] = v, "criterio"
    return ef, fuente
 
 
def pares_cartera(corr, tickers, top=10):
    ts = [t for t in tickers if t in corr.columns]
    filas = []
    for i, a in enumerate(ts):
        for b in ts[i + 1:]:
            v = corr.loc[a, b]
            if pd.notna(v):
                filas.append((a, b, float(v)))
    return pd.DataFrame(filas, columns=["Activo A", "Activo B", "Correlación"]).sort_values(
        "Correlación", ascending=False).head(top).reset_index(drop=True)
 
 
def retorno_sectorial(R, sector_fn, min_n=3):
    """Retorno promedio de cada sector (solo sectores con al menos min_n activos)."""
    grupos = {}
    for t in R.columns:
        s = sector_fn(t)
        if s not in ("Sin clasificar", "Factor / sin cotización", "ÍNDICES/ETFs"):
            grupos.setdefault(s, []).append(t)
    return pd.DataFrame({s: R[ts].mean(axis=1) for s, ts in grupos.items() if len(ts) >= min_n})
 
 
# ---------- sectores ----------
def cargar_sectores():
    import json
    import os
    if os.path.exists(CACHE_SECT):
        try:
            with open(CACHE_SECT, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return {}
    return {}
 
 
def descargar_sectores(tickers, cache, progreso=None):
    """Sector de cada ticker según yfinance (lento: ~0,3 s por activo). Se guarda y se puede reanudar."""
    import json
    import yfinance as yf
    pend = [t for t in tickers if t not in cache]
    for i, t in enumerate(pend):
        try:
            cache[t] = (yf.Ticker(t).info or {}).get("sector") or ""
        except Exception:
            cache[t] = ""
        if progreso:
            progreso((i + 1) / max(1, len(pend)), t)
        if (i + 1) % 25 == 0 or i == len(pend) - 1:
            with open(CACHE_SECT, "w", encoding="utf-8") as fh:
                json.dump(cache, fh, ensure_ascii=False)
    return cache
 
 
def sector_de(t, cache):
    if t in DRIVERS or t == "OPENAI":
        return "Factor / sin cotización"
    s = cache.get(t)
    if s:
        return SECT_ES.get(s, s)
    for k, v in SECTOR_MAP.items():
        if t in v:
            return k
    return "Sin clasificar"
 
 
# ---------- figuras ----------
def figura_ego(A, vec, sector_fn, valor):
    """Un solo activo en el centro y sus vínculos alrededor. Pocos nodos, lectura rápida."""
    fig = go.Figure()
    n = len(vec)
    sectores = sorted({sector_fn(t) for t in vec["Nodo"]} | {sector_fn(A)})
    color = {s: PALETA[i % len(PALETA)] for i, s in enumerate(sectores)}
    orden = vec.assign(_s=[sector_fn(t) for t in vec["Nodo"]]).sort_values(["_s", "Nodo"]).reset_index(drop=True)
    pos = {A: (0.0, 0.0)}
    for i, nodo in enumerate(orden["Nodo"]):
        a = 2 * math.pi * i / max(n, 1) + math.pi / 2
        pos[nodo] = (math.cos(a), math.sin(a))
    # líneas estadísticas (grosor = fuerza) y flechas causales
    for _, r in orden.iterrows():
        x1, y1 = pos[r["Nodo"]]
        if pd.notna(r["Correlación"]):
            col = "rgba(46,125,50,0.55)" if r["Correlación"] > 0 else "rgba(198,40,40,0.6)"
            fig.add_trace(go.Scatter(x=[0, x1], y=[0, y1], mode="lines", hoverinfo="skip", showlegend=False,
                                     line=dict(color=col, width=1 + 7 * abs(float(r["Correlación"])))))
        if r["Dir"]:
            ini, fin = (0.16, 0.84) if r["Dir"] == "sale" else (0.84, 0.16)
            ac = "#1B5E20" if r["Signo"] > 0 else "#B71C1C"
            fig.add_annotation(x=x1 * fin, y=y1 * fin, ax=x1 * ini, ay=y1 * ini, xref="x", yref="y", axref="x",
                               ayref="y", showarrow=True, arrowhead=3, arrowsize=1.4, arrowwidth=2.4, arrowcolor=ac)
    xs, ys, txt, hov, siz, bord, sym, col_n = [], [], [], [], [], [], [], []
    for _, r in orden.iterrows():
        nodo = r["Nodo"]
        xs.append(pos[nodo][0]); ys.append(pos[nodo][1]); txt.append(ETIQUETA.get(nodo, nodo))
        c = r["Correlación"]
        siz.append(20 + (22 * abs(float(c)) if pd.notna(c) else 8))
        bord.append("#111111" if nodo in valor else "rgba(0,0,0,0)")
        sym.append("diamond" if nodo in DRIVERS or nodo == "OPENAI" else "circle")
        col_n.append(color[sector_fn(nodo)])
        h = f"<b>{ETIQUETA.get(nodo, nodo)}</b> · {sector_fn(nodo)}"
        if r["Rol"]:
            h += f"<br>Causal: {r['Rol']}"
        if pd.notna(c):
            h += f"<br>Correlación: {float(c):+.2f} · Beta: {float(r['Beta']):+.2f}"
        if pd.notna(r["Impacto %"]):
            h += f"<br>Impacto esperado: {float(r['Impacto %']):+.1f}% ({r['Fuente']})"
        if nodo in valor:
            h += "<br>En tu cartera"
        hov.append(h)
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="markers+text", text=txt, textposition="top center", hovertext=hov,
                             hoverinfo="text", showlegend=False, textfont=dict(size=11),
                             marker=dict(size=siz, color=col_n, symbol=sym, line=dict(color=bord, width=2.5))))
    fig.add_trace(go.Scatter(x=[0], y=[0], mode="markers+text", text=[ETIQUETA.get(A, A)], textposition="middle center",
                             hovertext=[f"<b>{ETIQUETA.get(A, A)}</b> · {sector_fn(A)}"], hoverinfo="text",
                             showlegend=False, textfont=dict(size=12, color="white"),
                             marker=dict(size=58, color="#004D40", line=dict(color="#111111" if A in valor else "#004D40",
                                                                            width=3))))
    for s in sectores:   # leyenda de sectores
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name=s, marker=dict(size=10, color=color[s])))
    fig.update_layout(height=560, margin=dict(l=0, r=0, t=0, b=0), plot_bgcolor="white",
                      xaxis=dict(visible=False, range=[-1.45, 1.45]),
                      yaxis=dict(visible=False, range=[-1.3, 1.3], scaleanchor="x"),
                      legend=dict(orientation="h", y=-0.02), hovermode="closest")
    return fig
 
 
def figura_sectores(corr_sec):
    fig = go.Figure(go.Heatmap(z=corr_sec.values, x=list(corr_sec.columns), y=list(corr_sec.index), zmin=-1, zmax=1,
                               colorscale=[[0, "#C62828"], [0.5, "#FFFFFF"], [1, "#2E7D32"]],
                               text=np.round(corr_sec.values, 2), texttemplate="%{text}", hoverongaps=False))
    fig.update_layout(height=520, margin=dict(l=0, r=0, t=10, b=0), yaxis=dict(autorange="reversed"))
    return fig
 
 
# ═════════════════════════════════════════════
# INTERFAZ
# ═════════════════════════════════════════════
st.set_page_config(layout="wide", page_title="SLY | Mapa de vínculos")
st.markdown("""
<style>
    .stApp { background-color: #FFFFFF; color: #1C1E21; }
    h1 { color: #004D40; font-weight: 800; border-bottom: 3px solid #004D40; }
</style>
""", unsafe_allow_html=True)
st.title("🔗 SLY | MAPA DE VÍNCULOS")
 
for k, v in {"edges_df": EDGES_DEFAULT.copy(), "cartera_df": CARTERA_DF_DEFAULT.copy(), "extra": [],
             "sectores": None, "precios": None, "errores_precios": []}.items():
    if k not in st.session_state:
        st.session_state[k] = v
if st.session_state["sectores"] is None:
    st.session_state["sectores"] = cargar_sectores()
if st.session_state["precios"] is None:
    import os
    st.session_state["precios"] = pd.read_pickle(CACHE_PRECIOS) if os.path.exists(CACHE_PRECIOS) else pd.DataFrame()
 
edges = limpiar_edges(st.session_state["edges_df"])
cartera = limpiar_cartera(st.session_state["cartera_df"])
valor = dict(zip(cartera["Ticker"], cartera["Valor ARS"]))
total_cartera = float(cartera["Valor ARS"].sum())
UNI = universo(cartera, st.session_state["extra"])
precios = st.session_state["precios"]
sec_cache = st.session_state["sectores"]
sector_fn = lambda t: sector_de(t, sec_cache)
 
 
@st.cache_data(show_spinner="Calculando vínculos…")
def matrices_cache(_precios, firma, dias, quitar):
    return calcular_matrices_puro(_precios, dias, quitar)
 
 
firma = (len(precios), str(precios.index.max()) if len(precios) else "")
 
with st.sidebar:
    st.header("⚙️ Datos")
    ventana = st.selectbox("Ventana de análisis:", list(VENTANAS), index=1)
    st.caption(f"{len(UNI)} activos en el universo (tu lista del V56 + tu cartera + factores).")
    nuevos = st.text_input("Agregar tickers (separados por coma):", "")
    if nuevos:
        st.session_state["extra"] = sorted({t.strip().upper() for t in nuevos.split(",") if t.strip()})
    if st.button("🚀 Descargar / actualizar precios", type="primary", use_container_width=True):
        barra = st.progress(0, text="Descargando por lotes…")
        df, errs = descargar_precios(UNI, 100, "2y", lambda p: barra.progress(p, text="Descargando por lotes…"))
        barra.empty()
        if not df.empty:
            df.to_pickle(CACHE_PRECIOS)
            st.session_state["precios"] = df
        st.session_state["errores_precios"] = errs
        st.rerun()
    if len(precios):
        st.caption(f"Precios hasta {precios.index.max():%d/%m/%Y} · {precios.shape[1]} activos con datos.")
    else:
        st.info("Todavía no hay precios. Descargalos para ver los vínculos por datos.")
    if st.button("🏷️ Cargar sectores (una vez, tarda unos minutos)", use_container_width=True):
        barra = st.progress(0, text="Sectores…")
        st.session_state["sectores"] = descargar_sectores(
            UNI, dict(sec_cache), lambda p, t: barra.progress(p, text=f"Sector de {t}"))
        barra.empty()
        st.rerun()
    if st.session_state["errores_precios"]:
        with st.expander("⚠️ Errores de descarga"):
            st.write("\n\n".join(st.session_state["errores_precios"]))
 
tab_v, tab_s, tab_sec, tab_c = st.tabs(["🔗 Vínculos", "💥 Simulador", "🧭 Sectores", "💼 Mi cartera"])
OPCIONES = sorted(set(UNI) | DRIVERS | {"OPENAI"})
nombre = lambda n: f"{ETIQUETA[n]} ({n})" if n in ETIQUETA else n
dias = VENTANAS[ventana]
 
# ---------------- Vínculos ----------------
with tab_v:
    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    A = c1.selectbox("Activo o factor:", OPCIONES, index=OPCIONES.index("NVDA") if "NVDA" in OPCIONES else 0,
                     format_func=nombre)
    n_pos = c2.slider("Se mueven igual", 0, 15, 8)
    n_neg = c3.slider("Se mueven al revés", 0, 6, 3)
    shock = c4.number_input("Si se mueve (%)", -50.0, 50.0, -5.0, 0.5)
    quitar = st.checkbox("Quitar el efecto del mercado (SPY)", value=True,
                         help="Con esto ves lo propio de cada vínculo (sector, cadena de suministro) y no solo que "
                              "'todo sube y baja con el mercado'.")
    R, corr, cov = matrices_cache(precios, firma, dias, quitar) if len(precios) else (pd.DataFrame(),) * 3
    vec = tabla_vecinos(A, edges, corr, cov, shock, n_pos, n_neg)
    if vec.empty:
        st.info("No hay vínculos para este activo. Descargá precios (barra lateral) o agregale vínculos causales en 'Mi cartera'.")
    else:
        gcol, tcol = st.columns([3, 2])
        with gcol:
            st.plotly_chart(figura_ego(A, vec, sector_fn, valor), use_container_width=True)
            st.caption("Línea verde: se mueven en el mismo sentido · roja: al revés · grosor = fuerza (correlación). "
                       "Flecha: vínculo causal de la cadena de negocio (criterio manual). ◆ factor sin cotización · "
                       "borde negro: está en tu cartera.")
        with tcol:
            st.markdown(f"**Si {nombre(A)} se mueve {shock:+.1f}%, lo esperable es:**")
            vista = pd.DataFrame({
                "Activo": vec["Nodo"], "Sector": [sector_fn(t) for t in vec["Nodo"]],
                "Corr.": vec["Correlación"].round(2), "Impacto %": vec["Impacto %"].round(2), "Fuente": vec["Fuente"],
                "Vínculo causal": vec["Rol"], "Mi cartera (ARS)": [valor.get(t, np.nan) for t in vec["Nodo"]]})
            st.dataframe(vista, hide_index=True, use_container_width=True, height=520)
        if not len(precios):
            st.warning("Solo se muestran los vínculos causales (criterio manual). Descargá precios para sumar los vínculos medidos con datos.")
    st.caption("Correlación no es causalidad: dos activos pueden moverse juntos por un tercer factor. "
               "'Impacto %' por datos = beta histórica × el movimiento; por criterio = peso manual del vínculo. Es una guía, no una predicción.")
 
# ---------------- Simulador ----------------
with tab_s:
    if not len(precios):
        st.info("Descargá precios para simular con datos. Sin precios solo funciona el contagio causal de los factores.")
    s1, s2, s3 = st.columns([2, 1, 1])
    O = s1.selectbox("Qué se mueve:", OPCIONES, index=OPCIONES.index("NVDA") if "NVDA" in OPCIONES else 0,
                     format_func=nombre, key="sim_o")
    sh = s2.slider("Variación (%)", -30.0, 30.0, -10.0, 0.5, key="sim_sh")
    ccl = s3.slider("Dólar CCL (%)", -20.0, 20.0, 0.0, 0.5)
    mercado_ok = st.checkbox("Incluir el movimiento general del mercado", value=True,
                             help="Si cae una empresa grande, suele arrastrar al índice. Tildado = efecto total. "
                                  "Destildado = solo el vínculo propio.")
    Rs, corr_s, cov_s = matrices_cache(precios, firma, dias, not mercado_ok) if len(precios) else (pd.DataFrame(),) * 3
    ef, fuente = efectos_simulador(O, sh, edges, cov_s, 3, 0.7)
    imp = impacto_cartera(ef, cartera)
    imp["Efecto total %"] = (1 + imp["Efecto %"] / 100) * (1 + ccl / 100) * 100 - 100
    imp["Impacto ARS"] = imp["Valor ARS"] * imp["Efecto total %"] / 100
    imp["Fuente"] = imp["Ticker"].map(fuente).fillna("—")
    tot = float(imp["Impacto ARS"].sum())
    m1, m2 = st.columns(2)
    m1.metric("Impacto estimado en tu cartera", f"ARS {tot:,.0f}".replace(",", "."),
              f"{tot / total_cartera * 100:+.2f}%" if total_cartera else "")
    m2.metric("Posiciones con efecto", int((imp["Efecto %"].abs() > 0.05).sum()))
    a, b = st.columns(2)
    with a:
        st.markdown("**Los más afectados (todo el universo)**")
        top = pd.DataFrame([{"Activo": k, "Sector": sector_fn(k), "Efecto %": round(v, 2), "Fuente": fuente[k],
                             "En cartera": k in valor} for k, v in ef.items()])
        if len(top):
            st.dataframe(top.sort_values("Efecto %", key=lambda s_: s_.abs(), ascending=False).head(25),
                         hide_index=True, use_container_width=True, height=420)
    with b:
        st.markdown("**Tu cartera**")
        v2 = imp[imp["Efecto %"].abs() > 0.05].sort_values("Impacto ARS")[
            ["Ticker", "Valor ARS", "Efecto total %", "Impacto ARS", "Fuente"]].round(2)
        st.dataframe(v2, hide_index=True, use_container_width=True, height=420)
    st.caption("Por datos: beta histórica de cada activo respecto del que se mueve. Por criterio: contagio causal manual "
               "(factores y activos sin historial). El CCL se combina aparte. No es una predicción.")
 
# ---------------- Sectores ----------------
with tab_sec:
    if not len(precios):
        st.info("Descargá precios para ver cómo se mueven los sectores entre sí.")
    else:
        q2 = st.checkbox("Quitar el efecto del mercado (SPY)", value=True, key="q_sec")
        Rq, cq, _ = matrices_cache(precios, firma, dias, q2)
        rs = retorno_sectorial(Rq, sector_fn)
        if rs.shape[1] < 3:
            st.info("Hay pocos sectores clasificados. Usá '🏷️ Cargar sectores' en la barra lateral.")
        else:
            cs = rs.corr(min_periods=MIN_OBS)
            st.plotly_chart(figura_sectores(cs), use_container_width=True)
            st.caption("Verde: sectores que se mueven juntos · rojo: se mueven al revés. Cada sector es el promedio "
                       "de sus activos. Más sectores aparecen al cargar los sectores desde yfinance.")
 
# ---------------- Mi cartera ----------------
with tab_c:
    st.markdown("**Tu cartera** (valores en ARS; los iniciales son los de tu captura del 5/11, actualizalos)")
    st.session_state["cartera_df"] = st.data_editor(st.session_state["cartera_df"], num_rows="dynamic",
                                                    use_container_width=True, key="ed_cartera", height=300)
    if len(precios):
        Rc, cc, _ = matrices_cache(precios, firma, dias, True)
        pc = pares_cartera(cc, list(cartera["Ticker"]), 10)
        st.markdown("**Riesgo oculto: tus posiciones que más se mueven juntas** (sin efecto del mercado)")
        st.dataframe(pc.round(2), hide_index=True, use_container_width=True)
    with st.expander("✏️ Editar vínculos causales (criterio manual)"):
        st.markdown("signo +1 (mismo sentido) o -1 (inverso) · peso: intensidad (1.0 = se mueve igual) · "
                    "usá los tickers (NVDA, TSM…) o factores (TASAS, BRENT…).")
        st.session_state["edges_df"] = st.data_editor(st.session_state["edges_df"], num_rows="dynamic",
                                                      use_container_width=True, height=420, key="ed_edges")
        d1, d2 = st.columns(2)
        d1.download_button("⬇️ Bajar vínculos (CSV)", st.session_state["edges_df"].to_csv(index=False).encode("utf-8"),
                           "vinculos_sly.csv", "text/csv")
        sub = d2.file_uploader("Subir vínculos (CSV)", type="csv")
        if sub is not None and st.session_state.get("csv_cargado") != (sub.name, sub.size):
            st.session_state["csv_cargado"] = (sub.name, sub.size)
            try:
                st.session_state["edges_df"] = pd.read_csv(sub)[EDGE_COLS]
                st.rerun()
            except Exception as ex:
                st.error(f"No pude leer el CSV: {ex}")
        if st.button("↩️ Volver a los originales"):
            st.session_state["edges_df"] = EDGES_DEFAULT.copy()
            st.session_state["cartera_df"] = CARTERA_DF_DEFAULT.copy()
            st.rerun()
