"""Sane object wrappers for data returned by the API"""

from datetime import datetime

from .utils import mine_for


class DataEntry:
    """Base template class for more structured data returned by the API."""

    def __init__(self, user: str = None, title: str = None, summary: str = None, timestamp: str = None):
        """Initializer, creates a new DataEntry.

        Args:
            user (str, optional): The user associated with this entry. `User:` prefix should be omitted. Defaults to None.
            title (str, optional): The page title associated with this entry. Defaults to None.
            summary (str, optional): The summary associated with this entry. Defaults to None.
            timestamp (str, optional): The timestamp (in ISO 8601) the entry occured at. Defaults to None.
        """
        self.user: str = user
        self.title: str = title
        self.summary: str = summary
        self.timestamp: datetime = datetime.fromisoformat(timestamp.replace("Z", "+00:00")) if timestamp else None

    def __repr__(self) -> str:
        """Creates a str representation of this DataEntry.  Useful for debugging.

        Returns:
            str: The str representation of this DataEntry.
        """
        return f"User: {self.user} | Title: {self.title} | Summary: {self.summary} | Timestamp: {self.timestamp}"


class Contrib(DataEntry):
    def __init__(self, e: dict):
        super().__init__(e.get("user"), e.get("title"), e.get("comment"), e.get("timestamp"))

        self.is_page_create: bool = e.get("new")
        self.is_minor: bool = e.get("minor")
        self.is_top: bool = e.get("top")


class ImageInfo(DataEntry):

    def __init__(self, e: dict):
        super().__init__(e.get("user"), summary=e.get("comment"), timestamp=e.get("timestamp"))

        self.size: int = e.get("size")
        self.width: int = e.get("width")
        self.height: int = e.get("height")
        self.url: str = e.get("url")
        self.sha1: str = e.get("sha1")


class Revision(DataEntry):
    """Represents an edit to a page on a wiki"""

    def __init__(self, e: dict):
        """Initializer, creates a new Revision

        Args:
            e (dict): A json object from the `"revisions"` list in the response from the server.
        """
        super().__init__(e.get("user"), summary=e.get("comment"), timestamp=e.get("timestamp"))

        self.text: str = mine_for(e, "slots", "main", "content")

    def __repr__(self) -> str:
        return f"{super().__repr__()} | text: {self.text}"
