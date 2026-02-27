import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

url = "https://m.cafe.daum.net/volleyballsok/Ifrx"
resp = requests.get(url, headers=HEADERS, timeout=10)
print("상태코드:", resp.status_code)
print("HTML 길이:", len(resp.text))
print()
print("--- HTML 앞부분 ---")
print(resp.text[:1000])