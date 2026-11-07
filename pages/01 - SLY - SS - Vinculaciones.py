"""
SLY | MAPA DE VÍNCULOS  —  quién depende de quién y cómo se contagia un shock.
 
Requisitos:  pip install streamlit plotly pandas numpy
Ejecutar:    streamlit run sly_mapa_vinculos.py
 
IMPORTANTE: los vínculos y pesos son un criterio aproximado armado a mano (hipótesis de trabajo),
NO datos oficiales ni una predicción. Podés corregirlos desde la pestaña "Editar vínculos".
"""
import math
 
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
 
# ─────────────────────────────────────────────
# NODOS  (id -> (ecosistema, descripción))
# Los nodos "driver" son factores/sectores (no empresas): demanda, commodities, macro.
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
 
 
# ─────────────────────────────────────────────
# LÓGICA
# ─────────────────────────────────────────────
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
 
 
def armar_nodos(edges, cartera):
    """Nodos conocidos + cualquier ticker nuevo que aparezca en vínculos o cartera (grupo 'Otros')."""
    nodos = dict(NODOS)
    for t in set(edges["origen"]) | set(edges["destino"]) | set(cartera["Ticker"]):
        if t not in nodos:
            nodos[t] = ("Otros", "Agregado por el usuario")
    return nodos
 
 
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
 
 
def sensibilidad_por_factor(edges, cartera, shock=-10.0, profundidad=3, decaimiento=0.7):
    """Qué factor (driver) le pegaría más a tu cartera ante un shock de -10%."""
    filas = []
    total = float(cartera["Valor ARS"].sum())
    for dr in sorted(DRIVERS):
        if dr not in set(edges["origen"]):
            continue
        ef = propagar(edges, dr, shock, profundidad, decaimiento)
        imp = float(impacto_cartera(ef, cartera)["Impacto ARS"].sum())
        filas.append({"Factor": ETIQUETA.get(dr, dr), "Shock": shock, "Impacto ARS": imp,
                      "Impacto % cartera": imp / total * 100 if total else 0.0})
    return pd.DataFrame(filas).sort_values("Impacto ARS").reset_index(drop=True)
 
 
def posiciones(nodos):
    """Cada ecosistema es un racimo: factores adentro, empresas en el anillo exterior."""
    centros = {"IA y centros de datos": (0, 0), "Energía y metales": (9, 3), "Cripto": (9, -3.6),
               "Consumo y medios": (-9, 3.5), "Salud": (-9, -3.6), "Defensa y aeroespacial": (0, -8.5),
               "Japón y autos": (0, 8.2), "Tasas y macro": (-9, 9.5), "Otros": (9, -9)}
    pos = {}
    grupos = {}
    for n, (g, _) in nodos.items():
        grupos.setdefault(g, []).append(n)
    for g, ns in grupos.items():
        cx, cy = centros.get(g, (0, 0))
        drivers = [n for n in ns if n in DRIVERS]
        emp = [n for n in ns if n not in DRIVERS]
        r_out = 0.9 + 0.17 * len(emp) if emp else 0
        r_in = 0 if len(drivers) <= 1 else 0.6 + 0.12 * len(drivers)
        for i, n in enumerate(drivers):
            a = 2 * math.pi * i / max(1, len(drivers))
            pos[n] = (cx + r_in * math.cos(a), cy + r_in * math.sin(a))
        for i, n in enumerate(emp):
            a = 2 * math.pi * i / max(1, len(emp)) + math.pi / 2
            pos[n] = (cx + r_out * math.cos(a), cy + r_out * math.sin(a))
    return pos
 
 
def figura(nodos, edges, cartera, seleccion=None, efectos=None):
    pos = posiciones(nodos)
    valor = dict(zip(cartera["Ticker"], cartera["Valor ARS"]))
    total = max(1.0, float(cartera["Valor ARS"].sum()))
    vecinos = set()
    if seleccion:
        vecinos = set(edges.loc[edges["origen"] == seleccion, "destino"]) | set(
            edges.loc[edges["destino"] == seleccion, "origen"])
    activos = ({seleccion} | vecinos) if seleccion else set(nodos)
 
    fig = go.Figure()
    # líneas tenues: verde = mismo sentido, rojo = sentido inverso
    for signo, color in ((1, "rgba(46,125,50,0.18)"), (-1, "rgba(198,40,40,0.22)")):
        xs, ys = [], []
        for o, d, s in zip(edges["origen"], edges["destino"], edges["signo"]):
            if s == signo and o in pos and d in pos:
                xs += [pos[o][0], pos[d][0], None]
                ys += [pos[o][1], pos[d][1], None]
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=color, width=1),
                                 hoverinfo="skip", showlegend=False))
    # vínculos del nodo elegido, con flecha
    if seleccion:
        for o, d, s, w in zip(edges["origen"], edges["destino"], edges["signo"], edges["peso"]):
            if (o == seleccion or d == seleccion) and o in pos and d in pos:
                fig.add_annotation(x=pos[d][0], y=pos[d][1], ax=pos[o][0], ay=pos[o][1], xref="x", yref="y",
                                   axref="x", ayref="y", showarrow=True, arrowhead=3, arrowsize=1.2,
                                   arrowwidth=1 + 2.2 * min(w, 1.5),
                                   arrowcolor="#2E7D32" if s > 0 else "#C62828", opacity=0.9)
    # nodos por ecosistema
    for g, color in list(GRUPOS.items()) + [("Otros", "#9E9E9E")]:
        ns = [n for n, (gg, _) in nodos.items() if gg == g and n in pos]
        if not ns:
            continue
        sizes, lines, texts, hov, opac = [], [], [], [], []
        for n in ns:
            en_cartera = n in valor
            base = 16 if n in DRIVERS else 12
            sizes.append(base + (min(28, math.sqrt(valor[n] / total) * 70) if en_cartera else 0))
            lines.append("#111111" if en_cartera else "rgba(0,0,0,0)")
            texts.append(ETIQUETA.get(n, n))
            ef = efectos.get(n) if efectos else None
            hov.append(f"<b>{ETIQUETA.get(n, n)}</b><br>{nodos[n][1]}"
                       + (f"<br>En cartera: ARS {valor[n]:,.0f}".replace(",", ".") if n in valor else "")
                       + (f"<br>Efecto simulado: {ef:+.1f}%" if ef is not None else ""))
            opac.append(1.0 if n in activos else 0.18)
        symbols = ["diamond" if n in DRIVERS else "circle" for n in ns]
        fig.add_trace(go.Scatter(
            x=[pos[n][0] for n in ns], y=[pos[n][1] for n in ns], mode="markers+text", name=g,
            text=texts, textposition="top center", textfont=dict(size=10), hovertext=hov, hoverinfo="text",
            marker=dict(size=sizes, color=color, symbol=symbols, opacity=opac, line=dict(color=lines, width=2.2))))
    fig.update_layout(height=720, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor="white",
                      xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x"),
                      legend=dict(orientation="h", y=-0.02), hovermode="closest")
    return fig
 
 
def tabla_vinculos(edges, nodo):
    """Qué le pasa a 'nodo' y a quién afecta, en palabras."""
    sale = edges[edges["origen"] == nodo].copy()
    entra = edges[edges["destino"] == nodo].copy()
    sale["Lectura"] = [f"Si {ETIQUETA.get(nodo, nodo)} sube, {ETIQUETA.get(d, d)} tiende a {'subir' if s > 0 else 'bajar'}"
                       for d, s in zip(sale["destino"], sale["signo"])]
    entra["Lectura"] = [f"Si {ETIQUETA.get(o, o)} sube, {ETIQUETA.get(nodo, nodo)} tiende a {'subir' if s > 0 else 'bajar'}"
                        for o, s in zip(entra["origen"], entra["signo"])]
    return sale, entra
 
 
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
st.title("🕸️ SLY | MAPA DE VÍNCULOS")
st.caption("Quién le vende a quién, quién depende de qué factor y cómo se contagia un shock. "
           "Los vínculos y pesos son aproximados y editables: sirven para ordenar ideas, no para predecir precios.")
 
if "edges_df" not in st.session_state:
    st.session_state["edges_df"] = EDGES_DEFAULT.copy()
if "cartera_df" not in st.session_state:
    st.session_state["cartera_df"] = CARTERA_DF_DEFAULT.copy()
 
tab_mapa, tab_sim, tab_sens, tab_edit = st.tabs(
    ["🗺️ Mapa", "💥 Simulador de shock", "📊 Sensibilidad de mi cartera", "✏️ Editar vínculos y cartera"])
 
edges = limpiar_edges(st.session_state["edges_df"])
cartera = limpiar_cartera(st.session_state["cartera_df"])
nodos = armar_nodos(edges, cartera)
total_cartera = float(cartera["Valor ARS"].sum())
 
 
def nombre(n):
    return f"{ETIQUETA.get(n, n)}  ({n})" if n in ETIQUETA else n
 
 
# ---------------- Mapa ----------------
with tab_mapa:
    c1, c2 = st.columns([1, 3])
    with c1:
        opciones = ["(ninguno)"] + sorted(nodos, key=lambda n: (nodos[n][0], n))
        sel = st.selectbox("Elegí un nodo para ver sus vínculos:", opciones, format_func=lambda n: n if n == "(ninguno)" else nombre(n))
        sel = None if sel == "(ninguno)" else sel
        st.markdown("**Cómo leerlo**\n- ◆ factor o sector · ● empresa\n- Borde negro: está en tu cartera (más grande = más peso)\n"
                    "- Flecha verde: el destino se mueve en el mismo sentido · roja: en sentido inverso\n- Grosor de la flecha: intensidad aproximada")
        if sel:
            sale, entra = tabla_vinculos(edges, sel)
            st.markdown(f"**{nodos[sel][1]}**")
            if sel in set(cartera["Ticker"]):
                v = float(cartera.loc[cartera["Ticker"] == sel, "Valor ARS"].iloc[0])
                st.metric("En tu cartera", f"ARS {v:,.0f}".replace(",", "."), f"{v / total_cartera * 100:.1f}% del total" if total_cartera else "")
    with c2:
        st.plotly_chart(figura(nodos, edges, cartera, sel), use_container_width=True)
    if sel:
        a, b = st.columns(2)
        with a:
            st.markdown(f"**Afecta a** ({len(sale)})")
            st.dataframe(sale[["Lectura", "peso", "tipo", "confianza"]], hide_index=True, use_container_width=True)
        with b:
            st.markdown(f"**Depende de** ({len(entra)})")
            st.dataframe(entra[["Lectura", "peso", "tipo", "confianza"]], hide_index=True, use_container_width=True)
 
# ---------------- Simulador ----------------
with tab_sim:
    st.markdown("Elegí qué se mueve y cuánto. El efecto se propaga por los vínculos y se pierde fuerza en cada salto.")
    s1, s2, s3, s4 = st.columns(4)
    origen = s1.selectbox("Qué se mueve:", sorted(nodos, key=lambda n: (nodos[n][0], n)), format_func=nombre,
                          index=sorted(nodos, key=lambda n: (nodos[n][0], n)).index("IA_GASTO") if "IA_GASTO" in nodos else 0)
    shock = s2.slider("Variación (%)", -30.0, 30.0, -10.0, 0.5)
    prof = s3.slider("Saltos de contagio", 1, 4, 3)
    decae = s4.slider("Fuerza que se mantiene desde el 2.º salto", 0.3, 1.0, 0.7, 0.05)
    ccl = st.slider("Variación del dólar CCL (%) — afecta a todos los CEDEARs en pesos", -20.0, 20.0, 0.0, 0.5)
 
    efectos = propagar(edges, origen, shock, prof, decae)
    imp = impacto_cartera(efectos, cartera)
    imp["Efecto total %"] = (1 + imp["Efecto %"] / 100) * (1 + ccl / 100) * 100 - 100
    imp["Impacto total ARS"] = imp["Valor ARS"] * imp["Efecto total %"] / 100
    tot = float(imp["Impacto total ARS"].sum())
    m1, m2, m3 = st.columns(3)
    m1.metric("Impacto estimado en tu cartera", f"ARS {tot:,.0f}".replace(",", "."),
              f"{tot / total_cartera * 100:+.2f}%" if total_cartera else "")
    m2.metric("Posiciones afectadas", int((imp["Efecto %"].abs() > 0.05).sum()))
    m3.metric("Nodos alcanzados", len(efectos))
    st.plotly_chart(figura(nodos, edges, cartera, origen, efectos), use_container_width=True)
 
    lista = pd.DataFrame([{"Nodo": nombre(n), "Efecto %": round(v, 2), "En cartera": n in set(cartera["Ticker"])}
                          for n, v in efectos.items() if n != origen])
    cA, cB = st.columns(2)
    with cA:
        st.markdown("**Todos los nodos alcanzados**")
        if len(lista):
            st.dataframe(lista.sort_values("Efecto %", key=lambda s: s.abs(), ascending=False), hide_index=True,
                         use_container_width=True, height=380)
        else:
            st.info("Ese nodo no tiene vínculos de salida en la tabla actual.")
    with cB:
        st.markdown("**Tu cartera: mayor impacto**")
        vista = imp[imp["Efecto %"].abs() > 0.05].sort_values("Impacto total ARS")[
            ["Ticker", "Valor ARS", "Efecto %", "Impacto total ARS"]].round(2)
        st.dataframe(vista, hide_index=True, use_container_width=True, height=380)
    st.caption("El primer salto usa el peso completo del vínculo. Se toma la ruta de mayor efecto para cada nodo (no se suman rutas). Los pesos son criterio aproximado. "
               "El CCL se combina aparte: efecto total = (1 + efecto del activo) × (1 + CCL) − 1.")
 
# ---------------- Sensibilidad ----------------
with tab_sens:
    st.markdown("¿A qué factor está más expuesta tu cartera? Se aplica un shock de **-10%** a cada factor "
                "(IA, petróleo, tasas, bitcoin, etc.) y se mide cuánto perdería tu cartera.")
    sh = st.slider("Shock a aplicar (%)", -30.0, -2.0, -10.0, 1.0, key="sh_sens")
    sens = sensibilidad_por_factor(edges, cartera, sh, 3, 0.7)
    if sens.empty:
        st.info("No hay factores con vínculos en la tabla actual.")
    else:
        fig2 = go.Figure(go.Bar(x=sens["Impacto % cartera"], y=sens["Factor"], orientation="h",
                                marker_color=["#C62828" if v < 0 else "#2E7D32" for v in sens["Impacto % cartera"]],
                                text=[f"{v:+.2f}%" for v in sens["Impacto % cartera"]], textposition="outside"))
        fig2.update_layout(height=520, margin=dict(l=0, r=40, t=10, b=0), plot_bgcolor="white",
                           xaxis_title="Impacto estimado sobre el total de la cartera (%)")
        st.plotly_chart(fig2, use_container_width=True)
        st.dataframe(sens.round(2), hide_index=True, use_container_width=True)
        st.caption("Negativo = te perjudica; positivo = te beneficia (p. ej. una baja de tasas o de inflación).")
    # exposición por ecosistema
    st.markdown("**Cuánto de tu cartera está en cada ecosistema**")
    por_grupo = cartera.assign(Ecosistema=cartera["Ticker"].map(lambda t: nodos[t][0] if t in nodos else "Otros"))
    por_grupo = por_grupo.groupby("Ecosistema", as_index=False)["Valor ARS"].sum().sort_values("Valor ARS", ascending=False)
    por_grupo["% cartera"] = (por_grupo["Valor ARS"] / total_cartera * 100).round(1) if total_cartera else 0.0
    st.dataframe(por_grupo, hide_index=True, use_container_width=True)
    st.caption("Ojo: un mismo activo puede depender de más de un factor, y MSTR suma exposición a cripto aunque la veas en otro rubro.")
 
# ---------------- Edición ----------------
with tab_edit:
    st.markdown("**Tu cartera** (valores en ARS; los iniciales son los de tu captura del 5/11 — actualizalos)")
    st.session_state["cartera_df"] = st.data_editor(st.session_state["cartera_df"], num_rows="dynamic",
                                                    use_container_width=True, key="ed_cartera")
    st.markdown("**Vínculos** — signo +1 (mismo sentido) o -1 (inverso) · peso: intensidad (1.0 = se mueve igual) · "
                "usá los códigos de los nodos (NVDA, TASAS, BRENT…). Podés agregar filas y empresas nuevas.")
    st.session_state["edges_df"] = st.data_editor(st.session_state["edges_df"], num_rows="dynamic",
                                                  use_container_width=True, height=520, key="ed_edges")
    cdl1, cdl2 = st.columns(2)
    cdl1.download_button("⬇️ Bajar vínculos (CSV)", st.session_state["edges_df"].to_csv(index=False).encode("utf-8"),
                         "vinculos_sly.csv", "text/csv")
    sub = cdl2.file_uploader("Subir vínculos (CSV con las mismas columnas)", type="csv")
    if sub is not None and st.session_state.get("csv_cargado") != (sub.name, sub.size):
        try:
            st.session_state["edges_df"] = pd.read_csv(sub)[EDGE_COLS]
            st.session_state["csv_cargado"] = (sub.name, sub.size)
            st.success("Vínculos cargados.")
            st.rerun()
        except Exception as ex:
            st.session_state["csv_cargado"] = (sub.name, sub.size)
            st.error(f"No pude leer el CSV: {ex}")
    if st.button("↩️ Volver a los vínculos y cartera originales"):
        st.session_state["edges_df"] = EDGES_DEFAULT.copy()
        st.session_state["cartera_df"] = CARTERA_DF_DEFAULT.copy()
        st.rerun()
    st.caption("Los cambios viven en la sesión del navegador: si cerrás la pestaña se pierden. Bajá el CSV para guardarlos.")
