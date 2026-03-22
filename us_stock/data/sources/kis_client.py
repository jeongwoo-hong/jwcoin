"""
한국투자증권 해외주식 API 클라이언트
https://apiportal.koreainvestment.com/
"""
import os
import json
import time
import logging
import requests
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class KISClient:
    """한국투자증권 해외주식 API 클라이언트"""

    def __init__(self):
        self.app_key = os.getenv("KIS_APP_KEY")
        self.app_secret = os.getenv("KIS_APP_SECRET")
        self.account_no = os.getenv("KIS_ACCOUNT_NO")  # 계좌번호 (8자리-2자리)

        self.is_paper = os.getenv("KIS_IS_PAPER", "false").lower() == "true"

        if self.is_paper:
            self.base_url = "https://openapivts.koreainvestment.com:29443"
        else:
            self.base_url = "https://openapi.koreainvestment.com:9443"

        self.access_token = None
        self.token_expires = None

        self._validate_credentials()

    def _validate_credentials(self):
        """API 키 검증"""
        if not all([self.app_key, self.app_secret, self.account_no]):
            raise ValueError(
                "KIS API credentials not found. "
                "Set KIS_APP_KEY, KIS_APP_SECRET, KIS_ACCOUNT_NO environment variables."
            )

        # 계좌번호 형식 검증 (XXXXXXXX-XX)
        if "-" not in self.account_no:
            raise ValueError("KIS_ACCOUNT_NO should be in format: XXXXXXXX-XX")

    def _get_token(self) -> str:
        """액세스 토큰 발급/갱신"""
        # 토큰이 유효하면 재사용
        if self.access_token and self.token_expires:
            if datetime.now() < self.token_expires - timedelta(minutes=10):
                return self.access_token

        url = f"{self.base_url}/oauth2/tokenP"
        headers = {"Content-Type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
        }

        response = requests.post(url, headers=headers, json=body, timeout=30)
        response.raise_for_status()

        data = response.json()
        self.access_token = data["access_token"]
        # 토큰 만료시간 (보통 24시간)
        self.token_expires = datetime.now() + timedelta(hours=23)

        logger.info("KIS API 토큰 발급 완료")
        return self.access_token

    def _get_headers(self, tr_id: str) -> Dict:
        """API 요청 헤더 생성"""
        token = self._get_token()
        return {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
            "custtype": "P",  # 개인
        }

    def _get_account_parts(self) -> tuple:
        """계좌번호 분리 (CANO, ACNT_PRDT_CD)"""
        parts = self.account_no.split("-")
        return parts[0], parts[1]

    def _request_with_retry(
        self,
        method: str,
        url: str,
        headers: Dict,
        params: Dict = None,
        json_body: Dict = None,
        max_retries: int = 3,
        timeout: int = 30
    ) -> Optional[Dict]:
        """재시도 메커니즘이 있는 API 요청"""
        for attempt in range(max_retries):
            try:
                if method == "GET":
                    response = requests.get(url, headers=headers, params=params, timeout=timeout)
                else:
                    response = requests.post(url, headers=headers, json=json_body, timeout=timeout)

                response.raise_for_status()
                return response.json()

            except requests.Timeout:
                logger.warning(f"Request timeout (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # 지수 백오프
                else:
                    logger.error(f"Request failed after {max_retries} attempts")
                    return None

            except requests.RequestException as e:
                logger.warning(f"Request error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    logger.error(f"Request failed after {max_retries} attempts: {e}")
                    return None

        return None

    # =========================================================================
    # 시세 조회
    # =========================================================================

    def get_price(self, symbol: str, exchange: str = "NAS") -> Optional[Dict]:
        """
        해외주식 현재가 조회

        Args:
            symbol: 종목 코드 (예: AAPL)
            exchange: 거래소 (NAS: 나스닥, NYS: 뉴욕, AMS: 아멕스)

        Returns:
            현재가 정보 딕셔너리
        """
        url = f"{self.base_url}/uapi/overseas-price/v1/quotations/price"

        # 모의투자 vs 실전투자 tr_id
        tr_id = "HHDFS00000300" if not self.is_paper else "VTTT1002U"

        headers = self._get_headers(tr_id)
        params = {
            "AUTH": "",
            "EXCD": exchange,
            "SYMB": symbol,
        }

        data = self._request_with_retry("GET", url, headers, params=params)
        if not data:
            return None

        if data.get("rt_cd") == "0":
            output = data.get("output", {})
            return {
                "symbol": symbol,
                "price": float(output.get("last", 0)),
                "change": float(output.get("diff", 0)),
                "change_pct": float(output.get("rate", 0)),
                "open": float(output.get("open", 0)),
                "high": float(output.get("high", 0)),
                "low": float(output.get("low", 0)),
                "volume": int(output.get("tvol", 0)),
                "timestamp": datetime.now(),
            }
        else:
            logger.error(f"Price fetch error for {symbol}: {data.get('msg1')}")
            return None

    def get_daily_prices(
        self,
        symbol: str,
        exchange: str = "NAS",
        period: str = "D",
        count: int = 100
    ) -> Optional[List[Dict]]:
        """
        해외주식 기간별 시세 조회

        Args:
            symbol: 종목 코드
            exchange: 거래소
            period: 기간 (D: 일, W: 주, M: 월)
            count: 조회 개수

        Returns:
            OHLCV 리스트
        """
        url = f"{self.base_url}/uapi/overseas-price/v1/quotations/dailyprice"
        tr_id = "HHDFS76240000"
        headers = self._get_headers(tr_id)

        # 종료일: 오늘
        end_date = datetime.now().strftime("%Y%m%d")

        params = {
            "AUTH": "",
            "EXCD": exchange,
            "SYMB": symbol,
            "GUBN": "0",  # 0: 일, 1: 주, 2: 월
            "BYMD": end_date,
            "MODP": "1",  # 수정주가 반영
        }

        data = self._request_with_retry("GET", url, headers, params=params)
        if not data:
            return None

        if data.get("rt_cd") == "0":
            output = data.get("output2", [])
            prices = []
            for item in output[:count]:
                prices.append({
                    "date": item.get("xymd"),
                    "open": float(item.get("open", 0)),
                    "high": float(item.get("high", 0)),
                    "low": float(item.get("low", 0)),
                    "close": float(item.get("clos", 0)),
                    "volume": int(item.get("tvol", 0)),
                })
            return prices
        else:
            logger.error(f"Daily prices error for {symbol}: {data.get('msg1')}")
            return None

    # =========================================================================
    # 잔고 조회
    # =========================================================================

    def get_balance(self) -> Optional[Dict]:
        """
        해외주식 잔고 조회

        Returns:
            잔고 정보 (현금, 보유종목 등)
        """
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-balance"

        # 실전/모의 tr_id
        tr_id = "TTTS3012R" if not self.is_paper else "VTTS3012R"

        headers = self._get_headers(tr_id)
        cano, acnt_prdt_cd = self._get_account_parts()

        params = {
            "CANO": cano,
            "ACNT_PRDT_CD": acnt_prdt_cd,
            "OVRS_EXCG_CD": "NASD",  # 나스닥
            "TR_CRCY_CD": "USD",
            "CTX_AREA_FK200": "",
            "CTX_AREA_NK200": "",
        }

        data = self._request_with_retry("GET", url, headers, params=params)
        if not data:
            return None

        if data.get("rt_cd") == "0":
            output1 = data.get("output1", [])  # 보유종목
            output2 = data.get("output2", {})  # 계좌 요약

            positions = []
            for item in output1:
                if float(item.get("ovrs_cblc_qty", 0)) > 0:
                    positions.append({
                        "symbol": item.get("ovrs_pdno"),
                        "name": item.get("ovrs_item_name"),
                        "quantity": int(item.get("ovrs_cblc_qty", 0)),
                        "avg_cost": float(item.get("pchs_avg_pric", 0)),
                        "current_price": float(item.get("now_pric2", 0)),
                        "market_value": float(item.get("ovrs_stck_evlu_amt", 0)),
                        "unrealized_pnl": float(item.get("frcr_evlu_pfls_amt", 0)),
                        "unrealized_pnl_pct": float(item.get("evlu_pfls_rt", 0)),
                    })

            # 매수가능금액 조회로 실제 달러 잔고 확인
            cash_usd = self._get_buyable_cash()

            return {
                "positions": positions,
                "total_value": float(output2.get("tot_evlu_pfls_amt", 0)) if output2 else 0,
                "cash_usd": cash_usd,
                "timestamp": datetime.now(),
            }
        else:
            logger.error(f"Balance fetch error: {data.get('msg1')}")
            return None

    def _get_buyable_cash(self) -> float:
        """매수가능금액 조회로 달러 잔고 확인"""
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-psamount"
        tr_id = "TTTS3007R" if not self.is_paper else "VTTS3007R"

        headers = self._get_headers(tr_id)
        cano, acnt_prdt_cd = self._get_account_parts()

        params = {
            "CANO": cano,
            "ACNT_PRDT_CD": acnt_prdt_cd,
            "OVRS_EXCG_CD": "NASD",
            "OVRS_ORD_UNPR": "100",
            "ITEM_CD": "AAPL",
        }

        data = self._request_with_retry("GET", url, headers, params=params)
        if data and data.get("rt_cd") == "0":
            output = data.get("output", {})
            return float(output.get("ord_psbl_frcr_amt", 0))
        return 0.0

    # =========================================================================
    # 주문
    # =========================================================================

    def buy(
        self,
        symbol: str,
        quantity: int,
        price: Optional[float] = None,
        exchange: str = "NASD"
    ) -> Optional[Dict]:
        """
        해외주식 매수 주문

        Args:
            symbol: 종목 코드
            quantity: 수량
            price: 가격 (None이면 시장가)
            exchange: 거래소

        Returns:
            주문 결과
        """
        return self._place_order(
            symbol=symbol,
            quantity=quantity,
            price=price,
            side="buy",
            exchange=exchange
        )

    def sell(
        self,
        symbol: str,
        quantity: int,
        price: Optional[float] = None,
        exchange: str = "NASD"
    ) -> Optional[Dict]:
        """
        해외주식 매도 주문

        Args:
            symbol: 종목 코드
            quantity: 수량
            price: 가격 (None이면 시장가)
            exchange: 거래소

        Returns:
            주문 결과
        """
        return self._place_order(
            symbol=symbol,
            quantity=quantity,
            price=price,
            side="sell",
            exchange=exchange
        )

    def _place_order(
        self,
        symbol: str,
        quantity: int,
        price: Optional[float],
        side: str,
        exchange: str
    ) -> Optional[Dict]:
        """주문 실행"""
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/order"

        # tr_id 결정
        if self.is_paper:
            tr_id = "VTTT1002U" if side == "buy" else "VTTT1001U"
        else:
            tr_id = "TTTT1002U" if side == "buy" else "TTTT1006U"

        headers = self._get_headers(tr_id)
        cano, acnt_prdt_cd = self._get_account_parts()

        # 주문 유형 (00: 지정가, 01: 시장가)
        order_type = "00" if price else "01"

        body = {
            "CANO": cano,
            "ACNT_PRDT_CD": acnt_prdt_cd,
            "OVRS_EXCG_CD": exchange,
            "PDNO": symbol,
            "ORD_QTY": str(quantity),
            "OVRS_ORD_UNPR": str(price) if price else "0",
            "ORD_SVR_DVSN_CD": "0",
            "ORD_DVSN": order_type,
        }

        data = self._request_with_retry("POST", url, headers, json_body=body)
        if not data:
            return {"success": False, "error": "Request failed after retries"}

        if data.get("rt_cd") == "0":
            output = data.get("output", {})
            logger.info(
                f"Order placed: {side.upper()} {quantity} {symbol} "
                f"@ {'MARKET' if not price else price}"
            )
            return {
                "success": True,
                "order_id": output.get("ODNO"),
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": price,
                "timestamp": datetime.now(),
            }
        else:
            logger.error(f"Order error: {data.get('msg1')}")
            return {
                "success": False,
                "error": data.get("msg1"),
            }

    # =========================================================================
    # 체결 조회
    # =========================================================================

    def get_orders(self, status: str = "all") -> Optional[List[Dict]]:
        """
        주문 내역 조회

        Args:
            status: 조회 상태 (all: 전체, pending: 미체결, filled: 체결)

        Returns:
            주문 내역 리스트
        """
        url = f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-ccnl"

        tr_id = "TTTS3035R" if not self.is_paper else "VTTS3035R"
        headers = self._get_headers(tr_id)
        cano, acnt_prdt_cd = self._get_account_parts()

        # 오늘 날짜
        today = datetime.now().strftime("%Y%m%d")

        params = {
            "CANO": cano,
            "ACNT_PRDT_CD": acnt_prdt_cd,
            "PDNO": "",  # 전체 종목
            "ORD_STRT_DT": today,
            "ORD_END_DT": today,
            "SLL_BUY_DVSN": "00",  # 전체
            "CCLD_NCCS_DVSN": "00",  # 전체
            "OVRS_EXCG_CD": "NASD",
            "SORT_SQN": "DS",  # 내림차순
            "ORD_DT": "",
            "ORD_GNO_BRNO": "",
            "ODNO": "",
            "CTX_AREA_NK200": "",
            "CTX_AREA_FK200": "",
        }

        data = self._request_with_retry("GET", url, headers, params=params)
        if not data:
            return None

        if data.get("rt_cd") == "0":
            output = data.get("output", [])
            orders = []
            for item in output:
                orders.append({
                    "order_id": item.get("odno"),
                    "symbol": item.get("pdno"),
                    "side": "buy" if item.get("sll_buy_dvsn_cd") == "02" else "sell",
                    "quantity": int(item.get("ft_ord_qty", 0)),
                    "filled_qty": int(item.get("ft_ccld_qty", 0)),
                    "price": float(item.get("ft_ord_unpr3", 0)),
                    "filled_price": float(item.get("ft_ccld_unpr3", 0)),
                    "status": item.get("ord_stat"),
                    "timestamp": item.get("ord_tmd"),
                })
            return orders
        else:
            logger.error(f"Orders fetch error: {data.get('msg1')}")
            return None

    # =========================================================================
    # 유틸리티
    # =========================================================================

    def get_exchange_rate(self) -> Optional[float]:
        """USD/KRW 환율 조회"""
        # 간단히 고정 환율 또는 외부 API 사용
        # 실제로는 KIS API의 환율 조회 기능 사용
        try:
            # 임시로 고정 환율
            return 1350.0
        except Exception as e:
            logger.error(f"Exchange rate error: {e}")
            return None

    def is_market_open(self) -> bool:
        """미국 시장 개장 여부 확인"""
        from datetime import timezone
        import pytz

        # 미국 동부 시간
        eastern = pytz.timezone('US/Eastern')
        now_et = datetime.now(eastern)

        # 주말 체크
        if now_et.weekday() >= 5:
            return False

        # 정규장 시간 (9:30 - 16:00 ET)
        market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)

        return market_open <= now_et <= market_close