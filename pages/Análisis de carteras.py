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
        value='10, 10, 10, 10, 10, 10, 10, 30', 
        help="Si lo dejas vacío, se asigna el mismo peso a todos."
    )
    
    benchmark = st.selectbox(
        "Comparar contra:", 
        ['SPY', 'QQQ', 'DIA', 'VT', 'BTC-USD', 'IWM', 'GLD']
    )
    
    anios = st.slider("Historial Máximo (Años):", 1, 20, 10)
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

        pesos = pesos / pesos.sum() # Normalizar

        # Descarga
        with st.spinner("Analizando mercado..."):
            try:
                # Descargamos todo
                data = yf.download(tickers + [benchmark], period=f"{anios}y", progress=False, auto_adjust=True)
                
                if isinstance(data.columns, pd.MultiIndex):
                    try: precios = data["Close"]
                    except: precios = data
                else:
                    precios = data["Close"] if "Close" in data else data

                # === CORRECCIÓN INTELIGENTE DE FECHAS ===
                # En lugar de dropna() ciego que borra todo si un activo es nuevo,
                # buscamos la fecha donde TODOS los activos ya tienen datos.
                
                start_date = precios.dropna().index[0]
                
                # Recortamos desde esa fecha
                precios = precios[precios.index >= start_date]
                returns = precios.pct_change().dropna()
                
                # Check de validez
                valid_tickers = [t for t in tickers if t in returns.columns]
                if not valid_tickers: st.error("Sin datos."); return
                
                # Aviso de recorte de historia
                real_years = (precios.index[-1] - precios.index[0]).days / 365.25
                if real_years < anios * 0.8:
                    st.warning(f"⚠️ Atención: Algunos activos son muy nuevos (ej: IBIT, ETHA). El análisis se recortó a los últimos **{real_years:.1f} años** disponibles para poder comparar todo junto.")
                
                # Reajuste de pesos
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
        
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("CAGR (Anual)", f"{cagr:.2%}", delta=f"{cagr-cagr_b:.2%}")
        k2.metric("Volatilidad", f"{vol:.2%}")
        k3.metric("Sharpe", f"{sharpe:.2f}")
        k4.metric("Beta", f"{beta:.2f}")

        # DIAGNÓSTICO
        st.divider()
        st.subheader("⚖️ Diagnóstico de Ponderación (Robo-Advisor)")
        
        col_diag1, col_diag2 = st.columns([1, 2])
        
        df_weights = pd.DataFrame({'Ticker': valid_tickers, 'Peso Actual': pesos})
        df_weights['Peso Ideal (Equi)'] = 1 / len(valid_tickers)
        
        alerts = []
        for i, row in df_weights.iterrows():
            if row['Peso Actual'] > 0.20: 
                alerts.append(f"🔴 **{row['Ticker']}** concentrado ({row['Peso Actual']:.1%}).")
            elif row['Peso Actual'] < 0.03:
                alerts.append(f"🟡 **{row['Ticker']}** irrelevante (<3%).")
        
        with col_diag1:
            if alerts:
                for a in alerts: st.markdown(a)
                st.info("Consejo: Mantén activos entre 5% y 15%.")
            else:
                st.success("✅ Excelente Balance.")
                
        with col_diag2:
            df_melt = df_weights.melt(id_vars='Ticker', value_vars=['Peso Actual', 'Peso Ideal (Equi)'], var_name='Tipo', value_name='Peso')
            fig_bal = px.bar(df_melt, x='Ticker', y='Peso', color='Tipo', barmode='group')
            st.plotly_chart(fig_bal, use_container_width=True)

        # GRÁFICO HISTÓRICO
        st.subheader("📈 Curva de Capital")
        df_chart = pd.DataFrame({"Mi Cartera": cum_port, benchmark: cum_bench})
        st.line_chart(df_chart)

        # CORRELACIÓN
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🍰 Composición")
            fig_pie = px.pie(df_weights, values='Peso Actual', names='Ticker', hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with c2:
            st.subheader("🔥 Mapa de Riesgo")
            corr = returns[valid_tickers].corr()
            fig_corr = px.imshow(corr, text_auto=".2f", color_continuous_scale="RdBu_r", zmin=-1, zmax=1)
            st.plotly_chart(fig_corr, use_container_width=True)
            
            pairs = []
            for i in range(len(valid_tickers)):
                for j in range(i+1, len(valid_tickers)):
                    if corr.iloc[i,j] > 0.85: pairs.append(f"{valid_tickers[i]}-{valid_tickers[j]}")
            
            if pairs: st.warning(f"⚠️ Activos Gemelos (>0.85): {', '.join(pairs)}")
            else: st.success("✅ Diversificación Eficiente")

if __name__ == "__main__":
    main()
