from pwiki.mquery import MQuery
from pwiki.ns import NS

from .base import QueryTestCase


class TestPropNoCont(QueryTestCase):
    """Tests MQuery's PropNoCont methods"""

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


class TestPropCont(QueryTestCase):
    """Tests MQuery's PropCont methods"""

    def test_duplicate_files(self):
        expected = {"File:FastilyTest.svg": ["File:FastilyTestCopy.svg"], "File:FastilyTestCircle2.svg": []}
        self.assertDictEqual(expected, MQuery.duplicate_files(self.wiki, list(expected.keys())))

    def test_file_usage(self):
        m = MQuery.file_usage(self.wiki, ["File:FastilyTest.svg", "File:Fastily NonExistent File.png"])

        self.assertSetEqual({"User:Fastily/Sandbox/ImageLinks", "User:Fastily/Sandbox/Page"}, set(m["File:FastilyTest.svg"]))
        self.assertListEqual([], m["File:Fastily NonExistent File.png"])

    def test_links_on_page(self):
        m = MQuery.links_on_page(self.wiki, ["User:Fastily/Sandbox/Page"], NS.USER)

        self.assertSetEqual({"User:Fastily/Sandbox/Page/1", "User:Fastily/Sandbox/Page/2", "User:Fastily/Sandbox/Page/3", "User:Fastily/Sandbox/Page/4"}, set(m["User:Fastily/Sandbox/Page"]))
