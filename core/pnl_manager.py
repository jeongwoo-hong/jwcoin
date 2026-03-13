"""
손절/익절 관리 모듈
"""
import time
from typing import Dict, Optional, Tuple
from config import settings

class PnLManager:
    def __init__(self):
        self.cooldowns = {}
    
    def _is_on_cooldown(self, level: str) -> bool:
        if level not in self.cooldowns:
            return False
        return (time.time() - self.cooldowns[level]) < settings.PNL_COOLDOWN
    
    def _set_cooldown(self, level: str):
        self.cooldowns[level] = time.time()
    
    def calculate_pnl(self, avg_buy_price: float, current_price: float) -> float:
        """손익률 계산"""
        if avg_buy_price <= 0:
            return 0.0
        return (current_price - avg_buy_price) / avg_buy_price
    
    def check_stop_loss(self, pnl_pct: float, btc_balance: float) -> Optional[Dict]:
        """손절 체크"""
        if btc_balance <= 0:
            return None
        
        # 레벨 3: 강제 손절 (쿨다운 없음)
        if pnl_pct <= settings.STOP_LOSS_L3:
            return {
                "action": "FORCE_SELL",
                "level": 3,
                "pnl_pct": pnl_pct,
                "sell_percentage": 100,
                "message": f"🚨 강제 손절 발동: {pnl_pct*100:.1f}%",
                "requires_ai": False
            }
        
        # 레벨 2: AI 긴급 판단
        if pnl_pct <= settings.STOP_LOSS_L2:
            if self._is_on_cooldown("stop_l2"):
                return None
            self._set_cooldown("stop_l2")
            return {
                "action": "AI_URGENT",
                "level": 2,
                "pnl_pct": pnl_pct,
                "message": f"⚠️ 손실 경고: {pnl_pct*100:.1f}%",
                "requires_ai": True,
                "prompt": f"""⚠️ 긴급 손절 판단 요청

현재 손익률: {pnl_pct*100:.1f}%
상황: 손실이 -5%에 도달했습니다.

즉시 손절 여부를 결정해주세요.
홀드를 선택하려면 명확한 반등 근거가 필요합니다.

응답 형식:
- decision: "sell" 또는 "hold"
- percentage: 매도 시 비율 (0-100)
- reason: 판단 근거"""
            }
        
        # 레벨 1: AI 상담
        if pnl_pct <= settings.STOP_LOSS_L1:
            if self._is_on_cooldown("stop_l1"):
                return None
            self._set_cooldown("stop_l1")
            return {
                "action": "AI_CONSULT",
                "level": 1,
                "pnl_pct": pnl_pct,
                "message": f"📉 손실 발생: {pnl_pct*100:.1f}%",
                "requires_ai": True,
                "prompt": f"""손절 판단 요청

현재 손익률: {pnl_pct*100:.1f}%
상황: 손실이 -3%에 도달했습니다.

시장 상황을 분석하고 손절/홀드를 결정해주세요.

응답 형식:
- decision: "sell" 또는 "hold"
- percentage: 매도 시 비율 (0-100)
- reason: 판단 근거"""
            }
        
        return None
    
    def check_take_profit(self, pnl_pct: float, btc_balance: float) -> Optional[Dict]:
        """익절 체크"""
        if btc_balance <= 0:
            return None
        
        # 레벨 3: 강제 부분 익절
        if pnl_pct >= settings.TAKE_PROFIT_L3:
            return {
                "action": "FORCE_PARTIAL_SELL",
                "level": 3,
                "pnl_pct": pnl_pct,
                "sell_percentage": 50,
                "message": f"💰 강제 부분 익절: {pnl_pct*100:.1f}% (50% 매도)",
                "requires_ai": False
            }
        
        # 레벨 2: 부분 익절 권고
        if pnl_pct >= settings.TAKE_PROFIT_L2:
            if self._is_on_cooldown("profit_l2"):
                return None
            self._set_cooldown("profit_l2")
            return {
                "action": "AI_SUGGEST_PARTIAL",
                "level": 2,
                "pnl_pct": pnl_pct,
                "message": f"🎉 수익 +{pnl_pct*100:.1f}%",
                "requires_ai": True,
                "prompt": f"""💰 부분 익절 판단 요청

현재 수익률: +{pnl_pct*100:.1f}%
상황: 수익이 +10%에 도달했습니다.

부분 익절(50%)을 권장합니다.
어떻게 하시겠습니까?

응답 형식:
- decision: "sell", "partial_sell", 또는 "hold"
- percentage: 매도 시 비율 (0-100)
- reason: 판단 근거"""
            }
        
        # 레벨 1: AI 상담
        if pnl_pct >= settings.TAKE_PROFIT_L1:
            if self._is_on_cooldown("profit_l1"):
                return None
            self._set_cooldown("profit_l1")
            return {
                "action": "AI_CONSULT",
                "level": 1,
                "pnl_pct": pnl_pct,
                "message": f"📈 수익 발생: +{pnl_pct*100:.1f}%",
                "requires_ai": True,
                "prompt": f"""익절 판단 요청

현재 수익률: +{pnl_pct*100:.1f}%
상황: 수익이 +5%에 도달했습니다.

익절/홀드를 결정해주세요.

응답 형식:
- decision: "sell", "partial_sell", 또는 "hold"
- percentage: 매도 시 비율 (0-100)
- reason: 판단 근거"""
            }
        
        return None
    
    def check(self, avg_buy_price: float, current_price: float, btc_balance: float) -> Optional[Dict]:
        """손절/익절 체크"""
        pnl_pct = self.calculate_pnl(avg_buy_price, current_price)
        
        # 손절 체크
        stop_loss = self.check_stop_loss(pnl_pct, btc_balance)
        if stop_loss:
            return stop_loss
        
        # 익절 체크
        take_profit = self.check_take_profit(pnl_pct, btc_balance)
        if take_profit:
            return take_profit
        
        return None
