#!/bin/bash

# EC2 배포 스크립트
# 사용법: ./deploy_ec2.sh [EC2_IP] [KEY_PATH]
# 예시: ./deploy_ec2.sh 3.35.123.456 ~/Downloads/jwcoin-key.pem

EC2_IP=$1
KEY_PATH=$2

if [ -z "$EC2_IP" ] || [ -z "$KEY_PATH" ]; then
    echo "사용법: ./deploy_ec2.sh [EC2_IP] [KEY_PATH]"
    echo "예시: ./deploy_ec2.sh 3.35.123.456 ~/Downloads/jwcoin-key.pem"
    exit 1
fi

echo "=== EC2 배포 시작 ==="
echo "Target: ec2-user@$EC2_IP"

# 1. 필요한 파일 업로드
echo "파일 업로드 중..."
scp -i "$KEY_PATH" \
    autotrade_ec2.py \
    requirements_ec2.txt \
    strategy.txt \
    .env \
    ec2-user@$EC2_IP:~/jwcoin/

# 2. EC2에서 설정 실행
echo "EC2 서버 설정 중..."
ssh -i "$KEY_PATH" ec2-user@$EC2_IP << 'ENDSSH'
cd ~/jwcoin

# 가상환경 생성 (없으면)
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# 의존성 설치
source venv/bin/activate
pip install -r requirements_ec2.txt

# autotrade.py로 이름 변경
cp autotrade_ec2.py autotrade.py

echo "배포 완료!"
echo ""
echo "다음 명령어로 서비스를 시작하세요:"
echo "  sudo systemctl start jwcoin"
echo ""
echo "로그 확인:"
echo "  sudo journalctl -u jwcoin -f"
ENDSSH

echo "=== 배포 완료 ==="