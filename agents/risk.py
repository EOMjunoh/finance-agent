# agents/risk.py
"""
Risk Management Agent
- FD  (Fraud Detection)        : 전세사기 위험 룰 스코어링 (깡통전세·신탁·근저당·체납)
- DRP (Default Risk Prediction): DSR 기반 부채 리스크 등급
규칙 기준은 시연용 단순화 값 — 실제 심사 기준과 다를 수 있음.
"""

def fraud_detect(deposit: int, price: int, mortgage: int = 0,
                 trust_registered: bool = False, tax_arrears: bool = False,
                 landlord_multi: bool = False) -> dict:
    """
    전세사기(깡통전세) 위험 점수 0~100.
    deposit  : 전세 보증금 (만원)
    price    : 주택 매매 시세 (만원)
    mortgage : 선순위 근저당 채권최고액 (만원)
    """
    score, reasons = 0, []
    if price <= 0:
        return {"score": 90, "grade": "위험", "reasons": ["매매 시세 확인 불가 — 시세 미확인 자체가 고위험 신호"]}

    ratio = (deposit + mortgage) / price * 100     # 보증금+근저당 / 시세
    if ratio >= 90:
        score += 45; reasons.append(f"보증금+근저당이 시세의 {ratio:.0f}% — 깡통전세 위험")
    elif ratio >= 80:
        score += 30; reasons.append(f"보증금+근저당이 시세의 {ratio:.0f}% — 경계 구간(80%↑)")
    elif ratio >= 70:
        score += 15; reasons.append(f"보증금+근저당이 시세의 {ratio:.0f}% — 주의 관찰")
    else:
        reasons.append(f"보증금+근저당 비율 {ratio:.0f}% — 안전 구간")

    if mortgage > 0:
        score += 10; reasons.append(f"선순위 근저당 {mortgage:,}만원 존재 — 경매 시 배당 후순위")
    if trust_registered:
        score += 20; reasons.append("신탁 등기 — 수탁사 동의 없는 계약은 보증금 보호 불가")
    if tax_arrears:
        score += 15; reasons.append("임대인 세금 체납 — 조세채권이 보증금보다 우선 변제")
    if landlord_multi:
        score += 10; reasons.append("임대인 다주택 보유 — 동시 보증사고 위험")

    score = min(score, 100)
    grade = "위험" if score >= 60 else ("주의" if score >= 30 else "안전")
    actions = {
        "위험": ["계약 보류 후 전세보증보험(HUG) 가입 가능 여부 우선 확인",
                "등기부등본 을구 재확인 및 시세 재검증(국토부 실거래가)"],
        "주의": ["전세보증보험 가입을 계약 특약에 명시",
                "잔금일 당일 근저당 말소 조건 특약 추가"],
        "안전": ["확정일자 + 전입신고 즉시 완료로 대항력 확보"],
    }[grade]
    return {"score": score, "grade": grade,
            "ltv_like_ratio": round(ratio, 1),
            "reasons": reasons, "actions": actions,
            "method": "rule-scoring(demo)"}


def default_risk(annual_income: int, existing_annual_payment: int,
                 new_loan: int, rate_pct: float = 4.0, years: int = 30) -> dict:
    """
    DSR 기반 부채 리스크.
    annual_income           : 연소득 (만원)
    existing_annual_payment : 기존 대출 연 원리금 상환액 (만원)
    new_loan                : 신규 대출 원금 (만원)
    """
    if annual_income <= 0:
        return {"error": "연소득이 필요합니다"}
    r = rate_pct / 100 / 12
    n = years * 12
    monthly = new_loan * r * (1 + r) ** n / ((1 + r) ** n - 1) if r > 0 else new_loan / n
    new_annual = monthly * 12
    dsr = (existing_annual_payment + new_annual) / annual_income * 100

    if dsr >= 70:   grade, msg = "고위험", "상환 부담이 소득의 70%를 넘어 연체 가능성이 높습니다"
    elif dsr >= 40: grade, msg = "규제한도 초과", "은행권 DSR 40% 규제로 신규 대출이 제한될 수 있습니다"
    elif dsr >= 30: grade, msg = "적정 상한", "대출은 가능하나 여유 자금 관리가 필요합니다"
    else:           grade, msg = "안정", "상환 여력이 충분한 수준입니다"

    max_annual_capacity = annual_income * 0.40 - existing_annual_payment
    return {"dsr_pct": round(dsr, 1), "grade": grade, "message": msg,
            "new_monthly_payment": round(monthly, 1),
            "max_additional_annual_payment": round(max(0, max_annual_capacity), 1),
            "assumption": f"금리 {rate_pct}% · {years}년 원리금균등",
            "method": "DSR-rule(demo)"}


async def run(fraud_input: dict | None = None, drp_input: dict | None = None) -> dict:
    out = {"agent": "RiskManagementAgent", "tasks": ["FD", "DRP"]}
    if fraud_input:
        out["fd"] = fraud_detect(**fraud_input)
    if drp_input:
        out["drp"] = default_risk(**drp_input)
    return out
