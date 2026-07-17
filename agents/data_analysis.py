# agents/data_analysis.py
"""
Data Analysis Agent
- TS  (Text Summarization)          : 빈도 기반 추출 요약 (LLM 키 있으면 생성 요약)
- NER (Named Entity Recognition)    : 금융 도메인 사전 + 정규식
- FRE (Financial Relation Extraction): 패턴 기반 관계 추출
모든 기능은 외부 API 키 없이 동작하며, OPENAI_API_KEY가 있으면 LLM으로 고도화됩니다.
"""
import os, re, json
from collections import Counter

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# ── 금융 개체 사전 ──
ORG_DICT = [
    "한국은행", "금융위원회", "금융감독원", "국토교통부", "기획재정부",
    "KB국민은행", "신한은행", "하나은행", "우리은행", "NH농협은행",
    "주택도시보증공사", "HUG", "주택금융공사", "HF", "LH", "SH공사",
    "연방준비제도", "Fed", "한국부동산원",
]
_STOPWORDS = {"있다","했다","한다","및","등","이","그","저","것","수","를","을","는","은","가","의","에","로","으로"}


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?다요])\s+", text.strip())
    return [p.strip() for p in parts if len(p.strip()) > 8]


def ts_summarize(text: str, max_sentences: int = 2) -> dict:
    """추출 요약: 단어 빈도로 문장 점수화 → 상위 N문장을 원문 순서로."""
    sents = _sentences(text)
    if len(sents) <= max_sentences:
        return {"summary": text.strip(), "method": "passthrough", "sentences_used": len(sents)}

    words = re.findall(r"[가-힣A-Za-z]{2,}", text)
    freq = Counter(w for w in words if w not in _STOPWORDS)
    scored = []
    for i, s in enumerate(sents):
        s_words = re.findall(r"[가-힣A-Za-z]{2,}", s)
        score = sum(freq.get(w, 0) for w in s_words) / (len(s_words) + 1)
        scored.append((score, i, s))
    top = sorted(sorted(scored, reverse=True)[:max_sentences], key=lambda x: x[1])
    return {"summary": " ".join(s for _, _, s in top),
            "method": "extractive-tf", "sentences_used": max_sentences}


def ner(text: str) -> dict:
    """기관 사전 + 정규식으로 금융 개체 추출."""
    ents = {"ORG": [], "MONEY": [], "RATE": [], "DATE": []}
    for org in ORG_DICT:
        if org in text:
            ents["ORG"].append(org)
    ents["MONEY"] = list(dict.fromkeys(
        re.findall(r"\d[\d,.]*\s*(?:조|억|천만|백만|만)\s*원", text)))
    ents["RATE"] = list(dict.fromkeys(
        re.findall(r"(?:연\s*)?\d+(?:\.\d+)?\s*%(?:p)?", text)))
    ents["DATE"] = list(dict.fromkeys(
        re.findall(r"\d{4}년\s*\d{1,2}월(?:\s*\d{1,2}일)?|\d{1,2}월\s*\d{1,2}일|올해|내년|이번\s*달", text)))
    ents["ORG"] = list(dict.fromkeys(ents["ORG"]))
    return {"entities": ents,
            "count": sum(len(v) for v in ents.values())}


_REL_PATTERNS = [
    (r"([가-힣A-Za-z]+(?:은행|공사|위원회|부|원))[은는이가]?\s*.{0,25}?(인상|인하|동결)", "정책결정"),
    (r"([가-힣A-Za-z]+(?:은행|공사|위원회|부|원))[은는이가]?\s*.{0,25}?(지원|공급|출시|확대)", "지원·공급"),
    (r"([가-힣A-Za-z]+(?:은행|공사|위원회|부|원))[은는이가]?\s*.{0,25}?(규제|제한|강화|점검)", "규제"),
]

def fre(text: str) -> dict:
    """주어(기관)-행위 패턴으로 금융 관계 추출."""
    relations = []
    for pat, rel_type in _REL_PATTERNS:
        for m in re.finditer(pat, text):
            relations.append({"subject": m.group(1), "action": m.group(2), "type": rel_type})
    seen, uniq = set(), []
    for r in relations:
        k = (r["subject"], r["action"])
        if k not in seen:
            seen.add(k); uniq.append(r)
    return {"relations": uniq, "count": len(uniq)}


async def _llm_enhance(text: str, base: dict) -> dict:
    """OPENAI_API_KEY가 있으면 생성 요약으로 교체."""
    if not OPENAI_API_KEY:
        return base
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        res = await client.chat.completions.create(
            model="gpt-4o-mini", temperature=0, max_tokens=200,
            messages=[
                {"role": "system", "content": "금융 뉴스를 2문장 한국어로 요약하세요. 수치는 원문 그대로 유지."},
                {"role": "user", "content": text[:2000]},
            ])
        base["ts"]["summary"] = res.choices[0].message.content.strip()
        base["ts"]["method"] = "llm-abstractive"
    except Exception as e:
        base["ts"]["llm_error"] = str(e)[:100]
    return base


async def run(text: str) -> dict:
    """에이전트 진입점."""
    result = {
        "agent": "DataAnalysisAgent",
        "tasks": ["TS", "NER", "FRE"],
        "ts": ts_summarize(text),
        "ner": ner(text),
        "fre": fre(text),
    }
    return await _llm_enhance(text, result)
