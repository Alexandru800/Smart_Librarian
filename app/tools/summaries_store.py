import json

from pathlib import Path
from typing import Optional

from app.config import BOOK_SUMMARIES_PATH


class SummariesStore:
    def __init__(self, path: Path | None = None):
        self.path = Path(path or BOOK_SUMMARIES_PATH)
        with self.path.open("r", encoding="utf-8") as f:
            self._records = json.load(f)
        # map normalized title -> record
        self._by_title = {self._norm(r["title"]): r for r in self._records}

    def _norm(self, s: str) -> str:
        return " ".join(s.lower().split())

    def get_summary_by_title(self, title: str) -> Optional[str]:
        rec = self._by_title.get(self._norm(title))
        return rec["summary"] if rec else None

    def titles(self) -> list[str]:
        return [r["title"] for r in self._records]
