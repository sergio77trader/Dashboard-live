"""
SLY | TRADER MULTI-TF  (KuCoin spot, por lotes)

Requisitos:  pip install streamlit ccxt pandas numpy pandas_ta
Ejecutar:    streamlit run sly_trader_multitf.py

Qué muestra por cada cripto:
  Activo · Sector · Estado señal (4H) · Precio
  Régimen 4H · MACD 4H · RSI PRO 4H
  Última señal 4H / 1H (o 2H) / 30M  y el PnL de cada una

La dirección la decide el régimen de 4H (EMA52 vs EMA260): alcista -> señales LONG, bajista -> señales SHORT,
y esa misma dirección se usa en 4H, 1H/2H y 30M. La lógica es la del tracker SLY (DEMA MACD 12/26/9, RSI suavizado
con DEMA, Heikin Ashi), con su versión espejo para SHORT.
PnL (en la dirección de la operación; en SHORT gana si el precio baja): si la señal sigue vigente = ganancia/pérdida abierta contra el precio actual;
si ya se cerró = resultado entre la entrada y la salida de esa señal.
Por defecto solo usa velas CERRADAS, para que una señal no aparezca y desaparezca mientras la vela se forma.
Las horas se muestran en horario de Argentina. No es una recomendación de inversión.
"""
import time
from datetime import datetime

import ccxt
import numpy as np
import pandas as pd
import streamlit as st

try:
    import pandas_ta as ta

    def _rsi(s, n):
        r = ta.rsi(s, length=n)
        if r is None:
            raise ValueError("RSI sin datos suficientes")
        return r

    def _ema(s, n):
        r = ta.ema(s, length=n)
        if r is None:
            return pd.Series(np.nan, index=s.index)
        return r
except Exception:  # sin pandas_ta: implementación propia equivalente
    def _rsi(s, n):
        d = s.diff()
        up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
        dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
        return 100 - 100 / (1 + up / dn.replace(0, np.nan))

    def _ema(s, n):
        return s.ewm(span=n, adjust=False, min_periods=n).mean()

st.set_page_config(layout="wide", page_title="SLY | TRADER MULTI-TF")
st.markdown("""
<style>
    .stApp { background-color: #FFFFFF; color: #1C1E21; }
    .stDataFrame { font-size: 11px; font-family: 'Roboto Mono', monospace; }
    h1 { color: #E65100; font-weight: 800; border-bottom: 3px solid #E65100; }
    .stProgress > div > div > div > div { background-color: #E65100; }
</style>
""", unsafe_allow_html=True)

TZ = "America/Argentina/Buenos_Aires"
TF_MAIN, TF_LOW = "4h", "30m"
TF_MS = {"30m": 1_800_000, "1h": 3_600_000, "2h": 7_200_000, "4h": 14_400_000}
RSI_BB_MULT = 2.0
VOL_Z_THRESHOLD = 1.5

CRYPTO_SECTORS = {
    "LEADER": ["BTC/USDT", "ETH/USDT"],
    "LAYER 1": ["SOL/USDT", "ADA/USDT", "DOT/USDT", "AVAX/USDT", "MATIC/USDT", "NEAR/USDT", "FTM/USDT", "ALGO/USDT"],
    "DEFI/L2": ["ARB/USDT", "OP/USDT", "LINK/USDT", "UNI/USDT", "AAVE/USDT", "LDO/USDT"],
    "AI/DEPIN": ["RNDR/USDT", "FET/USDT", "FIL/USDT", "THETA/USDT"],
    "MEMES": ["DOGE/USDT", "SHIB/USDT", "PEPE/USDT", "BONK/USDT", "FLOKI/USDT"],
    "EXCHANGE": ["BNB/USDT", "KCS/USDT", "OKB/USDT"],
}


def get_crypto_sector(ticker):
    for sector, members in CRYPTO_SECTORS.items():
        if ticker.upper() in members:
            return sector
    return "ALTCOINS / OTROS"


# ─────────────────────────────────────────────
# MOTOR SLY
# ─────────────────────────────────────────────
def dema(s, length):
    e1 = s.ewm(span=length, adjust=False).mean()
    e2 = e1.ewm(span=length, adjust=False).mean()
    return 2 * e1 - e2


def get_sly_indicators(df):
    """(dataframe calculado, motivo). Si no hay datos suficientes: (vacío, explicación)."""
    try:
        df = df.copy()
        df.columns = [c.capitalize() for c in df.columns]
        df = df.dropna(subset=["Close"])
        total = len(df)
        df["macd_line"] = dema(df["Close"], 12) - dema(df["Close"], 26)
        df["signal_line"] = df["macd_line"].ewm(span=9, adjust=False).mean()
        df["hist"] = df["macd_line"] - df["signal_line"]
        df["rsi_smooth"] = dema(_rsi(df["Close"], 14).fillna(50), 5)
        df["rsi_basis"] = df["rsi_smooth"].rolling(20).mean()
        df["rsi_std"] = df["rsi_smooth"].rolling(20).std()
        df["rsi_upper"] = df["rsi_basis"] + RSI_BB_MULT * df["rsi_std"]
        df["vol_avg"] = df["Vol"].rolling(20).mean()
        df["vol_std"] = df["Vol"].rolling(20).std()
        df["vol_z"] = (df["Vol"] - df["vol_avg"]) / df["vol_std"]
        rn, rp = df["rsi_smooth"], df["rsi_smooth"].shift(1)
        conds = [(rn > 50) & (rn > rp), (rn > 50) & (rn <= rp), (rn < 50) & (rn < rp), (rn < 50) & (rn >= rp)]
        df["rsi_state"] = np.select(conds, ["ALCISTA FUERTE 🟢🟢", "ALCISTA DÉBIL 🟢", "BAJISTA FUERTE 🔴🔴", "BAJISTA DÉBIL 🔴"],
                                    default="NEUTRAL ⚪")
        ha_c = (df["Open"] + df["High"] + df["Low"] + df["Close"]) / 4
        ha_o = np.zeros(len(df))
        ha_o[0] = (df["Open"].iloc[0] + df["Close"].iloc[0]) / 2
        for i in range(1, len(df)):
            ha_o[i] = (ha_o[i - 1] + ha_c.iloc[i - 1]) / 2
        df["ha_color"] = np.where(ha_c > ha_o, "Verde", "Rojo")
        df["ema52"] = _ema(df["Close"], 52)
        df["ema260"] = _ema(df["Close"], 260)
        res = df.dropna(subset=["ema260"])
        if res.empty:
            return pd.DataFrame(), f"Historial insuficiente: {total} velas (se necesitan ≥260 para EMA260)"
        return res, "OK"
    except Exception as e:
        return pd.DataFrame(), f"Error de cálculo: {type(e).__name__}: {e}"


def find_last_signal(df, direction):
    """
    Lógica SLY para LONG o SHORT (espejo una de otra).
      LONG : entrada = Heikin Ashi pasa de rojo a verde + MACD acelera + RSI sube estando bajo 50.
             salida  = HA rojo + MACD cae + RSI cae.
      SHORT: entrada = Heikin Ashi pasa de verde a rojo + MACD desacelera + RSI baja estando sobre 50.
             salida  = HA verde + MACD sube + RSI sube.
    Guarda también la salida para calcular el PnL de señales cerradas.
    """
    out = {"dir": direction, "entry_date": None, "entry_px": None, "active": False,
           "exit_date": None, "exit_px": None, "verdict": "-"}
    if df.empty or len(df) < 2:
        return out
    short = direction == "SHORT"
    for i in range(1, len(df)):
        hc, hp_ = df["ha_color"].iloc[i], df["ha_color"].iloc[i - 1]
        h, hp = df["hist"].iloc[i], df["hist"].iloc[i - 1]
        r, rp = df["rsi_smooth"].iloc[i], df["rsi_smooth"].iloc[i - 1]
        if short:
            entrada = hc == "Rojo" and hp_ == "Verde" and h < hp and r < rp and r > 50
            salida = hc == "Verde" and h > hp and r > rp
        else:
            entrada = hc == "Verde" and hp_ == "Rojo" and h > hp and r > rp and r < 50
            salida = hc == "Rojo" and h < hp and r < rp
        if not out["active"] and entrada:
            out.update(active=True, entry_date=df.index[i], entry_px=float(df["Close"].iloc[i]), exit_date=None, exit_px=None)
        elif out["active"] and salida:
            out.update(active=False, exit_date=df.index[i], exit_px=float(df["Close"].iloc[i]))
    if out["active"]:
        c, p = df["hist"].iloc[-1], df["hist"].iloc[-2]
        if short:
            out["verdict"] = "cerrar" if (p < 0 and c >= 0) else ("mantener" if c < p else "pierde fuerza")
        else:
            out["verdict"] = "cerrar" if (p > 0 and c <= 0) else ("mantener" if c > p else "pierde fuerza")
    return out


# ─────────────────────────────────────────────
# DATOS Y TEXTOS
# ─────────────────────────────────────────────
def fetch_tf(ex, sym, tf, limit=1000):
    raw = ex.fetch_ohlcv(sym, timeframe=tf, limit=limit)
    if not raw:
        raise ValueError(f"sin velas {tf}")
    d = pd.DataFrame(raw, columns=["time", "open", "high", "low", "close", "vol"])
    return d.drop_duplicates("time").sort_values("time").reset_index(drop=True)


def preparar(df_raw, tf, solo_cerradas):
    """Devuelve (velas listas para calcular con hora argentina, último precio incluyendo la vela abierta)."""
    px_now = float(df_raw["close"].iloc[-1])
    d = df_raw
    if solo_cerradas and len(d) > 1 and int(d["time"].iloc[-1]) + TF_MS[tf] > int(time.time() * 1000):
        d = d.iloc[:-1]
    d = d.copy()
    d["time"] = pd.to_datetime(d["time"], unit="ms", utc=True).dt.tz_convert(TZ)
    return d.set_index("time"), px_now


def macd_label(data):
    h, hp = data["hist"].iloc[-1], data["hist"].iloc[-2]
    if h > 0:
        return "POSITIVO · GANA FUERZA ▲" if h > hp else "POSITIVO · PIERDE FUERZA ▼"
    return "NEGATIVO · SE RECUPERA ▲" if h > hp else "NEGATIVO · PIERDE FUERZA ▼"


def senal_txt(sig, tf):
    """Hora = CIERRE de la vela que dio la señal (cuando realmente se confirma). Si esa vela sigue abierta, lo aclara."""
    if sig["entry_date"] is None:
        return "-"
    cierre = sig["entry_date"] + pd.Timedelta(milliseconds=TF_MS[tf])
    if cierre > pd.Timestamp.now(tz=TZ):
        t = f"{sig['entry_date'].strftime('%d/%m %H:%M')} (en formación)"
    else:
        t = cierre.strftime("%d/%m %H:%M")
    return f"{t} · {sig['dir']} {'VIGENTE 🟢' if sig['active'] else 'CERRADA 🔴'}"


def pnl_txt(sig, px_now):
    """PnL en la dirección de la operación: en SHORT, ganar es que el precio baje."""
    if sig["entry_px"] is None:
        return "-"
    k = -1 if sig["dir"] == "SHORT" else 1
    if sig["active"]:
        return f"{k * (px_now / sig['entry_px'] - 1) * 100:+.2f}% (abierta)"
    if sig["exit_px"] is not None:
        return f"{k * (sig['exit_px'] / sig['entry_px'] - 1) * 100:+.2f}% (cerrada)"
    return "-"


def fila_vacia(sym, motivo):
    return {"Activo": sym.replace("/USDT", ""), "Sector": get_crypto_sector(sym), "Estado señal": "SIN CÁLCULO ⚪",
            "Precio": "-", "Dirección": "-", "Régimen 4H": "-", "MACD 4H": "-", "RSI PRO 4H": "-", "Motivo": motivo}


def procesar_simbolo(ex, sym, tf_mid, solo_cerradas):
    lbl_mid = tf_mid.upper()
    try:
        raw4 = fetch_tf(ex, sym, TF_MAIN)
    except Exception as e:
        return fila_vacia(sym, f"4H: {type(e).__name__}: {str(e)[:120]}")
    d4, px4 = preparar(raw4, TF_MAIN, solo_cerradas)
    data4, motivo = get_sly_indicators(d4)
    if data4.empty:
        return fila_vacia(sym, f"4H: {motivo}")
    # La dirección la decide el régimen de 4H: alcista -> LONG, bajista -> SHORT (vale para 4H, 1H/2H y 30M)
    alcista = bool(data4["ema52"].iloc[-1] > data4["ema260"].iloc[-1])
    direccion = "LONG" if alcista else "SHORT"
    sig4 = find_last_signal(data4, direccion)
    motivos = []
    row = {"Activo": sym.replace("/USDT", ""), "Sector": get_crypto_sector(sym)}
    extra = {}
    for tf, lbl in ((tf_mid, lbl_mid), (TF_LOW, "30M")):
        try:
            raw = fetch_tf(ex, sym, tf)
            d, px = preparar(raw, tf, solo_cerradas)
            data, mot = get_sly_indicators(d)
            if data.empty:
                raise ValueError(mot)
            extra[lbl] = (find_last_signal(data, direccion), px)
        except Exception as e:
            extra[lbl] = None
            motivos.append(f"{lbl}: {str(e)[:100]}")
    # precio más fresco disponible: 30M, si no 1H/2H, si no 4H
    px_now = (extra.get("30M") or extra.get(lbl_mid) or (None, px4))[1]
    est = f"{direccion} VIGENTE 🟢 · {sig4['verdict']}" if sig4["active"] else f"{direccion} CERRADA 🔴"
    if sig4["entry_date"] is None:
        est = "SIN SEÑAL ⚪"
    row.update({
        "Estado señal": est,
        "Precio": f"{px_now:.6g}",
        "Dirección": "LONG ▲" if alcista else "SHORT ▼",
        "Régimen 4H": "ALCISTA" if alcista else "BAJISTA",
        "MACD 4H": macd_label(data4),
        "RSI PRO 4H": f"{data4['rsi_state'].iloc[-1]} ({data4['rsi_smooth'].iloc[-1]:.0f})",
        "Última señal 4H": senal_txt(sig4, TF_MAIN),
        f"Última señal {lbl_mid}": senal_txt(extra[lbl_mid][0], tf_mid) if extra.get(lbl_mid) else "-",
        "Última señal 30M": senal_txt(extra["30M"][0], TF_LOW) if extra.get("30M") else "-",
        "PnL 4H": pnl_txt(sig4, px_now),
        f"PnL {lbl_mid}": pnl_txt(extra[lbl_mid][0], px_now) if extra.get(lbl_mid) else "-",
        "PnL 30M": pnl_txt(extra["30M"][0], px_now) if extra.get("30M") else "-",
        "Motivo": " | ".join(motivos) if motivos else "OK",
    })
    return row


def estilo_celda(val):
    import re
    s = str(val)
    if s in ("-", ""):
        return ""
    verde = "background-color: #C8E6C9; color: #1B5E20; font-weight: bold;"
    verde2 = "background-color: #A5D6A7; color: #1B5E20; font-weight: bold;"
    rojo = "background-color: #FFCDD2; color: #B71C1C; font-weight: bold;"
    rojo2 = "background-color: #EF9A9A; color: #B71C1C; font-weight: bold;"
    amar = "background-color: #FFF9C4; color: #827717; font-weight: bold;"
    if s == "LONG ▲":
        return verde2
    if s == "SHORT ▼":
        return rojo2
    if re.match(r"^[+-]\d", s):
        return verde if s.startswith("+") else rojo
    if "VIGENTE" in s and ("pierde" in s or "cerrar" in s):
        return amar
    if "VIGENTE" in s or "POSITIVO · GANA" in s:
        return verde
    if "ALCISTA FUERTE" in s:
        return verde2
    if "BAJISTA FUERTE" in s:
        return rojo2
    if "POSITIVO · PIERDE" in s or "NEGATIVO · SE RECUPERA" in s:
        return amar
    if s.startswith("ALCISTA"):
        return verde
    if "CERRADA" in s or s.startswith("BAJISTA") or "NEGATIVO" in s:
        return rojo
    return ""


# ═════════════════════════════════════════════
# INTERFAZ
# ═════════════════════════════════════════════
@st.cache_resource
def get_exchange():
    return ccxt.kucoin({"enableRateLimit": True})


def fetch_symbols():
    try:
        markets = get_exchange().load_markets()
        out = [s for s, m in markets.items() if s.endswith("/USDT") and ":" not in s and m.get("active", True)
               and not any(x in s for x in ["3L", "3S", "USDC", "DAI", "PAX", "TUSD"])]
        return sorted(out)
    except Exception as e:
        st.session_state["sync_error"] = f"{type(e).__name__}: {str(e)[:300]}"
        return []


if "tr_results" not in st.session_state:
    st.session_state["tr_results"] = {}
if "tr_updated" not in st.session_state:
    st.session_state["tr_updated"] = None

st.title("🎯 SLY | TRADER MULTI-TF")

with st.sidebar:
    st.header("⚙️ Configuración")
    mid_lbl = st.selectbox("Temporalidad intermedia:", ["1H", "2H"], index=0)
    TF_MID = mid_lbl.lower()
    st.caption("Dirección automática: régimen 4H alcista → señales LONG · bajista → señales SHORT.")
    solo_cerradas = st.checkbox("Solo velas cerradas", value=True,
                                help="Evita señales que aparecen y desaparecen mientras la vela se forma. "
                                     "Desmarcá para ver señales en tiempo real (pueden cambiar).")
    if st.button("📡 Sincronizar Mercado KuCoin"):
        st.session_state.pop("sync_error", None)
        lst = fetch_symbols()
        if lst:
            st.session_state["crypto_list"] = lst
            st.rerun()
    if st.session_state.get("sync_error"):
        st.error(f"No se pudo leer el mercado: {st.session_state['sync_error']}")

    symbols = st.session_state.get("crypto_list")
    run_symbols = None
    if symbols:
        st.subheader("Ejecución")
        lote_size = int(st.number_input("Tamaño de lote:", 10, 100, 30))
        total_lotes = (len(symbols) - 1) // lote_size + 1
        batch_idx = st.selectbox("Lote:", range(total_lotes), format_func=lambda x: f"Lote {x + 1}")
        st.caption("Cada cripto hace 3 pedidos (4H, " + mid_lbl + " y 30M).")
        if st.button("🚀 ACTUALIZAR LOTE", type="primary", use_container_width=True):
            run_symbols = symbols[batch_idx * lote_size:(batch_idx + 1) * lote_size]
        if st.session_state["tr_results"] and st.button("🔄 Refrescar todas las cargadas", use_container_width=True):
            run_symbols = list(st.session_state["tr_results"].keys())
    if st.button("🗑️ Limpiar memoria"):
        st.session_state["tr_results"] = {}
        st.rerun()

    if run_symbols:
        ex = get_exchange()
        prog = st.progress(0)
        for i, sym in enumerate(run_symbols):
            prog.progress((i + 1) / len(run_symbols), text=f"Analizando {sym}")
            try:
                st.session_state["tr_results"][sym] = procesar_simbolo(ex, sym, TF_MID, solo_cerradas)
            except Exception as e:
                st.session_state["tr_results"][sym] = fila_vacia(sym, f"{type(e).__name__}: {str(e)[:150]}")
            time.sleep(0.05)
        prog.empty()
        st.session_state["tr_updated"] = datetime.now().strftime("%d/%m %H:%M:%S")
        st.rerun()

res = st.session_state["tr_results"]
if not res:
    st.info("👈 Sincronizá el mercado y actualizá un lote para empezar.")
    st.stop()

df = pd.DataFrame(list(res.values()))
cols = ["Activo", "Sector", "Estado señal", "Precio", "Dirección", "Régimen 4H", "MACD 4H", "RSI PRO 4H",
        "Última señal 4H", f"Última señal {mid_lbl}", "Última señal 30M",
        "PnL 4H", f"PnL {mid_lbl}", "PnL 30M", "Motivo"]
for c in cols:
    if c not in df.columns:
        df[c] = "-"
df = df[cols].fillna("-")

if st.session_state["tr_updated"]:
    st.caption(f"Última actualización: {st.session_state['tr_updated']} (hora local) · {len(df)} criptos cargadas")

f1, f2, f3 = st.columns([1, 1, 2])
solo_vig = f1.checkbox("Solo vigentes en 4H", value=False)
solo_alin = f2.checkbox(f"Vigentes en 4H + {mid_lbl} + 30M", value=False)
sect = f3.multiselect("Sector", sorted(df["Sector"].unique()))

v = df
if solo_vig:
    v = v[v["Estado señal"].str.contains("VIGENTE")]
if solo_alin:
    v = v[v["Estado señal"].str.contains("VIGENTE") & v[f"Última señal {mid_lbl}"].str.contains("VIGENTE")
          & v["Última señal 30M"].str.contains("VIGENTE")]
if sect:
    v = v[v["Sector"].isin(sect)]

orden = {"VIGENTE": 0, "CERRADA": 1, "SIN SEÑAL": 2, "SIN CÁLCULO": 3}
v = v.assign(_o=v["Estado señal"].map(lambda s: next((o for k, o in orden.items() if k in s), 4)))
v = v.sort_values(["_o", "Activo"]).drop(columns="_o")

c1, c2, c3 = st.columns(3)
c1.metric("Vigentes en 4H", int(df["Estado señal"].str.contains("VIGENTE").sum()))
c2.metric(f"Vigentes en {mid_lbl}", int(df[f"Última señal {mid_lbl}"].str.contains("VIGENTE").sum()))
c3.metric("Vigentes en 30M", int(df["Última señal 30M"].str.contains("VIGENTE").sum()))

styler = v.style
styler = styler.map(estilo_celda) if hasattr(styler, "map") else styler.applymap(estilo_celda)
st.dataframe(styler, use_container_width=True, height=620, hide_index=True)
st.caption("La hora de cada señal es el cierre de la vela que la generó. Señal 'VIGENTE' = entrada abierta y todavía sin salida. PnL (abierta) contra el precio actual; PnL (cerrada) entre entrada y salida. "
           "Estadística y lectura técnica, no recomendación.")
