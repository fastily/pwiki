"""Shared utilities and constants"""
import logging

from contextlib import suppress
from typing import Any

API_DEFAULTS = {"format": "json", "formatversion": "2"}

log = logging.getLogger(__name__)


def has_error(response: dict) -> bool:
    """Checks if a response from the server contains an error.

    Args:
        response (dict): The json response from the server.

    Returns:
        bool: True if the response contained an error.
    """
    return "error" in response


def make_params(action: str, pl: dict = None) -> dict:
    """Convienence method to generate payload parameters.  Fills in useful details that should be submitted with every request.

    Args:
        action (str): The action value (e.g. "query", "edit", "purge")
        pl (dict, optional): Additional parameters besides the defaults in _API_DEFAULTS and the action parameter. Defaults to None.

    Returns:
        dict: A new dict with the parameters
    """
    return {**API_DEFAULTS, **(pl or {}), "action": action}


def mine_for(target: dict, *keys: str) -> Any:
    """Digs through nested json objects, following the keys named by `keys`.  PRECONDITION: `target` only contains json objects.

    Args:
        target (dict): The json object to dig through.
        keys (str): The keys to follow.

    Returns:
        Any: Whatever value is found at the end of following the specified keys.  `None` if nothing was not found.
    """
    try:
        for k in keys:
            target = target.get(k, {})

        return target if target != {} else None
    except Exception:
        log.debug("Crash in mine_for(), something must have gone *terribly* wrong", exc_info=True)


def read_error(action: str, response: dict) -> tuple[str, str]:
    """Reads the error or result from an action response.  Useful for logging.

    Args:
        action (str): The type of action that was just performed.
        response (dict): The json response from the server

    Returns:
        tuple[str, str]: A tuple such that the first element is the status code and the second element is the error description.
    """
    with suppress(Exception):
        if has_error(response):
            return response["error"]["code"], response["error"]["info"]
        elif action in response:
            return response[action]["result"], response[action]["reason"]

    log.warning("Unable to parse error which occurred while perfoming a '%s' action", action)
    log.debug(response)

    return (None,)*2
