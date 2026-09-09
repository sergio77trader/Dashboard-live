```python
import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────

st.set_page_config(
    layout="wide",
    page_title="SLY | CRIPTO MULTI-TF MONITOR + RSI PRO"
)

st.markdown("""
<style>
    .stApp {
        background-color: #FFFFFF;
        color: #1C1E21;
    }

    .stDataFrame {
        font-size: 11px;
        font-family: 'Roboto Mono', monospace;
    }

    h1 {
        color: #E65100;
        font-weight: 800;
        border-bottom: 3px solid #E65100;
    }

    .stProgress > div > div > div > div {
        background-color: #E65100;
    }

    .sector-box {
        background-color: #FFF3E0;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #E64A19;
        margin-bottom: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }

    .sector-title {
        font-weight: bold;
        color: #BF360C;
        font-size: 1.1em;
    }

    .rsi-green-box {
        background-color: #C8E6C9;
        color: #1B5E20;
        padding: 14px;
        border-radius: 8px;
        border-left: 6px solid #2E7D32;
        margin-bottom: 10px;
        font-weight: bold;
    }

    .alpha-box {
        background-color: #FFF3CD;
        color: #7A4F00;
        padding: 14px;
        border-radius: 8px;
        border-left: 6px solid #FF9800;
        margin-bottom: 10px;
        font-weight: bold;
    }

    .exhaustion-box {
        background-color: #FFCDD2;
        color: #B71C1C;
        padding: 14px;
        border-radius: 8px;
        border-left: 6px solid #C62828;
        margin-bottom: 10px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# MEMORIA
# ─────────────────────────────────────────────

if "master_results_crypto" not in st.session_state:
    st.session_state["master_results_crypto"] = {}


# ─────────────────────────────────────────────
# TEMPORALIDADES
# ─────────────────────────────────────────────

TF_OPTIONS = {
    "30 MIN": "30m",
    "1 HS": "1h",
    "4 HS": "4h",
    "1 DIA": "1d",
    "1 SEMANA": "1w",
    "1 MES": "1M"
}


# ─────────────────────────────────────────────
# SECTORES CRIPTO
# ─────────────────────────────────────────────

CRYPTO_SECTORS = {
    "LEADER": [
        "BTC/USDT",
        "ETH/USDT"
    ],

    "LAYER 1": [
        "SOL/USDT",
        "ADA/USDT",
        "DOT/USDT",
        "AVAX/USDT",
        "MATIC/USDT",
        "NEAR/USDT",
        "FTM/USDT",
        "ALGO/USDT"
    ],

    "DEFI/L2": [
        "ARB/USDT",
        "OP/USDT",
        "LINK/USDT",
        "UNI/USDT",
        "AAVE/USDT",
        "LDO/USDT"
    ],

    "AI/DEPIN": [
        "RNDR/USDT",
        "FET/USDT",
        "FIL/USDT",
        "THETA/USDT"
    ],

    "MEMES": [
        "DOGE/USDT",
        "SHIB/USDT",
        "PEPE/USDT",
        "BONK/USDT",
        "FLOKI/USDT"
    ],

    "EXCHANGE": [
        "BNB/USDT",
        "KCS/USDT",
        "OKB/USDT"
    ]
}


def get_crypto_sector(ticker):
    for sector, members in CRYPTO_SECTORS.items():
        if ticker.upper() in members:
            return sector

    return "ALTCOINS / OTROS"


# ─────────────────────────────────────────────
# MOTOR DEMA
# ─────────────────────────────────────────────

def dema(s, length):
    ema1 = s.ewm(
        span=length,
        adjust=False,
        min_periods=length
    ).mean()

    ema2 = ema1.ewm(
        span=length,
        adjust=False,
        min_periods=length
    ).mean()

    return 2 * ema1 - ema2


# ─────────────────────────────────────────────
# MOTOR PRINCIPAL
#
# INTEGRA:
# 1) SLY ORIGINAL
# 2) RSI PRO INSTITUTIONAL MOMENTUM
# ─────────────────────────────────────────────

def get_sly_indicators(df):

    try:

        # -------------------------------------------------
        # NORMALIZACIÓN DE COLUMNAS
        # -------------------------------------------------

        df = df.copy()

        df.columns = [str(c).capitalize() for c in df.columns]

        required = [
            "Open",
            "High",
            "Low",
            "Close",
            "Vol"
        ]

        for col in required:
            if col not in df.columns:
                return pd.DataFrame()

        df = df.dropna(
            subset=["Open", "High", "Low", "Close", "Vol"]
        )

        if len(df) < 300:
            return pd.DataFrame()


        # =================================================
        # SLY ORIGINAL — MACD DEMA
        # =================================================

        df["macd_line"] = (
            dema(df["Close"], 12)
            -
            dema(df["Close"], 26)
        )

        df["signal_line"] = (
            df["macd_line"]
            .ewm(
                span=9,
                adjust=False
            )
            .mean()
        )

        df["hist"] = (
            df["macd_line"]
            -
            df["signal_line"]
        )


        # =================================================
        # RSI PRO — RSI 14
        # =================================================

        raw_rsi = ta.rsi(
            df["Close"],
            length=14
        )

        # Igual que el segundo script:
        # RSI nulo inicial -> 50
        raw_rsi = raw_rsi.fillna(50)

        df["rsi_raw"] = raw_rsi


        # =================================================
        # RSI PRO — DEMA 5
        # =================================================

        df["rsi_smooth"] = dema(
            df["rsi_raw"],
            5
        )


        # =================================================
        # RSI PRO — SMA 20
        # =================================================

        df["rsi_basis"] = (
            df["rsi_smooth"]
            .rolling(
                window=20,
                min_periods=20
            )
            .mean()
        )


        # =================================================
        # RSI PRO — DESVIACIÓN ESTÁNDAR 20
        # =================================================

        df["rsi_std"] = (
            df["rsi_smooth"]
            .rolling(
                window=20,
                min_periods=20
            )
            .std()
        )


        # =================================================
        # RSI PRO — BANDAS DINÁMICAS
        #
        # upper = basis + 2 std
        # lower = basis - 2 std
        # =================================================

        df["upper_band"] = (
            df["rsi_basis"]
            +
            2.0 * df["rsi_std"]
        )

        df["lower_band"] = (
            df["rsi_basis"]
            -
            2.0 * df["rsi_std"]
        )


        # =================================================
        # RSI PRO — VOLUMEN
        # =================================================

        df["vol_avg"] = (
            df["Vol"]
            .rolling(
                window=20,
                min_periods=20
            )
            .mean()
        )

        df["vol_std"] = (
            df["Vol"]
            .rolling(
                window=20,
                min_periods=20
            )
            .std()
        )


        # Evita división por cero
        df["vol_z"] = np.where(
            df["vol_std"] != 0,
            (
                df["Vol"]
                -
                df["vol_avg"]
            )
            /
            df["vol_std"],
            0
        )


        # =================================================
        # RSI PRO — VOLUMEN INSTITUCIONAL
        #
        # Pine:
        # vol_z > 1.5
        # =================================================

        df["vol_alpha"] = (
            df["vol_z"] > 1.5
        )


        # =================================================
        # RSI PRO — DIRECCIÓN DEL RSI
        # =================================================

        df["rsi_rising"] = (
            df["rsi_smooth"]
            >
            df["rsi_smooth"].shift(1)
        )

        df["rsi_falling"] = (
            df["rsi_smooth"]
            <
            df["rsi_smooth"].shift(1)
        )


        # =================================================
        # RSI PRO — COLORES EXACTOS DEL SEGUNDO SCRIPT
        #
        # VERDE FUERTE:
        # RSI > 50 Y subiendo
        #
        # VERDE OSCURO:
        # RSI > 50 Y bajando
        #
        # ROJO:
        # RSI < 50 Y bajando
        #
        # ROJO OSCURO:
        # RSI < 50 Y subiendo
        # =================================================

        conditions = [
            (
                (df["rsi_smooth"] > 50)
                &
                df["rsi_rising"]
            ),

            (
                (df["rsi_smooth"] > 50)
                &
                df["rsi_falling"]
            ),

            (
                (df["rsi_smooth"] < 50)
                &
                df["rsi_falling"]
            ),

            (
                (df["rsi_smooth"] < 50)
                &
                df["rsi_rising"]
            )
        ]

        choices = [
            "VERDE 🟢",
            "VERDE OSCURO 🟩",
            "ROJO 🔴",
            "ROJO OSCURO 🟥"
        ]

        df["rsi_pro_color"] = np.select(
            conditions,
            choices,
            default="NEUTRO ⚪"
        )


        # =================================================
        # RSI PRO — ALPHA STRIKE
        #
        # Pine:
        # crossover(rsi_smooth, 50)
        # AND vol_z > 1.5
        # =================================================

        rsi_cross_up = (
            (df["rsi_smooth"] > 50)
            &
            (df["rsi_smooth"].shift(1) <= 50)
        )

        df["alpha_strike"] = (
            rsi_cross_up
            &
            df["vol_alpha"]
        )


        # =================================================
        # RSI PRO — EXHAUSTION
        #
        # Pine:
        # crossunder(rsi_smooth, upper_band)
        # =================================================

        rsi_cross_under_upper = (
            (df["rsi_smooth"] < df["upper_band"])
            &
            (
                df["rsi_smooth"].shift(1)
                >=
                df["upper_band"].shift(1)
            )
        )

        df["exhaustion"] = (
            rsi_cross_under_upper
        )


        # =================================================
        # RSI PRO — ALERTA VERDE
        #
        # IMPORTANTE:
        # Esto NO exige cruce de 50.
        #
        # Si RSI > 50 y sigue subiendo:
        # VERDE
        # =================================================

        df["rsi_pro_green"] = (
            (df["rsi_smooth"] > 50)
            &
            df["rsi_rising"]
        )


        # =================================================
        # HEIKIN ASHI ORIGINAL
        # =================================================

        ha_c = (
            df["Open"]
            +
            df["High"]
            +
            df["Low"]
            +
            df["Close"]
        ) / 4

        ha_o = np.zeros(len(df))

        ha_o[0] = (
            df["Open"].iloc[0]
            +
            df["Close"].iloc[0]
        ) / 2

        for i in range(1, len(df)):

            ha_o[i] = (
                ha_o[i - 1]
                +
                ha_c.iloc[i - 1]
            ) / 2

        df["ha_color"] = np.where(
            ha_c > ha_o,
            "Verde",
            "Rojo"
        )


        # =================================================
        # EMA 52 / EMA 260
        # =================================================

        df["ema52"] = ta.ema(
            df["Close"],
            length=52
        )

        df["ema260"] = ta.ema(
            df["Close"],
            length=260
        )


        # =================================================
        # LIMPIEZA FINAL
        # =================================================

        df = df.dropna(
            subset=[
                "ema260",
                "rsi_smooth",
                "rsi_basis",
                "rsi_std",
                "upper_band",
                "lower_band"
            ]
        )

        return df

    except Exception:
        return pd.DataFrame()


# ─────────────────────────────────────────────
# MACD MENSUAL
# ─────────────────────────────────────────────

def get_monthly_macd_force(ex, symbol):

    try:

        raw = ex.fetch_ohlcv(
            symbol,
            timeframe="1M",
            limit=50
        )

        df = pd.DataFrame(
            raw,
            columns=[
                "time",
                "open",
                "high",
                "low",
                "close",
                "vol"
            ]
        )

        if len(df) < 30:
            return "N/A"

        m_macd = (
            dema(df["close"], 12)
            -
            dema(df["close"], 26)
        )

        m_signal = (
            m_macd
            .ewm(
                span=9,
                adjust=False
            )
            .mean()
        )

        m_hist = (
            m_macd
            -
            m_signal
        )

        current_h = m_hist.iloc[-1]
        previous_h = m_hist.iloc[-2]

        if current_h > previous_h:
            return "GANANDO FUERZA 📈"

        return "PERDIENDO FUERZA 📉"

    except Exception:
        return "N/A"


# ─────────────────────────────────────────────
# SEÑAL ORIGINAL SLY
# ─────────────────────────────────────────────

def find_last_signal(df, bear_longs):

    if df.empty or len(df) < 2:
        return None, None, False, "-"

    last_entry_date = None
    last_entry_px = None
    is_active = False
    verdict = "-"

    for i in range(1, len(df)):

        authorized = (
            df["ema52"].iloc[i]
            >
            df["ema260"].iloc[i]
        ) or bear_longs

        ha_flip = (
            df["ha_color"].iloc[i] == "Verde"
            and
            df["ha_color"].iloc[i - 1] == "Rojo"
        )

        macd_accel = (
            df["hist"].iloc[i]
            >
            df["hist"].iloc[i - 1]
        )

        rsi_ok = (
            df["rsi_smooth"].iloc[i]
            >
            df["rsi_smooth"].iloc[i - 1]
            and
            df["rsi_smooth"].iloc[i] < 50
        )

        # ENTRADA ORIGINAL
        if (
            not is_active
            and
            authorized
            and
            ha_flip
            and
            macd_accel
            and
            rsi_ok
        ):

            is_active = True
            last_entry_date = df.index[i]
            last_entry_px = df["Close"].iloc[i]

        # SALIDA ORIGINAL
        elif (
            is_active
            and
            df["ha_color"].iloc[i] == "Rojo"
            and
            df["hist"].iloc[i]
            <
            df["hist"].iloc[i - 1]
            and
            df["rsi_smooth"].iloc[i]
            <
            df["rsi_smooth"].iloc[i - 1]
        ):

            is_active = False

    if is_active:

        c_h = df["hist"].iloc[-1]
        p_h = df["hist"].iloc[-2]

        if p_h > 0 and c_h <= 0:

            verdict = "CERRAR OPERACIÓN 🔴"

        elif c_h > p_h:

            verdict = "MANTENER 🟢"

        else:

            verdict = "PIERDE FUERZA 🟡"

    return (
        last_entry_date,
        last_entry_px,
        is_active,
        verdict
    )


# ─────────────────────────────────────────────
# KUCOIN
# ─────────────────────────────────────────────

@st.cache_resource
def get_exchange():

    return ccxt.kucoin({
        "enableRateLimit": True
    })


def fetch_symbols():

    try:

        ex = get_exchange()

        markets = ex.load_markets()

        symbols = [
            s
            for s in markets
            if "/USDT" in s
            and markets[s]["active"]
        ]

        filtered = [
            s
            for s in symbols
            if not any(
                x in s
                for x in [
                    "3L",
                    "3S",
                    "USDC",
                    "DAI",
                    "PAX",
                    "TUSD"
                ]
            )
        ]

        return sorted(filtered)

    except Exception:

        return []


# ─────────────────────────────────────────────
# INTERFAZ
# ─────────────────────────────────────────────

st.title(
    "🛡️ SLY | CRIPTO SIGNAL TRACKER + RSI PRO"
)

st.caption(
    "SLY original + RSI PRO Institutional Momentum integrado"
)


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:

    st.header("⚙️ Configuración")

    st.subheader(
        "1. Parámetros de Tiempo"
    )

    selected_tf_label = st.selectbox(
        "Seleccionar Temporalidad:",
        list(TF_OPTIONS.keys()),
        index=2
    )

    selected_tf_code = TF_OPTIONS[
        selected_tf_label
    ]


    if st.button(
        "📡 Sincronizar Mercado KuCoin"
    ):

        with st.spinner(
            "Sincronizando mercados..."
        ):

            st.session_state[
                "crypto_list"
            ] = fetch_symbols()

        st.rerun()


    if "crypto_list" in st.session_state:

        st.subheader(
            "2. Ejecución"
        )

        lote_size = st.number_input(
            "Tamaño de Lote:",
            min_value=10,
            max_value=100,
            value=50,
            step=10
        )

        total_lotes = max(
            1,
            (
                len(
                    st.session_state[
                        "crypto_list"
                    ]
                )
                +
                lote_size
                -
                1
            )
            //
            lote_size
        )

        batch_idx = st.selectbox(
            "Seleccionar Lote:",
            range(total_lotes),
            format_func=lambda x:
                f"Lote {x + 1}"
        )

        bear_longs = st.checkbox(
            "Habilitar Bear-Longs",
            value=True
        )


        if st.button(
            "🚀 ACTUALIZAR Y ACUMULAR",
            type="primary"
        ):

            ex = get_exchange()

            crypto_list = st.session_state[
                "crypto_list"
            ]

            start_idx = (
                batch_idx
                *
                lote_size
            )

            end_idx = (
                start_idx
                +
                lote_size
            )

            subset = crypto_list[
                start_idx:end_idx
            ]

            if not subset:

                st.warning(
                    "El lote seleccionado está vacío."
                )

            else:

                prog = st.progress(0)

                for i, sym in enumerate(subset):

                    try:

                        prog.progress(
                            (i + 1) / len(subset),
                            text=(
                                f"Auditando "
                                f"{selected_tf_label}: "
                                f"{sym}"
                            )
                        )


                        # -----------------------------------------
                        # DATOS PRINCIPALES
                        # -----------------------------------------

                        raw_data = ex.fetch_ohlcv(
                            sym,
                            timeframe=selected_tf_code,
                            limit=1000
                        )

                        if not raw_data:
                            continue

                        df = pd.DataFrame(
                            raw_data,
                            columns=[
                                "time",
                                "open",
                                "high",
                                "low",
                                "close",
                                "vol"
                            ]
                        )

                        df["time"] = pd.to_datetime(
                            df["time"],
                            unit="ms"
                        )

                        df.set_index(
                            "time",
                            inplace=True
                        )


                        data = get_sly_indicators(df)

                        if data.empty:
                            continue


                        # -----------------------------------------
                        # MACD MENSUAL
                        # -----------------------------------------

                        monthly_force = (
                            get_monthly_macd_force(
                                ex,
                                sym
                            )
                        )


                        # -----------------------------------------
                        # SEÑAL SLY ORIGINAL
                        # -----------------------------------------

                        (
                            sig_date,
                            sig_px,
                            vigente,
                            verd
                        ) = find_last_signal(
                            data,
                            bear_longs
                        )


                        if (
                            vigente
                            and
                            sig_px
                            and
                            sig_px != 0
                        ):

                            pnl_val = (
                                (
                                    (
                                        data["Close"].iloc[-1]
                                        -
                                        sig_px
                                    )
                                    /
                                    sig_px
                                )
                                *
                                100
                            )

                            pnl_val = (
                                f"{pnl_val:.2f}%"
                            )

                        else:

                            pnl_val = "-"


                        # =========================================
                        # RSI PRO — VALORES ACTUALES
                        # =========================================

                        last_rsi = (
                            data[
                                "rsi_smooth"
                            ].iloc[-1]
                        )

                        previous_rsi = (
                            data[
                                "rsi_smooth"
                            ].iloc[-2]
                        )

                        last_upper = (
                            data[
                                "upper_band"
                            ].iloc[-1]
                        )

                        last_lower = (
                            data[
                                "lower_band"
                            ].iloc[-1]
                        )

                        last_rsi_basis = (
                            data[
                                "rsi_basis"
                            ].iloc[-1]
                        )

                        last_rsi_std = (
                            data[
                                "rsi_std"
                            ].iloc[-1]
                        )

                        last_vol_z = (
                            data[
                                "vol_z"
                            ].iloc[-1]
                        )


                        # -----------------------------------------
                        # COLOR RSI PRO
                        # -----------------------------------------

                        rsi_pro_color = (
                            data[
                                "rsi_pro_color"
                            ].iloc[-1]
                        )


                        # -----------------------------------------
                        # RSI VERDE
                        # -----------------------------------------

                        rsi_green = bool(
                            data[
                                "rsi_pro_green"
                            ].iloc[-1]
                        )


                        # -----------------------------------------
                        # ALPHA STRIKE
                        # -----------------------------------------

                        alpha_strike = bool(
                            data[
                                "alpha_strike"
                            ].iloc[-1]
                        )


                        # -----------------------------------------
                        # EXHAUSTION
                        # -----------------------------------------

                        exhaustion = bool(
                            data[
                                "exhaustion"
                            ].iloc[-1]
                        )


                        # -----------------------------------------
                        # ZONA RSI
                        # -----------------------------------------

                        if last_rsi > 50:

                            rsi_zone = (
                                "SOBRE 50 🟢"
                            )

                        else:

                            rsi_zone = (
                                "BAJO 50 🔴"
                            )


                        # -----------------------------------------
                        # RSI PRO ESTADO
                        # -----------------------------------------

                        if rsi_green:

                            rsi_pro_status = (
                                "🟢 VERDE"
                            )

                        elif last_rsi > 50:

                            rsi_pro_status = (
                                "🟩 VERDE OSCURO"
                            )

                        elif last_rsi < 50 and (
                            data[
                                "rsi_rising"
                            ].iloc[-1]
                        ):

                            rsi_pro_status = (
                                "🟥 ROJO OSCURO"
                            )

                        elif last_rsi < 50:

                            rsi_pro_status = (
                                "🔴 ROJO"
                            )

                        else:

                            rsi_pro_status = (
                                "⚪ NEUTRO"
                            )


                        # -----------------------------------------
                        # ALPHA STATUS
                        # -----------------------------------------

                        if alpha_strike:

                            alpha_status = (
                                "🔥 ALPHA STRIKE"
                            )

                        else:

                            alpha_status = "-"


                        # -----------------------------------------
                        # EXHAUSTION STATUS
                        # -----------------------------------------

                        if exhaustion:

                            exhaustion_status = (
                                "⚠️ EXHAUSTION"
                            )

                        else:

                            exhaustion_status = "-"


                        # -----------------------------------------
                        # AVISO
                        # -----------------------------------------

                        if (
                            rsi_green
                            and
                            alpha_strike
                        ):

                            alert_status = (
                                "🔥🟢 VERDE + ALPHA"
                            )

                        elif rsi_green:

                            alert_status = (
                                "🟢 RSI PRO VERDE"
                            )

                        elif exhaustion:

                            alert_status = (
                                "⚠️ EXHAUSTION"
                            )

                        else:

                            alert_status = "-"


                        # -----------------------------------------
                        # GUARDAR RESULTADOS
                        # -----------------------------------------

                        st.session_state[
                            "master_results_crypto"
                        ][sym] = {

                            "Activo":
                                sym.replace(
                                    "/USDT",
                                    ""
                                ),

                            "Temporalidad":
                                selected_tf_label,

                            "Sector":
                                get_crypto_sector(
                                    sym
                                ),

                            "MACD Mensual":
                                monthly_force,

                            "RSI PRO":
                                rsi_pro_status,

                            "Alerta RSI":
                                alert_status,

                            "Alpha":
                                alpha_status,

                            "Exhaustion":
                                exhaustion_status,

                            "Estado":
                                (
                                    "VIGENTE 🟢"
                                    if vigente
                                    else
                                    "CERRADA 🔴"
                                ),

                            "Veredicto":
                                verd,

                            "PnL Real":
                                pnl_val,

                            "Última Señal":
                                (
                                    sig_date.strftime(
                                        "%d/%m %H:%M"
                                    )
                                    if sig_date
                                    else "-"
                                ),

                            "Zona RSI":
                                rsi_zone,

                            "RSI":
                                round(
                                    last_rsi,
                                    2
                                ),

                            "RSI Anterior":
                                round(
                                    previous_rsi,
                                    2
                                ),

                            "RSI Base":
                                round(
                                    last_rsi_basis,
                                    2
                                ),

                            "Banda Superior":
                                round(
                                    last_upper,
                                    2
                                ),

                            "Banda Inferior":
                                round(
                                    last_lower,
                                    2
                                ),

                            "Vol Z":
                                round(
                                    last_vol_z,
                                    2
                                ),

                            "Precio":
                                f"{data['Close'].iloc[-1]:.4f}",

                            "Régimen":
                                (
                                    "ALCISTA"
                                    if
                                    data[
                                        "ema52"
                                    ].iloc[-1]
                                    >
                                    data[
                                        "ema260"
                                    ].iloc[-1]
                                    else
                                    "BAJISTA"
                                )
                        }

                        time.sleep(0.05)

                    except Exception:
                        continue

                st.rerun()


    if st.button(
        "🗑️ Limpiar Memoria"
    ):

        st.session_state[
            "master_results_crypto"
        ] = {}

        st.rerun()


# ─────────────────────────────────────────────
# RESULTADOS
# ─────────────────────────────────────────────

if st.session_state[
    "master_results_crypto"
]:

    df_full = pd.DataFrame(
        st.session_state[
            "master_results_crypto"
        ].values()
    )


    # =================================================
    # AVISOS RSI PRO
    # =================================================

    green_df = df_full[
        df_full["RSI PRO"] == "🟢 VERDE"
    ]

    alpha_df = df_full[
        df_full["Alpha"] == "🔥 ALPHA STRIKE"
    ]

    exhaustion_df = df_full[
        df_full["Exhaustion"] == "⚠️ EXHAUSTION"
    ]


    # =================================================
    # AVISO VERDE
    # =================================================

    if not green_df.empty:

        st.markdown(
            '<div class="rsi-green-box">'
            '🟢 RSI PRO VERDE DETECTADO — '
            'RSI DEMA(5) está por encima de 50 '
            'y subiendo.'
            '</div>',
            unsafe_allow_html=True
        )

        green_assets = []

        for _, row in green_df.iterrows():

            green_assets.append(
                f"**{row['Activo']} "
                f"{row['Temporalidad']}** "
                f"(RSI {row['RSI']:.2f})"
            )

        st.success(
            " | ".join(green_assets)
        )


    # =================================================
    # ALPHA STRIKE
    # =================================================

    if not alpha_df.empty:

        st.markdown(
            '<div class="alpha-box">'
            '🔥 ALPHA STRIKE DETECTADO — '
            'RSI acaba de cruzar 50 al alza '
            'con Volume Z-Score > 1.5.'
            '</div>',
            unsafe_allow_html=True
        )

        alpha_assets = []

        for _, row in alpha_df.iterrows():

            alpha_assets.append(
                f"{row['Activo']} "
                f"{row['Temporalidad']}"
            )

        st.warning(
            "🔥 " + " | ".join(alpha_assets)
        )


    # =================================================
    # EXHAUSTION
    # =================================================

    if not exhaustion_df.empty:

        st.markdown(
            '<div class="exhaustion-box">'
            '⚠️ EXHAUSTION — RSI cruzó por debajo '
            'de su banda superior dinámica.'
            '</div>',
            unsafe_allow_html=True
        )


    # =================================================
    # RESUMEN SECTORIAL
    # =================================================

    df_vigentes = df_full[
        df_full["Estado"] == "VIGENTE 🟢"
    ]


    st.subheader(
        "📊 RESUMEN DE EXPOSICIÓN (VIGENTES)"
    )


    if not df_vigentes.empty:

        summary = (
            df_vigentes
            .groupby("Sector")["Activo"]
            .apply(list)
            .reset_index()
        )

        cols = st.columns(3)

        for idx, row in summary.iterrows():

            with cols[idx % 3]:

                st.markdown(
                    f"""
                    <div class="sector-box">
                        <div class="sector-title">
                            {row['Sector']}: {len(row['Activo'])}
                        </div>
                        <div style='font-size: 0.85em;'>
                            {', '.join(row['Activo'])}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    else:

        st.warning(
            "Sin posiciones abiertas en "
            "la temporalidad analizada."
        )


    # =================================================
    # MATRIZ PRINCIPAL
    # =================================================

    st.subheader(
        f"📋 MATRIZ DE SEÑALES "
        f"(Filtro Actual: {selected_tf_label})"
    )


    df_res = df_full.sort_values(
        by=[
            "Alerta RSI",
            "Estado",
            "Activo"
        ],
        ascending=[
            True,
            False,
            True
        ]
    )


    # =================================================
    # ORDEN DE COLUMNAS
    # =================================================

    cols_order = [

        "Activo",
        "Sector",
        "Temporalidad",

        "RSI PRO",
        "Alerta RSI",
        "Alpha",
        "Exhaustion",

        "RSI",
        "RSI Anterior",
        "Vol Z",

        "Banda Superior",
        "Banda Inferior",

        "MACD Mensual",

        "Estado",
        "Veredicto",
        "PnL Real",
        "Última Señal",

        "Zona RSI",
        "Precio",
        "Régimen"
    ]


    # Seguridad por si alguna columna no existe
    cols_order = [
        c
        for c in cols_order
        if c in df_res.columns
    ]

    df_res = df_res[
        cols_order
    ]


    # =================================================
    # COLORES
    # =================================================

    def color_cells(val):

        str_v = str(val)

        # VERDE
        if (
            "🟢 VERDE" in str_v
            or
            "VERDE 🟢" in str_v
            or
            "ALPHA" in str_v
            or
            "VIGENTE" in str_v
            or
            "MANTENER" in str_v
            or
            "ALCISTA" in str_v
            or
            "SOBRE 50" in str_v
            or
            "GANANDO" in str_v
        ):

            return (
                "background-color: #C8E6C9; "
                "color: #1B5E20; "
                "font-weight: bold;"
            )


        # ROJO
        if (
            "ROJO 🔴" in str_v
            or
            "ROJO OSCURO" in str_v
            or
            "CERRADA" in str_v
            or
            "CERRAR" in str_v
            or
            "BAJISTA" in str_v
            or
            "BAJO 50" in str_v
            or
            "PERDIENDO" in str_v
        ):

            return (
                "background-color: #FFCDD2; "
                "color: #B71C1C; "
                "font-weight: bold;"
            )


        # AMARILLO
        if (
            "PIERDE FUERZA" in str_v
            or
            "EXHAUSTION" in str_v
        ):

            return (
                "background-color: #FFF9C4; "
                "color: #827717; "
                "font-weight: bold;"
            )


        # VERDE OSCURO
        if "VERDE OSCURO" in str_v:

            return (
                "background-color: #DCEDC8; "
                "color: #33691E; "
                "font-weight: bold;"
            )


        return ""


    st.dataframe(
        df_res.style.map(color_cells),
        use_container_width=True,
        height=700
    )


    # =================================================
    # RESUMEN RÁPIDO
    # =================================================

    st.subheader(
        "🎯 RESUMEN RSI PRO"
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        st.metric(
            "🟢 RSI VERDE",
            len(green_df)
        )

    with c2:

        st.metric(
            "🔥 ALPHA STRIKE",
            len(alpha_df)
        )

    with c3:

        st.metric(
            "⚠️ EXHAUSTION",
            len(exhaustion_df)
        )

    with c4:

        st.metric(
            "Total analizados",
            len(df_full)
        )


else:

    st.info(
        "👈 Seleccione temporalidad, "
        "sincronice el mercado y analice los lotes."
    )
```
