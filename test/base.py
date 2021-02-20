"""Shared template TestCase classes for use in pwiki tests"""

import json

from pathlib import Path
from unittest import TestCase

from pwiki.wiki import Wiki


def file_to_json(name: str) -> dict:
    return json.loads(Path(f"./test/res/{name}.json").read_text())


def new_wiki(**kwargs):
    return Wiki("test.wikipedia.org", **kwargs)


class QueryTestCase(TestCase):
    """Basic template for query tests"""

    _WIKI = new_wiki(cookie_jar=None)

    @classmethod
    def setUpClass(cls) -> None:
        cls.wiki = QueryTestCase._WIKI
