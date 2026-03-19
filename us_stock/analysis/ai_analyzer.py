"""
AI 기반 투자 결정 엔진
Claude API를 활용한 최종 투자 판단
"""
import logging
import json
from typing import Dict, List, Optional
from datetime import datetime

from anthropic import Anthropic

logger = logging.getLogger(__name__)


class AIAnalyzer:
    """Claude AI 기반 투자 분석기"""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.client = Anthropic(api_key=api_key)
        self.model = model

    def analyze(
        self,
        symbol: str,
        comprehensive_result: Dict,
        portfolio: Dict,
        market_condition: Dict,
    ) -> Dict:
        """
        AI 기반 최종 투자 결정

        Args:
            symbol: 종목 심볼
            comprehensive_result: ComprehensiveScorer의 분석 결과
            portfolio: 현재 포트폴리오 상태
            market_condition: 시장 상황

        Returns:
            AI 투자 결정 딕셔너리
        """
        try:
            # 프롬프트 생성
            prompt = self._build_prompt(
                symbol, comprehensive_result, portfolio, market_condition
            )

            # Claude API 호출 (tool_use로 구조화된 응답)
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                tools=[self._get_decision_tool()],
                tool_choice={"type": "tool", "name": "make_trading_decision"},
                messages=[{"role": "user", "content": prompt}],
            )

            # 응답 파싱
            decision = self._parse_response(response)
            decision["symbol"] = symbol
            decision["model"] = self.model
            decision["timestamp"] = datetime.now().isoformat()

            return decision

        except Exception as e:
            logger.error(f"AI analysis error for {symbol}: {e}")
            return {
                "symbol": symbol,
                "decision": "hold",
                "confidence": 0.0,
                "reason": f"AI analysis failed: {str(e)}",
                "error": str(e),
            }

    def _get_decision_tool(self) -> Dict:
        """투자 결정 도구 정의"""
        return {
            "name": "make_trading_decision",
            "description": "Make a trading decision based on comprehensive analysis",
            "input_schema": {
                "type": "object",
                "properties": {
                    "decision": {
                        "type": "string",
                        "enum": ["strong_buy", "buy", "hold", "sell", "strong_sell"],
                        "description": "Trading decision",
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Confidence level (0.0 to 1.0)",
                    },
                    "position_size_pct": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 10,
                        "description": "Recommended position size as percentage of portfolio (0-10%)",
                    },
                    "entry_price": {
                        "type": "number",
                        "description": "Recommended entry price (0 if no trade)",
                    },
                    "stop_loss_pct": {
                        "type": "number",
                        "minimum": 1,
                        "maximum": 15,
                        "description": "Stop loss percentage from entry (1-15%)",
                    },
                    "take_profit_pct": {
                        "type": "number",
                        "minimum": 5,
                        "maximum": 50,
                        "description": "Take profit percentage from entry (5-50%)",
                    },
                    "time_horizon": {
                        "type": "string",
                        "enum": ["short_term", "medium_term", "long_term"],
                        "description": "Expected holding period",
                    },
                    "key_reasons": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Top 3-5 reasons for the decision",
                    },
                    "risks": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Top 3 risks to monitor",
                    },
                    "catalyst": {
                        "type": "string",
                        "description": "Expected catalyst or trigger for price movement",
                    },
                    "alternative_scenario": {
                        "type": "string",
                        "description": "What would change this decision",
                    },
                },
                "required": [
                    "decision",
                    "confidence",
                    "position_size_pct",
                    "stop_loss_pct",
                    "take_profit_pct",
                    "time_horizon",
                    "key_reasons",
                    "risks",
                ],
            },
        }

    def _build_prompt(
        self,
        symbol: str,
        analysis: Dict,
        portfolio: Dict,
        market: Dict,
    ) -> str:
        """분석 프롬프트 생성"""

        # 기술적 분석 요약
        tech = analysis.get("technical", {})
        tech_summary = f"""
기술적 분석 (점수: {tech.get('score', 'N/A')}):
- 추세: {tech.get('trend', 'N/A')}
- RSI: {tech.get('rsi', 'N/A')} ({tech.get('rsi_signal', 'N/A')})
- MACD 신호: {tech.get('macd_signal', 'N/A')}
- 볼린저밴드: {tech.get('bb_signal', 'N/A')}
- 52주 고점 대비: {tech.get('pct_from_high', 'N/A'):.1f}%
- 지지/저항: 지지 {tech.get('support', 'N/A')}, 저항 {tech.get('resistance', 'N/A')}
"""

        # 기본적 분석 요약
        fund = analysis.get("fundamental", {})
        valuation = fund.get("valuation", {})
        profitability = fund.get("profitability", {})
        growth = fund.get("growth", {})
        health = fund.get("financial_health", {})

        fund_summary = f"""
기본적 분석 (점수: {fund.get('score', 'N/A')}):
- P/E: {valuation.get('pe_ratio', 'N/A')} (섹터 대비: {valuation.get('pe_signal', 'N/A')})
- PEG: {valuation.get('peg_ratio', 'N/A')} ({valuation.get('peg_signal', 'N/A')})
- ROE: {profitability.get('roe', 'N/A')}
- 영업이익률: {profitability.get('operating_margin', 'N/A')}
- 매출 성장률: {growth.get('revenue_growth', 'N/A')}
- 성장 단계: {growth.get('stage', 'N/A')}
- 재무 건전성: {health.get('grade', 'N/A')}
- 부채비율: {health.get('debt_to_equity', 'N/A')}
"""

        # 센티멘트 분석 요약
        sent = analysis.get("sentiment", {})
        analyst = sent.get("analyst", {})
        target = sent.get("target", {})
        insider = sent.get("insider", {})

        sent_summary = f"""
센티멘트 분석 (점수: {sent.get('score', 'N/A')}):
- 애널리스트 컨센서스: {analyst.get('consensus', 'N/A')} ({analyst.get('total_analysts', 0)}명)
- 목표가 업사이드: {target.get('upside', 'N/A'):.1f}% (평균 목표가: ${target.get('target_mean', 'N/A')})
- 내부자 거래: {insider.get('signal', 'N/A')} (순매수: {insider.get('net_activity', 0)})
- 뉴스 센티멘트: {sent.get('news', {}).get('signal', 'N/A')}
"""

        # 거시경제 분석 요약
        macro = analysis.get("macro", {})
        macro_market = macro.get("market", {})
        macro_rates = macro.get("rates", {})

        macro_summary = f"""
거시경제 분석 (점수: {macro.get('score', 'N/A')}):
- 시장 레짐: {macro.get('regime', 'N/A')}
- 리스크 수준: {macro.get('risk_level', 'N/A')}
- VIX: {macro_market.get('vix', 'N/A')} ({macro_market.get('vix_signal', 'N/A')})
- S&P 500 변화: {macro_market.get('sp500_change', 'N/A')}%
- 10년 국채: {macro_rates.get('treasury_10y', 'N/A')}%
- 수익률 곡선: {macro_rates.get('curve_signal', 'N/A')}
- 권장 노출도: {macro.get('recommended_exposure', 'N/A'):.0%}
"""

        # 종합 점수
        composite = analysis.get("composite_score", 0)
        adjusted = analysis.get("adjusted_score", 0)
        signal = analysis.get("signal", "hold")
        confidence = analysis.get("confidence", 0.5)
        decision = analysis.get("decision", {})

        score_summary = f"""
종합 평가:
- 종합 점수: {composite:.1f} (조정 후: {adjusted:.1f})
- 신호: {signal}
- 시스템 확신도: {confidence:.0%}
- 시스템 결정: {decision.get('decision', 'N/A')} ({decision.get('percentage', 0)}%)

주요 긍정 요인:
{chr(10).join('- ' + f for f in decision.get('key_factors', [])[:5])}

주요 리스크:
{chr(10).join('- ' + r for r in decision.get('risks', [])[:5])}
"""

        # 포트폴리오 상태
        portfolio_summary = f"""
포트폴리오 상태:
- 총 자산: ${portfolio.get('total_value', 0):,.0f}
- 현금 비중: {portfolio.get('cash_ratio', 0):.0%}
- 현재 {symbol} 보유: {portfolio.get('positions', {}).get(symbol, {}).get('quantity', 0)}주
- 전체 종목 수: {len(portfolio.get('positions', {}))}
"""

        # 최종 프롬프트
        prompt = f"""당신은 미국 주식 투자 전문 AI입니다. 아래 분석 데이터를 바탕으로 {symbol}에 대한 투자 결정을 내려주세요.

### 중요 원칙 ###
1. 손실 방지가 최우선입니다. 불확실하면 HOLD를 선택하세요.
2. 한 종목에 포트폴리오의 5% 이상 투자하지 마세요.
3. 거시경제 리스크가 높으면 보수적으로 판단하세요.
4. 기술적, 기본적, 센티멘트가 모두 일치할 때만 적극적인 결정을 내리세요.
5. 확신도가 60% 미만이면 거래하지 마세요.

### 분석 데이터 ###

{tech_summary}

{fund_summary}

{sent_summary}

{macro_summary}

{score_summary}

{portfolio_summary}

### 시장 상황 ###
- 현재 시간: {datetime.now().strftime('%Y-%m-%d %H:%M')} (한국 시간)
- 미국 시장 상태: {market.get('is_open', False) and '개장중' or '폐장'}

위 데이터를 종합적으로 분석하여 투자 결정을 내려주세요.
결정을 내릴 때는 반드시 근거를 명확히 하고, 리스크를 식별하세요.
"""
        return prompt

    def _parse_response(self, response) -> Dict:
        """Claude 응답 파싱"""
        for block in response.content:
            if block.type == "tool_use" and block.name == "make_trading_decision":
                return block.input

        # tool_use가 없으면 기본값 반환
        return {
            "decision": "hold",
            "confidence": 0.0,
            "position_size_pct": 0,
            "stop_loss_pct": 7,
            "take_profit_pct": 15,
            "time_horizon": "medium_term",
            "key_reasons": ["Unable to parse AI response"],
            "risks": ["AI response parsing failed"],
        }

    def batch_analyze(
        self,
        analyses: List[Dict],
        portfolio: Dict,
        market_condition: Dict,
        max_recommendations: int = 5,
    ) -> Dict:
        """
        여러 종목 분석 후 최적 포트폴리오 추천

        Args:
            analyses: 각 종목의 ComprehensiveScorer 분석 결과 리스트
            portfolio: 현재 포트폴리오
            market_condition: 시장 상황
            max_recommendations: 최대 추천 종목 수

        Returns:
            포트폴리오 추천 딕셔너리
        """
        try:
            # 각 종목별 AI 분석
            decisions = []
            for analysis in analyses:
                symbol = analysis.get("symbol")
                if symbol:
                    decision = self.analyze(
                        symbol, analysis, portfolio, market_condition
                    )
                    decisions.append(decision)

            # 점수순 정렬
            buy_candidates = [
                d for d in decisions
                if d.get("decision") in ["strong_buy", "buy"]
                and d.get("confidence", 0) >= 0.6
            ]
            buy_candidates.sort(
                key=lambda x: (x.get("confidence", 0), x.get("position_size_pct", 0)),
                reverse=True,
            )

            sell_candidates = [
                d for d in decisions
                if d.get("decision") in ["strong_sell", "sell"]
                and d.get("confidence", 0) >= 0.6
            ]

            return {
                "timestamp": datetime.now().isoformat(),
                "total_analyzed": len(decisions),
                "buy_recommendations": buy_candidates[:max_recommendations],
                "sell_recommendations": sell_candidates,
                "hold": [
                    d for d in decisions
                    if d.get("decision") == "hold" or d.get("confidence", 0) < 0.6
                ],
                "market_condition": market_condition,
            }

        except Exception as e:
            logger.error(f"Batch analysis error: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }


class QuickAnalyzer:
    """빠른 스크리닝용 분석기 (Haiku 사용)"""

    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-haiku-4-5-20251001"

    def quick_screen(self, symbol: str, basic_data: Dict) -> Dict:
        """빠른 스크리닝 (관심 여부만 판단)"""
        try:
            prompt = f"""
{symbol} 주식에 대해 빠르게 평가해주세요:

현재가: ${basic_data.get('price', 0):.2f}
P/E: {basic_data.get('pe_ratio', 'N/A')}
52주 변화: {basic_data.get('52w_change', 'N/A')}%
RSI: {basic_data.get('rsi', 'N/A')}

이 종목이 더 자세한 분석이 필요한지 YES/NO로 답하고 간단한 이유를 설명하세요.
"""
            response = self.client.messages.create(
                model=self.model,
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )

            text = response.content[0].text
            worth_analyzing = "YES" in text.upper()

            return {
                "symbol": symbol,
                "worth_analyzing": worth_analyzing,
                "reason": text,
            }

        except Exception as e:
            logger.error(f"Quick screen error for {symbol}: {e}")
            return {
                "symbol": symbol,
                "worth_analyzing": True,  # 에러시 분석 진행
                "error": str(e),
            }