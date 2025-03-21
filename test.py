import os
from dotenv import load_dotenv

load_dotenv()

# print("Hello Coin World")
# print(os.getenv("UPBIT_ACCESS_KEY"))

from selenium import webdriver

browser = webdriver.Chrome()
browser.get('http://selenium.dev/')