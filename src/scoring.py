"""미국 원전 사업기회 전략 점수 엔진.

opportunities.json 의 각 사업기회를 strategy_rubric.json 가중치(EPC 우선)에 따라
차원별/종합 점수로 변환한다. 에이전트는 직접 판단하지 않고, 공개 자료에서 매핑된
level(1~5)과 confidence 를 입력으로 받아 결정론적·재현가능하게 점수를 계산한다.
수주 우선순위(발주처 접촉 순서)의 정량 근거를 제공할 뿐, 최종 판단은 사람이 한다.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# level(1~5) -> 0~100 선형 매핑
LEVEL_TO_SCORE = {1: 10.0, 2: 32.5, 3: 55.0, 4: 77.5, 5: 100.0}

# confidence -> 가중치 보정 계수 (신뢰도 낮으면 기여도 할인)
CONFIDENCE_FACTOR = {"high": 1.0, "medium": 0.85, "low": 0.7}


def load_json(name: str) -> dict[str, Any]:
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def score_opportunity(opp: dict, rubric: dict) -> dict:
    """하나의 사업기회에 대해 차원별 점수와 EPC 우선 종합점수를 계산."""
    dims = rubric["dimensions"]  # {key: {weight, label, ...}}
    total_weight = sum(d["weight"] for d in dims.values())

    dim_results: dict[str, dict] = {}
    weighted_sum = 0.0
    conf_weighted_sum = 0.0
    conf_tally = {"high": 0, "medium": 0, "low": 0}

    for key, spec in dims.items():
        entry = opp.get("dimensions", {}).get(key)
        if entry is None:
            continue
        level = int(entry["level"])
        confidence = entry.get("confidence", "low")
        base = LEVEL_TO_SCORE[level]
        weight = spec["weight"]

        weighted_sum += base * weight
        conf_weighted_sum += base * weight * CONFIDENCE_FACTOR[confidence]
        conf_tally[confidence] = conf_tally.get(confidence, 0) + 1

        dim_results[key] = {
            "label": spec["label"],
            "weight": weight,
            "level": level,
            "confidence": confidence,
            "score": round(base, 1),
            "rationale": entry.get("rationale", ""),
        }

    overall = round(weighted_sum / total_weight, 1) if total_weight else 0.0
    overall_conf_adj = round(conf_weighted_sum / total_weight, 1) if total_weight else 0.0

    n = sum(conf_tally.values()) or 1
    if conf_tally["low"] / n >= 0.4:
        data_confidence = "low"
    elif conf_tally["high"] / n >= 0.5:
        data_confidence = "high"
    else:
        data_confidence = "medium"

    return {
        "overall_score": overall,
        "overall_score_confidence_adjusted": overall_conf_adj,
        "data_confidence": data_confidence,
        "dimensions": dim_results,
    }


def evaluate_all() -> dict:
    """전체 사업기회를 평가해 대시보드/리포트용 구조로 반환(점수 내림차순)."""
    rubric = load_json("strategy_rubric.json")
    db = load_json("opportunities.json")

    evaluated = []
    for o in db["opportunities"]:
        result = score_opportunity(o, rubric)
        evaluated.append({**o, "evaluation": result})

    evaluated.sort(key=lambda x: x["evaluation"]["overall_score"], reverse=True)
    for rank, o in enumerate(evaluated, 1):
        o["evaluation"]["rank"] = rank

    return {
        "meta": {
            "rubric_version": rubric["version"],
            "data_version": db["version"],
            "updated": db["updated"],
            "disclaimer": db["disclaimer"],
            "count": len(evaluated),
        },
        "rubric": rubric,
        "opportunities": evaluated,
    }


if __name__ == "__main__":
    out = evaluate_all()
    print(f"전략 평가 완료: {out['meta']['count']}개 사업기회 (rubric v{out['meta']['rubric_version']})")
    print(f"가중치: EPC수주 접근성 최우선\n")
    print(f"{'순위':>3} {'종합':>5} {'보정':>5} {'신뢰':>4}  {'유형':<18} 사업기회")
    print("-" * 92)
    for o in out["opportunities"]:
        ev = o["evaluation"]
        print(
            f"{ev['rank']:>3} {ev['overall_score']:>5} "
            f"{ev['overall_score_confidence_adjusted']:>5} "
            f"[{ev['data_confidence'][:1].upper()}]  {o['type']:<18} {o['title']}"
        )
