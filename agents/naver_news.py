# agents/naver_news.py
"""
네이버 뉴스 검색 오픈API 연동 (공식 API — https://developers.naver.com)
- NAVER_CLIENT_ID / NAVER_CLIENT_SECRET이 없으면 조용히 비활성화 상태로 남는다
  (기존 수동 실시간 피드는 그대로 동작)
- 여러 검색어를 주기적으로 조회해 새로 나온 기사만 실시간 피드에 추가한다
"""
import os, re, json, urllib.request, urllib.parse

API_URL = "https://openapi.naver.com/v1/search/news.json"
DEFAULT_QUERIES = ["기준금리", "전세사기", "대출 규제"]

_TAG_RE = re.compile(r"<[^>]+>")


def enabled() -> bool:
    return bool(os.getenv("NAVER_CLIENT_ID") and os.getenv("NAVER_CLIENT_SECRET"))


def queries() -> list[str]:
    raw = os.getenv("NAVER_QUERIES", "")
    qs = [q.strip() for q in raw.split(",") if q.strip()]
    return qs or DEFAULT_QUERIES


def _clean(s: str) -> str:
    return (_TAG_RE.sub("", s)
            .replace("&quot;", '"').replace("&amp;", "&")
            .replace("&lt;", "<").replace("&gt;", ">").strip())


def search(query: str, display: int = 5) -> list[dict]:
    """뉴스 검색 → [{title, description, link, pub_date}]. 미설정/오류 시 빈 리스트."""
    if not enabled():
        return []
    qs = urllib.parse.urlencode({"query": query, "display": display, "sort": "date"})
    req = urllib.request.Request(
        f"{API_URL}?{qs}",
        headers={"X-Naver-Client-Id": os.environ["NAVER_CLIENT_ID"],
                  "X-Naver-Client-Secret": os.environ["NAVER_CLIENT_SECRET"]})
    with urllib.request.urlopen(req, timeout=4) as res:
        payload = json.loads(res.read().decode("utf-8"))
    return [{
        "title": _clean(it.get("title", "")),
        "description": _clean(it.get("description", "")),
        "link": it.get("originallink") or it.get("link", ""),
        "pub_date": it.get("pubDate", ""),
    } for it in payload.get("items", [])]
