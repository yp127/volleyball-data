import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://cafe.daum.net/volleyballsok/Iy5T/1278?svc=cafeapi",
}

url = "https://cafe.daum.net/_c21_/bbs_search_read"
params = {
    "grpid": "1ILxW",
    "fldid": "Iy5T",
    "datanum": "1278",
    "svc": "cafeapi",
}

resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
soup = BeautifulSoup(resp.text, "html.parser")

# 모든 div id/class 출력해서 구조 파악
print("=== 모든 div id ===")
for tag in soup.find_all(id=True):
    print(f"  id={tag.get('id')} / tag={tag.name}")

print("\n=== 텍스트 100자 이상인 div ===")
for div in soup.find_all("div"):
    text = div.get_text(strip=True)
    if len(text) > 100:
        print(f"  class={div.get('class')} id={div.get('id')}")
        print(f"  텍스트: {text[:200]}")
        print()