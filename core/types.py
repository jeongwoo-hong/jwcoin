"""
공통 타입 정의
"""
from enum import Enum


class TradeDecision(str, Enum):
    """거래 결정 타입"""
    BUY = "buy"
    SELL = "sell"
    PARTIAL_SELL = "partial_sell"
    HOLD = "hold"

    def __str__(self):
        return self.value