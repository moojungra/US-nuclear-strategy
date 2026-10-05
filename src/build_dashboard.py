"""전략 평가 결과 + 3축 데이터 + 소스 메타를 대시보드가 읽는 data.js 로 내보낸다.

산출물: dashboard/data.js  ->  `window.USNS_DATA = {...}`
dashboard/index.html 이 이 파일을 로드해 렌더링한다(로컬 file:// 에서도 동작).
data.js 가 없으면 index.html 내장 베이스라인으로 단독 동작한다.
"""
from __future__ import annotations

import json
from pathlib import Path

from scoring import evaluate_all
from sources.registry import SOURCES

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "dashboard" / "data.js"


def build() -> dict:
    data = evaluate_all()  # {meta, rubric, opportunities(점수포함)}
    data["sources"] = SOURCES
    data["utilities"] = json.loads((DATA / "utilities.json").read_text(encoding="utf-8")).get("utilities", [])
    data["states"] = json.loads((DATA / "states.json").read_text(encoding="utf-8")).get("states", [])

    # 라이브 수집 신호(collect.py 산출물)를 병합
    collected_path = DATA / "collected.json"
    if collected_path.exists():
        col = json.loads(collected_path.read_text(encoding="utf-8"))
        data["collected_at"] = col.get("collected_at")
        data["review_flags"] = col.get("review_flags", [])
        live_opp = col.get("opportunities", {})
        for o in data["opportunities"]:
            if o["id"] in live_opp:
                o["live"] = live_opp[o["id"]]
        live_util = col.get("utilities", {})
        for u in data["utilities"]:
            if u["id"] in live_util:
                u["live"] = live_util[u["id"]]
        eia = col.get("eia_nuclear_generation_by_state", {})
        for s in data["states"]:
            if s["id"] in eia:
                s["eia"] = eia[s["id"]]
    return data


def main() -> None:
    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    OUT.write_text(f"window.USNS_DATA = {payload};\n", encoding="utf-8")
    print(f"대시보드 데이터 생성: {OUT}")
    print(f"  사업기회 {data['meta']['count']}개 · 유틸리티 {len(data['utilities'])}개 · "
          f"주 {len(data['states'])}개 · 소스 {len(data['sources'])}개")


if __name__ == "__main__":
    main()
