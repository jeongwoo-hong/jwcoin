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