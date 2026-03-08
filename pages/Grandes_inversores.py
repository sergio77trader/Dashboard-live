import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

st.set_page_config(page_title="Hedge Fund Tracker", layout="wide")

st.title("📊 Hedge Fund Tracker")
st.write("Seguimiento de inversiones de grandes inversores")

# Carteras ejemplo
portfolios = {
    "Warren Buffett": {
        "empresa": ["Apple", "Bank of America", "American Express", "Coca Cola", "Chevron"],
        "ticker": ["AAPL", "BAC", "AXP", "KO", "CVX"],
        "peso": [40, 10, 8, 7, 6]
    },
    "Bill Ackman": {
        "empresa": ["Google", "Chipotle", "Hilton", "Lowe's"],
        "ticker": ["GOOGL", "CMG", "HLT", "LOW"],
        "peso": [30, 25, 25, 20]
    },
    "Ray Dalio": {
        "empresa": ["SPY ETF", "Gold ETF", "Emerging Markets ETF"],
        "ticker": ["SPY", "GLD", "EEM"],
        "peso": [50, 25, 25]
    }
}

investor = st.sidebar.selectbox(
    "Seleccionar inversor",
    list(portfolios.keys())
)

data = portfolios[investor]

df = pd.DataFrame({
    "Empresa": data["empresa"],
    "Ticker": data["ticker"],
    "Peso %": data["peso"]
})

# Obtener precios
prices = []

for ticker in df["Ticker"]:
    try:
        stock = yf.Ticker(ticker)
        price = stock.history(period="1d")["Close"].iloc[-1]
        prices.append(round(price,2))
    except:
        prices.append(None)

df["Precio USD"] = prices

# Layout
col1, col2 = st.columns(2)

with col1:
    st.subheader("Portfolio")
    st.dataframe(df)

with col2:
    st.subheader("Distribución")
    fig = px.pie(df, values="Peso %", names="Empresa")
    st.plotly_chart(fig)

# Consenso entre fondos
st.subheader("Acciones más repetidas")

all_tickers = []

for p in portfolios.values():
    all_tickers += p["ticker"]

consensus = pd.Series(all_tickers).value_counts().reset_index()
consensus.columns = ["Ticker", "Cantidad de fondos"]

st.dataframe(consensus)

fig2 = px.bar(consensus, x="Ticker", y="Cantidad de fondos")
st.plotly_chart(fig2)
