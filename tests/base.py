"""Shared template TestCase classes and methods for use in pwiki tests"""

import json

from pathlib import Path
from unittest import TestCase

from pwiki.wiki import Wiki


_RES = Path("./tests/res/")


def file_to_text(name: str, ext: str = "txt") -> str:
    """Gets the text from the specified `res` file as a `str`.

    Args:
        name (str): The name of the file, without its extension.
        ext (str, optional): The extension of the file.  Don't include the leading `.`. Defaults to "txt".

    Returns:
        str: The contents of `name`.
    """
    return (_RES / f"{name}.{ext}").read_text()


def file_to_json(name: str) -> dict:
    """Gets the text from the specified `res` file as json.  This is a shortcut for `json.loads(file_to_text(name, "json"))`.

    Args:
        name (str): The name of the file, without its extension.

    Returns:
        dict: The contents of `name`, as json.
    """
    return json.loads(file_to_text(name, "json"))


def new_wiki(**kwargs) -> Wiki:
    """Convienence method, creates a new `Wiki` pointed to testwiki.  `kwargs` will be passed to the `Wiki` constructor.

    Returns:
        Wiki: A new Wiki pointed to testwiki.
    """
    return Wiki("test.wikipedia.org", **kwargs)


class WikiTestCase(TestCase):
    """Basic template for query tests"""
    _WIKI = new_wiki(cookie_jar=None)

    @classmethod
    def setUpClass(cls) -> None:
        """Sets up an instance of a `Wiki` pointed to testwiki"""
        cls.wiki = WikiTestCase._WIKI
