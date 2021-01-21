from __future__ import annotations

import logging

from typing import TYPE_CHECKING

from .query_utils import basic_query, extract_body
from .utils import has_error

if TYPE_CHECKING:
    from .wiki import Wiki

log = logging.getLogger(__name__)


class OQuery:
    """Collection of miscellaneous and one-off query action methods"""

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
        log.info("%s: Fetching %s token...", wiki, "login" if login_token else "csrf")

        pl = {"meta": "tokens"}
        if login_token:
            pl["type"] = "login"

        if not has_error(response := basic_query(wiki, pl)):
            return extract_body("tokens", response)["logintoken" if login_token else "csrftoken"]

        log.debug(response)
        raise OSError(f"{wiki}: Could not retrieve tokens, network error?")

    @staticmethod
    def uploadable_filetypes(wiki: Wiki) -> set:
        """Queries the Wiki for all acceptable file types which may be uploaded to this Wiki.  PRECONDITION: the target Wiki permits file uploads.

        Returns:
            set: A set containing all acceptable file types as their extensions ("." prefix is included) 
        """
        log.info("%s: Fetching a list of acceptable file upload extensions", wiki)

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
        log.info("%s: Asking the server who we are logged in as...", wiki)

        if not has_error(response := basic_query(wiki, {"meta": "userinfo"})):
            return extract_body("userinfo", response)["name"]

        log.debug(response)
        log.error("%s: Could get this Wiki's username from the server", wiki)
