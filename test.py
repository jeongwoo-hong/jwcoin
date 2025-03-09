import os
from dotenv import load_dotenv

load_dotenv()

print("Hello Coin World")
print(os.getenv("UPBIT_ACCESS_KEY"))