import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    BINANCE_API_KEY = os.getenv("BINANCE_TESTNET_API_KEY", "")
    BINANCE_API_SECRET = os.getenv("BINANCE_TESTNET_API_SECRET", "")
    BASE_URL = "https://testnet.binance.vision"
    
    # Data Paths
    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    BACKTEST_TRADES_PATH = os.path.join(DATA_DIR, "backtest_trades.csv")
    LIVE_TRADES_PATH = os.path.join(DATA_DIR, "live_trades.csv")
