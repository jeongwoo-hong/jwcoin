# import os
# from dotenv import load_dotenv

# load_dotenv()

# # print("Hello Coin World")
# # print(os.getenv("UPBIT_ACCESS_KEY"))

# from selenium import webdriver

# browser = webdriver.Chrome()
# browser.get('http://selenium.dev/')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time
import os
import sys
from datetime import datetime

def capture_upbit_chart():
    # 크롬 드라이버 옵션 설정
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")  # 브라우저를 최대화 상태로 실행
    chrome_options.add_argument("--disable-notifications")  # 알림 비활성화
    chrome_options.add_argument("--no-sandbox")  # 샌드박스 비활성화
    chrome_options.add_argument("--disable-dev-shm-usage")  # 공유 메모리 제한 비활성화
    chrome_options.add_argument("--disable-gpu")  # GPU 하드웨어 가속 비활성화
    
    # 필요에 따라 헤드리스 모드 추가 (화면에 브라우저가 표시되지 않음)
    # chrome_options.add_argument("--headless=new")  # 새로운 헤드리스 모드 사용
    
    # 명시적인 인코딩 설정
    chrome_options.add_argument("--lang=ko_KR.UTF-8")
    
    try:
        # 웹드라이버 초기화
        driver = webdriver.Chrome(options=chrome_options)
    except Exception as e:
        print(f"드라이버 초기화 중 오류 발생: {e}")
        sys.exit(1)
    
    try:
        # Upbit 차트 페이지 접속
        url = "https://upbit.com/full_chart?code=CRIX.UPBIT.KRW-BTC"
        driver.get(url)
        
        print("페이지 로딩 중...")
        
        # 페이지 로드 확인을 위한 명시적 대기
        wait = WebDriverWait(driver, 20)
        # 차트 컨테이너가 로드될 때까지 대기 (페이지의 실제 요소에 맞게 조정 필요)
        try:
            # 일반적인 차트 컨테이너 확인
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
            print("기본 페이지 요소 확인됨")
            
            # 차트가 로드될 시간을 추가로 확보
            time.sleep(15)
        except Exception as wait_error:
            print(f"페이지 로드 대기 중 오류: {wait_error}")
            print("타임아웃되었지만 스크린샷 시도")
        
        # 현재 날짜와 시간으로 파일명 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"upbit_btc_chart_{timestamp}.png"
        
        # 스크린샷 저장 경로 설정
        save_path = os.path.join(os.getcwd(), filename)
        
        print(f"스크린샷 캡처 시도 중: {save_path}")
        
        # 스크린샷 촬영
        result = driver.save_screenshot(save_path)
        
        if result:
            print(f"스크린샷이 성공적으로 저장되었습니다: {save_path}")
        else:
            print("스크린샷 저장에 실패했습니다.")
        
    except Exception as e:
        print(f"에러 발생: {e}")
    
    finally:
        # 브라우저 종료
        driver.quit()

if __name__ == "__main__":
    capture_upbit_chart()