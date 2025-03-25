import os
import json
import time
import re
import pandas as pd
import numpy as np
import requests
import base64
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pyupbit
from openai import OpenAI
import ta
from ta.trend import MACD, SMAIndicator, EMAIndicator
from ta.momentum import RSIIndicator, StochasticOscillator, WilliamsRIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator, AccDistIndexIndicator, MFIIndicator

# 셀레니움 관련 라이브러리 추가
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import logging
from PIL import Image
import io

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BitcoinTradingBot:
    def __init__(self):
        # API 키 설정
        self.upbit_access = os.getenv("UPBIT_ACCESS_KEY")
        self.upbit_secret = os.getenv("UPBIT_SECRET_KEY")
        self.serpapi_key = os.getenv("SERPAPI_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        
        # API 클라이언트 초기화
        if self.upbit_access and self.upbit_secret:
            self.upbit = pyupbit.Upbit(self.upbit_access, self.upbit_secret)
        else:
            self.upbit = None
            logger.warning("업비트 API 키가 설정되지 않았습니다.")
        
        if self.openai_key:
            self.openai_client = OpenAI(api_key=self.openai_key)
        else:
            self.openai_client = None
            logger.warning("OpenAI API 키가 설정되지 않았습니다.")
        
        # 설정 값
        self.ticker = "KRW-BTC"  # 비트코인 티커
        self.trading_interval = 60 * 10  # 매매 주기 (10분)
        
        # 셀레니움 드라이버
        self.driver = None
        
        # 차트 스크린샷 파일 경로
        self.screenshot_dir = "chart_screenshots"
        os.makedirs(self.screenshot_dir, exist_ok=True)
        
    def setup_selenium_driver(self):
        """셀레니움 드라이버를 설정합니다."""
        try:
            logger.info("셀레니움 드라이버 초기화 중...")
            
            # 크롬 옵션 설정
            chrome_options = Options()
            chrome_options.add_argument("--start-maximized")  # 브라우저를 최대화하여 시작
            chrome_options.add_argument("--disable-dev-shm-usage")  # /dev/shm 파티션 사용 비활성화
            chrome_options.add_argument("--no-sandbox")  # 샌드박스 비활성화
            chrome_options.add_argument("--disable-gpu")  # GPU 가속 비활성화
            chrome_options.add_argument("--lang=ko_KR.UTF-8")  # 언어 및 인코딩 설정
            chrome_options.add_argument("--headless=new")  # 새로운 헤드리스 모드 (백그라운드 실행)
            
            # 드라이버 초기화
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("셀레니움 드라이버 초기화 완료")
            return True
        except Exception as e:
            logger.error(f"셀레니움 드라이버 초기화 오류: {e}")
            return False
    
    def capture_chart_screenshot(self):
        """업비트 차트 페이지를 캡처합니다."""
        if self.driver is None:
            if not self.setup_selenium_driver():
                logger.error("셀레니움 드라이버를 설정할 수 없어 차트 캡처를 건너뜁니다.")
                return None
        
        try:
            # 타임스탬프 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"upbit_btc_chart_{timestamp}.png"
            filepath = os.path.join(self.screenshot_dir, filename)
            
            # 업비트 차트 페이지 접속
            url = "https://upbit.com/full_chart?code=CRIX.UPBIT.KRW-BTC"
            logger.info(f"차트 페이지 접속 중: {url}")
            self.driver.get(url)
            
            # 페이지 로딩 대기
            logger.info("차트 로딩 대기 중...")
            time.sleep(15)  # 차트가 로드될 때까지 충분한 시간 대기
            
            # 스크린샷 캡처 시도
            logger.info("차트 스크린샷 캡처 중...")
            success = self.driver.save_screenshot(filepath)
            
            if success:
                logger.info(f"차트 스크린샷 저장 성공: {filepath}")
                return filepath
            else:
                logger.warning("스크린샷 저장 실패")
                return None
            
        except Exception as e:
            logger.error(f"차트 캡처 오류: {e}")
            return None
    
    def encode_image_to_base64(self, image_path):
        """이미지 파일을 Base64로 인코딩합니다."""
        try:
            if image_path and os.path.exists(image_path):
                with open(image_path, "rb") as image_file:
                    return base64.b64encode(image_file.read()).decode("utf-8")
            else:
                logger.warning(f"이미지 파일이 존재하지 않습니다: {image_path}")
                return None
        except Exception as e:
            logger.error(f"이미지 인코딩 오류: {e}")
            return None
    
    def get_chart_vision_analysis(self, base64_image):
        """OpenAI Vision API를 사용하여 차트 이미지를 분석합니다."""
        if not self.openai_client or not base64_image:
            logger.warning("OpenAI 클라이언트 또는 이미지가 없어 차트 비전 분석을 건너뜁니다.")
            return None
        
        try:
            logger.info("차트 이미지 비전 분석 중...")
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert in technical analysis of cryptocurrency price charts.
                                
Analyze the Bitcoin price chart image provided and identify the following:
1. Current price trend (bullish, bearish, or consolidation)
2. Key support and resistance levels visible in the chart
3. Chart patterns (e.g., head and shoulders, double tops, flags, etc.)
4. Candlestick patterns (e.g., doji, hammer, engulfing, etc.)
5. Visible technical indicators and their current signals
6. Volume analysis and what it suggests about the price movement
7. Overall market structure and potential future price direction

Respond in JSON format with the following structure:
{
  "chart_analysis": {
    "price_trend": "bullish|bearish|consolidation",
    "key_levels": {
      "support": [list of price levels],
      "resistance": [list of price levels]
    },
    "chart_patterns": [list of identified patterns],
    "candlestick_patterns": [list of identified patterns],
    "indicators": {
      "indicator_name": "bullish|bearish|neutral signal description"
    },
    "volume_analysis": "description of volume patterns and implications",
    "market_structure": "description of overall market structure",
    "potential_direction": "bullish|bearish|neutral with confidence level"
  },
  "trading_suggestion": {
    "suggestion": "buy|sell|hold",
    "reasoning": "explanation for the suggestion",
    "risk_level": "high|medium|low",
    "confidence": 0.0-1.0
  }
}"""
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Analyze this Bitcoin price chart from Upbit exchange."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                response_format={ "type": "json_object" }
            )
            
            vision_analysis = json.loads(response.choices[0].message.content)
            logger.info("차트 비전 분석 완료")
            return vision_analysis
        except Exception as e:
            logger.error(f"차트 비전 분석 오류: {e}")
            return None
    
    def get_account_status(self):
        """계정 상태 정보를 가져옵니다."""
        if not self.upbit:
            return None
            
        result = {}
        
        # KRW 잔액 확인
        krw_balance = self.upbit.get_balance("KRW")
        result["KRW_balance"] = krw_balance
        
        # BTC 잔액 확인
        btc_balance = self.upbit.get_balance(self.ticker)
        result["BTC_balance"] = btc_balance
        
        # BTC 현재가 확인
        current_price = pyupbit.get_current_price(self.ticker)
        result["BTC_current_price"] = current_price
        
        # BTC 보유 가치 계산
        btc_value = btc_balance * current_price if btc_balance else 0
        result["BTC_value_in_KRW"] = btc_value
        
        # 총 자산 가치
        result["total_value_in_KRW"] = krw_balance + btc_value
        
        # BTC 평균 매수가 (직접 필터링하여 가져옴)
        balances = self.upbit.get_balances()
        for balance in balances:
            if balance['currency'] == 'BTC':
                result["BTC_avg_buy_price"] = float(balance['avg_buy_price'])
                break
        
        return result
    
    def get_orderbook_data(self):
        """호가 데이터를 가져옵니다."""
        orderbook = pyupbit.get_orderbook(ticker=self.ticker)
        return orderbook
    
    def add_technical_indicators(self, df):
        """차트 데이터에 기술적 분석 지표를 추가합니다."""
        # 데이터 프레임에 NaN 값이 있는지 확인하고 처리합니다
        df = df.copy()
        df = ta.utils.dropna(df)
        
        # 트렌드 지표 (Trend Indicators)
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
        # 일일 수익률 (Daily Return)
        df['daily_return'] = df['close'].pct_change() * 100
        
        # 변동성 (가격 변화의 표준편차)
        df['volatility'] = df['close'].pct_change().rolling(window=20).std() * 100
        
        # 이격도 (가격과 이동평균선의 차이 비율)
        df['price_to_sma20'] = (df['close'] / df['sma20'] - 1) * 100
        
        return df
    
    def get_chart_data(self):
        """차트 데이터와 기술적 분석 지표를 가져옵니다."""
        # 30일 일봉 데이터
        daily_df = pyupbit.get_ohlcv(self.ticker, count=30, interval="day")
        daily_df = self.add_technical_indicators(daily_df)
        
        # 24시간 시간봉 데이터
        hourly_df = pyupbit.get_ohlcv(self.ticker, count=24, interval="minute60")
        hourly_df = self.add_technical_indicators(hourly_df)
        
        return {
            "daily": daily_df.to_dict('records'),
            "hourly": hourly_df.to_dict('records'),
            "daily_df": daily_df,
            "hourly_df": hourly_df
        }
    
    def analyze_technical_indicators(self, df):
        """기술적 분석 지표를 해석하여 시장 상황을 분석합니다."""
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
    
    def get_fear_greed_index(self, limit=7):
        """Fear and Greed Index API에서 공포 탐욕 지수 데이터를 가져옵니다."""
        try:
            url = f"https://api.alternative.me/fng/?limit={limit}"
            response = requests.get(url)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Fear & Greed Index API 오류: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Fear & Greed Index API 요청 오류: {e}")
            return None
    
    def interpret_fear_greed_index(self, fg_data):
        """공포 탐욕 지수 데이터를 해석합니다."""
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