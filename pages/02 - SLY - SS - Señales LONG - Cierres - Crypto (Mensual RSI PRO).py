
```python
import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time

# ============================================================
# CONFIGURACIÓN
# ============================================================

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

.alert-green {
    background-color: #C8E6C9;
    color: #1B5E20;
    padding: 12px;
    border-radius: 8px;
    border-left: 6px solid #2E7D32;
    font-weight: bold;
}

.alert-alpha {
    background-color: #FFF3CD;
    color: #7A4F00;
    padding: 12px;
    border-radius: 8px;
    border-left: 6px solid #FF9800;
    font-weight: bold;
}

.alert-exhaustion {
    background-color: #FFCDD2;
    color: #B71C1C;
    padding: 12px;
    border-radius: 8px;
    border-left: 6px solid #C62828;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# MEMORIA
# ============================================================

if "master_results_crypto" not in st.session_state:
    st.session_state["master_results_crypto"] = {}


# ============================================================
# TEMPORALIDADES
# ============================================================

TF_OPTIONS = {
    "30 MIN": "30m",
    "1 HS": "1h",
    "4 HS": "4h",
    "1 DIA": "1d",
    "1 SEMANA": "1w",
    "1 MES": "1M",
}


# ============================================================
# SECTORES
# ============================================================

CRYPTO_SECTORS = {
    "LEADER": [
        "BTC/USDT",
        "ETH/USDT",
    ],

    "LAYER 1": [
        "SOL/USDT",
        "ADA/USDT",
        "DOT/USDT",
        "AVAX/USDT",
        "MATIC/USDT",
        "NEAR/USDT",
        "FTM/USDT",
        "ALGO/USDT",
    ],

    "DEFI/L2": [
        "ARB/USDT",
        "OP/USDT",
        "LINK/USDT",
        "UNI/USDT",
        "AAVE/USDT",
        "LDO/USDT",
    ],

    "AI/DEPIN": [
        "RNDR/USDT",
        "FET/USDT",
        "FIL/USDT",
        "THETA/USDT",
    ],

    "MEMES": [
        "DOGE/USDT",
        "SHIB/USDT",
        "PEPE/USDT",
        "BONK/USDT",
        "FLOKI/USDT",
    ],

    "EXCHANGE": [
        "BNB/USDT",
        "KCS/USDT",
        "OKB/USDT",
    ],
}


def get_crypto_sector(ticker):
    ticker = ticker.upper()

    for sector, members in CRYPTO_SECTORS.items():
        if ticker in members:
            return sector

    return "ALTCOINS / OTROS"


# ============================================================
# DEMA
# ============================================================

def dema(series, length):
    ema1 = series.ewm(
        span=length,
        adjust=False
    ).mean()

    ema2 = ema1.ewm(
        span=length,
        adjust=False
    ).mean()

    return 2 * ema1 - ema2


# ============================================================
# MOTOR SLY + RSI PRO
# ============================================================

def get_sly_indicators(df):

    try:

        df = df.copy()

        df.columns = [
            str(c).capitalize()
            for c in df.columns
        ]

        required = [
            "Open",
            "High",
            "Low",
            "Close",
            "Vol",
        ]

        for col in required:
            if col not in df.columns:
                return pd.DataFrame()

        df = df.dropna(
            subset=required
        )

        if len(df) < 300:
            return pd.DataFrame()


        # ====================================================
        # SLY ORIGINAL
        # MACD DEMA 12 / 26
        # ====================================================

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


        # ====================================================
        # RSI PRO
        # RSI 14
        # ====================================================

        raw_rsi = ta.rsi(
            df["Close"],
            length=14
        )

        raw_rsi = raw_rsi.fillna(50)

        df["rsi_raw"] = raw_rsi


        # ====================================================
        # RSI PRO
        # DEMA 5
        # ====================================================

        df["rsi_smooth"] = dema(
            df["rsi_raw"],
            5
        )


        # ====================================================
        # RSI PRO
        # SMA 20
        # ====================================================

        df["rsi_basis"] = (
            df["rsi_smooth"]
            .rolling(
                window=20,
                min_periods=20
            )
            .mean()
        )


        # ====================================================
        # RSI PRO
        # DESVIACIÓN ESTÁNDAR 20
        # ====================================================

        df["rsi_std"] = (
            df["rsi_smooth"]
            .rolling(
                window=20,
                min_periods=20
            )
            .std()
        )


        # ====================================================
        # RSI PRO
        # BANDAS DINÁMICAS
        # ====================================================

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


        # ====================================================
        # RSI PRO
        # VOLUMEN
        # ====================================================

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


        # ====================================================
        # VOLUME Z-SCORE
        # ====================================================

        df["vol_z"] = (
            (
                df["Vol"]
                -
                df["vol_avg"]
            )
            /
            df["vol_std"]
        )

        df["vol_z"] = (
            df["vol_z"]
            .replace(
                [np.inf, -np.inf],
                np.nan
            )
            .fillna(0.0)
        )


        # ====================================================
        # VOLUME ALPHA
        # Z > 1.5
        # ====================================================

        df["vol_alpha"] = (
            df["vol_z"] > 1.5
        )


        # ====================================================
        # DIRECCIÓN RSI
        # ====================================================

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


        # ====================================================
        # COLORES EXACTOS DEL RSI PRO
        #
        # VERDE:
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
        # ====================================================

        df["rsi_pro_color"] = np.select(

            [
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
                ),
            ],

            [
                "VERDE",
                "VERDE OSCURO",
                "ROJO",
                "ROJO OSCURO",
            ],

            default="NEUTRO",
        )


        # ====================================================
        # RSI PRO VERDE
        #
        # ESTA ES LA ALERTA QUE PEDISTE
        #
        # RSI DEMA(5) > 50
        # Y RSI DEMA(5) SUBIENDO
        # ====================================================

        df["rsi_pro_green"] = (
            (df["rsi_smooth"] > 50)
            &
            df["rsi_rising"]
        )


        # ====================================================
        # CROSSOVER RSI 50
        # ====================================================

        df["rsi_cross_up"] = (
            (df["rsi_smooth"] > 50)
            &
            (
                df["rsi_smooth"].shift(1)
                <= 50
            )
        )


        # ====================================================
        # ALPHA STRIKE
        #
        # RSI cruza 50 al alza
        # +
        # Volume Z > 1.5
        # ====================================================

        df["alpha_strike"] = (
            df["rsi_cross_up"]
            &
            df["vol_alpha"]
        )


        # ====================================================
        # EXHAUSTION
        #
        # RSI cruza hacia abajo
        # la banda superior
        # ====================================================

        df["exhaustion"] = (
            (
                df["rsi_smooth"]
                <
                df["upper_band"]
            )
            &
            (
                df["rsi_smooth"].shift(1)
                >=
                df["upper_band"].shift(1)
            )
        )


        # ====================================================
        # HEIKIN ASHI
        # ====================================================

        ha_c = (
            df["Open"]
            +
            df["High"]
            +
            df["Low"]
            +
            df["Close"]
        ) / 4.0

        ha_o = np.zeros(
            len(df),
            dtype=float
        )

        ha_o[0] = (
            df["Open"].iloc[0]
            +
            df["Close"].iloc[0]
        ) / 2.0

        for i in range(1, len(df)):

            ha_o[i] = (
                ha_o[i - 1]
                +
                ha_c.iloc[i - 1]
            ) / 2.0

        df["ha_color"] = np.where(
            ha_c > ha_o,
            "Verde",
            "Rojo"
        )


        # ====================================================
        # EMA 52 / EMA 260
        # ====================================================

        df["ema52"] = ta.ema(
            df["Close"],
            length=52
        )

        df["ema260"] = ta.ema(
            df["Close"],
            length=260
        )


        # ====================================================
        # LIMPIEZA
        # ====================================================

        df = df.dropna(
            subset=[
                "ema260",
                "rsi_smooth",
                "rsi_basis",
                "rsi_std",
                "upper_band",
                "lower_band",
            ]
        )

        return df

    except Exception:
        return pd.DataFrame()


# ============================================================
# MACD MENSUAL
# ============================================================

def get_monthly_macd_force(ex, symbol):

    try:

        raw = ex.fetch_ohlcv(
            symbol,
            timeframe="1M",
            limit=50
        )

        if not raw or len(raw) < 30:
            return "N/A"

        df = pd.DataFrame(
            raw,
            columns=[
                "time",
                "open",
                "high",
                "low",
                "close",
                "vol",
            ]
        )

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

        if (
            m_hist.iloc[-1]
            >
            m_hist.iloc[-2]
        ):
            return "GANANDO FUERZA 📈"

        return "PERDIENDO FUERZA 📉"

    except Exception:
        return "N/A"


# ============================================================
# SEÑAL SLY ORIGINAL
# ============================================================

def find_last_signal(
    df,
    bear_longs
):

    if df.empty or len(df) < 2:
        return None, None, False, "-"

    last_entry_date = None
    last_entry_px = None
    is_active = False
    verdict = "-"

    for i in range(1, len(df)):

        authorized = (
            (
                df["ema52"].iloc[i]
                >
                df["ema260"].iloc[i]
            )
            or
            bear_longs
        )

        ha_flip = (
            df["ha_color"].iloc[i]
            ==
            "Verde"
            and
            df["ha_color"].iloc[i - 1]
            ==
            "Rojo"
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
            df["rsi_smooth"].iloc[i]
            <
            50
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

            last_entry_date = (
                df.index[i]
            )

            last_entry_px = (
                df["Close"].iloc[i]
            )


        # SALIDA ORIGINAL
        elif is_active:

            exit_signal = (
                df["ha_color"].iloc[i]
                ==
                "Rojo"
                and
                df["hist"].iloc[i]
                <
                df["hist"].iloc[i - 1]
                and
                df["rsi_smooth"].iloc[i]
                <
                df["rsi_smooth"].iloc[i - 1]
            )

            if exit_signal:
                is_active = False


    if is_active:

        current_h = df["hist"].iloc[-1]
        previous_h = df["hist"].iloc[-2]

        if (
            previous_h > 0
            and
            current_h <= 0
        ):

            verdict = (
                "CERRAR OPERACIÓN 🔴"
            )

        elif current_h > previous_h:

            verdict = "MANTENER 🟢"

        else:

            verdict = (
                "PIERDE FUERZA 🟡"
            )


    return (
        last_entry_date,
        last_entry_px,
        is_active,
        verdict
    )


# ============================================================
# KUCOIN
# ============================================================

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
            and markets[s].get(
                "active",
                False
            )
        ]

        excluded = [
            "3L",
            "3S",
            "USDC",
            "DAI",
            "PAX",
            "TUSD",
        ]

        filtered = [
            s
            for s in symbols
            if not any(
                x in s
                for x in excluded
            )
        ]

        return sorted(filtered)

    except Exception:
        return []


# ============================================================
# TÍTULO
# ============================================================

st.title(
    "🛡️ SLY | CRIPTO SIGNAL TRACKER + RSI PRO"
)

st.caption(
    "SLY original + RSI PRO Institutional Momentum"
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("⚙️ Configuración")

    st.subheader(
        "1. Parámetros de Tiempo"
    )

    selected_tf_label = st.selectbox(
        "Seleccionar Temporalidad:",
        list(TF_OPTIONS.keys()),
        index=2,
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

        lote_size = int(
            st.number_input(
                "Tamaño de Lote:",
                min_value=10,
                max_value=100,
                value=50,
                step=10,
            )
        )

        crypto_count = len(
            st.session_state[
                "crypto_list"
            ]
        )

        total_lotes = max(
            1,
            (
                crypto_count
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
                f"Lote {x + 1}",
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

            start = (
                batch_idx
                *
                lote_size
            )

            end = (
                start
                +
                lote_size
            )

            subset = (
                st.session_state[
                    "crypto_list"
                ][start:end]
            )


            if not subset:

                st.warning(
                    "El lote seleccionado está vacío."
                )

            else:

                prog = st.progress(0)

                for i, sym in enumerate(
                    subset
                ):

                    try:

                        prog.progress(
                            (i + 1)
                            /
                            len(subset),

                            text=(
                                f"Auditando "
                                f"{selected_tf_label}: "
                                f"{sym}"
                            ),
                        )


                        # ------------------------------------
                        # DATOS
                        # ------------------------------------

                        raw_data = (
                            ex.fetch_ohlcv(
                                sym,
                                timeframe=selected_tf_code,
                                limit=1000,
                            )
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
                                "vol",
                            ],
                        )

                        df["time"] = pd.to_datetime(
                            df["time"],
                            unit="ms"
                        )

                        df.set_index(
                            "time",
                            inplace=True
                        )


                        # ------------------------------------
                        # INDICADORES
                        # ------------------------------------

                        data = (
                            get_sly_indicators(
                                df
                            )
                        )

                        if data.empty:
                            continue


                        # ------------------------------------
                        # MACD MENSUAL
                        # ------------------------------------

                        monthly_force = (
                            get_monthly_macd_force(
                                ex,
                                sym
                            )
                        )


                        # ------------------------------------
                        # SEÑAL ORIGINAL
                        # ------------------------------------

                        (
                            sig_date,
                            sig_px,
                            vigente,
                            verd,
                        ) = find_last_signal(
                            data,
                            bear_longs
                        )


                        # ------------------------------------
                        # PNL
                        # ------------------------------------

                        if (
                            vigente
                            and
                            sig_px is not None
                            and
                            sig_px != 0
                        ):

                            pnl_val = (
                                (
                                    (
                                        data[
                                            "Close"
                                        ].iloc[-1]
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


                        # ------------------------------------
                        # RSI PRO
                        # ------------------------------------

                        last_rsi = float(
                            data[
                                "rsi_smooth"
                            ].iloc[-1]
                        )

                        previous_rsi = float(
                            data[
                                "rsi_smooth"
                            ].iloc[-2]
                        )

                        rsi_color = str(
                            data[
                                "rsi_pro_color"
                            ].iloc[-1]
                        )

                        rsi_green = (
                            rsi_color
                            ==
                            "VERDE"
                        )

                        alpha = bool(
                            data[
                                "alpha_strike"
                            ].iloc[-1]
                        )

                        exhaustion = bool(
                            data[
                                "exhaustion"
                            ].iloc[-1]
                        )

                        vol_z = float(
                            data[
                                "vol_z"
                            ].iloc[-1]
                        )


                        # ------------------------------------
                        # TEXTO RSI PRO
                        # ------------------------------------

                        if rsi_color == "VERDE":

                            rsi_pro_text = (
                                "🟢 VERDE"
                            )

                        elif (
                            rsi_color
                            ==
                            "VERDE OSCURO"
                        ):

                            rsi_pro_text = (
                                "🟩 VERDE OSCURO"
                            )

                        elif rsi_color == "ROJO":

                            rsi_pro_text = (
                                "🔴 ROJO"
                            )

                        elif (
                            rsi_color
                            ==
                            "ROJO OSCURO"
                        ):

                            rsi_pro_text = (
                                "🟥 ROJO OSCURO"
                            )

                        else:

                            rsi_pro_text = (
                                "⚪ NEUTRO"
                            )


                        # ------------------------------------
                        # ALERTA
                        # ------------------------------------

                        if (
                            rsi_green
                            and
                            alpha
                        ):

                            alert = (
                                "🔥🟢 VERDE + ALPHA"
                            )

                        elif rsi_green:

                            alert = (
                                "🟢 RSI PRO VERDE"
                            )

                        elif exhaustion:

                            alert = (
                                "⚠️ EXHAUSTION"
                            )

                        else:

                            alert = "-"


                        # ------------------------------------
                        # ZONA RSI
                        # ------------------------------------

                        if last_rsi > 50:

                            rsi_zone = (
                                "SOBRE 50 🟢"
                            )

                        else:

                            rsi_zone = (
                                "BAJO 50 🔴"
                            )


                        # ------------------------------------
                        # GUARDAR
                        # ------------------------------------

                        st.session_state[
                            "master_results_crypto"
                        ][sym] = {

                            "Activo":
                                sym.replace(
                                    "/USDT",
                                    ""
                                ),

                            "Sector":
                                get_crypto_sector(
                                    sym
                                ),

                            "Temporalidad":
                                selected_tf_label,

                            "RSI PRO":
                                rsi_pro_text,

                            "Alerta RSI":
                                alert,

                            "Alpha Strike":
                                (
                                    "🔥 SI"
                                    if alpha
                                    else "-"
                                ),

                            "Exhaustion":
                                (
                                    "⚠️ SI"
                                    if exhaustion
                                    else "-"
                                ),

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

                            "Vol Z":
                                round(
                                    vol_z,
                                    2
                                ),

                            "Banda Superior":
                                round(
                                    float(
                                        data[
                                            "upper_band"
                                        ].iloc[-1]
                                    ),
                                    2
                                ),

                            "Banda Inferior":
                                round(
                                    float(
                                        data[
                                            "lower_band"
                                        ].iloc[-1]
                                    ),
                                    2
                                ),

                            "MACD Mensual":
                                monthly_force,

                            "Última Señal":
                                (
                                    sig_date.strftime(
                                        "%d/%m %H:%M"
                                    )
                                    if sig_date
                                    is not None
                                    else "-"
                                ),

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

                            "Zona RSI":
                                rsi_zone,

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
                                ),
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


# ============================================================
# RESULTADOS
# ============================================================

if st.session_state[
    "master_results_crypto"
]:

    df_full = pd.DataFrame(
        st.session_state[
            "master_results_crypto"
        ].values()
    )


    # ========================================================
    # ALERTAS
    # ========================================================

    green_df = df_full[
        df_full["RSI PRO"]
        ==
        "🟢 VERDE"
    ]

    alpha_df = df_full[
        df_full["Alpha Strike"]
        ==
        "🔥 SI"
    ]

    exhaustion_df = df_full[
        df_full["Exhaustion"]
        ==
        "⚠️ SI"
    ]


    # ========================================================
    # RSI VERDE
    # ========================================================

    if not green_df.empty:

        assets = ", ".join(
            [
                (
                    f"{row['Activo']} "
                    f"{row['Temporalidad']} "
                    f"(RSI {row['RSI']:.2f})"
                )
                for _, row
                in green_df.iterrows()
            ]
        )

        st.markdown(
            f"""
            <div class="alert-green">
            🟢 RSI PRO VERDE DETECTADO:
            {assets}
            </div>
            """,
            unsafe_allow_html=True,
        )


    # ========================================================
    # ALPHA STRIKE
    # ========================================================

    if not alpha_df.empty:

        assets = ", ".join(
            [
                (
                    f"{row['Activo']} "
                    f"{row['Temporalidad']}"
                )
                for _, row
                in alpha_df.iterrows()
            ]
        )

        st.markdown(
            f"""
            <div class="alert-alpha">
            🔥 ALPHA STRIKE:
            {assets}
            </div>
            """,
            unsafe_allow_html=True,
        )


    # ========================================================
    # EXHAUSTION
    # ========================================================

    if not exhaustion_df.empty:

        assets = ", ".join(
            [
                (
                    f"{row['Activo']} "
                    f"{row['Temporalidad']}"
                )
                for _, row
                in exhaustion_df.iterrows()
            ]
        )

        st.markdown(
            f"""
            <div class="alert-exhaustion">
            ⚠️ EXHAUSTION:
            {assets}
            </div>
            """,
            unsafe_allow_html=True,
        )


    # ========================================================
    # RESUMEN SECTORIAL
    # ========================================================

    df_vigentes = df_full[
        df_full["Estado"]
        ==
        "VIGENTE 🟢"
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

            with cols[
                idx % 3
            ]:

                st.markdown(
                    f"""
                    <div class="sector-box">
                        <div class="sector-title">
                            {row['Sector']}: {len(row['Activo'])}
                        </div>
                        <div style="font-size: 0.85em;">
                            {', '.join(row['Activo'])}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    else:

        st.warning(
            "Sin posiciones abiertas en "
            "la temporalidad analizada."
        )


    # ========================================================
    # MATRIZ
    # ========================================================

    st.subheader(
        f"📋 Matriz de Señales "
        f"(Filtro Actual: {selected_tf_label})"
    )


    cols_order = [

        "Activo",
        "Sector",
        "Temporalidad",

        "RSI PRO",
        "Alerta RSI",
        "Alpha Strike",
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
        "Régimen",
    ]


    df_res = df_full[
        cols_order
    ].sort_values(
        by=["Activo"],
        ascending=[True],
    )


    # ========================================================
    # COLORES
    # ========================================================

    def color_cells(val):

        text = str(val)


        if (
            "VERDE + ALPHA"
            in text
            or
            "ALPHA"
            in text
        ):

            return (
                "background-color: #FFF3CD; "
                "color: #7A4F00; "
                "font-weight: bold;"
            )


        if (
            "🟢 VERDE"
            in text
            or
            "RSI PRO VERDE"
            in text
        ):

            return (
                "background-color: #C8E6C9; "
                "color: #1B5E20; "
                "font-weight: bold;"
            )


        if "VERDE OSCURO" in text:

            return (
                "background-color: #DCEDC8; "
                "color: #33691E; "
                "font-weight: bold;"
            )


        if (
            "EXHAUSTION"
            in text
            or
            "PIERDE FUERZA"
            in text
        ):

            return (
                "background-color: #FFF9C4; "
                "color: #827717; "
                "font-weight: bold;"
            )


        if (
            "ROJO"
            in text
            or
            "CERRADA"
            in text
            or
            "CERRAR"
            in text
            or
            "BAJISTA"
            in text
            or
            "BAJO 50"
            in text
            or
            "PERDIENDO"
            in text
        ):

            return (
                "background-color: #FFCDD2; "
                "color: #B71C1C; "
                "font-weight: bold;"
            )


        if (
            "VIGENTE"
            in text
            or
            "MANTENER"
            in text
            or
            "ALCISTA"
            in text
            or
            "SOBRE 50"
            in text
            or
            "GANANDO"
            in text
        ):

            return (
                "background-color: #C8E6C9; "
                "color: #1B5E20; "
                "font-weight: bold;"
            )


        return ""


    st.dataframe(
        df_res.style.map(color_cells),
        use_container_width=True,
        height=650,
    )


    # ========================================================
    # RESUMEN RSI PRO
    # ========================================================

    st.subheader(
        "🎯 RESUMEN RSI PRO"
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "🟢 RSI VERDE",
        len(green_df)
    )

    c2.metric(
        "🔥 ALPHA STRIKE",
        len(alpha_df)
    )

    c3.metric(
        "⚠️ EXHAUSTION",
        len(exhaustion_df)
    )

    c4.metric(
        "Total analizados",
        len(df_full)
    )


else:

    st.info(
        "👈 Seleccione temporalidad, "
        "sincronice mercado y analice los lotes."
    )
```
