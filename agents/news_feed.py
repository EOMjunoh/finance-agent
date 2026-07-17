# agents/news_feed.py
"""
실시간 뉴스 피드 (인메모리, 프로세스 단일 인스턴스 기준)
- 새 항목이 add()로 들어오면 list_since()를 폴링하는 모든 화면에 즉시 반영된다
- 저작권 있는 언론사 RSS를 무단으로 자동 수집하지 않는다(AI 활용 금지 조항 등 존재) —
  실서비스 전환 시 라이선스가 확인된 뉴스 API/제휴 피드를 이 모듈에 연결하면 된다
"""
import time, itertools, pathlib

_SAMPLE_PATH = pathlib.Path(__file__).parent.parent / "data" / "sample_news.txt"
_MAX = 30

_counter = itertools.count(1)
_items: list[dict] = []


def _seed() -> None:
    if _items:
        return
    text = _SAMPLE_PATH.read_text(encoding="utf-8").strip()
    _items.append({"id": next(_counter), "ts": time.time(), "text": text, "source": "sample", "link": None})


def add(text: str, source: str = "manual", link: str | None = None) -> dict:
    text = (text or "").strip()
    if not text:
        raise ValueError("empty text")
    _seed()
    item = {"id": next(_counter), "ts": time.time(), "text": text, "source": source, "link": link}
    _items.append(item)
    del _items[:-_MAX]
    return item


def list_since(after_id: int = 0) -> list[dict]:
    _seed()
    return [i for i in _items if i["id"] > after_id]


def latest_id() -> int:
    _seed()
    return _items[-1]["id"] if _items else 0
