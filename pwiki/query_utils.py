from __future__ import annotations

import logging

from contextlib import suppress
from typing import TYPE_CHECKING

from .utils import make_params

if TYPE_CHECKING:
    from .wiki import Wiki

log = logging.getLogger(__name__)

class QueryUtils:

    @staticmethod
    def extract_body(id:str, response:dict):
        with suppress(Exception):
            return response["query"][id]

    @staticmethod
    def basic_query(wiki: Wiki, pl: dict):
        try:
            return wiki.client.get(wiki.endpoint, params=make_params("query", pl)).json()
        except Exception:
            log.error("%s: Could not reach server or read response while performing query with params: %s", wiki, pl, exc_info=True)

        return {}

