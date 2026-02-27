# debug.py - 빈 본문 원인 확인
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

# 빈 본문인 게시글들 테스트
TEST_CASES = [
    ("Iy5T", 1285, "제1회 창원 상남으뜸 플란트 치과배"),   # 첨부파일만
    ("Iy5T", 1279, "제2회 완도풀 힐링"),                   # 본문 있어보임
    ("Iy5T", 1274, "서울시민리그"),                         # 본문 있어보임
    ("Iy5T", 1273, "부여굿뜨래배"),                         # 본문 있어보임
]

for fldid, datanum, label in TEST_CASES:
    url = "https://cafe.daum.net/_c21_/bbs_search_read"
    params = {"grpid": "1ILxW", "fldid": fldid, "datanum": str(datanum), "svc": "cafeapi"}
    resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
    soup = BeautifulSoup(resp.text, "html.parser")

    print(f"\n{'='*50}")
    print(f"[{datanum}] {label}")
    print(f"HTML 길이: {len(resp.text)}")

    # 어떤 셀렉터에 텍스트가 있는지 확인
    for sel in ["div.article_view", "div#article", "div.cont_view", 
                "div.tview", "div.table-wrap", "div#articleContent",
                "div.view_inbox", "div.inbox"]:
        el = soup.select_one(sel)
        if el:
            text = el.get_text(strip=True)
            print(f"  [{sel}] 길이={len(text)} / 미리보기: {text[:80]}")
        else:
            print(f"  [{sel}] 없음")