import re, json, sys, datetime
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

# 게시판 목록 주소. 안 열리면 아래 "문제 해결"을 보세요.
LIST_URLS = [
    "https://dorm.kmu.ac.kr/bbs/dorm/1211/artclList.do",
    "http://cms.kmu.ac.kr/bbs/dorm/1211/artclList.do",
    "http://cms.kmu.ac.kr/dorm/13426/subview.do",
]
HEADERS = {"User-Agent": "Mozilla/5.0"}


def get_soup(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    r.encoding = "utf-8"
    return BeautifulSoup(r.text, "html.parser")


def find_latest_post():
    """목록에서 제목에 '식단표'가 있는 첫 글(가장 최근 글)의 주소와 제목."""
    for list_url in LIST_URLS:
        try:
            soup = get_soup(list_url)
        except Exception as e:
            print("목록 실패:", list_url, e)
            continue
        for a in soup.find_all("a", href=True):
            title = a.get_text(" ", strip=True)
            if "식단표" in title and "artclView" in a["href"]:
                return urljoin(list_url, a["href"]), title
    return None, None


DATE = re.compile(r"(\d{1,2})월\s*(\d{1,2})일")
DOW = re.compile(r"\(([월화수목금토일])\)")


def parse_menu(soup):
    days, cur = [], None
    for tr in soup.select("table tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
        if not cells:
            continue
        if cells[0].startswith("식재료"):          # 표의 끝
            break
        m = DATE.fullmatch(cells[0])
        if m:                                       # 새 날짜 시작
            cur = {"date": f"{int(m[1])}/{int(m[2])}", "dow": "",
                   "breakfast": [], "lunch": [], "dinner": []}
            days.append(cur)
            cells = cells[1:]
        elif cur and DOW.fullmatch(cells[0]):       # 요일 칸
            cur["dow"] = DOW.fullmatch(cells[0])[1]
            cells = cells[1:]
        if cur is None or len(cells) != 3:
            continue
        for key, text in zip(("breakfast", "lunch", "dinner"), cells):
            if text:
                cur[key].append(text)
    return days


def main():
    url, title = find_latest_post()
    if not url:
        sys.exit("식단표 글을 찾지 못했습니다.")
    days = parse_menu(get_soup(url))
    if not days:
        sys.exit("표에서 날짜를 읽지 못했습니다. 페이지 구조가 바뀌었을 수 있습니다.")
    data = {
        "updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "title": title,
        "source": url,
        "days": days,
    }
    with open("menu.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"완료: {title} / {len(days)}일치")


main()
