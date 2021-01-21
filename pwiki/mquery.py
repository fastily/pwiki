"""Mass/Bulk query methods and classes"""

from __future__ import annotations

import logging

from typing import Any, Callable, TYPE_CHECKING

from .query_utils import basic_query, chunker
from .utils import has_error, mine_for, read_error

if TYPE_CHECKING:
    from .wiki import Wiki

log = logging.getLogger(__name__)


class MQuery:

    @staticmethod
    def prop_no_cont(wiki: Wiki, prop: str, pl: dict, titles: list[str], retrieve_value: Callable[[dict], Any]) -> dict:

        out = dict.fromkeys(titles)

        for chunk in chunker(titles, 50):
            if not (response := basic_query(wiki, {**pl, "prop": prop, "titles": "|".join(chunk)})):
                continue

            if has_error(response):
                log.error("%s: encountered error while performing prop_no_cont, server said: %s", wiki, read_error("query", response))
                log.debug(response)
                continue

            for p in mine_for(response, "query", "pages"):
                try:
                    out[p["title"]] = retrieve_value(p)
                except Exception:
                    log.debug("%s: Unable able to parse prop value from: %s", wiki, p, exc_info=True)

        return out

    def prop_cont(wiki: Wiki, prop: str, pl: dict, titles: list[str], retrieve_value: Callable[[dict], Any]):
        pass

    @staticmethod
    def page_text(wiki: Wiki, titles: list[str]) -> dict:
        log.info("%s: fetching page text for %s", wiki, titles)
        return MQuery.prop_no_cont(wiki, "revisions", {"rvprop": "content", "rvslots": "main"}, titles, lambda r: mine_for(r["revisions"][0], "slots", "main", "content"))
