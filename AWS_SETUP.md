# AWS Lambda + EventBridge 설정 가이드

## 1. DynamoDB 테이블 생성

```bash
aws dynamodb create-table \
    --table-name bitcoin_trades \
    --attribute-definitions AttributeName=id,AttributeType=S \
    --key-schema AttributeName=id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region ap-northeast-2
```

## 2. IAM 역할 생성

Lambda 함수에 필요한 권한:
- `AWSLambdaBasicExecutionRole` (CloudWatch Logs)
- DynamoDB 접근 권한

### IAM 정책 (inline policy)
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:PutItem",
                "dynamodb:Scan",
                "dynamodb:GetItem"
            ],
            "Resource": "arn:aws:dynamodb:ap-northeast-2:*:table/bitcoin_trades"
        }
    ]
}
```

## 3. Lambda 함수 생성

### AWS Console에서 생성
1. Lambda > 함수 생성
2. 함수 이름: `jwcoin-trading-bot`
3. 런타임: Python 3.11
4. 아키텍처: x86_64
5. 실행 역할: 위에서 생성한 역할 선택

### 설정 변경
- **메모리**: 512 MB (권장)
- **제한 시간**: 5분 (300초)

### 환경 변수 설정
| 변수명 | 값 |
|--------|-----|
| UPBIT_ACCESS_KEY | 업비트 API 액세스 키 |
| UPBIT_SECRET_KEY | 업비트 API 시크릿 키 |
| OPENAI_API_KEY | OpenAI API 키 |
| SERPAPI_API_KEY | SerpAPI 키 (선택사항) |
| DYNAMODB_TABLE | bitcoin_trades |

## 4. 배포 패키지 업로드

```bash
# 배포 스크립트 실행
chmod +x deploy_lambda.sh
./deploy_lambda.sh

# AWS CLI로 업로드 (파일 크기가 10MB 초과시 S3 사용)
aws lambda update-function-code \
    --function-name jwcoin-trading-bot \
    --zip-file fileb://lambda_deployment.zip \
    --region ap-northeast-2
```

### 파일이 너무 큰 경우 (S3 사용)
```bash
# S3 버킷에 업로드
aws s3 cp lambda_deployment.zip s3://your-bucket-name/

# S3에서 Lambda로 배포
aws lambda update-function-code \
    --function-name jwcoin-trading-bot \
    --s3-bucket your-bucket-name \
    --s3-key lambda_deployment.zip \
    --region ap-northeast-2
```

## 5. EventBridge 규칙 생성 (스케줄링)

매일 9시, 15시, 21시 (KST) 실행:

```bash
# 9시 (KST) = 0시 (UTC)
aws events put-rule \
    --name "trading-bot-9am" \
    --schedule-expression "cron(0 0 * * ? *)" \
    --region ap-northeast-2

# 15시 (KST) = 6시 (UTC)
aws events put-rule \
    --name "trading-bot-3pm" \
    --schedule-expression "cron(0 6 * * ? *)" \
    --region ap-northeast-2

# 21시 (KST) = 12시 (UTC)
aws events put-rule \
    --name "trading-bot-9pm" \
    --schedule-expression "cron(0 12 * * ? *)" \
    --region ap-northeast-2
```

### Lambda 함수를 타겟으로 추가
```bash
# 각 규칙에 대해 실행
aws events put-targets \
    --rule "trading-bot-9am" \
    --targets "Id"="1","Arn"="arn:aws:lambda:ap-northeast-2:YOUR_ACCOUNT_ID:function:jwcoin-trading-bot" \
    --region ap-northeast-2
```

### Lambda에 EventBridge 권한 추가
```bash
aws lambda add-permission \
    --function-name jwcoin-trading-bot \
    --statement-id trading-bot-9am \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn arn:aws:events:ap-northeast-2:YOUR_ACCOUNT_ID:rule/trading-bot-9am \
    --region ap-northeast-2
```

## 6. 테스트

```bash
# Lambda 함수 직접 호출
aws lambda invoke \
    --function-name jwcoin-trading-bot \
    --region ap-northeast-2 \
    output.json

# 결과 확인
cat output.json
```

## 7. 모니터링

### CloudWatch Logs 확인
```bash
aws logs tail /aws/lambda/jwcoin-trading-bot --follow --region ap-northeast-2
```

## 예상 비용 (월)

| 서비스 | 예상 비용 |
|--------|----------|
| Lambda | ~$0 (Free Tier: 월 100만 요청, 40만 GB-초) |
| DynamoDB | ~$0 (Free Tier: 25GB 저장, 2억 요청) |
| EventBridge | ~$0 (Free Tier: 스케줄 규칙 무료) |
| **총합** | **거의 $0** |

※ OpenAI API 비용은 별도 (GPT-4: 약 $0.03/실행)