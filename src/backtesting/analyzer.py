import pandas as pd
import csv
import numpy as np
from config.config import Config
from src.utils.logger import setup_logger

logger = setup_logger("analyzer")

def save_backtest_trades(stats, symbol="BTCUSDT"):
    """Save backtest trades to CSV aligned with config."""
    trades = []
    
    df = None
    if hasattr(stats, "trades"):
        df = stats.trades
    elif hasattr(stats, "_trades"):
        df = stats._trades
    elif isinstance(stats, dict) and "_trades" in stats:
        df = stats["_trades"]

    if df is not None and len(df) > 0:
        for _, row in df.iterrows():
            try:
                size = row.get("Size", 0)
                if size == 0: continue
                
                direction = "BUY" if size > 0 else "SELL"
                
                trade = {
                    'entry_time': row.get("EntryTime", ""),
                    'exit_time': row.get("ExitTime", ""),
                    'symbol': symbol,
                    'direction': direction,
                    'entry_price': row.get("EntryPrice", 0),
                    'exit_price': row.get("ExitPrice", 0),
                    'quantity': abs(size),
                    'pnl': row.get("PnL", 0),
                }
                trades.append(trade)
            except Exception:
                continue

    out_path = Config.BACKTEST_TRADES_PATH
    try:
        with open(out_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'entry_time', 'exit_time', 'symbol', 'direction', 
                'entry_price', 'exit_price', 'quantity', 'pnl'
            ])
            writer.writeheader()
            writer.writerows(trades)
            logger.info(f"Saved {len(trades)} trades to {out_path}")
    except Exception as e:
        logger.error(f"Failed to save trades: {e}")
