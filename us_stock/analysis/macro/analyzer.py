"""
거시경제 분석 엔진
"""
import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MacroAnalyzer:
    """거시경제 분석 엔진"""

    def analyze(
        self,
        indices: Dict = None,
        treasury_yields: Dict = None,
        sector_performance: Dict = None,
        target_sector: str = None,
    ) -> Dict:
        """
        종합 거시경제 분석

        Args:
            indices: 시장 지수 데이터
            treasury_yields: 국채 수익률
            sector_performance: 섹터별 성과
            target_sector: 분석 대상 종목의 섹터

        Returns:
            분석 결과 딕셔너리
        """
        result = {}

        # 시장 상황 분석
        if indices:
            result["market"] = self._analyze_market(indices)
        else:
            result["market"] = {"regime": "unknown", "risk_level": "medium"}

        # 금리 환경 분석
        if treasury_yields:
            result["rates"] = self._analyze_rates(treasury_yields)
        else:
            result["rates"] = {"environment": "unknown"}

        # 섹터 분석
        if sector_performance:
            result["sectors"] = self._analyze_sectors(sector_performance, target_sector)
        else:
            result["sectors"] = {}

        # 종합 평가
        result["regime"] = self._determine_regime(result)
        result["risk_level"] = self._assess_risk(result)
        result["recommended_exposure"] = self._calculate_exposure(result)

        # 점수
        result["score"] = self._calculate_score(result)
        result["signal"] = self._generate_signal(result)

        return result

    def _analyze_market(self, indices: Dict) -> Dict:
        """시장 지수 분석"""
        sp500 = indices.get("S&P 500", {})
        nasdaq = indices.get("NASDAQ", {})
        vix = indices.get("VIX", {})

        sp500_change = sp500.get("change_pct", 0)
        nasdaq_change = nasdaq.get("change_pct", 0)
        vix_level = vix.get("price", 20)

        # 시장 방향
        if sp500_change > 1:
            market_direction = "strong_up"
        elif sp500_change > 0:
            market_direction = "up"
        elif sp500_change > -1:
            market_direction = "down"
        else:
            market_direction = "strong_down"

        # VIX 해석
        if vix_level < 15:
            vix_signal = "complacent"
        elif vix_level < 20:
            vix_signal = "normal"
        elif vix_level < 30:
            vix_signal = "elevated"
        elif vix_level < 40:
            vix_signal = "high"
        else:
            vix_signal = "extreme"

        # 시장 레짐
        if vix_level < 20 and sp500_change >= 0:
            regime = "risk_on"
        elif vix_level > 30 or sp500_change < -2:
            regime = "risk_off"
        else:
            regime = "neutral"

        return {
            "sp500_change": sp500_change,
            "nasdaq_change": nasdaq_change,
            "vix": vix_level,
            "vix_signal": vix_signal,
            "direction": market_direction,
            "regime": regime,
        }

    def _analyze_rates(self, yields: Dict) -> Dict:
        """금리 환경 분석"""
        ten_year = yields.get("10Y", 4.0)
        two_year = yields.get("2Y", 4.0) if "2Y" in yields else None
        three_month = yields.get("3M", 4.0) if "3M" in yields else None

        result = {
            "treasury_10y": ten_year,
        }

        # 장단기 금리차 (yield curve)
        if two_year:
            spread_10y2y = ten_year - two_year
            result["yield_curve_10y2y"] = spread_10y2y

            if spread_10y2y < -0.5:
                result["curve_signal"] = "deeply_inverted"  # 경기 침체 경고
            elif spread_10y2y < 0:
                result["curve_signal"] = "inverted"  # 주의
            elif spread_10y2y < 0.5:
                result["curve_signal"] = "flat"
            else:
                result["curve_signal"] = "normal"

        # 금리 수준
        if ten_year > 5:
            result["rate_level"] = "high"
            result["equity_impact"] = "negative"
        elif ten_year > 4:
            result["rate_level"] = "elevated"
            result["equity_impact"] = "neutral_negative"
        elif ten_year > 3:
            result["rate_level"] = "moderate"
            result["equity_impact"] = "neutral"
        else:
            result["rate_level"] = "low"
            result["equity_impact"] = "positive"

        return result

    def _analyze_sectors(self, performance: Dict, target_sector: str = None) -> Dict:
        """섹터 분석"""
        result = {
            "performance": performance,
            "leaders": [],
            "laggards": [],
        }

        # 성과순 정렬
        sorted_sectors = sorted(
            performance.items(),
            key=lambda x: x[1].get("change_pct", 0),
            reverse=True
        )

        result["leaders"] = [s[0] for s in sorted_sectors[:3]]
        result["laggards"] = [s[0] for s in sorted_sectors[-3:]]

        # 대상 섹터 상대 강도
        if target_sector and target_sector in performance:
            sector_perf = performance[target_sector].get("change_pct", 0)

            # 전체 평균
            avg_perf = sum(s[1].get("change_pct", 0) for s in sorted_sectors) / len(sorted_sectors)
            relative_strength = sector_perf - avg_perf

            result["target_sector"] = target_sector
            result["target_performance"] = sector_perf
            result["relative_strength"] = relative_strength

            if relative_strength > 1:
                result["target_signal"] = "outperforming"
            elif relative_strength < -1:
                result["target_signal"] = "underperforming"
            else:
                result["target_signal"] = "inline"

        # 섹터 순환 단계 추정
        # (간단한 휴리스틱 - 실제로는 더 복잡한 분석 필요)
        defensive = ["Consumer Staples", "Utilities", "Healthcare"]
        cyclical = ["Technology", "Consumer Discretionary", "Financials"]

        defensive_avg = sum(
            performance.get(s, {}).get("change_pct", 0) for s in defensive
        ) / len(defensive)
        cyclical_avg = sum(
            performance.get(s, {}).get("change_pct", 0) for s in cyclical
        ) / len(cyclical)

        if cyclical_avg > defensive_avg + 0.5:
            result["rotation_phase"] = "early_cycle"  # 경기 회복
        elif defensive_avg > cyclical_avg + 0.5:
            result["rotation_phase"] = "late_cycle"  # 경기 후반
        else:
            result["rotation_phase"] = "mid_cycle"

        return result

    def _determine_regime(self, result: Dict) -> str:
        """시장 레짐 결정"""
        market_regime = result.get("market", {}).get("regime", "neutral")
        curve_signal = result.get("rates", {}).get("curve_signal", "normal")
        rotation = result.get("sectors", {}).get("rotation_phase", "mid_cycle")

        # 리스크 오프 조건
        if market_regime == "risk_off":
            return "risk_off"
        if curve_signal in ["inverted", "deeply_inverted"]:
            return "cautious"
        if rotation == "late_cycle":
            return "late_cycle"

        # 리스크 온 조건
        if market_regime == "risk_on" and curve_signal == "normal":
            return "risk_on"
        if rotation == "early_cycle":
            return "early_cycle"

        return "neutral"

    def _assess_risk(self, result: Dict) -> str:
        """리스크 수준 평가"""
        vix = result.get("market", {}).get("vix", 20)
        vix_signal = result.get("market", {}).get("vix_signal", "normal")
        curve_signal = result.get("rates", {}).get("curve_signal", "normal")

        risk_score = 0

        # VIX 기반
        if vix_signal == "extreme":
            risk_score += 4
        elif vix_signal == "high":
            risk_score += 3
        elif vix_signal == "elevated":
            risk_score += 2
        elif vix_signal == "complacent":
            risk_score += 1  # 너무 낮은 VIX도 주의

        # 금리 곡선
        if curve_signal in ["inverted", "deeply_inverted"]:
            risk_score += 2

        # 등급
        if risk_score >= 5:
            return "extreme"
        elif risk_score >= 3:
            return "high"
        elif risk_score >= 2:
            return "medium"
        else:
            return "low"

    def _calculate_exposure(self, result: Dict) -> float:
        """권장 노출도 계산 (0.0 ~ 1.0)"""
        risk_level = result.get("risk_level", "medium")
        regime = result.get("regime", "neutral")

        base_exposure = 1.0

        # 리스크 수준에 따른 조정
        if risk_level == "extreme":
            base_exposure *= 0.3
        elif risk_level == "high":
            base_exposure *= 0.5
        elif risk_level == "medium":
            base_exposure *= 0.8

        # 레짐에 따른 조정
        if regime == "risk_off":
            base_exposure *= 0.5
        elif regime == "cautious":
            base_exposure *= 0.7
        elif regime == "risk_on":
            base_exposure *= 1.1

        return min(1.0, max(0.2, base_exposure))

    def _calculate_score(self, result: Dict) -> float:
        """종합 점수 계산 (-100 ~ +100)"""
        score = 0

        # 시장 방향 (±30)
        direction = result.get("market", {}).get("direction", "neutral")
        if direction == "strong_up":
            score += 30
        elif direction == "up":
            score += 15
        elif direction == "down":
            score -= 15
        elif direction == "strong_down":
            score -= 30

        # VIX (±25)
        vix_signal = result.get("market", {}).get("vix_signal", "normal")
        if vix_signal == "normal":
            score += 10
        elif vix_signal == "complacent":
            score += 5  # 너무 낮은 것도 좋지 않음
        elif vix_signal == "elevated":
            score -= 10
        elif vix_signal == "high":
            score -= 20
        elif vix_signal == "extreme":
            score -= 25

        # 금리 환경 (±20)
        equity_impact = result.get("rates", {}).get("equity_impact", "neutral")
        if equity_impact == "positive":
            score += 20
        elif equity_impact == "neutral":
            score += 5
        elif equity_impact == "neutral_negative":
            score -= 10
        elif equity_impact == "negative":
            score -= 20

        # 수익률 곡선 (±15)
        curve_signal = result.get("rates", {}).get("curve_signal", "normal")
        if curve_signal == "normal":
            score += 15
        elif curve_signal == "flat":
            score += 0
        elif curve_signal == "inverted":
            score -= 10
        elif curve_signal == "deeply_inverted":
            score -= 15

        # 섹터 상대 강도 (±10)
        target_signal = result.get("sectors", {}).get("target_signal")
        if target_signal == "outperforming":
            score += 10
        elif target_signal == "underperforming":
            score -= 10

        return max(-100, min(100, score))

    def _generate_signal(self, result: Dict) -> Dict:
        """종합 신호 생성"""
        score = result.get("score", 0)
        regime = result.get("regime", "neutral")
        risk_level = result.get("risk_level", "medium")

        # 점수 기반 신호
        if score >= 40:
            signal = "bullish"
        elif score >= 10:
            signal = "slightly_bullish"
        elif score <= -40:
            signal = "bearish"
        elif score <= -10:
            signal = "slightly_bearish"
        else:
            signal = "neutral"

        # 경고
        warnings = []
        if risk_level in ["high", "extreme"]:
            warnings.append(f"High market risk ({risk_level})")
        if regime == "risk_off":
            warnings.append("Risk-off environment")
        if result.get("rates", {}).get("curve_signal") in ["inverted", "deeply_inverted"]:
            warnings.append("Inverted yield curve - recession risk")

        return {
            "signal": signal,
            "regime": regime,
            "risk_level": risk_level,
            "recommended_exposure": result.get("recommended_exposure", 0.8),
            "warnings": warnings,
        }