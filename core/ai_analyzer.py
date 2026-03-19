"""
AI 분석 모듈
"""
import os
import json
from typing import Dict, Optional, List
from datetime import datetime
# from openai import OpenAI  # OpenAI 사용 시 주석 해제
import anthropic
from pydantic import BaseModel
from config.database import get_supabase
import logging

logger = logging.getLogger(__name__)

# # OpenAI 모델별 가격 (USD per 1K tokens) - 2024년 기준 대략적 가격
# MODEL_PRICING_OPENAI = {
#     "gpt-4.1": {
#         "input": 0.01,    # $0.01 per 1K input tokens
#         "output": 0.03    # $0.03 per 1K output tokens
#     },
#     "gpt-4.1-mini": {
#         "input": 0.0004,  # $0.0004 per 1K input tokens
#         "output": 0.0016  # $0.0016 per 1K output tokens
#     }
# }

# Claude 모델별 가격 (USD per 1K tokens) - 2025년 기준
MODEL_PRICING = {
    "claude-sonnet-4-5-20250929": {
        "input": 0.003,    # $3 per 1M tokens = $0.003 per 1K tokens
        "output": 0.015    # $15 per 1M tokens = $0.015 per 1K tokens
    },
    "claude-haiku-4-5-20251001": {
        "input": 0.0008,   # $0.80 per 1M tokens = $0.0008 per 1K tokens
        "output": 0.004    # $4 per 1M tokens = $0.004 per 1K tokens
    }
}

# 환율 (대략적)
USD_TO_KRW = 1450

class TradingDecision(BaseModel):
    decision: str
    percentage: int
    reason: str
    model: str = ""  # 사용된 AI 모델명

class AIAnalyzer:
    def __init__(self):
        # self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  # OpenAI 사용 시 주석 해제
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.supabase = get_supabase()

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> Dict:
        """토큰 사용량 기반 비용 계산"""
        pricing = MODEL_PRICING.get(model, MODEL_PRICING["claude-sonnet-4-5-20250929"])

        input_cost_usd = (input_tokens / 1000) * pricing["input"]
        output_cost_usd = (output_tokens / 1000) * pricing["output"]
        total_cost_usd = input_cost_usd + output_cost_usd
        total_cost_krw = total_cost_usd * USD_TO_KRW

        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost_usd": total_cost_usd,
            "cost_krw": total_cost_krw
        }

    def _log_api_cost(self, model: str, analysis_type: str, cost_info: Dict):
        """API 비용을 Supabase에 저장"""
        try:
            data = {
                "category": "api",
                "name": f"Claude {model}",
                "amount": round(cost_info["cost_krw"], 2),
                "description": f"{analysis_type} - {cost_info['total_tokens']} tokens (${cost_info['cost_usd']:.6f})",
                "is_recurring": False
            }

            self.supabase.table("expenses").insert(data).execute()
            logger.debug(f"API cost logged: {cost_info['cost_krw']:.2f} KRW ({cost_info['total_tokens']} tokens)")

        except Exception as e:
            logger.error(f"API cost logging error: {e}")

    # # OpenAI 버전 _call_ai (OpenAI 사용 시 주석 해제)
    # def _call_ai(self, system_prompt: str, user_prompt: str, model: str = "gpt-4.1",
    #              analysis_type: str = "analysis", max_tokens: int = 2000) -> Optional[TradingDecision]:
    #     """AI 호출 (OpenAI)"""
    #     try:
    #         response = self.client.chat.completions.create(
    #             model=model,
    #             messages=[
    #                 {"role": "system", "content": system_prompt},
    #                 {"role": "user", "content": user_prompt}
    #             ],
    #             response_format={
    #                 "type": "json_schema",
    #                 "json_schema": {
    #                     "name": "trading_decision",
    #                     "strict": True,
    #                     "schema": {
    #                         "type": "object",
    #                         "properties": {
    #                             "decision": {"type": "string", "enum": ["buy", "sell", "hold", "partial_sell"]},
    #                             "percentage": {"type": "integer"},
    #                             "reason": {"type": "string"}
    #                         },
    #                         "required": ["decision", "percentage", "reason"],
    #                         "additionalProperties": False
    #                     }
    #                 }
    #             },
    #             max_tokens=max_tokens
    #         )
    #
    #         # 토큰 사용량 추적 및 비용 계산
    #         if response.usage:
    #             cost_info = self._calculate_cost(
    #                 model=model,
    #                 input_tokens=response.usage.prompt_tokens,
    #                 output_tokens=response.usage.completion_tokens
    #             )
    #             self._log_api_cost(model, analysis_type, cost_info)
    #
    #         return TradingDecision.model_validate_json(response.choices[0].message.content)
    #     except Exception as e:
    #         logger.error(f"AI call error: {e}")
    #         return None

    def _call_ai(self, system_prompt: str, user_prompt: str, model: str = "claude-sonnet-4-5-20250929",
                 analysis_type: str = "analysis", max_tokens: int = 2000) -> Optional[TradingDecision]:
        """AI 호출 (Claude)"""
        # trading_decision 도구 정의
        tools = [
            {
                "name": "trading_decision",
                "description": "Submit a trading decision with decision type, percentage, and reason",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "decision": {
                            "type": "string",
                            "enum": ["buy", "sell", "hold", "partial_sell"],
                            "description": "The trading decision"
                        },
                        "percentage": {
                            "type": "integer",
                            "description": "Percentage of funds/holdings to use (0-100)"
                        },
                        "reason": {
                            "type": "string",
                            "description": "Detailed reason for the decision"
                        }
                    },
                    "required": ["decision", "percentage", "reason"]
                }
            }
        ]

        try:
            response = self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system_prompt + "\n\nYou must use the trading_decision tool to submit your decision.",
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                tools=tools,
                tool_choice={"type": "tool", "name": "trading_decision"}
            )

            # 토큰 사용량 추적 및 비용 계산
            if response.usage:
                cost_info = self._calculate_cost(
                    model=model,
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens
                )
                self._log_api_cost(model, analysis_type, cost_info)

            # tool_use 결과에서 trading_decision 추출
            for block in response.content:
                if block.type == "tool_use" and block.name == "trading_decision":
                    decision = TradingDecision(**block.input)
                    decision.model = model  # 사용된 모델 정보 추가
                    return decision

            logger.error("No trading_decision tool use found in response")
            return None
        except Exception as e:
            logger.error(f"AI call error: {e}")
            return None
    
    def emergency_analysis(self, triggers: List[Dict], indicators: Dict, balance_info: Dict) -> Optional[TradingDecision]:
        """긴급 분석 (트리거 발동 시)"""
        trigger_messages = "\n".join([t["message"] for t in triggers])
        
        system_prompt = """당신은 비트코인 긴급 매매 판단 전문가입니다.
트리거가 발동되어 긴급 분석이 필요합니다.
빠르고 명확하게 판단해주세요.

응답 시 percentage는:
- buy: 사용 가능한 KRW의 몇 %를 매수할지 (1-100)
- sell/partial_sell: 보유 BTC의 몇 %를 매도할지 (1-100)
- hold: 0"""

        user_prompt = f"""🚨 긴급 분석 요청

발동된 트리거:
{trigger_messages}

현재 지표:
- 가격: {indicators['price']:,.0f} KRW
- RSI(14): {indicators['rsi']:.1f}
- 볼린저밴드: {indicators['bb_lower']:,.0f} ~ {indicators['bb_upper']:,.0f}
- 거래량: 평균 대비 {indicators['volume_ratio']*100:.0f}%

보유 현황:
- BTC: {balance_info.get('btc_balance', 0):.6f}
- KRW: {balance_info.get('krw_balance', 0):,.0f}

빠르게 판단해주세요."""

        # return self._call_ai(system_prompt, user_prompt, model="gpt-4.1-mini", analysis_type="긴급분석")  # OpenAI
        return self._call_ai(system_prompt, user_prompt, model="claude-haiku-4-5-20251001", analysis_type="긴급분석")
    
    def pnl_analysis(self, pnl_info: Dict, indicators: Dict) -> Optional[TradingDecision]:
        """손절/익절 분석"""
        system_prompt = """당신은 비트코인 손절/익절 판단 전문가입니다.
현재 손익 상황을 분석하고 최적의 판단을 내려주세요.

응답 시 percentage는:
- sell: 전량 매도 시 100
- partial_sell: 부분 매도 비율 (예: 50)
- hold: 0"""

        user_prompt = pnl_info.get("prompt", "") + f"""

현재 지표:
- RSI(14): {indicators['rsi']:.1f}
- 볼린저밴드: {indicators['bb_lower']:,.0f} ~ {indicators['bb_upper']:,.0f}
- 거래량: 평균 대비 {indicators['volume_ratio']*100:.0f}%"""

        # return self._call_ai(system_prompt, user_prompt, model="gpt-4.1-mini", analysis_type="손익분석")  # OpenAI
        return self._call_ai(system_prompt, user_prompt, model="claude-haiku-4-5-20251001", analysis_type="손익분석")

    # # OpenAI 버전 generate_reflection (OpenAI 사용 시 주석 해제)
    # def generate_reflection(self, recent_trades: str, market_data: Dict) -> str:
    #     """AI 반성 생성 (OpenAI)"""
    #     try:
    #         response = self.client.chat.completions.create(
    #             model="gpt-4.1-mini",
    #             messages=[
    #                 {
    #                     "role": "system",
    #                     "content": "You are an AI trading assistant tasked with analyzing recent trading performance and current market conditions to generate insights and improvements for future trading decisions."
    #                 },
    #                 {
    #                     "role": "user",
    #                     "content": f"""
    # Recent trading data:
    # {recent_trades}
    #
    # Current market data:
    # {json.dumps(market_data, indent=2, default=str)}
    #
    # Please analyze this data and provide:
    # 1. A brief reflection on the recent trading decisions
    # 2. Insights on what worked well and what didn't
    # 3. Suggestions for improvement in future trading decisions
    # 4. Any patterns or trends you notice in the market data
    #
    # Limit your response to 250 words or less.
    # """
    #                 }
    #             ],
    #             max_tokens=500
    #         )
    #
    #         # 비용 로깅
    #         if response.usage:
    #             cost_info = self._calculate_cost(
    #                 model="gpt-4.1-mini",
    #                 input_tokens=response.usage.prompt_tokens,
    #                 output_tokens=response.usage.completion_tokens
    #             )
    #             self._log_api_cost("gpt-4.1-mini", "reflection", cost_info)
    #
    #         return response.choices[0].message.content
    #     except Exception as e:
    #         logger.error(f"Reflection generation error: {e}")
    #         return ""

    def generate_reflection(self, recent_trades: str, market_data: Dict) -> str:
        """AI 반성 생성 (Claude)"""
        try:
            model = "claude-haiku-4-5-20251001"
            response = self.client.messages.create(
                model=model,
                max_tokens=500,
                system="You are an AI trading assistant tasked with analyzing recent trading performance and current market conditions to generate insights and improvements for future trading decisions.",
                messages=[
                    {
                        "role": "user",
                        "content": f"""
Recent trading data:
{recent_trades}

Current market data:
{json.dumps(market_data, indent=2, default=str)}

Please analyze this data and provide:
1. A brief reflection on the recent trading decisions
2. Insights on what worked well and what didn't
3. Suggestions for improvement in future trading decisions
4. Any patterns or trends you notice in the market data

Limit your response to 250 words or less.
"""
                    }
                ]
            )

            # 비용 로깅
            if response.usage:
                cost_info = self._calculate_cost(
                    model=model,
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens
                )
                self._log_api_cost(model, "reflection", cost_info)

            return response.content[0].text
        except Exception as e:
            logger.error(f"Reflection generation error: {e}")
            return ""

    def scheduled_analysis(self, market_data: Dict, balance_info: Dict,
                          recent_trades: str = "", reflection: str = "") -> Optional[TradingDecision]:
        """정기 분석 (4시간마다)"""
        system_prompt = """You are an expert in Bitcoin investing. Analyze the provided data and determine whether to buy, sell, or hold at the current moment. Consider the following in your analysis:

- Technical indicators and market data (RSI, Bollinger Bands, MACD, volume)
- Recent trading performance and reflection
- Overall market sentiment and trends

Particularly important is to always refer to the trading method of 'Wonyyotti', a legendary Korean investor:
1. Chart-focused trading - prioritize chart analysis over news
2. Identify key support/resistance levels for entry/exit
3. Target consistent 1-2% daily gains (compound effect)
4. Only invest 20-30% of total capital per trade
5. Use dollar-cost averaging (split buy/sell)
6. Strict risk management - cut losses when plan fails

Response format:
1. Decision (buy, sell, or hold)
2. If 'buy': percentage (1-100) of available KRW to use
   If 'sell': percentage (1-100) of held BTC to sell
   If 'hold': set percentage to 0
3. Detailed reason for your decision including:
   - Technical indicator analysis (RSI levels, Bollinger Band position, volume trends)
   - Support/resistance levels identified
   - Risk assessment
   - How this aligns with Wonyyotti strategy

Provide your reason in English with thorough technical analysis."""

        user_prompt = f"""Scheduled Analysis Request

Market Data:
- Current Price: {market_data.get('price', 0):,.0f} KRW
- RSI(14): {market_data.get('rsi', 0):.2f}
- Bollinger Bands: Lower {market_data.get('bb_lower', 0):,.0f} | Upper {market_data.get('bb_upper', 0):,.0f}
- Volume Ratio: {market_data.get('volume_ratio', 1)*100:.1f}% of average

Current Holdings:
- BTC Balance: {balance_info.get('btc_balance', 0):.6f}
- KRW Balance: {balance_info.get('krw_balance', 0):,.0f}
- Average Buy Price: {balance_info.get('avg_buy_price', 0):,.0f} KRW

Recent Trades:
{recent_trades}

Previous Analysis Reflection:
{reflection}

Please provide a comprehensive analysis and trading decision."""

        # return self._call_ai(system_prompt, user_prompt, model="gpt-4.1", analysis_type="정기분석", max_tokens=2000)  # OpenAI
        return self._call_ai(system_prompt, user_prompt, model="claude-sonnet-4-5-20250929", analysis_type="정기분석", max_tokens=2000)
