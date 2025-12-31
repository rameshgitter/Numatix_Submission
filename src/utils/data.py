import requests
import pandas as pd
from datetime import datetime
import time
from ..utils.logger import setup_logger

logger = setup_logger("data_utils")

def fetch_binance_klines(symbol, interval, limit=1000):
    """
    Fetch historical klines from Binance public API.
    """
    url = "https://testnet.binance.vision/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        # [Open Time, Open, High, Low, Close, Volume, ...]
        df = pd.DataFrame(data, columns=[
            "open_time", "open", "high", "low", "close", "volume", 
            "close_time", "qav", "num_trades", "taker_base_vol", "taker_quote_vol", "ignore"
        ])
        
        df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms")
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)
            
        return df[["timestamp", "open", "high", "low", "close", "volume"]]
        
    except Exception as e:
        logger.error(f"Error fetching data for {symbol} {interval}: {e}")
        return pd.DataFrame()
