# import os
# from dotenv import load_dotenv

# load_dotenv()

# # print("Hello Coin World")
# # print(os.getenv("UPBIT_ACCESS_KEY"))

# from selenium import webdriver

# browser = webdriver.Chrome()
# browser.get('http://selenium.dev/')

# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.chrome.options import Options
# from webdriver_manager.chrome import ChromeDriverManager
# import time
# import logging

# # 로깅 설정
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# def setup_chrome_options():
#     chrome_options = Options()
#     chrome_options.add_argument("--start-maximized")  # 브라우저를 최대화하여 시작
#     return chrome_options

# def create_driver():
#     logger.info("ChromeDriver 설정 중...")
#     service = Service(ChromeDriverManager().install())
#     driver = webdriver.Chrome(service=service, options=setup_chrome_options())
#     return driver

# def capture_full_page_screenshot(driver, url, filename):
#     logger.info(f"{url} 로딩 중...")
#     driver.get(url)
    
#     # 페이지 로딩을 위한 대기 시간
#     logger.info("페이지 로딩 대기 중...")
#     time.sleep(10)  # 페이지 로딩을 위해 10초 대기
    
#     logger.info("전체 페이지 스크린샷 촬영 중...")
#     driver.save_screenshot(filename)
#     logger.info(f"스크린샷이 성공적으로 저장되었습니다: {filename}")

# def main():
#     driver = None
#     try:
#         driver = create_driver()
#         capture_full_page_screenshot(
#             driver, 
#             "https://upbit.com/full_chart?code=CRIX.UPBIT.KRW-BTC",
#             "upbit_btc_full_chart.png"
#         )
#     except Exception as e:
#         logger.error(f"오류 발생: {e}")
#     finally:
#         if driver:
#             driver.quit()

# if __name__ == "__main__":
#     main()

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import logging
import os
from datetime import datetime
from PIL import Image
import io
import base64

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_chrome_options():
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")  # 브라우저를 최대화하여 시작
    chrome_options.add_argument("--disable-dev-shm-usage")  # /dev/shm 파티션 사용 비활성화
    chrome_options.add_argument("--no-sandbox")  # 샌드박스 비활성화
    chrome_options.add_argument("--disable-gpu")  # GPU 가속 비활성화
    chrome_options.add_argument("--lang=ko_KR.UTF-8")  # 언어 및 인코딩 설정
    
    # 옵션: 헤드리스 모드 (필요시 주석 해제)
    # chrome_options.add_argument("--headless=new")  # 새로운 헤드리스 모드
    
    return chrome_options

def create_driver():
    logger.info("ChromeDriver 설정 중...")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=setup_chrome_options())
    return driver

def get_screenshot_with_js(driver, filename):
    """
    JavaScript를 사용하여 스크린샷을 캡처합니다.
    이 방법은 일반적인 save_screenshot() 메서드보다 더 안정적일 수 있습니다.
    """
    logger.info("JavaScript를 사용하여 스크린샷 캡처 중...")
    
    # 전체 페이지 캡처를 위한 JavaScript 실행
    try:
        # Canvas 기반 스크린샷 캡처
        screenshot_base64 = driver.execute_script("""
            // 페이지 전체 크기에 맞게 캔버스 생성
            var canvas = document.createElement('canvas');
            var context = canvas.getContext('2d');
            var scrollWidth = document.documentElement.scrollWidth;
            var scrollHeight = document.documentElement.scrollHeight;
            
            canvas.width = scrollWidth;
            canvas.height = scrollHeight;
            
            // 문서의 현재 내용으로 캔버스 채우기
            context.drawWindow(window, 0, 0, scrollWidth, scrollHeight, "rgb(255,255,255)");
            
            // 캔버스 이미지 반환
            return canvas.toDataURL('image/png');
        """)
        
        # Base64 이미지 데이터 처리
        if screenshot_base64.startswith('data:image/png;base64,'):
            screenshot_base64 = screenshot_base64.split(',')[1]
        
        # Base64를 이미지로 디코딩
        screenshot_data = base64.b64decode(screenshot_base64)
        image = Image.open(io.BytesIO(screenshot_data))
        image.save(filename)
        logger.info(f"JavaScript 방식으로 스크린샷 저장 성공: {filename}")
        return True
    except Exception as e:
        logger.error(f"JavaScript 스크린샷 방식 실패: {e}")
        return False

def capture_full_page_screenshot(driver, url, filename):
    logger.info(f"{url} 로딩 중...")
    driver.get(url)
    
    # 페이지 로딩을 위한 대기 시간
    logger.info("페이지 로딩 대기 중...")
    time.sleep(15)  # 차트 로딩을 위해 충분한 시간 대기
    
    # 방법 1: 일반 Selenium 스크린샷 메서드 시도
    try:
        logger.info("방법 1: Selenium 기본 스크린샷 메서드 시도 중...")
        success = driver.save_screenshot(filename)
        if success:
            logger.info(f"방법 1 성공: 스크린샷이 저장되었습니다: {filename}")
            return
        else:
            logger.warning("방법 1 실패: 스크린샷이 저장되지 않았습니다.")
    except Exception as e:
        logger.error(f"방법 1 오류: {e}")
    
    # 방법 2: JavaScript 방식 시도
    try:
        logger.info("방법 2: JavaScript 방식 스크린샷 시도 중...")
        if get_screenshot_with_js(driver, filename):
            return
    except Exception as e:
        logger.error(f"방법 2 오류: {e}")
    
    # 방법 3: get_screenshot_as_* 메서드 시도
    try:
        logger.info("방법 3: get_screenshot_as_png 메서드 시도 중...")
        screenshot_png = driver.get_screenshot_as_png()
        with open(filename, 'wb') as f:
            f.write(screenshot_png)
        logger.info(f"방법 3 성공: 스크린샷이 저장되었습니다: {filename}")
        return
    except Exception as e:
        logger.error(f"방법 3 오류: {e}")
    
    # 방법 4: get_screenshot_as_base64 시도
    try:
        logger.info("방법 4: get_screenshot_as_base64 메서드 시도 중...")
        screenshot_base64 = driver.get_screenshot_as_base64()
        screenshot_data = base64.b64decode(screenshot_base64)
        with open(filename, 'wb') as f:
            f.write(screenshot_data)
        logger.info(f"방법 4 성공: 스크린샷이 저장되었습니다: {filename}")
        return
    except Exception as e:
        logger.error(f"방법 4 오류: {e}")
    
    logger.error("모든 스크린샷 방법이 실패했습니다.")

def main():
    driver = None
    try:
        driver = create_driver()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"upbit_btc_chart_{timestamp}.png"
        
        capture_full_page_screenshot(
            driver, 
            "https://upbit.com/full_chart?code=CRIX.UPBIT.KRW-BTC",
            filename
        )
    except Exception as e:
        logger.error(f"오류 발생: {e}")
    finally:
        if driver:
            driver.quit()
            logger.info("드라이버가 종료되었습니다.")

if __name__ == "__main__":
    main()