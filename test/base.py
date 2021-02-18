"""Shared template TestCase classes for use in pwiki tests"""

import unittest

from pwiki.wiki import Wiki


class QueryTestCase(unittest.TestCase):
    """Basic template for query tests"""

    _WIKI = Wiki("test.wikipedia.org", cookie_jar=None)

    @classmethod
    def setUpClass(cls) -> None:
        cls.wiki = QueryTestCase._WIKI
