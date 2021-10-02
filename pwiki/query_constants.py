"""Constants shared between query classes"""

from typing import Any, Callable, Union

from .dwrap import Contrib, ImageInfo, Log, Revision
from .utils import mine_for

MAX = "max"


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

    def pl_with_limit(self, limit_value: Union[int, str] = MAX) -> dict:
        """Get the parameter list (`self.pl`) for this QConstant and include this QConstant's `self.limit_key` and the specified `limit_value` if possible.

        Args:
            limit_value (Union[int, str], optional): The limit value to associate with this QConstant's `self.limit_key` in the returned parameter list. Defaults to "max".

        Returns:
            dict: A new parameter wtih the key-value pairs in `self.pl` and a `limit_key` and `limit_value` as specified.
        """
        pl = {**self.pl}
        if self.limit_key and limit_value:
            pl[self.limit_key] = limit_value

        return pl


class PropNoCont:
    """Collection of QConstant objects which fulfill the page prop with no continuation strategy."""
    EXISTS = QConstant("pageprops", {"ppprop": "missing"}, retrieve_results=lambda r: "missing" not in r)
    CATEGORY_SIZE = QConstant("categoryinfo", retrieve_results=lambda r: mine_for(r, "categoryinfo", "size") or 0)
    PAGE_TEXT = QConstant("revisions", {"rvprop": "content", "rvslots": "main"}, retrieve_results=lambda r: Revision(r["revisions"][0]).text if "revisions" in r else "")


class PropCont:
    """Collection of QConstant objects which fulfill the page prop with continuation strategy."""
    CATEGORIES = QConstant("categories", limit_key="cllimit")
    DUPLICATE_FILES = QConstant("duplicatefiles", limit_key="dflimit", retrieve_results=lambda l: [e["name"] for e in l])
    DUPLICATE_FILES_SHARED = QConstant("duplicatefiles", limit_key="dflimit", retrieve_results=lambda l: [e["name"] for e in l if e.get("shared")])
    GLOBAL_USAGE = QConstant("globalusage", limit_key="gulimit", retrieve_results=lambda l: [(e["title"], e["wiki"]) for e in l])
    EXTERNAL_LINKS = QConstant("extlinks", {"elexpandurl": 1}, "ellimit", lambda l: [e["url"] for e in l])
    FILEUSAGE = QConstant("fileusage", limit_key="fulimit")
    IMAGE_INFO = QConstant("imageinfo", {"iiprop": "comment|sha1|size|timestamp|url|user"}, "iilimit", lambda l: [ImageInfo(e) for e in l])
    IMAGES = QConstant("images", limit_key="imlimit")
    LINKS_HERE = QConstant("linkshere", limit_key="lhlimit")
    TEMPLATES = QConstant("templates", limit_key="tllimit")
    TRANSCLUDED_IN = QConstant("transcludedin", limit_key="tilimit")
    WIKILINKS_ON_PAGE = QConstant("links", limit_key="pllimit")


class PropContSingle:
    """Collection of QConstant objects which fulfill the prop cont single strategy."""
    REVISIONS = QConstant("revisions", {"rvslots": "main"}, "rvlimit", lambda l: [Revision(e) for e in l])


class ListCont:
    """Collection of QConstant objects which fulfill the list cont strategy."""
    ALL_USERS = QConstant("allusers", limit_key="aulimit", retrieve_results=lambda l: [e["name"] for e in l])
    CATEGORY_MEMBERS = QConstant("categorymembers", limit_key="cmlimit")
    CONTRIBS = QConstant("usercontribs", limit_key="uclimit", retrieve_results=lambda l: [Contrib(e) for e in l])
    DUPLICATE_FILES = QConstant("querypage", {"qppage": "ListDuplicatedFiles"}, "qplimit", lambda q: [e["title"] for e in q["results"]])
    LOGS = QConstant("logevents", {"leprop": "title|type|user|timestamp|comment|tags"}, "lelimit", lambda l: [Log(e) for e in l])
    PREFIX_INDEX = QConstant("allpages", limit_key="aplimit")
    RANDOM = QConstant("random", {"rnfilterredir": "nonredirects"}, "rnlimit")
    SEARCH = QConstant("search", {"srprop": ""}, "srlimit")
    STASHED_FILES = QConstant("mystashedfiles", {"msfprop": "size"}, "msflimit", lambda l: [(e["filekey"], e["size"], e["status"]) for e in l])
    USER_UPLOADS = QConstant("allimages", {"aisort": "timestamp"}, "ailimit")
