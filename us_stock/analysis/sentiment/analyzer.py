"""
센티멘트 분석 엔진
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """센티멘트 분석 엔진"""

    # 긍정/부정 키워드
    POSITIVE_KEYWORDS = [
        "beat", "beats", "exceeds", "exceeded", "surge", "surges", "rally",
        "upgrade", "upgraded", "buy", "outperform", "bullish", "growth",
        "profit", "gains", "rises", "climbs", "record", "high", "strong",
        "positive", "success", "breakthrough", "innovation", "partnership",
    ]

    NEGATIVE_KEYWORDS = [
        "miss", "misses", "missed", "falls", "drops", "plunges", "crash",
        "downgrade", "downgraded", "sell", "underperform", "bearish", "decline",
        "loss", "losses", "tumbles", "warning", "concern", "weak", "negative",
        "lawsuit", "investigation", "fraud", "recall", "layoffs", "bankruptcy",
    ]

    def analyze(
        self,
        news: List[Dict] = None,
        analyst_ratings: Dict = None,
        price_target: Dict = None,
        insider_trades: List[Dict] = None,
        current_price: float = None,
    ) -> Dict:
        """
        종합 센티멘트 분석

        Args:
            news: 뉴스 리스트
            analyst_ratings: 애널리스트 평가
            price_target: 목표가
            insider_trades: 내부자 거래
            current_price: 현재 가격

        Returns:
            분석 결과 딕셔너리
        """
        result = {}

        # 뉴스 센티멘트
        if news:
            result["news"] = self._analyze_news(news)
        else:
            result["news"] = {"score": 0, "signal": "neutral", "count": 0}

        # 애널리스트 센티멘트
        if analyst_ratings:
            result["analyst"] = self._analyze_analyst(analyst_ratings)
        else:
            result["analyst"] = {"score": 0, "signal": "neutral"}

        # 목표가 분석
        if price_target and current_price:
            result["target"] = self._analyze_target(price_target, current_price)
        else:
            result["target"] = {"upside": None, "signal": "neutral"}

        # 내부자 거래 분석
        if insider_trades:
            result["insider"] = self._analyze_insider(insider_trades)
        else:
            result["insider"] = {"signal": "neutral", "net_activity": 0}

        # 종합 점수
        result["score"] = self._calculate_score(result)
        result["signal"] = self._generate_signal(result["score"])

        return result

    def _analyze_news(self, news: List[Dict]) -> Dict:
        """뉴스 센티멘트 분석"""
        if not news:
            return {"score": 0, "signal": "neutral", "count": 0}

        total_score = 0
        headlines = []

        for article in news[:20]:  # 최근 20개
            headline = article.get("headline", "").lower()
            summary = article.get("summary", "").lower()
            text = headline + " " + summary

            # 키워드 기반 점수
            positive_count = sum(1 for kw in self.POSITIVE_KEYWORDS if kw in text)
            negative_count = sum(1 for kw in self.NEGATIVE_KEYWORDS if kw in text)

            article_score = positive_count - negative_count
            total_score += article_score

            headlines.append({
                "headline": article.get("headline"),
                "source": article.get("source"),
                "score": article_score,
            })

        # 평균 점수 (-1 ~ +1 범위로 정규화)
        avg_score = total_score / len(news) if news else 0
        normalized_score = max(-1, min(1, avg_score / 3))

        # 뉴스 양 (이상치 감지)
        volume = len(news)
        volume_signal = "high" if volume > 10 else "normal" if volume > 3 else "low"

        return {
            "score": normalized_score,
            "count": volume,
            "volume_signal": volume_signal,
            "headlines": headlines[:5],  # 상위 5개만
            "signal": "positive" if normalized_score > 0.2 else
                     "negative" if normalized_score < -0.2 else "neutral",
        }

    def _analyze_analyst(self, ratings: Dict) -> Dict:
        """애널리스트 평가 분석"""
        strong_buy = ratings.get("strong_buy", 0)
        buy = ratings.get("buy", 0)
        hold = ratings.get("hold", 0)
        sell = ratings.get("sell", 0)
        strong_sell = ratings.get("strong_sell", 0)

        total = strong_buy + buy + hold + sell + strong_sell

        if total == 0:
            return {"score": 0, "signal": "neutral", "consensus": "no_coverage"}

        # 가중 점수 (Strong Buy=5, Buy=4, Hold=3, Sell=2, Strong Sell=1)
        weighted_score = (
            strong_buy * 5 + buy * 4 + hold * 3 + sell * 2 + strong_sell * 1
        ) / total

        # 분포
        buy_pct = (strong_buy + buy) / total * 100
        hold_pct = hold / total * 100
        sell_pct = (sell + strong_sell) / total * 100

        # 컨센서스
        if weighted_score >= 4.5:
            consensus = "strong_buy"
        elif weighted_score >= 3.5:
            consensus = "buy"
        elif weighted_score >= 2.5:
            consensus = "hold"
        elif weighted_score >= 1.5:
            consensus = "sell"
        else:
            consensus = "strong_sell"

        # -100 ~ +100 점수
        score = (weighted_score - 3) / 2 * 100

        return {
            "score": score,
            "weighted_rating": weighted_score,
            "consensus": consensus,
            "total_analysts": total,
            "buy_pct": buy_pct,
            "hold_pct": hold_pct,
            "sell_pct": sell_pct,
            "signal": "positive" if score > 20 else
                     "negative" if score < -20 else "neutral",
        }

    def _analyze_target(self, target: Dict, current_price: float) -> Dict:
        """목표가 분석"""
        target_mean = target.get("target_mean")
        target_high = target.get("target_high")
        target_low = target.get("target_low")

        if not target_mean or not current_price:
            return {"upside": None, "signal": "neutral"}

        upside = (target_mean / current_price - 1) * 100
        upside_high = (target_high / current_price - 1) * 100 if target_high else None
        upside_low = (target_low / current_price - 1) * 100 if target_low else None

        # 신호
        if upside > 30:
            signal = "strong_positive"
        elif upside > 15:
            signal = "positive"
        elif upside > 0:
            signal = "neutral"
        elif upside > -15:
            signal = "negative"
        else:
            signal = "strong_negative"

        return {
            "target_mean": target_mean,
            "target_high": target_high,
            "target_low": target_low,
            "upside": upside,
            "upside_high": upside_high,
            "upside_low": upside_low,
            "signal": signal,
        }

    def _analyze_insider(self, trades: List[Dict]) -> Dict:
        """내부자 거래 분석"""
        if not trades:
            return {"signal": "neutral", "net_activity": 0}

        buys = 0
        sells = 0
        buy_value = 0
        sell_value = 0

        for trade in trades:
            change = trade.get("change", 0)
            if change > 0:
                buys += 1
                buy_value += abs(change)
            elif change < 0:
                sells += 1
                sell_value += abs(change)

        net_activity = buys - sells
        net_value = buy_value - sell_value

        # 신호
        if net_activity >= 3:
            signal = "strong_positive"
        elif net_activity >= 1:
            signal = "positive"
        elif net_activity <= -3:
            signal = "strong_negative"
        elif net_activity <= -1:
            signal = "negative"
        else:
            signal = "neutral"

        return {
            "buys": buys,
            "sells": sells,
            "buy_value": buy_value,
            "sell_value": sell_value,
            "net_activity": net_activity,
            "net_value": net_value,
            "signal": signal,
        }

    def _calculate_score(self, result: Dict) -> float:
        """종합 점수 계산 (-100 ~ +100)"""
        score = 0

        # 뉴스 센티멘트 (±30)
        news_score = result.get("news", {}).get("score", 0)
        score += news_score * 30

        # 애널리스트 평가 (±30)
        analyst_score = result.get("analyst", {}).get("score", 0)
        score += analyst_score * 0.3

        # 목표가 업사이드 (±25)
        upside = result.get("target", {}).get("upside")
        if upside is not None:
            if upside > 30:
                score += 25
            elif upside > 15:
                score += 15
            elif upside > 0:
                score += 5
            elif upside > -15:
                score -= 10
            else:
                score -= 25

        # 내부자 거래 (±15)
        insider_signal = result.get("insider", {}).get("signal", "neutral")
        if insider_signal == "strong_positive":
            score += 15
        elif insider_signal == "positive":
            score += 10
        elif insider_signal == "negative":
            score -= 10
        elif insider_signal == "strong_negative":
            score -= 15

        return max(-100, min(100, score))

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