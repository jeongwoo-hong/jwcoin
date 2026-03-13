"""
AI 분석 모듈
"""
import os
import json
from typing import Dict, Optional, List
from openai import OpenAI
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

class TradingDecision(BaseModel):
    decision: str
    percentage: int
    reason: str

class AIAnalyzer:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def _call_ai(self, system_prompt: str, user_prompt: str, model: str = "gpt-4.1") -> Optional[TradingDecision]:
        """AI 호출"""
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "trading_decision",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "decision": {"type": "string", "enum": ["buy", "sell", "hold", "partial_sell"]},
                                "percentage": {"type": "integer"},
                                "reason": {"type": "string"}
                            },
                            "required": ["decision", "percentage", "reason"],
                            "additionalProperties": False
                        }
                    }
                },
                max_tokens=500
            )
            
            return TradingDecision.model_validate_json(response.choices[0].message.content)
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

        return self._call_ai(system_prompt, user_prompt, model="gpt-4.1-mini")
    
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

        return self._call_ai(system_prompt, user_prompt, model="gpt-4.1-mini")
    
    def scheduled_analysis(self, market_data: Dict, balance_info: Dict, 
                          recent_trades: str = "", reflection: str = "") -> Optional[TradingDecision]:
        """정기 분석 (4시간마다)"""
        system_prompt = """당신은 비트코인 투자 전문가입니다.
원띠(Wonyyotti) 투자 전략을 따릅니다:

1. 차트 위주 매매 - 호재/악재보다 차트 분석 중심
2. 주요 지지선/저항선 기준 매수/매도 시점 결정
3. 하루 1-2% 꾸준한 수익 목표
4. 전체 시드의 20-30%만 투자
5. 분할 매수/매도 전략
6. 철저한 리스크 관리

응답 시 percentage는:
- buy: 사용 가능한 KRW의 몇 %를 매수할지 (1-100)
- sell: 보유 BTC의 몇 %를 매도할지 (1-100)
- hold: 0"""

        user_prompt = f"""정기 분석 요청 (4시간 주기)

시장 데이터:
{json.dumps(market_data, indent=2, default=str)}

보유 현황:
- BTC: {balance_info.get('btc_balance', 0):.6f}
- KRW: {balance_info.get('krw_balance', 0):,.0f}
- 평균 매수가: {balance_info.get('avg_buy_price', 0):,.0f}

최근 거래:
{recent_trades}

이전 분석 반성:
{reflection}

종합적으로 분석하고 판단해주세요."""

        return self._call_ai(system_prompt, user_prompt, model="gpt-4.1")
