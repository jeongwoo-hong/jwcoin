"""
매매 실행 모듈
"""
import os
import time
import threading
import logging
import pyupbit
from typing import Dict, Optional
from datetime import datetime
from supabase import create_client, Client
from config import settings

logger = logging.getLogger(__name__)

class TradeExecutor:
    def __init__(self):
        self.upbit = pyupbit.Upbit(
            os.getenv("UPBIT_ACCESS_KEY"),
            os.getenv("UPBIT_SECRET_KEY")
        )
        self.supabase: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )
        
        self.lock = threading.Lock()
        self.last_trade_time = None
        self.daily_trades = 0
        self.daily_emergency_trades = 0
        self.last_reset_date = datetime.now().date()
    
    def _reset_daily_counters(self):
        """일일 카운터 리셋"""
        today = datetime.now().date()
        if today != self.last_reset_date:
            self.daily_trades = 0
            self.daily_emergency_trades = 0
            self.last_reset_date = today
    
    def can_trade(self, is_emergency: bool = False) -> bool:
        """거래 가능 여부 체크"""
        self._reset_daily_counters()
        
        # 일일 제한 체크
        if self.daily_trades >= settings.MAX_DAILY_TRADES:
            logger.warning("Daily trade limit reached")
            return False
        
        if is_emergency and self.daily_emergency_trades >= settings.MAX_DAILY_EMERGENCY:
            logger.warning("Daily emergency trade limit reached")
            return False
        
        # 최소 거래 간격 체크
        if self.last_trade_time:
            elapsed = time.time() - self.last_trade_time
            if elapsed < settings.MIN_TRADE_INTERVAL:
                logger.info(f"Trade cooldown: {settings.MIN_TRADE_INTERVAL - elapsed:.0f}s remaining")
                return False
        
        return True
    
    def get_balance(self) -> Dict:
        """잔고 조회"""
        try:
            balances = self.upbit.get_balances()
            btc_balance = 0
            krw_balance = 0
            avg_buy_price = 0
            
            for b in balances:
                if b['currency'] == 'BTC':
                    btc_balance = float(b['balance'])
                    avg_buy_price = float(b['avg_buy_price'])
                elif b['currency'] == 'KRW':
                    krw_balance = float(b['balance'])
            
            current_price = pyupbit.get_current_price("KRW-BTC")
            
            return {
                "btc_balance": btc_balance,
                "krw_balance": krw_balance,
                "avg_buy_price": avg_buy_price,
                "current_price": current_price
            }
        except Exception as e:
            logger.error(f"Balance fetch error: {e}")
            return {}
    
    def execute(self, decision: str, percentage: int, reason: str,
                source: str = "scheduled", trigger_reason: str = "",
                pnl_percentage: float = None, reflection: str = "") -> bool:
        """매매 실행"""
        with self.lock:
            is_emergency = source in ["triggered", "stop_loss", "take_profit"]
            
            if not self.can_trade(is_emergency):
                return False
            
            try:
                balance = self.get_balance()
                if not balance:
                    return False
                
                order = None
                
                if decision == "buy":
                    krw = balance["krw_balance"]
                    buy_amount = krw * (percentage / 100) * 0.9995
                    
                    if buy_amount < 5000:
                        logger.warning("Buy amount too small")
                        return False
                    
                    order = self.upbit.buy_market_order("KRW-BTC", buy_amount)
                    logger.info(f"BUY executed: {buy_amount:,.0f} KRW ({percentage}%)")
                
                elif decision in ["sell", "partial_sell"]:
                    btc = balance["btc_balance"]
                    sell_amount = btc * (percentage / 100)
                    current_price = balance["current_price"]

                    if sell_amount * current_price < 5000:
                        logger.warning("Sell amount too small")
                        return False

                    order = self.upbit.sell_market_order("KRW-BTC", sell_amount)
                    logger.info(f"SELL executed: {sell_amount:.6f} BTC ({percentage}%)")
                
                elif decision == "hold":
                    logger.info("HOLD - No action")
                    order = True  # 로깅은 하지만 실제 주문 없음
                
                if order:
                    self.last_trade_time = time.time()
                    self.daily_trades += 1
                    if is_emergency:
                        self.daily_emergency_trades += 1

                    # 로깅
                    self._log_trade(decision, percentage, reason, source,
                                   trigger_reason, pnl_percentage, balance, reflection)
                    return True
                
                return False
                
            except Exception as e:
                logger.error(f"Trade execution error: {e}")
                return False
    
    def execute_force_sell(self, percentage: int, reason: str, pnl_percentage: float) -> bool:
        """강제 매도 (손절/익절)"""
        # 강제 매도는 쿨다운 무시
        with self.lock:
            try:
                balance = self.get_balance()
                if not balance:
                    return False
                
                btc = balance["btc_balance"]
                sell_amount = btc * (percentage / 100)
                current_price = balance["current_price"]
                
                if sell_amount * current_price < 5000:
                    return False
                
                order = self.upbit.sell_market_order("KRW-BTC", sell_amount)
                
                if order:
                    self.last_trade_time = time.time()
                    self.daily_trades += 1
                    
                    source = "stop_loss" if pnl_percentage < 0 else "take_profit"
                    self._log_trade("sell", percentage, reason, source, 
                                   reason, pnl_percentage, balance)
                    
                    logger.info(f"FORCE SELL executed: {sell_amount:.6f} BTC ({percentage}%)")
                    return True
                
                return False
                
            except Exception as e:
                logger.error(f"Force sell error: {e}")
                return False
    
    def _log_trade(self, decision: str, percentage: int, reason: str,
                   source: str, trigger_reason: str, pnl_percentage: float,
                   balance: Dict, reflection: str = ""):
        """거래 로깅"""
        try:
            # 최신 잔고 조회
            time.sleep(1)
            updated_balance = self.get_balance()

            data = {
                "decision": decision,
                "percentage": percentage,
                "reason": reason,
                "btc_balance": updated_balance.get("btc_balance", balance["btc_balance"]),
                "krw_balance": updated_balance.get("krw_balance", balance["krw_balance"]),
                "btc_avg_buy_price": updated_balance.get("avg_buy_price", balance["avg_buy_price"]),
                "btc_krw_price": updated_balance.get("current_price", balance["current_price"]),
                "source": source,
                "trigger_reason": trigger_reason,
                "pnl_percentage": pnl_percentage,
                "reflection": reflection
            }

            self.supabase.table("trades").insert(data).execute()
            logger.info(f"Trade logged: {decision} ({source})")
            
        except Exception as e:
            logger.error(f"Trade logging error: {e}")
