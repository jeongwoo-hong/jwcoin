"""
기본적 분석 엔진
"""
import logging
from typing import Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SectorMedians:
    """섹터별 중앙값 (대략적 기준)"""
    pe: float = 20.0
    pb: float = 3.0
    ps: float = 2.5
    ev_ebitda: float = 12.0
    roe: float = 0.15
    debt_equity: float = 0.8


SECTOR_BENCHMARKS = {
    "Technology": SectorMedians(pe=25, pb=5, ps=5, ev_ebitda=15, roe=0.20, debt_equity=0.5),
    "Healthcare": SectorMedians(pe=22, pb=4, ps=4, ev_ebitda=14, roe=0.18, debt_equity=0.6),
    "Financials": SectorMedians(pe=12, pb=1.2, ps=3, ev_ebitda=10, roe=0.12, debt_equity=2.0),
    "Consumer Discretionary": SectorMedians(pe=20, pb=4, ps=1.5, ev_ebitda=12, roe=0.15, debt_equity=1.0),
    "Consumer Staples": SectorMedians(pe=22, pb=5, ps=1.8, ev_ebitda=14, roe=0.20, debt_equity=0.8),
    "Energy": SectorMedians(pe=12, pb=1.5, ps=1.0, ev_ebitda=6, roe=0.10, debt_equity=0.5),
    "Industrials": SectorMedians(pe=18, pb=3, ps=1.5, ev_ebitda=11, roe=0.15, debt_equity=0.8),
    "Materials": SectorMedians(pe=15, pb=2, ps=1.2, ev_ebitda=8, roe=0.12, debt_equity=0.6),
    "Utilities": SectorMedians(pe=18, pb=1.8, ps=2, ev_ebitda=10, roe=0.10, debt_equity=1.2),
    "Real Estate": SectorMedians(pe=35, pb=2, ps=8, ev_ebitda=18, roe=0.08, debt_equity=1.0),
    "Communication Services": SectorMedians(pe=18, pb=3, ps=2.5, ev_ebitda=10, roe=0.15, debt_equity=0.8),
}


class FundamentalAnalyzer:
    """기본적 분석 엔진"""

    def analyze(self, data: Dict, sector: str = "Technology") -> Dict:
        """
        종합 기본적 분석

        Args:
            data: yfinance에서 가져온 펀더멘털 데이터
            sector: 종목 섹터

        Returns:
            분석 결과 딕셔너리
        """
        if not data:
            logger.warning("No fundamental data provided")
            return {}

        try:
            benchmark = SECTOR_BENCHMARKS.get(sector, SectorMedians())

            result = {
                # 원본 데이터
                **data,

                # 밸류에이션 분석
                "valuation": self._analyze_valuation(data, benchmark),

                # 수익성 분석
                "profitability": self._analyze_profitability(data),

                # 성장성 분석
                "growth": self._analyze_growth(data),

                # 재무 건전성
                "financial_health": self._analyze_health(data),

                # 배당 분석
                "dividend": self._analyze_dividend(data),
            }

            # 종합 점수
            result["score"] = self._calculate_score(result)
            result["signal"] = self._generate_signal(result["score"])

            return result

        except Exception as e:
            logger.error(f"Fundamental analysis error: {e}")
            return {}

    def _analyze_valuation(self, data: Dict, benchmark: SectorMedians) -> Dict:
        """밸류에이션 분석"""
        pe = data.get("pe_ratio")
        forward_pe = data.get("forward_pe")
        pb = data.get("pb_ratio")
        ps = data.get("ps_ratio")
        peg = data.get("peg_ratio")
        ev_ebitda = data.get("ev_ebitda")

        result = {
            "pe_ratio": pe,
            "forward_pe": forward_pe,
            "pb_ratio": pb,
            "ps_ratio": ps,
            "peg_ratio": peg,
            "ev_ebitda": ev_ebitda,
        }

        # 섹터 대비 비교
        if pe and benchmark.pe:
            result["pe_vs_sector"] = (pe / benchmark.pe - 1) * 100
            result["pe_signal"] = "undervalued" if pe < benchmark.pe * 0.8 else \
                                  "overvalued" if pe > benchmark.pe * 1.2 else "fair"

        if pb and benchmark.pb:
            result["pb_vs_sector"] = (pb / benchmark.pb - 1) * 100

        if ev_ebitda and benchmark.ev_ebitda:
            result["ev_ebitda_vs_sector"] = (ev_ebitda / benchmark.ev_ebitda - 1) * 100

        # PEG 해석
        if peg:
            if peg < 1:
                result["peg_signal"] = "undervalued"
            elif peg < 2:
                result["peg_signal"] = "fair"
            else:
                result["peg_signal"] = "overvalued"

        # 밸류에이션 점수 (0-100)
        valuation_score = 50
        if pe and benchmark.pe:
            if pe < benchmark.pe * 0.7:
                valuation_score += 25
            elif pe < benchmark.pe:
                valuation_score += 15
            elif pe > benchmark.pe * 1.3:
                valuation_score -= 25
            else:
                valuation_score -= 10

        if peg:
            if peg < 1:
                valuation_score += 15
            elif peg > 2:
                valuation_score -= 15

        result["score"] = max(0, min(100, valuation_score))

        return result

    def _analyze_profitability(self, data: Dict) -> Dict:
        """수익성 분석"""
        gross_margin = data.get("gross_margin")
        operating_margin = data.get("operating_margin")
        profit_margin = data.get("profit_margin")
        roe = data.get("roe")
        roa = data.get("roa")

        result = {
            "gross_margin": gross_margin,
            "operating_margin": operating_margin,
            "profit_margin": profit_margin,
            "roe": roe,
            "roa": roa,
        }

        # 수익성 점수 (0-100)
        score = 50

        if gross_margin:
            if gross_margin > 0.5:
                score += 15
            elif gross_margin > 0.3:
                score += 5
            elif gross_margin < 0.2:
                score -= 10

        if operating_margin:
            if operating_margin > 0.2:
                score += 15
            elif operating_margin > 0.1:
                score += 5
            elif operating_margin < 0.05:
                score -= 15

        if roe:
            if roe > 0.20:
                score += 15
            elif roe > 0.15:
                score += 10
            elif roe > 0.10:
                score += 5
            elif roe < 0.05:
                score -= 15

        result["score"] = max(0, min(100, score))

        # 신호
        if score >= 70:
            result["signal"] = "excellent"
        elif score >= 55:
            result["signal"] = "good"
        elif score >= 40:
            result["signal"] = "average"
        else:
            result["signal"] = "poor"

        return result

    def _analyze_growth(self, data: Dict) -> Dict:
        """성장성 분석"""
        revenue_growth = data.get("revenue_growth")
        earnings_growth = data.get("earnings_growth")

        result = {
            "revenue_growth": revenue_growth,
            "earnings_growth": earnings_growth,
        }

        # 성장성 점수 (0-100)
        score = 50

        if revenue_growth:
            if revenue_growth > 0.3:
                score += 20
            elif revenue_growth > 0.15:
                score += 15
            elif revenue_growth > 0.05:
                score += 5
            elif revenue_growth < 0:
                score -= 20

        if earnings_growth:
            if earnings_growth > 0.3:
                score += 20
            elif earnings_growth > 0.15:
                score += 15
            elif earnings_growth > 0:
                score += 5
            elif earnings_growth < -0.1:
                score -= 25

        result["score"] = max(0, min(100, score))

        # 성장 단계
        if score >= 70:
            result["stage"] = "high_growth"
        elif score >= 55:
            result["stage"] = "growth"
        elif score >= 40:
            result["stage"] = "mature"
        else:
            result["stage"] = "declining"

        return result

    def _analyze_health(self, data: Dict) -> Dict:
        """재무 건전성 분석"""
        current_ratio = data.get("current_ratio")
        debt_equity = data.get("debt_to_equity")
        free_cash_flow = data.get("free_cash_flow")

        result = {
            "current_ratio": current_ratio,
            "debt_to_equity": debt_equity,
            "free_cash_flow": free_cash_flow,
        }

        # 건전성 점수 (0-100)
        score = 50

        if current_ratio:
            if current_ratio > 2:
                score += 15
            elif current_ratio > 1.5:
                score += 10
            elif current_ratio > 1:
                score += 5
            else:
                score -= 20  # 유동성 위험

        if debt_equity is not None:
            if debt_equity < 0.3:
                score += 15
            elif debt_equity < 0.6:
                score += 10
            elif debt_equity < 1:
                score += 5
            elif debt_equity > 2:
                score -= 20  # 과도한 부채

        if free_cash_flow:
            if free_cash_flow > 0:
                score += 15
            else:
                score -= 15  # 현금 소진

        result["score"] = max(0, min(100, score))

        # 건전성 등급
        if score >= 70:
            result["grade"] = "A"
        elif score >= 55:
            result["grade"] = "B"
        elif score >= 40:
            result["grade"] = "C"
        else:
            result["grade"] = "D"

        return result

    def _analyze_dividend(self, data: Dict) -> Dict:
        """배당 분석"""
        dividend_yield = data.get("dividend_yield")
        payout_ratio = data.get("payout_ratio")

        result = {
            "dividend_yield": dividend_yield,
            "payout_ratio": payout_ratio,
            "is_dividend_stock": dividend_yield is not None and dividend_yield > 0,
        }

        if dividend_yield:
            if dividend_yield > 0.04:
                result["yield_category"] = "high"
            elif dividend_yield > 0.02:
                result["yield_category"] = "moderate"
            else:
                result["yield_category"] = "low"

            # 배당 안정성 (payout ratio 기준)
            if payout_ratio:
                if 0.3 <= payout_ratio <= 0.6:
                    result["sustainability"] = "sustainable"
                elif payout_ratio < 0.3:
                    result["sustainability"] = "room_to_grow"
                else:
                    result["sustainability"] = "at_risk"

        return result

    def _calculate_score(self, result: Dict) -> float:
        """종합 점수 계산 (-100 ~ +100)"""
        # 각 카테고리 점수 (0-100)를 (-100 ~ +100)으로 변환
        valuation_score = result.get("valuation", {}).get("score", 50)
        profitability_score = result.get("profitability", {}).get("score", 50)
        growth_score = result.get("growth", {}).get("score", 50)
        health_score = result.get("financial_health", {}).get("score", 50)

        # 가중 평균
        weighted = (
            valuation_score * 0.30 +      # 밸류에이션 30%
            profitability_score * 0.25 +  # 수익성 25%
            growth_score * 0.25 +         # 성장성 25%
            health_score * 0.20           # 건전성 20%
        )

        # 0-100 → -100 ~ +100
        return (weighted - 50) * 2

    def _generate_signal(self, score: float) -> str:
        """매매 신호 생성"""
        if score >= 40:
            return "strong_buy"
        elif score >= 20:
            return "buy"
        elif score <= -40:
            return "strong_sell"
        elif score <= -20:
            return "sell"
        else:
            return "hold"