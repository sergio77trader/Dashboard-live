import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Análisis de Carteras (Plotly)", layout="wide")

st.title("📊 Análisis Profesional de Carteras")
st.markdown("Adaptado para funcionar sin Seaborn ni dependencias externas de Excel.")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("Parámetros")
    
    tickers_str = st.text_area(
        "Tickers (separados por coma):", 
        value='JPM, GOLD, V, MRK, FXI, EWZ, KO',
        height=100
    )
    
    pesos_str = st.text_area(
        "Pesos % (opcional, separador por coma):", 
        value='10, 20, 20, 10, 10, 10, 20',
        help="Si se deja vacío, se equipondera."
    )
    
    benchmark = st.selectbox("Benchmark:", ['SPY', 'QQQ', 'DIA'], index=0)
    anios = st.slider("Años de historia:", 1, 20, 10)
    
    calc_btn = st.button("🚀 Calcular", type="primary")

# --- FUNCIONES ---
def convert_df_to_csv(df):
    return df.to_csv(index=True).encode('utf-8')

def main():
    if calc_btn:
        # 1. Procesar Inputs
        tickers = [t.strip().upper() for t in tickers_str.split(",") if t.strip()]
        
        if not tickers:
            st.error("Ingresa al menos un ticker.")
            return

        # Procesar Pesos
        if pesos_str.strip():
            try:
                pesos_list = [float(p) for p in pesos_str.split(",")]
                if len(pesos_list) != len(tickers):
                    st.error(f"Error: {len(tickers)} tickers vs {len(pesos_list)} pesos.")
                    return
                pesos = np.array(pesos_list)
            except:
                st.error("Error en formato de pesos.")
                return
        else:
            pesos = np.ones(len(tickers)) / len(tickers)

        # Normalizar al 100%
        pesos = pesos / pesos.sum()

        # 2. Descargar Datos
        with st.spinner("Descargando datos..."):
            activos = tickers + [benchmark]
            try:
                # Usamos yfinance
                data = yf.download(activos, period=f"{anios}y", progress=False, auto_adjust=True)
                
                # Manejo de estructura de datos (MultiIndex o simple)
                if isinstance(data.columns, pd.MultiIndex):
                    # Si bajamos más de 1 activo, yfinance devuelve MultiIndex
                    # Buscamos 'Close' si existe, sino tomamos todo (caso download auto-adjust=True a veces devuelve solo precio)
                    try:
                        precios = data["Close"]
                    except KeyError:
                        precios = data # A veces devuelve el DF directo si solo hay Close
                else:
                    precios = data["Close"] if "Close" in data else data

                # Limpiar y calcular retornos
                precios = precios.dropna()
                returns = precios.pct_change().dropna()

                if returns.empty:
                    st.error("No hay datos suficientes.")
                    return
                
                # Verificar que los tickers existan en las columnas descargadas
                # (A veces YF cambia el nombre, ej: BRK.B -> BRK-B)
                valid_tickers = [t for t in tickers if t in returns.columns]
                
                if not valid_tickers:
                    st.error("Ningún ticker válido encontrado en la descarga.")
                    return
                
                # Re-ajustar pesos si algún ticker falló
                if len(valid_tickers) < len(tickers):
                    st.warning(f"Tickers ignorados (sin datos): {set(tickers) - set(valid_tickers)}")
                    # Re-normalizar pesos para los validos (simple: equiponderar lo que queda o recortar)
                    # Para evitar errores matemáticos, aquí re-equiponderamos simple:
                    pesos = np.ones(len(valid_tickers)) / len(valid_tickers)
                    st.info("Se han re-calculado los pesos equitativamente entre los activos válidos.")

            except Exception as e:
                st.error(f"Error técnico: {e}")
                return

        # 3. Matemática Financiera
        # Retorno de la cartera (producto punto matriz retornos x pesos)
        ret_port = returns[valid_tickers].dot(pesos)
        
        # Series Acumuladas (Base 100 para graficar)
        cum_port = (1 + ret_port).cumprod() * 100
        cum_bench = (1 + returns[benchmark]).cumprod() * 100

        # Métricas
        # Beta
        cov = np.cov(ret_port, returns[benchmark])[0,1]
        var = np.var(returns[benchmark])
        beta = cov / var
        
        # Volatilidad Anual
        vol_port = ret_port.std() * np.sqrt(252)
        vol_bench = returns[benchmark].std() * np.sqrt(252)
        
        # Correlación Cartera vs Benchmark
        corr_bench = np.corrcoef(ret_port, returns[benchmark])[0,1]
        
        # CAGR
        days = (cum_port.index[-1] - cum_port.index[0]).days
        years = days / 365.25
        cagr_port = (cum_port.iloc[-1] / 100) ** (1/years) - 1
        cagr_bench = (cum_bench.iloc[-1] / 100) ** (1/years) - 1
        
        # Sharpe (asumiendo tasa libre riesgo 0 para simplificar)
        sharpe = (ret_port.mean() * 252) / (ret_port.std() * np.sqrt(252))

        # 4. Visualización
        
        # KPI ROW
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("CAGR (Anual)", f"{cagr_port:.2%}", delta=f"{cagr_port-cagr_bench:.2%}")
        k2.metric("Volatilidad", f"{vol_port:.2%}")
        k3.metric("Sharpe Ratio", f"{sharpe:.2f}")
        k4.metric("Beta", f"{beta:.2f}")

        # GRÁFICO DE LÍNEA (Plotly es mejor que st.line_chart)
        st.subheader("📈 Evolución Patrimonial (Base 100)")
        df_chart = pd.DataFrame({
            "Mi Cartera": cum_port,
            f"Benchmark ({benchmark})": cum_bench
        })
        
        fig_line = px.line(df_chart, title=f"Rendimiento Histórico ({years:.1f} años)")
        st.plotly_chart(fig_line, use_container_width=True)

        c1, c2 = st.columns(2)

        # GRÁFICO TORTA (Plotly)
        with c1:
            st.subheader("🍰 Composición")
            df_pie = pd.DataFrame({'Ticker': valid_tickers, 'Peso': pesos})
            fig_pie = px.pie(df_pie, values='Peso', names='Ticker', hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)

        # MATRIZ CORRELACIÓN (Plotly Heatmap en vez de Seaborn)
        with c2:
            st.subheader("🔥 Matriz de Correlación")
            corr_matrix = returns[valid_tickers].corr()
            
            fig_heat = px.imshow(
                corr_matrix,
                text_auto=".2f", # Muestra los números
                aspect="auto",
                color_continuous_scale="RdBu_r", # Rojo a Azul
                zmin=-1, zmax=1
            )
            st.plotly_chart(fig_heat, use_container_width=True)

        # ALERTA DE CORRELACIÓN
        high_corr = []
        for i in range(len(valid_tickers)):
            for j in range(i+1, len(valid_tickers)):
                val = corr_matrix.iloc[i,j]
                if val > 0.85:
                    high_corr.append(f"{valid_tickers[i]} - {valid_tickers[j]} ({val:.2f})")
        
        if high_corr:
            st.warning(f"⚠️ **Alerta de Diversificación:** Pares con correlación > 0.85:\n\n" + ", ".join(high_corr))
        else:
            st.success("✅ **Cartera bien diversificada:** No hay correlaciones extremas entre activos.")

        # DESCARGA DATOS (CSV)
        st.divider()
        csv_data = convert_df_to_csv(df_chart)
        st.download_button(
            label="📥 Descargar Datos Históricos (CSV)",
            data=csv_data,
            file_name="backtest_cartera.csv",
            mime="text/csv"
        )

if __name__ == "__main__":
    main()
