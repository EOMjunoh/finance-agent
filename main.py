# main.py — FinAgent MVP 백엔드
import asyncio, pathlib
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from agents import mac, risk, live_rate, news_feed

load_dotenv()
app = FastAPI(title="FinAgent — 금융 멀티에이전트 MVP")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

BASE = pathlib.Path(__file__).parent
SAMPLE_NEWS = (BASE / "data" / "sample_news.txt").read_text(encoding="utf-8")


def _sanitize(text: str) -> str:
    """깨진 서로게이트 문자(예: 잘린 이모지, IME 조합 중 유실)가 섞여 들어오면
    JSON 응답 인코딩(UnicodeEncodeError)이 실패하므로 안전하게 치환한다."""
    return text.encode("utf-8", "replace").decode("utf-8")


@app.on_event("startup")
async def _startup():
    await asyncio.to_thread(live_rate.refresh, True)   # 기동 시 1회 즉시 갱신

    async def _loop():
        while True:
            await asyncio.sleep(live_rate.REFRESH_SEC)
            await asyncio.to_thread(live_rate.refresh, True)

    asyncio.create_task(_loop())


class PipelineReq(BaseModel):
    text: str | None = None          # 없으면 샘플 뉴스 사용


class NewsItemReq(BaseModel):
    text: str


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
    text = _sanitize((req.text or "").strip()) or SAMPLE_NEWS
    return await mac.run_pipeline(text)


@app.post("/api/fraud")
async def fraud(req: FraudReq):
    return risk.fraud_detect(**req.model_dump())


@app.post("/api/drp")
async def drp(req: DrpReq):
    return risk.default_risk(**req.model_dump())


@app.get("/api/rate/live")
async def rate_live():
    return live_rate.status()


@app.get("/api/news/feed")
async def get_feed(after_id: int = 0):
    items = news_feed.list_since(after_id)
    return {"items": items, "latest_id": news_feed.latest_id()}


@app.post("/api/news/feed")
async def post_feed(req: NewsItemReq):
    try:
        return news_feed.add(_sanitize(req.text))
    except ValueError:
        return {"error": "빈 텍스트는 추가할 수 없습니다."}


app.mount("/legacy", StaticFiles(directory="legacy"), name="legacy")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return FileResponse("static/index.html", headers={"Cache-Control": "no-store"})
