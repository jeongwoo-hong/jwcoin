import os
import json
import logging
import boto3
from datetime import datetime, timedelta
from decimal import Decimal

import pyupbit
import pandas as pd
import requests
from openai import OpenAI
import ta
from ta.utils import dropna
from pydantic import BaseModel

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# DynamoDB 클라이언트
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('DYNAMODB_TABLE', 'bitcoin_trades'))

# Upbit 객체 생성
def get_upbit_client():
    access = os.environ.get("UPBIT_ACCESS_KEY")
    secret = os.environ.get("UPBIT_SECRET_KEY")
    if not access or not secret:
        logger.error("API keys not found.")
        raise ValueError("Missing API keys")
    return pyupbit.Upbit(access, secret)

# OpenAI 구조화된 출력 체크용 클래스
class TradingDecision(BaseModel):
    decision: str
    percentage: int
    reason: str

# 거래 기록을 DynamoDB에 저장
def log_trade(decision, percentage, reason, btc_balance, krw_balance, btc_avg_buy_price, btc_krw_price, reflection=''):
    timestamp = datetime.now().isoformat()
    item = {
        'id': timestamp,
        'timestamp': timestamp,
        'decision': decision,
        'percentage': percentage,
        'reason': reason,
        'btc_balance': Decimal(str(btc_balance)),
        'krw_balance': Decimal(str(krw_balance)),
        'btc_avg_buy_price': Decimal(str(btc_avg_buy_price)),
        'btc_krw_price': Decimal(str(btc_krw_price)),
        'reflection': reflection
    }
    table.put_item(Item=item)
    logger.info(f"Trade logged: {decision}")

# 최근 투자 기록 조회 (DynamoDB)
def get_recent_trades(days=7):
    seven_days_ago = (datetime.now() - timedelta(days=days)).isoformat()
    response = table.scan(
        FilterExpression='#ts > :date',
        ExpressionAttributeNames={'#ts': 'timestamp'},
        ExpressionAttributeValues={':date': seven_days_ago}
    )
    items = response.get('Items', [])
    if not items:
        return pd.DataFrame()

    # Decimal을 float으로 변환
    for item in items:
        for key, value in item.items():
            if isinstance(value, Decimal):
                item[key] = float(value)

    df = pd.DataFrame(items)
    df = df.sort_values('timestamp', ascending=False)
    return df

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

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

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
                {trades_df.to_json(orient='records') if not trades_df.empty else "No recent trades"}

                Current market data:
                {json.dumps(current_market_data, default=str)}

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

    return response.choices[0].message.content

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
    serpapi_key = os.environ.get("SERPAPI_API_KEY")
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

# 원띠 전략 (코드에 포함)
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

# 메인 트레이딩 로직
def ai_trading():
    upbit = get_upbit_client()

    # 1. 현재 투자 상태 조회
    all_balances = upbit.get_balances()
    filtered_balances = [balance for balance in all_balances if balance['currency'] in ['BTC', 'KRW']]

    # 2. 오더북 조회
    orderbook = pyupbit.get_orderbook("KRW-BTC")

    # 3. 차트 데이터 조회 및 보조지표 추가
    df_daily = pyupbit.get_ohlcv("KRW-BTC", interval="day", count=30)
    df_daily = dropna(df_daily)
    df_daily = add_indicators(df_daily)

    df_hourly = pyupbit.get_ohlcv("KRW-BTC", interval="minute60", count=24)
    df_hourly = dropna(df_hourly)
    df_hourly = add_indicators(df_hourly)

    # 4. 공포 탐욕 지수
    fear_greed_index = get_fear_and_greed_index()

    # 5. 뉴스 헤드라인
    news_headlines = get_bitcoin_news()

    # 6. 최근 거래 내역
    recent_trades = get_recent_trades()

    # 현재 시장 데이터
    current_market_data = {
        "fear_greed_index": fear_greed_index,
        "news_headlines": news_headlines,
        "daily_ohlcv": df_daily.tail(5).to_dict(),
        "hourly_ohlcv": df_hourly.tail(5).to_dict()
    }

    # 반성 생성
    reflection = generate_reflection(recent_trades, current_market_data)

    # AI 트레이딩 결정
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

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

                Particularly important is to always refer to the trading method below:
                {TRADING_STRATEGY}

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

    result = TradingDecision.model_validate_json(response.choices[0].message.content)

    logger.info(f"AI Decision: {result.decision.upper()}")
    logger.info(f"Reason: {result.reason}")

    order_executed = False

    if result.decision == "buy":
        my_krw = upbit.get_balance("KRW")
        if my_krw is None:
            logger.error("Failed to retrieve KRW balance.")
            return {"error": "Failed to retrieve KRW balance"}
        buy_amount = my_krw * (result.percentage / 100) * 0.9995
        if buy_amount > 5000:
            logger.info(f"Buy Order: {result.percentage}% of KRW")
            order = upbit.buy_market_order("KRW-BTC", buy_amount)
            if order:
                logger.info(f"Buy order executed: {order}")
                order_executed = True
        else:
            logger.warning("Insufficient KRW (< 5000)")

    elif result.decision == "sell":
        my_btc = upbit.get_balance("KRW-BTC")
        if my_btc is None:
            logger.error("Failed to retrieve BTC balance.")
            return {"error": "Failed to retrieve BTC balance"}
        sell_amount = my_btc * (result.percentage / 100)
        current_price = pyupbit.get_current_price("KRW-BTC")
        if sell_amount * current_price > 5000:
            logger.info(f"Sell Order: {result.percentage}% of BTC")
            order = upbit.sell_market_order("KRW-BTC", sell_amount)
            if order:
                order_executed = True
        else:
            logger.warning("Insufficient BTC (< 5000 KRW worth)")

    # 잔고 조회 및 기록
    import time
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

    return {
        "decision": result.decision,
        "percentage": result.percentage,
        "reason": result.reason,
        "order_executed": order_executed
    }

# Lambda 핸들러
def lambda_handler(event, context):
    logger.info("Lambda function started")

    try:
        result = ai_trading()
        return {
            'statusCode': 200,
            'body': json.dumps(result, default=str)
        }
    except Exception as e:
        logger.error(f"Error in lambda_handler: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }