import pandas as pd
import logging
import sys
import os
from datetime import datetime, timedelta

# Add src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config.config import Config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', handlers=[
    logging.StreamHandler(sys.stdout),
    logging.FileHandler("trade_matching.log")
])
logger = logging.getLogger(__name__)

class TradeComparator:
    def __init__(self, time_tol_minutes=5, price_tol_pct=0.02):
        self.time_tol = timedelta(minutes=time_tol_minutes)
        self.price_tol = price_tol_pct

    def load_trades(self):
        try:
            bt_trades = pd.read_csv(Config.BACKTEST_TRADES_PATH)
            live_trades = pd.read_csv(Config.LIVE_TRADES_PATH)
            
            # Standardize Columns
            expected_cols = ['entry_time', 'symbol', 'direction', 'entry_price', 'quantity']
            
            # Helper to parse time
            def parse_time(t):
                try:
                    return pd.to_datetime(t).to_pydatetime()
                except:
                    return None

            bt_trades['dt'] = bt_trades['entry_time'].apply(parse_time)
            live_trades['dt'] = live_trades['entry_time'].apply(parse_time)
            
            return bt_trades, live_trades
        except Exception as e:
            logger.error(f"Error loading trades: {e}")
            return pd.DataFrame(), pd.DataFrame()

    def compare(self):
        bt_df, live_df = self.load_trades()
        
        logger.info(f"Loaded {len(bt_df)} trades from backtest")
        logger.info(f"Loaded {len(live_df)} trades from live")
        logger.info(f"Matching with tolerance: Time={self.time_tol}, Price={self.price_tol*100}%")
        logger.info("-" * 80)
        logger.info("TRADE MATCHING REPORT")
        logger.info("-" * 80)

        metrics = {"matched": 0, "unmatched_live": 0, "unmatched_bt": 0}
        
        # Iterate live trades to find matches in backtest
        # We assume live trades are fewer and we want to validate them
        
        matched_indices_bt = set()
        
        for idx, live_trade in live_df.iterrows():
            match_found = False
            best_match = None
            min_score = float('inf') # Lower is better
            
            lt_time = live_trade['dt']
            
            if lt_time is None: continue

            # Search in backtest
            candidates = bt_df[
                (bt_df['symbol'] == live_trade['symbol']) &
                (bt_df['direction'] == live_trade['direction'])
            ]
            
            for bt_idx, bt_trade in candidates.iterrows():
                if bt_idx in matched_indices_bt: continue
                
                bt_time = bt_trade['dt']
                if bt_time is None: continue
                
                time_diff = abs(lt_time - bt_time)
                
                if time_diff <= self.time_tol:
                    # Time match, check price
                    price_diff = abs(float(live_trade['entry_price']) - float(bt_trade['entry_price']))
                    price_avg = (float(live_trade['entry_price']) + float(bt_trade['entry_price'])) / 2
                    price_pct_diff = price_diff / price_avg
                    
                    if price_pct_diff <= self.price_tol:
                        # Match candidate
                        score = time_diff.total_seconds() + (price_pct_diff * 10000) 
                        if score < min_score:
                            min_score = score
                            best_match = (bt_idx, bt_trade)
                            match_found = True
            
            if match_found:
                metrics["matched"] += 1
                matched_indices_bt.add(best_match[0])
                logger.info(f"[MATCH] Live Trade @ {lt_time} matched Backtest Trade @ {best_match[1]['dt']}")
            else:
                metrics["unmatched_live"] += 1
                logger.info(f"[NO MATCH] Live Trade @ {lt_time} {live_trade['direction']} {live_trade['entry_price']}")
                
        metrics["unmatched_bt"] = len(bt_df) - len(matched_indices_bt)
        
        logger.info("-" * 80)
        logger.info(f"Summary: Matched: {metrics['matched']} | Unmatched Live: {metrics['unmatched_live']}")
        if len(live_df) > 0:
            match_rate = (metrics['matched'] / len(live_df)) * 100
            logger.info(f"Match Rate: {match_rate:.1f}%")
        else:
            logger.info("No live trades to match.")

if __name__ == "__main__":
    comparator = TradeComparator()
    comparator.compare()
