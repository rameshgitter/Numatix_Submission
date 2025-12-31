"""
Multi-Timeframe Trading Strategy
Single source of truth for both backtesting and live trading.
"""

import logging
from typing import Optional, Dict, List
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
import pandas_ta as ta
from src.strategy.base import BaseStrategy

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("strategy")


class TradeDirection(Enum):
    LONG = "BUY"
    SHORT = "SELL"


@dataclass
class Signal:
    timestamp: datetime
    symbol: str
    direction: TradeDirection
    confidence: float
    reason: str


@dataclass
class Position:
    symbol: str
    direction: TradeDirection
    entry_price: float
    entry_time: datetime
    quantity: float
    stop_loss: float
    take_profit: float


class MultiTimeframeStrategy(BaseStrategy):
    """
    Multi-timeframe strategy:
    - 15-minute: Entry signals
    - 1-hour: Trend confirmation filter
    
    Entry Rules:
    - Fast MA (15-min) crosses above Slow MA (15-min) AND
    - Price is above 1-hour MA (uptrend confirmation)
    
    Exit Rules:
    - SL/TP hit, or
    - Fast MA crosses below Slow MA (15-min)
    
    Position Sizing:
    - Fixed quantity per trade (can be adjusted for risk management)
    """

    def __init__(self, symbol: str = "BTCUSDT", risk_per_trade: float = 0.02):
        self.symbol = symbol
        self.risk_per_trade = risk_per_trade
        self.position: Optional[Position] = None
        
        # MA parameters
        self.fast_ma_period = 9  # 15-min timeframe
        self.slow_ma_period = 21  # 15-min timeframe
        self.hourly_ma_period = 20  # 1-hour confirmation
        
        # Risk management
        self.atr_multiplier_sl = 2.0
        self.atr_multiplier_tp = 3.0
        self.atr_period = 14
        
        logger.info(f"Strategy initialized for {symbol}")

    def calculate_sma(self, prices: List[float], period: int) -> Optional[float]:
        """Calculate Simple Moving Average"""
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period

    def calculate_atr(self, highs: List[float], lows: List[float], closes: List[float]) -> Optional[float]:
        """Calculate Average True Range"""
        if len(closes) < self.atr_period:
            return None
        
        tr_values = []
        for i in range(1, len(closes)):
            high_low = highs[i] - lows[i]
            high_close = abs(highs[i] - closes[i-1])
            low_close = abs(lows[i] - closes[i-1])
            tr = max(high_low, high_close, low_close)
            tr_values.append(tr)
        
        return sum(tr_values[-self.atr_period:]) / self.atr_period

    def generate_signal(
        self,
        closes_15m: List[float],
        highs_15m: List[float],
        lows_15m: List[float],
        closes_1h: List[float],
        timestamp: datetime
    ) -> Optional[Signal]:
        """
        Generate trading signal based on multi-timeframe analysis.
        
        Args:
            closes_15m: 15-minute close prices (recent first in list order)
            highs_15m: 15-minute high prices
            lows_15m: 15-minute low prices
            closes_1h: 1-hour close prices
            timestamp: Current timestamp
        """
        
        # Calculate moving averages on 15-min
        fast_ma = self.calculate_sma(closes_15m, self.fast_ma_period)
        slow_ma = self.calculate_sma(closes_15m, self.slow_ma_period)
        
        # Calculate confirmation on 1-hour
        hourly_ma = self.calculate_sma(closes_1h, self.hourly_ma_period)
        
        # Calculate ATR for SL/TP
        atr = self.calculate_atr(highs_15m, lows_15m, closes_15m)
        
        if not all([fast_ma, slow_ma, hourly_ma, atr]):
            logger.debug("Insufficient data for signal generation")
            return None
        
        current_price = closes_15m[-1]
        
        # ENTRY LOGIC
        # Long signal: Fast MA > Slow MA AND Price > Hourly MA
        if fast_ma > slow_ma and current_price > hourly_ma:
            if self.position is None:  # No existing position
                logger.info(
                    f"LONG signal generated: fast_ma={fast_ma:.2f} > slow_ma={slow_ma:.2f}, "
                    f"price={current_price:.2f} > hourly_ma={hourly_ma:.2f}"
                )
                return Signal(
                    timestamp=timestamp,
                    symbol=self.symbol,
                    direction=TradeDirection.LONG,
                    confidence=0.7,
                    reason=f"Fast MA {fast_ma:.2f} > Slow MA {slow_ma:.2f}, Price above hourly MA"
                )
        
        # Short signal: Fast MA < Slow MA AND Price < Hourly MA
        elif fast_ma < slow_ma and current_price < hourly_ma:
            if self.position is None:
                logger.info(
                    f"SHORT signal generated: fast_ma={fast_ma:.2f} < slow_ma={slow_ma:.2f}, "
                    f"price={current_price:.2f} < hourly_ma={hourly_ma:.2f}"
                )
                return Signal(
                    timestamp=timestamp,
                    symbol=self.symbol,
                    direction=TradeDirection.SHORT,
                    confidence=0.7,
                    reason=f"Fast MA {fast_ma:.2f} < Slow MA {slow_ma:.2f}, Price below hourly MA"
                )
        
        # EXIT LOGIC
        if self.position:
            # Exit on MA crossover (reversal)
            if self.position.direction == TradeDirection.LONG and fast_ma < slow_ma:
                logger.info("EXIT signal: Long position MA crossover (fast < slow)")
                return Signal(
                    timestamp=timestamp,
                    symbol=self.symbol,
                    direction=TradeDirection.SHORT,  # Opposite direction signals exit
                    confidence=0.8,
                    reason="Exit: Fast MA < Slow MA (reversal)"
                )
            
            if self.position.direction == TradeDirection.SHORT and fast_ma > slow_ma:
                logger.info("EXIT signal: Short position MA crossover (fast > slow)")
                return Signal(
                    timestamp=timestamp,
                    symbol=self.symbol,
                    direction=TradeDirection.LONG,  # Opposite direction signals exit
                    confidence=0.8,
                    reason="Exit: Fast MA > Slow MA (reversal)"
                )
        
        return None

    def on_trade_entry(
        self,
        symbol: str,
        direction: TradeDirection,
        entry_price: float,
        entry_time: datetime,
        quantity: float,
        atr: float
    ):
        """Record position entry"""
        sl = entry_price - (atr * self.atr_multiplier_sl) if direction == TradeDirection.LONG else entry_price + (atr * self.atr_multiplier_sl)
        tp = entry_price + (atr * self.atr_multiplier_tp) if direction == TradeDirection.LONG else entry_price - (atr * self.atr_multiplier_tp)
        
        self.position = Position(
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            entry_time=entry_time,
            quantity=quantity,
            stop_loss=sl,
            take_profit=tp
        )
        
        logger.info(
            f"Position OPENED: {direction.value} {quantity} {symbol} @ {entry_price:.2f} | "
            f"SL={sl:.2f}, TP={tp:.2f}"
        )
        return self.position

    def on_trade_exit(self, exit_price: float, exit_time: datetime) -> Dict:
        """Record position exit and return trade details"""
        if not self.position:
            logger.warning("Attempted exit with no open position")
            return {}
        
        pnl = (exit_price - self.position.entry_price) * self.position.quantity
        if self.position.direction == TradeDirection.SHORT:
            pnl = -pnl
        
        trade_dict = {
            "symbol": self.position.symbol,
            "direction": self.position.direction.value,
            "entry_price": self.position.entry_price,
            "entry_time": self.position.entry_time,
            "exit_price": exit_price,
            "exit_time": exit_time,
            "quantity": self.position.quantity,
            "pnl": pnl,
            "sl": self.position.stop_loss,
            "tp": self.position.take_profit
        }
        
        logger.info(
            f"Position CLOSED: {self.position.direction.value} {self.position.quantity} "
            f"{self.position.symbol} @ exit {exit_price:.2f} | PnL: {pnl:.2f}"
        )
        
        self.position = None
        return trade_dict

    def check_sl_tp(self, current_price: float) -> Optional[str]:
        """Check if SL or TP has been hit. Returns 'SL' or 'TP' or None"""
        if not self.position:
            return None
        
        if self.position.direction == TradeDirection.LONG:
            if current_price <= self.position.stop_loss:
                return "SL"
            if current_price >= self.position.take_profit:
                return "TP"
        else:  # SHORT
            if current_price >= self.position.stop_loss:
                return "SL"
            if current_price <= self.position.take_profit:
                return "TP"
        
        return None

    def reset(self):
        """Reset strategy state (for new backtest runs)"""
        self.position = None
        logger.debug("Strategy reset")
