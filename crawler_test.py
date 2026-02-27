# crawler_test.py
import requests
from bs4 import BeautifulSoup
import csv
import time
import re
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

GRPID = "1ILxW"
KEYWORDS = ["대회결과", "경기결과", "대회 결과", "경기 결과", "결과보고", "성적"]

# 제거할 노이즈 패턴
NOISE_PATTERNS = [
    r"다음 카페의 ie10.*?업데이트 해주세요\.",
    r"다시보지않기",
    r"Daum \| 카페 \| 테이블 \| 메일.*?로그인",
    r"카페앱 설치.*?전국대회",
    r"카페정보.*?카페 전체 메뉴",
    r"▲ 검색 카페 게시글 목록.*?스팸처리",
    r"북마크 번역하기 공유하기 기능 더보기",
    r"게시글 본문내용",
    r"다음검색.*?비영리",
    r"저작자 표시.*?비영리",
    r"출처:.*?원문보기",
    r"댓글\d+.*?추천해요\d+.*?스크랩\d+",
    r"댓글\d{2}\.\d{2}\.\d{2}.*",  # 댓글 내용
    r"검색 옵션.*?재로딩",
    r"최신목록 글쓰기.*?스팸처리",
    r"서비스 약관.*?ⓒ AXZ Corp\.",
    r"첨부된 파일.*?다운로드",
    r"이전글 다음글 검색이 허용된 게시물입니다\.",
    r"추천 \d+ 조회.*?댓글\d+",
    r"카페 게시글 목록",
    r"ⓒ AXZ Corp\.",
]

def clean_content(text):
    """노이즈 제거 및 본문만 추출"""
    for pattern in NOISE_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.DOTALL)
    # 연속 공백/줄바꿈 정리
    text = re.sub(r"\s{3,}", "\n", text)
    text = text.strip()
    return text

def get_boards():
    url = "https://cafe.daum.net/_c21_/home"
    resp = requests.get(url, headers=HEADERS, params={"grpid": GRPID}, timeout=10)
    soup = BeautifulSoup(resp.text, "html.parser")
    boards = []
    seen = set()
    for a in soup.select("a[href*='fldid']"):
        href = a.get("href", "")
        match = re.search(r"fldid=([A-Za-z0-9]+)", href)
        if match:
            fldid = match.group(1)
            name = a.get_text(strip=True)
            if fldid and name and fldid not in seen:
                seen.add(fldid)
                boards.append((fldid, name))
    return boards

def get_article_list(fldid):
    url = "https://cafe.daum.net/_c21_/bottom/articles"
    params = {"grpid": GRPID, "fldid": fldid, "contentval": "000zzzzzzzzzzzzzzzzzzzzzzzzzz"}
    resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
    try:
        return resp.json().get("articles", [])
    except:
        return []

def get_content(fldid, datanum):
    url = "https://cafe.daum.net/_c21_/bbs_search_read"
    params = {"grpid": "1ILxW", "fldid": fldid, "datanum": str(datanum), "svc": "cafeapi"}
    resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
    soup = BeautifulSoup(resp.text, "html.parser")

    # 1순위: xmp 태그 (본문이 여기 있는 경우)
    xmp = soup.find("xmp", id="template_xmp")
    if xmp:
        return clean_content(xmp.get_text(separator=" ", strip=True))

    # 2순위: 기존 div 셀렉터
    for sel in ["div.article_view", "div#article", "div.cont_view", "div.tview"]:
        c = soup.select_one(sel)
        if c:
            for tag in c.select("div.cont_comment, div#comment-list"):
                tag.decompose()
            return clean_content(c.get_text(separator=" ", strip=True))

    # 3순위: table-wrap
    tables = soup.select("div.table-wrap")
    if tables:
        combined = " ".join(t.get_text(separator=" ", strip=True) for t in tables)
        return clean_content(combined)

    return ""

def is_match(title):
    return any(kw in title for kw in KEYWORDS)

def main():
    print("=" * 50)
    print("카페 크롤링 시작:", datetime.now().strftime("%Y-%m-%d %H:%M"))
    print("=" * 50)

    print("\n[1] 게시판 목록 수집 중...")
    boards = get_boards()
    print(f"  → {len(boards)}개 게시판 발견")

    results = []

    for fldid, board_name in boards:
        print(f"\n[2] [{board_name}] 수집 중...")
        articles = get_article_list(fldid)
        matched = [a for a in articles if is_match(a.get("dataname", ""))]
        print(f"  → {len(articles)}개 중 {len(matched)}개 매칭")

        for a in matched:
            print(f"  [수집] {a['dataname']}")
            content = get_content(fldid, a["dataid"])
            results.append({
                "게시판": board_name,
                "dataid": a["dataid"],
                "제목": a["dataname"],
                "작성일": a["regdtshow"],
                "조회수": a["viewcount"],
                "본문": content,
                "URL": f"https://cafe.daum.net/volleyballsok/{fldid}/{a['dataid']}"
            })
            time.sleep(0.3)

    filename = f"배구대회결과_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["게시판","dataid","제목","작성일","조회수","본문","URL"])
        writer.writeheader()
        writer.writerows(results)

    print(f"\n완료! 총 {len(results)}개 저장 → {filename}")

if __name__ == "__main__":
    main()