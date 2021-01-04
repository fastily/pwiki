"""Shared utilities and constants"""

API_DEFAULTS = {"format": "json", "formatversion": "2"}


def make_params(action: str, pl: dict = None) -> dict:
    """Convienence method to generate payload parameters.  Fills in useful details that should be submitted with every request.

    Args:
        action (str): The action value (e.g. "query", "edit", "purge")
        pl (dict, optional): Additional parameters besides the defaults in _API_DEFAULTS and the action parameter. Defaults to None.

    Returns:
        dict: A new dict with the parameters
    """
    return {**API_DEFAULTS, **(pl or {}), "action": action}
