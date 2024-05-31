Earnyearn is a websocket monitoring script that checks for MACD on earnings stocks and sends a request to buy or sell to the Alpaca API.

Flow of earnyearn:

- Connect to finnhub api and creates a list of stock symbols with earnings
- Take list of earnings tickers and submit those to the websockets connection with Alpaca API
- For each ticker build a list of bar data to save and analyze with different TA strategies
- When strategies trigger an order is submitted for either buy or sell to the Alpaca API webhook service

