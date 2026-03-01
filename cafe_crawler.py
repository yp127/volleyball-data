"""
volleyball_crawler.py
- 다음 카페: 대회결과 + 대회일정
- 인스타그램: 해시태그 크롤링
- GitHub 자동 push (CSV + 뷰어)
- 변경사항 감지 (신규 글만 감지)
"""

import requests
from bs4 import BeautifulSoup
import csv, time, re, json, os, base64
from datetime import datetime
from zoneinfo import ZoneInfo

try:
    import instaloader
    INSTA_AVAILABLE = True
except ImportError:
    INSTA_AVAILABLE = False

# ══════════════════════════════════════
# 설정
# ══════════════════════════════════════
GITHUB_TOKEN    = os.environ.get("GITHUB_TOKEN", "")
GITHUB_USER     = "yp127"
GITHUB_REPO     = "volleyball-data"
GITHUB_BRANCH   = "main"

INSTA_USERNAME  = "vbv20_26"
INSTA_PASSWORD  = "instagram1357!"   # ← 인스타 비밀번호 입력
INSTA_HASHTAGS  = ["배구대회결과", "전국배구대회", "생활체육배구", "배구경기결과"]
INSTA_MAX_POSTS = 20

CAFE_TASKS = [
    {"board": "전국.지역대회결과", "fldid": "Iy5T", "start": 1287, "count": 30},
    {"board": "전국대회",          "fldid": "Ifrx", "start": 5446, "count": 30},
]
SCHEDULE_POST   = {"fldid": "Ifrx", "dataid": 5446}

CAFE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://cafe.daum.net/volleyballsok",
}

SKIP_TITLE_WORDS = [
    "랭구랭구", "단체사진", "팀 사진", "조편성", "대진표",
    "참가현황", "참가팀 현황", "추가모집", "숙지사항",
    "접수현황", "본선 대진",
]
RESULT_KEYWORDS = ["우승", "준우승", "1위", "2위", "경기결과", "입상", "순위", "결과"]
PLACES = "서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주"

LAST_IDS_FILE = "last_ids.json"


# ══════════════════════════════════════
# 유틸
# ══════════════════════════════════════
def clean_text(text):
    return re.sub(r"\s+", " ", text).strip()

def now_str():
    return datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M")

def load_last_ids():
    if os.path.exists(LAST_IDS_FILE):
        with open(LAST_IDS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"cafe_results": [], "insta": []}

def save_last_ids(data):
    with open(LAST_IDS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def rows_to_csv_string(rows, fieldnames):
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


# ══════════════════════════════════════
# GitHub API
# ══════════════════════════════════════
def github_get_sha(path):
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{path}"
    r = requests.get(url, headers={
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    })
    if r.status_code == 200:
        return r.json().get("sha")
    return None

def github_push_file(path, content_str, commit_msg):
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{path}"
    content_b64 = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")
    sha = github_get_sha(path)
    payload = {
        "message": commit_msg,
        "content": content_b64,
        "branch":  GITHUB_BRANCH,
    }
    if sha:
        payload["sha"] = sha
    r = requests.put(url, headers={
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }, json=payload)
    return r.status_code in (200, 201)

def github_enable_pages():
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/pages"
    r = requests.post(url, headers={
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }, json={"source": {"branch": "main", "path": "/"}})
    return r.status_code in (200, 201, 409)


# ══════════════════════════════════════
# 카페 크롤링
# ══════════════════════════════════════
def get_cafe_post(fldid, dataid):
    url = "https://cafe.daum.net/_c21_/bbs_search_read"
    params = {"grpid": "1ILxW", "fldid": fldid, "datanum": str(dataid), "svc": "cafeapi"}
    try:
        r = requests.get(url, headers=CAFE_HEADERS, params=params, timeout=10)
    except:
        return None
    if r.status_code != 200:
        return None

    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text()
    if "이 게시판은" in text or "삭제된 게시물" in text:
        return None

    t = soup.select_one(".bbs_read_tit")
    if not t:
        return None
    title = re.sub(r"\s+", " ", t.get_text()).strip()
    for b in ["전국.지역대회결과", "전국대회", "전국.지역대회공지"]:
        title = title.replace(b, "")
    if "추천" in title:
        title = title[:title.find("추천")]
    title = title.strip()
    if not title:
        return None

    if any(w in title for w in SKIP_TITLE_WORDS):
        return {"skip": True, "reason": title[:25]}

    m = re.search(r"\d{2}\.\d{2}\.\d{2}", text)
    date = m.group() if m else ""
    m2 = re.search(r"조회\s*([\d,]+)", text)
    views = m2.group(1).replace(",", "") if m2 else "0"

    content = ""
    xmp = soup.find("xmp", id="template_xmp")
    if xmp:
        content = clean_text(BeautifulSoup(xmp.get_text(), "html.parser").get_text())
    if not content:
        tables = soup.select("div.table-wrap")
        if tables:
            content = " ".join(clean_text(t.get_text()) for t in tables)

    return {"title": title, "date": date, "views": views, "content": content, "soup": soup}


def parse_schedule(soup):
    rows = []
    tables = soup.select("div.table-wrap")
    if len(tables) < 2:
        return rows
    raw = clean_text(tables[1].get_text())
    entries = re.split(r'(?=\d{1,2}월\d)', raw)
    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue
        m_month = re.match(r'^(\d{1,2})월', entry)
        if not m_month:
            continue
        month = int(m_month.group(1))
        rest = entry[m_month.end():]
        m_period = re.match(
            r'^(\d{1,2}일[~\-]\d{1,2}(?:/\d+)?일?|\d{1,2}일\([^)]*\)|\d{1,2}일토요일?|예정|~\d{1,2}월경?)',
            rest)
        period = m_period.group(1) if m_period else ""
        rest = rest[m_period.end():].strip() if m_period else rest
        m_place = re.search(r'(' + PLACES + r')[^\s]*\s*$', rest)
        if m_place:
            place = rest[m_place.start():].strip()
            name = rest[:m_place.start()].strip()
        else:
            place = ""
            name = rest.strip()
        name = re.sub(r'\s*/결과.*$', '', name)
        name = re.sub(r'\s*/예정.*$', '', name)
        name = clean_text(name)
        if len(name) < 4:
            continue
        rows.append({"월": f"{month}월", "기간": period, "대회명": name, "장소": place})
    return rows


def crawl_cafe(last_ids):
    result_rows = []
    schedule_rows = []
    new_ids = []
    changes = []

    print("[카페] 대회일정 파싱 중...")
    sched = get_cafe_post(SCHEDULE_POST["fldid"], SCHEDULE_POST["dataid"])
    if sched and not sched.get("skip"):
        schedule_rows = parse_schedule(sched["soup"])
        print(f"  → {len(schedule_rows)}개 일정")
    time.sleep(2)

    for task in CAFE_TASKS:
        board  = task["board"]
        fldid  = task["fldid"]
        dataid = task["start"]
        count  = task["count"]
        done = miss = 0
        print(f"\n[카페] [{board}] {dataid}번부터 {count}개")

        while done < count and miss < 15:
            post = get_cafe_post(fldid, dataid)
            if post is None:
                miss += 1
            elif post.get("skip"):
                print(f"  {dataid}: 스킵 ({post['reason']})")
                miss += 1
            else:
                title = post["title"]
                content = post["content"]
                if board == "전국.지역대회결과":
                    if not any(k in title + content for k in RESULT_KEYWORDS):
                        dataid -= 1
                        miss += 1
                        time.sleep(1)
                        continue
                post_id = f"{fldid}_{dataid}"
                is_new  = post_id not in last_ids.get("cafe_results", [])
                row = {
                    "게시판": board, "dataid": dataid, "제목": title,
                    "작성일": post["date"], "조회수": post["views"],
                    "본문": content[:3000],
                    "URL": f"https://cafe.daum.net/volleyballsok/{fldid}/{dataid}",
                    "신규": "Y" if is_new else "",
                    "수집일": now_str(),
                }
                result_rows.append(row)
                new_ids.append(post_id)
                done += 1; miss = 0
                if is_new:
                    changes.append({"구분": "카페신규", "제목": title, "날짜": post["date"]})
                    print(f"  {dataid}: ★신규 {title[:35]}")
                else:
                    print(f"  {dataid}: ✓ {title[:35]}")
            dataid -= 1
            time.sleep(2)
        print(f"  → {done}개 완료")

    return result_rows, schedule_rows, new_ids, changes


# ══════════════════════════════════════
# 인스타 크롤링
# ══════════════════════════════════════
def crawl_instagram(last_ids):
    if not INSTA_AVAILABLE:
        print("\n[인스타] instaloader 미설치 스킵 → pip install instaloader")
        return [], [], []
    if not INSTA_PASSWORD:
        print("\n[인스타] 비밀번호 미설정 스킵")
        return [], [], []

    rows = []
    new_ids = []
    changes = []

    print(f"\n[인스타] 로그인 중... ({INSTA_USERNAME})")
    L = instaloader.Instaloader(
        download_pictures=False, download_videos=False,
        download_video_thumbnails=False, save_metadata=False, quiet=True)
    try:
        L.login(INSTA_USERNAME, INSTA_PASSWORD)
        print("  로그인 성공")
    except Exception as e:
        print(f"  로그인 실패: {e}")
        return [], [], []

    for tag in INSTA_HASHTAGS:
        print(f"  #{tag} 수집 중...")
        try:
            hashtag = instaloader.Hashtag.from_name(L.context, tag)
            count = 0
            for post in hashtag.get_posts():
                if count >= INSTA_MAX_POSTS:
                    break
                post_id = str(post.shortcode)
                is_new  = post_id not in last_ids.get("insta", [])
                caption = (post.caption or "")[:1000]
                row = {
                    "해시태그": f"#{tag}",
                    "작성일":   post.date_local.strftime("%y.%m.%d"),
                    "본문":     caption,
                    "좋아요":   post.likes,
                    "URL":      f"https://www.instagram.com/p/{post.shortcode}/",
                    "신규":     "Y" if is_new else "",
                    "수집일":   now_str(),
                }
                rows.append(row)
                new_ids.append(post_id)
                count += 1
                if is_new:
                    changes.append({"구분": "인스타신규", "제목": caption[:40], "날짜": row["작성일"]})
                time.sleep(1)
            print(f"    → {count}개")
            time.sleep(3)
        except Exception as e:
            print(f"    오류: {e}")
            time.sleep(5)

    return rows, new_ids, changes


# ══════════════════════════════════════
# GitHub Push
# ══════════════════════════════════════
def push_to_github(result_rows, schedule_rows, insta_rows, changes):
    print("\n[GitHub] 업로드 중...")
    ts = now_str()

    # CSV 파일들
    files = []

    if result_rows:
        csv_str = rows_to_csv_string(result_rows,
            ["게시판","dataid","제목","작성일","조회수","본문","URL","신규","수집일"])
        files.append(("cafe_results.csv", csv_str, f"update cafe_results {ts}"))

    if schedule_rows:
        csv_str = rows_to_csv_string(schedule_rows, ["월","기간","대회명","장소"])
        files.append(("cafe_schedule.csv", csv_str, f"update cafe_schedule {ts}"))

    if insta_rows:
        csv_str = rows_to_csv_string(insta_rows,
            ["해시태그","작성일","본문","좋아요","URL","신규","수집일"])
        files.append(("insta_results.csv", csv_str, f"update insta_results {ts}"))

    # 변경이력
    changelog_path = "changelog.json"
    existing_sha = github_get_sha(changelog_path)
    if existing_sha:
        url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{changelog_path}"
        r = requests.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
        try:
            existing = json.loads(base64.b64decode(r.json()["content"]).decode("utf-8"))
        except:
            existing = []
    else:
        existing = []

    if changes:
        for c in changes:
            c["수집일"] = ts
        existing = changes + existing
    existing_str = json.dumps(existing[:200], ensure_ascii=False, indent=2)
    files.append((changelog_path, existing_str, f"update changelog {ts}"))

    # 업로드 메타
    meta = json.dumps({"last_updated": ts, "total_results": len(result_rows),
                       "total_schedule": len(schedule_rows), "total_insta": len(insta_rows),
                       "new_count": len(changes)}, ensure_ascii=False, indent=2)
    files.append(("meta.json", meta, f"update meta {ts}"))

    # 파일 push
    ok_count = 0
    for path, content, msg in files:
        ok = github_push_file(path, content, msg)
        status = "✓" if ok else "✗"
        print(f"  {status} {path}")
        if ok:
            ok_count += 1
        time.sleep(0.5)

    # GitHub Pages 활성화 시도
    github_enable_pages()

    print(f"\n  완료: {ok_count}/{len(files)}개 업로드")
    print(f"  뷰어 URL: https://{GITHUB_USER}.github.io/{GITHUB_REPO}/")


# ══════════════════════════════════════
# 메인
# ══════════════════════════════════════
def main():
    print(f"{'='*55}")
    print(f"  배구대회 크롤러: {now_str()}")
    print(f"{'='*55}")

    last_ids = load_last_ids()

    result_rows, schedule_rows, cafe_new_ids, cafe_changes = crawl_cafe(last_ids)
    insta_rows, insta_new_ids, insta_changes = crawl_instagram(last_ids)

    all_changes = cafe_changes + insta_changes
    print(f"\n변경: 카페 {len(cafe_changes)}건 / 인스타 {len(insta_changes)}건")

    # 로컬 CSV 저장
    if result_rows:
        with open("cafe_results.csv", "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["게시판","dataid","제목","작성일","조회수","본문","URL","신규","수집일"])
            w.writeheader(); w.writerows(result_rows)
    if schedule_rows:
        with open("cafe_schedule.csv", "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["월","기간","대회명","장소"])
            w.writeheader(); w.writerows(schedule_rows)

    # GitHub push
    push_to_github(result_rows, schedule_rows, insta_rows, all_changes)

    # 실행 기록 저장
    save_last_ids({
        "cafe_results": cafe_new_ids,
        "insta": insta_new_ids,
        "last_run": now_str(),
    })

    print(f"\n완료: {now_str()}")


if __name__ == "__main__":
    main()