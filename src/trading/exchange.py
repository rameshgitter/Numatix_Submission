import requests
import hmac
import hashlib
import time
import pandas as pd
from urllib.parse import urlencode
from config.config import Config
from src.utils.logger import setup_logger

logger = setup_logger("exchange")

class BinanceTestnetClient:
    def __init__(self):
        self.base_url = Config.BASE_URL
        self.api_key = Config.BINANCE_API_KEY
        self.api_secret = Config.BINANCE_API_SECRET
        
        if not self.api_key or not self.api_secret:
            logger.warning("Binance API credentials not found in env vars")

    def _get_timestamp(self):
        return int(time.time() * 1000)

    def _sign(self, params):
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def get_klines(self, symbol, interval, limit=100):
        endpoint = "/api/v3/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        try:
            response = requests.get(f"{self.base_url}{endpoint}", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching klines: {e}")
            return []

    def get_account_info(self):
        endpoint = "/api/v3/account"
        params = {"timestamp": self._get_timestamp()}
        params["signature"] = self._sign(params)
        headers = {"X-MBX-APIKEY": self.api_key}
        
        try:
            response = requests.get(f"{self.base_url}{endpoint}", headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching account info: {e}")
            return None

    def place_order(self, symbol, side, type, quantity, price=None, time_in_force="GTC"):
        endpoint = "/api/v3/order"
        params = {
            "symbol": symbol,
            "side": side,
            "type": type,
            "quantity": quantity,
            "timestamp": self._get_timestamp()
        }
        if price:
            params["price"] = price
            params["timeInForce"] = time_in_force
            
        params["signature"] = self._sign(params)
        headers = {"X-MBX-APIKEY": self.api_key}
        
        try:
            response = requests.post(f"{self.base_url}{endpoint}", headers=headers, params=params)
            response.raise_for_status()
            logger.info(f"Order placed: {response.json()}")
            return response.json()
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            logger.error(f"Response: {response.text if 'response' in locals() else 'No response'}")
            return None
    
    def get_symbol_price(self, symbol):
        endpoint = "/api/v3/ticker/price"
        params = {"symbol": symbol}
        try:
            response = requests.get(f"{self.base_url}{endpoint}", params=params)
            return float(response.json()["price"])
        except Exception:
            return None
