import pandas as pd
import streamlit as st
import time
from kucoin.client import Market

@st.cache_data(ttl=60)
def traer_perpetuos_usdtp_por_lotes(lote_size=50):
    client = Market()

    # 1) Traemos lista completa de símbolos
    tickers = client.get_contracts_list()
    
    # Filtramos solo USDT-M perp
    symbols = [
        t["symbol"] for t in tickers
        if "USDTM" in t.get("symbol", "")
    ]

    st.write(f"Total contratos encontrados: {len(symbols)}")

    dfs = []
    columnas_vistas = set()

    # 2) Procesamos por lotes
    for i in range(0, len(symbols), lote_size):
        lote = symbols[i:i+lote_size]
        st.write(f"Procesando lote {i} → {i+lote_size}")

        filas = []

        for s in lote:
            try:
                data = client.get_ticker(s)
                data["cripto"] = s
                filas.append(data)

            except Exception as e:
                st.warning(f"Error con {s}: {e}")
                continue

        if filas:
            df_lote = pd.DataFrame(filas)

            # Guardamos columnas vistas
            columnas_vistas.update(df_lote.columns)

            dfs.append(df_lote)

        time.sleep(1.2)  # evita bloqueo de KuCoin

    # 3) Unimos todo
    if not dfs:
        st.error("KuCoin no devolvió datos válidos.")
        return pd.DataFrame()

    df_final = pd.concat(dfs, ignore_index=True)

    # 4) Normalizamos columnas (CLAVE para que no rompa Streamlit)
    columnas_base = list(columnas_vistas)
    df_final = df_final.reindex(columns=columnas_base)

    # 5) Ordenamos por cripto (tu error original)
    if "cripto" in df_final.columns:
        df_final = df_final.sort_values("cripto").reset_index(drop=True)

    return df_final
