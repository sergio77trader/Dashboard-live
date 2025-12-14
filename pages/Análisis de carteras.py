import yfinance as yf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap
from ipywidgets import interact, widgets, Button, HBox
from IPython.display import display
from google.colab import files  # IMPORTANTE para descarga en Colab

def analizar_cartera(tickers_str, pesos_str, benchmark, anios):
    tickers = [t.strip().upper() for t in tickers_str.split(",") if t.strip()]
    if len(tickers) == 0:
        print("Debe ingresar al menos 1 ticker.")
        return

    if pesos_str.strip():
        pesos = [float(p) for p in pesos_str.split(",")]
        if len(pesos) != len(tickers):
            print("La cantidad de pesos debe coincidir con los tickers.")
            return
        pesos = np.array(pesos)
    else:
        pesos = np.ones(len(tickers)) / len(tickers)

    pesos = pesos / pesos.sum()

    # Descargar precios
    activos = tickers + [benchmark, "SPY", "QQQ", "DIA"]
    activos = list(dict.fromkeys(activos))
    data = yf.download(activos, period=f"{anios}y", auto_adjust=True)["Close"]
    returns = data.pct_change(fill_method=None).dropna()
    precios = data.dropna()

    # Serie de cartera y benchmark
    retornos_portafolio = returns[tickers].dot(pesos)
    serie_portafolio = (1 + retornos_portafolio).cumprod()
    serie_bench = (1 + returns[benchmark]).cumprod()

    # CAGR función
    def calcular_cagr(serie, años):
        if len(serie) == 0: return np.nan
        return (serie[-1] / serie[0])**(1/años) - 1

    # Métricas cartera
    beta = np.cov(retornos_portafolio, returns[benchmark])[0,1] / np.var(returns[benchmark])
    volatilidad = retornos_portafolio.std() * np.sqrt(252)
    correlacion = np.corrcoef(retornos_portafolio, returns[benchmark])[0,1]
    rendimiento_12m = (1 + retornos_portafolio[-252:]).prod() - 1 if len(retornos_portafolio) >= 252 else np.nan
    cagr_portafolio = calcular_cagr(serie_portafolio.values, anios)
    sharpe_portafolio = (retornos_portafolio.mean()*252) / (retornos_portafolio.std()*np.sqrt(252))

    # Métricas benchmark seleccionado
    cagr_bench = calcular_cagr(serie_bench.values, anios)
    volatilidad_bench = returns[benchmark].std()*np.sqrt(252)
    rendimiento_bench_12m = (1 + returns[benchmark][-252:]).prod()-1 if len(returns[benchmark])>=252 else np.nan
    sharpe_bench = (returns[benchmark].mean()*252) / (returns[benchmark].std()*np.sqrt(252))

    # Tabla resumen
    resultados = pd.DataFrame({
        'Conjunto': ['Cartera', benchmark],
        'Beta': [f"{beta:.2f}", "-"],
        'Volatilidad Anualizada': [f"{volatilidad:.2%}", f"{volatilidad_bench:.2%}"],
        'CAGR': [f"{cagr_portafolio:.2%}", f"{cagr_bench:.2%}"],
        'Rendimiento 12M': [f"{rendimiento_12m:.2%}", f"{rendimiento_bench_12m:.2%}"],
        'Correlación con Benchmark': [f"{correlacion:.2f}", "1.00"],
        'Sharpe Ratio': [f"{sharpe_portafolio:.2f}", f"{sharpe_bench:.2f}"]
    })
    display(resultados)

    # Matriz de correlación (usada en varios lados)
    corr_matrix = returns[tickers].corr()

    # Exportación a Excel/CSV + descarga
    def export_excel(_):
        with pd.ExcelWriter('resultados_cartera.xlsx') as writer:
            resultados.to_excel(writer, index=False, sheet_name='Resumen')
            corr_matrix.to_excel(writer, sheet_name='Correlacion')
            pd.DataFrame({'Retorno cartera': serie_portafolio, f'Retorno {benchmark}': serie_bench}).to_excel(writer, sheet_name='Evolucion')
        print('Archivo "resultados_cartera.xlsx" generado.')
        files.download('resultados_cartera.xlsx')

    def export_csv(_):
        resultados.to_csv('resultados_cartera.csv', index=False)
        corr_matrix.to_csv('correlacion_activos.csv')
        pd.DataFrame({'Retorno cartera': serie_portafolio, f'Retorno {benchmark}': serie_bench}).to_csv('evolucion_cartera.csv')
        print('Archivos CSV generados.')
        files.download('resultados_cartera.csv')
        files.download('correlacion_activos.csv')
        files.download('evolucion_cartera.csv')

    boton_excel = Button(description="Exportar a Excel")
    boton_excel.on_click(export_excel)
    boton_csv = Button(description="Exportar a CSV")
    boton_csv.on_click(export_csv)
    display(HBox([boton_excel, boton_csv]))

    # Pie chart
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(pesos, labels=tickers, autopct='%1.1f%%', startangle=140)
    ax.set_title("Composición de la Cartera")
    plt.show()

    # Matriz de correlación (heatmap)
    cmap_custom = LinearSegmentedColormap.from_list('CelesteRojoInvert', ['lightblue', 'red'], N=256)
    fig, ax = plt.subplots(figsize=(10, 8), dpi=100)
    sns.heatmap(
        corr_matrix, annot=True, fmt=".2f", annot_kws={"size": 11},
        cmap=cmap_custom, vmin=0.0, vmax=1.0,
        linewidths=0.5, linecolor='gray', square=True,
        cbar_kws={"shrink": 0.8, "pad": 0.02, "label": "Correlación"},
        ax=ax
    )
    ax.set_title("Matriz de Correlaciones entre Activos")
    plt.show()

    # Alerta de activos muy correlacionados
    high_corr_pairs = []
    for i in range(len(tickers)):
        for j in range(i+1, len(tickers)):
            if corr_matrix.iloc[i,j] > 0.85:
                high_corr_pairs.append((tickers[i], tickers[j], corr_matrix.iloc[i,j]))
    if high_corr_pairs:
        print("\033[91mALERTA: Hay activos en cartera con correlación > 0.85:\033[0m")
        for t1, t2, val in high_corr_pairs:
            print(f"- {t1} y {t2}: correlación = {val:.2f}")
    else:
        print("No se detectan pares de activos con correlación mayor a 0.85.")

    # CAGR individuales (activos y benchmarks)
    activos_cagr = {}
    for ticker in tickers + ["SPY", "QQQ", "DIA"]:
        if ticker in precios:
            serie = precios[ticker].dropna()
            años_cagr = (len(serie) / 252)
            activos_cagr[ticker] = calcular_cagr(serie.values, años_cagr)
    activos_cagr['Cartera'] = cagr_portafolio
    activos_cagr[benchmark] = cagr_bench

    # Grafico de barras verticales
    fig, ax = plt.subplots(figsize=(10, 5))
    nombres = list(activos_cagr.keys())
    valores = [v*100 for v in activos_cagr.values()]
    barras = ax.bar(nombres, valores, color=['royalblue' if n in tickers else 'orange' if n=='Cartera' else 'gray' for n in nombres])
    ax.set_ylabel('CAGR (%)')
    ax.set_title('CAGR Anualizado - Cartera, Activos y Benchmarks')
    plt.setp(ax.get_xticklabels(), rotation=45)
    plt.tight_layout()
    plt.show()

    # Gráfico de evolución acumulada (cartera vs benchmark)
    fig, ax = plt.subplots(figsize=(12, 6))
    serie_portafolio.plot(ax=ax, label="Cartera", linewidth=2)
    serie_bench.plot(ax=ax, label=f"Benchmark: {benchmark}", linewidth=2, linestyle='--')
    ax.set_title("Evolución acumulada: Cartera vs Benchmark")
    ax.set_ylabel("Multiplicador sobre el capital inicial")
    ax.legend()
    plt.tight_layout()
    plt.show()

# Widget interactivo único (no hace falta display antes)
interact(
    analizar_cartera,
    tickers_str=widgets.Text(
        value='JPM, GOLD, V, MRK, FXI, EWZ, KO',
        placeholder='Escribir hasta 50 tickers separados por coma',
        description='Tickers:', layout=widgets.Layout(width='90%')),
    pesos_str=widgets.Text(
        value='10, 20, 20, 10, 10, 10, 20',
        placeholder='Pesos separados por coma',
        description='Pesos:', layout=widgets.Layout(width='90%')),
    benchmark=widgets.Dropdown(
        options=['SPY', 'QQQ', 'DIA'],
        value='SPY', description='Benchmark:'),
    anios=widgets.IntText(
    value=10,
    description='Años:',
    min=1
)

);
