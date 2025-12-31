import sys
import os
import pandas as pd
from backtesting import Backtest, Strategy
import numpy as np

# Adjust path to find src if run directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.strategy.multi_tf import MultiTimeframeStrategy, TradeDirection
from src.utils.data import fetch_binance_klines
from src.utils.logger import setup_logger
from src.backtesting.analyzer import save_backtest_trades
from config.config import Config

logger = setup_logger("backtest", "backtest.log")

class BacktestingStrategy(Strategy):
    def __init__(self, broker, data,params):
        super().__init__(broker, data, params)
        self.strategy_instance = MultiTimeframeStrategy()
        self.trades_log = []
        self.last_1h_update = None
        self.closes_1h_sim = pd.Series()

    def init(self):
        # We don't pre-calculate indicators here because we need multi-timeframe 
        # logic that might be complex to vectorise perfectly with backtesting.py's I()
        # Instead we simply prepare our storage.
        pass

    def next(self):
        # Current 15m candle
        current_time = self.data.index[-1]
        current_price = self.data.Close[-1]
        
        # --- Resample Logic for 1h Data ---
        # Get all 15m closes up to now
        closes_15m = pd.Series(self.data.Close, index=self.data.index)
        
        # Resample to 1h. 
        # Note: Backtesting.py provides data slice up to current bar.
        # We need to ensure we don't look ahead. 
        # Resampling generally takes the last available data in the bin.
        # For a 15m strategy, 'now' is the close of the 15m bar.
        closes_1h = closes_15m.resample('1h').last().dropna()
        
        # Generate Signal
        highs_15m = pd.Series(self.data.High, index=self.data.index)
        lows_15m = pd.Series(self.data.Low, index=self.data.index)

        # Generate Signal
        signal = self.strategy_instance.generate_signal(
            closes_15m=closes_15m.tolist(),
            highs_15m=highs_15m.tolist(),
            lows_15m=lows_15m.tolist(),
            closes_1h=closes_1h.tolist(),
            timestamp=pd.to_datetime(current_time)
        )
        
        # Debug logging (optional, maybe reduce frequency)
        # logger.debug(f"Time: {current_time}, Price: {current_price}")

        if signal:
            if signal.direction == TradeDirection.LONG and not self.position:
                # Entry
                quantity = self.equity * 0.95 / current_price 
                self.strategy_instance.on_trade_entry(
                    symbol="BTCUSDT",
                    direction=signal.direction,
                    entry_price=current_price,
                    entry_time=current_time,
                    quantity=quantity,
                    atr=0 # Calculated inside logic if needed, or we pass dummy
                )
                self.buy(size=0.95)
                logger.info(f"BUY signal executed @ {current_price:.2f}")
            
            elif signal.direction == TradeDirection.SHORT and not self.position:
                 # Short Entry
                quantity = self.equity * 0.95 / current_price
                self.strategy_instance.on_trade_entry(
                    symbol="BTCUSDT", 
                    direction=signal.direction,
                    entry_price=current_price, 
                    entry_time=current_time,
                    quantity=quantity, 
                    atr=0
                )
                self.sell(size=0.95)
                logger.info(f"SELL signal executed @ {current_price:.2f}")

            elif signal.direction == TradeDirection.SHORT and self.position.is_long:
                # Exit Long
                exit_dict = self.strategy_instance.on_trade_exit(current_price, current_time)
                if exit_dict:
                    self.trades_log.append(exit_dict)
                self.position.close()
                logger.info(f"Long Position Closed @ {current_price:.2f}")
                
            elif signal.direction == TradeDirection.LONG and self.position.is_short:
                # Exit Short
                exit_dict = self.strategy_instance.on_trade_exit(current_price, current_time)
                if exit_dict:
                    self.trades_log.append(exit_dict)
                self.position.close()
                logger.info(f"Short Position Closed @ {current_price:.2f}")

def run_backtest():
    symbol = "BTCUSDT"
    logger.info("Fetching backtest data...")
    # Fetch enough data
    df = fetch_binance_klines(symbol, "15m", limit=3000)
    
    if df.empty:
        logger.error("No data fetched.")
        return

    # Backtesting.py expects columns: Open, High, Low, Close, Volume
    df = df.rename(columns={
        "open": "Open", 
        "high": "High", 
        "low": "Low", 
        "close": "Close", 
        "volume": "Volume"
    })
    df = df.set_index("timestamp")
    
    logger.info(f"Running backtest on {len(df)} candles...")
    
    bt = Backtest(df, BacktestingStrategy, cash=1_000_000, commission=.001)
    stats = bt.run()
    
    logger.info("--- Backtest Results ---")
    logger.info(f"Return: {stats['Return [%]']:.2f}%")
    logger.info(f"Equity Final: ${stats['Equity Final [$]']:.2f}")
    
    save_backtest_trades(stats)

if __name__ == "__main__":
    run_backtest()
