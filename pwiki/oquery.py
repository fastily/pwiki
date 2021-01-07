from __future__ import annotations

import logging

from typing import TYPE_CHECKING

from .query_utils import QueryUtils
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
        pl = {"meta": "tokens"}
        if login_token:
            pl["type"] = "login"

        response = QueryUtils.basic_query(wiki, pl)
        if has_error(response):
            log.debug(response)
            raise OSError(f"{wiki}: Could not retrieve tokens, network error?")

        return QueryUtils.extract_body("tokens", response)["logintoken" if login_token else "csrftoken"]
