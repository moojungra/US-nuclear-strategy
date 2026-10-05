"""U.S. EIA Open Data(v2) 커넥터 — 주별 원전 발전량/설비의 권위 소스.

무료 API 키가 필요하다(환경변수 EIA_API_KEY). 키가 없으면 available()==False 로
우아하게 비활성화되고, data/states.json 의 베이스라인이 그대로 유지된다.
주별 원자력 순발전량(연간)을 수집해 states.json 의 수치를 교차검증하는 용도.

참고: https://www.eia.gov/opendata/  (v2 API, 무료 등록)
"""
from __future__ import annotations

import os
from typing import Any

from .base import SourceConnector

try:
    import requests
    _HAS_REQUESTS = True
except Exception:  # pragma: no cover
    _HAS_REQUESTS = False

# 전력 운영 데이터(발전량) — 연료=원자력(NUC), 전 부문(99)
OPERATIONAL = "https://api.eia.gov/v2/electricity/electric-power-operational-data/data/"
# 소매 판매·요금(주별·부문별) — price 단위 cents/kWh
RETAIL = "https://api.eia.gov/v2/electricity/retail-sales/data/"


class EiaConnector(SourceConnector):
    name = "U.S. EIA"
    homepage = "https://www.eia.gov/opendata/"
    provides = ["nuclear_net_generation_by_state", "capability"]
    note = "주별 원자력 순발전량(연간). 무료 API 키(EIA_API_KEY) 필요."

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("EIA_API_KEY", "")

    def available(self) -> bool:
        return _HAS_REQUESTS and bool(self.api_key)

    def nuclear_generation_by_state(self, year: int | None = None,
                                    timeout: int = 30) -> dict[str, dict[str, Any]]:
        """주별 원자력 순발전량(천 MWh)을 {주코드: {year, value}} 로 반환.

        실패 시 빈 dict. 자동 반영이 아니라 states.json 교차검증용 신호.
        """
        if not self.available():
            return {}
        params = {
            "api_key": self.api_key,
            "frequency": "annual",
            "data[0]": "generation",
            "facets[fueltypeid][]": "NUC",
            "facets[sectorid][]": "99",
            "sort[0][column]": "period",
            "sort[0][direction]": "desc",
            "length": 5000,
        }
        if year:
            params["start"] = str(year)
            params["end"] = str(year)
        try:
            r = requests.get(OPERATIONAL, params=params, timeout=timeout)
            if r.status_code != 200:
                return {}
            rows = r.json().get("response", {}).get("data", [])
        except Exception:
            return {}

        out: dict[str, dict[str, Any]] = {}
        for row in rows:
            loc = row.get("location")           # 주코드(예: 'TX'), 'US' 등
            val = row.get("generation")
            period = row.get("period")
            if not loc or loc in ("US",) or val is None:
                continue
            # 최신 연도만 유지(내림차순 정렬 → 처음 등장한 것이 최신)
            if loc not in out:
                out[loc] = {"year": period, "nuclear_generation_thousand_mwh": val,
                            "units": row.get("generation-units", "thousand MWh")}
        return out

    def retail_price_by_state(self, sectors: tuple[str, ...] = ("RES", "IND"),
                              timeout: int = 30) -> dict[str, dict[str, Any]]:
        """주별·부문별 최신 소매 전기요금(¢/kWh)을 {주코드: {residential, industrial, year}} 로 반환.

        sectors: RES(주택)·COM(상업)·IND(산업). 실패 시 빈 dict(베이스라인 유지).
        """
        if not self.available():
            return {}
        label = {"RES": "residential", "COM": "commercial", "IND": "industrial"}
        params = {
            "api_key": self.api_key,
            "frequency": "annual",
            "data[0]": "price",
            "sort[0][column]": "period",
            "sort[0][direction]": "desc",
            "length": 5000,
        }
        for i, s in enumerate(sectors):
            params[f"facets[sectorid][{i}]"] = s
        try:
            r = requests.get(RETAIL, params=params, timeout=timeout)
            if r.status_code != 200:
                return {}
            rows = r.json().get("response", {}).get("data", [])
        except Exception:
            return {}

        out: dict[str, dict[str, Any]] = {}
        for row in rows:
            loc = row.get("stateid") or row.get("location")
            sector = row.get("sectorid")
            price = row.get("price")
            period = row.get("period")
            if not loc or loc in ("US",) or price is None or sector not in label:
                continue
            rec = out.setdefault(loc, {"year": period})
            key = label[sector]
            if key not in rec:  # 최신 연도 우선
                rec[key] = round(float(price), 2)
        return out


if __name__ == "__main__":
    c = EiaConnector()
    print(f"EIA 사용 가능: {c.available()} (EIA_API_KEY {'설정됨' if c.api_key else '없음'})")
    if c.available():
        data = c.nuclear_generation_by_state()
        print(f"주별 원자력 발전량 {len(data)}개 주 수신")
        for st, d in sorted(data.items(), key=lambda x: -(x[1]['nuclear_generation_thousand_mwh'] or 0))[:10]:
            print(f"  {st}: {d['nuclear_generation_thousand_mwh']} {d['units']} ({d['year']})")
