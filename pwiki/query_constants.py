"""Constants shared between query classes"""

from typing import Any, Callable

from .utils import mine_for

class QConstant:

    def __init__(self, name: str, pl: dict = None, limit_key: str = None, retrieve_results: Callable[[dict], Any] = None):
        self.name = name
        self.pl = pl or {}
        self.limit_key = limit_key
        self.retrieve_results = retrieve_results or (lambda l: [e["title"] for e in l])

    def pl_with_limit(self, limit_value="max"):
        pl = {**self.pl}
        if self.limit_key and limit_value:
            pl[self.limit_key] = limit_value

        return pl

class NoContProp:
    EXISTS = QConstant("pageprops", {"ppprop": "missing"}, retrieve_results=lambda r: "missing" not in r)
    PAGE_TEXT = QConstant("revisions", {"rvprop": "content", "rvslots": "main"}, retrieve_results=lambda r: mine_for(r["revisions"][0], "slots", "main", "content"))

class ContProp:
    FILEUSAGE = QConstant("fileusage", limit_key="fulimit")





