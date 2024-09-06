import pandas as pd
import numpy as np
import os
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, GetAssetsRequest
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.enums import OrderSide, TimeInForce

paper = True if os.getenv("ENVIRONMENT", "dev") != "main" else False

# Initialize the TradingClient
trading_client = TradingClient(
    os.getenv("APCA_API_KEY_ID"), os.getenv("APCA_API_SECRET_KEY"), paper=paper
)

# Initialize clients
data_client = StockHistoricalDataClient(os.getenv("APCA_API_KEY_ID"), os.getenv("APCA_API_SECRET_KEY"))

def get_largest_etfs(limit=100):
    # Fetch all tradable ETFs
    assets = trading_client.get_all_assets()
    etfs = [asset for asset in assets if asset.exchange == 'ARCA']
    
    # Filter and sort ETFs by market capitalization
    etfs_sorted = sorted(etfs, key=lambda x: x.market_cap, reverse=True)
    top_etfs = [etf.symbol for etf in etfs_sorted[:limit]]
    
    return top_etfs

def get_top_performing_stocks(limit=100):
    # Get all tradable assets
    assets = trading_client.get_all_assets()
    tradable_assets = [asset.symbol for asset in assets if asset.tradable and asset.classification == 'us_equity']
    
    # Fetch today's stock data to find top performers
    barset = data_client.get_stock_latest_bar(
        StockBarsRequest(
            symbol_or_symbols=tradable_assets,
            timeframe=TimeFrame.Minute,
        )
    )
    
    # Calculate percent change for the day
    stock_data = [
        {
            "symbol": symbol,
            "percent_change": (bar.close - bar.open) / bar.open * 100
        }
        for symbol, bar in barset.items()
    ]
    
    # Sort stocks by percent change
    sorted_stocks = sorted(stock_data, key=lambda x: x["percent_change"], reverse=True)
    
    # Get the top performing stocks
    top_performing_stocks = [stock["symbol"] for stock in sorted_stocks[:limit]]
    return top_performing_stocks

def calculate_average_low(symbol, days=2):
    # Fetch historical data for the past two days
    bars = data_client.get_stock_bars(
        StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Day,
            start=pd.Timestamp.now() - pd.Timedelta(days=days+1),  # Plus one for data granularity
            end=pd.Timestamp.now()
        )
    )
    
    # Extract low prices
    lows = [bar.low for bar in bars[symbol]]
    
    # Calculate average of the lowest lows of the past two days
    average_low = np.mean(lows)
    return average_low

def place_limit_order(symbol, price):
    # Create a limit order request
    order_data = MarketOrderRequest(
        symbol=symbol,
        qty=1,  # Adjust quantity as needed
        side=OrderSide.BUY,
        type='limit',
        limit_price=price,
        time_in_force=TimeInForce.GTC
    )
    
    # Place the order
    trading_client.submit_order(order_data)

def main():
    # Get the top 100 largest equity ETFs
    largest_etfs = get_largest_etfs()
    # Get the top 100 best performing stocks by percentage gain
    top_performing_stocks = get_top_performing_stocks()
    
    # Combine lists for processing (you can process them separately as well)
    combined_list = largest_etfs + top_performing_stocks
    
    # Iterate over each ETF/stock and place limit orders
    for symbol in combined_list:
        avg_low = calculate_average_low(symbol)
        print(f"Placing limit order for {symbol} at price {avg_low}")
        place_limit_order(symbol, avg_low)

if __name__ == "__main__":
    main()
