"""
주문 실행 엔진
실제 거래 실행 및 모니터링
"""
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import time

logger = logging.getLogger(__name__)


class OrderExecutor:
    """주문 실행 엔진"""

    def __init__(self, kis_client, risk_manager, db_client=None):
        """
        Args:
            kis_client: KIS API 클라이언트
            risk_manager: 리스크 관리자
            db_client: 데이터베이스 클라이언트 (Supabase 등)
        """
        self.kis = kis_client
        self.risk = risk_manager
        self.db = db_client
        self.pending_orders: Dict[str, Dict] = {}

    def execute_decision(
        self,
        decision: Dict,
        portfolio: Dict,
        market_condition: Dict,
    ) -> Dict:
        """
        AI 결정 실행

        Args:
            decision: AI 투자 결정
            portfolio: 현재 포트폴리오
            market_condition: 시장 상황

        Returns:
            실행 결과
        """
        symbol = decision.get("symbol")
        action = decision.get("decision")

        if action == "hold":
            return {
                "status": "skipped",
                "reason": "Hold decision - no action needed",
                "symbol": symbol,
            }

        # 리스크 검증
        approved, reason, adjusted = self.risk.validate_entry(
            symbol, decision, portfolio, market_condition
        )

        if not approved:
            logger.warning(f"Trade rejected for {symbol}: {reason}")
            return {
                "status": "rejected",
                "reason": reason,
                "symbol": symbol,
            }

        # 조정된 파라미터 사용
        if adjusted:
            decision = {**decision, **adjusted}

        # 포지션 크기가 0이면 스킵
        if decision.get("position_size_pct", 0) <= 0:
            return {
                "status": "skipped",
                "reason": "Position size reduced to 0 by risk management",
                "symbol": symbol,
            }

        # 실행
        if action in ["strong_buy", "buy"]:
            return self._execute_buy(decision, portfolio)
        elif action in ["strong_sell", "sell"]:
            return self._execute_sell(decision, portfolio)
        else:
            return {
                "status": "error",
                "reason": f"Unknown action: {action}",
                "symbol": symbol,
            }

    def _execute_buy(self, decision: Dict, portfolio: Dict) -> Dict:
        """매수 실행"""
        symbol = decision.get("symbol")
        position_pct = decision.get("position_size_pct", 0) / 100
        total_value = portfolio.get("total_value", 0)
        current_price = decision.get("entry_price", 0)

        if not current_price:
            # 현재가 조회
            price_data = self.kis.get_price(symbol)
            if price_data:
                current_price = price_data.get("price", 0)

        if not current_price or current_price <= 0:
            return {
                "status": "error",
                "reason": "Could not get current price",
                "symbol": symbol,
            }

        # 주문 수량 계산
        order_amount = total_value * position_pct
        quantity = int(order_amount / current_price)

        if quantity <= 0:
            return {
                "status": "skipped",
                "reason": "Order quantity is 0",
                "symbol": symbol,
            }

        # 주문 실행
        try:
            result = self.kis.buy(symbol, quantity, current_price)

            if result.get("success"):
                order_id = result.get("order_id")

                # 손절가 계산
                stop_loss_pct = decision.get("stop_loss_pct", 7) / 100
                stop_loss_price = current_price * (1 - stop_loss_pct)

                # 익절가 계산
                take_profit_pct = decision.get("take_profit_pct", 15) / 100
                take_profit_price = current_price * (1 + take_profit_pct)

                trade_record = {
                    "symbol": symbol,
                    "action": "buy",
                    "quantity": quantity,
                    "price": current_price,
                    "amount": quantity * current_price,
                    "order_id": order_id,
                    "stop_loss": stop_loss_price,
                    "take_profit": take_profit_price,
                    "decision_confidence": decision.get("confidence"),
                    "key_reasons": decision.get("key_reasons", []),
                    "model": decision.get("model"),
                    "timestamp": datetime.now().isoformat(),
                }

                # DB 기록
                self._log_trade(trade_record)

                logger.info(
                    f"BUY executed: {symbol} x{quantity} @ ${current_price:.2f}"
                )

                return {
                    "status": "success",
                    "symbol": symbol,
                    "action": "buy",
                    "quantity": quantity,
                    "price": current_price,
                    "order_id": order_id,
                    "stop_loss": stop_loss_price,
                    "take_profit": take_profit_price,
                }
            else:
                return {
                    "status": "error",
                    "reason": result.get("error", "Order failed"),
                    "symbol": symbol,
                }

        except Exception as e:
            logger.error(f"Buy execution error for {symbol}: {e}")
            return {
                "status": "error",
                "reason": str(e),
                "symbol": symbol,
            }

    def _execute_sell(self, decision: Dict, portfolio: Dict) -> Dict:
        """매도 실행"""
        symbol = decision.get("symbol")
        position = portfolio.get("positions", {}).get(symbol, {})

        if not position:
            return {
                "status": "skipped",
                "reason": f"No position in {symbol}",
                "symbol": symbol,
            }

        holding_quantity = position.get("quantity", 0)
        if holding_quantity <= 0:
            return {
                "status": "skipped",
                "reason": f"No quantity to sell for {symbol}",
                "symbol": symbol,
            }

        # 매도 비율 결정
        confidence = decision.get("confidence", 0.5)
        if confidence > 0.8:
            sell_ratio = 1.0  # 전량 매도
        elif confidence > 0.6:
            sell_ratio = 0.5  # 50% 매도
        else:
            sell_ratio = 0.3  # 30% 매도

        sell_quantity = max(1, int(holding_quantity * sell_ratio))

        # 현재가 조회
        price_data = self.kis.get_price(symbol)
        current_price = price_data.get("price", 0) if price_data else 0

        if not current_price:
            return {
                "status": "error",
                "reason": "Could not get current price",
                "symbol": symbol,
            }

        # 주문 실행
        try:
            result = self.kis.sell(symbol, sell_quantity, current_price)

            if result.get("success"):
                order_id = result.get("order_id")

                # 손익 계산
                entry_price = position.get("avg_price", current_price)
                pnl = (current_price - entry_price) * sell_quantity
                pnl_pct = (current_price / entry_price - 1) * 100

                trade_record = {
                    "symbol": symbol,
                    "action": "sell",
                    "quantity": sell_quantity,
                    "price": current_price,
                    "amount": sell_quantity * current_price,
                    "order_id": order_id,
                    "pnl": pnl,
                    "pnl_pct": pnl_pct,
                    "decision_confidence": decision.get("confidence"),
                    "key_reasons": decision.get("key_reasons", []),
                    "model": decision.get("model"),
                    "timestamp": datetime.now().isoformat(),
                }

                # DB 기록
                self._log_trade(trade_record)

                # 리스크 매니저에 손익 업데이트
                self.risk.update_daily_pnl(pnl)

                logger.info(
                    f"SELL executed: {symbol} x{sell_quantity} @ ${current_price:.2f} "
                    f"(P&L: ${pnl:+.2f}, {pnl_pct:+.1f}%)"
                )

                return {
                    "status": "success",
                    "symbol": symbol,
                    "action": "sell",
                    "quantity": sell_quantity,
                    "price": current_price,
                    "order_id": order_id,
                    "pnl": pnl,
                    "pnl_pct": pnl_pct,
                }
            else:
                return {
                    "status": "error",
                    "reason": result.get("error", "Order failed"),
                    "symbol": symbol,
                }

        except Exception as e:
            logger.error(f"Sell execution error for {symbol}: {e}")
            return {
                "status": "error",
                "reason": str(e),
                "symbol": symbol,
            }

    def execute_stop_loss(self, symbol: str, portfolio: Dict) -> Dict:
        """손절 실행"""
        logger.warning(f"Executing stop loss for {symbol}")

        position = portfolio.get("positions", {}).get(symbol, {})
        if not position:
            return {"status": "skipped", "reason": "No position"}

        quantity = position.get("quantity", 0)
        if quantity <= 0:
            return {"status": "skipped", "reason": "No quantity"}

        # 시장가 매도
        try:
            result = self.kis.sell(symbol, quantity, price=0)  # 시장가

            if result.get("success"):
                logger.info(f"Stop loss executed: {symbol} x{quantity}")

                trade_record = {
                    "symbol": symbol,
                    "action": "stop_loss",
                    "quantity": quantity,
                    "order_id": result.get("order_id"),
                    "timestamp": datetime.now().isoformat(),
                }
                self._log_trade(trade_record)

                return {"status": "success", "symbol": symbol}
            else:
                return {"status": "error", "reason": result.get("error")}

        except Exception as e:
            logger.error(f"Stop loss execution error for {symbol}: {e}")
            return {"status": "error", "reason": str(e)}

    def check_stop_conditions(self, portfolio: Dict, price_data: Dict) -> List[Dict]:
        """손절/익절 조건 확인"""
        triggered = []

        for symbol, position in portfolio.get("positions", {}).items():
            current_price = price_data.get(symbol, {}).get("price")
            if not current_price:
                continue

            entry_price = position.get("avg_price", current_price)
            stop_loss = position.get("stop_loss")
            take_profit = position.get("take_profit")
            highest_price = position.get("highest_price", current_price)

            # 손절 확인
            if stop_loss and current_price <= stop_loss:
                triggered.append({
                    "symbol": symbol,
                    "type": "stop_loss",
                    "trigger_price": stop_loss,
                    "current_price": current_price,
                })

            # 익절 확인
            elif take_profit and current_price >= take_profit:
                triggered.append({
                    "symbol": symbol,
                    "type": "take_profit",
                    "trigger_price": take_profit,
                    "current_price": current_price,
                })

            # 트레일링 스탑 확인
            else:
                trailing_stop, should_trigger = self.risk.calculate_trailing_stop(
                    entry_price, current_price, highest_price
                )
                if should_trigger:
                    triggered.append({
                        "symbol": symbol,
                        "type": "trailing_stop",
                        "trigger_price": trailing_stop,
                        "current_price": current_price,
                    })

        return triggered

    def _log_trade(self, trade: Dict):
        """거래 기록"""
        if self.db:
            try:
                self.db.table("us_stock_trades").insert(trade).execute()
            except Exception as e:
                logger.error(f"Failed to log trade: {e}")
        else:
            logger.info(f"Trade: {trade}")


class PositionMonitor:
    """포지션 모니터링"""

    def __init__(self, kis_client, executor: OrderExecutor):
        self.kis = kis_client
        self.executor = executor

    def monitor_positions(self, portfolio: Dict) -> Dict:
        """포지션 모니터링 및 가격 업데이트"""
        updated_positions = {}

        for symbol, position in portfolio.get("positions", {}).items():
            price_data = self.kis.get_price(symbol)

            if price_data:
                current_price = price_data.get("price", 0)
                entry_price = position.get("avg_price", current_price)
                quantity = position.get("quantity", 0)

                unrealized_pnl = (current_price - entry_price) * quantity
                unrealized_pnl_pct = (current_price / entry_price - 1) if entry_price else 0

                updated_positions[symbol] = {
                    **position,
                    "current_price": current_price,
                    "unrealized_pnl": unrealized_pnl,
                    "unrealized_pnl_pct": unrealized_pnl_pct,
                    "highest_price": max(
                        position.get("highest_price", current_price),
                        current_price
                    ),
                    "last_updated": datetime.now().isoformat(),
                }

        return updated_positions

    def get_portfolio_summary(self, portfolio: Dict) -> Dict:
        """포트폴리오 요약"""
        positions = portfolio.get("positions", {})
        cash = portfolio.get("cash", 0)

        total_invested = sum(
            p.get("current_price", 0) * p.get("quantity", 0)
            for p in positions.values()
        )
        total_unrealized_pnl = sum(
            p.get("unrealized_pnl", 0) for p in positions.values()
        )

        total_value = cash + total_invested

        return {
            "total_value": total_value,
            "cash": cash,
            "cash_ratio": cash / total_value if total_value else 1,
            "invested": total_invested,
            "unrealized_pnl": total_unrealized_pnl,
            "unrealized_pnl_pct": total_unrealized_pnl / (total_invested - total_unrealized_pnl) if total_invested > total_unrealized_pnl else 0,
            "position_count": len(positions),
        }