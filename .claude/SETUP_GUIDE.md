# 설치 및 실행 가이드

## 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### requirements.txt 내용
```
python-dotenv      # 환경변수 관리
openai             # OpenAI API
pyupbit            # 업비트 API
ta                 # 기술 지표 계산
selenium           # 웹 자동화
webdriver-manager  # ChromeDriver 자동 관리
pillow             # 이미지 처리
youtube-transcript-api  # 유튜브 자막
streamlit          # 대시보드
plotly             # 차트 시각화
schedule           # 스케줄링
googletrans==4.0.0-rc1  # 번역 (선택)
```

### CLI DB 관리자 추가 의존성
```bash
pip install tabulate pandas
```

## 2. 환경 변수 설정

`.env` 파일 생성:

```bash
# 업비트 API 키 (https://upbit.com/mypage/open_api_management)
UPBIT_ACCESS_KEY=your_access_key_here
UPBIT_SECRET_KEY=your_secret_key_here

# OpenAI API 키 (https://platform.openai.com/api-keys)
OPENAI_API_KEY=your_openai_api_key_here

# SerpAPI 키 (https://serpapi.com/manage-api-key) - 뉴스 검색용
SERPAPI_API_KEY=your_serpapi_key_here

# 실행 환경
ENVIRONMENT=local  # 또는 ec2
```

## 3. ChromeDriver 설정

### Local 환경 (macOS/Windows)
```python
# webdriver-manager가 자동으로 처리
# 별도 설정 불필요
```

### EC2 환경 (Ubuntu)
```bash
# Chrome 설치
sudo apt update
sudo apt install -y google-chrome-stable

# ChromeDriver 설치
sudo apt install -y chromium-chromedriver

# 또는 수동 설치
wget https://chromedriver.storage.googleapis.com/LATEST_RELEASE
VERSION=$(cat LATEST_RELEASE)
wget https://chromedriver.storage.googleapis.com/${VERSION}/chromedriver_linux64.zip
unzip chromedriver_linux64.zip
sudo mv chromedriver /usr/bin/
sudo chmod +x /usr/bin/chromedriver
```

## 4. 실행 방법

### 자동매매 실행
```bash
# 포그라운드 실행
python autotrade.py

# 백그라운드 실행 (EC2)
nohup python autotrade.py > autotrade.log 2>&1 &

# 또는 screen 사용
screen -S autotrade
python autotrade.py
# Ctrl+A, D로 분리
```

### 대시보드 실행
```bash
streamlit run streamlit_app.py

# 외부 접근 허용 (EC2)
streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8501
```

### DB 관리 CLI
```bash
# 거래 내역 조회
python cli_db_manager.py view --limit 20

# 특정 ID 상세 조회
python cli_db_manager.py view --id 5

# 유형별 필터링
python cli_db_manager.py view --type deposit

# 입금 추가
python cli_db_manager.py deposit 500000 --desc "추가 입금"

# 출금 추가
python cli_db_manager.py withdraw 100000 --desc "출금"

# 거래 삭제
python cli_db_manager.py delete 5 --force

# 요약 보기
python cli_db_manager.py summary

# 키워드 검색
python cli_db_manager.py search "manual"

# 백업
python cli_db_manager.py backup --path backup_20250226.db
```

## 5. EC2 배포 가이드

### 인스턴스 설정
- OS: Ubuntu 22.04 LTS
- 인스턴스 타입: t3.small 이상 (Chrome 실행을 위해)
- 보안 그룹: 8501 포트 오픈 (Streamlit)

### 배포 스크립트
```bash
#!/bin/bash

# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# Python 설치
sudo apt install -y python3 python3-pip python3-venv

# Chrome 설치
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
sudo apt update
sudo apt install -y google-chrome-stable

# ChromeDriver 설치
sudo apt install -y chromium-chromedriver

# 가상환경 생성
python3 -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
echo "ENVIRONMENT=ec2" >> .env
```

### systemd 서비스 등록

`/etc/systemd/system/autotrade.service`:
```ini
[Unit]
Description=Bitcoin Auto Trading Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/jwcoin
Environment=PATH=/home/ubuntu/jwcoin/venv/bin
ExecStart=/home/ubuntu/jwcoin/venv/bin/python autotrade.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable autotrade
sudo systemctl start autotrade
sudo systemctl status autotrade
```

## 6. 로그 확인

```bash
# autotrade 로그 (nohup 사용 시)
tail -f autotrade.log

# systemd 로그
sudo journalctl -u autotrade -f

# Streamlit 로그
tail -f ~/.streamlit/logs/
```

## 7. 문제 해결

### Chrome/Selenium 오류
```bash
# Chrome 버전 확인
google-chrome --version

# ChromeDriver 버전 확인
chromedriver --version

# 메모리 부족 시
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### DB 오류
```bash
# DB 파일 권한 확인
ls -la bitcoin_trades.db

# DB 백업 후 복구
cp bitcoin_trades.db bitcoin_trades_backup.db
python cli_db_manager.py backup
```

### API 오류
```bash
# 환경 변수 확인
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('UPBIT_ACCESS_KEY')[:10])"

# API 연결 테스트
python -c "import pyupbit; print(pyupbit.get_current_price('KRW-BTC'))"
```