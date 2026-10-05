"""Wikipedia REST 커넥터 — 유틸리티·플랜트 개요와 최종수정일(신선도).

공개 엔드포인트: https://en.wikipedia.org/api/rest_v1/page/summary/<title>
교차검증·개요 보강용. 자격증명 불필요.
"""
from __future__ import annotations

import urllib.parse
from typing import Any

from .base import SourceConnector

try:
    import requests
    _HAS_REQUESTS = True
except Exception:  # pragma: no cover
    _HAS_REQUESTS = False

UA = "US-Nuclear-Strategy-Agent/0.1 (public research)"
SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"


class WikipediaConnector(SourceConnector):
    name = "Wikipedia"
    homepage = "https://en.wikipedia.org/"
    provides = ["summary", "last_modified"]
    note = "유틸리티·플랜트 개요와 최종수정일(신선도)."

    def available(self) -> bool:
        return _HAS_REQUESTS

    def summary(self, title: str, timeout: int = 15) -> dict[str, Any] | None:
        if not _HAS_REQUESTS or not title:
            return None
        url = SUMMARY.format(title=urllib.parse.quote(title.replace(" ", "_")))
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
            if r.status_code != 200:
                return None
            j = r.json()
        except Exception:
            return None
        return {
            "title": j.get("title"),
            "extract": j.get("extract"),
            "last_modified": (j.get("timestamp") or "")[:10],
            "url": j.get("content_urls", {}).get("desktop", {}).get("page"),
        }
