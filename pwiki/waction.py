"""Classes and functions backing the actions API.  Not a stable API, should not be used outside of pwiki."""
from __future__ import annotations

import json
import logging

from contextlib import suppress
from typing import TYPE_CHECKING

from .config import make_params

if TYPE_CHECKING:
    from .wiki import Wiki

log = logging.getLogger(__name__)


class WAction:

    @staticmethod
    def post_action(wiki: Wiki, action: str, form: dict = None, apply_token: bool = True):
        pl = make_params(action, form)
        if apply_token:
            pl["token"] = wiki.csrf_token

        try:
            return wiki.client.post(wiki.endpoint, data=pl).json()
        except Exception:
            log.error("Could not reach server or read response while performing %s with params %s", action, pl, exc_info=True)

    @staticmethod
    def is_success(action: str, response: dict) -> bool:
        with suppress(Exception):
            return response[action]["result"] == "Success"

        return False

        # try:
        #     return response[action]["result"] == "Success"
        # except Exception:
        #     log.error("Error reading response status on %s", action, exc_info=True)
        #     log.debug(response)

        # return False

    @staticmethod
    def read_error(action:str, response: dict) -> tuple:
        with suppress(Exception):
            if action in response:
                return response[action]["result"], response[action]["reason"]
            elif "error" in response:
                return response["error"]["code"], response["error"]["info"]

        log.warning("Unable to parse error which occurred while perfoming a '%s' action", action)
        log.debug(response)

        return None, None

    @staticmethod
    def edit(wiki: Wiki, title: str, text: str, summary: str = ""):
        log.info("%s: Editing '%s'", wiki, title)

        pl = {"title": title, "text": text, "summary": summary}

        response = WAction.post_action(wiki, "edit", pl)

        if WAction.is_success("edit", response):
            return True
        
        log.error("%s: Could not edit '%s', server said: %s", wiki, title, WAction.read_error("edit", response))
        return False
