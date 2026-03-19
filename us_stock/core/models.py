"""
데이터 모델 정의
"""
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum


class Decision(str, Enum):
    """거래 결정 유형"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    REDUCE = "reduce"           # 일부 매도
    ACCUMULATE = "accumulate"   # 추가 매수


class TimeHorizon(str, Enum):
    """투자 기간"""
    DAY = "day"
    SWING = "swing"             # 2-10일
    POSITION = "position"       # 2주-3개월
    LONG_TERM = "long_term"     # 3개월+


class TradingDecision(BaseModel):
    """개별 종목 거래 결정"""
    symbol: str
    decision: Decision
    quantity: int = 0                      # 주 수
    percentage: int = 0                    # 포지션 비중 (0-100)
    confidence: int = 5                    # 확신도 (1-10)
    time_horizon: TimeHorizon = TimeHorizon.POSITION
    entry_price: Optional[float] = None    # 진입가
    stop_loss: Optional[float] = None      # 손절가
    take_profit: Optional[List[float]] = None  # 목표가 (복수)
    reason: str = ""                       # 판단 이유
    risks: List[str] = []                  # 주요 리스크
    model: str = ""                        # 사용된 AI 모델


class PortfolioDecision(BaseModel):
    """포트폴리오 전체 결정"""
    timestamp: datetime
    rebalance_needed: bool = False
    actions: List[TradingDecision] = []
    cash_allocation: float = 0.10          # 현금 비중
    sector_adjustments: Dict[str, float] = {}  # 섹터별 조정
    risk_assessment: str = ""              # 리스크 평가
    overall_strategy: str = ""             # 전체 전략
    model: str = ""


class StockAnalysis(BaseModel):
    """종목 분석 결과"""
    symbol: str
    timestamp: datetime

    # 종합 점수
    composite_score: float = 0             # -100 ~ +100
    technical_score: float = 0
    fundamental_score: float = 0
    sentiment_score: float = 0
    macro_score: float = 0
    quality_score: float = 0

    # 밸류에이션
    current_price: float = 0
    fair_value: Optional[float] = None
    margin_of_safety: Optional[float] = None  # (공정가치 - 현재가) / 공정가치

    # 기술적 지표 요약
    trend: str = ""                        # bullish/bearish/neutral
    rsi: float = 0
    macd_signal: str = ""
    support: Optional[float] = None
    resistance: Optional[float] = None

    # 펀더멘털 요약
    pe_ratio: Optional[float] = None
    peg_ratio: Optional[float] = None
    roe: Optional[float] = None
    debt_to_equity: Optional[float] = None

    # 센티멘트 요약
    news_sentiment: float = 0              # -1 ~ +1
    analyst_consensus: str = ""            # strong_buy/buy/hold/sell/strong_sell
    target_price: Optional[float] = None
    short_interest: Optional[float] = None

    # 해석
    signal: str = ""                       # strong_buy/buy/hold/sell/strong_sell
    key_factors: List[str] = []
    risks: List[str] = []


class Position(BaseModel):
    """보유 포지션"""
    symbol: str
    quantity: int
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    weight: float                          # 포트폴리오 내 비중
    sector: str
    holding_days: int = 0


class Portfolio(BaseModel):
    """포트폴리오 현황"""
    timestamp: datetime
    total_value: float
    cash: float
    cash_pct: float
    positions: List[Position] = []
    sector_weights: Dict[str, float] = {}
    total_unrealized_pnl: float = 0
    total_unrealized_pnl_pct: float = 0
    daily_pnl: float = 0
    daily_pnl_pct: float = 0


class MarketCondition(BaseModel):
    """시장 상황"""
    timestamp: datetime

    # 지수
    sp500_price: float = 0
    sp500_change_pct: float = 0
    sp500_vs_200sma: float = 0
    nasdaq_change_pct: float = 0
    vix: float = 0

    # 금리
    treasury_10y: float = 0
    yield_curve_10y2y: float = 0

    # 경제
    fed_funds_rate: float = 0

    # 해석
    regime: str = ""                       # risk_on/risk_off/neutral
    risk_level: str = ""                   # low/medium/high/extreme
    recommended_exposure: float = 1.0      # 0-1 (비중 조절 계수)