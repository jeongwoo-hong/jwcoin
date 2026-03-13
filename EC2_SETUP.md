# EC2 배포 가이드 (t4g.nano - 월 $3)

## 1. EC2 인스턴스 생성

### AWS Console 접속
1. https://console.aws.amazon.com/ec2 접속
2. 리전: **아시아 태평양 (서울) ap-northeast-2** 선택

### 인스턴스 시작
1. **인스턴스 시작** 클릭
2. 설정:
   - **이름**: `jwcoin-trading-bot`
   - **AMI**: Amazon Linux 2023 (ARM 지원되는 것 확인)
   - **아키텍처**: 64비트 (Arm) ⚠️ t4g는 ARM 아키텍처
   - **인스턴스 유형**: `t4g.nano` (2 vCPU, 0.5GB RAM, ~$2.56/월)
   - **키 페어**: 새로 생성하거나 기존 키 선택
     - 새로 생성 시: `jwcoin-key` → `.pem` 파일 다운로드 후 안전하게 보관
   - **네트워크 설정**:
     - 퍼블릭 IP 자동 할당: 활성화
     - 보안 그룹: 새로 생성
       - SSH (22번 포트): 내 IP만 허용
   - **스토리지**: 8GB gp3 (기본값, 무료 티어)

3. **인스턴스 시작** 클릭

---

## 2. Elastic IP 할당 (고정 IP)

### Elastic IP 생성
1. EC2 콘솔 → **네트워크 및 보안** → **탄력적 IP**
2. **탄력적 IP 주소 할당** 클릭
3. **할당** 클릭

### 인스턴스에 연결
1. 생성된 Elastic IP 선택
2. **작업** → **탄력적 IP 주소 연결**
3. 인스턴스: `jwcoin-trading-bot` 선택
4. **연결** 클릭

### ⚠️ 중요: 이 IP를 Upbit API에 등록
- 할당된 Elastic IP (예: `3.35.xxx.xxx`)를 복사
- Upbit API 관리 페이지에서 이 IP 등록

---

## 3. SSH 접속

### Mac/Linux
```bash
# 키 파일 권한 설정
chmod 400 ~/Downloads/jwcoin-key.pem

# SSH 접속
ssh -i ~/Downloads/jwcoin-key.pem ec2-user@[ELASTIC_IP]
```

### Windows (PowerShell)
```powershell
ssh -i C:\Users\[사용자명]\Downloads\jwcoin-key.pem ec2-user@[ELASTIC_IP]
```

---

## 4. 서버 환경 설정

### 기본 패키지 업데이트
```bash
sudo dnf update -y
```

### Python 3.11 및 pip 설치
```bash
sudo dnf install python3.11 python3.11-pip git -y

# 기본 python으로 설정
sudo alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
sudo alternatives --install /usr/bin/pip3 pip3 /usr/bin/pip3.11 1

# 확인
python3 --version  # Python 3.11.x
pip3 --version
```

### 프로젝트 디렉토리 생성
```bash
mkdir -p ~/jwcoin
cd ~/jwcoin
```

---

## 5. 코드 배포

### 방법 1: Git 사용 (권장)
```bash
# 프라이빗 레포인 경우 토큰 필요
git clone https://github.com/[username]/jwcoin.git ~/jwcoin
cd ~/jwcoin
```

### 방법 2: SCP로 직접 업로드
로컬에서 실행:
```bash
# 필요한 파일만 업로드
scp -i ~/Downloads/jwcoin-key.pem \
    autotrade.py requirements.txt strategy.txt \
    ec2-user@[ELASTIC_IP]:~/jwcoin/
```

### 의존성 설치
```bash
cd ~/jwcoin

# 가상환경 생성 (권장)
python3 -m venv venv
source venv/bin/activate

# 의존성 설치 (Selenium 제외)
pip install python-dotenv openai pyupbit ta youtube-transcript-api pydantic requests schedule
```

---

## 6. 환경변수 설정

### .env 파일 생성
```bash
nano ~/jwcoin/.env
```

내용 입력:
```
UPBIT_ACCESS_KEY=your_upbit_access_key
UPBIT_SECRET_KEY=your_upbit_secret_key
OPENAI_API_KEY=your_openai_key
SERPAPI_API_KEY=your_serpapi_key
ENVIRONMENT=ec2
```

저장: `Ctrl+O` → `Enter` → `Ctrl+X`

### 권한 설정
```bash
chmod 600 ~/jwcoin/.env
```

---

## 7. 코드 수정 (Selenium 제거)

기존 autotrade.py에서 Selenium 관련 코드를 제거해야 합니다.
이미 lambda_function.py에서 Selenium을 제거했으므로, 그 로직을 참고하거나 아래 수정된 버전을 사용하세요.

### 간단한 수정 방법
autotrade.py의 ai_trading() 함수에서:
1. Selenium 관련 import 제거
2. create_driver(), perform_chart_actions(), capture_and_encode_screenshot() 함수 제거
3. chart_image 관련 코드 제거
4. OpenAI API 호출에서 image_url 부분 제거

또는 제가 만들어둔 `autotrade_ec2.py`를 사용하세요 (아래에서 생성).

---

## 8. systemd 서비스 설정 (자동 실행)

### 서비스 파일 생성
```bash
sudo nano /etc/systemd/system/jwcoin.service
```

내용:
```ini
[Unit]
Description=JWCoin Trading Bot
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user/jwcoin
Environment=PATH=/home/ec2-user/jwcoin/venv/bin
ExecStart=/home/ec2-user/jwcoin/venv/bin/python autotrade.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

저장: `Ctrl+O` → `Enter` → `Ctrl+X`

### 서비스 활성화 및 시작
```bash
# 서비스 등록
sudo systemctl daemon-reload

# 부팅 시 자동 시작
sudo systemctl enable jwcoin

# 서비스 시작
sudo systemctl start jwcoin

# 상태 확인
sudo systemctl status jwcoin
```

### 로그 확인
```bash
# 실시간 로그
sudo journalctl -u jwcoin -f

# 최근 100줄
sudo journalctl -u jwcoin -n 100
```

---

## 9. 유용한 명령어

```bash
# 서비스 재시작
sudo systemctl restart jwcoin

# 서비스 중지
sudo systemctl stop jwcoin

# 수동 실행 (테스트용)
cd ~/jwcoin
source venv/bin/activate
python autotrade.py
```

---

## 10. 모니터링 설정 (선택사항)

### CloudWatch Agent 설치
```bash
sudo dnf install amazon-cloudwatch-agent -y
```

### 간단한 헬스체크 스크립트
```bash
nano ~/check_bot.sh
```

```bash
#!/bin/bash
if ! systemctl is-active --quiet jwcoin; then
    echo "Bot is down! Restarting..."
    sudo systemctl restart jwcoin
fi
```

```bash
chmod +x ~/check_bot.sh

# cron에 등록 (5분마다 체크)
crontab -e
# 추가: */5 * * * * /home/ec2-user/check_bot.sh
```

---

## 비용 요약

| 항목 | 월 비용 |
|------|---------|
| EC2 t4g.nano | ~$2.56 |
| EBS 8GB gp3 | ~$0.64 |
| Elastic IP | $0 (인스턴스 연결 시) |
| 데이터 전송 | ~$0 (소량) |
| **총합** | **~$3.20/월** |

---

## 문제 해결

### SSH 접속 안 됨
- 보안 그룹에서 22번 포트 열려있는지 확인
- Elastic IP가 제대로 연결되었는지 확인
- 키 파일 권한이 400인지 확인

### 봇이 실행되지 않음
```bash
# 로그 확인
sudo journalctl -u jwcoin -n 50

# 수동 실행으로 에러 확인
cd ~/jwcoin && source venv/bin/activate && python autotrade.py
```

### 메모리 부족 (t4g.nano는 512MB)
```bash
# 스왑 메모리 추가
sudo dd if=/dev/zero of=/swapfile bs=128M count=8
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 영구 적용
echo '/swapfile swap swap defaults 0 0' | sudo tee -a /etc/fstab
```