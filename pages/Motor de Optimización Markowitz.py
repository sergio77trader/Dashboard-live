import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.optimize import minimize

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE LA PÁGINA DE OPTIMIZACIÓN
# ─────────────────────────────────────────────
def run_markowitz_optimizer(selected_tickers):
    st.header("📈 Optimizador de Cartera Markowitz")
    
    if len(selected_tickers) < 2:
        st.warning("Selecciona al menos 2 activos para optimizar.")
        return

    # Parámetros de tiempo
    years = st.slider("Años de historia para el análisis:", 1, 10, 3)
    
    # 1. DESCARGA DE DATOS
    @st.cache_data
    def get_hist_data(tickers, period):
        data = yf.download(tickers, period=f"{period}y")['Close']
        return data

    data = get_hist_data(selected_tickers, years)
    
    if data.empty:
        st.error("No se pudieron obtener datos.")
        return

    # 2. CÁLCULOS FINANCIEROS
    returns = data.pct_change().dropna()
    mean_returns = returns.mean() * 252 # Anualizado
    cov_matrix = returns.cov() * 252    # Anualizado

    # 3. FUNCIONES DE OPTIMIZACIÓN
    def portfolio_performance(weights, mean_returns, cov_matrix):
        returns = np.sum(mean_returns * weights)
        std = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        return returns, std

    # Maximizar Sharpe Ratio (Minimizar el negativo del Sharpe)
    def neg_sharpe_ratio(weights, mean_returns, cov_matrix, risk_free_rate=0.04):
        p_ret, p_std = portfolio_performance(weights, mean_returns, cov_matrix)
        return -(p_ret - risk_free_rate) / p_std

    # Restricciones: la suma de pesos es 1 y pesos entre 0 y 1 (sin cortos)
    constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
    bounds = tuple((0, 1) for _ in range(len(selected_tickers)))
    init_guess = len(selected_tickers) * [1. / len(selected_tickers)]

    # 4. EJECUCIÓN DE LA OPTIMIZACIÓN
    opt_results = minimize(neg_sharpe_ratio, init_guess, 
                           args=(mean_returns, cov_matrix), 
                           method='SLSQP', bounds=bounds, constraints=constraints)
    
    opt_weights = opt_results.x
    opt_ret, opt_std = portfolio_performance(opt_weights, mean_returns, cov_matrix)

    # 5. SIMULACIÓN DE MONTE CARLO (Para dibujar la nube de puntos)
    num_portfolios = 1000
    all_weights = np.zeros((num_portfolios, len(selected_tickers)))
    ret_arr = np.zeros(num_portfolios)
    std_arr = np.zeros(num_portfolios)

    for i in range(num_portfolios):
        weights = np.array(np.random.random(len(selected_tickers)))
        weights = weights / np.sum(weights)
        all_weights[i,:] = weights
        ret_arr[i], std_arr[i] = portfolio_performance(weights, mean_returns, cov_matrix)

    # 6. VISUALIZACIÓN: FRONTERA EFICIENTE
    fig = go.Figure()
    # Nube de carteras
    fig.add_trace(go.Scatter(x=std_arr, y=ret_arr, mode='markers',
        marker=dict(color=(ret_arr - 0.04) / std_arr, colorscale='Viridis', showscale=True, title="Sharpe"),
        name="Carteras Aleatorias"))
    # Cartera Óptima
    fig.add_trace(go.Scatter(x=[opt_std], y=[opt_ret], mode='markers',
        marker=dict(color='red', size=15, symbol='star'),
        name="Máximo Sharpe (Markowitz)"))

    fig.update_layout(title="Frontera Eficiente", xaxis_title="Riesgo (Volatilidad)", yaxis_title="Retorno Anualizado")
    st.plotly_chart(fig, use_container_width=True)

    # 7. RESULTADOS DE PESOS
    st.subheader("🎯 Asignación Óptima de Capital")
    weights_df = pd.DataFrame({
        'Activo': selected_tickers,
        'Peso (%)': [round(w * 100, 2) for w in opt_weights]
    }).sort_values(by='Peso (%)', ascending=False)
    
    c1, c2 = st.columns(2)
    with c1:
        st.write(weights_df)
    with c2:
        st.metric("Retorno Esperado Anual", f"{round(opt_ret*100, 2)}%")
        st.metric("Volatilidad Esperada", f"{round(opt_std*100, 2)}%")
        st.metric("Sharpe Ratio", round((opt_ret - 0.04) / opt_std, 2))

# ─────────────────────────────────────────────
# INTEGRACIÓN EN TU SIDEBAR EXISTENTE
# ─────────────────────────────────────────────
# Puedes añadir esto en tu sidebar para elegir los activos:
with st.sidebar:
    st.divider()
    st.header("🧪 Lab Markowitz")
    selected_for_opt = st.multiselect("Activos para optimizar:", MASTER_TICKERS, default=["BTC-USD", "SPY", "GLD", "AAPL"])
    if st.button("Calcular Cartera Óptima"):
        run_markowitz_optimizer(selected_for_opt)
