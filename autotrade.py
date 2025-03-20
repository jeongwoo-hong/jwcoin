import os
import json
import time
import pandas as pd
from dotenv import load_dotenv
import pyupbit
from openai import OpenAI

# 환경 변수 로드
load_dotenv()

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

def get_chart_data():
    """BTC 차트 데이터를 가져옵니다."""
    # 30일 일봉 데이터
    daily_df = pyupbit.get_ohlcv("KRW-BTC", count=30, interval="day")
    
    # 24시간 시간봉 데이터
    hourly_df = pyupbit.get_ohlcv("KRW-BTC", count=24, interval="minute60")
    
    return {
        "daily": daily_df.to_dict('records'),
        "hourly": hourly_df.to_dict('records')
    }

# TA ---

import pandas as pd
import numpy as np
import pyupbit
import ta
from ta.trend import MACD, SMAIndicator, EMAIndicator
from ta.momentum import RSIIndicator, StochasticOscillator, WilliamsRIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator, AccDistIndexIndicator, MFIIndicator

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

def get_chart_with_indicators(ticker="KRW-BTC"):
    """
    특정 암호화폐의 일봉과 시간봉 데이터를 가져와 기술적 분석 지표를 추가합니다.
    
    Parameters:
    -----------
    ticker : str
        암호화폐 티커 (예: "KRW-BTC")
        
    Returns:
    --------
    tuple (pandas.DataFrame, pandas.DataFrame)
        기술적 분석 지표가 추가된 일봉과 시간봉 데이터
    """
    # 일봉 데이터 가져오기 (최근 200일)
    daily_df = pyupbit.get_ohlcv(ticker, interval="day", count=200)
    
    # 시간봉 데이터 가져오기 (최근 200시간)
    hourly_df = pyupbit.get_ohlcv(ticker, interval="minute60", count=200)
    
    # 각 데이터에 기술적 분석 지표 추가
    daily_df = add_indicators(daily_df)
    hourly_df = add_indicators(hourly_df)
    
    return daily_df, hourly_df

def print_recent_indicators(df, periods=5, title="최근 기술적 분석 지표"):
    """
    최근 몇 개 기간의 주요 기술적 분석 지표를 출력합니다.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        기술적 분석 지표가 추가된 DataFrame
    periods : int
        출력할 최근 기간 수
    title : str
        출력할 제목
    """
    print(f"\n===== {title} =====")
    
    # 주요 지표만 선택
    important_indicators = [
        'close', 'sma20', 'ema12', 'rsi14', 'macd', 'macd_signal', 
        'stoch_k', 'stoch_d', 'bb_high', 'bb_low', 'atr', 'mfi'
    ]
    
    # 최근 몇 개 기간만 선택하여 출력
    print(df[important_indicators].tail(periods))
    
    # 추가 분석: 최근 지표값에 따른 시장 상황 해석
    latest = df.iloc[-1]
    
    print("\n----- 시장 상황 해석 -----")
    
    # RSI 해석
    rsi = latest['rsi14']
    if rsi > 70:
        rsi_status = "과매수 상태 (매도 고려)"
    elif rsi < 30:
        rsi_status = "과매도 상태 (매수 기회)"
    else:
        rsi_status = "중립"
    print(f"RSI(14): {rsi:.2f} - {rsi_status}")
    
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
    
    print(f"MACD: {macd:.2f}, Signal: {macd_signal:.2f}, Diff: {macd_diff:.2f} - {macd_status}")
    
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
    
    print(f"볼린저 밴드: 위치={bb_pband:.2f}, 폭={bb_width:.2f} - {bb_status}")
    
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
    
    print(f"스토캐스틱: K={stoch_k:.2f}, D={stoch_d:.2f} - {stoch_status}")
    
    # MFI(자금 흐름 지수) 해석
    mfi = latest['mfi']
    if mfi > 80:
        mfi_status = "과매수 상태 (돈이 빠져나갈 가능성)"
    elif mfi < 20:
        mfi_status = "과매도 상태 (돈이 유입될 가능성)"
    else:
        mfi_status = "중립"
    print(f"MFI: {mfi:.2f} - {mfi_status}")

# 메인 실행 코드
if __name__ == "__main__":
    # 비트코인 데이터 가져오기 및 지표 계산
    daily_df, hourly_df = get_chart_with_indicators("KRW-BTC")
    
    # 일봉 데이터의 주요 지표 출력
    print_recent_indicators(daily_df, periods=5, title="비트코인 일봉 기술적 분석 지표")
    
    # 시간봉 데이터의 주요 지표 출력
    print_recent_indicators(hourly_df, periods=5, title="비트코인 시간봉 기술적 분석 지표")
    
    # 데이터 저장 (선택 사항)
    # daily_df.to_csv("btc_daily_with_indicators.csv")
    # hourly_df.to_csv("btc_hourly_with_indicators.csv")


# --- TA


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
    daily_df = pd.DataFrame(chart_data["daily"])
    print("\n===== 30일 일봉 데이터 요약 =====")
    print(f"기간: {daily_df.index[0].strftime('%Y-%m-%d')} ~ {daily_df.index[-1].strftime('%Y-%m-%d')}")
    print(f"시작가: {daily_df['open'].iloc[0]:,.0f}원")
    print(f"현재가: {daily_df['close'].iloc[-1]:,.0f}원")
    print(f"30일 최고가: {daily_df['high'].max():,.0f}원")
    print(f"30일 최저가: {daily_df['low'].min():,.0f}원")
    print(f"30일 변동률: {((daily_df['close'].iloc[-1] / daily_df['open'].iloc[0]) - 1) * 100:.2f}%")
    
    # AI에게 데이터 제공하고 판단 받기
    client = OpenAI()
    
    # 데이터 준비 (일봉 데이터를 기본으로 사용)
    df = pyupbit.get_ohlcv("KRW-BTC", count=30, interval="day")
    
    data_for_ai = {
        "daily_chart": df.to_dict('records'),
        "hourly_chart": chart_data["hourly"],
        "account_status": account_status,
        "orderbook": orderbook[0]
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
                        "text": "You are an expert in Bitcoin investing. Tell me whether to buy, sell, or hold at the moment based on the chart data, account status, and orderbook provided. response in json format.\n\nResponse Example : \n{\"decision\":\"buy\", \"reason\":\"some technical reason\", \"confidence_level\": 0.8}\n{\"decision\":\"sell\", \"reason\":\"some technical reason\", \"confidence_level\": 0.7}\n{\"decision\":\"hold\", \"reason\":\"some technical reason\", \"confidence_level\": 0.6}\n"
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