"""
US Stock Wealth Builder - 미국 주식 자동매매 시스템
메인 실행 파일
"""
import os
import sys
import time
import schedule
from datetime import datetime
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 로깅 설정
from us_stock.utils.logger import setup_logger
logger = setup_logger("us_stock", "INFO")

# 모듈 임포트
from us_stock.config import settings
from us_stock.config.watchlist import WATCHLIST, get_sector
from us_stock.data.sources.kis_client import KISClient
from us_stock.data.sources.market_data import MarketDataCollector

# 분석 엔진
from us_stock.analysis.scoring import ComprehensiveScorer
from us_stock.analysis.ai_analyzer import AIAnalyzer, QuickAnalyzer

# 리스크 관리
from us_stock.risk.manager import RiskManager, RiskLimits

# 실행
from us_stock.execution.executor import OrderExecutor, PositionMonitor


class USStockTrader:
    """미국 주식 자동매매 시스템"""

    def __init__(self):
        logger.info("=" * 60)
        logger.info("US Stock Wealth Builder 시작")
        logger.info("=" * 60)

        # 클라이언트 초기화
        self.kis = KISClient()
        self.market_data = MarketDataCollector()

        # 분석기 초기화
        self.scorer = ComprehensiveScorer()

        # AI 분석기 (Claude API)
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            self.ai_analyzer = AIAnalyzer(anthropic_key)
            self.quick_analyzer = QuickAnalyzer(anthropic_key)
            logger.info("Claude AI 분석기 활성화")
        else:
            self.ai_analyzer = None
            self.quick_analyzer = None
            logger.warning("ANTHROPIC_API_KEY 없음 - AI 분석 비활성화")

        # 리스크 관리자
        self.risk_manager = RiskManager(RiskLimits(
            max_position_pct=settings.MAX_POSITION_RATIO,
            max_daily_loss_pct=settings.MAX_DAILY_LOSS,
            min_cash_ratio=settings.MIN_CASH_RATIO,
        ))

        # 실행기
        self.executor = OrderExecutor(self.kis, self.risk_manager)
        self.monitor = PositionMonitor(self.kis, self.executor)

        # 상태
        self.is_running = True
        self.last_analysis_time = None
        self.trading_halted = False

        logger.info(f"거래 모드: {'모의투자' if self.kis.is_paper else '실전투자'}")
        logger.info(f"감시 종목: {len(WATCHLIST)}개")
        logger.info("초기화 완료")

    def check_market_status(self) -> bool:
        """시장 상태 확인"""
        is_open = self.kis.is_market_open()
        logger.info(f"미국 시장 상태: {'개장' if is_open else '폐장'}")
        return is_open

    def _can_trade(self, require_market_open: bool = True) -> bool:
        """거래 가능 여부 체크"""
        if require_market_open and not self.kis.is_market_open():
            logger.info("시장 미개장")
            return False

        if self.trading_halted:
            logger.warning("거래 중단 상태")
            return False

        return True

    def _get_analysis_context(self) -> tuple:
        """분석 컨텍스트 조회 (포트폴리오 + 시장 상황)"""
        portfolio = self.get_portfolio_status()
        if not portfolio:
            return None, None

        market_condition = self.get_market_condition()
        return portfolio, market_condition

    def get_portfolio_status(self) -> dict:
        """포트폴리오 현황 조회"""
        logger.info("포트폴리오 현황 조회 중...")

        balance = self.kis.get_balance()
        if not balance:
            logger.error("잔고 조회 실패")
            return None

        positions = balance.get("positions", [])
        cash = balance.get("cash_usd", 0)

        # 포지션을 딕셔너리로 변환
        position_dict = {}
        total_invested = 0

        for pos in positions:
            symbol = pos.get("symbol")
            quantity = pos.get("quantity", 0)
            current_price = pos.get("current_price", 0)
            avg_cost = pos.get("avg_cost", current_price)
            market_value = quantity * current_price

            position_dict[symbol] = {
                "symbol": symbol,
                "quantity": quantity,
                "avg_price": avg_cost,
                "current_price": current_price,
                "market_value": market_value,
                "unrealized_pnl": (current_price - avg_cost) * quantity,
                "unrealized_pnl_pct": (current_price / avg_cost - 1) if avg_cost else 0,
                "sector": get_sector(symbol),
            }
            total_invested += market_value

        total_value = cash + total_invested

        # 섹터별 가중치 계산
        sector_weights = {}
        for pos in position_dict.values():
            sector = pos.get("sector", "Unknown")
            weight = pos.get("market_value", 0) / total_value if total_value else 0
            sector_weights[sector] = sector_weights.get(sector, 0) + weight
            pos["weight"] = weight

        portfolio = {
            "total_value": total_value,
            "cash": cash,
            "cash_ratio": cash / total_value if total_value else 1,
            "invested": total_invested,
            "positions": position_dict,
            "sector_weights": sector_weights,
        }

        logger.info(f"총 자산: ${total_value:,.2f}")
        logger.info(f"현금: ${cash:,.2f} ({portfolio['cash_ratio']:.1%})")
        logger.info(f"투자금: ${total_invested:,.2f}")
        logger.info(f"보유 종목: {len(positions)}개")

        for symbol, pos in position_dict.items():
            logger.info(
                f"  {symbol}: {pos['quantity']}주 "
                f"@ ${pos['avg_price']:.2f} → ${pos['current_price']:.2f} "
                f"({pos['unrealized_pnl_pct']:+.1%})"
            )

        return portfolio

    def get_market_condition(self) -> dict:
        """시장 상황 조회"""
        logger.info("시장 현황 조회 중...")

        indices = self.market_data.get_market_indices()
        treasury = self.market_data.get_treasury_yields()
        sectors = self.market_data.get_sector_performance()

        vix = indices.get("VIX", {}).get("price", 20)
        sp500_change = indices.get("S&P 500", {}).get("change_pct", 0)

        for name, data in indices.items():
            logger.info(
                f"  {name}: {data['price']:,.2f} ({data['change_pct']:+.2f}%)"
            )

        # 리스크 레벨 판단
        risk_check = self.risk_manager.detect_market_risk({
            "vix": vix,
            "sp500_change": sp500_change,
            "yield_curve": treasury.get("10Y", 4) - treasury.get("2Y", 4),
        })

        return {
            "indices": indices,
            "treasury": treasury,
            "sectors": sectors,
            "vix": vix,
            "sp500_change": sp500_change,
            "is_open": self.kis.is_market_open(),
            "risk_level": risk_check.get("risk_level"),
            "risk_signals": risk_check.get("signals", []),
            "timestamp": datetime.now().isoformat(),
        }

    def analyze_stock(self, symbol: str, market_condition: dict) -> dict:
        """개별 종목 분석"""
        logger.info(f"[{symbol}] 분석 중...")

        try:
            sector = get_sector(symbol)

            # 가격 데이터
            price_data = self.market_data.get_price_history(symbol, period="6mo")
            if price_data is None or price_data.empty:
                logger.warning(f"[{symbol}] 가격 데이터 없음")
                return None

            # 펀더멘털 데이터
            fundamental = self.market_data.get_fundamentals(symbol)

            # 뉴스
            news = self.market_data.get_news(symbol, days=7)

            # 애널리스트 평가
            analyst = self.market_data.get_analyst_ratings(symbol)

            # 목표가
            target = self.market_data.get_price_target(symbol)

            # 내부자 거래
            insider = self.market_data.get_insider_trades(symbol)

            # 종합 분석
            result = self.scorer.analyze(
                symbol=symbol,
                price_data=price_data,
                fundamental_data=fundamental,
                news=news,
                analyst_ratings=analyst,
                price_target=target,
                insider_trades=insider,
                market_indices=market_condition.get("indices", {}),
                treasury_yields=market_condition.get("treasury", {}),
                sector_performance=market_condition.get("sectors", {}),
                sector=sector,
            )

            score = result.get("adjusted_score", 0)
            signal = result.get("signal", "hold")
            logger.info(f"[{symbol}] 점수: {score:.1f}, 신호: {signal}")

            return result

        except Exception as e:
            logger.error(f"[{symbol}] 분석 오류: {e}")
            return None

    def pre_market_analysis(self):
        """프리마켓 분석 (매일 22:00 KST)"""
        logger.info("=" * 60)
        logger.info("프리마켓 분석 시작")
        logger.info("=" * 60)

        try:
            # 1. 시장 현황
            market_condition = self.get_market_condition()

            # 시장 리스크 체크
            if market_condition.get("risk_level") == "extreme":
                logger.warning("극단적 시장 리스크 - 분석 중단")
                self.trading_halted = True
                return

            # 2. 포트폴리오 상태
            portfolio = self.get_portfolio_status()
            if not portfolio:
                return

            # 3. 빠른 스크리닝 (Haiku)
            candidates = []
            if self.quick_analyzer:
                logger.info("빠른 스크리닝 시작...")
                for symbol in WATCHLIST:
                    basic_data = self.market_data.get_quick_quote(symbol)
                    if basic_data:
                        screen_result = self.quick_analyzer.quick_screen(symbol, basic_data)
                        if screen_result.get("worth_analyzing"):
                            candidates.append(symbol)

                logger.info(f"스크리닝 결과: {len(candidates)}/{len(WATCHLIST)} 종목 선정")
            else:
                # AI 없으면 전체 분석
                candidates = list(WATCHLIST)

            # 4. 상세 분석
            analyses = []
            for symbol in candidates[:20]:  # 최대 20개
                result = self.analyze_stock(symbol, market_condition)
                if result:
                    analyses.append(result)

            # 5. AI 최종 분석 (Sonnet)
            if self.ai_analyzer and analyses:
                logger.info("AI 최종 분석 시작...")
                recommendations = self.ai_analyzer.batch_analyze(
                    analyses=analyses,
                    portfolio=portfolio,
                    market_condition=market_condition,
                    max_recommendations=5,
                )

                buy_recs = recommendations.get("buy_recommendations", [])
                sell_recs = recommendations.get("sell_recommendations", [])

                logger.info(f"매수 추천: {len(buy_recs)}개")
                for rec in buy_recs:
                    logger.info(
                        f"  {rec.get('symbol')}: {rec.get('decision')} "
                        f"(확신도: {rec.get('confidence', 0):.0%})"
                    )

                logger.info(f"매도 추천: {len(sell_recs)}개")
                for rec in sell_recs:
                    logger.info(
                        f"  {rec.get('symbol')}: {rec.get('decision')} "
                        f"(확신도: {rec.get('confidence', 0):.0%})"
                    )

            logger.info("프리마켓 분석 완료")

        except Exception as e:
            logger.error(f"프리마켓 분석 오류: {e}")

    def market_open_check(self):
        """장 시작 체크 (23:35 KST)"""
        logger.info("=" * 60)
        logger.info("장 시작 체크")
        logger.info("=" * 60)

        try:
            if not self._can_trade():
                return

            portfolio, market_condition = self._get_analysis_context()
            if not portfolio:
                return

            # 손절 조건 체크
            self._check_stop_conditions(portfolio, market_condition)

            logger.info("장 시작 체크 완료")

        except Exception as e:
            logger.error(f"장 시작 체크 오류: {e}")

    def intraday_check(self):
        """장중 체크"""
        logger.info("장중 모니터링...")

        try:
            if not self._can_trade():
                return

            portfolio, market_condition = self._get_analysis_context()
            if not portfolio:
                return

            # 블랙 스완 감지
            if market_condition.get("risk_level") == "extreme":
                logger.warning("!!! 긴급 상황 감지 !!!")
                self._handle_emergency(portfolio, market_condition)
                return

            # 손절 조건 체크
            self._check_stop_conditions(portfolio, market_condition)

        except Exception as e:
            logger.error(f"장중 체크 오류: {e}")

    def _check_stop_conditions(self, portfolio: dict, market_condition: dict):
        """손절/익절 조건 체크"""
        # 각 포지션의 현재가 조회
        price_data = {}
        for symbol in portfolio.get("positions", {}).keys():
            quote = self.kis.get_price(symbol)
            if quote:
                price_data[symbol] = quote

        # 손절/익절 조건 확인
        triggered = self.executor.check_stop_conditions(portfolio, price_data)

        for trigger in triggered:
            symbol = trigger.get("symbol")
            trigger_type = trigger.get("type")

            logger.warning(
                f"[{symbol}] {trigger_type} 발동: "
                f"현재가 ${trigger.get('current_price'):.2f}"
            )

            # 실행
            result = self.executor.execute_stop_loss(symbol, portfolio)
            logger.info(f"[{symbol}] 실행 결과: {result.get('status')}")

    def _handle_emergency(self, portfolio: dict, market_condition: dict):
        """긴급 상황 대응"""
        logger.warning("=" * 40)
        logger.warning("긴급 상황 대응 시작")
        logger.warning("=" * 40)

        severity = "extreme" if market_condition.get("vix", 20) > 40 else "high"

        actions = self.risk_manager.black_swan_response(
            portfolio, {"severity": severity}
        )

        for action in actions:
            logger.warning(f"긴급 조치: {action}")

            if action.get("type") == "sell":
                result = self.executor.execute_stop_loss(
                    action.get("symbol"), portfolio
                )
                logger.info(f"실행 결과: {result}")

            elif action.get("type") == "trading_halt":
                self.trading_halted = True
                logger.warning("거래 중단됨")

        logger.warning("긴급 상황 대응 완료")

    def daily_review(self):
        """일일 리뷰 (07:00 KST)"""
        logger.info("=" * 60)
        logger.info("일일 리뷰")
        logger.info("=" * 60)

        try:
            # 최종 포트폴리오 상태
            portfolio = self.get_portfolio_status()
            if not portfolio:
                return

            # 리스크 지표
            risk_metrics = self.risk_manager.get_portfolio_risk_metrics(portfolio)
            logger.info("리스크 지표:")
            logger.info(f"  최대 포지션 비중: {risk_metrics['max_position_weight']:.1%}")
            logger.info(f"  최대 섹터 비중: {risk_metrics['max_sector_weight']:.1%}")
            logger.info(f"  현금 비율: {risk_metrics['cash_ratio']:.1%}")
            logger.info(f"  한도 내: {risk_metrics['within_limits']}")

            # 거래 중단 해제
            if self.trading_halted:
                logger.info("거래 중단 상태 해제")
                self.trading_halted = False

            logger.info("일일 리뷰 완료")

        except Exception as e:
            logger.error(f"일일 리뷰 오류: {e}")

    def setup_schedule(self):
        """스케줄 설정"""
        logger.info("스케줄 설정 중...")

        # 프리마켓 분석 (22:00 KST)
        schedule.every().day.at("22:00").do(self.pre_market_analysis)
        logger.info("  - 프리마켓 분석: 22:00")

        # 장 시작 체크 (23:35 KST)
        schedule.every().day.at("23:35").do(self.market_open_check)
        logger.info("  - 장 시작 체크: 23:35")

        # 장중 체크 (00:00, 01:00, 02:00, 03:00, 04:00, 05:00 KST)
        for hour in ["00:00", "01:00", "02:00", "03:00", "04:00", "05:00"]:
            schedule.every().day.at(hour).do(self.intraday_check)
        logger.info("  - 장중 체크: 00:00~05:00 (매시간)")

        # 장 마감 전 (05:45 KST)
        schedule.every().day.at("05:45").do(self.intraday_check)
        logger.info("  - 장 마감 전: 05:45")

        # 일일 리뷰 (07:00 KST)
        schedule.every().day.at("07:00").do(self.daily_review)
        logger.info("  - 일일 리뷰: 07:00")

        logger.info("스케줄 설정 완료")

    def run(self):
        """메인 실행"""
        try:
            # 스케줄 설정
            self.setup_schedule()

            # 초기 상태 확인
            logger.info("\n초기 상태 확인...")
            self.check_market_status()
            self.get_portfolio_status()

            logger.info("\n" + "=" * 60)
            logger.info("자동매매 시스템 가동 중...")
            logger.info("종료하려면 Ctrl+C를 누르세요.")
            logger.info("=" * 60 + "\n")

            # 메인 루프
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)  # 1분마다 스케줄 체크

        except KeyboardInterrupt:
            logger.info("\n시스템 종료 요청...")
            self.is_running = False

        except Exception as e:
            logger.error(f"시스템 오류: {e}")
            raise

        finally:
            logger.info("US Stock Wealth Builder 종료")


def main():
    """메인 함수"""
    # 필수 환경변수 체크
    required_vars = ["KIS_APP_KEY", "KIS_APP_SECRET", "KIS_ACCOUNT_NO"]
    missing = [v for v in required_vars if not os.getenv(v)]

    if missing:
        print(f"Error: Missing environment variables: {', '.join(missing)}")
        print("\nRequired variables:")
        print("  KIS_APP_KEY      - 한국투자증권 앱 키")
        print("  KIS_APP_SECRET   - 한국투자증권 앱 시크릿")
        print("  KIS_ACCOUNT_NO   - 계좌번호 (XXXXXXXX-XX)")
        print("\nOptional variables:")
        print("  KIS_IS_PAPER     - 모의투자 여부 (true/false)")
        print("  FINNHUB_API_KEY  - Finnhub API 키 (뉴스/애널리스트)")
        print("  ANTHROPIC_API_KEY - Claude API 키")
        sys.exit(1)

    # 트레이더 실행
    trader = USStockTrader()
    trader.run()


if __name__ == "__main__":
    main()