"""Generator-based query methods which can be used to fetch a limited number of results"""

from __future__ import annotations

import logging

from collections.abc import Iterator
from datetime import datetime
from typing import Any, TYPE_CHECKING, Union

from .dwrap import Revision
from .query_constants import PropCont, PropContSingle, QConstant
from .query_utils import get_continue_params, query_and_validate
from .utils import mine_for

if TYPE_CHECKING:
    from .wiki import Wiki

log = logging.getLogger(__name__)


class GQuery:
    """Collection of queries which fetch and yield results via Generator."""

    @staticmethod
    def prop_cont(wiki: Wiki, title: str, limit_value: Union[int, str], template: QConstant, extra_pl: dict = None) -> Iterator[Any]:
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

    @staticmethod
    def categories_on_page(wiki: Wiki, title: str, limit: Union[int, str] = 1) -> Iterator[list[str]]:
        return GQuery.prop_cont(wiki, title, limit, PropCont.CATEGORIES)

    @staticmethod
    def revisions(wiki: Wiki, title: str, limit: Union[int, str] = 1, older_first: bool = False, start: datetime = None, end: datetime = None, include_text: bool = False) -> Iterator[list[Revision]]:
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

        return GQuery.prop_cont(wiki, title, limit, PropContSingle.REVISIONS, pl)
