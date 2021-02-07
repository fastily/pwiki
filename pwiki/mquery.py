"""Mass/Bulk query methods and classes designed to fetch as many results as possible in the fewest round trips"""

from __future__ import annotations

import logging

from collections import defaultdict
from typing import TYPE_CHECKING

from .query_constants import PropCont, PropNoCont, QConstant
from .query_utils import chunker, denormalize_result, get_continue_params, query_and_validate
from .utils import mine_for

if TYPE_CHECKING:
    from .wiki import Wiki

log = logging.getLogger(__name__)


class MQuery:
    """Collection of queries optimized for performing mass/bulk data retrieval from the API"""

    @staticmethod
    def prop_no_cont(wiki: Wiki, titles: list[str], template: QConstant) -> dict:

        out = dict.fromkeys(titles)

        for chunk in chunker(titles, wiki.prop_title_max):
            if response := query_and_validate(wiki, {**template.pl, "prop": template.name, "titles": "|".join(chunk)}, desc=f"peform a prop_no_cont query with '{template.name}'"):
                for p in mine_for(response, "query", "pages"):
                    try:
                        out[p["title"]] = template.retrieve_results(p)
                    except Exception:
                        log.debug("%s: Unable able to parse prop value from: %s", wiki, p, exc_info=True)

                denormalize_result(out, response)

        return out

    @staticmethod
    def prop_cont(wiki: Wiki, titles: list[str], template: QConstant) -> dict:
        out = defaultdict(list)

        for chunk in chunker(titles, wiki.prop_title_max):
            params = {**template.pl_with_limit(), "prop": template.name, "titles": "|".join(chunk)}

            while True:
                if not (response := query_and_validate(wiki, params, desc=f"peform a prop_cont query with '{template.name}'")):
                    break

                for p in mine_for(response, "query", "pages"):
                    try:
                        out[p["title"]] += template.retrieve_results(p[template.name]) if template.name in p else []
                    except Exception:
                        log.debug("%s: Unable able to parse prop value from: %s", wiki, p, exc_info=True)

                denormalize_result(out, response, list)

                if not (cont := get_continue_params(response)):
                    break

                params.update(cont)

        out |= {t: None for t in titles if t not in out}
        return dict(out)

    ##################################################################################################
    ######################################### P R O P  N O  C O N T ##################################
    ##################################################################################################

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

    ##################################################################################################
    ########################################## P R O P  C O N T ######################################
    ##################################################################################################

    @staticmethod
    def file_usage(wiki: Wiki, titles: list[str]) -> dict:
        log.debug("%s: fetching file usage: %s", wiki, titles)
        return MQuery.prop_cont(wiki, titles, PropCont.FILEUSAGE)

    @staticmethod
    def categories_on_page(wiki: Wiki, titles: list[str]) -> dict:
        log.debug("%s: fetching categories on pages: %s", wiki, titles)
        return MQuery.prop_cont(wiki, titles, PropCont.CATEGORIES)
