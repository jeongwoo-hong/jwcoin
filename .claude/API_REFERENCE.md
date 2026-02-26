# API 및 외부 서비스 참조

## 1. Upbit API (pyupbit)

### 인증
```python
import pyupbit
upbit = pyupbit.Upbit(access_key, secret_key)
```

### 사용 메서드

| 메서드 | 설명 | 반환값 |
|--------|------|--------|
| `upbit.get_balances()` | 전체 잔고 조회 | List[Dict] |
| `upbit.get_balance("KRW")` | 특정 자산 잔고 | float |
| `upbit.get_balance("KRW-BTC")` | BTC 잔고 | float |
| `upbit.buy_market_order("KRW-BTC", amount)` | 시장가 매수 | Dict |
| `upbit.sell_market_order("KRW-BTC", amount)` | 시장가 매도 | Dict |
| `upbit.get_order("KRW-BTC", state="done")` | 체결 내역 | List[Dict] |

### 비인증 메서드

| 메서드 | 설명 |
|--------|------|
| `pyupbit.get_ohlcv("KRW-BTC", interval="day", count=30)` | OHLCV 데이터 |
| `pyupbit.get_orderbook("KRW-BTC")` | 호가 데이터 |
| `pyupbit.get_current_price("KRW-BTC")` | 현재가 |

### 주의사항
- 최소 주문 금액: 5,000 KRW
- 수수료: 0.05% (매수 시 0.9995 적용)
- API 호출 제한: 초당 10회

---

## 2. OpenAI API

### 초기화
```python
from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
```

### 사용 모델

| 모델 | 용도 |
|------|------|
| `gpt-4.1` | 메인 매매 결정 (이미지 분석 포함) |
| `gpt-4.1-mini` | 반성 일기 생성 |
| `gpt-4o` | MVP 버전 (간단 분석) |

### 응답 포맷 (Structured Output)
```python
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
}
```

### 이미지 입력
```python
{
    "type": "image_url",
    "image_url": {
        "url": f"data:image/png;base64,{chart_image}"
    }
}
```

---

## 3. Fear and Greed Index API

### 엔드포인트
```
GET https://api.alternative.me/fng/
```

### 응답 예시
```json
{
    "data": [{
        "value": "25",
        "value_classification": "Extreme Fear",
        "timestamp": "1234567890",
        "time_until_update": "12345"
    }]
}
```

### 분류
| 값 | 상태 |
|----|------|
| 0-24 | Extreme Fear |
| 25-49 | Fear |
| 50 | Neutral |
| 51-74 | Greed |
| 75-100 | Extreme Greed |

---

## 4. SerpAPI (뉴스 검색)

### 엔드포인트
```
GET https://serpapi.com/search.json
```

### 파라미터
```python
params = {
    "engine": "google_news",
    "q": "btc",
    "api_key": serpapi_key
}
```

### 응답 처리
```python
headlines = []
for item in data.get("news_results", []):
    headlines.append({
        "title": item.get("title", ""),
        "date": item.get("date", "")
    })
return headlines[:5]  # 최신 5개만
```

---

## 5. YouTube Transcript API

### 사용
```python
from youtube_transcript_api import YouTubeTranscriptApi

transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko'])
combined_text = ' '.join(entry['text'] for entry in transcript)
```

### 주의사항
- 자막이 없는 영상은 오류 발생
- 언어 우선순위: 한국어 ('ko')

---

## 6. 기술 지표 라이브러리 (ta)

### 볼린저 밴드
```python
from ta.volatility import BollingerBands

bb = BollingerBands(close=df['close'], window=20, window_dev=2)
df['bb_bbm'] = bb.bollinger_mavg()   # 중간선
df['bb_bbh'] = bb.bollinger_hband()  # 상단선
df['bb_bbl'] = bb.bollinger_lband()  # 하단선
```

### RSI
```python
from ta.momentum import RSIIndicator

df['rsi'] = RSIIndicator(close=df['close'], window=14).rsi()
```

### MACD
```python
from ta.trend import MACD

macd = MACD(close=df['close'])
df['macd'] = macd.macd()
df['macd_signal'] = macd.macd_signal()
df['macd_diff'] = macd.macd_diff()
```

### 이동평균
```python
from ta.trend import SMAIndicator, EMAIndicator

df['sma_20'] = SMAIndicator(close=df['close'], window=20).sma_indicator()
df['ema_12'] = EMAIndicator(close=df['close'], window=12).ema_indicator()
```

---

## 7. Selenium WebDriver

### 설정
```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
```

### Local 환경
```python
from webdriver_manager.chrome import ChromeDriverManager
service = Service(ChromeDriverManager().install())
```

### EC2 환경
```python
service = Service('/usr/bin/chromedriver')
```

### 스크린샷
```python
png = driver.get_screenshot_as_png()
img = Image.open(io.BytesIO(png))
img.thumbnail((2000, 2000))  # OpenAI 제한에 맞춤
buffered = io.BytesIO()
img.save(buffered, format="PNG")
base64_image = base64.b64encode(buffered.getvalue()).decode('utf-8')
```

---

## 8. SQLite 스키마

### trades 테이블 생성
```sql
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    decision TEXT,
    percentage INTEGER,
    reason TEXT,
    btc_balance REAL,
    krw_balance REAL,
    btc_avg_buy_price REAL,
    btc_krw_price REAL,
    reflection TEXT,
    transaction_type TEXT DEFAULT "trade",
    manual_entry INTEGER DEFAULT 0,
    notes TEXT
)
```

### 주요 쿼리
```sql
-- 최근 N일 거래 조회
SELECT * FROM trades
WHERE timestamp > ?
ORDER BY timestamp DESC

-- 거래 유형별 통계
SELECT transaction_type, COUNT(*) as count
FROM trades
GROUP BY transaction_type

-- 큰 KRW 변화 탐지
SELECT timestamp, krw_balance,
       krw_balance - LAG(krw_balance) OVER (ORDER BY timestamp) as krw_change
FROM trades
WHERE ABS(krw_change) > 100000 AND decision NOT IN ('buy', 'sell')
```