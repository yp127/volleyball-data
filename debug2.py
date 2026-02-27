# debug2.py
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

url = "https://cafe.daum.net/_c21_/bbs_search_read"
params = {"grpid": "1ILxW", "fldid": "Iy5T", "datanum": "1279", "svc": "cafeapi"}
resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
soup = BeautifulSoup(resp.text, "html.parser")

# 텍스트 100자 이상인 모든 태그 출력
print("=== 텍스트 100자 이상인 태그 ===")
for tag in soup.find_all(True):
    text = tag.get_text(strip=True)
    if 100 < len(text) < 500:
        print(f"tag={tag.name} class={tag.get('class')} id={tag.get('id')}")
        print(f"  → {text[:150]}")
        print()