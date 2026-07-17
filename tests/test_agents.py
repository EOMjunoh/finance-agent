# tests/test_agents.py
import asyncio, pytest
from agents import data_analysis, research, risk, mac

SAMPLE = ("한국은행이 기준금리를 2.50%로 인하하면서 전세자금대출 금리 부담이 완화될 전망이다. "
          "국토교통부는 청년 임대주택 공급을 확대한다고 밝혔다. "
          "일부 지역의 깡통전세 위험은 여전히 리스크 요인으로 지적된다.")


def test_ts_summarize():
    out = data_analysis.ts_summarize(SAMPLE, max_sentences=2)
    assert out["summary"]
    assert out["sentences_used"] <= 2


def test_ner_extracts_org_and_rate():
    out = data_analysis.ner(SAMPLE)
    assert "한국은행" in out["entities"]["ORG"]
    assert any("2.50" in r for r in out["entities"]["RATE"])


def test_fre_relation():
    out = data_analysis.fre(SAMPLE)
    assert any(r["subject"] == "한국은행" and r["action"] == "인하" for r in out["relations"])


def test_sa_labels():
    assert research.sa("금리 인하와 공급 확대로 시장 회복 기대")["label"] == "긍정"
    assert research.sa("연체와 부실 위험이 급증하며 시장이 침체")["label"] == "부정"


def test_ec_classifies_rate_event():
    out = research.ec(SAMPLE)
    assert out["primary"] == "금리결정"


def test_tsf_forecast_shape():
    out = research.tsf(horizon=3)
    assert len(out["forecast"]) == 3
    assert all(0 <= v <= 10 for v in out["forecast"])
    assert out["trend"] in ("상승", "하락", "보합")
    # 0.25%p 스텝 반올림 검증
    assert all(abs(v * 4 - round(v * 4)) < 1e-9 for v in out["forecast"])


def test_fraud_danger_case():
    out = risk.fraud_detect(deposit=18000, price=20000, mortgage=3000, trust_registered=True)
    assert out["grade"] == "위험" and out["score"] >= 60
    assert out["actions"]


def test_fraud_safe_case():
    out = risk.fraud_detect(deposit=10000, price=30000)
    assert out["grade"] == "안전"


def test_drp_regulation_boundary():
    out = risk.default_risk(annual_income=3000, existing_annual_payment=0,
                            new_loan=25000, rate_pct=4.0, years=30)
    assert out["dsr_pct"] > 40
    assert out["grade"] in ("규제한도 초과", "고위험")


def test_drp_zero_income_guard():
    assert "error" in risk.default_risk(annual_income=0, existing_annual_payment=0, new_loan=1000)


def test_mac_pipeline_end_to_end():
    result = asyncio.run(mac.run_pipeline(SAMPLE,
                fraud_input={"deposit": 18000, "price": 20000},
                drp_input={"annual_income": 3200, "existing_annual_payment": 0, "new_loan": 15000}))
    assert 0.30 <= result["mac"]["confidence"] <= 0.95
    assert result["mac"]["verdict"]
    assert len(result["audit"]) == 4
    assert "fd" in result["risk"] and "drp" in result["risk"]
