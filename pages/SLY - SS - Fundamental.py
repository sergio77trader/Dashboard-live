import os
import time
import math
import warnings
from datetime import datetime

import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")


# ============================================================
# CONFIGURACIÓN
# ============================================================

MIN_MARKET_CAP = 10_000_000_000       # USD 10B
MIN_PRICE = 10

MAX_PE = 35
MAX_FORWARD_PE = 25
MAX_PEG = 1.50
MAX_PFCF = 35

MIN_EPS_GROWTH_5Y = 10
MIN_EPS_GROWTH_NEXT_5Y = 10
MIN_EPS_GROWTH_NEXT_Y = 10
MIN_EPS_GROWTH_QQ = 10

MIN_SALES_GROWTH_5Y = 5
MIN_SALES_GROWTH_QQ = 5

MIN_ROE = 15
MIN_ROIC = 10
MIN_OPERATING_MARGIN = 15
MIN_PROFIT_MARGIN = 10
MIN_GROSS_MARGIN = 30

MAX_DEBT_EQUITY = 2.0

# Cantidad de empresas a analizar
MAX_TICKERS = 1000

# Pausa entre acciones para evitar demasiadas solicitudes
REQUEST_DELAY = 0.15


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def clean_number(value):
    """Convierte valores a float cuando sea posible."""
    try:
        if value is None:
            return np.nan

        value = float(value)

        if math.isnan(value) or math.isinf(value):
            return np.nan

        return value

    except Exception:
        return np.nan


def percent(value):
    """
    Convierte ratios decimales a porcentaje.
    Ejemplo: 0.25 -> 25
    """
    value = clean_number(value)

    if pd.isna(value):
        return np.nan

    if abs(value) <= 2:
        return value * 100

    return value


def get_value(dictionary, *keys):
    """Busca la primera clave disponible."""
    for key in keys:
        if key in dictionary:
            return dictionary[key]

    return np.nan


def safe_row(df, names):
    """
    Obtiene la fila disponible de un DataFrame financiero.
    """
    if df is None or df.empty:
        return None

    for name in names:
        if name in df.index:
            row = df.loc[name]

            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]

            return row

    return None


def latest_value(df, names):
    """
    Obtiene el último valor disponible de una fila financiera.
    """
    row = safe_row(df, names)

    if row is None:
        return np.nan

    values = row.dropna()

    if len(values) == 0:
        return np.nan

    return clean_number(values.iloc[0])


def growth_from_series(df, names, periods=4):
    """
    Calcula crecimiento histórico aproximado utilizando estados financieros.
    """
    row = safe_row(df, names)

    if row is None:
        return np.nan

    values = row.dropna()

    if len(values) < periods + 1:
        return np.nan

    try:
        latest = float(values.iloc[0])
        old = float(values.iloc[periods])

        if old == 0:
            return np.nan

        return ((latest / old) ** (1 / periods) - 1) * 100

    except Exception:
        return np.nan


# ============================================================
# SCORE
# ============================================================

def score_company(data):
    """
    Quality Growth Score 0-100.
    """

    score = 0

    # --------------------------------------------------------
    # CRECIMIENTO - 30 puntos
    # --------------------------------------------------------

    eps5 = data["EPS Growth 5Y"]
    eps_next = data["EPS Growth Next 5Y"]
    sales = data["Sales Growth 5Y"]

    if not pd.isna(eps5):
        if eps5 >= 20:
            score += 10
        elif eps5 >= 10:
            score += 7
        elif eps5 > 0:
            score += 3

    if not pd.isna(eps_next):
        if eps_next >= 20:
            score += 10
        elif eps_next >= 10:
            score += 7
        elif eps_next > 0:
            score += 3

    if not pd.isna(sales):
        if sales >= 15:
            score += 10
        elif sales >= 5:
            score += 7
        elif sales > 0:
            score += 3

    # --------------------------------------------------------
    # RENTABILIDAD - 25 puntos
    # --------------------------------------------------------

    roe = data["ROE"]
    roic = data["ROIC"]
    margin = data["Operating Margin"]

    if not pd.isna(roe):
        if roe >= 25:
            score += 9
        elif roe >= 15:
            score += 6
        elif roe > 0:
            score += 2

    if not pd.isna(roic):
        if roic >= 20:
            score += 9
        elif roic >= 10:
            score += 6
        elif roic > 0:
            score += 2

    if not pd.isna(margin):
        if margin >= 25:
            score += 7
        elif margin >= 15:
            score += 5
        elif margin > 0:
            score += 2

    # --------------------------------------------------------
    # VALUACIÓN - 30 puntos
    # --------------------------------------------------------

    peg = data["PEG"]
    fwd_pe = data["Forward PE"]
    pfcf = data["P/FCF"]

    if not pd.isna(peg):
        if peg <= 0.8:
            score += 12
        elif peg <= 1.0:
            score += 10
        elif peg <= 1.5:
            score += 7
        elif peg <= 2:
            score += 3

    if not pd.isna(fwd_pe):
        if fwd_pe <= 15:
            score += 10
        elif fwd_pe <= 20:
            score += 8
        elif fwd_pe <= 25:
            score += 5
        elif fwd_pe <= 35:
            score += 2

    if not pd.isna(pfcf):
        if pfcf <= 20:
            score += 8
        elif pfcf <= 30:
            score += 5
        elif pfcf <= 35:
            score += 2

    # --------------------------------------------------------
    # DEUDA - 15 puntos
    # --------------------------------------------------------

    debt = data["Debt/Equity"]

    if not pd.isna(debt):
        if debt <= 0.5:
            score += 15
        elif debt <= 1:
            score += 12
        elif debt <= 2:
            score += 8
        elif debt <= 3:
            score += 3

    return min(score, 100)


# ============================================================
# ANALIZAR UNA EMPRESA
# ============================================================

def analyze_ticker(symbol):

    try:

        print(f"Analizando {symbol}...")

        ticker = yf.Ticker(symbol)

        info = ticker.info

        if not info:
            return None

        price = clean_number(
            get_value(
                info,
                "currentPrice",
                "regularMarketPrice"
            )
        )

        market_cap = clean_number(
            get_value(
                info,
                "marketCap"
            )
        )

        # ----------------------------------------------------
        # VALUACIÓN
        # ----------------------------------------------------

        pe = clean_number(
            get_value(
                info,
                "trailingPE"
            )
        )

        forward_pe = clean_number(
            get_value(
                info,
                "forwardPE"
            )
        )

        peg = clean_number(
            get_value(
                info,
                "pegRatio"
            )
        )

        pfcf = clean_number(
            get_value(
                info,
                "priceToFreeCashflow"
            )
        )

        ev_ebitda = clean_number(
            get_value(
                info,
                "enterpriseToEbitda"
            )
        )

        # ----------------------------------------------------
        # CRECIMIENTO
        # ----------------------------------------------------

        eps_growth_5y = percent(
            get_value(
                info,
                "earningsGrowth"
            )
        )

        eps_growth_next_y = percent(
            get_value(
                info,
                "earningsQuarterlyGrowth"
            )
        )

        eps_growth_next_5y = np.nan

        try:
            growth = ticker.growth_estimates

            if growth is not None and not growth.empty:

                # Intentar encontrar estimación 5Y
                possible_columns = [
                    "5Y",
                    "5y",
                    "Next 5Y"
                ]

                for col in possible_columns:

                    if col in growth.columns:

                        val = growth[col].iloc[0]

                        if not pd.isna(val):
                            eps_growth_next_5y = percent(val)
                            break

        except Exception:
            pass

        # ----------------------------------------------------
        # MÁRGENES
        # ----------------------------------------------------

        gross_margin = percent(
            get_value(
                info,
                "grossMargins"
            )
        )

        operating_margin = percent(
            get_value(
                info,
                "operatingMargins"
            )
        )

        profit_margin = percent(
            get_value(
                info,
                "profitMargins"
            )
        )

        # ----------------------------------------------------
        # ROE
        # ----------------------------------------------------

        roe = percent(
            get_value(
                info,
                "returnOnEquity"
            )
        )

        # ----------------------------------------------------
        # DEUDA
        # ----------------------------------------------------

        debt_equity = clean_number(
            get_value(
                info,
                "debtToEquity"
            )
        )

        # Yahoo normalmente devuelve Debt/Equity como porcentaje
        # Ej: 50 = 0.50x
        if not pd.isna(debt_equity):
            debt_equity = debt_equity / 100

        # ----------------------------------------------------
        # FREE CASH FLOW
        # ----------------------------------------------------

        free_cash_flow = clean_number(
            get_value(
                info,
                "freeCashflow"
            )
        )

        # ----------------------------------------------------
        # ROIC
        # ----------------------------------------------------

        roic = np.nan

        try:

            income = ticker.income_stmt
            balance = ticker.balance_sheet

            operating_income = latest_value(
                income,
                [
                    "Operating Income",
                    "OperatingIncome"
                ]
            )

            total_debt = latest_value(
                balance,
                [
                    "Total Debt",
                    "TotalDebt"
                ]
            )

            equity = latest_value(
                balance,
                [
                    "Stockholders Equity",
                    "StockholdersEquity"
                ]
            )

            cash = latest_value(
                balance,
                [
                    "Cash And Cash Equivalents",
                    "CashCashEquivalentsAndShortTermInvestments",
                    "Cash Financial"
                ]
            )

            if (
                not pd.isna(operating_income)
                and not pd.isna(equity)
            ):

                if pd.isna(total_debt):
                    total_debt = 0

                if pd.isna(cash):
                    cash = 0

                invested_capital = (
                    equity
                    + total_debt
                    - cash
                )

                if invested_capital > 0:

                    # Aproximación ROIC antes de impuestos.
                    roic = (
                        operating_income
                        / invested_capital
                    ) * 100

        except Exception:
            pass

        # ----------------------------------------------------
        # CRECIMIENTO DE VENTAS
        # ----------------------------------------------------

        sales_growth_5y = np.nan

        try:

            income = ticker.income_stmt

            sales_growth_5y = growth_from_series(
                income,
                [
                    "Total Revenue",
                    "TotalRevenue"
                ],
                periods=4
            )

        except Exception:
            pass

        # ----------------------------------------------------
        # CRECIMIENTO EPS Q/Q
        # ----------------------------------------------------

        eps_growth_qq = np.nan

        try:

            quarterly = ticker.quarterly_income_stmt

            net_income_latest = latest_value(
                quarterly,
                [
                    "Net Income",
                    "NetIncome"
                ]
            )

            net_income_previous = np.nan

            row = safe_row(
                quarterly,
                [
                    "Net Income",
                    "NetIncome"
                ]
            )

            if row is not None:

                values = row.dropna()

                if len(values) >= 2:

                    current = float(values.iloc[0])
                    previous = float(values.iloc[1])

                    if previous != 0:

                        eps_growth_qq = (
                            (current / previous) - 1
                        ) * 100

        except Exception:
            pass

        # ----------------------------------------------------
        # CAÍDA DESDE MÁXIMO 52 SEMANAS
        # ----------------------------------------------------

        high_52 = clean_number(
            get_value(
                info,
                "fiftyTwoWeekHigh"
            )
        )

        low_52 = clean_number(
            get_value(
                info,
                "fiftyTwoWeekLow"
            )
        )

        drawdown_52 = np.nan

        if (
            not pd.isna(price)
            and not pd.isna(high_52)
            and high_52 > 0
        ):

            drawdown_52 = (
                (price / high_52) - 1
            ) * 100

        # ----------------------------------------------------
        # RESULTADO
        # ----------------------------------------------------

        data = {

            "Ticker": symbol,

            "Price": price,

            "Market Cap": market_cap,

            "PE": pe,

            "Forward PE": forward_pe,

            "PEG": peg,

            "P/FCF": pfcf,

            "EV/EBITDA": ev_ebitda,

            "EPS Growth 5Y": eps_growth_5y,

            "EPS Growth Next 5Y": eps_growth_next_5y,

            "EPS Growth Next Y": eps_growth_next_y,

            "EPS Growth Q/Q": eps_growth_qq,

            "Sales Growth 5Y": sales_growth_5y,

            "Gross Margin": gross_margin,

            "Operating Margin": operating_margin,

            "Profit Margin": profit_margin,

            "ROE": roe,

            "ROIC": roic,

            "Debt/Equity": debt_equity,

            "Free Cash Flow": free_cash_flow,

            "52W Drawdown": drawdown_52,
        }

        # ----------------------------------------------------
        # SCORE
        # ----------------------------------------------------

        data["Quality Growth Score"] = score_company(data)

        # ----------------------------------------------------
        # FILTRO PRINCIPAL
        # ----------------------------------------------------

        data["PASS"] = True

        # Market Cap
        if not pd.isna(market_cap):
            if market_cap < MIN_MARKET_CAP:
                data["PASS"] = False

        # Precio
        if not pd.isna(price):
            if price < MIN_PRICE:
                data["PASS"] = False

        # P/E
        if not pd.isna(pe):
            if pe > MAX_PE:
                data["PASS"] = False

        # Forward P/E
        if not pd.isna(forward_pe):
            if forward_pe > MAX_FORWARD_PE:
                data["PASS"] = False

        # PEG
        if not pd.isna(peg):
            if peg > MAX_PEG or peg <= 0:
                data["PASS"] = False

        # Crecimiento EPS
        if not pd.isna(eps_growth_5y):
            if eps_growth_5y < MIN_EPS_GROWTH_5Y:
                data["PASS"] = False

        if not pd.isna(eps_growth_next_5y):
            if eps_growth_next_5y < MIN_EPS_GROWTH_NEXT_5Y:
                data["PASS"] = False

        # Ventas
        if not pd.isna(sales_growth_5y):
            if sales_growth_5y < MIN_SALES_GROWTH_5Y:
                data["PASS"] = False

        # Rentabilidad
        if not pd.isna(roe):
            if roe < MIN_ROE:
                data["PASS"] = False

        if not pd.isna(roic):
            if roic < MIN_ROIC:
                data["PASS"] = False

        if not pd.isna(operating_margin):
            if operating_margin < MIN_OPERATING_MARGIN:
                data["PASS"] = False

        if not pd.isna(profit_margin):
            if profit_margin < MIN_PROFIT_MARGIN:
                data["PASS"] = False

        # Deuda
        if not pd.isna(debt_equity):
            if debt_equity > MAX_DEBT_EQUITY:
                data["PASS"] = False

        return data

    except Exception as e:

        print(f"ERROR {symbol}: {e}")

        return None


# ============================================================
# CARGAR TICKERS
# ============================================================

def load_tickers():

    if not os.path.exists("tickers.txt"):

        print("No existe tickers.txt")

        return []

    with open(
        "tickers.txt",
        "r",
        encoding="utf-8"
    ) as file:

        tickers = []

        for line in file:

            symbol = line.strip().upper()

            if (
                symbol
                and not symbol.startswith("#")
            ):

                tickers.append(symbol)

    return tickers[:MAX_TICKERS]


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("QUALITY GROWTH STOCK SCREENER")
    print("=" * 70)

    print(
        "Fecha:",
        datetime.utcnow().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    tickers = load_tickers()

    print(
        f"Empresas a analizar: {len(tickers)}"
    )

    results = []

    for i, symbol in enumerate(tickers, 1):

        print(
            f"[{i}/{len(tickers)}] {symbol}"
        )

        data = analyze_ticker(symbol)

        if data is not None:

            results.append(data)

        time.sleep(REQUEST_DELAY)

    if not results:

        print("No se obtuvieron datos.")

        return

    df = pd.DataFrame(results)

    # Ordenar por Score
    df = df.sort_values(
        "Quality Growth Score",
        ascending=False
    )

    # --------------------------------------------------------
    # FORMATO
    # --------------------------------------------------------

    percentage_columns = [
        "EPS Growth 5Y",
        "EPS Growth Next 5Y",
        "EPS Growth Next Y",
        "EPS Growth Q/Q",
        "Sales Growth 5Y",
        "Gross Margin",
        "Operating Margin",
        "Profit Margin",
        "ROE",
        "ROIC",
        "52W Drawdown"
    ]

    for col in percentage_columns:

        if col in df.columns:

            df[col] = df[col].round(2)

    numeric_columns = [
        "Price",
        "PE",
        "Forward PE",
        "PEG",
        "P/FCF",
        "EV/EBITDA",
        "Debt/Equity",
        "Quality Growth Score"
    ]

    for col in numeric_columns:

        if col in df.columns:

            df[col] = df[col].round(2)

    # --------------------------------------------------------
    # GUARDAR TODOS
    # --------------------------------------------------------

    os.makedirs(
        "output",
        exist_ok=True
    )

    df.to_csv(
        "output/all_stocks.csv",
        index=False
    )

    # --------------------------------------------------------
    # GUARDAR SOLO LAS QUE PASAN
    # --------------------------------------------------------

    passed = df[
        df["PASS"] == True
    ].copy()

    passed.to_csv(
        "output/top_stocks.csv",
        index=False
    )

    # --------------------------------------------------------
    # TOP 50
    # --------------------------------------------------------

    top50 = passed.head(50)

    top50.to_csv(
        "output/top50.csv",
        index=False
    )

    # --------------------------------------------------------
    # JSON
    # --------------------------------------------------------

    top50.to_json(
        "output/top50.json",
        orient="records",
        indent=2
    )

    # --------------------------------------------------------
    # IMPRIMIR RESULTADO
    # --------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("TOP QUALITY GROWTH")
    print("=" * 70)

    columns_to_show = [
        "Ticker",
        "Price",
        "PE",
        "Forward PE",
        "PEG",
        "EPS Growth Next 5Y",
        "Sales Growth 5Y",
        "ROE",
        "ROIC",
        "52W Drawdown",
        "Quality Growth Score"
    ]

    print(
        top50[
            columns_to_show
        ].to_string(
            index=False
        )
    )

    print("\n")
    print(
        f"Empresas analizadas: {len(df)}"
    )

    print(
        f"Empresas que pasan: {len(passed)}"
    )

    print(
        "Archivo principal:"
        " output/top_stocks.csv"
    )

    print("=" * 70)


if __name__ == "__main__":
    main()
