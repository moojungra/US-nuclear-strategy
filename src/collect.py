"""공개 소스 실수집 오케스트레이터 (미국 원전 사업전략 백데이터).

유틸리티·사업기회별로 Google News 최신 신호를 수집하고, EIA로 주별 원자력 발전량을
교차검증해:
  - data/collected.json        : 대시보드가 라이브로 표시할 신호
  - data/collection_report.md  : 상태 변화 제안 + 큐레이션 불일치 리포트
를 생성한다. 큐레이션된 전략평가(dimension level/confidence)는 덮어쓰지 않는다
('에이전트가 직접 판단'이 아니라 '공개 자료 신호를 수집·제시', 승급은 사람이 한다).

로컬 Python이 없어도 GitHub Actions(러너)가 주기적으로 실행한다.
추가 의존성은 requests 뿐이며, EIA는 EIA_API_KEY 가 있을 때만 활성화된다.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from sources.eia import EiaConnector
from sources.googlenews import GoogleNewsConnector, status_hint
from sources.wikipedia import WikipediaConnector

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# 사업기회 id -> Google News 질의(특정 토큰으로 노이즈 축소). 미지정 시 자동 생성.
OPP_QUERIES: dict[str, str] = {
    "framework-ap1000-6": '"AP1000" (Korea OR Westinghouse) US framework nuclear reactors',
    "framework-apr1400-2": '"APR1400" United States (Korea OR KHNP) reactor',
    "vc-summer-completion": '"V.C. Summer" OR "VC Summer" AP1000 (complete OR restart OR revive)',
    "duke-carolinas-newbuild": '"Duke Energy" (new nuclear OR SMR OR reactor) Carolinas',
    "ny-newbuild-1gw": 'New York (new nuclear OR "advanced nuclear") (reactor OR plant) -SMR',
    "tva-clinch-river-bwrx300": '"Clinch River" "BWRX-300" TVA',
    "tva-entra1-nuscale-6gw": 'TVA (ENTRA1 OR NuScale) nuclear gigawatt',
    "dow-seadrift-xe100": '"Seadrift" OR (Dow "X-energy") Xe-100 reactor',
    "energy-northwest-xe100": '"Energy Northwest" "X-energy" OR Xe-100 reactor Washington',
    "natrium-kemmerer": '"Natrium" (TerraPower OR Kemmerer) reactor -stock',
    "holtec-smr300-palisades": '"SMR-300" Holtec Palisades',
    "north-anna-smr": '"North Anna" SMR Dominion reactor',
    "palisades-restart": '"Palisades" restart Holtec reactor',
    "crane-restart": '"Crane Clean Energy" OR (Three Mile Island restart) Constellation',
    "duane-arnold-restart": '"Duane Arnold" restart NextEra reactor',
}

# 유틸리티 id -> Wikipedia 제목(개요 보강). 미지정 시 생략.
UTIL_WIKI: dict[str, str] = {
    "constellation": "Constellation Energy", "vistra": "Vistra",
    "southern": "Southern Company", "duke": "Duke Energy", "tva": "Tennessee Valley Authority",
    "dominion": "Dominion Energy", "nextera": "NextEra Energy", "entergy": "Entergy",
    "xcel": "Xcel Energy", "pseg": "Public Service Enterprise Group",
    "energy-northwest": "Energy Northwest", "talen": "Talen Energy",
    "aps": "Arizona Public Service", "pge-ca": "Pacific Gas and Electric Company",
    "ameren": "Ameren", "evergy": "Evergy", "holtec": "Holtec International", "dte": "DTE Energy",
}


def opp_query(opp: dict) -> str:
    if opp["id"] in OPP_QUERIES:
        return OPP_QUERIES[opp["id"]]
    bits = []
    if opp.get("site") and "미정" not in opp["site"]:
        bits.append(f'"{opp["site"]}"')
    if opp.get("technology") and "미정" not in opp["technology"]:
        bits.append(f'"{opp["technology"]}"')
    bits.append("nuclear reactor")
    return " ".join(bits)


def util_query(util: dict) -> str:
    return f'"{util["name"].split("(")[0].strip()}" nuclear (SMR OR reactor OR restart OR "data center" OR uprate)'


def curated_levels(opp: dict) -> dict[str, int]:
    return {k: v["level"] for k, v in opp.get("dimensions", {}).items()}


def main(delay: float = 0.8) -> None:
    utilities = json.loads((DATA / "utilities.json").read_text(encoding="utf-8"))
    states = json.loads((DATA / "states.json").read_text(encoding="utf-8"))
    opps = json.loads((DATA / "opportunities.json").read_text(encoding="utf-8"))

    news = GoogleNewsConnector()
    wiki = WikipediaConnector()
    eia = EiaConnector()
    print(f"수집 시작 · GoogleNews={news.available()} · Wikipedia={wiki.available()} · EIA={eia.available()}")
    print(f"  유틸리티 {len(utilities['utilities'])} · 주 {len(states['states'])} · 사업기회 {len(opps['opportunities'])}")

    collected_opps: dict[str, dict] = {}
    collected_utils: dict[str, dict] = {}
    flags: list[str] = []
    report: list[str] = []

    # --- 사업기회 신호 수집 ---
    report.append("## 사업기회별 최신 신호\n")
    for o in opps["opportunities"]:
        q = opp_query(o)
        items = news.search(q, limit=6)
        time.sleep(delay)
        hint = status_hint(items)
        collected_opps[o["id"]] = {
            "news": [{k: it[k] for k in ("title", "source", "date", "url")} for it in items[:5]],
            "status_hint": hint,
        }
        top = items[0]["title"] if items else "(뉴스 없음)"
        top_date = items[0]["date"] if items else "—"
        report.append(f"### {o['title']}  \n- 최신: {top_date} · {top}")
        if hint:
            report.append(f"- 신호: **{hint['label']}** → {hint['dimension']} 제안 Lv{hint['suggested_level']} "
                          f"(근거: {hint['evidence']})")
            cur = curated_levels(o).get(hint["dimension"])
            if cur is not None and hint["suggested_level"] > cur:
                msg = (f"⚠ {o['title']}: {hint['dimension']} 큐레이션 Lv{cur} < 수집신호 "
                       f"Lv{hint['suggested_level']} — 검토 필요 ({hint['label']})")
                flags.append(msg)
                report.append(f"- {msg}")
        report.append("")
        print(f"  · OPP {o['id']:<26} 뉴스 {len(items)}건" + (f" · {hint['label']}" if hint else ""))

    # --- 유틸리티 신호 수집 ---
    report.append("## 유틸리티별 최신 신호\n")
    for u in utilities["utilities"]:
        items = news.search(util_query(u), limit=5)
        time.sleep(delay)
        w = wiki.summary(UTIL_WIKI[u["id"]]) if u["id"] in UTIL_WIKI else None
        time.sleep(delay if w else 0)
        collected_utils[u["id"]] = {
            "news": [{k: it[k] for k in ("title", "source", "date", "url")} for it in items[:4]],
            "wiki": w,
        }
        top = items[0]["title"] if items else "(뉴스 없음)"
        report.append(f"### {u['name']} ({u.get('ticker','')})  \n- 최신: {items[0]['date'] if items else '—'} · {top}")
        report.append("")
        print(f"  · UTL {u['id']:<16} 뉴스 {len(items)}건")

    # --- EIA 주별 원자력 발전량 교차검증(키 있을 때만) ---
    eia_cross = {}
    if eia.available():
        gen = eia.nuclear_generation_by_state()
        state_ids = {s["id"] for s in states["states"]}
        eia_cross = {k: v for k, v in gen.items() if k in state_ids}
        print(f"  EIA 주별 원자력 발전량 {len(eia_cross)}개 주 교차검증 수신")

    out = {
        "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "opportunities": collected_opps,
        "utilities": collected_utils,
        "eia_nuclear_generation_by_state": eia_cross,
        "review_flags": flags,
    }
    (DATA / "collected.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    header = [
        "# 미국 원전 사업전략 수집 리포트",
        f"수집 시각: {out['collected_at']}",
        "",
        f"## 검토 필요 — 상태 변화 감지 ({len(flags)}건)",
        "",
    ]
    header += [f"- {m}" for m in flags] if flags else ["- (없음) 큐레이션 상태와 수집 신호 일치"]
    header += ["", "---", ""]
    (DATA / "collection_report.md").write_text("\n".join(header + report), encoding="utf-8")

    print(f"\n완료 → data/collected.json, data/collection_report.md")
    print(f"상태변화 검토 {len(flags)}건")
    for m in flags:
        print("  " + m)


if __name__ == "__main__":
    main()
