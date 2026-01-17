import pandas as pd
import streamlit as st
import time
import requests

BASE_URL = "https://api-futures.kucoin.com"

@st.cache_data(ttl=60)
def traer_perpetuos_usdtp_por_lotes(lote_size=50):

    # 1) Traer lista de contratos
    url = f"{BASE_URL}/api/v1/contracts/active"
    r = requests.get(url, timeout=15)
    data = r.json()

    if data["code"] != "200000":
        st.error("KuCoin bloqueó la respuesta. Probá en 30–60 segundos.")
        return pd.DataFrame()

    contracts = data["data"]

    # Filtrar solo USDT-M
    symbols = [
        c["symbol"] for c in contracts
        if "USDTM" in c["symbol"]
    ]

    st.write(f"Total contratos USDT-M: {len(symbols)}")

    dfs = []
    columnas_vistas = set()

    # 2) Procesar por lotes de 50
    for i in range(0, len(symbols), lote_size):
        lote = symbols[i:i+lote_size]
        st.write(f"Procesando lote {i} → {i+lote_size}")

        filas = []

        for s in lote:
            try:
                ticker_url = f"{BASE_URL}/api/v1/ticker?symbol={s}"
                r = requests.get(ticker_url, timeout=10)
                d = r.json()

                if d["code"] == "200000":
                    row = d["data"]
                    row["cripto"] = s
                    filas.append(row)

            except Exception as e:
                st.warning(f"Error con {s}: {e}")

        if filas:
            df_lote = pd.DataFrame(filas)
            columnas_vistas.update(df_lote.columns)
            dfs.append(df_lote)

        time.sleep(1.2)  # evita bloqueo

    if not dfs:
        st.error("KuCoin no devolvió datos válidos.")
        return pd.DataFrame()

    df_final = pd.concat(dfs, ignore_index=True)

    # Normalizamos columnas (clave para que no rompa Streamlit)
    df_final = df_final.reindex(columns=list(columnas_vistas))

    # Orden final por cripto
    if "cripto" in df_final.columns:
        df_final = df_final.sort_values("cripto").reset_index(drop=True)

    return df_final
 df_final

st.title("Dashboard KuCoin Perpetuos")

df = traer_perpetuos_usdtp_por_lotes(lote_size=50)

st.dataframe(df)
