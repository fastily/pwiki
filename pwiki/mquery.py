"""Mass/Bulk query methods and classes designed to fetch as many results as possible in the fewest round trips"""

from __future__ import annotations

import logging

from typing import TYPE_CHECKING

from .query_constants import PropCont, PropNoCont, QConstant
from .query_utils import basic_query, chunker, get_continue_params
from .utils import has_error, mine_for, read_error

if TYPE_CHECKING:
    from .wiki import Wiki

log = logging.getLogger(__name__)


class MQuery:

    @staticmethod
    def prop_no_cont(wiki: Wiki, titles: list[str], template: QConstant) -> dict:

        out = dict.fromkeys(titles)

        for chunk in chunker(titles, 50):
            if not (response := basic_query(wiki, {**template.pl, "prop": template.name, "titles": "|".join(chunk)})):
                log.error("%s: No response from server while performing a prop_no_cont query with prop '%s' and titles %s", wiki, template.name, chunk)
                continue

            if has_error(response):
                log.error("%s: encountered error while performing prop_no_cont, server said: %s", wiki, read_error("query", response))
                log.debug(response)
                continue

            for p in mine_for(response, "query", "pages"):
                try:
                    out[p["title"]] = template.retrieve_results(p)
                except Exception:
                    log.debug("%s: Unable able to parse prop value from: %s", wiki, p, exc_info=True)

        return out

    @staticmethod
    def prop_cont(wiki: Wiki, titles: list[str], template: QConstant) -> dict:

        out = {t: [] for t in titles}

        for chunk in chunker(titles, 50):
            params = {**template.pl_with_limit(), "prop": template.name, "titles": "|".join(chunk)}

            while True:
                if not (response := basic_query(wiki, params)):
                    log.error("%s: No response from server while performing a prop_cont query with prop '%s' and titles %s", wiki, template.name, chunk)
                    break

                if has_error(response):
                    log.error("%s: encountered error while performing prop_cont, server said: %s", wiki, read_error("query", response))
                    log.debug(response)
                    break

                for p in mine_for(response, "query", "pages"):
                    if template.name in p:
                        try:
                            out[p["title"]] += template.retrieve_results(p[template.name])
                        except Exception:
                            log.debug("%s: Unable able to parse prop value from: %s", wiki, p, exc_info=True)

                if not (cont := get_continue_params(response)):
                    break

                params.update(cont)

        return out

    # PROP NO CONT

    @staticmethod
    def page_text(wiki: Wiki, titles: list[str]) -> dict:
        """Queries the Wiki for the text of a title.

        Args:
            wiki (Wiki): The Wiki object to use.
            titles (list[str]): The titles to query.

        Returns:
            dict: A `dict` where each key is the title and each value is a `str` with the wikitext of the title.  If a title does not exist, the str will be replaced with `None`.
        """
        log.debug("%s: fetching page text for %s", wiki, titles)
        return MQuery.prop_no_cont(wiki, titles, PropNoCont.PAGE_TEXT)

    @staticmethod
    def exists(wiki: Wiki, titles: list[str]) -> dict:
        """Queries the Wiki to determine if the specified list of titles exists.

        Args:
            wiki (Wiki): The Wiki object to use.
            titles (list[str]): The titles to query.

        Returns:
            dict: A `dict` where each key is a title and each value is a bool indiciating if the title exists (`True`) or not (`False`).
        """
        log.debug("%s: determining if pages exist: %s", wiki, titles)
        return MQuery.prop_no_cont(wiki, titles, PropNoCont.EXISTS)

    @staticmethod
    def category_size(wiki: Wiki, titles: list[str]) -> dict:
        log.debug("%s: fetching category sizes for: %s", wiki, titles)
        return MQuery.prop_no_cont(wiki, titles, PropNoCont.CATEGORY_SIZE)

    # PROP CONT

    @staticmethod
    def file_usage(wiki: Wiki, titles: list[str]) -> dict:
        log.debug("%s: fetching file usage: %s", wiki, titles)
        return MQuery.prop_cont(wiki, titles, PropCont.FILEUSAGE)

    @staticmethod
    def categories_on_page(wiki: Wiki, titles: list[str]) -> dict:
        log.debug("%s: fetching categories on pages: %s", wiki, titles)
        return MQuery.prop_cont(wiki, titles, PropCont.CATEGORIES)
