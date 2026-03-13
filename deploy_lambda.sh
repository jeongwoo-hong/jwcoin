#!/bin/bash

# Lambda 배포 스크립트
# 사용법: ./deploy_lambda.sh

set -e

FUNCTION_NAME="jwcoin-trading-bot"
REGION="ap-northeast-2"  # 서울 리전

echo "=== Lambda 배포 시작 ==="

# 1. 패키지 디렉토리 생성
rm -rf lambda_package
mkdir -p lambda_package

# 2. 의존성 설치
echo "의존성 설치 중..."
pip install -r requirements_lambda.txt -t lambda_package/ --platform manylinux2014_x86_64 --only-binary=:all:

# 3. Lambda 함수 코드 복사
cp lambda_function.py lambda_package/

# 4. ZIP 파일 생성
echo "ZIP 파일 생성 중..."
cd lambda_package
zip -r ../lambda_deployment.zip .
cd ..

echo "lambda_deployment.zip 생성 완료!"
echo ""
echo "=== 다음 단계 ==="
echo "1. AWS Console에서 Lambda 함수 생성"
echo "2. lambda_deployment.zip 업로드"
echo "3. 환경 변수 설정"
echo "4. EventBridge 규칙 생성"
echo ""
echo "자세한 설정은 AWS_SETUP.md 참조"