# JWCoin - AI 비트코인 자동매매 시스템

## 프로젝트 개요

업비트 API와 OpenAI GPT를 활용한 비트코인 자동매매 시스템입니다. '원요띠' 투자자의 트레이딩 전략을 기반으로 AI가 매매 결정을 내립니다.

## 기술 스택

| 구분 | 기술 |
|------|------|
| 언어 | Python 3.x |
| 거래소 API | pyupbit (업비트) |
| AI | OpenAI GPT-4.1, GPT-4.1-mini |
| 차트 캡처 | Selenium + ChromeDriver |
| 데이터베이스 | SQLite |
| 대시보드 | Streamlit + Plotly |
| 기술 지표 | ta (Technical Analysis) |
| 스케줄링 | schedule |

## 핵심 기능

1. **AI 기반 매매 결정**: 차트 데이터, 기술 지표, 뉴스, 공포탐욕지수를 분석하여 buy/sell/hold 결정
2. **자동 실행**: 매일 09:00, 15:00, 21:00에 자동 트레이딩
3. **거래 기록 저장**: SQLite DB에 모든 거래 내역 저장
4. **실시간 대시보드**: Streamlit으로 자산 현황 및 거래 분석 시각화
5. **반성 기능**: 최근 7일 거래를 분석하여 AI가 개선점 제안

## 파일 구조

```
jwcoin/
├── autotrade.py           # 핵심 자동매매 로직
├── streamlit_app.py       # 웹 대시보드
├── cli_db_manager.py      # CLI DB 관리 도구
├── manual_deposit_manager.py  # 수동 입출금 관리
├── check_deposit_status.py    # 입금 상태 확인
├── database_deposit_checker.py # DB 구조 분석
├── delete_manual_deposit.py   # 수동 입금 삭제
├── mvp.py                 # 기본 MVP 버전
├── test.py                # 유튜브 자막 테스트
├── strategy.txt           # 원요띠 트레이딩 전략
├── requirements.txt       # 의존성 목록
├── bitcoin_trades.db      # 거래 내역 DB
└── .claude/               # 프로젝트 문서
```

## 환경 변수 (.env)

```
UPBIT_ACCESS_KEY=your_access_key
UPBIT_SECRET_KEY=your_secret_key
OPENAI_API_KEY=your_openai_key
SERPAPI_API_KEY=your_serpapi_key
ENVIRONMENT=local  # or ec2
```

## 실행 방법

### 자동매매 실행
```bash
python autotrade.py
```

### 대시보드 실행
```bash
streamlit run streamlit_app.py
```

### DB 관리 CLI
```bash
python cli_db_manager.py view --limit 20
python cli_db_manager.py deposit 500000 --desc "추가 입금"
python cli_db_manager.py summary
```

## 트레이딩 전략 (원요띠 기법)

1. **차트 중심 매매**: 호재/악재보다 차트 패턴 우선
2. **시장 심리 분석**: 캔들 패턴과 이평선으로 추세 파악
3. **리스크 관리**:
   - 투자금의 20-30%만 투자
   - 낮은 레버리지 사용
   - 분할 매수/매도
4. **복리 투자**: 하루 1-2% 꾸준한 수익 추구
5. **유연한 손절**: 시나리오 이탈 시 손절

## 데이터베이스 스키마

### trades 테이블
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| id | INTEGER | PK, 자동증가 |
| timestamp | TEXT | 거래 시간 |
| decision | TEXT | buy/sell/hold |
| percentage | INTEGER | 거래 비율 (1-100) |
| reason | TEXT | AI 판단 이유 |
| btc_balance | REAL | BTC 잔액 |
| krw_balance | REAL | KRW 잔액 |
| btc_avg_buy_price | REAL | 평균 매수가 |
| btc_krw_price | REAL | 현재 BTC 가격 |
| reflection | TEXT | AI 반성 내용 |
| transaction_type | TEXT | trade/deposit/withdrawal |
| manual_entry | INTEGER | 수동 입력 여부 |
| notes | TEXT | 메모 |