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
import time
import os
from datetime import datetime

def capture_upbit_chart():
    # 크롬 드라이버 옵션 설정
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")  # 브라우저를 최대화 상태로 실행
    chrome_options.add_argument("--disable-notifications")  # 알림 비활성화
    
    # 필요에 따라 헤드리스 모드 추가 (화면에 브라우저가 표시되지 않음)
    # chrome_options.add_argument("--headless")
    
    # 드라이버 경로 설정 (chromedriver가 PATH에 있다고 가정)
    # chromedriver_path = "/path/to/chromedriver"  # 필요시 경로 지정
    
    # 웹드라이버 초기화
    # 최신 버전의 Selenium에서는 Service 객체를 생성하여 서비스 경로를 지정할 수 있음
    # service = Service(executable_path=chromedriver_path)
    # driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # 또는 PATH에 chromedriver가 있는 경우 간단히 다음과 같이 사용
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # Upbit 차트 페이지 접속
        url = "https://upbit.com/full_chart?code=CRIX.UPBIT.KRW-BTC"
        driver.get(url)
        
        # 페이지가 완전히 로드될 때까지 기다림 (10초)
        time.sleep(10)  # 차트가 완전히 로드될 때까지 충분한 시간을 줌
        
        # 현재 날짜와 시간으로 파일명 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"upbit_btc_chart_{timestamp}.png"
        
        # 스크린샷 저장 경로 설정
        save_path = os.path.join(os.getcwd(), filename)
        
        # 스크린샷 촬영
        driver.save_screenshot(save_path)
        print(f"스크린샷이 저장되었습니다: {save_path}")
        
    except Exception as e:
        print(f"에러 발생: {e}")
    
    finally:
        # 브라우저 종료
        driver.quit()

if __name__ == "__main__":
    capture_upbit_chart()