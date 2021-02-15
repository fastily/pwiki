"""Mass/Bulk query methods and classes designed to fetch as many results as possible in the fewest round trips"""

from __future__ import annotations

import logging

from collections import defaultdict
from typing import TYPE_CHECKING, Union

from .ns import NS
from .query_constants import PropCont, PropNoCont, QConstant
from .query_utils import chunker, denormalize_result, get_continue_params, query_and_validate
from .utils import mine_for

if TYPE_CHECKING:
    from .wiki import Wiki

log = logging.getLogger(__name__)


class MQuery:
    """Collection of queries optimized for performing mass/bulk data retrieval from the API"""

    @staticmethod
    def _prop_no_cont(wiki: Wiki, titles: list[str], template: QConstant) -> dict:
        """Performs a prop query and does not do any query continuation.  Use this for fetching page properties that are one-off in nature.

        Args:
            wiki (Wiki): The Wiki object to use.
            titles (list[str]): The titles to work on.
            template (QConstant): The QConstant to use.

        Returns:
            dict: A dict where each key is a title and the value is the corresponding value that was retrieved from the server.  A `None` value means something probably went wrong server side.
        """
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
    def _prop_cont(wiki: Wiki, titles: list[str], template: QConstant, extra_pl: dict = None) -> dict:
        """Performs a prop query with query continuation.  Use this for fetching page properties that take the form of a list.  All available values will be fetched.

        Args:
            wiki (Wiki): The Wiki object to use.
            titles (list[str]): The titles to work on.
            template (QConstant): The QConstant to use.
            extra_pl (dict, optional): Extra parameters to the passed along with the request.  Useful for queries that accept optional configuration. Defaults to None.

        Returns:
            dict: A dict where each key is a title and the value is the corresponding list of values for this title that were retrieved from the server.  A `None` value means something probably went wrong server side.
        """
        out = {t: [] for t in titles}
        # out = defaultdict(list)

        for chunk in chunker(titles, wiki.prop_title_max):
            params = {**template.pl_with_limit(), "prop": template.name, "titles": "|".join(chunk)} | (extra_pl or {})

            while response := query_and_validate(wiki, params, desc=f"peform a prop_cont query with '{template.name}'"):
                for p in mine_for(response, "query", "pages"):
                    try:
                        out[p["title"]] += template.retrieve_results(p[template.name]) if template.name in p else []
                    except Exception:
                        log.debug("%s: Unable able to parse prop value from: %s", wiki, p, exc_info=True)
                        return dict.fromkeys(titles)

                denormalize_result(out, response, list)

                if not (cont := get_continue_params(response)):
                    break

                params.update(cont)

        return dict(out) | {t: None for t in titles if t not in out}

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
        return MQuery._prop_no_cont(wiki, titles, PropNoCont.PAGE_TEXT)

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
        return MQuery._prop_no_cont(wiki, titles, PropNoCont.EXISTS)

    @staticmethod
    def category_size(wiki: Wiki, titles: list[str]) -> dict:
        """Queries the Wiki and gets the number of elements categorized in each of the specified categories.

        Args:
            wiki (Wiki): The Wiki object to use.
            titles (list[str]): The categories to get the size of.  Each list element must include the `Category:` prefix

        Returns:
            dict: A dict where each key is the category name and each value is an `int` representing the number of elements categorized in this category.
        """
        log.debug("%s: fetching category sizes for: %s", wiki, titles)
        return MQuery._prop_no_cont(wiki, titles, PropNoCont.CATEGORY_SIZE)

    ##################################################################################################
    ########################################## P R O P  C O N T ######################################
    ##################################################################################################

    @staticmethod
    def categories_on_page(wiki: Wiki, titles: list[str]) -> dict:
        """Fetch the categories used on a page.

        Args:
            wiki (Wiki): The Wiki object to use
            titles (list[str]): The list of pages to get categories of.

        Returns:
            dict: A `dict` such that each key is the title and each value is the list of categories the page is categorized in.
        """
        log.debug("%s: fetching categories on pages: %s", wiki, titles)
        return MQuery._prop_cont(wiki, titles, PropCont.CATEGORIES)

    @staticmethod
    def duplicate_files(wiki: Wiki, titles: list[str], local_only: bool = True) -> dict:
        """Find dupliates of the specified files if possible.

        Args:
            wiki (Wiki): The Wiki object to use
            titles (list[str]): The list of files to get duplicates of (must start with `File:` prefix).
            local_only (bool, optional): Set `False` to also search the associated shared media repository wiki.  If that sounded like a foreign language to you, then ignore this parameter.  Defaults to True.

        Returns:
            dict:  A `dict` such that each key is the title and each value is the list of files that duplicate the specified file.
        """
        log.debug("%s: fetching duplicates of %s", wiki, titles)
        return {k: ([wiki.convert_ns(s, NS.FILE) for s in v] if v is not None else None) for k, v in MQuery._prop_cont(wiki, titles, PropCont.DUPLICATE_FILES, {"dflocalonly": 1} if local_only else {}).items()}

    @staticmethod
    def external_links(wiki: Wiki, titles: list[str]) -> dict:
        log.debug("%s: fetching external links on %s", wiki, titles)
        return MQuery._prop_cont(wiki, titles, PropCont.EXTERNAL_LINKS)

    @staticmethod
    def file_usage(wiki: Wiki, titles: list[str]) -> dict:
        """Fetch the titles of all pages displaying the specified list of media files.

        Args:
            wiki (Wiki): The Wiki object to use
            titles (list[str]): The files to get file usage of.  Each list element must include the `File:` prefix

        Returns:
            dict: A dict such that each key is the title and each value is the list of pages displaying the file.
        """
        log.debug("%s: fetching file usage: %s", wiki, titles)
        return MQuery._prop_cont(wiki, titles, PropCont.FILEUSAGE)

    @staticmethod
    def global_usage(wiki: Wiki, titles: list[str]) -> dict:
        log.debug("%s: fetching global usage of %s", wiki, titles)
        return MQuery._prop_cont(wiki, titles, PropCont.GLOBAL_USAGE)

    @staticmethod
    def image_info(wiki: Wiki, titles: list[str]) -> dict:
        log.debug("%s: fetching image info for %s", wiki, titles)
        return MQuery._prop_cont(wiki, titles, PropCont.IMAGE_INFO)

    @staticmethod
    def images_on_page(wiki: Wiki, titles: list[str]) -> dict:
        log.debug("%s: determining what files are embedded on %s", wiki, titles)
        return MQuery._prop_cont(wiki, titles, PropCont.IMAGES)

    @staticmethod
    def links_on_page(wiki: Wiki, titles: list[str], *ns: Union[NS, str]) -> dict:
        log.debug("%s: fetching wikilinks on %s", wiki, titles)
        return MQuery._prop_cont(wiki, titles, PropCont.WIKILINKS_ON_PAGE, {"plnamespace": wiki.ns_manager.create_filter(*ns)} if ns else {})

    @staticmethod
    def templates_on_page(wiki: Wiki, titles: list[str]) -> dict:
        log.debug("%s: determining what templates are transcluded on %s", wiki, titles)
        return MQuery._prop_cont(wiki, titles, PropCont.TEMPLATES)

    @staticmethod
    def what_links_here(wiki: Wiki, titles: list[str]) -> dict:
        log.debug("%s: determining what pages link to %s", wiki, titles)
        return MQuery._prop_cont(wiki, titles, PropCont.LINKS_HERE)

    @staticmethod
    def what_transcludes_here(wiki: Wiki, titles: list[str], *ns: Union[NS, str]) -> dict:
        log.debug("%s: fetching transclusions of %s", wiki, titles)
        return MQuery._prop_cont(wiki, titles, PropCont.TRANSCLUDED_IN, {"tinamespace": wiki.ns_manager.create_filter(*ns)} if ns else {})
