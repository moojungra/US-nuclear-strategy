"""U.S. NRC 커넥터 — 신규/SMR 인허가 상태의 1차 소스(참조 계층).

NRC는 운영로 목록·신규 및 SMR 인허가 신청 현황을 공개 페이지로 제공하나,
깨끗한 구조화 API가 없어(대부분 HTML/문서) 자동 수집은 단계적으로 추가한다.
현재는 참조 URL과, 사업기회(opportunities.json)의 deal_certainty 를 교차검증할
수 있는 '상태 라벨' 매핑을 제공한다.
"""
from __future__ import annotations

from .base import SourceConnector

# NRC 공개 페이지(사람이 확인·수집하는 1차 소스)
PAGES = {
    "operating_reactors": "https://www.nrc.gov/reactors/operating/list-power-reactor-units.html",
    "new_reactors": "https://www.nrc.gov/reactors/new-reactors.html",
    "smr": "https://www.nrc.gov/reactors/new-reactors/advanced.html",
    "col": "https://www.nrc.gov/reactors/new-reactors/large-lwr/col.html",
}

# NRC 인허가 단계 -> 사업기회 deal_certainty 제안(1~5). 자동 반영 아님(검토용).
LICENSING_STAGE_TO_CERTAINTY = {
    "operating": 5,
    "construction permit issued": 5,
    "col issued": 5,
    "under construction": 5,
    "application under review": 4,
    "docketed": 4,
    "design certification": 4,
    "pre-application": 3,
    "letter of intent": 2,
    "early site permit": 3,
}


class NrcConnector(SourceConnector):
    name = "U.S. NRC"
    homepage = "https://www.nrc.gov/"
    provides = ["licensing_status", "operating_reactor_list"]
    note = "인허가 상태 1차 소스. 구조화 API 제한 → 현재는 참조 URL 제공."

    def available(self) -> bool:
        return False  # 구조화 수집 미구현(참조 계층)

    def reference_pages(self) -> dict[str, str]:
        return dict(PAGES)

    @staticmethod
    def certainty_from_stage(stage: str) -> int | None:
        return LICENSING_STAGE_TO_CERTAINTY.get(stage.strip().lower())


if __name__ == "__main__":
    c = NrcConnector()
    print("NRC 참조 페이지:")
    for k, v in c.reference_pages().items():
        print(f"  {k}: {v}")
