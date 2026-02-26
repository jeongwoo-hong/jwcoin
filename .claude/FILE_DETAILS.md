# 파일별 상세 분석

## 1. autotrade.py (핵심 자동매매)

**크기**: 558줄 | **역할**: 메인 자동매매 로직

### 주요 클래스/함수

| 함수명 | 설명 |
|--------|------|
| `TradingDecision` | Pydantic 모델 - AI 응답 검증 |
| `init_db()` | SQLite DB 초기화 |
| `log_trade()` | 거래 기록 저장 |
| `get_recent_trades()` | 최근 N일 거래 조회 |
| `calculate_performance()` | 수익률 계산 |
| `generate_reflection()` | AI 반성 일기 생성 |
| `add_indicators()` | 기술 지표 추가 (BB, RSI, MACD, SMA, EMA) |
| `get_fear_and_greed_index()` | 공포탐욕지수 조회 |
| `get_bitcoin_news()` | SerpAPI로 뉴스 조회 |
| `get_combined_transcript()` | 유튜브 자막 추출 |
| `create_driver()` | Selenium ChromeDriver 생성 |
| `perform_chart_actions()` | 차트 조작 (1시간봉, 볼린저밴드) |
| `capture_and_encode_screenshot()` | 차트 스크린샷 → base64 |
| `ai_trading()` | **핵심** - AI 매매 판단 및 실행 |

### 데이터 수집 흐름

```
1. 현재 잔고 조회 (upbit.get_balances)
2. 호가 데이터 조회 (pyupbit.get_orderbook)
3. 일봉/시간봉 OHLCV + 기술지표
4. 공포탐욕지수 (alternative.me API)
5. 뉴스 헤드라인 (SerpAPI)
6. 전략 텍스트 (strategy.txt)
7. 차트 스크린샷 (Selenium)
8. 최근 거래 기록 (SQLite)
9. AI 반성 내용 생성
```

### 스케줄링

```python
schedule.every().day.at("09:00").do(job)
schedule.every().day.at("15:00").do(job)
schedule.every().day.at("21:00").do(job)
```

---

## 2. streamlit_app.py (대시보드)

**크기**: 520줄 | **역할**: 실시간 거래 대시보드

### 주요 기능

1. **현재 자산 현황**: BTC/KRW 잔고, 총 자산
2. **거래 성과 분석**: 실현/미실현 손익, 수수료
3. **차트 시각화**:
   - 거래 타임라인 (매수/매도 시점)
   - 일별 거래량 바 차트
4. **거래 내역 테이블**: 최근 20건 표시
5. **AI 트레이딩 기록**: 로컬 DB 연동

### 데이터 소스

- `업비트 API`: 실시간 거래 내역
- `로컬 DB`: AI 트레이딩 기록
- `통합`: 양쪽 모두

### 캐싱 설정

```python
@st.cache_data(ttl=60)   # 잔고 조회: 1분
@st.cache_data(ttl=300)  # 거래 내역: 5분
```

---

## 3. cli_db_manager.py (CLI 관리 도구)

**크기**: 400줄 | **역할**: EC2에서 DB 관리

### CLI 명령어

| 명령어 | 설명 | 예시 |
|--------|------|------|
| `view` | 거래 내역 조회 | `--limit 20 --type deposit --id 5` |
| `deposit` | 입금 추가 | `deposit 500000 --desc "추가입금"` |
| `withdraw` | 출금 추가 | `withdraw 100000` |
| `delete` | 거래 삭제 | `delete 5 --force` |
| `update` | 유형 수정 | `update 5 trade` |
| `search` | 키워드 검색 | `search "manual"` |
| `summary` | 요약 정보 | - |
| `backup` | DB 백업 | `--path backup.db` |

### 거래 유형

- `trade`: AI 자동 거래
- `deposit`: 입금
- `withdrawal`: 출금
- `fee`: 수수료
- `other`: 기타

---

## 4. manual_deposit_manager.py

**크기**: 335줄 | **역할**: 수동 입출금 관리 (인터랙티브)

### 기능

1. 입금 내역 추가
2. 출금 내역 추가
3. 최근 거래 내역 확인
4. 누락된 입금 추정 (KRW 급증 분석)

### 특징

- 컬럼 타입별 안전한 기본값 처리
- 출금 시 잔액 부족 경고
- 상세 로깅 출력

---

## 5. check_deposit_status.py

**크기**: 143줄 | **역할**: 입금 상태 확인

### 분석 기능

1. 최근 10개 거래의 KRW 변화
2. 500,000원 관련 변화 탐지
3. Manual deposit 항목 검색
4. 데이터베이스 건강성 검사 (중복 타임스탬프 등)

---

## 6. database_deposit_checker.py

**크기**: 177줄 | **역할**: DB 구조 및 입출금 분석

### 분석 항목

1. 모든 테이블 목록
2. trades 테이블 구조
3. 입출금 관련 컬럼 존재 여부
4. KRW 잔액 변화 패턴
5. 큰 KRW 변화 감지 (입출금 추정)

---

## 7. delete_manual_deposit.py

**크기**: 161줄 | **역할**: 수동 입금 삭제

### 삭제 대상 조건

- `reason LIKE '%Manual deposit%'`
- `reason LIKE '%수동%'`
- `reason LIKE '%누락%'`
- `reason LIKE '%복구%'`
- KRW 변화가 정확히 500,000원

---

## 8. mvp.py (최소 기능 버전)

**크기**: 93줄 | **역할**: 기본 자동매매 프로토타입

### 특징

- 단순 구조: 30일 일봉 → GPT-4o → 매매
- 10초 간격 무한 루프
- 기술 지표/차트 캡처 없음
- 로깅/DB 저장 없음

---

## 9. test.py (유틸리티 테스트)

**크기**: 11줄 | **역할**: 유튜브 자막 추출 테스트

```python
from youtube_transcript_api import YouTubeTranscriptApi
# 지정된 video_id의 자막을 하나의 문자열로 결합
```

---

## 10. strategy.txt (트레이딩 전략)

**역할**: 원요띠 투자 전략 참조 텍스트

AI에게 제공되는 트레이딩 가이드라인으로, 원요띠의 성공 비법을 담고 있음:
- 차트 중심 매매
- 시장 심리 분석
- 리스크 관리 원칙
- 복리 투자 전략