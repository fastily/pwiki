"""Generator-based query methods which can be used to fetch a limited number of results"""

from __future__ import annotations

import logging

from collections.abc import Generator
from datetime import datetime
from typing import TYPE_CHECKING, Union

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
    def _list_cont(wiki: Wiki, limit_value: Union[int, str], template: QConstant, extra_pl: dict = None) -> Generator[list, None, None]:
        """Performs a list query with query continuation.  Use this for fetching queries that take the form of a list.  Fetches up to `limit_value` number of results each iteration.

        Args:
            wiki (Wiki): The Wiki object to use
            limit_value (Union[int, str]): The maximum number of elements to return each iteration.  The maximum is normally 500 for non-bots and 5000 for bots; alternatively, use `str` `"max"`.
            template (QConstant): The QConstant to use.
            extra_pl (dict, optional): Extra parameters to the passed along with the request.  Useful for queries that accept optional configuration. Defaults to None.

        Raises:
            OSError: If the query failed for whatever reason.  Usually this indiciates network failure.

        Yields:
            Generator[list, None, None]: A Generator which yields a `list` (as returned by `template`'s `retrieve_results()`) containing the results of the query.
        """
        params = {**template.pl_with_limit(limit_value), "list": template.name} | (extra_pl or {})
        while True:
            if not (response := query_and_validate(wiki, params, desc=f"peform a list_cont query with '{template.name}'")):
                raise OSError(f"Critical failure performing a list_cont query with {template.name}, cannot proceed")

            if template.name not in (q := mine_for(response, "query")) or not (result := template.retrieve_results(q[template.name])):
                break

            yield result

            if not (cont := get_continue_params(response)):
                break

            params.update(cont)

    @staticmethod
    def _prop_cont(wiki: Wiki, title: str, limit_value: Union[int, str], template: QConstant, extra_pl: dict = None) -> Generator[list, None, None]:
        """Performs a prop query with query continuation.  Use this for fetching page properties that take the form of a list.

        Args:
            wiki (Wiki): The Wiki object to use.
            titles (list[str]): The titles to work on.
            limit_value (Union[int, str]): The maximum number of elements to return each iteration.  The maximum is normally 500 for non-bots and 5000 for bots; alternatively, use `str` `"max"`.
            template (QConstant): The QConstant to use.
            extra_pl (dict, optional): Extra parameters to the passed along with the request.  Useful for queries that accept optional configuration. Defaults to None.

        Raises:
            OSError: If the query failed for whatever reason.  Usually this indiciates network failure.

        Yields:
            Generator[list, None, None]: A `Generator` which yields a `list` (as returned by `template`'s `retrieve_results()`) containing the results of the query.
        """
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
    def all_users(wiki: Wiki, groups: Union[list[str], str] = [], limit: Union[int, str] = 1) -> Generator[list[str], None, None]:
        """Lists all users on a wiki.  Can filter users by right(s) they have been assigned.

        Args:
            wiki (Wiki): The Wiki object to use
            groups (Union[list[str], str], optional): The group(s) to filter by (e.g. `sysop`, `bot`).  Optional, leave empty to disable. Defaults to [].
            limit (Union[int, str], optional): The maximum number of elements to return per iteration. Defaults to 1.

        Returns:
            Generator[list[str], None, None]: A `Generator` which yields a `list` containing users (without the `User:` prefix) that match the specified crteria.
        """
        if isinstance(groups, str):
            groups = [groups]

        return GQuery._list_cont(wiki, limit, ListCont.ALL_USERS, {"augroup": "|".join(groups)} if groups else {})

    @staticmethod
    def category_members(wiki: Wiki, title: str, ns: list[Union[NS, str]] = [], limit: Union[int, str] = 1) -> Generator[list[str], None, None]:
        """Fetches the elements in a category.

        Args:
            wiki (Wiki): The Wiki object to use
            title (str): The title of the category to fetch elements from.  Must include `Category:` prefix.
            ns (list[Union[NS, str]], optional): Only return results that are in these namespaces.  Optional, set empty list to disable. Defaults to [].
            limit (Union[int, str], optional): The maximum number of elements to return per iteration. Defaults to 1.

        Returns:
            Generator[list[str], None, None]: A `Generator` which yields a `list` containing the category's category members.
        """
        return GQuery._list_cont(wiki, limit, ListCont.CATEGORY_MEMBERS, {"cmtitle": title} | ({"cmnamespace": wiki.ns_manager.create_filter(ns)} if ns else {}))

    @staticmethod
    def contribs(wiki: Wiki, user: str, older_first: bool = False, ns: list[Union[NS, str]] = [], limit: Union[int, str] = 1) -> Generator[list[Contrib], None, None]:
        """Fetches contributions of a user.

        Args:
            wiki (Wiki): The Wiki object to use
            user (str): The username to query, excluding the `User:` prefix.
            older_first (bool, optional): Set `True` to fetch older elements first. Defaults to False.
            ns (list[Union[NS, str]], optional): Only return results that are in these namespaces.  Optional, set empty list to disable.  Defaults to [].
            limit (Union[int, str], optional): The maximum number of elements to return per iteration.  Defaults to 1.

        Returns:
            Generator[list[Contrib], None, None]: A `Generator` which yields a `list` of `Contrib` as specified.
        """
        pl = {"ucuser": user}
        if ns:
            pl["ucnamespace"] = wiki.ns_manager.create_filter(ns)
        if older_first:
            pl["ucdir"] = "newer"

        return GQuery._list_cont(wiki, limit, ListCont.CONTRIBS, pl)

    @staticmethod
    def list_duplicate_files(wiki: Wiki, limit: Union[int, str] = 1) -> Generator[list[str], None, None]:
        """List files on a wiki which have duplicates by querying the Special page `Special:ListDuplicatedFiles`.

        Args:
            wiki (Wiki): The Wiki object to use
            limit (Union[int, str], optional): The maximum number of elements to return per iteration. Defaults to 1.

        Returns:
            Generator[list[str], None, None]: A `Generator` which yields a `list` containing files that have duplicates on the wiki.
        """
        return GQuery._list_cont(wiki, limit, ListCont.DUPLICATE_FILES)

    @staticmethod
    def logs(wiki: Wiki, title: str = None, log_type: str = None, log_action: str = None, user: str = None, ns: Union[NS, str] = None, tag: str = None, start: datetime = None, end: datetime = None, older_first: bool = False, limit: Union[int, str] = 1) -> Generator[list[Log], None, None]:
        """Fetches `Special:Log` entries from a wiki. PRECONDITION: if `start` and `end` are both set, then `start` must occur before `end`.

        Args:
            wiki (Wiki): The Wiki object to use
            title (str, optional): The title of the page to get logs for, if applicable. Defaults to None.
            log_type (str, optional): The type of log to fetch (e.g. `"delete"`). Defaults to None.
            log_action (str, optional): The type and sub-action of the log to fetch (e.g. `"delete/restore"`).  Overrides `log_type`.  Defaults to None.
            user (str, optional): The user associated with the log action, if applicable.  Do not include `User:` prefix.  Defaults to None.
            ns (Union[NS, str], optional): Only return results that are in this namespace. Defaults to None.
            tag (str, optional): Only return results that are tagged with this tag. Defaults to None.
            start (datetime, optional): Set to filter out revisions older than this date.  If no timezone is specified in the datetime, then UTC is assumed. Defaults to None.
            end (datetime, optional): Set to filter out revisions newer than this date.  If no timezone is specified in the datetime, then UTC is assumed. Defaults to None.
            older_first (bool, optional): Set to `True` to fetch older log entries first. Defaults to False.
            limit (Union[int, str], optional): The maximum number of elements to return per iteration. Defaults to 1.

        Returns:
            Generator[list[Log], None, None]: A `Generator` which yields a `list` of `Log` as specified.
        """
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
    def prefix_index(wiki: Wiki, ns: Union[NS, str], prefix: str, limit: Union[int, str] = 1) -> Generator[list[str], None, None]:
        """Performs a prefix index query and returns all matching titles.

        Args:
            wiki (Wiki): The Wiki object to use
            ns (Union[NS, str]): The namespace to search in.
            prefix (str): Fetches all titles in the specified namespace that start with this str.  To return subpages only, append a `/` character to this param.
            limit (Union[int, str], optional): The maxmimum number of elements to fetch each iteration. Defaults to 1.

        Returns:
            Generator[list[str], None, None]: A `Generator` which yields a `list` containing files that match the specified prefix index.
        """
        return GQuery._list_cont(wiki, limit, ListCont.PREFIX_INDEX, {"apnamespace": wiki.ns_manager.intify(ns), "apprefix": prefix})

    @staticmethod
    def random(wiki: Wiki, ns: list[Union[NS, str]] = [], limit: Union[int, str] = 1) -> Generator[list[str], None, None]:
        """Fetches a list of random pages from the wiki.

        Args:
            wiki (Wiki): The Wiki object to use
            ns (list[Union[NS, str]], optional): Only return results that are in these namespaces.  Optional, set empty list to disable. Defaults to [].
            limit (Union[int, str], optional): The maxmimum number of elements to fetch each iteration.  Defaults to 1.

        Returns:
            Generator[list[str], None, None]: A `Generator` which yields a `list` containing random elements that match specified parameters.
        """
        return GQuery._list_cont(wiki, limit, ListCont.RANDOM, {"rnnamespace": wiki.ns_manager.create_filter(ns)} if ns else {})

    @staticmethod
    def search(wiki: Wiki, phrase: str, ns: list[Union[NS, str]] = [], limit: Union[int, str] = 1) -> Generator[list[str], None, None]:
        """Perform a search on the wiki.

        Args:
            wiki (Wiki): The Wiki object to use
            phrase (str): The phrase to query with
            ns (list[Union[NS, str]], optional): Only return results that are in these namespaces.  Optional, set empty list to disable. Defaults to [].
            limit (Union[int, str], optional): The maxmimum number of elements to fetch each iteration.  Defaults to 1.

        Returns:
            Generator[list[str], None, None]: A `Generator` which yields a `list` containing the results of the search.
        """
        return GQuery._list_cont(wiki, limit, ListCont.SEARCH, {"srsearch": phrase} | ({"srnamespace": wiki.ns_manager.create_filter(ns)} if ns else {}))

    @staticmethod
    def stashed_files(wiki: Wiki, limit: Union[int, str] = 1) -> Generator[list[tuple[str, int, str]], None, None]:
        """Fetch the user's stashed files.  PRECONDITION: You must be logged in for this to work

        Args:
            wiki (Wiki): The Wiki object to use
            limit (Union[int, str], optional): The maxmimum number of elements to fetch each iteration.  Defaults to 1.

        Returns:
            Generator[list[tuple[str, int]], None, None]: A `Generator` which yields a `list` of 3-`tuple` where each tuple is of the form (file key, file size, status).   Known values for status: `"finished"`, `"chunks"`
        """
        return GQuery._list_cont(wiki, limit, ListCont.STASHED_FILES)

    @staticmethod
    def user_uploads(wiki: Wiki, user: str, limit: Union[int, str] = 1) -> Generator[list[str], None, None]:
        """Gets the uploads of a user.

        Args:
            wiki (Wiki): The Wiki object to use
            user (str): The username to query, without the `User:` prefix.
            limit (Union[int, str], optional): The maxmimum number of elements to fetch each iteration. Defaults to 1.

        Returns:
            Generator[list[str], None, None]: A `Generator` which yields a `list` containing the files uploaded by `user`.
        """
        return GQuery._list_cont(wiki, limit, ListCont.USER_UPLOADS, {"aiuser": user})

    ##################################################################################################
    ########################################### P R O P  C O N T #####################################
    ##################################################################################################

    @staticmethod
    def categories_on_page(wiki: Wiki, title: str, limit: Union[int, str] = 1) -> Generator[list[str], None, None]:
        """Fetch the categories used on a page.

        Args:
            wiki (Wiki): The Wiki object to use
            title (str): The title to query.
            limit (Union[int, str], optional): The maxmimum number of elements to fetch each iteration. Defaults to 1.

        Returns:
            Generator[list[str], None, None]: A `Generator` which yields a `list` containing the categories contained on `title`.
        """
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
            include_text (bool, optional): If `True`, then also fetch the wikitext of each revision.  Will populate the `Revision.text` field.  Defaults to False.

        Returns:
            Generator[list[Revision], None, None]: A `Generator` which yields a `list` containing the Revision objects of `title`.
        """
        if start and end and start >= end:
            raise ValueError(f"start '{start}' cannot be equal to or after end '{end}' !")

        pl = {"rvprop": "comment|ids|timestamp|user"}

        if older_first:
            pl["rvdir"] = "newer"
        else:
            start, end = end, start  # quirk of MediaWiki, older requires end < start

        if start:
            pl["rvstart"] = start.isoformat()
        if end:
            pl["rvend"] = end.isoformat()
        if include_text:
            pl["rvprop"] += "|content"

        return GQuery._prop_cont(wiki, title, limit, PropContSingle.REVISIONS, pl)
