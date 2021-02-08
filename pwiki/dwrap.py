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
        self.user = user
        self.title = title
        self.summary = summary
        self.timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00")) if timestamp else None

    def __repr__(self) -> str:
        """Creates a str representation of this DataEntry.  Useful for debugging.

        Returns:
            str: The str representation of this DataEntry.
        """
        return f"User: {self.user} | Title: {self.title} | Summary: {self.summary} | Timestamp: {self.timestamp}"


class Revision(DataEntry):
    """Represents an edit to a page on a wiki"""

    def __init__(self, rev: dict, title: str = None):
        """Initializer, creates a new Revision

        Args:
            rev (dict): A json object from the `"revisions"` list in the response from the server.
            title (str, optional): The page title associated with this Revision.  Defaults to None.
        """
        super().__init__(rev.get("user"), title, rev.get("comment"), rev.get("timestamp"))

        self.text: str = mine_for(rev, "slots", "main", "content")

    def __repr__(self) -> str:
        return f"{super().__repr__()} | text: {self.text}"