"""Shared template TestCase classes for use in pwiki tests"""

import unittest

from pwiki.wiki import Wiki


class QueryTestCase(unittest.TestCase):
    """Basic template for query tests"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.wiki = Wiki("test.wikipedia.org", cookie_jar=None)
