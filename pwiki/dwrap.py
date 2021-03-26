"""Sane object wrappers for data returned by the API"""

from datetime import datetime

from .utils import mine_for


class _DataEntry:
    """Base template class for more structured data returned by the API."""

    def __init__(self, e: dict):
        """Initializer, creates a new DataEntry.

        Args:
            e (dict): A json object from the list in the response from the server.
        """
        self.user: str = e.get("user")
        self.title: str = e.get("title")
        self.summary: str = e.get("comment")
        self.timestamp: datetime = datetime.fromisoformat(ts.replace("Z", "+00:00")) if (ts := e.get("timestamp")) else None

    def __repr__(self) -> str:
        """Creates a str representation of this DataEntry.  Useful for debugging.

        Returns:
            str: The str representation of this DataEntry.
        """
        return f"User: {self.user} | Title: {self.title} | Summary: {self.summary} | Timestamp: {self.timestamp}"


class Contrib(_DataEntry):
    """Represents a contribution (i.e. edit) made by a user, as obtained from `Special:MyContributions`."""

    def __init__(self, e: dict):
        """Initializer, creates a new Contrib

        Args:
            e (dict): A json object from the `"contributions"` list in the response from the server.
        """
        super().__init__(e)

        self.is_page_create: bool = e.get("new")
        self.is_minor: bool = e.get("minor")
        self.is_top: bool = e.get("top")


class ImageInfo(_DataEntry):
    """Represents an image info revision to a media file."""

    def __init__(self, e: dict):
        """Initializer, creates a new ImageInfo

        Args:
            e (dict): A json object from the `"imageinfo"` list in the response from the server.
        """
        super().__init__(e)

        self.size: int = e.get("size")
        self.width: int = e.get("width")
        self.height: int = e.get("height")
        self.url: str = e.get("url")
        self.sha1: str = e.get("sha1")


class Log(_DataEntry):
    """Represents an log entry from `Special:Log`."""

    def __init__(self, e: dict):
        """Initializer, creates a new Log

        Args:
            e (dict): A json object from the `"logevents"` list in the response from the server.
        """
        super().__init__(e)

        self.type: str = e.get("type")
        self.action: str = e.get("action")
        self.tags: list[str] = e.get("tags")


class Revision(_DataEntry):
    """Represents an edit to a page on a wiki"""

    def __init__(self, e: dict):
        """Initializer, creates a new Revision

        Args:
            e (dict): A json object from the `"revisions"` list in the response from the server.
        """
        super().__init__(e)

        self.revid: int = int(e.get("revid", 0))  # default 0 because it is impossible to have a revision with id 0
        self.text: str = mine_for(e, "slots", "main", "content")

    def __repr__(self) -> str:
        """Creates a `str` representation of this Revision.  Useful for debugging.

        Returns:
            str: The str representation of this Revision.
        """
        return f"{super().__repr__()} | text: {self.text}"
