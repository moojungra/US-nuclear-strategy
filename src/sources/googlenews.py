"""Google News 커넥터 — 유틸리티·사업기회별 최신 신호(상태 변화)를 RSS로 수집.

공개 엔드포인트: https://news.google.com/rss/search?q=<query>&hl=en-US&gl=US&ceid=US:en
사업전략 백데이터에서 '상태 변화'(FID·건설허가·EPC 계약·데이터센터 offtake 등)는
시간에 따라 바뀌므로 자동 수집의 핵심 대상이다. feedparser 없이 표준 xml 파서만 사용.
"""
from __future__ import annotations

import html
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import timezone
from email.utils import parsedate_to_datetime
from typing import Any

from .base import SourceConnector

try:
    import requests
    _HAS_REQUESTS = True
except Exception:  # pragma: no cover
    _HAS_REQUESTS = False

UA = "US-Nuclear-Strategy-Agent/0.1 (public research)"
RSS = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"

# 뉴스 제목의 키워드 -> (전략 차원, 제안 성숙도, 라벨)
# 사업기회의 deal_certainty / epc_accessibility / financing_policy 신호를 감지.
STATUS_KEYWORDS: list[tuple[tuple[str, ...], str, int, str]] = [
    (("epc contract", "engineering procurement", "awarded contract", "construction contract",
      "selected as contractor", "epc consortium"), "epc_accessibility", 5, "EPC 계약/수주"),
    (("final investment decision", " fid ", "greenlight", "approves construction",
      "board approval", "sanctioned"), "deal_certainty", 5, "FID/착공결정"),
    (("construction permit", "begins construction", "starts construction", "first concrete",
      "breaks ground", "groundbreaking", "construction license"), "deal_certainty", 5, "건설허가/착공"),
    (("construction permit application", "license application", "docketed", "nrc review",
      "safety review", "early site permit"), "deal_certainty", 4, "인허가 심사"),
    (("power purchase", "offtake", "data center", "ppa", "hyperscaler"),
     "financing_policy", 4, "offtake/데이터센터"),
    (("doe loan", "loan guarantee", "conditional commitment", "ardp", "doe award",
      "federal loan"), "financing_policy", 5, "DOE 금융지원"),
    (("restart", "recommission", "return to service", "reopen"), "deal_certainty", 4, "재가동"),
    (("memorandum of understanding", " mou ", "framework", "feasibility", "letter of intent"),
     "deal_certainty", 2, "MOU/타당성"),
]


class GoogleNewsConnector(SourceConnector):
    name = "Google News"
    homepage = "https://news.google.com/"
    provides = ["latest_signal", "milestones"]
    note = "RSS 검색 — 유틸리티·사업기회별 인허가·EPC·offtake 최신 신호."

    def available(self) -> bool:
        return _HAS_REQUESTS

    def search(self, query: str, limit: int = 6, timeout: int = 15) -> list[dict[str, Any]]:
        """질의에 대한 최신 기사 목록(최신순)."""
        if not _HAS_REQUESTS or not query:
            return []
        url = RSS.format(q=urllib.parse.quote(query))
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
            if r.status_code != 200:
                return []
            root = ET.fromstring(r.content)
        except Exception:
            return []

        items: list[dict[str, Any]] = []
        for it in root.iterfind(".//item"):
            title = (it.findtext("title") or "").strip()
            link = (it.findtext("link") or "").strip()
            pub = it.findtext("pubDate")
            src_el = it.find("source")
            source = (src_el.text if src_el is not None else "") or ""
            iso, ts = None, 0.0
            if pub:
                try:
                    dt = parsedate_to_datetime(pub)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    iso = dt.astimezone(timezone.utc).strftime("%Y-%m-%d")
                    ts = dt.timestamp()
                except Exception:
                    pass
            items.append({"title": html.unescape(title), "source": html.unescape(source),
                          "date": iso, "_ts": ts, "url": link})

        items.sort(key=lambda x: x["_ts"], reverse=True)
        return items[:limit]


def status_hint(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    """최신 기사들에서 가장 진전된 상태 신호를 추출(제안용, 자동 반영 아님)."""
    best = None
    for it in items:
        t = f" {it['title'].lower()} "
        for keys, dim, level, label in STATUS_KEYWORDS:
            if any(k in t for k in keys):
                cand = {"dimension": dim, "suggested_level": level, "label": label,
                        "evidence": it["title"], "date": it.get("date"), "url": it["url"]}
                if best is None or level > best["suggested_level"]:
                    best = cand
                break
    return best
