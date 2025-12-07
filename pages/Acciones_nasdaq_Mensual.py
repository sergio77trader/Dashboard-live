import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SystemaTrader - Radar Risk/Reward")

# --- DATOS (UNIVERSO Y SECTORES) ---
CEDEAR_UNIVERSE = {
    'AAPL', 'MSFT', 'NVDA', 'AVGO', 'ADBE', 'CRM', 'AMD', 'INTC', 'CSCO', 'ORCL',
    'BRK-B', 'JPM', 'V', 'MA', 'BAC', 'WFC', 'MS', 'GS', 'BLK', 'C',
    'LLY', 'UNH', 'JNJ', 'MRK', 'ABBV', 'TMO', 'PFE', 'ABT', 'AMGN', 'DHR',
    'AMZN', 'TSLA', 'HD', 'MCD', 'NKE', 'LOW', 'SBUX', 'TJX', 'BKNG', 'F',
    'PG', 'COST', 'PEP', 'KO', 'WMT', 'PM', 'MDLZ', 'MO', 'CL', 'TGT',
    'XOM', 'CVX', 'EOG', 'SLB', 'OXY', 'HES', 'VLO',
    'GE', 'CAT', 'BA', 'DE', 'LMT', 'RTX', 'MMM', 'HON', 'UPS', 'UNP',
    'LIN', 'FCX', 'NEM', 'DOW', 'DD',
    'GOOGL', 'META', 'NFLX', 'DIS', 'VZ', 'T', 'TMUS',
    'AMT', 'CCI', 'EQIX', 'PLD'
}

SECTOR_DATA = {
    'Tecnología (XLK)': ['AAPL', 'MSFT', 'NVDA', 'AVGO', 'ADBE', 'CRM', 'AMD', 'INTC', 'CSCO', 'ORCL'],
    'Financiero (XLF)': ['BRK-B', 'JPM', 'V', 'MA', 'BAC', 'WFC', 'MS', 'GS', 'BLK', 'C'],
    'Salud (XLV)': ['LLY', 'UNH', 'JNJ', 'MRK', 'ABBV', 'TMO', 'PFE', 'ABT', 'AMGN', 'DHR'],
    'Consumo Discrecional (XLY)': ['AMZN', 'TSLA', 'HD', 'MCD', 'NKE', 'LOW', 'SBUX', 'TJX', 'BKNG', 'F'],
    'Consumo Básico (XLP)': ['PG', 'COST', 'PEP', 'KO', 'WMT', 'PM', 'MDLZ', 'MO', 'CL', 'TGT'],
    'Energía (XLE)': ['XOM', 'CVX', 'EOG', 'SLB', 'MPC', 'PXD', 'VLO', 'OXY', 'HES', 'KMI'],
    'Industrial (XLI)': ['GE', 'CAT', 'UNP', 'HON', 'UPS', 'BA', 'RTX', 'DE', 'LMT', 'MMM'],
    'Materiales (XLB)': ['LIN', 'SHW', 'APD', 'FCX', 'ECL', 'NEM', 'CTVA', 'DOW', 'DD', 'PPG'],
    'Utilities (XLU)': ['NEE', 'SO', 'DUK', 'SRE', 'AEP', 'D', 'PEG', 'ED', 'XEL', 'PCG'],
    'Comunicaciones (XLC)': ['GOOGL', 'META', 'NFLX', 'DIS', 'TMUS', 'CMCSA', 'VZ', 'T', 'CHTR', 'WBD'],
    'Real Estate (XLRE)': ['PLD', 'AMT', 'EQIX', 'CCI', 'PSA', 'O', 'VICI', 'DLR', 'WELL', 'SBAC']
}

SECTOR_ETFS = {
    'Tecnología (XLK)': 'XLK', 'Financiero (XLF)': 'XLF', 'Salud (XLV)': 'XLV',
    'Consumo Discrecional (XLY)': 'XLY', 'Consumo Básico (XLP)': 'XLP', 'Energía (XLE)': 'XLE',
    'Industrial (XLI)': 'XLI', 'Materiales (XLB)': 'XLB', 'Utilities (XLU)': 'XLU',
    'Comunicaciones (XLC)': 'XLC', 'Real Estate (XLRE)': 'XLRE'
}

MONTH_NAMES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
MONTH_DICT = {name: i+1 for i, name in enumerate(MONTH_NAMES)}

# --- FUNCIONES ---
@st.cache_data
def get_monthly_stats(tickers, start_year=2010):
    start_date = f"{start_year}-01-01"
    try:
        data = yf.download(tickers, start=start_date, progress=False, group_by='ticker', auto_adjust=True)
    except Exception: return pd.DataFrame()

    stats_list = []
    if len(tickers) == 1: data_dict = {tickers[0]: data}
    else: data_dict = {t: data[t] for t in tickers}

    for ticker in tickers:
        try:
            if ticker not in data_dict: continue
            df = data_dict[ticker]
            if 'Close' not in df.columns: continue
            
            monthly_ret = df['Close'].resample('M').last().pct_change() * 100
            monthly_ret = monthly_ret.dropna()
            
            temp_df = pd.DataFrame(monthly_ret)
            temp_df.columns = ['Return']
            temp_df['Month'] = temp_df.index.month
            
            def avg_win(x): return x[x > 0].mean() if len(x[x > 0]) > 0 else 0
            def avg_loss(x): return x[x < 0].mean() if len(x[x < 0]) > 0 else 0
            
            grouped = temp_df.groupby('Month')['Return'].agg([
                'mean', 'median', 'count', 
                lambda x: (x > 0).mean() * 100,
                avg_win,
                avg_loss
            ])
            grouped.columns = ['Avg_Return', 'Median_Return', 'Years', 'Win_Rate', 'Avg_Win', 'Avg_Loss']
            
            is_cedear = ticker in CEDEAR_UNIVERSE
            
            for m in range(1, 13):
                if m in grouped.index:
                    stats_list.append({
                        'Ticker': ticker,
                        'Is_Cedear': is_cedear,
                        'Month_Num': m,
                        'Month_Name': MONTH_NAMES[m-1],
                        'Avg_Return': grouped.loc[m, 'Avg_Return'],
                        'Median_Return': grouped.loc[m, 'Median_Return'],
                        'Win_Rate': grouped.loc[m, 'Win_Rate'],
                        'Avg_Win': grouped.loc[m, 'Avg_Win'],
                        'Avg_Loss': grouped.loc[m, 'Avg_Loss'],
                        'Years': grouped.loc[m, 'Years']
                    })
        except Exception: continue
            
    return pd.DataFrame(stats_list)

def generate_tv_link(ticker, is_cedear):
    # Fix: Url encoding simple para asegurar compatibilidad
    symbol = f"BCBA%3A{ticker}" if is_cedear else ticker
    return f"https://es.tradingview.com/chart/?symbol={symbol}"

# --- INTERFAZ ---
st.title("📊 SystemaTrader: Radar Estacional v4.1")
st.markdown("**Fase 1 - Radar de Probabilidades & Riesgo**")

with st.sidebar:
    st.header("Parámetros")
    start_year = st.number_input("Año Inicio:", 1990, 2024, 2010)
    selected_month = st.selectbox("Mes Objetivo:", MONTH_NAMES, index=datetime.now().month - 1)

# --- FASE MACRO ---
st.subheader(f"1️⃣ Análisis de Riesgo Sectorial: {selected_month}")

if st.button("Ejecutar Análisis"):
    with st.spinner("Calculando métricas de riesgo..."):
        df_sectors = get_monthly_stats(list(SECTOR_ETFS.values()), start_year)
        
        if not df_sectors.empty:
            month_num = MONTH_DICT[selected_month]
            df_month = df_sectors[df_sectors['Month_Num'] == month_num].copy()
            inv_map = {v: k for k, v in SECTOR_ETFS.items()}
            df_month['Sector_Name'] = df_month['Ticker'].map(inv_map)
            
            st.session_state['df_sectors_month'] = df_month
            
            # Scatter
            fig = px.scatter(
                df_month, x="Avg_Return", y="Win_Rate", size="Win_Rate",
                color="Sector_Name", hover_name="Sector_Name",
                title=f"Probabilidad vs Retorno ({start_year}-Presente)"
            )
            fig.add_hline(y=70, line_dash="dash", line_color="green")
            fig.add_vline(x=0, line_color="white")
            st.plotly_chart(fig, use_container_width=True)
            
            # Risk/Reward Bars
            st.markdown("#### ⚖️ Asimetría de Riesgo (Verde > Rojo = Bueno)")
            df_risk = df_month[['Sector_Name', 'Avg_Win', 'Avg_Loss']].melt(
                id_vars='Sector_Name', value_vars=['Avg_Win', 'Avg_Loss'],
                var_name='Metric', value_name='Percent'
            )
            fig_risk = px.bar(
                df_risk, x='Sector_Name', y='Percent', color='Metric',
                barmode='group', color_discrete_map={'Avg_Win': '#00CC96', 'Avg_Loss': '#EF553B'}
            )
            st.plotly_chart(fig_risk, use_container_width=True)
            
            # Table
            st.dataframe(
                df_month[['Sector_Name', 'Win_Rate', 'Avg_Return', 'Median_Return', 'Avg_Win', 'Avg_Loss', 'Years']]
                .style.format({'Win_Rate': '{:.1f}%', 'Avg_Return': '{:.2f}%', 'Median_Return': '{:.2f}%', 'Avg_Win': '{:.2f}%', 'Avg_Loss': '{:.2f}%'})
                .background_gradient(subset=['Win_Rate', 'Avg_Win'], cmap='Greens'),
                use_container_width=True
            )

# --- FASE MICRO ---
st.divider()
st.subheader("2️⃣ Selección de Activos")

if 'df_sectors_month' in st.session_state:
    df_s = st.session_state['df_sectors_month'].sort_values('Win_Rate', ascending=False)
    best_s = df_s.iloc[0]['Sector_Name']
    target_sector = st.selectbox("Sector:", list(SECTOR_DATA.keys()), index=list(SECTOR_DATA.keys()).index(best_s) if best_s in SECTOR_DATA else 0)
    
    if st.button(f"Analizar {target_sector}"):
        with st.spinner("Procesando..."):
            df_stocks = get_monthly_stats(SECTOR_DATA[target_sector], start_year)
            
            if not df_stocks.empty:
                month_num = MONTH_DICT[selected_month]
                df_m = df_stocks[df_stocks['Month_Num'] == month_num].copy()
                df_m['Label'] = df_m.apply(lambda x: f"{x['Ticker']} 🇦🇷" if x['Is_Cedear'] else x['Ticker'], axis=1)
                df_m = df_m.sort_values('Win_Rate', ascending=False)
                
                # Scatter Stocks
                fig_s = px.scatter(
                    df_m, x="Avg_Return", y="Win_Rate", color="Avg_Win",
                    size="Win_Rate", text="Label", color_continuous_scale="Greens",
                    title="Oportunidades Individuales"
                )
                fig_s.update_traces(textposition='top center')
                fig_s.add_hline(y=70, line_dash="dash", line_color="green")
                st.plotly_chart(fig_s, use_container_width=True)
                
                # Tabla Final con CORRECCIÓN DE ERROR
                df_m['Link'] = df_m.apply(lambda x: generate_tv_link(x['Ticker'], x['Is_Cedear']), axis=1)
                
                st.dataframe(
                    df_m[['Ticker', 'Is_Cedear', 'Win_Rate', 'Avg_Return', 'Avg_Win', 'Avg_Loss', 'Link']],
                    column_config={
                        "Link": st.column_config.LinkColumn("Chart", display_text="Abrir 📈"),
                        "Is_Cedear": st.column_config.CheckboxColumn("CEDEAR?", help="Disponible en BYMA"), # CORREGIDO AQUI
                        "Avg_Win": st.column_config.NumberColumn("Win Avg", format="%.2f%%"),
                        "Avg_Loss": st.column_config.NumberColumn("Loss Avg", format="%.2f%%")
                    },
                    hide_index=True, use_container_width=True
                )
else:
    st.info("Ejecuta el paso 1 primero.")
