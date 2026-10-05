"""미국 원전 사업전략 백데이터가 참조하는 공개 데이터 소스 레지스트리.

각 소스가 어떤 엔티티(유틸리티/주/사업기회)의 어떤 필드를 권위 있게 제공하는지
목록화한다. 실제 수집 로직은 모듈별로 단계적으로 구현하며, 그 전까지 data/*.json 은
공개 자료 기반 수작업 검증 베이스라인으로 유지한다.
"""
from __future__ import annotations

SOURCES = [
    {
        "key": "eia",
        "name": "U.S. EIA (Energy Information Administration)",
        "homepage": "https://www.eia.gov/",
        "api": "https://api.eia.gov/v2/ (open data API, 무료 키)",
        "provides": ["주별 원전 용량·발전량", "플랜트별 net MW(EIA-860)", "전원구성", "전력수요"],
        "live": True,
        "note": "유틸리티 선단 용량·주별 원전 비중의 1차 권위 소스. API 키 필요(무료).",
    },
    {
        "key": "nrc",
        "name": "U.S. NRC (Nuclear Regulatory Commission)",
        "homepage": "https://www.nrc.gov/",
        "api": "운영로 목록·신규/SMR 신청 현황 페이지(HTML/CSV)",
        "provides": ["운영 중 원자로 목록", "건설허가·COL·설계인증", "신규/SMR 인허가 상태"],
        "live": True,
        "note": "인허가 상태(사업기회 deal_certainty)의 1차 소스. 구조화 API는 제한적.",
    },
    {
        "key": "iaea_pris",
        "name": "IAEA PRIS",
        "homepage": "https://pris.iaea.org/",
        "api": "국가별 원자로 상태 DB",
        "provides": ["미국 원자로 운전/건설/정지 상태", "용량", "가동연도"],
        "live": False,
        "note": "국제 교차검증용. 미국 선단 상태 확인.",
    },
    {
        "key": "doe",
        "name": "U.S. DOE / LPO",
        "homepage": "https://www.energy.gov/",
        "api": "보도자료·대출프로그램(LPO) 공고",
        "provides": ["대출보증·ARDP 지원", "AP1000 장기자재 금융", "SMR 지원금"],
        "live": False,
        "note": "financing_policy 차원 근거. 보도자료 기반.",
    },
    {
        "key": "googlenews",
        "name": "Google News (RSS)",
        "homepage": "https://news.google.com/",
        "api": "RSS 검색",
        "provides": ["유틸리티·사업기회 최신 신호(FID·건설허가·EPC계약·offtake)"],
        "live": True,
        "note": "상태 변화 자동 감지의 핵심. 엔티티별 질의로 수집.",
    },
    {
        "key": "wikipedia",
        "name": "Wikipedia REST API",
        "homepage": "https://en.wikipedia.org/",
        "api": "REST summary",
        "provides": ["유틸리티·플랜트 개요", "최종수정일(신선도)"],
        "live": True,
        "note": "교차검증·개요 보강.",
    },
    {
        "key": "wna",
        "name": "World Nuclear Association / World Nuclear News",
        "homepage": "https://world-nuclear.org/",
        "api": "국가 프로파일·뉴스(HTML)",
        "provides": ["미국 원전 현황 서술", "신규·SMR 프로젝트 동향"],
        "live": False,
        "note": "서술형 교차검증.",
    },
    {
        "key": "framework",
        "name": "미-한 원전 프레임워크 / MOTIE / US DOC",
        "homepage": "https://www.motie.go.kr/",
        "api": "정부 발표·보도자료",
        "provides": ["AP1000 6기+APR1400 2기 구성", "한국기업 참여 원칙", "$350B 투자패키지 연계"],
        "live": False,
        "note": "korea_leverage 차원의 핵심 근거. 2026.9.30 프레임워크.",
    },
]


def by_key(key: str) -> dict | None:
    for s in SOURCES:
        if s["key"] == key:
            return s
    return None


def live_sources() -> list[dict]:
    return [s for s in SOURCES if s.get("live")]


if __name__ == "__main__":
    print(f"참조 공개 소스 {len(SOURCES)}개 (라이브 수집 가능 {len(live_sources())}개)\n")
    for s in SOURCES:
        tag = "LIVE" if s.get("live") else "ref "
        print(f"[{tag}] {s['name']}\n       제공: {', '.join(s['provides'])}")
