# agents/mac.py
"""
MAC (Multi-Agent Collaboration) Orchestrator
- 3개 전문 에이전트를 병렬 실행
- Conceptual Verbal Reinforcement: 에이전트 간 결과를 교차 검증해
  일치하면 신뢰도를 강화하고, 충돌하면 언어화된 충돌 사유와 함께 신뢰도를 감점
- 통합 판단(verdict)과 감사 로그(audit) 생성
"""
import os, time, asyncio
from . import data_analysis, research, risk

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


def _cross_check(da: dict, ir: dict) -> dict:
    """에이전트 간 개념적 교차 검증 (Verbal Reinforcement)."""
    confidence = 0.70
    reinforcements, conflicts = [], []

    sa_label = ir["sa"]["label"]
    trend = ir["tsf"]["trend"]
    events = {e["event"] for e in ir["ec"]["events"]}
    relations = {r["action"] for r in da["fre"]["relations"]}

    # 1. 감성 ↔ 금리 추세 정합성
    if sa_label == "긍정" and trend == "하락":
        confidence += 0.10
        reinforcements.append("뉴스 감성(긍정)과 금리 하락 추세가 일치 — 완화 국면 신호 강화")
    elif sa_label == "부정" and trend == "상승":
        confidence += 0.10
        reinforcements.append("뉴스 감성(부정)과 금리 상승 추세가 일치 — 긴축 국면 신호 강화")
    elif sa_label != "중립":
        confidence -= 0.10
        conflicts.append(f"감성({sa_label})과 금리 추세({trend})가 상충 — 해석 보류 권고")

    # 2. 관계 추출 ↔ 이벤트 분류 정합성
    if "인하" in relations and "금리결정" in events:
        confidence += 0.08
        reinforcements.append("FRE의 '인하' 관계와 EC의 금리결정 이벤트가 상호 확인됨")
    if "인상" in relations and sa_label == "긍정":
        confidence -= 0.08
        conflicts.append("금리 인상 관계가 추출됐으나 감성은 긍정 — 기사 맥락 재확인 필요")

    # 3. NER 밀도 → 근거 충분성
    if da["ner"]["count"] >= 5:
        confidence += 0.05
        reinforcements.append(f"개체 {da['ner']['count']}건 추출 — 근거 밀도 충분")
    elif da["ner"]["count"] <= 1:
        confidence -= 0.05
        conflicts.append("추출 개체가 부족 — 입력 텍스트의 정보량이 낮음")

    confidence = round(max(0.30, min(confidence, 0.95)), 2)
    return {"confidence": confidence,
            "reinforcements": reinforcements,
            "conflicts": conflicts}


def _verdict(ir: dict, check: dict) -> str:
    trend = ir["tsf"]["trend"]
    f = ir["tsf"]["forecast"]
    sa_label = ir["sa"]["label"]
    base = {
        "하락": f"기준금리는 향후 3개월 {f[0]}% → {f[-1]}% 하락 흐름이 유력합니다. 전세자금대출 금리 부담이 점진 완화될 수 있어, 변동금리 선택 시 이점이 커지는 국면입니다.",
        "상승": f"기준금리는 향후 3개월 {f[0]}% → {f[-1]}% 상승 압력이 있습니다. 고정금리 상품 우선 검토를 권합니다.",
        "보합": f"기준금리는 {f[0]}% 수준 보합이 예상됩니다. 금리보다 보증금 안전성(전세보증보험)에 집중할 시점입니다.",
    }[trend]
    tail = "" if not check["conflicts"] else " 단, 에이전트 간 신호 충돌이 감지되어 판단 신뢰도를 낮춰 제시합니다."
    return f"[뉴스 감성 {sa_label} · 금리 {trend}] {base}{tail}"


async def run_pipeline(text: str,
                       fraud_input: dict | None = None,
                       drp_input: dict | None = None) -> dict:
    t0 = time.time()
    audit = []

    # ── 병렬 실행 (Data Analysis + Investment Research) ──
    da_task = asyncio.create_task(data_analysis.run(text))
    ir_task = asyncio.create_task(research.run(text))
    rm_task = asyncio.create_task(risk.run(fraud_input, drp_input))
    da, ir, rm = await asyncio.gather(da_task, ir_task, rm_task)

    audit.append({"agent": "DataAnalysisAgent", "ms": int((time.time()-t0)*1000),
                  "tasks": da["tasks"]})
    audit.append({"agent": "InvestmentResearchAgent", "ms": int((time.time()-t0)*1000),
                  "tasks": ir["tasks"]})
    audit.append({"agent": "RiskManagementAgent", "ms": int((time.time()-t0)*1000),
                  "tasks": rm["tasks"]})

    # ── MAC 교차 검증 ──
    check = _cross_check(da, ir)
    audit.append({"agent": "MACOrchestrator", "ms": int((time.time()-t0)*1000),
                  "confidence": check["confidence"],
                  "conflicts": len(check["conflicts"])})

    return {
        "pipeline": "MAC-v1",
        "elapsed_ms": int((time.time() - t0) * 1000),
        "data_analysis": da,
        "research": ir,
        "risk": rm,
        "mac": {
            **check,
            "verdict": _verdict(ir, check),
        },
        "audit": audit,
        "llm_mode": bool(OPENAI_API_KEY),
        "disclaimer": "본 결과는 데모용 규칙·통계 모델 출력이며 투자·계약 판단의 근거가 될 수 없습니다.",
    }
