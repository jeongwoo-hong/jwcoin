# JWCoin 프로젝트 - 월별 비용 분석

## 요약

| 카테고리 | 월 예상 비용 | 상태 |
|---------|-------------|------|
| AI API (Claude) | ~$2.10 | 활성 |
| AWS 서비스 | ~$0.50 | 활성 (Free Tier) |
| 데이터베이스 (Supabase) | $0 ~ $25 | 활성 |
| 거래소 API | 수수료만 | 활성 |
| 데이터 수집 API | $0 ~ $50 | 활성 |
| 호스팅 (선택) | $0 ~ $10 | 선택사항 |
| **총 예상 비용** | **~$3 ~ $90/월** | - |

---

## 1. AI API 비용

### Claude (Anthropic) API - 주력 사용

| 모델 | 용도 | 파일 | 빈도 | 예상 비용/월 |
|------|------|------|------|-------------|
| claude-sonnet-4-5 | 정기 분석 | `autotrade_ec2.py` | 6회/일 | ~$1.00 |
| claude-sonnet-4-5 | 미국주식 분석 | `us_stock/analysis/ai_analyzer.py` | 변동 | ~$0.50 |
| claude-haiku-4-5 | 긴급 분석 | `autotrade_ec2.py` | 변동 | ~$0.20 |
| claude-haiku-4-5 | 반성 생성 | `core/ai_analyzer.py` | 6회/일 | ~$0.30 |
| claude-haiku-4-5 | 손익 분석 | `core/ai_analyzer.py` | 변동 | ~$0.10 |
| **합계** | | | | **~$2.10/월** |

**토큰 단가:**
- claude-sonnet: $3/1M 입력, $15/1M 출력
- claude-haiku: $0.80/1M 입력, $4/1M 출력

### OpenAI API - 레거시 (주석 처리됨)

현재 `lambda_function.py`에서만 사용 중. 대부분 Claude로 마이그레이션 완료.

---

## 2. AWS 서비스 비용

| 서비스 | 용도 | 월 비용 | 비고 |
|--------|------|---------|------|
| Lambda | 자동 매매 함수 | $0 | Free Tier (100만 요청/월) |
| DynamoDB | 거래 기록 저장 | $0 | Free Tier (25GB) |
| EventBridge | 스케줄러 (9시/15시/21시) | $0 | 스케줄 규칙 무료 |
| CloudWatch Logs | 로그 저장 | ~$0.50 | Free Tier 초과 시 |
| **합계** | | **~$0.50/월** | |

### EC2 (선택사항 - 24/7 실행 시)

| 항목 | 사양 | 월 비용 |
|------|------|---------|
| EC2 인스턴스 | t4g.nano | ~$2.56 |
| EBS 스토리지 | 8GB gp3 | ~$0.64 |
| Elastic IP | - | $0 |
| **합계** | | **~$3.20/월** |

---

## 3. 데이터베이스 비용

### Supabase (PostgreSQL)

| 플랜 | 월 비용 | 용량 | 현재 사용 |
|------|---------|------|----------|
| Free | $0 | 500MB, 1 프로젝트 | O |
| Pro | $25 | 8GB, 무제한 | - |

**저장 테이블:**
- `trades` - 암호화폐 거래 기록
- `expenses` - API 비용 추적
- `us_stock_trades` - 미국 주식 거래 기록

---

## 4. 거래소 API 비용

### Upbit (암호화폐)

| 항목 | 비용 |
|------|------|
| API 사용료 | 무료 |
| 거래 수수료 | 0.1% (매수/매도 각각) |

### 한국투자증권 KIS (미국 주식)

| 항목 | 비용 |
|------|------|
| API 사용료 | 무료 |
| 거래 수수료 | 증권사 수수료 적용 |

---

## 5. 데이터 수집 API 비용

| 서비스 | 용도 | 월 비용 | 비고 |
|--------|------|---------|------|
| yfinance | 주가/펀더멘털 데이터 | 무료 | 오픈소스 |
| Finnhub | 뉴스/애널리스트 평가 | 무료 | Free Plan (100회/분) |
| SerpAPI | Google 뉴스 검색 | $0~$50 | 100회/월 무료 |
| deep_translator | 번역 | 무료 | Google 웹 스크래핑 |

---

## 6. 호스팅 비용 (선택사항)

### Railway.app (Streamlit 대시보드)

| 플랜 | 월 비용 |
|------|---------|
| Starter | $0 (500시간/월) |
| Developer | $5~ |

---

## 7. 시나리오별 총 비용

### 최소 비용 (Free Tier 최대 활용)

| 항목 | 비용 |
|------|------|
| Claude API | ~$2.10 |
| AWS (Free Tier) | ~$0.50 |
| Supabase Free | $0 |
| 데이터 API | $0 |
| **합계** | **~$2.60/월** |

### 일반적인 사용

| 항목 | 비용 |
|------|------|
| Claude API | ~$2.10 |
| AWS (Free Tier) | ~$0.50 |
| Supabase Free | $0 |
| SerpAPI (초과 시) | ~$50 |
| **합계** | **~$52.60/월** |

### 프로덕션 환경 (24/7 EC2)

| 항목 | 비용 |
|------|------|
| Claude API | ~$5.00 (사용량 증가) |
| AWS EC2 | ~$3.20 |
| AWS 기타 | ~$0.50 |
| Supabase Pro | $25 |
| SerpAPI | ~$50 |
| **합계** | **~$83.70/월** |

---

## 8. 비용 최적화 팁

1. **Claude 모델 선택**
   - 단순 분석: `claude-haiku` 사용 (sonnet 대비 75% 저렴)
   - 중요 결정: `claude-sonnet` 사용

2. **AWS Free Tier 유지**
   - Lambda: 월 100만 요청 이내 유지
   - DynamoDB: 25GB 이내 유지

3. **SerpAPI 대안**
   - 무료 뉴스 API 검토 (NewsAPI 등)
   - 뉴스 호출 빈도 최적화

4. **EC2 대신 Lambda 활용**
   - 4시간마다 실행 시 Lambda가 더 경제적

---

## 9. 환경 변수 (API 키)

```bash
# AI API
ANTHROPIC_API_KEY=...

# AWS
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...

# 데이터베이스
SUPABASE_URL=...
SUPABASE_KEY=...

# 거래소
UPBIT_ACCESS_KEY=...
UPBIT_SECRET_KEY=...
KIS_APP_KEY=...
KIS_APP_SECRET=...
KIS_ACCOUNT_NO=...

# 데이터 수집
SERPAPI_API_KEY=...
FINNHUB_API_KEY=...
```

---

## 10. 비용 모니터링

프로젝트 내 비용 추적 기능:
- `core/ai_analyzer.py`: Claude API 토큰 사용량 로깅
- `config/database.py`: Supabase `expenses` 테이블에 비용 기록
- 환율: 1 USD = 1,450 KRW 기준

---

*마지막 업데이트: 2026-06-04*