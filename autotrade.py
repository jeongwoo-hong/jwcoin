import os
import json
import time
import re
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
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
            print("업비트 API 키가 설정되지 않았습니다.")
        
        if self.openai_key:
            self.openai_client = OpenAI(api_key=self.openai_key)
        else:
            self.openai_client = None
            print("OpenAI API 키가 설정되지 않았습니다.")
        
        # 설정 값
        self.ticker = "KRW-BTC"  # 비트코인 티커
        self.trading_interval = 60 * 10  # 매매 주기 (10분)
    
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
                print(f"Fear & Greed Index API 오류: {response.status_code}")
                return None
        except Exception as e:
            print(f"Fear & Greed Index API 요청 오류: {e}")
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
    
    def get_crypto_news(self, query="bitcoin", num_results=10, language="en", country="us"):
        """SerpAPI를 사용하여 암호화폐 관련 뉴스를 가져옵니다."""
        if not self.serpapi_key:
            return None
            
        base_url = "https://serpapi.com/search.json"
        
        params = {
            "engine": "google_news",
            "q": query,
            "api_key": self.serpapi_key,
            "hl": language,
            "gl": country,
            "num": num_results
        }
        
        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"뉴스 데이터 요청 오류: {e}")
            return None
    
    def extract_article_info(self, news_data):
        """SerpAPI의 응답에서 뉴스 기사의 제목과 날짜만 추출합니다."""
        articles = []
        
        if not news_data or "news_results" not in news_data:
            return articles
        
        for article in news_data.get("news_results", []):
            # 기본 정보 추출 (제목과 날짜만)
            article_info = {
                "title": article.get("title", ""),
                "source": article.get("source", {}).get("name", "Unknown"),
                "date": article.get("date", ""),
                "timestamp": datetime.now().isoformat()
            }
            
            # 하이라이트가 있으면 추가
            if "highlight" in article and "title" in article["highlight"] and article["highlight"]["title"]:
                article_info["title"] = article["highlight"]["title"]
            
            # 스토리가 있으면 처리
            if "stories" in article and article["stories"]:
                article_info["related_stories"] = []
                for story in article["stories"]:
                    story_info = {
                        "title": story.get("title", ""),
                        "source": story.get("source", {}).get("name", "Unknown"),
                        "date": story.get("date", "")
                    }
                    article_info["related_stories"].append(story_info)
            
            articles.append(article_info)
        
        return articles
    
    def analyze_news_sentiment(self, articles):
        """뉴스 기사의 제목을 분석하여 시장 분위기를 평가합니다."""
        if not articles:
            return {
                "sentiment": "neutral",
                "bullish_count": 0,
                "bearish_count": 0,
                "neutral_count": 0,
                "important_news": []
            }
        
        # 감정 분석 키워드
        bullish_keywords = [
            "surge", "rally", "soar", "jump", "gain", "rise", "climb", "recover",
            "positive", "bull", "bullish", "uptrend", "growth", "optimistic", "adoption",
            "breakthrough", "success", "outperform", "boost", "record high"
        ]
        
        bearish_keywords = [
            "crash", "fall", "drop", "decline", "tumble", "plunge", "sink", "dip",
            "negative", "bear", "bearish", "downtrend", "pessimistic", "fear",
            "risk", "concern", "warning", "underperform", "struggle", "record low"
        ]
        
        important_keywords = [
            "regulation", "sec", "fed", "federal reserve", "ban", "legal", "law", 
            "government", "hack", "security", "breach", "etf", "halving", "major", 
            "billion", "million", "institutional", "adoption", "whale", "record"
        ]
        
        bullish_count = 0
        bearish_count = 0
        neutral_count = 0
        important_news = []
        
        for article in articles:
            title = article.get("title", "").lower()
            
            is_bullish = any(keyword in title for keyword in bullish_keywords)
            is_bearish = any(keyword in title for keyword in bearish_keywords)
            is_important = any(keyword in title for keyword in important_keywords)
            
            if is_important:
                important_news.append({
                    "title": article["title"],
                    "source": article["source"],
                    "date": article.get("date", "")
                })
            
            if is_bullish and not is_bearish:
                bullish_count += 1
            elif is_bearish and not is_bullish:
                bearish_count += 1
            else:
                neutral_count += 1
        
        # 전체적인 시장 분위기 결정
        total_articles = bullish_count + bearish_count + neutral_count
        if total_articles == 0:
            sentiment = "neutral"
        elif bullish_count > bearish_count + (total_articles * 0.2):  # 강한 상승세
            sentiment = "strongly_bullish"
        elif bullish_count > bearish_count:  # 약한 상승세
            sentiment = "mildly_bullish"
        elif bearish_count > bullish_count + (total_articles * 0.2):  # 강한 하락세
            sentiment = "strongly_bearish"
        elif bearish_count > bullish_count:  # 약한 하락세
            sentiment = "mildly_bearish"
        else:  # 중립
            sentiment = "neutral"
        
        return {
            "sentiment": sentiment,
            "bullish_count": bullish_count,
            "bearish_count": bearish_count,
            "neutral_count": neutral_count,
            "important_news": important_news
        }
    
    def extract_price_mentions(self, articles):
        """뉴스 기사 제목에서 비트코인 가격 언급을 추출합니다."""
        # 가격 언급 패턴
        price_pattern = r'\$([0-9,]+)(?:\.[0-9]+)?[kK]?'
        price_mentions = []
        
        for article in articles:
            title = article.get("title", "")
            
            matches = re.findall(price_pattern, title)
            for match in matches:
                # 숫자만 추출하고 천 단위 구분 기호 제거
                price_str = match.replace(',', '')
                try:
                    price = float(price_str)
                    # K가 포함된 경우 (예: $50K) 처리
                    if 'k' in title.lower() or 'K' in title:
                        price *= 1000
                    
                    price_mentions.append({
                        "price": price,
                        "title": title,
                        "source": article.get("source", "Unknown"),
                        "date": article.get("date", "")
                    })
                except ValueError:
                    continue
        
        if price_mentions:
            avg_price = sum(mention["price"] for mention in price_mentions) / len(price_mentions)
            return {
                "mentions": price_mentions,
                "average_mentioned_price": avg_price,
                "mention_count": len(price_mentions)
            }
        else:
            return {
                "mentions": [],
                "average_mentioned_price": 0,
                "mention_count": 0
            }
    
    def get_news_analysis(self, queries=None):
        """암호화폐 관련 뉴스를 가져와 분석합니다."""
        if not self.serpapi_key:
            return None
            
        if queries is None:
            queries = ["bitcoin", "btc price", "crypto market"]
        
        all_articles = []
        
        for query in queries:
            news_data = self.get_crypto_news(query=query, num_results=5)
            if news_data:
                articles = self.extract_article_info(news_data)
                all_articles.extend(articles)
        
        # 중복 제거 (제목 기준)
        unique_articles = []
        seen_titles = set()
        for article in all_articles:
            title = article["title"]
            # 제목이 이미 처리된 적이 없으면 추가
            if title not in seen_titles:
                seen_titles.add(title)
                unique_articles.append(article)
        
        # 뉴스 감정 분석
        sentiment_analysis = self.analyze_news_sentiment(unique_articles)
        
        # 가격 언급 추출
        price_mentions = self.extract_price_mentions(unique_articles)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "articles": unique_articles[:10],  # 상위 10개 기사만 반환
            "sentiment_analysis": sentiment_analysis,
            "price_mentions": price_mentions,
            "article_count": len(unique_articles)
        }
    
    def get_ai_decision(self, data_for_ai):
        """AI 모델에게 분석 데이터를 전달하여 투자 결정을 요청합니다."""
        if not self.openai_client:
            return {
                "decision": "hold",
                "reason": "OpenAI API 키가 설정되지 않아 분석을 진행할 수 없습니다.",
                "confidence_level": 0.0
            }
        
        try:
            response = self.openai_client.chat.completions.create(
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
8. News sentiment and market news (if available)

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
  },
  "news_impact": {
    "assessment": "text assessment of news sentiment",
    "important_headlines": ["list of important headlines"],
    "sentiment_impact": "positive|negative|neutral"
  }
}

Note: If news data is not available, you can omit the news_impact field.
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
            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            print(f"AI 분석 오류: {e}")
            return {
                "decision": "hold",
                "reason": f"AI 분석 중 오류가 발생했습니다: {e}",
                "confidence_level": 0.0
            }
    
    def execute_trade(self, decision):
        """AI의 결정에 따라 거래를 실행합니다."""
        if not self.upbit:
            print("업비트 API 키가 설정되지 않아 거래를 실행할 수 없습니다.")
            return {"status": "error", "message": "API 키 없음"}
        
        # 매수 결정인 경우
        if decision["decision"] == "buy":
            my_krw = self.upbit.get_balance("KRW")
            if my_krw * 0.9995 > 5000:  # 수수료 고려, 최소 거래금액 5000원
                print("\n===== 매수 주문 실행 =====")
                order_result = self.upbit.buy_market_order(self.ticker, my_krw * 0.9995)
                print(f"주문 결과: {order_result}")
                return {"status": "success", "type": "buy", "result": order_result}
            else:
                print("\n===== 매수 주문 실패: KRW 잔액 부족 (5,000원 미만) =====")
                return {"status": "error", "type": "buy", "message": "잔액 부족"}
        
        # 매도 결정인 경우
        elif decision["decision"] == "sell":
            my_btc = self.upbit.get_balance(self.ticker)
            current_price = pyupbit.get_orderbook(ticker=self.ticker)['orderbook_units'][0]["ask_price"]
            if my_btc * current_price > 5000:  # 최소 거래금액 5000원
                print("\n===== 매도 주문 실행 =====")
                order_result = self.upbit.sell_market_order(self.ticker, my_btc)
                print(f"주문 결과: {order_result}")
                return {"status": "success", "type": "sell", "result": order_result}
            else:
                print("\n===== 매도 주문 실패: BTC 가치 부족 (5,000원 미만) =====")
                return {"status": "error", "type": "sell", "message": "보유량 부족"}
        
        # 홀딩 결정인 경우
        elif decision["decision"] == "hold":
            print("\n===== 홀딩 결정 =====")
            print(f"홀딩 이유: {decision['reason']}")
            return {"status": "success", "type": "hold"}
        
        else:
            print(f"\n===== 알 수 없는 결정: {decision['decision']} =====")
            return {"status": "error", "message": "알 수 없는 결정"}
    
    def print_account_status(self, account_status):
        """계정 상태 정보를 출력합니다."""
        if not account_status:
            print("===== 계정 상태 =====")
            print("계정 정보를 가져올 수 없습니다.")
            return
            
        print("===== 계정 상태 =====")
        print(f"KRW 잔액: {account_status['KRW_balance']:,.0f}원")
        print(f"BTC 보유량: {account_status['BTC_balance']:.8f} BTC")
        print(f"BTC 현재가: {account_status['BTC_current_price']:,.0f}원")
        print(f"BTC 보유 가치: {account_status['BTC_value_in_KRW']:,.0f}원")
        print(f"총 자산 가치: {account_status['total_value_in_KRW']:,.0f}원")
        if 'BTC_avg_buy_price' in account_status:
            print(f"BTC 평균 매수가: {account_status['BTC_avg_buy_price']:,.0f}원")
            
            # 수익률 계산 및 출력
            if account_status['BTC_balance'] > 0:
                profit_rate = (account_status['BTC_current_price'] / account_status['BTC_avg_buy_price'] - 1) * 100
                print(f"현재 수익률: {profit_rate:.2f}%")
    
    def print_orderbook_info(self, orderbook):
        """오더북(호가) 정보를 출력합니다."""
        if not orderbook:
            print("\n===== 오더북 정보 =====")
            print("오더북 정보를 가져올 수 없습니다.")
            return
            
        print("\n===== 오더북 정보 =====")
        print(f"매수 호가 총량: {orderbook[0]['total_bid_size']:.4f} BTC")
        print(f"매도 호가 총량: {orderbook[0]['total_ask_size']:.4f} BTC")
        print("최상위 5개 호가:")
        for i, unit in enumerate(orderbook[0]['orderbook_units'][:5]):
            print(f"  {i+1}. 매수: {unit['bid_price']:,.0f}원 ({unit['bid_size']:.4f} BTC) | 매도: {unit['ask_price']:,.0f}원 ({unit['ask_size']:.4f} BTC)")
    
    def print_chart_summary(self, daily_df):
        """차트 데이터 요약 정보를 출력합니다."""
        if daily_df is None or daily_df.empty:
            print("\n===== 차트 데이터 요약 =====")
            print("차트 데이터를 가져올 수 없습니다.")
            return
            
        print("\n===== 30일 일봉 데이터 요약 =====")
        print(f"기간: {daily_df.index[0].strftime('%Y-%m-%d')} ~ {daily_df.index[-1].strftime('%Y-%m-%d')}")
        print(f"시작가: {daily_df['open'].iloc[0]:,.0f}원")
        print(f"현재가: {daily_df['close'].iloc[-1]:,.0f}원")
        print(f"30일 최고가: {daily_df['high'].max():,.0f}원")
        print(f"30일 최저가: {daily_df['low'].min():,.0f}원")
        print(f"30일 변동률: {((daily_df['close'].iloc[-1] / daily_df['open'].iloc[0]) - 1) * 100:.2f}%")
    
    def print_technical_analysis(self, analysis):
        """기술적 분석 지표 정보를 출력합니다."""
        if not analysis:
            print("\n===== 기술적 분석 지표 =====")
            print("기술적 분석 정보를 가져올 수 없습니다.")
            return
            
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
    
    def print_fear_greed_info(self, fear_greed_analysis):
        """공포 탐욕 지수 정보를 출력합니다."""
        if not fear_greed_analysis:
            print("\n===== 공포 탐욕 지수 =====")
            print("공포 탐욕 지수 정보를 가져올 수 없습니다.")
            return
            
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
    
    def print_news_analysis(self, news_analysis):
        """뉴스 분석 결과를 출력합니다."""
        if not news_analysis:
            print("\n===== 뉴스 분석 =====")
            print("뉴스 데이터를 가져올 수 없습니다.")
            return
            
        sentiment = news_analysis["sentiment_analysis"]["sentiment"]
        sentiment_map = {
            "strongly_bullish": "매우 강한 상승세",
            "mildly_bullish": "약한 상승세",
            "neutral": "중립",
            "mildly_bearish": "약한 하락세",
            "strongly_bearish": "매우 강한 하락세"
        }
        
        print("\n===== 암호화폐 뉴스 분석 =====")
        print(f"뉴스 분석 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"수집된 기사: {news_analysis['article_count']}개")
        print(f"\n----- 시장 분위기 -----")
        print(f"전반적 시장 분위기: {sentiment_map.get(sentiment, sentiment)}")
        print(f"상승 관련 기사: {news_analysis['sentiment_analysis']['bullish_count']}개")
        print(f"하락 관련 기사: {news_analysis['sentiment_analysis']['bearish_count']}개")
        print(f"중립 기사: {news_analysis['sentiment_analysis']['neutral_count']}개")
        
        if news_analysis["price_mentions"]["mention_count"] > 0:
            print(f"\n----- 가격 언급 -----")
            print(f"가격 언급 횟수: {news_analysis['price_mentions']['mention_count']}회")
            print(f"평균 언급 가격: ${news_analysis['price_mentions']['average_mentioned_price']:,.2f}")
        
        important_news = news_analysis["sentiment_analysis"]["important_news"]
        if important_news:
            print(f"\n----- 중요 뉴스 -----")
            for i, news in enumerate(important_news[:5], 1):  # 상위 5개만 표시
                print(f"{i}. {news['title']} ({news['source']}) - {news.get('date', '')}")
        
        print(f"\n----- 최근 헤드라인 -----")
        for i, article in enumerate(news_analysis["articles"][:5], 1):  # 상위 5개만 표시
            print(f"{i}. {article['title']} ({article['source']}) - {article.get('date', '')}")
    
    def print_ai_decision(self, result):
        """AI의 투자 결정 내용을 출력합니다."""
        if not result:
            print("\n===== AI 투자 결정 =====")
            print("AI 분석 결과를 가져올 수 없습니다.")
            return
            
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
        
        # 뉴스 영향 정보 출력
        if 'news_impact' in result:
            news_impact = result['news_impact']
            print("\n----- 뉴스 영향 분석 -----")
            if 'assessment' in news_impact:
                print(f"뉴스 평가: {news_impact['assessment']}")
            if 'important_headlines' in news_impact and news_impact['important_headlines']:
                print("\n중요 헤드라인:")
                for i, headline in enumerate(news_impact['important_headlines'][:3], 1):
                    print(f"{i}. {headline}")
            if 'sentiment_impact' in news_impact:
                impact = news_impact['sentiment_impact']
                impact_emoji = "🔴" if impact == "negative" else "🟢" if impact == "positive" else "⚪"
                print(f"뉴스 영향: {impact} {impact_emoji}")
    
    def run_trading_cycle(self):
        """하나의 트레이딩 사이클을 실행합니다."""
        print(f"\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - 자동매매 실행 중...")
        print("=" * 50)
        
        # 1. 계정 상태 정보 가져오기
        account_status = self.get_account_status()
        self.print_account_status(account_status)
        
        # 2. 오더북(호가) 데이터 가져오기
        orderbook = self.get_orderbook_data()
        self.print_orderbook_info(orderbook)
        
        # 3. 차트 데이터 가져오기
        chart_data = self.get_chart_data()
        daily_df = chart_data.get("daily_df") if chart_data else None
        hourly_df = chart_data.get("hourly_df") if chart_data else None
        
        self.print_chart_summary(daily_df)
        
        # 4. 기술적 분석 지표 분석 및 출력
        daily_analysis = self.analyze_technical_indicators(daily_df) if daily_df is not None else None
        hourly_analysis = self.analyze_technical_indicators(hourly_df) if hourly_df is not None else None
        
        self.print_technical_analysis(daily_analysis)
        
        # 5. 공포 탐욕 지수 가져오기
        fear_greed_data = self.get_fear_greed_index(limit=7)
        fear_greed_analysis = self.interpret_fear_greed_index(fear_greed_data) if fear_greed_data else None
        
        self.print_fear_greed_info(fear_greed_analysis)
        
        # 6. 뉴스 데이터 가져오기
        news_queries = ["bitcoin price", "btc news", "crypto market"]
        news_analysis = self.get_news_analysis(queries=news_queries)
        
        self.print_news_analysis(news_analysis)
        
        # 7. AI에게 데이터 제공하고 판단 받기
        data_for_ai = {
            "daily_chart": chart_data.get("daily") if chart_data else [],
            "hourly_chart": chart_data.get("hourly") if chart_data else [],
            "account_status": account_status,
            "orderbook": orderbook[0] if orderbook else {},
            "technical_analysis": {
                "daily": daily_analysis,
                "hourly": hourly_analysis
            },
            "fear_greed_index": fear_greed_analysis
        }
        
        # 뉴스 데이터 추가 (간소화된 형태로)
        if news_analysis:
            simplified_news = {
                "timestamp": news_analysis["timestamp"],
                "articles": [{"title": article["title"], "date": article.get("date", ""), "source": article["source"]} 
                             for article in news_analysis["articles"]],
                "sentiment_analysis": news_analysis["sentiment_analysis"],
                "price_mentions": news_analysis["price_mentions"],
                "article_count": news_analysis["article_count"]
            }
            data_for_ai["news_analysis"] = simplified_news
        
        # AI 투자 결정 요청
        result = self.get_ai_decision(data_for_ai)
        self.print_ai_decision(result)
        
        # 8. 거래 실행
        trade_result = self.execute_trade(result)
        
        print("\n" + "="*50 + "\n")
        return result, trade_result
    
    def run(self):
        """자동 매매 프로그램을 실행합니다."""
        print("비트코인 AI 자동매매 프로그램을 시작합니다.")
        print("뉴스 데이터와 기술적 분석을 활용한 향상된 매매 시스템입니다.")
        print("Ctrl+C를 눌러 프로그램을 종료할 수 있습니다.")
        print("=" * 50)
        
        try:
            while True:
                # 매매 사이클 실행
                self.run_trading_cycle()
                
                # 다음 실행 시간 출력
                next_time = datetime.now() + timedelta(seconds=self.trading_interval)
                print(f"다음 실행 시간: {next_time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # 지정된 간격만큼 대기
                time.sleep(self.trading_interval)
                
        except KeyboardInterrupt:
            print("\n프로그램을 종료합니다.")
        except Exception as e:
            print(f"\n오류 발생: {e}")
            print("프로그램을 종료합니다.")

# 메인 실행 코드
if __name__ == "__main__":
    bot = BitcoinTradingBot()
    bot.run()