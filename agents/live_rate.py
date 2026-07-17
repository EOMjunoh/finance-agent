# agents/live_rate.py
"""
기준금리 실시간 연동 (한국은행 ECOS Open API — 722Y001, 공공데이터)
- ECOS_API_KEY가 없으면 공개 sample 키로 최대 10건까지 조회 가능
- 실패 시 data/base_rate.csv 샘플로 자동 폴백 (앱은 항상 동작)
- REFRESH_SEC마다 백그라운드에서 재조회되어 "실시간" 갱신을 흉내낸다
"""
import os, csv, json, time, pathlib, urllib.request

STAT_CODE = "722Y001"   # 1.3.1. 한국은행 기준금리 및 여수신금리
ITEM_CODE = "0101000"   # 한국은행 기준금리
REFRESH_SEC = int(os.getenv("ECOS_REFRESH_SEC", "1800"))

_CSV_PATH = pathlib.Path(__file__).parent.parent / "data" / "base_rate.csv"

_cache = {"series": None, "source": "init", "last_updated": None,
          "error": None, "fetched_at": 0.0}


def _load_csv() -> list[tuple[str, float]]:
    rows = []
    with open(_CSV_PATH, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append((r["month"], float(r["rate"])))
    return rows


def _fetch_ecos() -> list[tuple[str, float]]:
    key = os.getenv("ECOS_API_KEY", "sample")
    count = 10 if key == "sample" else 24
    end = time.strftime("%Y%m")
    start = f"{int(end[:4]) - 2}{end[4:]}"
    url = (f"https://ecos.bok.or.kr/api/StatisticSearch/{key}/json/kr/1/{count}/"
           f"{STAT_CODE}/M/{start}/{end}/{ITEM_CODE}")
    with urllib.request.urlopen(url, timeout=4) as res:
        payload = json.loads(res.read().decode("utf-8"))
    if "StatisticSearch" not in payload:
        raise RuntimeError(payload.get("RESULT", {}).get("MESSAGE", "ECOS 응답 오류"))
    series = [(r["TIME"][:4] + "-" + r["TIME"][4:], float(r["DATA_VALUE"]))
              for r in payload["StatisticSearch"]["row"] if r.get("DATA_VALUE")]
    series.sort(key=lambda x: x[0])
    return series


def refresh(force: bool = False) -> dict:
    """ECOS에서 최신 기준금리를 가져와 캐시 갱신. 실패해도 예외를 던지지 않고 폴백 유지."""
    now = time.time()
    if not force and _cache["series"] and (now - _cache["fetched_at"]) < REFRESH_SEC:
        return _cache
    try:
        series = _fetch_ecos()
        if len(series) < 3:
            raise RuntimeError("ECOS 응답 데이터 부족")
        _cache.update(series=series, source="ecos-live",
                       last_updated=time.strftime("%Y-%m-%d %H:%M:%S"),
                       fetched_at=now, error=None)
    except Exception as e:
        if not _cache["series"]:
            _cache.update(series=_load_csv(), source="sample-fallback",
                          last_updated=time.strftime("%Y-%m-%d %H:%M:%S"), fetched_at=now)
        _cache["error"] = str(e)[:200]
    return _cache


def get_series() -> list[tuple[str, float]]:
    if not _cache["series"]:
        refresh(force=True)
    return _cache["series"]


def status() -> dict:
    return {"source": _cache["source"], "last_updated": _cache["last_updated"],
            "error": _cache["error"], "points": len(_cache["series"] or [])}
