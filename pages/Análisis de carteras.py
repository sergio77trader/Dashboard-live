import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Portfolio Architect", layout="wide")

st.title("🏛️ Portfolio Architect: Análisis & Optimización")
st.markdown("Herramienta profesional para auditar y mejorar la estructura de tu cartera.")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("🏗️ Constructor de Cartera")
    
    tickers_str = st.text_area(
        "Activos (Tickers):", 
        value='JPM, GOLD, V, MRK, FXI, EWZ, KO, JD',
        height=100
    )
    
    pesos_str = st.text_area(
        "Pesos % (Opcional):", 
        value='10, 10, 10, 10, 10, 10, 10, 30', # Ejemplo desbalanceado para probar
        help="Si lo dejas vacío, se asigna el mismo peso a todos."
    )
    
    # Benchmark ampliado
    benchmark = st.selectbox(
        "Comparar contra:", 
        ['SPY', 'QQQ', 'DIA', 'VT', 'BTC-USD', 'IWM', 'GLD']
    )
    
    anios = st.slider("Historial (Años):", 1, 20, 10)
    calc_btn = st.button("🚀 AUDITAR CARTERA", type="primary")

# --- FUNCIONES ---
def convert_df_to_csv(df):
    return df.to_csv(index=True).encode('utf-8')

def main():
    if calc_btn:
        tickers = [t.strip().upper() for t in tickers_str.split(",") if t.strip()]
        if not tickers:
            st.error("Ingresa tickers."); return

        # Procesar Pesos
        if pesos_str.strip():
            try:
                raw_pesos = [float(p) for p in pesos_str.split(",")]
                if len(raw_pesos) != len(tickers):
                    st.error(f"Error: {len(tickers)} activos vs {len(raw_pesos)} pesos.")
                    return
                pesos = np.array(raw_pesos)
            except: st.error("Error en formato de pesos."); return
        else:
            pesos = np.ones(len(tickers)) / len(tickers)

        pesos = pesos / pesos.sum() # Normalizar al 100%

        # Descarga
        with st.spinner("Analizando mercado..."):
            try:
                data = yf.download(tickers + [benchmark], period=f"{anios}y", progress=False, auto_adjust=True)
                
                if isinstance(data.columns, pd.MultiIndex):
                    try: precios = data["Close"]
                    except: precios = data
                else:
                    precios = data["Close"] if "Close" in data else data

                precios = precios.dropna()
                returns = precios.pct_change().dropna()
                
                valid_tickers = [t for t in tickers if t in returns.columns]
                if not valid_tickers: st.error("Sin datos."); return
                
                # Reajuste de pesos si falló alguno
                if len(valid_tickers) < len(tickers):
                    st.warning("Algunos tickers no se encontraron. Re-equiponderando...")
                    pesos = np.ones(len(valid_tickers)) / len(valid_tickers)

            except Exception as e: st.error(f"Error: {e}"); return

        # Cálculos
        ret_port = returns[valid_tickers].dot(pesos)
        cum_port = (1 + ret_port).cumprod() * 100
        cum_bench = (1 + returns[benchmark]).cumprod() * 100

        # Métricas
        cov = np.cov(ret_port, returns[benchmark])[0,1]
        var = np.var(returns[benchmark])
        beta = cov / var
        vol = ret_port.std() * np.sqrt(252)
        sharpe = (ret_port.mean() * 252) / (ret_port.std() * np.sqrt(252))
        
        days = (cum_port.index[-1] - cum_port.index[0]).days
        years = days / 365.25
        cagr = (cum_port.iloc[-1]/100)**(1/years) - 1
        cagr_b = (cum_bench.iloc[-1]/100)**(1/years) - 1

        # --- VISUALIZACIÓN ---
        
        # 1. KPIs
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("CAGR (Anual)", f"{cagr:.2%}", delta=f"{cagr-cagr_b:.2%}")
        k2.metric("Volatilidad", f"{vol:.2%}")
        k3.metric("Sharpe", f"{sharpe:.2f}")
        k4.metric("Beta", f"{beta:.2f}")

        # 2. DIAGNÓSTICO DE PONDERACIÓN (NUEVO)
        st.divider()
        st.subheader("⚖️ Diagnóstico de Ponderación (Robo-Advisor)")
        
        col_diag1, col_diag2 = st.columns([1, 2])
        
        # Detectar Desbalances
        df_weights = pd.DataFrame({'Ticker': valid_tickers, 'Peso Actual': pesos})
        df_weights['Peso Ideal (Equi)'] = 1 / len(valid_tickers)
        df_weights['Desvío'] = df_weights['Peso Actual'] - df_weights['Peso Ideal (Equi)']
        
        alerts = []
        for i, row in df_weights.iterrows():
            if row['Peso Actual'] > 0.20: # Alerta si > 20%
                alerts.append(f"🔴 **{row['Ticker']}** tiene demasiada concentración ({row['Peso Actual']:.1%}). Riesgo alto.")
            elif row['Peso Actual'] < 0.03:
                alerts.append(f"🟡 **{row['Ticker']}** es irrelevante (<3%). Considera vender o aumentar.")
        
        with col_diag1:
            if alerts:
                for a in alerts: st.markdown(a)
                st.info("💡 **Consejo:** Ningún activo debería superar el 15-20% para una diversificación real.")
            else:
                st.success("✅ **Excelente Balance:** Ningún activo domina peligrosamente la cartera.")
                
        with col_diag2:
            # Gráfico de Barras: Actual vs Ideal
            df_melt = df_weights.melt(id_vars='Ticker', value_vars=['Peso Actual', 'Peso Ideal (Equi)'], var_name='Tipo', value_name='Peso')
            fig_bal = px.bar(df_melt, x='Ticker', y='Peso', color='Tipo', barmode='group', title="Tu Cartera vs. Cartera Equilibrada")
            st.plotly_chart(fig_bal, use_container_width=True)

        # 3. GRÁFICO HISTÓRICO
        st.subheader("📈 Curva de Capital")
        df_chart = pd.DataFrame({"Mi Cartera": cum_port, benchmark: cum_bench})
        st.line_chart(df_chart)

        # 4. CORRELACIÓN Y COMPOSICIÓN
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🍰 Composición Actual")
            fig_pie = px.pie(df_weights, values='Peso Actual', names='Ticker', hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with c2:
            st.subheader("🔥 Mapa de Riesgo (Correlación)")
            corr = returns[valid_tickers].corr()
            fig_corr = px.imshow(corr, text_auto=".2f", color_continuous_scale="RdBu_r", zmin=-1, zmax=1)
            st.plotly_chart(fig_corr, use_container_width=True)
            
            # Alerta de Correlación
            pairs = []
            for i in range(len(valid_tickers)):
                for j in range(i+1, len(valid_tickers)):
                    if corr.iloc[i,j] > 0.85: pairs.append(f"{valid_tickers[i]}-{valid_tickers[j]}")
            
            if pairs: st.warning(f"⚠️ Activos Gemelos (>0.85 corr): {', '.join(pairs)}")
            else: st.success("✅ Diversificación Eficiente")

if __name__ == "__main__":
    main()
