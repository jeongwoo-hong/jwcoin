# JWCoin 서비스 종료 가이드

## 1. AWS 서비스 종료

### 1.1 EventBridge 규칙 삭제 (스케줄러 중지)
```bash
# AWS CLI로 삭제
aws events delete-rule --name trading-bot-9am --region ap-northeast-2
aws events delete-rule --name trading-bot-3pm --region ap-northeast-2
aws events delete-rule --name trading-bot-9pm --region ap-northeast-2
```

또는 AWS 콘솔에서:
1. https://ap-northeast-2.console.aws.amazon.com/events 접속
2. Rules → 각 규칙 선택 → Delete

### 1.2 Lambda 함수 삭제
```bash
aws lambda delete-function --function-name jwcoin-trading-bot --region ap-northeast-2
```

또는 AWS 콘솔에서:
1. https://ap-northeast-2.console.aws.amazon.com/lambda 접속
2. Functions → jwcoin-trading-bot → Actions → Delete

### 1.3 DynamoDB 테이블 삭제
```bash
aws dynamodb delete-table --table-name bitcoin_trades --region ap-northeast-2
```

또는 AWS 콘솔에서:
1. https://ap-northeast-2.console.aws.amazon.com/dynamodb 접속
2. Tables → bitcoin_trades → Delete

### 1.4 CloudWatch Logs 삭제
```bash
aws logs delete-log-group --log-group-name /aws/lambda/jwcoin-trading-bot --region ap-northeast-2
```

### 1.5 EC2 인스턴스 종료 (있는 경우)
```bash
# 인스턴스 ID 확인 후
aws ec2 terminate-instances --instance-ids <INSTANCE_ID> --region ap-northeast-2
```

---

## 2. Supabase 종료

1. https://supabase.com/dashboard 접속
2. 프로젝트 선택
3. Settings → General → Delete project

또는 데이터만 삭제:
```sql
DROP TABLE IF EXISTS trades;
DROP TABLE IF EXISTS expenses;
DROP TABLE IF EXISTS us_stock_trades;
```

---

## 3. API 키 비활성화/삭제

### Claude (Anthropic)
1. https://console.anthropic.com 접속
2. API Keys → 해당 키 삭제

### OpenAI (사용 중인 경우)
1. https://platform.openai.com/api-keys 접속
2. 해당 키 삭제

### SerpAPI
1. https://serpapi.com/manage-api-key 접속
2. API Key 삭제 또는 계정 비활성화

### Finnhub
1. https://finnhub.io/dashboard 접속
2. API Key 삭제

---

## 4. 거래소 API 키 비활성화

### Upbit
1. https://upbit.com/mypage/open_api_management 접속
2. Open API 관리 → 해당 키 삭제

### 한국투자증권 (KIS)
1. https://apiportal.koreainvestment.com 접속
2. 마이페이지 → API 키 관리 → 삭제

---

## 5. Railway 종료 (사용 중인 경우)

1. https://railway.app/dashboard 접속
2. 프로젝트 선택 → Settings → Delete Project

---

## 6. 로컬 환경 정리

### .env 파일 삭제 또는 키 제거
```bash
rm /Users/jeongwoo.hong/Desktop/jwcoin/.env
```

### 프로젝트 폴더 삭제 (선택)
```bash
rm -rf /Users/jeongwoo.hong/Desktop/jwcoin
```

---

## 체크리스트

- [ ] EventBridge 규칙 삭제
- [ ] Lambda 함수 삭제
- [ ] DynamoDB 테이블 삭제
- [ ] CloudWatch Logs 삭제
- [ ] EC2 인스턴스 종료
- [ ] Supabase 프로젝트 삭제
- [ ] Anthropic API 키 삭제
- [ ] OpenAI API 키 삭제
- [ ] SerpAPI 키 삭제
- [ ] Upbit API 키 삭제
- [ ] KIS API 키 삭제
- [ ] Railway 프로젝트 삭제
- [ ] 로컬 .env 파일 삭제

---

*모든 항목 완료 후 월별 지출: $0*