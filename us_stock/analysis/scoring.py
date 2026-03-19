"""
종합 점수 시스템
모든 분석 축을 통합하여 최종 투자 점수 산출
"""
import logging
from typing import Dict, Optional, List
from datetime import datetime

from .technical.indicators import TechnicalAnalyzer
from .fundamental.analyzer import FundamentalAnalyzer
from .sentiment.analyzer import SentimentAnalyzer
from .macro.analyzer import MacroAnalyzer
from ..config import settings

logger = logging.getLogger(__name__)


class ComprehensiveScorer:
    """종합 점수 시스템"""

    # 설정에서 가중치와 점수 해석 가져오기
    WEIGHTS = settings.ANALYSIS_WEIGHTS
    SCORE_INTERPRETATION = settings.SCORE_INTERPRETATION

    def __init__(self):
        self.technical = TechnicalAnalyzer()
        self.fundamental = FundamentalAnalyzer()
        self.sentiment = SentimentAnalyzer()
        self.macro = MacroAnalyzer()

    def analyze(
        self,
        symbol: str,
        price_data,  # DataFrame
        fundamental_data: Dict,
        news: List[Dict],
        analyst_ratings: Dict,
        price_target: Dict,
        insider_trades: List[Dict],
        market_indices: Dict,
        treasury_yields: Dict,
        sector_performance: Dict,
        sector: str,
    ) -> Dict:
        """
        종합 분석 실행

        Returns:
            종합 분석 결과 딕셔너리
        """
        try:
            result = {
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
            }

            # 1. 기술적 분석
            tech_result = self.technical.analyze(price_data)
            result["technical"] = tech_result
            tech_score = tech_result.get("score", 0)

            # 2. 기본적 분석
            fund_result = self.fundamental.analyze(fundamental_data, sector)
            result["fundamental"] = fund_result
            fund_score = fund_result.get("score", 0)

            # 3. 센티멘트 분석
            current_price = tech_result.get("price", 0)
            sent_result = self.sentiment.analyze(
                news=news,
                analyst_ratings=analyst_ratings,
                price_target=price_target,
                insider_trades=insider_trades,
                current_price=current_price,
            )
            result["sentiment"] = sent_result
            sent_score = sent_result.get("score", 0)

            # 4. 거시경제 분석
            macro_result = self.macro.analyze(
                indices=market_indices,
                treasury_yields=treasury_yields,
                sector_performance=sector_performance,
                target_sector=sector,
            )
            result["macro"] = macro_result
            macro_score = macro_result.get("score", 0)

            # 5. 퀄리티 점수 (기본적 분석에서 추출)
            quality_score = self._calculate_quality_score(fundamental_data)
            result["quality"] = {"score": quality_score}

            # 6. 종합 점수 계산
            component_scores = {
                "technical": tech_score,
                "fundamental": fund_score,
                "sentiment": sent_score,
                "macro": macro_score,
                "quality": quality_score,
            }

            composite_score = self._calculate_composite_score(component_scores)
            adjusted_score = self._apply_adjustments(composite_score, component_scores, result)

            result["component_scores"] = component_scores
            result["composite_score"] = composite_score
            result["adjusted_score"] = adjusted_score
            result["signal"] = self._interpret_score(adjusted_score)
            result["confidence"] = self._calculate_confidence(component_scores)

            # 7. 투자 결정 생성
            result["decision"] = self._generate_decision(result)

            return result

        except Exception as e:
            logger.error(f"Comprehensive analysis error for {symbol}: {e}")
            return {
                "symbol": symbol,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def _calculate_quality_score(self, data: Dict) -> float:
        """퀄리티 점수 계산"""
        if not data:
            return 0

        score = 0

        # ROE 안정성
        roe = data.get("roe")
        if roe:
            if roe > 0.20:
                score += 30
            elif roe > 0.15:
                score += 20
            elif roe > 0.10:
                score += 10
            elif roe < 0:
                score -= 20

        # 마진 안정성
        operating_margin = data.get("operating_margin")
        if operating_margin:
            if operating_margin > 0.20:
                score += 25
            elif operating_margin > 0.10:
                score += 15
            elif operating_margin > 0:
                score += 5
            else:
                score -= 20

        # 부채 수준
        debt_equity = data.get("debt_to_equity")
        if debt_equity is not None:
            if debt_equity < 0.3:
                score += 25
            elif debt_equity < 0.6:
                score += 15
            elif debt_equity < 1:
                score += 5
            else:
                score -= 15

        # FCF 양수 여부
        fcf = data.get("free_cash_flow")
        if fcf:
            if fcf > 0:
                score += 20
            else:
                score -= 20

        # -100 ~ +100 범위로 정규화
        return max(-100, min(100, score))

    def _calculate_composite_score(self, scores: Dict) -> float:
        """가중 평균 점수 계산"""
        weighted_sum = 0

        for component, score in scores.items():
            weight = self.WEIGHTS.get(component, 0)
            weighted_sum += score * weight

        return weighted_sum

    def _apply_adjustments(self, score: float, components: Dict, result: Dict) -> float:
        """점수 조정 (극단적 상황 반영)"""
        adjusted = score

        # 기본적 분석이 매우 부정적이면 페널티 (-50 이하)
        if components.get("fundamental", 0) < -50:
            adjusted *= 0.7
            logger.debug("Fundamental penalty applied")

        # 거시경제가 리스크 오프면 하향
        macro_regime = result.get("macro", {}).get("regime")
        if macro_regime == "risk_off":
            adjusted -= 15
            logger.debug("Macro risk-off adjustment applied")

        # 기술적 + 센티멘트 동시 부정적이면 추가 하향
        if components.get("technical", 0) < -30 and components.get("sentiment", 0) < -30:
            adjusted -= 10
            logger.debug("Technical + Sentiment negative adjustment applied")

        # VIX 높으면 보수적으로
        vix = result.get("macro", {}).get("market", {}).get("vix", 20)
        if vix > 30:
            adjusted *= 0.9
            logger.debug("High VIX adjustment applied")

        return max(-100, min(100, adjusted))

    def _interpret_score(self, score: float) -> str:
        """점수 해석"""
        for (low, high), signal in self.SCORE_INTERPRETATION.items():
            if low <= score < high:
                return signal
        return "hold"

    def _calculate_confidence(self, scores: Dict) -> float:
        """확신도 계산 (0.0 ~ 1.0)"""
        # 모든 지표가 같은 방향이면 높은 확신도
        signs = []
        for v in scores.values():
            if v > 10:
                signs.append(1)
            elif v < -10:
                signs.append(-1)
            else:
                signs.append(0)

        # 일치도
        if len(set(signs)) == 1 and signs[0] != 0:
            agreement = 1.0
        else:
            positive = signs.count(1)
            negative = signs.count(-1)
            agreement = max(positive, negative) / len(signs)

        # 점수 크기
        avg_magnitude = sum(abs(v) for v in scores.values()) / len(scores)
        magnitude_factor = min(1.0, avg_magnitude / 50)

        confidence = (agreement * 0.6 + magnitude_factor * 0.4)

        return round(confidence, 2)

    def _generate_decision(self, result: Dict) -> Dict:
        """투자 결정 생성"""
        score = result.get("adjusted_score", 0)
        signal = result.get("signal", "hold")
        confidence = result.get("confidence", 0.5)

        # 기본 결정
        if signal in ["strong_buy", "buy"]:
            decision = "buy"
        elif signal in ["strong_sell", "sell"]:
            decision = "sell"
        elif signal == "lean_buy" and confidence > 0.6:
            decision = "buy"
        elif signal == "lean_sell" and confidence > 0.6:
            decision = "sell"
        else:
            decision = "hold"

        # 비중 계산 (확신도 기반)
        if decision == "buy":
            if confidence > 0.8 and score > 50:
                percentage = 5  # 최대 비중
            elif confidence > 0.6:
                percentage = 3
            else:
                percentage = 2
        elif decision == "sell":
            if confidence > 0.8 and score < -50:
                percentage = 100  # 전량 매도
            elif confidence > 0.6:
                percentage = 50
            else:
                percentage = 30
        else:
            percentage = 0

        # 주요 요인 추출
        key_factors = self._extract_key_factors(result)
        risks = self._extract_risks(result)

        return {
            "decision": decision,
            "percentage": percentage,
            "confidence": confidence,
            "score": score,
            "signal": signal,
            "key_factors": key_factors,
            "risks": risks,
        }

    def _extract_key_factors(self, result: Dict) -> List[str]:
        """주요 긍정/부정 요인 추출"""
        factors = []

        # 기술적 요인
        tech = result.get("technical", {})
        if tech.get("trend") == "bullish":
            factors.append("Strong uptrend with bullish SMA alignment")
        elif tech.get("trend") == "bearish":
            factors.append("Downtrend with bearish technical indicators")
        if tech.get("rsi_signal") == "oversold":
            factors.append("RSI indicates oversold condition (potential bounce)")
        elif tech.get("rsi_signal") == "overbought":
            factors.append("RSI indicates overbought condition (potential pullback)")

        # 기본적 요인
        fund = result.get("fundamental", {})
        valuation = fund.get("valuation", {})
        if valuation.get("pe_signal") == "undervalued":
            factors.append("Trading below sector average P/E (undervalued)")
        elif valuation.get("pe_signal") == "overvalued":
            factors.append("Trading above sector average P/E (expensive)")

        growth = fund.get("growth", {})
        if growth.get("stage") == "high_growth":
            factors.append("High revenue and earnings growth")
        elif growth.get("stage") == "declining":
            factors.append("Declining revenue/earnings growth")

        # 센티멘트 요인
        sent = result.get("sentiment", {})
        analyst = sent.get("analyst", {})
        if analyst.get("consensus") in ["strong_buy", "buy"]:
            factors.append(f"Positive analyst consensus ({analyst.get('consensus')})")

        target = sent.get("target", {})
        upside = target.get("upside")
        if upside and upside > 20:
            factors.append(f"Analyst target price {upside:.0f}% above current")
        elif upside and upside < -10:
            factors.append(f"Trading above analyst target price")

        insider = sent.get("insider", {})
        if insider.get("signal") == "strong_positive":
            factors.append("Significant insider buying activity")
        elif insider.get("signal") == "strong_negative":
            factors.append("Significant insider selling activity")

        return factors[:5]  # 상위 5개

    def _extract_risks(self, result: Dict) -> List[str]:
        """주요 리스크 추출"""
        risks = []

        # 거시경제 리스크
        macro = result.get("macro", {})
        if macro.get("risk_level") in ["high", "extreme"]:
            risks.append(f"High market risk environment (VIX elevated)")

        signal = macro.get("signal", {})
        warnings = signal.get("warnings", [])
        risks.extend(warnings)

        # 기술적 리스크
        tech = result.get("technical", {})
        pct_from_high = tech.get("pct_from_high", 0)
        if pct_from_high > -5:
            risks.append("Trading near 52-week high (limited upside)")

        # 기본적 리스크
        fund = result.get("fundamental", {})
        health = fund.get("financial_health", {})
        if health.get("grade") == "D":
            risks.append("Weak financial health (high debt or low liquidity)")

        # 센티멘트 리스크
        sent = result.get("sentiment", {})
        news = sent.get("news", {})
        if news.get("signal") == "negative":
            risks.append("Negative news sentiment")

        return risks[:5]  # 상위 5개