import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
import plotly.graph_objects as go
from datetime import datetime, timedelta
 
# ─────────────────────────────────────────────
# CONFIGURACIÓN INSTITUCIONAL - LIGHT THEME
# ─────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="SLY | CRIPTO MULTI-TF MONITOR")
 
st.markdown("""
<style>
    .stApp { background-color: #FFFFFF; color: #1C1E21; }
    .stDataFrame { font-size: 11px; font-family: 'Roboto Mono', monospace; }
    h1 { color: #E65100; font-weight: 800; border-bottom: 3px solid #E65100; }
    .stProgress > div > div > div > div { background-color: #E65100; }
    .sector-box { background-color: #FFF3E0; padding: 15px; border-radius: 8px; border-left: 5px solid #E64A19; margin-bottom: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .sector-title { font-weight: bold; color: #BF360C; font-size: 1.1em; }
</style>
""", unsafe_allow_html=True)
 
if "master_results_crypto" not in st.session_state:
    st.session_state["master_results_crypto"] = {}
for _k in ("liq_mapas", "liq_errores"):
    if _k not in st.session_state:
        st.session_state[_k] = {}
 
# Mapeo de temporalidades para CCXT
TF_OPTIONS = {
    "30 MIN": "30m",
    "1 HS": "1h",
    "4 HS": "4h",
    "1 DIA": "1d",
    "1 SEMANA": "1w",
    "1 MES": "1M"
}
 
# ─────────────────────────────────────────────
# MAPEO SECTORIAL CRIPTO
# ─────────────────────────────────────────────
CRYPTO_SECTORS = {
    "LEADER": ["BTC/USDT", "ETH/USDT"],
    "LAYER 1": ["SOL/USDT", "ADA/USDT", "DOT/USDT", "AVAX/USDT", "MATIC/USDT", "NEAR/USDT", "FTM/USDT", "ALGO/USDT"],
    "DEFI/L2": ["ARB/USDT", "OP/USDT", "LINK/USDT", "UNI/USDT", "AAVE/USDT", "LDO/USDT"],
    "AI/DEPIN": ["RNDR/USDT", "FET/USDT", "FIL/USDT", "THETA/USDT"],
    "MEMES": ["DOGE/USDT", "SHIB/USDT", "PEPE/USDT", "BONK/USDT", "FLOKI/USDT"],
    "EXCHANGE": ["BNB/USDT", "KCS/USDT", "OKB/USDT"]
}
 
def get_crypto_sector(ticker):
    for sector, members in CRYPTO_SECTORS.items():
        if ticker.upper() in members: return sector
    return "ALTCOINS / OTROS"
 
# ─────────────────────────────────────────────
# MOTORES TÉCNICOS SLY
# ─────────────────────────────────────────────
def dema(s, length):
    ema1 = s.ewm(span=length, adjust=False).mean()
    ema2 = ema1.ewm(span=length, adjust=False).mean()
    return 2 * ema1 - ema2
 
# --- RSI PRO: parámetros por defecto (idénticos al Pine Script) ---
RSI_BB_MULT = 2.0
VOL_Z_THRESHOLD = 1.5
 
def get_sly_indicators(df):
    """
    Devuelve (dataframe_calculado, motivo).
    Si el cálculo fue exitoso: motivo = "OK".
    Si no: dataframe vacío y motivo con la explicación puntual.
    """
    try:
        df.columns = [c.capitalize() for c in df.columns]
        df = df.dropna(subset=['Close'])
        velas_totales = len(df)
 
        df['macd_line'] = dema(df['Close'], 12) - dema(df['Close'], 26)
        df['signal_line'] = df['macd_line'].ewm(span=9, adjust=False).mean()
        df['hist'] = df['macd_line'] - df['signal_line']
        df['rsi_smooth'] = dema(ta.rsi(df['Close'], length=14).fillna(50), 5)
 
        # ─────────────────────────────────────
        # RSI PRO (AGREGADO) — Bandas estadísticas dinámicas
        # (Bollinger sobre el RSI, igual que el segundo script Pine)
        # ─────────────────────────────────────
        df['rsi_basis'] = df['rsi_smooth'].rolling(20).mean()
        df['rsi_std']   = df['rsi_smooth'].rolling(20).std()
        df['rsi_upper'] = df['rsi_basis'] + (RSI_BB_MULT * df['rsi_std'])
        df['rsi_lower'] = df['rsi_basis'] - (RSI_BB_MULT * df['rsi_std'])
 
        # ─────────────────────────────────────
        # RSI PRO (AGREGADO) — Filtro de volumen institucional (Z-score)
        # ─────────────────────────────────────
        df['vol_avg'] = df['Vol'].rolling(20).mean()
        df['vol_std'] = df['Vol'].rolling(20).std()
        df['vol_z']   = (df['Vol'] - df['vol_avg']) / df['vol_std']
        df['vol_alpha'] = df['vol_z'] > VOL_Z_THRESHOLD
 
        # ─────────────────────────────────────
        # RSI PRO (AGREGADO) — Estado cromático de 4 niveles
        # Verde fuerte  -> RSI > 50 y subiendo   (lo que pediste: "se pone en verde")
        # Verde débil   -> RSI > 50 pero bajando
        # Rojo fuerte   -> RSI < 50 y bajando
        # Rojo débil    -> RSI < 50 pero subiendo
        # ─────────────────────────────────────
        rsi_now  = df['rsi_smooth']
        rsi_prev = df['rsi_smooth'].shift(1)
        conditions = [
            (rsi_now > 50) & (rsi_now > rsi_prev),
            (rsi_now > 50) & (rsi_now <= rsi_prev),
            (rsi_now < 50) & (rsi_now < rsi_prev),
            (rsi_now < 50) & (rsi_now >= rsi_prev),
        ]
        choices = ["ALCISTA FUERTE 🟢🟢", "ALCISTA DÉBIL 🟢", "BAJISTA FUERTE 🔴🔴", "BAJISTA DÉBIL 🔴"]
        df['rsi_state'] = np.select(conditions, choices, default="NEUTRAL ⚪")
 
        # ─────────────────────────────────────
        # RSI PRO (AGREGADO) — Señales Alpha Strike / Agotamiento
        # ─────────────────────────────────────
        cross_up_50 = (rsi_now > 50) & (rsi_prev <= 50)
        df['alpha_strike'] = cross_up_50 & df['vol_alpha']
 
        cross_under_upper = (rsi_now < df['rsi_upper']) & (rsi_prev >= df['rsi_upper'].shift(1))
        df['exhaustion'] = cross_under_upper
 
        ha_c = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
        ha_o = np.zeros(len(df))
        ha_o[0] = (df['Open'].iloc[0] + df['Close'].iloc[0]) / 2
        for i in range(1, len(df)): ha_o[i] = (ha_o[i-1] + ha_c.iloc[i-1]) / 2
        df['ha_color'] = np.where(ha_c > ha_o, "Verde", "Rojo")
        df['ema52'] = ta.ema(df['Close'], length=52)
        df['ema260'] = ta.ema(df['Close'], length=260)
 
        resultado = df.dropna(subset=['ema260'])
        if resultado.empty:
            # El motivo casi siempre es historial insuficiente: EMA260 necesita
            # 260 velas válidas y este símbolo/timeframe no llega a esa cantidad.
            return pd.DataFrame(), f"Historial insuficiente: {velas_totales} velas disponibles (se necesitan ≥260 para EMA260)"
        return resultado, "OK"
    except Exception as e:
        return pd.DataFrame(), f"Error de cálculo: {type(e).__name__}: {e}"
 
# NUEVA FUNCIÓN: Analizar fuerza MACD Mensual
def get_monthly_macd_force(ex, symbol):
    try:
        # Pedimos pocas velas (50 son suficientes para MACD estable)
        raw = ex.fetch_ohlcv(symbol, timeframe='1M', limit=50)
        df = pd.DataFrame(raw, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
        
        m_macd = dema(df['close'], 12) - dema(df['close'], 26)
        m_signal = m_macd.ewm(span=9, adjust=False).mean()
        m_hist = m_macd - m_signal
        
        current_h = m_hist.iloc[-1]
        previous_h = m_hist.iloc[-2]
        
        if current_h > previous_h:
            return "GANANDO FUERZA 📈"
        else:
            return "PERDIENDO FUERZA 📉"
    except:
        return "N/A"
 
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
# LIQUIDACIONES ESTIMADAS (2do script integrado)
# Usa velas de 1 H + interés abierto de un exchange de perpetuos (Bybit/OKX).
# Es independiente de la temporalidad elegida arriba y de KuCoin spot.
# ─────────────────────────────────────────────
LEVS = [10, 25, 50, 100]
PESOS = [0.40, 0.30, 0.20, 0.10]
MMR = 0.005              # margen de mantenimiento aproximado (0,5 %)
RANGO, PASO = 0.15, 0.0025   # se mapea ±15 % alrededor del precio, en pasos de 0,25 %
BARS = 500               # 500 velas de 1 h ≈ 20 días (Binance entrega ~30 días de OI)
HOUR_MS = 3_600_000
 
 
def fmt_px(x):
    return f"{x:.6g}"
 
 
def fetch_velas_oi(ex, ex_id, sym):
    """Velas de 1 h y OI por hora (en USD) del mismo período."""
    ohlcv = ex.fetch_ohlcv(sym, timeframe="1h", limit=BARS)
    df = pd.DataFrame(ohlcv, columns=["time", "open", "high", "low", "close", "vol"])
    lim = {"bybit": 200, "okx": 100}.get(ex_id, 500)
    hist = ex.fetch_open_interest_history(sym, timeframe="1h", limit=lim)
    filas = []
    for h in hist:
        val = h.get("openInterestValue")
        if val is None and h.get("openInterestAmount") is not None:
            val = None   # se completa más abajo con el precio
        filas.append({"time": h.get("timestamp"), "amt": h.get("openInterestAmount"), "val": val})
    oi = pd.DataFrame(filas).dropna(subset=["time"])
    if oi.empty:
        raise ValueError("El exchange no devolvió interés abierto para este símbolo")
    oi["time"] = oi["time"].astype("int64")
    df = df.drop_duplicates("time").sort_values("time").reset_index(drop=True)
    if oi["val"].isna().all():            # sin valor en USD: cantidad × precio de cierre de esa hora
        mm = pd.merge_asof(oi.sort_values("time"), df[["time", "close"]], on="time", direction="nearest")
        oi["oi_usd"] = mm["amt"].to_numpy() * mm["close"].to_numpy()
    else:
        oi["oi_usd"] = oi["val"].astype(float)
    return df, oi[["time", "oi_usd"]].sort_values("time").reset_index(drop=True)
 
 
# ─────────────────────────────────────────────
# MOTOR: MAPA DE LIQUIDACIONES ESTIMADO
# ─────────────────────────────────────────────
def estimar_mapa(df, oi, rango=RANGO, paso=PASO):
    """
    df: velas 1 h (time, open, high, low, close). oi: (time, oi_usd).
    Devuelve centros de precio y USD estimados de liquidación de largos (debajo del precio) y de cortos (arriba).
    """
    m = pd.merge_asof(df.sort_values("time"), oi.sort_values("time"), on="time", direction="nearest",
                      tolerance=HOUR_MS).dropna(subset=["oi_usd"]).reset_index(drop=True)
    if len(m) < 48:
        raise ValueError(f"Datos insuficientes: {len(m)} horas con velas e interés abierto (se necesitan ≥48)")
    o, h, l, c = (m[k].astype(float).to_numpy() for k in ("open", "high", "low", "close"))
    oi_usd = m["oi_usd"].astype(float).to_numpy()
    nuevo = np.clip(np.diff(oi_usd, prepend=oi_usd[0]), 0, None)           # posiciones nuevas por hora (USD)
    if nuevo.sum() <= 0:
        raise ValueError("El interés abierto no aumentó en el período: no hay posiciones nuevas que estimar")
    tip = (h + l + c) / 3
    share_largo = np.where(c > o, 0.6, 0.4)
    n = len(m)
    # mínimo / máximo de lo que pasó DESPUÉS de cada hora (para saber si la posición ya fue liquidada)
    fmin = np.full(n, np.inf)
    fmax = np.full(n, -np.inf)
    for t in range(n - 2, -1, -1):
        fmin[t] = min(l[t + 1], fmin[t + 1])
        fmax[t] = max(h[t + 1], fmax[t + 1])
    px_l, w_l, px_s, w_s = [], [], [], []
    for lev, peso in zip(LEVS, PESOS):
        Lp = tip * (1 - 1 / lev + MMR)
        Sp = tip * (1 + 1 / lev - MMR)
        vivo_l = fmin > Lp
        vivo_s = fmax < Sp
        px_l.append(Lp[vivo_l]); w_l.append((nuevo * peso * share_largo)[vivo_l])
        px_s.append(Sp[vivo_s]); w_s.append((nuevo * peso * (1 - share_largo))[vivo_s])
    px_l, w_l, px_s, w_s = (np.concatenate(x) for x in (px_l, w_l, px_s, w_s))
    total = w_l.sum() + w_s.sum()
    if total <= 0:
        raise ValueError("Todas las posiciones estimadas ya habrían sido liquidadas")
    esc = oi_usd[-1] / total                                              # escala al OI actual
    price = float(c[-1])
    edges = price * (1 + np.arange(-rango, rango + paso / 2, paso))
    centros = (edges[:-1] + edges[1:]) / 2
    largos, _ = np.histogram(px_l, bins=edges, weights=w_l * esc)
    cortos, _ = np.histogram(px_s, bins=edges, weights=w_s * esc)
    debajo = centros < price
    return {"price": price, "oi_now": float(oi_usd[-1]), "centros": centros,
            "largos": np.where(debajo, largos, 0.0), "cortos": np.where(~debajo, cortos, 0.0), "horas": n}
 
 
def metricas(mapa, sig=0.5, cerca_pct=5.0):
    """Cúmulo significativo más cercano en cada lado (≥ 50 % del máximo de ese lado) y combustible a ≤ cerca_pct."""
    price, centros = mapa["price"], mapa["centros"]
    pct = (centros / price - 1) * 100
    k = np.array([1, 1, 1]) / 3
    out = {}
    for lado, arr, sentido in (("arr", mapa["cortos"], 1), ("abj", mapa["largos"], -1)):
        s = np.convolve(arr, k, mode="same")
        if s.max() <= 0:
            out[lado] = dict(dist=np.nan, usd=0.0, px=np.nan, mayor_dist=np.nan, mayor_usd=0.0, cerca=0.0)
            continue
        idx = np.flatnonzero(s >= sig * s.max())
        cercano = idx[np.argmin(np.abs(pct[idx]))]
        mayor = int(np.argmax(s))
        dentro = (pct * sentido > 0) & (np.abs(pct) <= cerca_pct)
        out[lado] = dict(dist=float(abs(pct[cercano])), usd=float(s[cercano]), px=float(centros[cercano]),
                         mayor_dist=float(abs(pct[mayor])), mayor_usd=float(s[mayor]), cerca=float(arr[dentro].sum()))
    return out
 
 
def etiqueta_lado(cerca_arr, cerca_abj, razon=1.5):
    if cerca_arr <= 0 and cerca_abj <= 0:
        return "sin datos"
    if cerca_arr > razon * cerca_abj:
        return "Más combustible ARRIBA (cortos)"
    if cerca_abj > razon * cerca_arr:
        return "Más combustible ABAJO (largos)"
    return "Equilibrado"
 
 
def figura_mapa(r):
    mp = r["_mapa"]
    x, price = mp["centros"], mp["price"]
    c_cortos = np.cumsum(mp["cortos"])                       # de cerca del precio hacia arriba
    c_largos = np.cumsum(mp["largos"][::-1])[::-1]           # de cerca del precio hacia abajo
    fig = go.Figure()
    fig.add_trace(go.Bar(x=x, y=mp["largos"] / 1e6, name="Liquidación de largos (estimada)", marker_color="#E53935"))
    fig.add_trace(go.Bar(x=x, y=mp["cortos"] / 1e6, name="Liquidación de cortos (estimada)", marker_color="#43A047"))
    fig.add_trace(go.Scatter(x=x[x < price], y=c_largos[x < price] / 1e6, mode="lines", name="Acumulado largos",
                             line=dict(color="#B71C1C", width=2), yaxis="y2"))
    fig.add_trace(go.Scatter(x=x[x >= price], y=c_cortos[x >= price] / 1e6, mode="lines", name="Acumulado cortos",
                             line=dict(color="#1B5E20", width=2), yaxis="y2"))
    fig.add_vline(x=price, line_dash="dash", line_color="#1565C0", annotation_text=f"Precio {fmt_px(price)}")
    fig.update_layout(height=470, barmode="overlay", margin=dict(l=0, r=0, t=30, b=0), plot_bgcolor="white",
                      yaxis=dict(title="USD estimados por nivel (M)"),
                      yaxis2=dict(title="Acumulado (M)", overlaying="y", side="right", showgrid=False),
                      xaxis=dict(title="Precio"), legend=dict(orientation="h", y=-0.2))
    return fig
 
 
def niveles_principales(mapa, n=6, min_rel=0.15):
    """Los n picos más grandes de liquidación de cada lado: lista de dicts (px, usd, lado)."""
    out = []
    for lado, arr in (("cortos", mapa["cortos"]), ("largos", mapa["largos"])):
        sm = np.convolve(arr, np.array([1, 1, 1]) / 3, mode="same")
        if sm.max() <= 0:
            continue
        pad = np.r_[0.0, sm, 0.0]
        picos = [i for i in range(len(sm)) if pad[i + 1] >= pad[i] and pad[i + 1] > pad[i + 2] and sm[i] >= min_rel * sm.max()]
        picos = sorted(picos, key=lambda i: -sm[i])[:n]
        out += [{"px": float(mapa["centros"][i]), "usd": float(sm[i]), "lado": lado} for i in picos]
    return out
 
 
def figura_velas_liq(sym, mapa, velas):
    """Velas de 1 H con líneas horizontales en los cúmulos de liquidación (verde = cortos arriba, rojo = largos abajo)."""
    price = mapa["price"]
    niv = niveles_principales(mapa)
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=velas["time"], open=velas["open"], high=velas["high"], low=velas["low"], close=velas["close"],
                                 name=sym, increasing_line_color="#2E7D32", decreasing_line_color="#C62828"))
    max_usd = max([v["usd"] for v in niv], default=1.0)
    for v in niv:
        color = "#2E7D32" if v["lado"] == "cortos" else "#C62828"
        pct = (v["px"] / price - 1) * 100
        fig.add_shape(type="line", xref="paper", x0=0, x1=1, yref="y", y0=v["px"], y1=v["px"],
                      line=dict(color=color, width=1 + 3 * v["usd"] / max_usd, dash="solid"), opacity=0.75)
        fig.add_annotation(xref="paper", x=1, xanchor="left", yref="y", y=v["px"], showarrow=False,
                           text=f"{fmt_px(v['px'])} · {v['usd'] / 1e6:.2f}M · {pct:+.1f}%", font=dict(color=color, size=10))
    fig.add_shape(type="line", xref="paper", x0=0, x1=1, yref="y", y0=price, y1=price, line=dict(color="#1565C0", width=1, dash="dash"))
    fig.add_annotation(xref="paper", x=0, xanchor="left", yref="y", y=price, showarrow=False, yshift=10,
                       text=f"Precio al escanear {fmt_px(price)}", font=dict(color="#1565C0", size=10))
    lo = min([velas["low"].min()] + [v["px"] for v in niv])
    hi = max([velas["high"].max()] + [v["px"] for v in niv])
    pad_y = (hi - lo) * 0.04
    fig.update_layout(height=560, margin=dict(l=0, r=170, t=30, b=0), plot_bgcolor="white", xaxis_rangeslider_visible=False,
                      yaxis=dict(range=[lo - pad_y, hi + pad_y], title="Precio"), showlegend=False,
                      title=f"{sym}: velas 1 H y niveles de liquidación estimados (verde = cortos, rojo = largos)")
    return fig
 
 
@st.cache_data(ttl=300, show_spinner=False)
def velas_liq(ex_id, sym_spot, limit=200):
    ex = get_liq_exchange(ex_id)
    if not ex.markets:
        ex.load_markets()
    raw = ex.fetch_ohlcv(sym_spot + ":USDT", timeframe="1h", limit=limit)
    d = pd.DataFrame(raw, columns=["time", "open", "high", "low", "close", "vol"])
    d["time"] = pd.to_datetime(d["time"], unit="ms")
    return d
 
 
LIQ_EXCHANGES = {"Bybit": "bybit", "OKX": "okx"}
 
 
@st.cache_resource
def get_liq_exchange(ex_id):
    return getattr(ccxt, ex_id)({"enableRateLimit": True})
 
 
def liq_para_simbolo(ex, ex_id, sym_spot):
    """sym_spot = 'BTC/USDT' (KuCoin). Busca el perpetuo 'BTC/USDT:USDT' y devuelve (fila_liq, mapa)."""
    perp = sym_spot + ":USDT"
    if not ex.markets:
        ex.load_markets()
    if perp not in ex.markets:
        raise ValueError("sin perpetuo USDT en este exchange")
    df, oi = fetch_velas_oi(ex, ex_id, perp)
    mapa = estimar_mapa(df, oi)
    mt = metricas(mapa)
    a, b = mt["arr"], mt["abj"]
    fila = {"Liq Lectura": etiqueta_lado(a["cerca"], b["cerca"]),
            "Liq ↑ %": round(a["dist"], 2) if np.isfinite(a["dist"]) else None,
            "Liq ↓ %": round(b["dist"], 2) if np.isfinite(b["dist"]) else None,
            "Cortos ≤5% (M USD)": round(a["cerca"] / 1e6, 3),
            "Largos ≤5% (M USD)": round(b["cerca"] / 1e6, 3)}
    return fila, mapa
 
 
LIQ_VACIO = {"Liq Lectura": "-", "Liq ↑ %": None, "Liq ↓ %": None,
             "Cortos ≤5% (M USD)": None, "Largos ≤5% (M USD)": None}
 
# ─────────────────────────────────────────────
# INTERFAZ Y CONECTIVIDAD KUCOIN
# ─────────────────────────────────────────────
@st.cache_resource
def get_exchange():
    return ccxt.kucoin({'enableRateLimit': True})
 
def fetch_symbols():
    try:
        ex = get_exchange()
        markets = ex.load_markets()
        symbols = [s for s in markets if '/USDT' in s and markets[s]['active']]
        filtered = [s for s in symbols if not any(x in s for x in ['3L', '3S', 'USDC', 'DAI', 'PAX', 'TUSD'])]
        # AGREGADO: excluir contratos de futuros/perpetuos. En la notación de ccxt
        # los pares spot son "BASE/QUOTE" (ej. "0G/USDT") y los perpetuos son
        # "BASE/QUOTE:SETTLE" (ej. "0G/USDT:USDT") — el ":" los distingue siempre.
        # Estos contratos suelen tener poco historial y son los que aparecían
        # como "SIN CÁLCULO" en la tabla.
        filtered = [s for s in filtered if ':' not in s]
        return sorted(filtered)
    except: return []
 
st.title("🛡️ SLY | CRIPTO SIGNAL TRACKER + LIQUIDACIONES")
 
with st.sidebar:
    st.header("⚙️ Configuración")
    
    st.subheader("1. Parámetros de Tiempo")
    selected_tf_label = st.selectbox("Seleccionar Temporalidad:", list(TF_OPTIONS.keys()), index=2) 
    selected_tf_code = TF_OPTIONS[selected_tf_label]
    
    if st.button("📡 Sincronizar Mercado KuCoin"):
        st.session_state["crypto_list"] = fetch_symbols()
        st.rerun()
 
    if "crypto_list" in st.session_state:
        st.subheader("2. Ejecución")
        lote_size = st.number_input("Tamaño de Lote:", 10, 100, 50)
        total_lotes = (len(st.session_state["crypto_list"]) // lote_size) + 1
        batch_idx = st.selectbox(f"Seleccionar Lote:", range(total_lotes), format_func=lambda x: f"Lote {x+1}")
        bear_longs = st.checkbox("Habilitar Bear-Longs", value=True)
        incluir_liq = st.checkbox("Incluir liquidaciones estimadas (1 H)", value=True,
                                  help="Suma 2 pedidos por cripto a Bybit/OKX. Si lo apagás, el escaneo es más rápido.")
        liq_ex_lbl = st.selectbox("Exchange de liquidaciones:", list(LIQ_EXCHANGES.keys()), index=1)
        liq_ex_id = LIQ_EXCHANGES[liq_ex_lbl]
        
        if st.button("🚀 ACTUALIZAR Y ACUMULAR", type="primary"):
            ex = get_exchange()
            subset = st.session_state["crypto_list"][batch_idx*lote_size : (batch_idx+1)*lote_size]
            prog = st.progress(0)
            
            for i, sym in enumerate(subset):
                try:
                    prog.progress((i+1)/len(subset), text=f"Auditando {selected_tf_label}: {sym}")
 
                    # Temporalidad principal
                    raw_data = ex.fetch_ohlcv(sym, timeframe=selected_tf_code, limit=1000)
                    df = pd.DataFrame(raw_data, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
                    df['time'] = pd.to_datetime(df['time'], unit='ms')
                    df.set_index('time', inplace=True)
 
                    data, motivo = get_sly_indicators(df)
 
                    if data.empty:
                        # AGREGADO: aunque no se pudo calcular, se deja la fila
                        # con el motivo explicando por qué (no desaparece en silencio).
                        st.session_state["master_results_crypto"][sym] = {
                            "Activo": sym.replace("/USDT", ""),
                            "Temporalidad": selected_tf_label,
                            "Sector": get_crypto_sector(sym),
                            "MACD Mensual": "-",
                            "Última Señal": "-",
                            "Estado": "SIN CÁLCULO ⚪",
                            "PnL Real": "-",
                            "Zona RSI": "-",
                            "Veredicto": "-",
                            "RSI PRO": "-",
                            "Vol Z-Score": "-",
                            "Alpha Strike": "-",
                            "Agotamiento": "-",
                            "Precio": "-",
                            "RSI": "-",
                            "Régimen": "-",
                            "Motivo": motivo,   # <-- NUEVO: por qué no se calculó
                        }
                        continue
 
                    # Análisis MACD Mensual
                    monthly_force = get_monthly_macd_force(ex, sym)
                    
                    sig_date, sig_px, vigente, verd = find_last_signal(data, bear_longs)
                    pnl_val = f"{((data['Close'].iloc[-1] - sig_px) / sig_px * 100):.2f}%" if (vigente and sig_px) else "-"
                    last_rsi = data['rsi_smooth'].iloc[-1]
                    rsi_zone = "SOBRE 50 🟢" if last_rsi > 50 else "BAJO 50 🔴"
 
                    # --- AGREGADO: lectura de columnas del RSI PRO en la última vela ---
                    rsi_pro_state = data['rsi_state'].iloc[-1]
                    vol_z_last = data['vol_z'].iloc[-1]
                    vol_z_txt = f"{vol_z_last:.2f}" if pd.notna(vol_z_last) else "-"
                    alpha_strike_txt = "SÍ 🚀" if bool(data['alpha_strike'].iloc[-1]) else "-"
                    exhaustion_txt = "SÍ ⚠️" if bool(data['exhaustion'].iloc[-1]) else "-"
                    
                    st.session_state["master_results_crypto"][sym] = {
                        "Activo": sym.replace("/USDT", ""), 
                        "Temporalidad": selected_tf_label,
                        "Sector": get_crypto_sector(sym),
                        "MACD Mensual": monthly_force, # AGREGADO
                        "Última Señal": sig_date.strftime('%d/%m %H:%M') if sig_date else "-",
                        "Estado": "VIGENTE 🟢" if vigente else "CERRADA 🔴",
                        "PnL Real": pnl_val,
                        "Zona RSI": rsi_zone,
                        "Veredicto": verd,
                        "RSI PRO": rsi_pro_state,          # <-- NUEVO: se pone en verde cuando el RSI sube
                        "Vol Z-Score": vol_z_txt,           # <-- NUEVO: filtro de volumen institucional
                        "Alpha Strike": alpha_strike_txt,   # <-- NUEVO: entrada institucional
                        "Agotamiento": exhaustion_txt,      # <-- NUEVO: alerta de sobre-extensión
                        "Precio": f"{data['Close'].iloc[-1]:.4f}",
                        "RSI": round(last_rsi, 1),
                        "Régimen": "ALCISTA" if data['ema52'].iloc[-1] > data['ema260'].iloc[-1] else "BAJISTA",
                        "Motivo": "OK",  # <-- NUEVO: para uniformar la columna
                    }
                    time.sleep(0.05)
                except Exception as e_sym:
                    # AGREGADO: si falla algo antes de llegar a get_sly_indicators
                    # (ej. error de conexión al pedir las velas), también se deja
                    # constancia del símbolo y el motivo real en vez de perderlo.
                    st.session_state["master_results_crypto"][sym] = {
                        "Activo": sym.replace("/USDT", ""),
                        "Temporalidad": selected_tf_label,
                        "Sector": get_crypto_sector(sym),
                        "MACD Mensual": "-", "Última Señal": "-", "Estado": "SIN CÁLCULO ⚪",
                        "PnL Real": "-", "Zona RSI": "-", "Veredicto": "-", "RSI PRO": "-",
                        "Vol Z-Score": "-", "Alpha Strike": "-", "Agotamiento": "-",
                        "Precio": "-", "RSI": "-", "Régimen": "-",
                        "Motivo": f"{type(e_sym).__name__}: {e_sym}",
                    }
                    continue
            if incluir_liq:
                prog2 = st.progress(0)
                lex = get_liq_exchange(liq_ex_id)
                for i, sym in enumerate(subset):
                    prog2.progress((i + 1) / len(subset), text=f"Liquidaciones {liq_ex_lbl}: {sym}")
                    fila = st.session_state["master_results_crypto"].get(sym)
                    if fila is None:
                        continue
                    try:
                        liq_fila, mapa = liq_para_simbolo(lex, liq_ex_id, sym)
                        fila.update(liq_fila)
                        st.session_state["liq_mapas"][sym] = mapa
                        st.session_state["liq_errores"].pop(sym, None)
                    except Exception as e_liq:
                        fila.update(LIQ_VACIO)
                        fila["Liq Lectura"] = "N/D"
                        st.session_state["liq_errores"][sym] = f"{sym}: {type(e_liq).__name__}: {str(e_liq)[:200]}"
                    time.sleep(0.05)
                prog2.empty()
            st.rerun()
 
    if st.button("🗑️ Limpiar Memoria"):
        st.session_state["master_results_crypto"] = {}
        st.session_state["liq_mapas"], st.session_state["liq_errores"] = {}, {}
        st.rerun()
 
# ─────────────────────────────────────────────
# RESUMEN SECTORIAL
# ─────────────────────────────────────────────
if st.session_state["master_results_crypto"]:
    df_full = pd.DataFrame(st.session_state["master_results_crypto"].values())
    
    # Reordenar para que MACD Mensual esté al principio (+ columnas nuevas del RSI PRO)
    cols_order = ["Activo", "Sector", "MACD Mensual", "Estado", "Veredicto", "PnL Real", "Última Señal",
                  "Temporalidad", "Zona RSI", "RSI PRO", "Vol Z-Score", "Alpha Strike", "Agotamiento",
                  "RSI", "Precio", "Régimen",
                  "Confluencia", "Liq Lectura", "Liq ↑ %", "Liq ↓ %", "Cortos ≤5% (M USD)", "Largos ≤5% (M USD)", "Motivo"]
    if "Liq Lectura" in df_full.columns:
        _lec = df_full["Liq Lectura"].astype(str)
        _vig = df_full["Estado"] == "VIGENTE 🟢"
        df_full["Confluencia"] = np.select(
            [_vig & _lec.str.contains("ARRIBA"), _vig & _lec.str.contains("ABAJO")],
            ["LONG + imán arriba ✅", "LONG pero combustible abajo ⚠️"], default="-")
    cols_order = [c for c in cols_order if c in df_full.columns]
    df_full = df_full[cols_order]
 
    df_vigentes = df_full[df_full["Estado"] == "VIGENTE 🟢"]
 
    st.subheader(f"📊 RESUMEN DE EXPOSICIÓN (VIGENTES)")
    if not df_vigentes.empty:
        summary = df_vigentes.groupby("Sector")["Activo"].apply(list).reset_index()
        cols = st.columns(3)
        for idx, row in summary.iterrows():
            with cols[idx % 3]:
                st.markdown(f"""
                <div class="sector-box">
                    <div class="sector-title">{row['Sector']}: {len(row['Activo'])}</div>
                    <div style='font-size: 0.85em;'>{', '.join(row['Activo'])}</div>
                </div>
                """, unsafe_allow_html=True)
    else: st.warning("Sin posiciones abiertas en la temporalidad analizada.")
 
    st.subheader(f"📋 Matriz de Señales (Filtro Actual: {selected_tf_label})")
    df_res = df_full.sort_values(by=["Estado", "Activo"], ascending=[False, True])
    
    def color_cells(val):
        str_v = str(val)
        if "ARRIBA" in str_v or "imán arriba" in str_v:
            return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
        if "ABAJO" in str_v or "combustible abajo" in str_v:
            return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
        # Estados fuertes / positivos -> verde intenso (AGREGADO)
        if "ALCISTA FUERTE" in str_v or "SÍ 🚀" in str_v:
            return 'background-color: #A5D6A7; color: #1B5E20; font-weight: bold;'
        if "VIGENTE" in str_v or "MANTENER" in str_v or "ALCISTA" in str_v or "SOBRE 50" in str_v or "GANANDO" in str_v: 
            return 'background-color: #C8E6C9; color: #1B5E20; font-weight: bold;'
        # Estados negativos fuertes -> rojo intenso (AGREGADO)
        if "BAJISTA FUERTE" in str_v:
            return 'background-color: #EF9A9A; color: #B71C1C; font-weight: bold;'
        if "CERRADA" in str_v or "CERRAR" in str_v or "BAJISTA" in str_v or "BAJO 50" in str_v or "PERDIENDO" in str_v: 
            return 'background-color: #FFCDD2; color: #B71C1C; font-weight: bold;'
        # Alerta de agotamiento (AGREGADO)
        if "PIERDE FUERZA" in str_v or "SÍ ⚠️" in str_v: 
            return 'background-color: #FFF9C4; color: #827717; font-weight: bold;'
        return ''
 
    st.dataframe(df_res.style.map(color_cells), use_container_width=True, height=600)
    st.caption("Liquidaciones: estimación propia con interés abierto de 1 H (Bybit/OKX); no es el dato de Coinglass. "
               "'Liq ↑ %' / 'Liq ↓ %' = distancia al cúmulo significativo más cercano arriba (cortos) / abajo (largos). "
               "'Confluencia' solo marca las señales VIGENTES; no es una recomendación de entrada.")
    if st.session_state["liq_mapas"]:
        _ops = [s for s in df_res["Activo"].tolist() if (s + "/USDT") in st.session_state["liq_mapas"]]
        if _ops:
            pick = st.selectbox("🧨 Ver mapa de liquidaciones de:", _ops)
            st.plotly_chart(figura_mapa({"_mapa": st.session_state["liq_mapas"][pick + "/USDT"]}), use_container_width=True)
            try:
                _ex_vel = globals().get("liq_ex_id", "okx")
                _velas = velas_liq(_ex_vel, pick + "/USDT")
                st.plotly_chart(figura_velas_liq(pick, st.session_state["liq_mapas"][pick + "/USDT"], _velas), use_container_width=True)
            except Exception as e_vel:
                st.warning(f"No se pudo dibujar el gráfico de velas: {type(e_vel).__name__}: {str(e_vel)[:200]}")
    if st.session_state["liq_errores"]:
        with st.expander(f"⚠️ {len(st.session_state['liq_errores'])} cripto sin liquidaciones"):
            st.write("\n\n".join(st.session_state["liq_errores"].values()))
else:
    st.info("👈 Seleccione temporalidad, sincronice mercado y analice lotes.")
