"""Sane object wrappers for data returned by the API"""

from datetime import datetime

from .utils import mine_for


class DataEntry:
    def __init__(self, user: str, title: str, summary: str, timestamp: str) -> None:
        self.user = user
        self.title = title
        self.summary = summary
        self.timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00")) if timestamp else None

    def __repr__(self) -> str:
        return f"User: {self.user} | Title: {self.title} | Summary: {self.summary} | Timestamp: {self.timestamp}"


class Revision(DataEntry):
    def __init__(self, title, rev: dict) -> None:
        super().__init__(rev.get("user"), title, rev.get("comment"), rev.get("timestamp"))

        self.text = mine_for(rev, "slots", "main", "content")
