import os
from dotenv import load_dotenv
import pyupbit
import pandas as pd
import json
from openai import OpenAI
import ta
from ta.utils import dropna
import time
import requests
import logging
from pydantic import BaseModel
from supabase import create_client, Client
from datetime import datetime, timedelta
import schedule

# .env 파일에서 환경 변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Upbit 객체 생성
access = os.getenv("UPBIT_ACCESS_KEY")
secret = os.getenv("UPBIT_SECRET_KEY")
if not access or not secret:
    logger.error("API keys not found. Please check your .env file.")
    raise ValueError("Missing API keys. Please check your .env file.")
upbit = pyupbit.Upbit(access, secret)

# Supabase 클라이언트 초기화
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
if not supabase_url or not supabase_key:
    logger.error("Supabase credentials not found. Please check your .env file.")
    raise ValueError("Missing Supabase credentials.")
supabase: Client = create_client(supabase_url, supabase_key)
logger.info("Supabase connected successfully")

# OpenAI 구조화된 출력 체크용 클래스
class TradingDecision(BaseModel):
    decision: str
    percentage: int
    reason: str

# 거래 기록을 Supabase에 저장
def log_trade(decision, percentage, reason, btc_balance, krw_balance, btc_avg_buy_price, btc_krw_price, reflection=''):
    try:
        data = {
            "decision": decision,
            "percentage": percentage,
            "reason": reason,
            "btc_balance": float(btc_balance),
            "krw_balance": float(krw_balance),
            "btc_avg_buy_price": float(btc_avg_buy_price),
            "btc_krw_price": float(btc_krw_price),
            "reflection": reflection
        }
        supabase.table("trades").insert(data).execute()
        logger.info(f"Trade logged to Supabase: {decision}")
    except Exception as e:
        logger.error(f"Error logging trade to Supabase: {e}")

# 최근 투자 기록 조회 (Supabase)
def get_recent_trades(days=7):
    try:
        seven_days_ago = (datetime.now() - timedelta(days=days)).isoformat()
        response = supabase.table("trades") \
            .select("*") \
            .gte("timestamp", seven_days_ago) \
            .order("timestamp", desc=True) \
            .execute()

        if response.data:
            return pd.DataFrame(response.data)
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Error fetching recent trades: {e}")
        return pd.DataFrame()

# 퍼포먼스 계산
def calculate_performance(trades_df):
    if trades_df.empty:
        return 0
    initial_balance = trades_df.iloc[-1]['krw_balance'] + trades_df.iloc[-1]['btc_balance'] * trades_df.iloc[-1]['btc_krw_price']
    final_balance = trades_df.iloc[0]['krw_balance'] + trades_df.iloc[0]['btc_balance'] * trades_df.iloc[0]['btc_krw_price']
    return (final_balance - initial_balance) / initial_balance * 100

# AI 반성 생성
def generate_reflection(trades_df, current_market_data):
    performance = calculate_performance(trades_df)

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    if not client.api_key:
        logger.error("OpenAI API key is missing or invalid.")
        return None

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": "You are an AI trading assistant tasked with analyzing recent trading performance and current market conditions to generate insights and improvements for future trading decisions."
            },
            {
                "role": "user",
                "content": f"""
                Recent trading data:
                {trades_df.to_json(orient='records')}

                Current market data:
                {current_market_data}

                Overall performance in the last 7 days: {performance:.2f}%

                Please analyze this data and provide:
                1. A brief reflection on the recent trading decisions
                2. Insights on what worked well and what didn't
                3. Suggestions for improvement in future trading decisions
                4. Any patterns or trends you notice in the market data

                Limit your response to 250 words or less.
                """
            }
        ]
    )

    try:
        return response.choices[0].message.content
    except (IndexError, AttributeError) as e:
        logger.error(f"Error extracting response content: {e}")
        return None

# 보조지표 추가
def add_indicators(df):
    indicator_bb = ta.volatility.BollingerBands(close=df['close'], window=20, window_dev=2)
    df['bb_bbm'] = indicator_bb.bollinger_mavg()
    df['bb_bbh'] = indicator_bb.bollinger_hband()
    df['bb_bbl'] = indicator_bb.bollinger_lband()

    df['rsi'] = ta.momentum.RSIIndicator(close=df['close'], window=14).rsi()

    macd = ta.trend.MACD(close=df['close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['macd_diff'] = macd.macd_diff()

    df['sma_20'] = ta.trend.SMAIndicator(close=df['close'], window=20).sma_indicator()
    df['ema_12'] = ta.trend.EMAIndicator(close=df['close'], window=12).ema_indicator()

    return df

# 공포 탐욕 지수 조회
def get_fear_and_greed_index():
    url = "https://api.alternative.me/fng/"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data['data'][0]
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching Fear and Greed Index: {e}")
        return None

# 뉴스 데이터 가져오기
def get_bitcoin_news():
    serpapi_key = os.getenv("SERPAPI_API_KEY")
    if not serpapi_key:
        logger.warning("SERPAPI API key is missing.")
        return []

    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_news",
        "q": "btc",
        "api_key": serpapi_key
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        news_results = data.get("news_results", [])
        headlines = []
        for item in news_results:
            headlines.append({
                "title": item.get("title", ""),
                "date": item.get("date", "")
            })

        return headlines[:5]
    except requests.RequestException as e:
        logger.error(f"Error fetching news: {e}")
        return []

# 원띠 전략
TRADING_STRATEGY = """
원띠 투자 전략 요약:
1. 차트 위주 매매 - 호재/악재보다 차트 분석 중심
2. 시장 분위기 파악 후 유연한 대응
3. 주요 지지선/저항선 기준 매수/매도 시점 결정
4. 높은 승률 + 저배율로 리스크 관리
5. 하루 1-2% 꾸준한 수익 목표 (복리 효과)
6. 전체 시드의 20-30%만 투자
7. 분할 매수/매도 전략
8. 캔들 패턴과 이평선 활용
9. 시총이 큰 코인 위주 매매
10. 철저한 리스크 관리 - 계획에서 벗어나면 손절
"""

# 메인 AI 트레이딩 로직
def ai_trading():
    global upbit
    logger.info("=== AI Trading Started ===")

    # 1. 현재 투자 상태 조회
    all_balances = upbit.get_balances()
    filtered_balances = [balance for balance in all_balances if balance['currency'] in ['BTC', 'KRW']]

    # 2. 오더북(호가 데이터) 조회
    orderbook = pyupbit.get_orderbook("KRW-BTC")

    # 3. 차트 데이터 조회 및 보조지표 추가
    df_daily = pyupbit.get_ohlcv("KRW-BTC", interval="day", count=30)
    df_daily = dropna(df_daily)
    df_daily = add_indicators(df_daily)

    df_hourly = pyupbit.get_ohlcv("KRW-BTC", interval="minute60", count=24)
    df_hourly = dropna(df_hourly)
    df_hourly = add_indicators(df_hourly)

    # 4. 공포 탐욕 지수 가져오기
    fear_greed_index = get_fear_and_greed_index()
    logger.info(f"Fear & Greed Index: {fear_greed_index}")

    # 5. 뉴스 헤드라인 가져오기
    news_headlines = get_bitcoin_news()
    logger.info(f"News Headlines: {len(news_headlines)} items")

    # 6. 전략 파일 읽기
    try:
        with open("strategy.txt", "r", encoding="utf-8") as f:
            strategy_content = f.read()
    except FileNotFoundError:
        strategy_content = TRADING_STRATEGY
        logger.warning("strategy.txt not found, using default strategy")

    # AI에게 데이터 제공하고 판단 받기
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    if not client.api_key:
        logger.error("OpenAI API key is missing or invalid.")
        return None

    try:
        recent_trades = get_recent_trades()

        current_market_data = {
            "fear_greed_index": fear_greed_index,
            "news_headlines": news_headlines,
            "orderbook": orderbook,
            "daily_ohlcv": df_daily.to_dict(),
            "hourly_ohlcv": df_hourly.to_dict()
        }

        reflection = generate_reflection(recent_trades, current_market_data)
        logger.info("Reflection generated")

        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {
                    "role": "system",
                    "content": f"""You are an expert in Bitcoin investing. Analyze the provided data and determine whether to buy, sell, or hold at the current moment. Consider the following in your analysis:

                    - Technical indicators and market data
                    - Recent news headlines and their potential impact on Bitcoin price
                    - The Fear and Greed Index and its implications
                    - Overall market sentiment
                    - Recent trading performance and reflection

                    Recent trading reflection:
                    {reflection}

                    Particularly important is to always refer to the trading method of 'Wonyyotti', a legendary Korean investor:

                    {strategy_content}

                    Based on this trading method, analyze the current market situation and make a judgment.

                    Response format:
                    1. Decision (buy, sell, or hold)
                    2. If 'buy': percentage (1-100) of available KRW to use
                       If 'sell': percentage (1-100) of held BTC to sell
                       If 'hold': set percentage to 0
                    3. Reason for your decision

                    Ensure percentage is an integer between 1-100 for buy/sell, exactly 0 for hold."""
                },
                {
                    "role": "user",
                    "content": f"""Current investment status: {json.dumps(filtered_balances)}
                    Orderbook: {json.dumps(orderbook)}
                    Daily OHLCV with indicators (30 days): {df_daily.to_json()}
                    Hourly OHLCV with indicators (24 hours): {df_hourly.to_json()}
                    Recent news headlines: {json.dumps(news_headlines)}
                    Fear and Greed Index: {json.dumps(fear_greed_index)}"""
                }
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "trading_decision",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "decision": {"type": "string", "enum": ["buy", "sell", "hold"]},
                            "percentage": {"type": "integer"},
                            "reason": {"type": "string"}
                        },
                        "required": ["decision", "percentage", "reason"],
                        "additionalProperties": False
                    }
                }
            },
            max_tokens=4095
        )

        try:
            result = TradingDecision.model_validate_json(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            return

        logger.info(f"AI Decision: {result.decision.upper()}")
        logger.info(f"Percentage: {result.percentage}%")
        logger.info(f"Reason: {result.reason}")

        order_executed = False

        if result.decision == "buy":
            my_krw = upbit.get_balance("KRW")
            if my_krw is None:
                logger.error("Failed to retrieve KRW balance.")
                return
            buy_amount = my_krw * (result.percentage / 100) * 0.9995
            if buy_amount > 5000:
                logger.info(f"Executing Buy Order: {result.percentage}% of KRW ({buy_amount:,.0f} KRW)")
                try:
                    order = upbit.buy_market_order("KRW-BTC", buy_amount)
                    if order:
                        logger.info(f"Buy order executed: {order}")
                        order_executed = True
                    else:
                        logger.error("Buy order failed.")
                except Exception as e:
                    logger.error(f"Error executing buy order: {e}")
            else:
                logger.warning("Buy Order Failed: Insufficient KRW (< 5000)")

        elif result.decision == "sell":
            my_btc = upbit.get_balance("KRW-BTC")
            if my_btc is None:
                logger.error("Failed to retrieve BTC balance.")
                return
            sell_amount = my_btc * (result.percentage / 100)
            current_price = pyupbit.get_current_price("KRW-BTC")
            if sell_amount * current_price > 5000:
                logger.info(f"Executing Sell Order: {result.percentage}% of BTC ({sell_amount:.6f} BTC)")
                try:
                    order = upbit.sell_market_order("KRW-BTC", sell_amount)
                    if order:
                        logger.info(f"Sell order executed: {order}")
                        order_executed = True
                    else:
                        logger.error("Sell order failed.")
                except Exception as e:
                    logger.error(f"Error executing sell order: {e}")
            else:
                logger.warning("Sell Order Failed: Insufficient BTC (< 5000 KRW worth)")
        else:
            logger.info("Decision: HOLD - No action taken")

        # 잔고 조회 및 기록
        time.sleep(2)
        balances = upbit.get_balances()
        btc_balance = next((float(balance['balance']) for balance in balances if balance['currency'] == 'BTC'), 0)
        krw_balance = next((float(balance['balance']) for balance in balances if balance['currency'] == 'KRW'), 0)
        btc_avg_buy_price = next((float(balance['avg_buy_price']) for balance in balances if balance['currency'] == 'BTC'), 0)
        current_btc_price = pyupbit.get_current_price("KRW-BTC")

        log_trade(
            result.decision,
            result.percentage if order_executed else 0,
            result.reason,
            btc_balance,
            krw_balance,
            btc_avg_buy_price,
            current_btc_price,
            reflection
        )

        logger.info(f"Current Balance - BTC: {btc_balance:.6f}, KRW: {krw_balance:,.0f}")
        logger.info("=== AI Trading Completed ===\n")

    except Exception as e:
        logger.error(f"Error in ai_trading: {e}")
        return

if __name__ == "__main__":
    logger.info("Trading bot starting...")

    # 중복 실행 방지
    trading_in_progress = False

    def job():
        global trading_in_progress
        if trading_in_progress:
            logger.warning("Trading job is already in progress, skipping this run.")
            return
        try:
            trading_in_progress = True
            ai_trading()
        except Exception as e:
            logger.error(f"An error occurred: {e}")
        finally:
            trading_in_progress = False

    # 스케줄 설정: 매시간 실행
    schedule.every().hour.at(":00").do(job)

    logger.info("Trading bot started. Scheduled to run every hour at :00")
    logger.info("Waiting for scheduled time...")

    # 시작 시 한번 실행 (테스트용 - 필요시 주석 해제)
    # job()

    while True:
        schedule.run_pending()
        time.sleep(60)