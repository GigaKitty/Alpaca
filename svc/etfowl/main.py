import pandas as pd
import numpy as np
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, GetAssetsRequest
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.enums import OrderSide, TimeInForce, AssetStatus, AssetClass, AssetExchange

paper = True if os.getenv("ENVIRONMENT", "dev") != "main" else False

# Initialize the TradingClient
trading_client = TradingClient(
    os.getenv("APCA_API_KEY_ID"), os.getenv("APCA_API_SECRET_KEY"), paper=paper
)

# Initialize clients
data_client = StockHistoricalDataClient(os.getenv("APCA_API_KEY_ID"), os.getenv("APCA_API_SECRET_KEY"))

def get_assets(limit=100):
    # Fetch all tradable ETFs
    assets = trading_client.get_all_assets()
    assets = sorted([asset.symbol for asset in assets if asset.exchange == AssetExchange.ARCA and asset.tradable and asset.status == AssetStatus.ACTIVE and asset.asset_class == AssetClass.US_EQUITY])
    
    return assets
    #print(etfs)
    # Filter and sort ETFs by market capitalization
    #etfs_sorted = sorted(etfs, key=lambda x: x.market_cap, reverse=True)
    #top_etfs = [etf.symbol for etf in etfs_sorted[:limit]]
    
    return etfs

def process_asset(asset):
    # Placeholder function to process each asset
    # Replace this with your actual processing logic
    print(f"Processing asset: {asset}")
    
    # Simulate some processing time
    #import time
    #time.sleep(1)
    return asset

def main():
    # Get the top 100 largest equity ETFs
    assets = get_assets()
    
  # Use ThreadPoolExecutor to run process_asset in parallel for each asset
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_asset, asset): asset for asset in assets}
        
        for future in as_completed(futures):
            asset = futures[future]
            try:
                result = future.result()
                print(f"Completed processing for asset: {result}")
            except Exception as e:
                print(f"Error processing asset {asset}: {e}")


#if __name__ == "__main__":
   #ain()
