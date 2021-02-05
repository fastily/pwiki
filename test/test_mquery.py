import unittest

from pwiki.mquery import MQuery
from pwiki.wiki import Wiki


class TestMQuery(unittest.TestCase):
    """Tests pwiki's OQuery methods"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.wiki = Wiki("test.wikipedia.org", cookie_jar=None)

    def test_file_usage(self):
        m = MQuery.file_usage(self.wiki, ["File:FastilyTest.svg", "File:Fastily NonExistent File.png"])

        self.assertSetEqual({"User:Fastily/Sandbox/ImageLinks", "User:Fastily/Sandbox/Page"}, set(m["File:FastilyTest.svg"]))
        self.assertListEqual([], m["File:Fastily NonExistent File.png"])

    def test_category_size(self):
        expected = {"Category:Fastily Test": 4, "Category:Fastily Test2": 2, "Category:Does0Not0Exist6": 0}
        self.assertDictEqual(expected, MQuery.category_size(self.wiki, list(expected.keys())))

    def test_exists(self):
        expected = {"Main Page": True, "User:Fastily/Sandbox": True, "User:Fastily/NoPageHere": False}
        self.assertDictEqual(expected, MQuery.exists(self.wiki, list(expected.keys())))

        expected = {"uSeR:fastily/Sandbox": True, "user:fastily/noPageHere": False}
        self.assertDictEqual(expected, MQuery.exists(self.wiki, list(expected.keys())))

    def test_page_text(self):
        expected = {"User:Fastily/Sandbox/HelloWorld": "Hello World!", "Category:Fastily Test": "jwiki unit testing!", "User:Fastily/NoPageHere": ""}
        self.assertDictEqual(expected, MQuery.page_text(self.wiki, list(expected.keys())))
