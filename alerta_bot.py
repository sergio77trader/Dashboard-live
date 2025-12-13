name: Bot Final SystemaTrader

on:
  schedule:
    # Horarios UTC (Lunes a Viernes)
    - cron: '30 14 * * 1-5'
    - cron: '0 17 * * 1-5'
    - cron: '30 20 * * 1-5'
  workflow_dispatch: # Botón manual

jobs:
  ejecutar:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Python Setup
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Instalar Dependencias
        run: pip install yfinance pandas numpy requests

      - name: Correr Bot
        env:
          TELEGRAM_TOKEN: ${{ secrets.TELEGRAM_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python alerta_bot.py
