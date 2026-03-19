"""
하이브리드 트레이딩 시스템
- 정기 매매: 4시간마다 (0, 4, 8, 12, 16, 20시)
- 긴급 매매: 트리거 발동 시
- 손절/익절: AI 판단 + 강제 안전장치
"""
import os
import time
import threading
import logging
import schedule
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 모듈 임포트
from config import settings
from config.database import get_supabase
from core.indicators import calculate_indicators
from core.triggers import TriggerManager
from core.pnl_manager import PnLManager
from core.ai_analyzer import AIAnalyzer
from core.executor import TradeExecutor

# Supabase 클라이언트 (싱글톤)
supabase = get_supabase()

def get_recent_trades_with_reasons(days=7, limit=50):
    """최근 거래 기록 및 판단 이유 조회 (토큰 최적화)"""
    try:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        response = supabase.table("trades") \
            .select("timestamp, decision, percentage, reason, btc_balance, btc_krw_price") \
            .gte("timestamp", cutoff) \
            .order("timestamp", desc=True) \
            .limit(limit) \
            .execute()

        if response.data:
            trades_text = []
            for t in response.data:
                # reason을 80자로 제한 (토큰 절약)
                reason = t.get('reason', '') or ''
                reason_short = reason[:80] + '...' if len(reason) > 80 else reason

                trades_text.append(
                    f"[{t['timestamp'][5:16]}] {t['decision'].upper()} {t['percentage']}% "
                    f"| BTC:{t['btc_balance']:.4f} @{t['btc_krw_price']/1000000:.1f}M "
                    f"| {reason_short}"
                )
            return "\n".join(trades_text)
        return "최근 거래 없음"
    except Exception as e:
        logger.error(f"Recent trades fetch error: {e}")
        return "조회 실패"

# 전역 객체
trigger_manager = TriggerManager()
pnl_manager = PnLManager()
ai_analyzer = AIAnalyzer()
executor = TradeExecutor()

# =============================================================================
# 정기 매매 (4시간마다)
# =============================================================================

def scheduled_trade():
    """정기 매매 실행"""
    logger.info("=== 정기 매매 시작 ===")
    
    try:
        # 잔고 조회
        balance = executor.get_balance()
        if not balance:
            logger.error("Failed to get balance")
            return
        
        # 지표 계산
        indicators = calculate_indicators()
        if not indicators:
            logger.error("Failed to calculate indicators")
            return
        
        # 시장 데이터 구성
        market_data = {
            "price": indicators["price"],
            "rsi": indicators["rsi"],
            "bb_upper": indicators["bb_upper"],
            "bb_lower": indicators["bb_lower"],
            "volume_ratio": indicators["volume_ratio"]
        }

        # 이전 거래 기록 조회 (7일, 최대 50건, reason 포함)
        recent_trades = get_recent_trades_with_reasons(days=7, limit=50)
        logger.info(f"Recent trades loaded: {len(recent_trades.split(chr(10)))} records")

        # AI 반성 생성
        reflection = ai_analyzer.generate_reflection(recent_trades, market_data)
        logger.info("Reflection generated")

        # AI 분석 (이전 기록 + 반성 포함)
        decision = ai_analyzer.scheduled_analysis(
            market_data,
            balance,
            recent_trades=recent_trades,
            reflection=reflection
        )

        if decision:
            logger.info(f"AI Decision: {decision.decision} ({decision.percentage}%)")
            logger.info(f"Reason: {decision.reason[:200]}...")

            # 매매 실행
            executor.execute(
                decision=decision.decision,
                percentage=decision.percentage,
                reason=decision.reason,
                source="scheduled",
                reflection=reflection,
                model=decision.model
            )

            # 정기 매매 시간 기록 (긴급 트리거 보호용)
            trigger_manager.set_scheduled_trade_time()
        
        logger.info("=== 정기 매매 완료 ===\n")
        
    except Exception as e:
        logger.error(f"Scheduled trade error: {e}")

# =============================================================================
# 실시간 모니터링
# =============================================================================

def monitor_loop():
    """실시간 모니터링 루프"""
    logger.info("모니터링 시작...")
    
    while True:
        try:
            # 지표 계산
            indicators = calculate_indicators()
            if not indicators:
                time.sleep(settings.MONITOR_INTERVAL)
                continue
            
            # 잔고 조회
            balance = executor.get_balance()
            if not balance:
                time.sleep(settings.MONITOR_INTERVAL)
                continue
            
            # 1. 손절/익절 체크 (최우선)
            if balance["btc_balance"] > 0 and balance["avg_buy_price"] > 0:
                pnl_result = pnl_manager.check(
                    balance["avg_buy_price"],
                    indicators["price"],
                    balance["btc_balance"]
                )
                
                if pnl_result:
                    handle_pnl_trigger(pnl_result, indicators, balance)
            
            # 2. 일반 트리거 체크
            triggers = trigger_manager.check_all(indicators)
            
            if triggers:
                handle_triggers(triggers, indicators, balance)
            
            time.sleep(settings.MONITOR_INTERVAL)
            
        except Exception as e:
            logger.error(f"Monitor error: {e}")
            time.sleep(settings.MONITOR_INTERVAL)

def handle_pnl_trigger(pnl_result: dict, indicators: dict, balance: dict):
    """손절/익절 트리거 처리"""
    logger.info(f"PnL Trigger: {pnl_result['message']}")
    
    if not pnl_result["requires_ai"]:
        # 강제 손절/익절
        executor.execute_force_sell(
            percentage=pnl_result["sell_percentage"],
            reason=pnl_result["message"],
            pnl_percentage=pnl_result["pnl_pct"]
        )
    else:
        # AI 판단 요청
        decision = ai_analyzer.pnl_analysis(pnl_result, indicators)
        
        if decision:
            logger.info(f"AI PnL Decision: {decision.decision} ({decision.percentage}%)")
            
            if decision.decision in ["sell", "partial_sell"]:
                executor.execute(
                    decision=decision.decision,
                    percentage=decision.percentage,
                    reason=decision.reason,
                    source="stop_loss" if pnl_result["pnl_pct"] < 0 else "take_profit",
                    trigger_reason=pnl_result["message"],
                    pnl_percentage=pnl_result["pnl_pct"],
                    model=decision.model
                )

def handle_triggers(triggers: list, indicators: dict, balance: dict):
    """일반 트리거 처리"""
    for trigger in triggers:
        logger.info(f"Trigger: {trigger['message']}")
    
    # AI 긴급 분석
    decision = ai_analyzer.emergency_analysis(triggers, indicators, balance)
    
    if decision:
        logger.info(f"AI Emergency Decision: {decision.decision} ({decision.percentage}%)")
        
        if decision.decision != "hold":
            trigger_messages = ", ".join([t["message"] for t in triggers])

            executor.execute(
                decision=decision.decision,
                percentage=decision.percentage,
                reason=decision.reason,
                source="triggered",
                trigger_reason=trigger_messages,
                model=decision.model
            )

# =============================================================================
# 메인
# =============================================================================

def main():
    logger.info("=" * 50)
    logger.info("하이브리드 트레이딩 시스템 시작")
    logger.info("=" * 50)
    logger.info(f"정기 매매: {settings.SCHEDULED_HOURS}시")
    logger.info(f"모니터링 간격: {settings.MONITOR_INTERVAL}초")
    logger.info("=" * 50)
    
    # 정기 매매 스케줄 설정 (4시간마다)
    for hour in settings.SCHEDULED_HOURS:
        schedule.every().day.at(f"{hour:02d}:00").do(scheduled_trade)
        logger.info(f"Scheduled: {hour:02d}:00")
    
    # 모니터링 스레드 시작
    monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
    monitor_thread.start()
    logger.info("모니터링 스레드 시작됨")
    
    # 시작 시 한번 실행 (선택)
    # scheduled_trade()
    
    # 메인 루프
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
