"""Classes and constants for making miscellaneous and other one-off queries"""

from __future__ import annotations

import logging

from typing import TYPE_CHECKING

from .ns import NSManager
from .query_constants import QConstant
from .query_utils import basic_query, chunker, extract_body, get_continue_params, mine_for, query_and_validate
from .utils import has_error

if TYPE_CHECKING:
    from .wiki import Wiki

log = logging.getLogger(__name__)


class OQuery:
    """Collection of miscellaneous and one-off query action methods"""

    @staticmethod
    def _pair_titles_query(wiki: Wiki, id: str, pl: dict, titles: list[str], desc: str) -> dict:
        """Performs a simple query (not `list` or `prop`) that returns a `query` json object containing a key with a list of to-from json objects.  Also parses and returns results.

        Args:
            wiki (Wiki): The Wiki object to use
            id (str): The key under `"query"` in `response` to fetch.
            pl (dict): Additional parameters, excluding `"titles"`.
            titles (list[str]): The titles to process.
            desc (str): A few words describing what this query was trying to accomplish.  This will be displayed in the logs if there was an error.

        Returns:
            dict: [description]
        """
        out = {s: s for s in titles}

        for chunk in chunker(titles, wiki.prop_title_max):
            if response := extract_body(id, query_and_validate(wiki, {**pl, "titles": "|".join(chunk)}, wiki.is_bot, desc)):
                for e in response:
                    out[e["from"]] = e["to"]

        return out

    @staticmethod
    def _prop_cont_single(wiki: Wiki, title: str, template: QConstant, extra_pl: dict = None) -> list:
        out = []

        params = {**template.pl_with_limit(), "prop": template.name, "titles": title}
        if extra_pl:
            params |= extra_pl

        while True:
            if not (response := query_and_validate(wiki, params, desc=f"peform a prop_cont_single query with '{template.name}'")):
                raise OSError(f"Critical failure performing a _prop_cont_single query with {template.name}, cannot proceed")

            if not ((l := mine_for(response, "query", "pages")) and template.name in (p := l[0])):
                break

            out += template.retrieve_results(p[template.name])

            if not (cont := get_continue_params(response)):
                break

            params.update(cont)

        return out


    @staticmethod
    def fetch_token(wiki: Wiki, login_token: bool = False) -> str:
        """Fetch a csrf or login token from the server.  By default, this method will retrieve a csrf token.

        Args:
            login_token (bool, optional): Set `True` to get a login token instead of a csrf token. Defaults to False.

        Raises:
            Exception: if there was a server error or the token couldn't be retrieved.

        Returns:
            str: The token as a str.
        """
        log.debug("%s: Fetching %s token...", wiki, "login" if login_token else "csrf")

        pl = {"meta": "tokens"}
        if login_token:
            pl["type"] = "login"

        if not has_error(response := basic_query(wiki, pl)):
            return extract_body("tokens", response)["logintoken" if login_token else "csrftoken"]

        log.debug(response)
        raise OSError(f"{wiki}: Could not retrieve tokens, network error?")

    @staticmethod
    def fetch_namespaces(wiki: Wiki) -> NSManager:
        """Fetches namespace data from the Wiki and returns it as an NSManager.

        Args:
            wiki (Wiki): The Wiki object to use

        Raises:
            OSError: If there was a network error or bad reply from the server.

        Returns:
            NSManager: An NSManager containing namespace data.
        """
        log.debug("%s: Fetching namespace data...", wiki)

        if not has_error(response := basic_query(wiki, {"meta": "siteinfo", "siprop": "namespaces|namespacealiases"})):
            return NSManager(response["query"])

        log.debug(response)
        raise OSError(f"{wiki}: Could not retrieve namespace data, network error?")

    @staticmethod
    def list_user_rights(wiki: Wiki, users: list[str]) -> dict:
        """Lists user rights for the specified users.

        Args:
            wiki (Wiki): The Wiki object to use.
            users (list[str]): The list of users to get rights for.  Usernames must be well formed (e.g. no wacky capitalization), and should not contain the `User:` prefix.

        Returns:
            dict: A dict such that each key is the username (without the `User:` prefix), and each value is a str list of the user's rights on-wiki.  Value will be None if the user does not exist or is an anonymous (IP) user.
        """
        out = {}

        for chunk in chunker(users, wiki.prop_title_max):
            if response := query_and_validate(wiki, {"list": "users", "usprop": "groups", "ususers": "|".join(chunk)}, wiki.is_bot, "determine user rights"):
                for p in mine_for(response, "query", "users"):
                    try:
                        out[p["name"]] = None if p.keys() & {"invalid", "missing"} else p["groups"]
                    except Exception:
                        log.debug("%s: Unable able to parse list value from: %s", wiki, p, exc_info=True)

        return out

    @staticmethod
    def normalize_titles(wiki: Wiki, titles: list[str]) -> dict:
        """Normalizes titles to match their canonical versions.  Usually this means fixing capitalization or replacing underscores with spaces.

        Args:
            wiki (Wiki): The Wiki object to use.
            titles (list[str]): The titles to normalize.

        Returns:
            dict: A `dict` where the original title is the key and the value is its normalized version.
        """
        return OQuery._pair_titles_query(wiki, "normalized", {}, titles, "normalize titles")

    @staticmethod
    def resolve_redirects(wiki: Wiki, titles: list[str]) -> dict:
        """Fetch the targets of redirect pages.

        Args:
            wiki (Wiki): The Wiki object to use
            titles (list[str]): The list of titles to query

        Returns:
            dict: A dict where each key is the title and the value is the redirect target.  If the key was not a redirect, then the value will be identical to the key.
        """
        return OQuery._pair_titles_query(wiki, "redirects", {"redirects": 1}, titles, "resolve title redirects")

    @staticmethod
    def uploadable_filetypes(wiki: Wiki) -> set:
        """Queries the Wiki for all acceptable file types which may be uploaded to this Wiki.  PRECONDITION: the target Wiki permits file uploads.

        Returns:
            set: A set containing all acceptable file types as their extensions ("." prefix is included) 
        """
        if not has_error(response := basic_query(wiki, {"meta": "siteinfo", "siprop": "fileextensions"})):
            return {jo["ext"] for jo in extract_body("fileextensions", response)}

        log.debug(response)
        log.error("%s: Could not fetch acceptable file upload extensions", wiki)

    @staticmethod
    def whoami(wiki: Wiki) -> str:
        """Get this Wiki's username from the server.  If not logged in, then this will return your external IP address.

        Args:
            wiki (Wiki): The Wiki object to use

        Returns:
            str: If logged in, this Wiki's username.  Otherwise, the external IP address of your device.
        """
        if not has_error(response := basic_query(wiki, {"meta": "userinfo"})):
            return extract_body("userinfo", response)["name"]

        log.debug(response)
        log.error("%s: Could not get this Wiki's username from the server", wiki)
