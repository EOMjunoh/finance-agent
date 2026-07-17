# agents/research.py
"""
Investment Research Agent
- SA  (Sentiment Analysis)      : 금융 감성 사전 기반 스코어링
- EC  (Event Classification)    : 키워드 기반 이벤트 분류
- TSF (Time Series Forecasting) : 선형회귀 + 이동평균으로 기준금리 3개월 예측
"""
import os, re, csv, pathlib

POS_WORDS = ["상승","호조","개선","확대","완화","증가","반등","회복","인하","지원",
             "성장","안정","호재","급등","강세","활성화","혜택","우대"]
NEG_WORDS = ["하락","악화","축소","위축","감소","급락","침체","인상","규제","부담",
             "리스크","위험","불안","약세","부실","연체","경고","제한"]

EVENT_RULES = [
    ("금리결정",  ["기준금리","금리 인상","금리 인하","금리 동결","금통위"]),
    ("규제정책",  ["규제","LTV","DSR 규제","대출 제한","전매 제한","투기"]),
    ("공급정책",  ["공급","분양","입주","착공","임대주택","청약"]),
    ("시장동향",  ["전세가","매매가","거래량","미분양","시세"]),
]


def sa(text: str) -> dict:
    pos = sum(text.count(w) for w in POS_WORDS)
    neg = sum(text.count(w) for w in NEG_WORDS)
    total = pos + neg
    score = 0.0 if total == 0 else round((pos - neg) / total, 3)
    label = "긍정" if score > 0.15 else ("부정" if score < -0.15 else "중립")
    return {"score": score, "label": label, "pos_hits": pos, "neg_hits": neg,
            "method": "lexicon"}


def ec(text: str) -> dict:
    events = []
    for name, kws in EVENT_RULES:
        hits = [k for k in kws if k in text]
        if hits:
            events.append({"event": name, "triggers": hits})
    return {"events": events, "primary": events[0]["event"] if events else "일반"}


def _load_rates() -> list[tuple[str, float]]:
    path = pathlib.Path(__file__).parent.parent / "data" / "base_rate.csv"
    rows = []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append((r["month"], float(r["rate"])))
    return rows


def tsf(horizon: int = 3) -> dict:
    """기준금리 시계열 → 최근 12개월 선형회귀로 horizon개월 예측."""
    series = _load_rates()
    recent = series[-12:]
    n = len(recent)
    xs = list(range(n))
    ys = [v for _, v in recent]
    x_mean = sum(xs) / n
    y_mean = sum(ys) / n
    denom = sum((x - x_mean) ** 2 for x in xs) or 1
    slope = sum((xs[i] - x_mean) * (ys[i] - y_mean) for i in range(n)) / denom
    intercept = y_mean - slope * x_mean

    forecast = []
    for h in range(1, horizon + 1):
        raw = intercept + slope * (n - 1 + h)
        forecast.append(round(max(0.0, min(raw, 10.0)) * 4) / 4)   # 0.25%p 스텝 반올림

    trend = "하락" if slope < -0.01 else ("상승" if slope > 0.01 else "보합")
    return {
        "history": [{"month": m, "rate": v} for m, v in series[-12:]],
        "forecast": forecast,
        "trend": trend,
        "slope_per_month": round(slope, 4),
        "method": "linear-regression(12m)",
        "note": "샘플 데이터 기반 통계 예측 — 투자 판단 근거 아님",
    }


async def run(text: str) -> dict:
    return {
        "agent": "InvestmentResearchAgent",
        "tasks": ["SA", "EC", "TSF"],
        "sa": sa(text),
        "ec": ec(text),
        "tsf": tsf(),
    }
