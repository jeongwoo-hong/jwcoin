"""
시장 데이터 수집 (yfinance, Finnhub 등)
"""
import os
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

import yfinance as yf
import pandas as pd
import requests

logger = logging.getLogger(__name__)


class MarketDataCollector:
    """시장 데이터 수집기"""

    def __init__(self):
        self.finnhub_key = os.getenv("FINNHUB_API_KEY")
        self.finnhub_base = "https://finnhub.io/api/v1"

    # =========================================================================
    # yfinance 기반 데이터
    # =========================================================================

    def get_stock_info(self, symbol: str) -> Optional[Dict]:
        """종목 기본 정보"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            return {
                "symbol": symbol,
                "name": info.get("longName", ""),
                "sector": info.get("sector", ""),
                "industry": info.get("industry", ""),
                "market_cap": info.get("marketCap", 0),
                "description": info.get("longBusinessSummary", "")[:500],
                "website": info.get("website", ""),
                "employees": info.get("fullTimeEmployees", 0),
            }
        except Exception as e:
            logger.error(f"Stock info error for {symbol}: {e}")
            return None

    def get_price_history(
        self,
        symbol: str,
        period: str = "1y",
        interval: str = "1d"
    ) -> Optional[pd.DataFrame]:
        """
        과거 가격 데이터

        Args:
            symbol: 종목 코드
            period: 기간 (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: 간격 (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo)

        Returns:
            OHLCV DataFrame
        """
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)

            if df.empty:
                return None

            df = df.reset_index()
            df.columns = [c.lower() for c in df.columns]
            return df

        except Exception as e:
            logger.error(f"Price history error for {symbol}: {e}")
            return None

    def get_fundamentals(self, symbol: str) -> Optional[Dict]:
        """기본적 분석 데이터"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            return {
                "symbol": symbol,

                # 밸류에이션
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "peg_ratio": info.get("pegRatio"),
                "pb_ratio": info.get("priceToBook"),
                "ps_ratio": info.get("priceToSalesTrailing12Months"),
                "ev_ebitda": info.get("enterpriseToEbitda"),
                "ev_revenue": info.get("enterpriseToRevenue"),

                # 수익성
                "gross_margin": info.get("grossMargins"),
                "operating_margin": info.get("operatingMargins"),
                "profit_margin": info.get("profitMargins"),
                "roe": info.get("returnOnEquity"),
                "roa": info.get("returnOnAssets"),

                # 성장성
                "revenue_growth": info.get("revenueGrowth"),
                "earnings_growth": info.get("earningsGrowth"),
                "earnings_quarterly_growth": info.get("earningsQuarterlyGrowth"),

                # 재무 건전성
                "current_ratio": info.get("currentRatio"),
                "debt_to_equity": info.get("debtToEquity"),
                "total_debt": info.get("totalDebt"),
                "total_cash": info.get("totalCash"),
                "free_cash_flow": info.get("freeCashflow"),

                # 배당
                "dividend_yield": info.get("dividendYield"),
                "dividend_rate": info.get("dividendRate"),
                "payout_ratio": info.get("payoutRatio"),

                # 기타
                "beta": info.get("beta"),
                "52_week_high": info.get("fiftyTwoWeekHigh"),
                "52_week_low": info.get("fiftyTwoWeekLow"),
                "50_day_avg": info.get("fiftyDayAverage"),
                "200_day_avg": info.get("twoHundredDayAverage"),
                "avg_volume": info.get("averageVolume"),
                "shares_outstanding": info.get("sharesOutstanding"),
                "float_shares": info.get("floatShares"),
                "short_ratio": info.get("shortRatio"),

                # 실적
                "next_earnings_date": str(info.get("earningsDate", [""])[0]) if info.get("earningsDate") else None,
            }

        except Exception as e:
            logger.error(f"Fundamentals error for {symbol}: {e}")
            return None

    def get_financials(self, symbol: str) -> Optional[Dict]:
        """재무제표 데이터"""
        try:
            ticker = yf.Ticker(symbol)

            return {
                "income_statement": ticker.income_stmt.to_dict() if ticker.income_stmt is not None else {},
                "balance_sheet": ticker.balance_sheet.to_dict() if ticker.balance_sheet is not None else {},
                "cash_flow": ticker.cashflow.to_dict() if ticker.cashflow is not None else {},
            }

        except Exception as e:
            logger.error(f"Financials error for {symbol}: {e}")
            return None

    # =========================================================================
    # 시장 지표
    # =========================================================================

    def get_market_indices(self) -> Dict:
        """주요 시장 지수"""
        indices = {
            "^GSPC": "S&P 500",
            "^IXIC": "NASDAQ",
            "^DJI": "Dow Jones",
            "^RUT": "Russell 2000",
            "^VIX": "VIX",
        }

        result = {}
        for symbol, name in indices.items():
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="5d")

                if not hist.empty:
                    current = hist['Close'].iloc[-1]
                    prev = hist['Close'].iloc[-2] if len(hist) > 1 else current

                    result[name] = {
                        "price": current,
                        "change": current - prev,
                        "change_pct": (current - prev) / prev * 100,
                    }
            except Exception as e:
                logger.error(f"Index error for {symbol}: {e}")

        return result

    def get_sector_performance(self) -> Dict:
        """섹터 ETF 성과"""
        sector_etfs = {
            "XLK": "Technology",
            "XLF": "Financials",
            "XLV": "Healthcare",
            "XLE": "Energy",
            "XLY": "Consumer Discretionary",
            "XLP": "Consumer Staples",
            "XLI": "Industrials",
            "XLB": "Materials",
            "XLU": "Utilities",
            "XLRE": "Real Estate",
            "XLC": "Communication Services",
        }

        result = {}
        for symbol, sector in sector_etfs.items():
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="5d")

                if not hist.empty:
                    current = hist['Close'].iloc[-1]
                    prev = hist['Close'].iloc[-2] if len(hist) > 1 else current

                    result[sector] = {
                        "symbol": symbol,
                        "price": current,
                        "change_pct": (current - prev) / prev * 100,
                    }
            except Exception as e:
                logger.error(f"Sector ETF error for {symbol}: {e}")

        return result

    # =========================================================================
    # Finnhub 데이터 (뉴스, 애널리스트)
    # =========================================================================

    def get_news(self, symbol: str, days: int = 7) -> Optional[List[Dict]]:
        """종목 뉴스"""
        if not self.finnhub_key:
            logger.warning("Finnhub API key not set")
            return []

        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            url = f"{self.finnhub_base}/company-news"
            params = {
                "symbol": symbol,
                "from": start_date.strftime("%Y-%m-%d"),
                "to": end_date.strftime("%Y-%m-%d"),
                "token": self.finnhub_key,
            }

            response = requests.get(url, params=params)
            response.raise_for_status()
            news = response.json()

            return [
                {
                    "headline": n.get("headline"),
                    "summary": n.get("summary"),
                    "source": n.get("source"),
                    "url": n.get("url"),
                    "datetime": datetime.fromtimestamp(n.get("datetime", 0)),
                }
                for n in news[:20]  # 최근 20개
            ]

        except Exception as e:
            logger.error(f"News error for {symbol}: {e}")
            return []

    def get_analyst_ratings(self, symbol: str) -> Optional[Dict]:
        """애널리스트 평가"""
        if not self.finnhub_key:
            logger.warning("Finnhub API key not set")
            return None

        try:
            # 추천 트렌드
            url = f"{self.finnhub_base}/stock/recommendation"
            params = {"symbol": symbol, "token": self.finnhub_key}

            response = requests.get(url, params=params)
            response.raise_for_status()
            recommendations = response.json()

            if recommendations:
                latest = recommendations[0]
                total = (latest.get("strongBuy", 0) + latest.get("buy", 0) +
                        latest.get("hold", 0) + latest.get("sell", 0) +
                        latest.get("strongSell", 0))

                return {
                    "period": latest.get("period"),
                    "strong_buy": latest.get("strongBuy", 0),
                    "buy": latest.get("buy", 0),
                    "hold": latest.get("hold", 0),
                    "sell": latest.get("sell", 0),
                    "strong_sell": latest.get("strongSell", 0),
                    "total_analysts": total,
                }

            return None

        except Exception as e:
            logger.error(f"Analyst ratings error for {symbol}: {e}")
            return None

    def get_price_target(self, symbol: str) -> Optional[Dict]:
        """목표가"""
        if not self.finnhub_key:
            return None

        try:
            url = f"{self.finnhub_base}/stock/price-target"
            params = {"symbol": symbol, "token": self.finnhub_key}

            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            return {
                "target_high": data.get("targetHigh"),
                "target_low": data.get("targetLow"),
                "target_mean": data.get("targetMean"),
                "target_median": data.get("targetMedian"),
                "last_updated": data.get("lastUpdated"),
            }

        except Exception as e:
            logger.error(f"Price target error for {symbol}: {e}")
            return None

    def get_insider_trades(self, symbol: str) -> Optional[List[Dict]]:
        """내부자 거래"""
        if not self.finnhub_key:
            return []

        try:
            url = f"{self.finnhub_base}/stock/insider-transactions"
            params = {"symbol": symbol, "token": self.finnhub_key}

            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            trades = []
            for t in data.get("data", [])[:20]:
                trades.append({
                    "name": t.get("name"),
                    "share": t.get("share"),
                    "change": t.get("change"),
                    "transaction_type": t.get("transactionType"),
                    "filing_date": t.get("filingDate"),
                })

            return trades

        except Exception as e:
            logger.error(f"Insider trades error for {symbol}: {e}")
            return []

    # =========================================================================
    # 경제 지표 (간단 버전 - FRED는 별도 구현)
    # =========================================================================

    def get_treasury_yields(self) -> Dict:
        """미국 국채 수익률"""
        treasury_symbols = {
            "^TNX": "10Y",
            "^FVX": "5Y",
            "^IRX": "3M",
        }

        result = {}
        for symbol, name in treasury_symbols.items():
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="5d")

                if not hist.empty:
                    result[name] = hist['Close'].iloc[-1]
            except Exception as e:
                logger.error(f"Treasury error for {symbol}: {e}")

        return result

    def get_quick_quote(self, symbol: str) -> Optional[Dict]:
        """빠른 시세 조회 (스크리닝용)"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            hist = ticker.history(period="1y")

            if hist.empty:
                return None

            current_price = hist['Close'].iloc[-1]
            year_ago_price = hist['Close'].iloc[0]

            # RSI 계산 (간단 버전)
            delta = hist['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1] if not rsi.empty else 50

            return {
                "symbol": symbol,
                "price": current_price,
                "pe_ratio": info.get("trailingPE"),
                "52w_change": (current_price / year_ago_price - 1) * 100 if year_ago_price else 0,
                "rsi": current_rsi,
                "volume": hist['Volume'].iloc[-1] if 'Volume' in hist.columns else 0,
            }

        except Exception as e:
            logger.error(f"Quick quote error for {symbol}: {e}")
            return None