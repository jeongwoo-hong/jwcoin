import os
import json
import time
import pandas as pd
import numpy as np
import requests
from dotenv import load_dotenv
import pyupbit
from openai import OpenAI
import ta
from ta.trend import MACD, SMAIndicator, EMAIndicator
from ta.momentum import RSIIndicator, StochasticOscillator, WilliamsRIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator, AccDistIndexIndicator, MFIIndicator

# 환경 변수 로드
load_dotenv()

def get_fear_greed_index(limit=7):
    """
    Fear and Greed Index API에서 공포 탐욕 지수 데이터를 가져옵니다.
    
    Parameters:
    -----------
    limit : int
        가져올 데이터의 개수 (기본값: 7일)
        
    Returns:
    --------
    dict
        공포 탐욕 지수 데이터
    """
    try:
        url = f"https://api.alternative.me/fng/?limit={limit}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Fear & Greed Index API 오류: {response.status_code}")
            return None
    except Exception as e:
        print(f"Fear & Greed Index API 요청 오류: {e}")
        return None

def interpret_fear_greed_index(fg_data):
    """
    공포 탐욕 지수 데이터를 해석합니다.
    
    Parameters:
    -----------
    fg_data : dict
        Fear and Greed Index API에서 가져온 데이터
        
    Returns:
    --------
    dict
        해석된 공포 탐욕 지수 정보
    """
    if not fg_data or "data" not in fg_data or not fg_data["data"]:
        return {
            "current": {
                "value": 0,
                "classification": "Unknown",
                "timestamp": 0,
                "time_until_update": 0
            },
            "trend": "Unknown",
            "market_sentiment": "Unknown",
            "analysis": "데이터를 가져올 수 없습니다."
        }
    
    # 현재 값
    current = fg_data["data"][0]
    current_value = int(current["value"])
    
    # 추세 계산 (최근 7일 또는 가능한 모든 데이터)
    values = [int(item["value"]) for item in fg_data["data"]]
    avg_value = sum(values) / len(values)
    
    # 추세 판단
    if current_value > avg_value + 5:
        trend = "상승"
    elif current_value < avg_value - 5:
        trend = "하락"
    else:
        trend = "유지"
    
    # 시장 심리 해석
    if current_value <= 25:
        market_sentiment = "극단적 공포"
        analysis = "시장에 극단적인 공포가 퍼져있습니다. 일반적으로 매수 기회일 수 있습니다."
    elif current_value <= 40:
        market_sentiment = "공포"
        analysis = "시장에 공포가 있습니다. 가격이 실제 가치보다 낮을 수 있어 매수 신호로 볼 수 있습니다."
    elif current_value <= 55:
        market_sentiment = "중립"
        analysis = "시장이 중립적입니다. 뚜렷한 매수/매도 신호가 없습니다."
    elif current_value <= 75:
        market_sentiment = "탐욕"
        analysis = "시장에 탐욕이 있습니다. 가격이 과대평가되었을 수 있어 주의가 필요합니다."
    else:
        market_sentiment = "극단적 탐욕"
        analysis = "시장에 극단적인 탐욕이 있습니다. 조정이 올 수 있어 매도 신호로 볼 수 있습니다."
    
    return {
        "current": {
            "value": current_value,
            "classification": current["value_classification"],
            "timestamp": int(current["timestamp"]),
            "time_until_update": int(current.get("time_until_update", 0))
        },
        "trend": trend,
        "market_sentiment": market_sentiment,
        "analysis": analysis,
        "historical_values": values
    }

def get_account_status(upbit):
    """BTC와 KRW에 대한 계정 상태 정보만 가져옵니다."""
    result = {}
    
    # KRW 잔액 확인
    krw_balance = upbit.get_balance("KRW")
    result["KRW_balance"] = krw_balance
    
    # BTC 잔액 확인
    btc_balance = upbit.get_balance("KRW-BTC")
    result["BTC_balance"] = btc_balance
    
    # BTC 현재가 확인
    current_price = pyupbit.get_current_price("KRW-BTC")
    result["BTC_current_price"] = current_price
    
    # BTC 보유 가치 계산
    btc_value = btc_balance * current_price if btc_balance else 0
    result["BTC_value_in_KRW"] = btc_value
    
    # 총 자산 가치
    result["total_value_in_KRW"] = krw_balance + btc_value
    
    # BTC 평균 매수가 (직접 필터링하여 가져옴)
    balances = upbit.get_balances()
    for balance in balances:
        if balance['currency'] == 'BTC':
            result["BTC_avg_buy_price"] = float(balance['avg_buy_price'])
            break
    
    return result

def get_orderbook_data():
    """BTC 오더북(호가) 데이터를 가져옵니다."""
    orderbook = pyupbit.get_orderbook(ticker="KRW-BTC")
    return orderbook

def add_indicators(df):
    """
    차트 데이터에 기술적 분석 지표를 추가합니다.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        OHLCV(open, high, low, close, volume) 데이터를 포함한 DataFrame
        
    Returns:
    --------
    pandas.DataFrame
        기술적 분석 지표가 추가된 DataFrame
    """
    # 데이터 프레임에 NaN 값이 있는지 확인하고 처리합니다
    df = df.copy()
    df = ta.utils.dropna(df)
    
    # 트렌드 지표 (Trend Indicators)
    # ------------------------------
    
    # 단순 이동평균선 (Simple Moving Average)
    df['sma5'] = SMAIndicator(close=df['close'], window=5).sma_indicator()
    df['sma20'] = SMAIndicator(close=df['close'], window=20).sma_indicator()
    df['sma60'] = SMAIndicator(close=df['close'], window=60).sma_indicator()
    df['sma120'] = SMAIndicator(close=df['close'], window=120).sma_indicator()
    
    # 지수 이동평균선 (Exponential Moving Average)
    df['ema12'] = EMAIndicator(close=df['close'], window=12).ema_indicator()
    df['ema26'] = EMAIndicator(close=df['close'], window=26).ema_indicator()
    df['ema200'] = EMAIndicator(close=df['close'], window=200).ema_indicator()
    
    # MACD (Moving Average Convergence Divergence)
    macd = MACD(
        close=df['close'], 
        window_slow=26, 
        window_fast=12, 
        window_sign=9
    )
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['macd_diff'] = macd.macd_diff()
    
    # 모멘텀 지표 (Momentum Indicators)
    # --------------------------------
    
    # RSI (Relative Strength Index)
    df['rsi14'] = RSIIndicator(close=df['close'], window=14).rsi()
    
    # 스토캐스틱 오실레이터 (Stochastic Oscillator)
    stoch = StochasticOscillator(
        high=df['high'],
        low=df['low'],
        close=df['close'],
        window=14,
        smooth_window=3
    )
    df['stoch_k'] = stoch.stoch()
    df['stoch_d'] = stoch.stoch_signal()
    
    # 윌리엄스 %R (Williams %R)
    df['williams_r'] = WilliamsRIndicator(
        high=df['high'],
        low=df['low'],
        close=df['close'],
        lbp=14
    ).williams_r()
    
    # 변동성 지표 (Volatility Indicators)
    # ----------------------------------
    
    # 볼린저 밴드 (Bollinger Bands)
    bollinger = BollingerBands(
        close=df['close'],
        window=20,
        window_dev=2
    )
    df['bb_high'] = bollinger.bollinger_hband()
    df['bb_mid'] = bollinger.bollinger_mavg()
    df['bb_low'] = bollinger.bollinger_lband()
    df['bb_width'] = bollinger.bollinger_wband()
    df['bb_pband'] = bollinger.bollinger_pband()  # 밴드 내 상대적 위치 (0~1)
    
    # 평균 실질 범위 (Average True Range)
    df['atr'] = AverageTrueRange(
        high=df['high'],
        low=df['low'],
        close=df['close'],
        window=14
    ).average_true_range()
    
    # 거래량 지표 (Volume Indicators)
    # -----------------------------
    
    # OBV (On-Balance Volume)
    df['obv'] = OnBalanceVolumeIndicator(
        close=df['close'],
        volume=df['volume']
    ).on_balance_volume()
    
    # 누적 분포선 (Accumulation/Distribution Line)
    df['adl'] = AccDistIndexIndicator(
        high=df['high'],
        low=df['low'],
        close=df['close'],
        volume=df['volume']
    ).acc_dist_index()
    
    # 자금 흐름 지수 (Money Flow Index)
    df['mfi'] = MFIIndicator(
        high=df['high'],
        low=df['low'],
        close=df['close'],
        volume=df['volume'],
        window=14
    ).money_flow_index()
    
    # 추가 지표들 - 커스텀 계산
    # -----------------------
    
    # 일일 수익률 (Daily Return)
    df['daily_return'] = df['close'].pct_change() * 100
    
    # 변동성 (가격 변화의 표준편차)
    df['volatility'] = df['close'].pct_change().rolling(window=20).std() * 100
    
    # 이격도 (가격과 이동평균선의 차이 비율)
    df['price_to_sma20'] = (df['close'] / df['sma20'] - 1) * 100
    
    return df

def get_chart_data():
    """BTC 차트 데이터와 기술적 분석 지표를 가져옵니다."""
    # 30일 일봉 데이터
    daily_df = pyupbit.get_ohlcv("KRW-BTC", count=30, interval="day")
    daily_df = add_indicators(daily_df)
    
    # 24시간 시간봉 데이터
    hourly_df = pyupbit.get_ohlcv("KRW-BTC", count=24, interval="minute60")
    hourly_df = add_indicators(hourly_df)
    
    return {
        "daily": daily_df.to_dict('records'),
        "hourly": hourly_df.to_dict('records'),
        "daily_df": daily_df,  # DataFrame 객체도 함께 반환
        "hourly_df": hourly_df  # DataFrame 객체도 함께 반환
    }

def analyze_technical_indicators(df):
    """
    기술적 분석 지표를 해석하여 시장 상황을 분석합니다.
    """
    result = {}
    latest = df.iloc[-1]
    
    # RSI 해석
    rsi = latest['rsi14']
    if rsi > 70:
        rsi_status = "과매수 상태 (매도 고려)"
    elif rsi < 30:
        rsi_status = "과매도 상태 (매수 기회)"
    else:
        rsi_status = "중립"
    result["rsi"] = {"value": rsi, "status": rsi_status}
    
    # MACD 해석
    macd = latest['macd']
    macd_signal = latest['macd_signal']
    macd_diff = latest['macd_diff']
    
    if macd > macd_signal and macd_diff > 0:
        macd_status = "강한 상승 신호"
    elif macd < macd_signal and macd_diff < 0:
        macd_status = "강한 하락 신호"
    elif macd > macd_signal:
        macd_status = "상승 신호 (약)"
    elif macd < macd_signal:
        macd_status = "하락 신호 (약)"
    else:
        macd_status = "중립"
    
    result["macd"] = {
        "value": macd, 
        "signal": macd_signal, 
        "diff": macd_diff, 
        "status": macd_status
    }
    
    # 볼린저 밴드 해석
    bb_pband = latest['bb_pband']
    bb_width = latest['bb_width']
    
    if bb_pband > 1:
        bb_status = "상단 돌파 (과매수 가능성)"
    elif bb_pband < 0:
        bb_status = "하단 돌파 (과매도 가능성)"
    elif bb_pband > 0.8:
        bb_status = "상단 밴드 접근 (상승 둔화 가능성)"
    elif bb_pband < 0.2:
        bb_status = "하단 밴드 접근 (반등 가능성)"
    else:
        bb_status = "중앙 밴드 부근 (추세 탐색)"
    
    result["bollinger"] = {
        "upper": latest['bb_high'],
        "middle": latest['bb_mid'],
        "lower": latest['bb_low'],
        "width": bb_width,
        "pband": bb_pband,
        "status": bb_status
    }
    
    # 스토캐스틱 해석
    stoch_k = latest['stoch_k']
    stoch_d = latest['stoch_d']
    
    if stoch_k > 80 and stoch_d > 80:
        stoch_status = "과매수 구간"
    elif stoch_k < 20 and stoch_d < 20:
        stoch_status = "과매도 구간"
    elif stoch_k > stoch_d and stoch_k < 80:
        stoch_status = "상승 반전 신호"
    elif stoch_k < stoch_d and stoch_k > 20:
        stoch_status = "하락 반전 신호"
    else:
        stoch_status = "중립"
    
    result["stochastic"] = {
        "k": stoch_k,
        "d": stoch_d,
        "status": stoch_status
    }
    
    # MFI(자금 흐름 지수) 해석
    mfi = latest['mfi']
    if mfi > 80:
        mfi_status = "과매수 상태 (돈이 빠져나갈 가능성)"
    elif mfi < 20:
        mfi_status = "과매도 상태 (돈이 유입될 가능성)"
    else:
        mfi_status = "중립"
    
    result["mfi"] = {
        "value": mfi,
        "status": mfi_status
    }
    
    # 이동평균선 정보
    result["moving_averages"] = {
        "sma5": latest['sma5'],
        "sma20": latest['sma20'],
        "sma60": latest['sma60'],
        "ema12": latest['ema12'],
        "ema26": latest['ema26'],
        "status": "상승세" if latest['sma5'] > latest['sma20'] else "하락세"
    }
    
    # 거래량 지표 해석
    result["volume"] = {
        "obv": latest['obv'],
        "adl": latest['adl'],
        "status": "증가" if df['volume'].iloc[-1] > df['volume'].iloc[-2] else "감소"
    }
    
    # 지지선/저항선 추정
    price_array = df['close'].values
    resistance_level = max(df['high'].iloc[-10:])
    support_level = min(df['low'].iloc[-10:])
    
    result["levels"] = {
        "resistance": resistance_level,
        "support": support_level
    }
    
    # 종합적인 시장 분석
    bullish_signals = 0
    bearish_signals = 0
    
    # RSI 신호
    if rsi < 30: bullish_signals += 1
    elif rsi > 70: bearish_signals += 1
    
    # MACD 신호
    if macd > macd_signal: bullish_signals += 1
    else: bearish_signals += 1
    
    # 볼린저 밴드 신호
    if bb_pband < 0.2: bullish_signals += 1
    elif bb_pband > 0.8: bearish_signals += 1
    
    # 스토캐스틱 신호
    if stoch_k < 20 and stoch_d < 20: bullish_signals += 1
    elif stoch_k > 80 and stoch_d > 80: bearish_signals += 1
    
    # 이동평균선 신호
    if latest['close'] > latest['sma20']: bullish_signals += 1
    else: bearish_signals += 1
    
    # 종합 상태
    if bullish_signals > bearish_signals + 1:
        market_status = "강한 매수 신호"
    elif bearish_signals > bullish_signals + 1:
        market_status = "강한 매도 신호"
    elif bullish_signals > bearish_signals:
        market_status = "약한 매수 신호"
    elif bearish_signals > bullish_signals:
        market_status = "약한 매도 신호"
    else:
        market_status = "중립"
    
    result["overall"] = {
        "bullish_signals": bullish_signals,
        "bearish_signals": bearish_signals,
        "status": market_status
    }
    
    return result

def print_technical_analysis(analysis):
    """
    분석된 기술적 지표 정보를 출력합니다.
    """
    print("\n===== 기술적 분석 지표 =====")
    
    # RSI 출력
    rsi = analysis["rsi"]
    print(f"RSI(14): {rsi['value']:.2f} - {rsi['status']}")
    
    # MACD 출력
    macd = analysis["macd"]
    print(f"MACD: {macd['value']:.2f}, Signal: {macd['signal']:.2f}, Diff: {macd['diff']:.2f} - {macd['status']}")
    
    # 볼린저 밴드 출력
    bb = analysis["bollinger"]
    print(f"볼린저 밴드: 상단={bb['upper']:,.0f}, 중앙={bb['middle']:,.0f}, 하단={bb['lower']:,.0f}")
    print(f"볼린저 밴드 폭: {bb['width']:.4f}, 위치: {bb['pband']:.2f} - {bb['status']}")
    
    # 스토캐스틱 출력
    stoch = analysis["stochastic"]
    print(f"스토캐스틱: K={stoch['k']:.2f}, D={stoch['d']:.2f} - {stoch['status']}")
    
    # MFI 출력
    mfi = analysis["mfi"]
    print(f"MFI: {mfi['value']:.2f} - {mfi['status']}")
    
    # 이동평균선 출력
    ma = analysis["moving_averages"]
    print(f"이동평균선: SMA(5)={ma['sma5']:,.0f}, SMA(20)={ma['sma20']:,.0f} - {ma['status']}")
    
    # 지지선/저항선 출력
    levels = analysis["levels"]
    print(f"저항선: {levels['resistance']:,.0f}원, 지지선: {levels['support']:,.0f}원")
    
    # 종합 분석 결과 출력
    overall = analysis["overall"]
    print(f"\n종합 분석: {overall['status']} (강세 신호: {overall['bullish_signals']}, 약세 신호: {overall['bearish_signals']})")

def ai_trading():
    # 업비트 API 설정
    access = os.getenv("UPBIT_ACCESS_KEY")
    secret = os.getenv("UPBIT_SECRET_KEY")
    upbit = pyupbit.Upbit(access, secret)
    
    # 계정 상태 정보 가져오기
    account_status = get_account_status(upbit)
    print("===== 계정 상태 =====")
    print(f"KRW 잔액: {account_status['KRW_balance']:,.0f}원")
    print(f"BTC 보유량: {account_status['BTC_balance']:.8f} BTC")
    print(f"BTC 현재가: {account_status['BTC_current_price']:,.0f}원")
    print(f"BTC 보유 가치: {account_status['BTC_value_in_KRW']:,.0f}원")
    print(f"총 자산 가치: {account_status['total_value_in_KRW']:,.0f}원")
    if 'BTC_avg_buy_price' in account_status:
        print(f"BTC 평균 매수가: {account_status['BTC_avg_buy_price']:,.0f}원")
    
    # 공포 탐욕 지수 가져오기
    fear_greed_data = get_fear_greed_index(limit=7)
    fear_greed_analysis = interpret_fear_greed_index(fear_greed_data)
    
    print("\n===== 공포 탐욕 지수 =====")
    current_fg = fear_greed_analysis["current"]
    print(f"현재 지수: {current_fg['value']} ({current_fg['classification']})")
    print(f"시장 심리: {fear_greed_analysis['market_sentiment']}")
    print(f"추세: {fear_greed_analysis['trend']}")
    print(f"분석: {fear_greed_analysis['analysis']}")
    
    # 지수 변화 추이 (작은 차트 형태로 표시)
    values = fear_greed_analysis.get("historical_values", [])
    if values:
        print("\n최근 추이:")
        # 간단한 ASCII 차트로 표시
        max_value = max(values)
        min_value = min(values)
        range_value = max(max_value - min_value, 1)  # 0으로 나누기 방지
        chart_width = 20
        
        for i, value in enumerate(values):
            bar_length = int((value - min_value) / range_value * chart_width)
            bar = "■" * bar_length
            date_offset = i  # 오늘부터 i일 전
            if i == 0:
                print(f"오늘: {value:2d} |{bar}")
            else:
                print(f"{date_offset}일 전: {value:2d} |{bar}")
    
    # 오더북(호가) 데이터 가져오기
    orderbook = get_orderbook_data()
    print("\n===== 오더북 정보 =====")
    print(f"매수 호가 총량: {orderbook[0]['total_bid_size']:.4f} BTC")
    print(f"매도 호가 총량: {orderbook[0]['total_ask_size']:.4f} BTC")
    print("최상위 5개 호가:")
    for i, unit in enumerate(orderbook[0]['orderbook_units'][:5]):
        print(f"  {i+1}. 매수: {unit['bid_price']:,.0f}원 ({unit['bid_size']:.4f} BTC) | 매도: {unit['ask_price']:,.0f}원 ({unit['ask_size']:.4f} BTC)")
    
    # 차트 데이터 가져오기
    chart_data = get_chart_data()
    
    # 30일 일봉 데이터 요약 정보 출력
    daily_df = chart_data["daily_df"]
    print("\n===== 30일 일봉 데이터 요약 =====")
    print(f"기간: {daily_df.index[0].strftime('%Y-%m-%d')} ~ {daily_df.index[-1].strftime('%Y-%m-%d')}")
    print(f"시작가: {daily_df['open'].iloc[0]:,.0f}원")
    print(f"현재가: {daily_df['close'].iloc[-1]:,.0f}원")
    print(f"30일 최고가: {daily_df['high'].max():,.0f}원")
    print(f"30일 최저가: {daily_df['low'].min():,.0f}원")
    print(f"30일 변동률: {((daily_df['close'].iloc[-1] / daily_df['open'].iloc[0]) - 1) * 100:.2f}%")
    
    # 기술적 분석 지표 분석 및 출력
    daily_analysis = analyze_technical_indicators(daily_df)
    hourly_analysis = analyze_technical_indicators(chart_data["hourly_df"])
    
    print_technical_analysis(daily_analysis)
    
    # AI에게 데이터 제공하고 판단 받기
    client = OpenAI()
    
    # 기술적 분석 지표가 포함된 데이터 준비
    data_for_ai = {
        "daily_chart": chart_data["daily"],
        "hourly_chart": chart_data["hourly"],
        "account_status": account_status,
        "orderbook": orderbook[0],
        "technical_analysis": {
            "daily": daily_analysis,
            "hourly": hourly_analysis
        },
        "fear_greed_index": fear_greed_analysis
    }
    
    # AI 요청
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": """You are an expert in Bitcoin investing and technical analysis. Based on the provided data, analyze the current market situation and decide whether to buy, sell, or hold Bitcoin.

Your analysis should consider:
1. Price trends and chart patterns
2. Technical indicators like RSI, MACD, Bollinger Bands, Stochastic, and MFI
3. Current account status and position
4. Market depth and orderbook data
5. Volume analysis
6. Support and resistance levels
7. Fear and Greed Index (market sentiment)

Respond in JSON format with the following structure:
{
  "decision": "buy|sell|hold",
  "reason": "detailed technical explanation of your decision",
  "confidence_level": 0.0-1.0,
  "key_indicators": {
    "trend": "bullish|bearish|neutral",
    "momentum": "strong|weak|neutral",
    "volatility": "high|normal|low",
    "support": "price level",
    "resistance": "price level"
  },
  "risk_level": "high|medium|low",
  "market_sentiment": {
    "fear_greed_assessment": "text assessment of fear and greed index",
    "sentiment_impact": "positive|negative|neutral"
  }
}
"""
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(data_for_ai)
                    }
                ]
            }
        ],
        response_format={
            "type": "json_object" 
        }
    )
    result = response.choices[0].message.content
    
    # AI의 판단에 따라 실제로 자동매매 진행하기
    result = json.loads(result)
    
    print("\n===== AI 투자 결정 =====")
    print(f"결정: {result['decision'].upper()}")
    print(f"이유: {result['reason']}")
    print(f"신뢰도: {result.get('confidence_level', 0) * 100:.1f}%")
    
    # 추가 지표 정보 출력
    if 'key_indicators' in result:
        print("\n----- 핵심 지표 분석 -----")
        indicators = result['key_indicators']
        print(f"추세: {indicators.get('trend', 'N/A')}")
        print(f"모멘텀: {indicators.get('momentum', 'N/A')}")
        print(f"변동성: {indicators.get('volatility', 'N/A')}")
        print(f"지지선: {indicators.get('support', 'N/A')}원")
        print(f"저항선: {indicators.get('resistance', 'N/A')}원")
    
    if 'risk_level' in result:
        print(f"\n위험도: {result['risk_level']}")
    
    # 시장 심리 정보 출력
    if 'market_sentiment' in result:
        sentiment = result['market_sentiment']
        print("\n----- 시장 심리 분석 -----")
        if 'fear_greed_assessment' in sentiment:
            print(f"공포 탐욕 평가: {sentiment['fear_greed_assessment']}")
        if 'sentiment_impact' in sentiment:
            impact = sentiment['sentiment_impact']
            impact_emoji = "🔴" if impact == "negative" else "🟢" if impact == "positive" else "⚪"
            print(f"심리 영향: {impact} {impact_emoji}")
    
    # 자동매매 실행
    if result["decision"] == "buy":
        my_krw = upbit.get_balance("KRW")
        if my_krw*0.9995 > 5000:
            print("\n===== 매수 주문 실행 =====")
            order_result = upbit.buy_market_order("KRW-BTC", my_krw*0.9995)
            print(f"주문 결과: {order_result}")
        else:
            print("\n===== 매수 주문 실패: KRW 잔액 부족 (5,000원 미만) =====")
    elif result["decision"] == "sell":
        my_btc = upbit.get_balance("KRW-BTC")
        current_price = pyupbit.get_orderbook(ticker="KRW-BTC")['orderbook_units'][0]["ask_price"]
        if my_btc*current_price > 5000:
            print("\n===== 매도 주문 실행 =====")
            order_result = upbit.sell_market_order("KRW-BTC", my_btc)
            print(f"주문 결과: {order_result}")
        else:
            print("\n===== 매도 주문 실패: BTC 가치 부족 (5,000원 미만) =====")
    elif result["decision"] == "hold":
        print("\n===== 홀딩 결정 =====")
        print(f"홀딩 이유: {result['reason']}")
    
    # 수익률 계산 및 출력
    if 'BTC_avg_buy_price' in account_status and account_status['BTC_balance'] > 0:
        profit_rate = (account_status['BTC_current_price'] / account_status['BTC_avg_buy_price'] - 1) * 100
        print(f"\n===== 수익률 정보 =====")
        print(f"현재 수익률: {profit_rate:.2f}%")
    
    print("\n" + "="*50 + "\n")
    return result

def main():
    print("비트코인 AI 자동매매 프로그램을 시작합니다.")
    print("Ctrl+C를 눌러 프로그램을 종료할 수 있습니다.")
    print("=" * 50)
    
    # 설정된 간격으로 자동매매 실행
    trading_interval = 60 * 10  # 10분마다 실행
    
    try:
        while True:
            print(f"\n{time.strftime('%Y-%m-%d %H:%M:%S')} - 자동매매 실행 중...")
            ai_trading()
            print(f"다음 실행 시간: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + trading_interval))}")
            time.sleep(trading_interval)
    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다.")
    except Exception as e:
        print(f"\n오류 발생: {e}")
        print("프로그램을 종료합니다.")

if __name__ == "__main__":
    main()