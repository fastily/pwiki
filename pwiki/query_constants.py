"""Constants shared between query classes"""

from typing import Any, Callable, Union

from .utils import mine_for


class QConstant:
    """Template information for API queries.  Can generate query parameters to send and contains the result retreival function."""

    def __init__(self, name: str, pl: dict = None, limit_key: str = None, retrieve_results: Callable[[Union[dict, list]], Any] = None):
        """Initializer, creates a new QConstant.

        Args:
            name (str): The name of the query, this should be the value to send with the `prop` or `list` key.
            pl (dict, optional): Additional parameters to send, excluding the limit key. Defaults to None.
            limit_key (str, optional): The limit key associated with this query, if applicable. Defaults to None.
            retrieve_results (Callable[[Union[dict, list]], Any], optional): The function to retrieve values from the server's response.  Varies between `prop`/`list` queries.  If not set, will use the default `prop` retrieval function. Defaults to None.
        """
        self.name = name
        self.pl = pl or {}
        self.limit_key = limit_key
        self.retrieve_results = retrieve_results or (lambda l: [e["title"] for e in l])

    def pl_with_limit(self, limit_value="max"):
        pl = {**self.pl}
        if self.limit_key and limit_value:
            pl[self.limit_key] = limit_value

        return pl

# class PropConstant(QConstant):
#     def __init__(self, name: str, pl: dict = None, limit_key: str = None, retrieve_results: Callable[[Union[dict, list]], Any] = None):
#         super().__init__(name, pl=pl, limit_key=limit_key, retrieve_results=retrieve_results or (lambda l: [e["title"] for e in l]))

# class ListQConstant(QConstant):
#     def __init__(self, name: str, titles_key:str, pl: dict = None, limit_key: str = None, retrieve_results: Callable[[Union[dict, list]], Any] = None):
#         super().__init__(name, pl=pl, limit_key=limit_key, retrieve_results=retrieve_results)

#         self.titles_key = titles_key


class PropNoCont:
    EXISTS = QConstant("pageprops", {"ppprop": "missing"}, retrieve_results=lambda r: "missing" not in r)
    CATEGORY_SIZE = QConstant("categoryinfo", retrieve_results=lambda r: mine_for(r, "categoryinfo", "size"))
    PAGE_TEXT = QConstant("revisions", {"rvprop": "content", "rvslots": "main"}, retrieve_results=lambda r: mine_for(r["revisions"][0], "slots", "main", "content"))

class PropCont:
    CATEGORIES = QConstant("categories", limit_key="cllimit")
    FILEUSAGE = QConstant("fileusage", limit_key="fulimit")

# class ListNoCont:
#     pass