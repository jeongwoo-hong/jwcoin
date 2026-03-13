"""
트리거 관리 모듈
"""
import time
from typing import Dict, Optional, List
from collections import deque
from config import settings

class TriggerManager:
    def __init__(self):
        self.price_history = deque(maxlen=settings.PRICE_HISTORY_SIZE)
        self.cooldowns = {}  # {trigger_name: last_triggered_time}
        self.last_scheduled_trade = None
    
    def add_price(self, price: float):
        """가격 기록 추가"""
        self.price_history.append({
            "price": price,
            "time": time.time()
        })
    
    def _is_on_cooldown(self, trigger_name: str, cooldown: int) -> bool:
        """쿨다운 체크"""
        if trigger_name not in self.cooldowns:
            return False
        return (time.time() - self.cooldowns[trigger_name]) < cooldown
    
    def _set_cooldown(self, trigger_name: str):
        """쿨다운 설정"""
        self.cooldowns[trigger_name] = time.time()
    
    def is_scheduled_protection_active(self) -> bool:
        """정기 매매 후 보호 기간인지 확인"""
        if self.last_scheduled_trade is None:
            return False
        return (time.time() - self.last_scheduled_trade) < settings.SCHEDULED_PROTECTION
    
    def set_scheduled_trade_time(self):
        """정기 매매 시간 기록"""
        self.last_scheduled_trade = time.time()
    
    def check_price_change(self) -> Optional[Dict]:
        """가격 급변 트리거 체크"""
        if self._is_on_cooldown("price_change", settings.TRIGGER_COOLDOWN):
            return None
        
        if len(self.price_history) < 2:
            return None
        
        current = self.price_history[-1]
        window_start = current["time"] - settings.PRICE_CHANGE_WINDOW
        
        # 윈도우 내 가장 오래된 가격 찾기
        old_price = None
        for p in self.price_history:
            if p["time"] >= window_start:
                old_price = p["price"]
                break
        
        if old_price is None or old_price == 0:
            return None
        
        change_pct = (current["price"] - old_price) / old_price
        
        if abs(change_pct) >= settings.PRICE_CHANGE_THRESHOLD:
            self._set_cooldown("price_change")
            return {
                "trigger": "price_change",
                "direction": "up" if change_pct > 0 else "down",
                "change_pct": change_pct,
                "current_price": current["price"],
                "message": f"가격 {'급등' if change_pct > 0 else '급락'}: {change_pct*100:.2f}% (5분)"
            }
        
        return None
    
    def check_rsi(self, rsi: float) -> Optional[Dict]:
        """RSI 극단값 트리거 체크"""
        if self._is_on_cooldown("rsi", settings.RSI_COOLDOWN):
            return None
        
        if rsi <= settings.RSI_OVERSOLD:
            self._set_cooldown("rsi")
            return {
                "trigger": "rsi_oversold",
                "value": rsi,
                "message": f"RSI 과매도: {rsi:.1f}"
            }
        elif rsi >= settings.RSI_OVERBOUGHT:
            self._set_cooldown("rsi")
            return {
                "trigger": "rsi_overbought",
                "value": rsi,
                "message": f"RSI 과매수: {rsi:.1f}"
            }
        
        return None
    
    def check_bollinger_bands(self, price: float, bb_upper: float, bb_lower: float) -> Optional[Dict]:
        """볼린저밴드 이탈 트리거 체크"""
        if self._is_on_cooldown("bb", settings.BB_COOLDOWN):
            return None
        
        if price < bb_lower:
            self._set_cooldown("bb")
            return {
                "trigger": "bb_lower",
                "price": price,
                "bb_lower": bb_lower,
                "message": f"볼린저밴드 하단 이탈: {price:,.0f} < {bb_lower:,.0f}"
            }
        elif price > bb_upper:
            self._set_cooldown("bb")
            return {
                "trigger": "bb_upper",
                "price": price,
                "bb_upper": bb_upper,
                "message": f"볼린저밴드 상단 이탈: {price:,.0f} > {bb_upper:,.0f}"
            }
        
        return None
    
    def check_volume_spike(self, volume_ratio: float) -> Optional[Dict]:
        """거래량 급증 트리거 체크"""
        if self._is_on_cooldown("volume", settings.TRIGGER_COOLDOWN):
            return None
        
        if volume_ratio >= settings.VOLUME_SPIKE_RATIO:
            self._set_cooldown("volume")
            return {
                "trigger": "volume_spike",
                "ratio": volume_ratio,
                "message": f"거래량 급증: 평균 대비 {volume_ratio*100:.0f}%"
            }
        
        return None
    
    def check_all(self, indicators: Dict) -> List[Dict]:
        """모든 트리거 체크"""
        if self.is_scheduled_protection_active():
            return []  # 정기 매매 후 보호 기간
        
        triggered = []
        
        # 가격 기록
        self.add_price(indicators["price"])
        
        # 가격 급변
        price_trigger = self.check_price_change()
        if price_trigger:
            triggered.append(price_trigger)
        
        # RSI
        rsi_trigger = self.check_rsi(indicators["rsi"])
        if rsi_trigger:
            triggered.append(rsi_trigger)
        
        # 볼린저밴드
        bb_trigger = self.check_bollinger_bands(
            indicators["price"],
            indicators["bb_upper"],
            indicators["bb_lower"]
        )
        if bb_trigger:
            triggered.append(bb_trigger)
        
        # 거래량
        volume_trigger = self.check_volume_spike(indicators["volume_ratio"])
        if volume_trigger:
            triggered.append(volume_trigger)
        
        return triggered
