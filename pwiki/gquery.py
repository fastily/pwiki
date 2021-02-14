"""Generator-based query methods which can be used to fetch a limited number of results"""

from __future__ import annotations

import logging

from collections.abc import Generator
from datetime import datetime
from typing import Any, TYPE_CHECKING, Union

from .dwrap import Contrib, Log, Revision
from .ns import NS
from .query_constants import ListCont, PropCont, PropContSingle, QConstant
from .query_utils import get_continue_params, query_and_validate
from .utils import mine_for

if TYPE_CHECKING:
    from .wiki import Wiki

log = logging.getLogger(__name__)


class GQuery:
    """Collection of queries which fetch and yield results via Generator."""

    @staticmethod
    def _list_cont(wiki: Wiki, limit_value: Union[int, str], template: QConstant, extra_pl: dict = None):
        params = {**template.pl_with_limit(limit_value), "list": template.name} | (extra_pl or {})
        while True:
            if not (response := query_and_validate(wiki, params, desc=f"peform a list_cont query with '{template.name}'")):
                raise OSError(f"Critical failure performing a list_cont query with {template.name}, cannot proceed")

            if template.name not in (q := mine_for(response, "query")):
                break

            yield template.retrieve_results(q[template.name])

            if not (cont := get_continue_params(response)):
                break

            params.update(cont)

    @staticmethod
    def _prop_cont(wiki: Wiki, title: str, limit_value: Union[int, str], template: QConstant, extra_pl: dict = None) -> Generator[Any, None, None]:
        params = {**template.pl_with_limit(limit_value), "prop": template.name, "titles": title} | (extra_pl or {})

        while True:
            if not (response := query_and_validate(wiki, params, desc=f"peform a prop_cont query with '{template.name}'")):
                raise OSError(f"Critical failure performing a prop_cont query with {template.name}, cannot proceed")

            if not ((l := mine_for(response, "query", "pages")) and template.name in (p := l[0])):
                break

            yield template.retrieve_results(p[template.name])

            if not (cont := get_continue_params(response)):
                break

            params.update(cont)

    ##################################################################################################
    ########################################### L I S T  C O N T #####################################
    ##################################################################################################

    @staticmethod
    def contribs(wiki: Wiki, user: str, older_first: bool = False, ns: list[Union[NS, str]] = [], limit: Union[int, str] = 1) -> Generator[list[Contrib], None, None]:
        pl = {"ucuser": user}
        if ns:
            pl["ucnamespace"] = wiki.ns_manager.create_filter(*ns)
        if older_first:
            pl["ucdir"] = "newer"

        return GQuery._list_cont(wiki, limit, ListCont.CONTRIBS, pl)

    @staticmethod
    def category_members(wiki: Wiki, title: str, ns: list[Union[NS, str]] = [], limit: Union[int, str] = 1) -> list:
        return GQuery._list_cont(wiki, limit, ListCont.CATEGORY_MEMBERS, {"cmtitle": title} | ({"cmnamespace": wiki.ns_manager.create_filter(*ns)} if ns else {}))

    @staticmethod
    def list_duplicate_files(wiki: Wiki, limit: Union[int, str] = 1) -> list:
        return GQuery._list_cont(wiki, limit, ListCont.DUPLICATE_FILES)

    @staticmethod
    def logs(wiki: Wiki, title: str = None, log_type: str = None, log_action: str = None, user: str = None, ns: Union[NS, str] = None, tag: str = None, start: datetime = None, end: datetime = None, older_first: bool = False, limit: Union[int, str] = 1) -> Generator[list[Log], None, None]:
        pl = {}
        if title:
            pl["letitle"] = title
        if log_type:
            pl["letype"] = log_type
        if log_action:
            pl["leaction"] = log_action
        if user:
            pl["leuser"] = user
        if ns:
            pl["lenamespace"] = wiki.ns_manager.create_filter(ns)
        if tag:
            pl["letag"] = tag
        if start:
            pl["lestart"] = start.isoformat()
        if end:
            pl["leend"] = end.isoformat()
        if older_first:
            pl["ledir"] = "newer"

        return GQuery._list_cont(wiki, limit, ListCont.LOGS, pl)

    @staticmethod
    def prefix_index(wiki: Wiki, ns: Union[NS, str], prefix: str, limit: Union[int, str] = 1) -> list[str]:
        """Performs a prefix index query and returns all matching titles.

        Args:
            wiki (Wiki): The Wiki object to use
            ns (Union[NS, str]): The namespace to search in.
            prefix (str): Fetches all titles in the specified namespace that start with this str.  To return subpages only, append a `/` character to this param.
            limit (Union[int, str], optional): The maxmimum number of elements to fetch each iteration. Defaults to 1.

        Returns:
            list[str]: A list of titles that match the specified prefix index query.
        """
        return GQuery._list_cont(wiki, limit, ListCont.PREFIX_INDEX, {"apnamespace": wiki.ns_manager.create_filter(ns), "apprefix": prefix})

    @staticmethod
    def random(wiki: Wiki, ns: list[Union[NS, str]] = [], limit: Union[int, str] = 1) -> list:
        return GQuery._list_cont(wiki, limit, ListCont.SEARCH, {"rnnamespace": wiki.ns_manager.create_filter(*ns)} if ns else {})

    @staticmethod
    def search(wiki: Wiki, phrase: str, ns: list[Union[NS, str]] = [], limit: Union[int, str] = 1) -> list:
        return GQuery._list_cont(wiki, limit, ListCont.RANDOM, {"srsearch": phrase} | ({"srnamespace": wiki.ns_manager.create_filter(*ns)} if ns else {}))

    @staticmethod
    def user_uploads(wiki: Wiki, user: str, limit: Union[int, str] = 1) -> list[str]:
        """Gets the uploads of a user.

        Args:
            wiki (Wiki): The Wiki object to use
            user (str): The username to query, without the `User:` prefix.
            limit (Union[int, str], optional): The maxmimum number of elements to fetch each iteration. Defaults to 1.

        Returns:
            list[str]: The files uploaded by `user`.
        """
        return GQuery._list_cont(wiki, limit, ListCont.USER_UPLOADS, {"aiuser": user})

    ##################################################################################################
    ########################################### P R O P  C O N T #####################################
    ##################################################################################################

    @staticmethod
    def categories_on_page(wiki: Wiki, title: str, limit: Union[int, str] = 1) -> Generator[list[str], None, None]:
        return GQuery._prop_cont(wiki, title, limit, PropCont.CATEGORIES)

    @staticmethod
    def revisions(wiki: Wiki, title: str, limit: Union[int, str] = 1, older_first: bool = False, start: datetime = None, end: datetime = None, include_text: bool = False) -> Generator[list[Revision], None, None]:
        """Gets the revisions of a page.  Fetches newer revisions first by default.  PRECONDITION: if `start` and `end` are both set, then `start` must occur before `end`.

        Args:
            wiki (Wiki): The Wiki object to use.
            title (str): The title to get revisions of.
            limit (Union[int, str], optional): The maxmimum number of revisions to fetch each iteration. Defaults to 1.
            older_first (bool, optional): Set to `True` to fetch older revisions first. Defaults to False.
            start (datetime, optional): Set to filter out revisions older than this date.  If no timezone is specified in the datetime, then UTC is assumed. Defaults to None.
            end (datetime, optional): Set to filter out revisions newer than this date. If no timezone is specified in the datetime, then UTC is assumed.  Defaults to None.
            include_text (bool, optional): If `True`, then also fetch the wikitext of each revision.  Will populate the Revision.text field.  Defaults to False.

        Returns:
            Iterator[list[Revision]]: A generator which fetches revisions as specified.
        """
        pl = {"rvprop": "comment|timestamp|user"}
        if older_first:
            pl["rvdir"] = "newer"
        if start:
            pl["rvstart"] = start.isoformat()
        if end:
            pl["rvend"] = end.isoformat()
        if include_text:
            pl["rvprop"] += "|content"

        return GQuery._prop_cont(wiki, title, limit, PropContSingle.REVISIONS, pl)
