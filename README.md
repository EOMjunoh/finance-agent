# FinAgent — 금융 멀티에이전트 MVP

논문의 금융 에이전트 프레임워크(Data Analysis · Investment Research · Risk Management · MAC)를
**API 키 없이도 완전히 동작**하는 형태로 구현한 배포용 MVP입니다.
청년 주거 금융 도메인(전세사기·DSR·금리)에 특화되어 있습니다.

## 데모 화면
`/` — 대시보드: 파이프라인 실행 → 뉴스 인사이트 · 시장 분석 · MAC 통합 판단 · 리스크 도구
`/legacy/bizpartner.html` — 기존 사장님 파트너 데모 (보존)

## 아키텍처

```
사용자 텍스트(뉴스·공시)
        │
        ▼
┌─────────────────────────────────────────────┐
│              MAC Orchestrator                │
│   병렬 실행 → 교차 검증(Verbal Reinforcement) │
│   → 충돌 감지 → 신뢰도 산정 → 통합 판단        │
└──────┬───────────────┬───────────────┬──────┘
       ▼               ▼               ▼
 Data Analysis   Investment Res.   Risk Mgmt
  TS 요약          SA 감성분석       FD 전세사기
  NER 개체추출     EC 이벤트분류     DRP 부채(DSR)
  FRE 관계추출     TSF 금리예측
```

| 에이전트 | 태스크 | 구현 방식 (키 없음) | LLM 모드 |
|---|---|---|---|
| DataAnalysisAgent | TS · NER · FRE | 빈도 추출요약 · 금융사전+정규식 · 패턴 관계추출 | OPENAI_API_KEY 시 생성요약 |
| InvestmentResearchAgent | SA · EC · TSF | 감성사전 · 키워드 분류 · 12개월 선형회귀 | — |
| RiskManagementAgent | FD · DRP | 깡통전세 룰 스코어링 · DSR 계산 | — |
| MACOrchestrator | 협업 조율 | 교차 검증으로 신뢰도 가감 + 충돌 언어화 | — |

## 빠른 시작

```bash
pip install -r requirements.txt
uvicorn main:app --reload
# http://127.0.0.1:8000
```

## API

| Method | Path | 설명 |
|---|---|---|
| GET  | /api/health   | 에이전트 상태 |
| POST | /api/pipeline | `{"text": "뉴스 본문"}` — 비우면 샘플 기사. MAC 전체 파이프라인 |
| POST | /api/fraud    | 전세사기 위험 진단 (보증금·시세·근저당·신탁·체납) |
| POST | /api/drp      | DSR 부채 리스크 (연소득·기존상환·신규대출·금리) |

## 배포 (Render 무료 티어)

1. 이 저장소를 GitHub에 push
2. render.com → New → Web Service → 저장소 연결
3. Build: `pip install -r requirements.txt`
   Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. (선택) 환경변수 `OPENAI_API_KEY` 등록 → TS가 생성 요약으로 업그레이드

Railway·Fly.io 동일 구조 (Procfile 포함).

## 확장 로드맵 (MVP 이후)
- Trading Agent: 증권사 OpenAPI 연동 후 전략 실행 — 실계좌·규제 이슈로 MVP 제외
- Investment Manager Agent: 포트폴리오 최적화 QA — 별도 데이터셋 필요
- TSF 고도화: Prophet/ARIMA + 한국은행 ECOS API 실시간 연동
- MAC 고도화: LangGraph 그래프 + LLM 기반 에이전트 간 토론(debate) 루프

## 면책
모든 점수·예측·판단은 데모용 규칙·통계 모델의 출력이며 투자·계약 의사결정의
근거가 될 수 없습니다. 기준금리 데이터는 샘플이므로 실서비스 전 교체하세요.
클라이언트 코드에 API 키를 넣지 마세요 — 서버 환경변수로만 관리합니다.

## 품질 · 운영
- `tests/` — 11개 pytest (TS·NER·FRE·SA·EC·TSF·FD·DRP·MAC E2E). `python -m pytest tests/ -q`
- `.github/workflows/ci.yml` — push 시 자동 테스트
- `Dockerfile` — `docker build -t finagent . && docker run -p 8000:8000 finagent`
- `scripts/update_rates.py` — ECOS_API_KEY 설정 시 시작 때 기준금리 최근 24개월 자동 갱신 (render.yaml에 반영됨)
