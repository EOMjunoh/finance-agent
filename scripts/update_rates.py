# scripts/update_rates.py
"""
한국은행 ECOS Open API에서 기준금리 월별 시계열을 받아 data/base_rate.csv를 갱신합니다.

사용법:
  1. https://ecos.bok.or.kr 에서 무료 인증키 발급
  2. export ECOS_API_KEY=발급키
  3. python scripts/update_rates.py

배포 환경에서는 시작 시 1회 실행하거나 cron으로 매일 갱신하세요.
통계코드 722Y001 / 항목 0101000 = 한국은행 기준금리.
"""
import os, sys, csv, json, pathlib, urllib.request
from datetime import date

ECOS_KEY = os.getenv("ECOS_API_KEY", "")
OUT = pathlib.Path(__file__).parent.parent / "data" / "base_rate.csv"

def main():
    if not ECOS_KEY:
        print("ECOS_API_KEY 미설정 — 기존 샘플 CSV를 유지합니다.")
        return 0

    end = date.today().strftime("%Y%m")
    start_year = date.today().year - 2
    url = (f"https://ecos.bok.or.kr/api/StatisticSearch/{ECOS_KEY}"
           f"/json/kr/1/100/722Y001/M/{start_year}01/{end}/0101000")
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            data = json.load(r)
        rows = data["StatisticSearch"]["row"]
    except Exception as e:
        print(f"ECOS 호출 실패({e}) — 기존 CSV 유지."); return 1

    records = []
    for row in rows:
        t = row["TIME"]                      # YYYYMM
        records.append((f"{t[:4]}-{t[4:]}", float(row["DATA_VALUE"])))
    records = records[-24:]                  # 최근 24개월

    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["month", "rate"])
        w.writerows(records)
    print(f"갱신 완료: {records[0][0]} ~ {records[-1][0]} ({len(records)}개월)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
