"""
기술지표 계산 모듈
"""
import logging
import pandas as pd
import numpy as np
from typing import Dict, Optional
import pyupbit

logger = logging.getLogger(__name__)

def calculate_rsi(prices: pd.Series, period: int = 14) -> float:
    """RSI 계산"""
    if len(prices) < period + 1:
        return 50.0  # 기본값
    
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0

def calculate_bollinger_bands(prices: pd.Series, period: int = 20, std: int = 2) -> Dict[str, float]:
    """볼린저밴드 계산"""
    if len(prices) < period:
        current = float(prices.iloc[-1])
        return {"upper": current * 1.05, "middle": current, "lower": current * 0.95}
    
    middle = prices.rolling(window=period).mean().iloc[-1]
    std_dev = prices.rolling(window=period).std().iloc[-1]
    
    return {
        "upper": float(middle + std * std_dev),
        "middle": float(middle),
        "lower": float(middle - std * std_dev)
    }

def calculate_volume_ratio(volumes: pd.Series, period: int = 24) -> float:
    """거래량 비율 (현재 / 평균)"""
    if len(volumes) < period:
        return 1.0
    
    avg_volume = volumes.iloc[-period:].mean()
    current_volume = volumes.iloc[-1]
    
    return float(current_volume / avg_volume) if avg_volume > 0 else 1.0

def calculate_indicators(ticker: str = "KRW-BTC") -> Optional[Dict]:
    """모든 지표 계산"""
    try:
        # 시간봉 데이터 조회
        df = pyupbit.get_ohlcv(ticker, interval="minute60", count=50)
        if df is None or df.empty:
            return None
        
        current_price = float(df['close'].iloc[-1])
        
        # RSI
        rsi = calculate_rsi(df['close'], 14)
        
        # 볼린저밴드
        bb = calculate_bollinger_bands(df['close'], 20, 2)
        
        # 거래량 비율
        volume_ratio = calculate_volume_ratio(df['volume'], 24)
        
        return {
            "price": current_price,
            "rsi": rsi,
            "bb_upper": bb["upper"],
            "bb_middle": bb["middle"],
            "bb_lower": bb["lower"],
            "volume_ratio": volume_ratio,
            "timestamp": df.index[-1]
        }
    except Exception as e:
        logger.error(f"Indicator calculation error: {e}")
        return None
