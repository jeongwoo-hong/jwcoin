"""
기술적 분석 지표 계산
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)


class TechnicalIndicators:
    """기술적 지표 계산기"""

    @staticmethod
    def sma(series: pd.Series, period: int) -> pd.Series:
        """단순 이동평균"""
        return series.rolling(window=period).mean()

    @staticmethod
    def ema(series: pd.Series, period: int) -> pd.Series:
        """지수 이동평균"""
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def rsi(series: pd.Series, period: int = 14) -> pd.Series:
        """RSI (Relative Strength Index)"""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    @staticmethod
    def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
        """MACD"""
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line

        return {
            "macd": macd_line,
            "signal": signal_line,
            "histogram": histogram,
        }

    @staticmethod
    def bollinger_bands(series: pd.Series, period: int = 20, std: float = 2) -> Dict[str, pd.Series]:
        """볼린저 밴드"""
        sma = series.rolling(window=period).mean()
        std_dev = series.rolling(window=period).std()

        upper = sma + (std_dev * std)
        lower = sma - (std_dev * std)

        # 밴드폭 (%B)
        pct_b = (series - lower) / (upper - lower)

        return {
            "upper": upper,
            "middle": sma,
            "lower": lower,
            "pct_b": pct_b,
            "bandwidth": (upper - lower) / sma,
        }

    @staticmethod
    def stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
                   k_period: int = 14, d_period: int = 3) -> Dict[str, pd.Series]:
        """스토캐스틱"""
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()

        k = 100 * (close - lowest_low) / (highest_high - lowest_low)
        d = k.rolling(window=d_period).mean()

        return {"k": k, "d": d}

    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """ATR (Average True Range)"""
        prev_close = close.shift(1)

        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        return atr

    @staticmethod
    def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """OBV (On-Balance Volume)"""
        direction = np.where(close > close.shift(1), 1,
                            np.where(close < close.shift(1), -1, 0))
        return (volume * direction).cumsum()

    @staticmethod
    def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
        """VWAP (Volume Weighted Average Price)"""
        typical_price = (high + low + close) / 3
        return (typical_price * volume).cumsum() / volume.cumsum()

    @staticmethod
    def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> Dict[str, pd.Series]:
        """ADX (Average Directional Index)"""
        plus_dm = high.diff()
        minus_dm = -low.diff()

        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

        atr = TechnicalIndicators.atr(high, low, close, period)

        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()

        return {
            "adx": adx,
            "plus_di": plus_di,
            "minus_di": minus_di,
        }

    @staticmethod
    def cci(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> pd.Series:
        """CCI (Commodity Channel Index)"""
        typical_price = (high + low + close) / 3
        sma = typical_price.rolling(window=period).mean()
        mad = typical_price.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())

        return (typical_price - sma) / (0.015 * mad)

    @staticmethod
    def williams_r(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Williams %R"""
        highest_high = high.rolling(window=period).max()
        lowest_low = low.rolling(window=period).min()

        return -100 * (highest_high - close) / (highest_high - lowest_low)

    @staticmethod
    def roc(series: pd.Series, period: int = 12) -> pd.Series:
        """ROC (Rate of Change)"""
        return ((series - series.shift(period)) / series.shift(period)) * 100


class TechnicalAnalyzer:
    """기술적 분석 엔진"""

    def __init__(self):
        self.indicators = TechnicalIndicators()

    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        종합 기술적 분석

        Args:
            df: OHLCV DataFrame (columns: open, high, low, close, volume)

        Returns:
            분석 결과 딕셔너리
        """
        if df is None or df.empty or len(df) < 50:
            logger.warning("Insufficient data for technical analysis")
            return {}

        try:
            close = df['close']
            high = df['high']
            low = df['low']
            volume = df['volume']

            current_price = close.iloc[-1]

            # 이동평균
            sma_20 = self.indicators.sma(close, 20)
            sma_50 = self.indicators.sma(close, 50)
            sma_200 = self.indicators.sma(close, 200) if len(df) >= 200 else None

            # 모멘텀 지표
            rsi = self.indicators.rsi(close, 14)
            macd_data = self.indicators.macd(close)
            stoch = self.indicators.stochastic(high, low, close)

            # 변동성 지표
            bb = self.indicators.bollinger_bands(close)
            atr = self.indicators.atr(high, low, close)

            # 거래량 지표
            obv = self.indicators.obv(close, volume)
            volume_sma = self.indicators.sma(volume, 20)

            # 추세 강도
            adx_data = self.indicators.adx(high, low, close)

            # 현재 값 추출
            result = {
                # 가격
                "price": current_price,
                "price_change_1d": (current_price / close.iloc[-2] - 1) * 100 if len(df) > 1 else 0,
                "price_change_5d": (current_price / close.iloc[-5] - 1) * 100 if len(df) > 5 else 0,
                "price_change_20d": (current_price / close.iloc[-20] - 1) * 100 if len(df) > 20 else 0,

                # 52주 고저
                "high_52w": high.tail(252).max() if len(df) >= 252 else high.max(),
                "low_52w": low.tail(252).min() if len(df) >= 252 else low.min(),
                "pct_from_high": (current_price / high.tail(252).max() - 1) * 100 if len(df) >= 252 else 0,
                "pct_from_low": (current_price / low.tail(252).min() - 1) * 100 if len(df) >= 252 else 0,

                # 이동평균
                "sma_20": sma_20.iloc[-1],
                "sma_50": sma_50.iloc[-1],
                "sma_200": sma_200.iloc[-1] if sma_200 is not None else None,
                "vs_sma_20": (current_price / sma_20.iloc[-1] - 1) * 100,
                "vs_sma_50": (current_price / sma_50.iloc[-1] - 1) * 100,
                "vs_sma_200": (current_price / sma_200.iloc[-1] - 1) * 100 if sma_200 is not None else None,

                # SMA 정배열 여부
                "sma_bullish_alignment": (
                    sma_20.iloc[-1] > sma_50.iloc[-1] > sma_200.iloc[-1]
                    if sma_200 is not None else sma_20.iloc[-1] > sma_50.iloc[-1]
                ),

                # 골든/데스 크로스 체크
                "golden_cross": self._check_cross(sma_50, sma_200, "golden") if sma_200 is not None else False,
                "death_cross": self._check_cross(sma_50, sma_200, "death") if sma_200 is not None else False,

                # RSI
                "rsi": rsi.iloc[-1],
                "rsi_signal": self._interpret_rsi(rsi.iloc[-1]),

                # MACD
                "macd": macd_data["macd"].iloc[-1],
                "macd_signal": macd_data["signal"].iloc[-1],
                "macd_histogram": macd_data["histogram"].iloc[-1],
                "macd_crossover": self._check_macd_cross(macd_data),

                # 스토캐스틱
                "stoch_k": stoch["k"].iloc[-1],
                "stoch_d": stoch["d"].iloc[-1],

                # 볼린저 밴드
                "bb_upper": bb["upper"].iloc[-1],
                "bb_middle": bb["middle"].iloc[-1],
                "bb_lower": bb["lower"].iloc[-1],
                "bb_pct_b": bb["pct_b"].iloc[-1],
                "bb_bandwidth": bb["bandwidth"].iloc[-1],

                # ATR
                "atr": atr.iloc[-1],
                "atr_pct": (atr.iloc[-1] / current_price) * 100,

                # ADX
                "adx": adx_data["adx"].iloc[-1],
                "plus_di": adx_data["plus_di"].iloc[-1],
                "minus_di": adx_data["minus_di"].iloc[-1],

                # 거래량
                "volume": volume.iloc[-1],
                "volume_sma_20": volume_sma.iloc[-1],
                "volume_ratio": volume.iloc[-1] / volume_sma.iloc[-1] if volume_sma.iloc[-1] > 0 else 1,

                # OBV 추세
                "obv_trend": "up" if obv.iloc[-1] > obv.iloc[-5] else "down",
            }

            # 지지/저항 계산
            support, resistance = self._find_support_resistance(df)
            result["support_1"] = support[0] if support else None
            result["support_2"] = support[1] if len(support) > 1 else None
            result["resistance_1"] = resistance[0] if resistance else None
            result["resistance_2"] = resistance[1] if len(resistance) > 1 else None

            # 종합 해석
            result["trend"] = self._determine_trend(result)
            result["signal"] = self._generate_signal(result)
            result["score"] = self._calculate_score(result)

            return result

        except Exception as e:
            logger.error(f"Technical analysis error: {e}")
            return {}

    def _interpret_rsi(self, rsi: float) -> str:
        """RSI 해석"""
        if rsi >= 70:
            return "overbought"
        elif rsi <= 30:
            return "oversold"
        else:
            return "neutral"

    def _check_cross(self, fast: pd.Series, slow: pd.Series, cross_type: str) -> bool:
        """골든/데스 크로스 체크"""
        if slow is None or len(fast) < 5:
            return False

        if cross_type == "golden":
            # 최근 5일 내 골든 크로스
            for i in range(-5, 0):
                if fast.iloc[i-1] <= slow.iloc[i-1] and fast.iloc[i] > slow.iloc[i]:
                    return True
        elif cross_type == "death":
            for i in range(-5, 0):
                if fast.iloc[i-1] >= slow.iloc[i-1] and fast.iloc[i] < slow.iloc[i]:
                    return True

        return False

    def _check_macd_cross(self, macd_data: Dict) -> Optional[str]:
        """MACD 크로스 체크"""
        macd = macd_data["macd"]
        signal = macd_data["signal"]

        if len(macd) < 3:
            return None

        # 최근 3일 내 크로스
        for i in range(-3, 0):
            if macd.iloc[i-1] <= signal.iloc[i-1] and macd.iloc[i] > signal.iloc[i]:
                return "bullish"
            if macd.iloc[i-1] >= signal.iloc[i-1] and macd.iloc[i] < signal.iloc[i]:
                return "bearish"

        return None

    def _find_support_resistance(self, df: pd.DataFrame, lookback: int = 60) -> Tuple[List[float], List[float]]:
        """지지/저항 레벨 찾기"""
        recent = df.tail(lookback)
        high = recent['high']
        low = recent['low']
        close = recent['close']

        current_price = close.iloc[-1]

        # 로컬 최저점 (지지)
        supports = []
        for i in range(2, len(low) - 2):
            if low.iloc[i] < low.iloc[i-1] and low.iloc[i] < low.iloc[i-2] and \
               low.iloc[i] < low.iloc[i+1] and low.iloc[i] < low.iloc[i+2]:
                if low.iloc[i] < current_price:
                    supports.append(low.iloc[i])

        # 로컬 최고점 (저항)
        resistances = []
        for i in range(2, len(high) - 2):
            if high.iloc[i] > high.iloc[i-1] and high.iloc[i] > high.iloc[i-2] and \
               high.iloc[i] > high.iloc[i+1] and high.iloc[i] > high.iloc[i+2]:
                if high.iloc[i] > current_price:
                    resistances.append(high.iloc[i])

        # 가장 가까운 순으로 정렬
        supports = sorted(set(supports), reverse=True)[:3]
        resistances = sorted(set(resistances))[:3]

        return supports, resistances

    def _determine_trend(self, data: Dict) -> str:
        """추세 판단"""
        bullish_signals = 0
        bearish_signals = 0

        # SMA 정배열
        if data.get("sma_bullish_alignment"):
            bullish_signals += 2
        else:
            bearish_signals += 1

        # 가격 위치
        if data.get("vs_sma_200") is not None:
            if data["vs_sma_200"] > 0:
                bullish_signals += 1
            else:
                bearish_signals += 1

        # ADX
        if data.get("adx", 0) > 25:
            if data.get("plus_di", 0) > data.get("minus_di", 0):
                bullish_signals += 1
            else:
                bearish_signals += 1

        # MACD
        if data.get("macd_histogram", 0) > 0:
            bullish_signals += 1
        else:
            bearish_signals += 1

        if bullish_signals > bearish_signals + 1:
            return "bullish"
        elif bearish_signals > bullish_signals + 1:
            return "bearish"
        else:
            return "neutral"

    def _generate_signal(self, data: Dict) -> str:
        """매매 신호 생성"""
        score = data.get("score", 0)

        if score >= 60:
            return "strong_buy"
        elif score >= 30:
            return "buy"
        elif score <= -60:
            return "strong_sell"
        elif score <= -30:
            return "sell"
        else:
            return "hold"

    def _calculate_score(self, data: Dict) -> float:
        """기술적 분석 점수 계산 (-100 ~ +100)"""
        score = 0

        # RSI (±20)
        rsi = data.get("rsi", 50)
        if rsi <= 30:
            score += 20  # 과매도 = 매수 기회
        elif rsi >= 70:
            score -= 20  # 과매수 = 매도 고려
        elif rsi < 50:
            score += 5
        else:
            score -= 5

        # MACD (±20)
        if data.get("macd_crossover") == "bullish":
            score += 20
        elif data.get("macd_crossover") == "bearish":
            score -= 20
        elif data.get("macd_histogram", 0) > 0:
            score += 10
        else:
            score -= 10

        # 추세 (±25)
        trend = data.get("trend")
        if trend == "bullish":
            score += 25
        elif trend == "bearish":
            score -= 25

        # SMA 위치 (±15)
        vs_sma_200 = data.get("vs_sma_200")
        if vs_sma_200 is not None:
            if vs_sma_200 > 10:
                score += 15
            elif vs_sma_200 > 0:
                score += 10
            elif vs_sma_200 > -10:
                score -= 10
            else:
                score -= 15

        # 볼린저 밴드 (±10)
        pct_b = data.get("bb_pct_b", 0.5)
        if pct_b < 0.2:
            score += 10  # 하단 근처 = 매수 기회
        elif pct_b > 0.8:
            score -= 10  # 상단 근처 = 과열

        # 거래량 (±10)
        volume_ratio = data.get("volume_ratio", 1)
        obv_trend = data.get("obv_trend")
        if volume_ratio > 1.5 and obv_trend == "up":
            score += 10
        elif volume_ratio > 1.5 and obv_trend == "down":
            score -= 10

        return max(-100, min(100, score))