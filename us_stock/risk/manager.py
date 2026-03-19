"""
리스크 관리 시스템
5겹 손실 방지 시스템 구현
"""
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import math

logger = logging.getLogger(__name__)


@dataclass
class RiskLimits:
    """리스크 한도 설정"""
    max_position_pct: float = 0.05      # 단일 종목 최대 5%
    max_sector_pct: float = 0.25        # 단일 섹터 최대 25%
    max_correlated_pct: float = 0.30    # 상관 종목군 최대 30%
    max_daily_loss_pct: float = 0.03    # 일일 최대 손실 3%
    max_weekly_loss_pct: float = 0.07   # 주간 최대 손실 7%
    min_cash_ratio: float = 0.20        # 최소 현금 비중 20%
    max_positions: int = 20             # 최대 보유 종목 수
    default_stop_loss_pct: float = 0.07 # 기본 손절 7%
    trailing_stop_pct: float = 0.10     # 트레일링 스탑 10%


class RiskManager:
    """리스크 관리자"""

    def __init__(self, limits: RiskLimits = None):
        self.limits = limits or RiskLimits()
        self.daily_pnl: Dict[str, float] = {}  # 일별 손익
        self.trade_history: List[Dict] = []

    # ==================== 1. 진입 검증 ====================

    def validate_entry(
        self,
        symbol: str,
        decision: Dict,
        portfolio: Dict,
        market_condition: Dict,
    ) -> Tuple[bool, str, Dict]:
        """
        진입 전 종합 검증

        Returns:
            (승인여부, 사유, 조정된 파라미터)
        """
        checks = []

        # 1. 포지션 크기 검증
        position_check = self._check_position_size(symbol, decision, portfolio)
        checks.append(position_check)

        # 2. 섹터 집중도 검증
        sector_check = self._check_sector_concentration(symbol, decision, portfolio)
        checks.append(sector_check)

        # 3. 일일 손실 한도 검증
        daily_check = self._check_daily_loss_limit(portfolio)
        checks.append(daily_check)

        # 4. 시장 상황 검증
        market_check = self._check_market_condition(market_condition)
        checks.append(market_check)

        # 5. 현금 비율 검증
        cash_check = self._check_cash_ratio(decision, portfolio)
        checks.append(cash_check)

        # 6. 최대 종목 수 검증
        position_count_check = self._check_position_count(symbol, portfolio)
        checks.append(position_count_check)

        # 결과 종합
        failed_checks = [c for c in checks if not c["passed"]]

        if failed_checks:
            # 실패한 검증이 있으면 거래 거부 또는 조정
            critical_failures = [c for c in failed_checks if c.get("critical")]

            if critical_failures:
                return (
                    False,
                    f"Critical risk check failed: {critical_failures[0]['reason']}",
                    {},
                )

            # 조정 가능한 경우
            adjusted_params = self._adjust_parameters(decision, failed_checks)
            return (
                True,
                f"Adjusted due to: {', '.join(c['reason'] for c in failed_checks)}",
                adjusted_params,
            )

        return (True, "All risk checks passed", decision)

    def _check_position_size(
        self, symbol: str, decision: Dict, portfolio: Dict
    ) -> Dict:
        """포지션 크기 검증"""
        requested_pct = decision.get("position_size_pct", 0) / 100
        max_allowed = self.limits.max_position_pct

        # 기존 포지션 확인
        existing = portfolio.get("positions", {}).get(symbol, {})
        existing_pct = existing.get("weight", 0)

        total_pct = existing_pct + requested_pct

        if total_pct > max_allowed:
            return {
                "passed": False,
                "reason": f"Position size {total_pct:.1%} exceeds limit {max_allowed:.1%}",
                "critical": False,
                "adjustment": {"position_size_pct": (max_allowed - existing_pct) * 100},
            }

        return {"passed": True}

    def _check_sector_concentration(
        self, symbol: str, decision: Dict, portfolio: Dict
    ) -> Dict:
        """섹터 집중도 검증"""
        sector = decision.get("sector", "Unknown")
        sector_positions = portfolio.get("sector_weights", {})
        current_sector_pct = sector_positions.get(sector, 0)

        requested_pct = decision.get("position_size_pct", 0) / 100
        total_sector_pct = current_sector_pct + requested_pct

        if total_sector_pct > self.limits.max_sector_pct:
            return {
                "passed": False,
                "reason": f"Sector {sector} concentration {total_sector_pct:.1%} exceeds {self.limits.max_sector_pct:.1%}",
                "critical": False,
                "adjustment": {
                    "position_size_pct": max(0, (self.limits.max_sector_pct - current_sector_pct) * 100)
                },
            }

        return {"passed": True}

    def _check_daily_loss_limit(self, portfolio: Dict) -> Dict:
        """일일 손실 한도 검증"""
        today = datetime.now().strftime("%Y-%m-%d")
        daily_loss = self.daily_pnl.get(today, 0)
        total_value = portfolio.get("total_value", 1)

        daily_loss_pct = abs(daily_loss) / total_value if daily_loss < 0 else 0

        if daily_loss_pct >= self.limits.max_daily_loss_pct:
            return {
                "passed": False,
                "reason": f"Daily loss {daily_loss_pct:.1%} reached limit",
                "critical": True,  # 일일 손실 한도는 critical
            }

        return {"passed": True}

    def _check_market_condition(self, market: Dict) -> Dict:
        """시장 상황 검증"""
        vix = market.get("vix", 20)
        regime = market.get("regime", "neutral")
        risk_level = market.get("risk_level", "medium")

        # 극단적 시장 상황
        if vix > 40:
            return {
                "passed": False,
                "reason": f"Extreme VIX ({vix}) - trading suspended",
                "critical": True,
            }

        if regime == "risk_off" and risk_level == "extreme":
            return {
                "passed": False,
                "reason": "Extreme risk-off environment",
                "critical": True,
            }

        # 높은 리스크 환경에서는 포지션 축소
        if risk_level in ["high", "extreme"]:
            return {
                "passed": False,
                "reason": f"High market risk ({risk_level})",
                "critical": False,
                "adjustment": {"position_size_pct_multiplier": 0.5},
            }

        return {"passed": True}

    def _check_cash_ratio(self, decision: Dict, portfolio: Dict) -> Dict:
        """현금 비율 검증"""
        current_cash_ratio = portfolio.get("cash_ratio", 1)
        requested_amount = (
            decision.get("position_size_pct", 0) / 100 * portfolio.get("total_value", 0)
        )
        cash = portfolio.get("cash", 0)

        if requested_amount > cash:
            return {
                "passed": False,
                "reason": "Insufficient cash for trade",
                "critical": True,
            }

        # 거래 후 현금 비율
        remaining_cash = cash - requested_amount
        new_cash_ratio = remaining_cash / portfolio.get("total_value", 1)

        if new_cash_ratio < self.limits.min_cash_ratio:
            max_trade = cash - (self.limits.min_cash_ratio * portfolio.get("total_value", 0))
            max_pct = max_trade / portfolio.get("total_value", 1) * 100

            return {
                "passed": False,
                "reason": f"Would reduce cash below {self.limits.min_cash_ratio:.0%}",
                "critical": False,
                "adjustment": {"position_size_pct": max(0, max_pct)},
            }

        return {"passed": True}

    def _check_position_count(self, symbol: str, portfolio: Dict) -> Dict:
        """보유 종목 수 검증"""
        current_positions = portfolio.get("positions", {})

        if symbol in current_positions:
            return {"passed": True}  # 기존 포지션 추가매수

        if len(current_positions) >= self.limits.max_positions:
            return {
                "passed": False,
                "reason": f"Maximum positions ({self.limits.max_positions}) reached",
                "critical": True,
            }

        return {"passed": True}

    def _adjust_parameters(self, decision: Dict, failed_checks: List[Dict]) -> Dict:
        """실패한 검증에 따라 파라미터 조정"""
        adjusted = decision.copy()

        for check in failed_checks:
            adjustment = check.get("adjustment", {})

            if "position_size_pct" in adjustment:
                adjusted["position_size_pct"] = min(
                    adjusted.get("position_size_pct", 0),
                    adjustment["position_size_pct"],
                )

            if "position_size_pct_multiplier" in adjustment:
                adjusted["position_size_pct"] *= adjustment["position_size_pct_multiplier"]

        # 최소 거래 금액 확인
        if adjusted.get("position_size_pct", 0) < 0.5:
            adjusted["position_size_pct"] = 0
            adjusted["decision"] = "hold"

        return adjusted

    # ==================== 2. 포지션 사이징 (Kelly Criterion) ====================

    def calculate_position_size(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        current_drawdown: float = 0,
    ) -> float:
        """
        Half-Kelly 기반 포지션 사이징

        Args:
            win_rate: 승률 (0.0 ~ 1.0)
            avg_win: 평균 수익률
            avg_loss: 평균 손실률 (양수)
            current_drawdown: 현재 드로다운 (0.0 ~ 1.0)

        Returns:
            권장 포지션 크기 (포트폴리오 비중)
        """
        if avg_loss == 0:
            return 0

        # Kelly Criterion: f = (bp - q) / b
        # b = avg_win / avg_loss (배당률)
        # p = win_rate
        # q = 1 - p
        b = avg_win / avg_loss
        p = win_rate
        q = 1 - p

        kelly = (b * p - q) / b

        # Half-Kelly (보수적)
        half_kelly = kelly / 2

        # 드로다운에 따른 추가 감소
        if current_drawdown > 0.1:
            # 드로다운 10% 이상이면 추가 축소
            drawdown_factor = 1 - (current_drawdown - 0.1) * 2
            half_kelly *= max(0.3, drawdown_factor)

        # 최대 한도 적용
        final_size = min(self.limits.max_position_pct, max(0, half_kelly))

        return round(final_size, 4)

    # ==================== 3. 손절 관리 ====================

    def calculate_stop_loss(
        self,
        entry_price: float,
        atr: float,
        support_level: float = None,
        volatility_rank: float = 0.5,
    ) -> Tuple[float, float]:
        """
        동적 손절가 계산

        Args:
            entry_price: 진입가
            atr: Average True Range
            support_level: 지지선 (있으면 사용)
            volatility_rank: 변동성 순위 (0=낮음, 1=높음)

        Returns:
            (손절가, 손절률)
        """
        # ATR 기반 기본 손절 (2 ATR)
        atr_stop = entry_price - (2 * atr)

        # 변동성에 따른 조정
        volatility_adjustment = 1 + (volatility_rank * 0.5)  # 변동성 높으면 더 넓게
        atr_stop = entry_price - (2 * atr * volatility_adjustment)

        # 지지선 활용
        if support_level and support_level < entry_price:
            # 지지선 약간 아래
            support_stop = support_level * 0.98

            # 더 보수적인(높은) 손절가 선택
            stop_price = max(atr_stop, support_stop)
        else:
            stop_price = atr_stop

        # 최소/최대 손절률 제한
        stop_pct = (entry_price - stop_price) / entry_price
        stop_pct = max(0.03, min(0.15, stop_pct))  # 3% ~ 15%

        final_stop_price = entry_price * (1 - stop_pct)

        return (round(final_stop_price, 2), round(stop_pct, 4))

    def calculate_trailing_stop(
        self, entry_price: float, current_price: float, highest_price: float
    ) -> Tuple[float, bool]:
        """
        트레일링 스탑 계산

        Returns:
            (트레일링 스탑가, 발동 여부)
        """
        # 수익 구간에서만 트레일링 적용
        if current_price <= entry_price:
            return (entry_price * (1 - self.limits.default_stop_loss_pct), False)

        # 트레일링 스탑가 계산
        trailing_stop = highest_price * (1 - self.limits.trailing_stop_pct)

        # 최소 손익분기점 보장
        trailing_stop = max(trailing_stop, entry_price * 1.01)

        triggered = current_price <= trailing_stop

        return (round(trailing_stop, 2), triggered)

    # ==================== 4. 시장 리스크 감지 ====================

    def detect_market_risk(self, market_data: Dict) -> Dict:
        """시장 리스크 감지"""
        risk_signals = []
        risk_score = 0

        vix = market_data.get("vix", 20)
        sp500_change = market_data.get("sp500_change", 0)
        yield_curve = market_data.get("yield_curve", 0)

        # VIX 스파이크
        if vix > 30:
            risk_signals.append(f"VIX elevated at {vix}")
            risk_score += 30
        if vix > 40:
            risk_signals.append(f"VIX extreme at {vix}")
            risk_score += 20

        # 급락
        if sp500_change < -2:
            risk_signals.append(f"S&P 500 down {sp500_change:.1f}%")
            risk_score += 25
        if sp500_change < -4:
            risk_signals.append("Severe market decline")
            risk_score += 25

        # 수익률 곡선 역전
        if yield_curve < -0.5:
            risk_signals.append("Deep yield curve inversion")
            risk_score += 15

        # 리스크 등급
        if risk_score >= 70:
            risk_level = "extreme"
            action = "halt_trading"
        elif risk_score >= 50:
            risk_level = "high"
            action = "reduce_exposure"
        elif risk_score >= 30:
            risk_level = "elevated"
            action = "caution"
        else:
            risk_level = "normal"
            action = "continue"

        return {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "signals": risk_signals,
            "recommended_action": action,
        }

    # ==================== 5. 블랙 스완 대응 ====================

    def black_swan_response(
        self, portfolio: Dict, market_shock: Dict
    ) -> List[Dict]:
        """
        급격한 시장 충격 대응

        Args:
            portfolio: 현재 포트폴리오
            market_shock: 충격 정보 (vix, change, etc.)

        Returns:
            긴급 액션 리스트
        """
        actions = []
        severity = market_shock.get("severity", "moderate")

        if severity == "extreme":
            # 극단적 상황: 50% 이상 현금화
            actions.append({
                "type": "emergency_liquidation",
                "target_cash_ratio": 0.7,
                "priority": "immediate",
                "reason": "Black swan event detected",
            })

            # 모든 손실 포지션 청산
            for symbol, position in portfolio.get("positions", {}).items():
                if position.get("unrealized_pnl", 0) < 0:
                    actions.append({
                        "type": "sell",
                        "symbol": symbol,
                        "quantity": position.get("quantity", 0),
                        "priority": "immediate",
                        "reason": "Emergency loss cut",
                    })

        elif severity == "high":
            # 높은 충격: 손실 포지션 정리
            for symbol, position in portfolio.get("positions", {}).items():
                pnl_pct = position.get("unrealized_pnl_pct", 0)
                if pnl_pct < -0.05:  # 5% 이상 손실
                    actions.append({
                        "type": "sell",
                        "symbol": symbol,
                        "quantity": position.get("quantity", 0),
                        "priority": "high",
                        "reason": f"Loss cut at {pnl_pct:.1%}",
                    })

            # 신규 매수 중지
            actions.append({
                "type": "trading_halt",
                "duration_hours": 24,
                "reason": "Market shock - cooling off",
            })

        return actions

    # ==================== 유틸리티 ====================

    def update_daily_pnl(self, pnl: float):
        """일일 손익 업데이트"""
        today = datetime.now().strftime("%Y-%m-%d")
        self.daily_pnl[today] = self.daily_pnl.get(today, 0) + pnl

    def get_portfolio_risk_metrics(self, portfolio: Dict) -> Dict:
        """포트폴리오 리스크 지표 계산"""
        positions = portfolio.get("positions", {})
        total_value = portfolio.get("total_value", 1)

        # 집중도 계산
        position_weights = [p.get("weight", 0) for p in positions.values()]
        max_position = max(position_weights) if position_weights else 0

        # 섹터 집중도
        sector_weights = portfolio.get("sector_weights", {})
        max_sector = max(sector_weights.values()) if sector_weights else 0

        # 현금 비율
        cash_ratio = portfolio.get("cash_ratio", 1)

        # 리스크 점수
        risk_score = 0
        if max_position > self.limits.max_position_pct:
            risk_score += 20
        if max_sector > self.limits.max_sector_pct:
            risk_score += 15
        if cash_ratio < self.limits.min_cash_ratio:
            risk_score += 25
        if len(positions) > self.limits.max_positions * 0.8:
            risk_score += 10

        return {
            "max_position_weight": max_position,
            "max_sector_weight": max_sector,
            "cash_ratio": cash_ratio,
            "position_count": len(positions),
            "risk_score": risk_score,
            "within_limits": risk_score < 30,
        }