"""Classes/Constants shared by query methods"""
from __future__ import annotations

import logging

from contextlib import suppress
from typing import TYPE_CHECKING, Union

from .utils import make_params

if TYPE_CHECKING:
    from .wiki import Wiki

log = logging.getLogger(__name__)


class QueryUtils:
    """Collection of methods shared by query classes"""

    @staticmethod
    def extract_body(id: str, response: dict) -> Union[dict, list]:
        """Gets the value from a json object 2 levels down, following the path `"query"` -> `id`.  Useful for extracting the results of a query.

        Args:
            id (str): The key under `"query"` in `response` to fetch.
            response (dict): The response from the server.

        Returns:
            Union[dict, list]: the contents under `"query"` -> `id`.
        """
        with suppress(Exception):
            return response["query"][id]

    @staticmethod
    def basic_query(wiki: Wiki, pl: dict) -> dict:
        """Performs a query action and returns the response from the server as json.

        Args:
            wiki (Wiki): The Wiki object to use
            pl (dict): The parameter list to send.  Do not include `{"action": "query"}`, this pair will be automatically included.

        Returns:
            dict: The response from the server.  Empty dict if something went wrong
        """
        try:
            return wiki.client.get(wiki.endpoint, params=make_params("query", pl)).json()
        except Exception:
            log.error("%s: Could not reach server or read response while performing query with params: %s", wiki, pl, exc_info=True)

        return {}
