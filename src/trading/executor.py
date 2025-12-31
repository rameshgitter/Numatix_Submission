import time
import pandas as pd
from datetime import datetime
import sys
import os

# Adjust path to find src if run directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.trading.exchange import BinanceTestnetClient
from src.strategy.multi_tf import MultiTimeframeStrategy, TradeDirection
from src.utils.logger import setup_logger
from config.config import Config

logger = setup_logger("live_trading", "live_trading.log")

def run_trading_loop():
    client = BinanceTestnetClient()
    strategy = MultiTimeframeStrategy()
    
    symbol = "BTCUSDT"
    logger.info(f"Starting live trading for {symbol}")
    
    # State tracking
    current_position = None  # None, 'LONG', 'SHORT'
    # entry_price = 0.0 # Unused variable
    
    while True:
        try:
            # 1. Fetch Data
            # Get 15m data for signals
            klines_15m = client.get_klines(symbol, "15m", limit=100)
            if not klines_15m:
                time.sleep(10)
                continue
                
            df_15m = pd.DataFrame(klines_15m, columns=[
                "open_time", "open", "high", "low", "close", "volume", 
                "close_time", "qav", "num_trades", "taker_base_vol", "taker_quote_vol", "ignore"
            ])
            df_15m = df_15m.astype({
                "open": float, "high": float, "low": float, "close": float, "volume": float
            })
            
            # Get 1h data for confirmation
            klines_1h = client.get_klines(symbol, "1h", limit=100)
            if not klines_1h:
                time.sleep(10)
                continue
                
            df_1h = pd.DataFrame(klines_1h, columns=[
                "open_time", "open", "high", "low", "close", "volume", 
                "close_time", "qav", "num_trades", "taker_base_vol", "taker_quote_vol", "ignore"
            ])
            df_1h = df_1h.astype({
                "open": float, "high": float, "low": float, "close": float, "volume": float
            })
            
            # 2. Generate Signal
            # We explicitly pass the Series
            signal = strategy.generate_signal(
                closes_15m=df_15m["close"].tolist(),
                highs_15m=df_15m["high"].tolist(),
                lows_15m=df_15m["low"].tolist(),
                closes_1h=df_1h["close"].tolist(),
                timestamp=datetime.now()
            )
            
            current_price = client.get_symbol_price(symbol)
            current_time = datetime.now().isoformat()
            
            logger.info(f"--- Trading cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
            
            # 3. Execute Trades
            if signal:
                logger.info(f"Signal generated: {signal.direction.name} - {signal.reason}")
                
                # Check for reversal/exit first
                if current_position:
                    if (current_position == 'LONG' and signal.direction == TradeDirection.SHORT) or \
                       (current_position == 'SHORT' and signal.direction == TradeDirection.LONG):
                        
                        logger.info(f"Executing EXIT for {current_position} position")
                        # Close existing
                        side = "SELL" if current_position == 'LONG' else "BUY"
                        client.place_order(symbol, side, "MARKET", quantity=0.001)
                        
                        exit_trade = strategy.on_trade_exit(current_price, current_time)
                        if exit_trade:
                            logger.info(f"Position CLOSED: {exit_trade}")
                            save_live_trade(exit_trade)
                        
                        current_position = None
                
                # Entry Logic
                if not current_position:
                    side = "BUY" if signal.direction == TradeDirection.LONG else "SELL"
                    logger.info(f"Executing {signal.direction.name} signal: 0.0010 @ {current_price}")
                    
                    order = client.place_order(symbol, side, "MARKET", quantity=0.001)
                    
                    if order and order.get('status') == 'FILLED':
                        entry_trade = strategy.on_trade_entry(
                            symbol=symbol,
                            direction=signal.direction,
                            entry_price=float(order['fills'][0]['price']),
                            entry_time=current_time,
                            quantity=0.001,
                            atr=500.0 # Dynamic ATR calculation should be added here
                        )
                        logger.info(f"Position OPENED: {entry_trade}")
                        save_live_trade({
                            'entry_time': current_time,
                            'symbol': symbol,
                            'direction': 'BUY' if signal.direction == TradeDirection.LONG else 'SELL',
                            'entry_price': entry_trade.entry_price,
                            'quantity': entry_trade.quantity,
                            'sl': entry_trade.stop_loss,
                            'tp': entry_trade.take_profit
                        })
                        current_position = 'LONG' if signal.direction == TradeDirection.LONG else 'SHORT'

            # 4. Monitor Open Position (SL/TP)
            if current_position:
                # In a real system, we'd check strategy.check_sl_tp(current_price) 
                # and verify order status or place OCO orders.
                # For this assignment, we rely on the loop.
                pass

            time.sleep(60) # Wait 1 minute
            
        except Exception as e:
            logger.error(f"Error in trading loop: {e}")
            time.sleep(10)
        except KeyboardInterrupt:
            logger.info("Trading loop interrupted by user")
            break

def save_live_trade(trade_dict):
    df = pd.DataFrame([trade_dict])
    file_path = Config.LIVE_TRADES_PATH
    
    if not os.path.exists(file_path):
        df.to_csv(file_path, index=False)
    else:
        df.to_csv(file_path, mode='a', header=False, index=False)
    logger.info(f"Saved {len(df)} live trades to live_trades.csv")

if __name__ == "__main__":
    run_trading_loop()
