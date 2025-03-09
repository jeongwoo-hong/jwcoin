import os
from dotenv import load_dotenv


load_dotenv()

# 업비트 차트 데이터 가져오기 (30일 일봉)
import pyupbit

df = pyupbit.get_ohlcv("KRW-BTC", count=30, interval="day")
# print(df.tail())
# print(df.to_json())

# AI에게 데이터 제공하고 판단 받기

from openai import OpenAI
client = OpenAI()

response = client.chat.completions.create(
  model="gpt-4o",
  messages=[
    {
      "role": "system",
      "content": [
        {
          "type": "text",
          "text": "you are an expert in Bitcoin investing. Tell me whether to buy, sell, or hold at the moment based on the chart data provided. response in json format.\n\nResponse Example : \n{\"decision\":\"buy\", \"reason\":\"some technical reason\"}\n{\"decision\":\"sell\", \"reason\":\"some technical reason\"}\n{\"decision\":\"hold\", \"reason\":\"some technical reason\"}\n"
        }
      ]
    },
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": df.to_json()
        }
      ]
    }
  ],
  response_format={
    "type": "json_object" 
  }
#   ,temperature=1,
#   max_completion_tokens=2048,
#   top_p=1,
#   frequency_penalty=0,
#   presence_penalty=0
)
print(response.choices[0].message.content)