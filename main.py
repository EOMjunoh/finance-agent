# main.py — FinAgent MVP 백엔드
import pathlib
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from agents import mac, risk

load_dotenv()
app = FastAPI(title="FinAgent — 금융 멀티에이전트 MVP")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

BASE = pathlib.Path(__file__).parent
SAMPLE_NEWS = (BASE / "data" / "sample_news.txt").read_text(encoding="utf-8")


class PipelineReq(BaseModel):
    text: str | None = None          # 없으면 샘플 뉴스 사용


class FraudReq(BaseModel):
    deposit: int                      # 보증금(만원)
    price: int                        # 매매 시세(만원)
    mortgage: int = 0                 # 선순위 근저당(만원)
    trust_registered: bool = False
    tax_arrears: bool = False
    landlord_multi: bool = False


class DrpReq(BaseModel):
    annual_income: int                # 연소득(만원)
    existing_annual_payment: int = 0  # 기존 연 원리금(만원)
    new_loan: int = 0                 # 신규 대출 원금(만원)
    rate_pct: float = 4.0
    years: int = 30


@app.get("/api/health")
async def health():
    return {"ok": True, "agents": ["DataAnalysis", "InvestmentResearch",
                                    "RiskManagement", "MACOrchestrator"]}


@app.post("/api/pipeline")
async def pipeline(req: PipelineReq):
    text = (req.text or "").strip() or SAMPLE_NEWS
    return await mac.run_pipeline(text)


@app.post("/api/fraud")
async def fraud(req: FraudReq):
    return risk.fraud_detect(**req.model_dump())


@app.post("/api/drp")
async def drp(req: DrpReq):
    return risk.default_risk(**req.model_dump())


app.mount("/legacy", StaticFiles(directory="legacy"), name="legacy")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return FileResponse("static/index.html")
