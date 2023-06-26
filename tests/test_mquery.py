from datetime import datetime

from pwiki.mquery import MQuery
from pwiki.ns import NS

from .base import WikiTestCase


class TestPropNoCont(WikiTestCase):
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


class TestPropCont(WikiTestCase):
    """Tests MQuery's PropCont methods"""

    def test_categories_on_page(self):
        m = MQuery.categories_on_page(self.wiki, ["User:Fastily/Sandbox/Page/2", "User:Fastily/NotARealPage123"])
        self.assertCountEqual(["Category:Fastily Test", "Category:Fastily Test2"], m["User:Fastily/Sandbox/Page/2"])
        self.assertFalse(m["User:Fastily/NotARealPage123"])

    def test_duplicate_files(self):
        expected = {"File:FastilyTest.svg": ["File:FastilyTestCopy.svg"], "File:FastilyTestCircle2.svg": [], "File:FastilyDoesNotExistFile.flac": []}
        self.assertDictEqual(expected, MQuery.duplicate_files(self.wiki, list(expected.keys())))

        expected = {"File:FastilyTest.svg": []}
        self.assertDictEqual(expected, MQuery.duplicate_files(self.wiki, list(expected.keys()), False, True))

    def test_external_links(self):
        m = MQuery.external_links(self.wiki, ["User:Fastily/Sandbox/ExternalLink", "User:Fastily/Sandbox", "User:Fastily/DoesNotExist789"])
        self.assertCountEqual(["https://www.google.com/", "https://www.facebook.com/", "https://github.com/"], m["User:Fastily/Sandbox/ExternalLink"])
        self.assertFalse(m["User:Fastily/Sandbox"])
        self.assertFalse(m["User:Fastily/DoesNotExist789"])

    def test_file_usage(self):
        m = MQuery.file_usage(self.wiki, ["File:FastilyTest.svg", "File:Fastily NonExistent File.png"])
        self.assertCountEqual(["User:Fastily/Sandbox/ImageLinks", "User:Fastily/Sandbox/Page"], m["File:FastilyTest.svg"])
        self.assertListEqual([], m["File:Fastily NonExistent File.png"])

    def test_global_usage(self):
        self.assertEqual(2, len(m := MQuery.global_usage(self.wiki, ["File:Anise2000px.JPG", "File:Strawberry3500px.jpg"])))
        for v in m.values():
            self.assertTrue(v)

    def test_image_info(self):
        m = MQuery.image_info(self.wiki, ["File:FastilyTestR.svg", "File:FastilyTest.svg", "File:FastilyTestCircle1.svg", "File:DoesNotExistFastily123.jpg"])

        result = m["File:FastilyTestR.svg"][0]
        self.assertEqual(477, result.height)
        self.assertEqual(512, result.width)
        self.assertEqual(876, result.size)
        self.assertEqual("275e96b2660f761cca02b8d2cb5425bcaab4dd98", result.sha1)

        result = m["File:FastilyTest.svg"][0]
        self.assertEqual(477, result.height)
        self.assertEqual(512, result.width)
        self.assertEqual(876, result.size)
        self.assertEqual("275e96b2660f761cca02b8d2cb5425bcaab4dd98", result.sha1)
        self.assertEqual("https://upload.wikimedia.org/wikipedia/test/f/f7/FastilyTest.svg", result.url)

        result = m["File:FastilyTestCircle1.svg"][0]
        self.assertEqual(502, result.height)
        self.assertEqual(512, result.width)
        self.assertEqual(1336, result.size)
        self.assertEqual("0bfe3100d0277c0d42553b9d16db71a89cc67ef7", result.sha1)
        self.assertEqual("unit test for wiki\n\n[[Category:Fastily Test3]]", result.summary)
        self.assertEqual(datetime.fromisoformat("2016-03-21T02:12:43+00:00"), result.timestamp)

        self.assertFalse(m["File:DoesNotExistFastily123.jpg"])

    def test_images_on_page(self):
        m = MQuery.images_on_page(self.wiki, ["User:Fastily/Sandbox/Page", "User:Fastily/DoesNotExist789"])
        self.assertCountEqual(["File:FastilyTest.svg", "File:FastilyTest.png"], m["User:Fastily/Sandbox/Page"])
        self.assertFalse(m["User:Fastily/DoesNotExist789"])

    def test_links_on_page(self):
        m = MQuery.links_on_page(self.wiki, ["User:Fastily/Sandbox/Page", "User:Fastily/DoesNotExist789"], NS.USER)
        self.assertCountEqual(["User:Fastily/Sandbox/Page/1", "User:Fastily/Sandbox/Page/2", "User:Fastily/Sandbox/Page/3", "User:Fastily/Sandbox/Page/4"], m["User:Fastily/Sandbox/Page"])
        self.assertFalse(m["User:Fastily/DoesNotExist789"])

    def test_templates_on_page(self):
        m = MQuery.templates_on_page(self.wiki, ["User:Fastily/Sandbox/T", "User:Fastily/DoesNotExist789"])
        self.assertCountEqual(["User:Fastily/Sandbox/T/1", "Template:FastilyTest"], m["User:Fastily/Sandbox/T"])
        self.assertFalse(m["User:Fastily/DoesNotExist789"])

    def test_what_links_here(self):
        m = MQuery.what_links_here(self.wiki, ["User:Fastily/Sandbox/Link/1", "User:Fastily/Sandbox/Link/4", "User:Fastily/DoesNotExist789"])
        self.assertCountEqual(["User:Fastily/Sandbox/Link", "User:Fastily/Sandbox/Link/2", "User:Fastily/Sandbox/Link/3"], m["User:Fastily/Sandbox/Link/1"])
        self.assertCountEqual(["User:Fastily/Sandbox/Link", "User:Fastily/Sandbox/Link/5", "User:Fastily/Sandbox/Link/6"], m["User:Fastily/Sandbox/Link/4"])
        self.assertFalse(m["User:Fastily/DoesNotExist789"])

        m = MQuery.what_links_here(self.wiki, ["User:Fastily/Sandbox/Link/1", "User:Fastily/DoesNotExist789"], True)
        self.assertListEqual(["User:Fastily/Sandbox/Link/4"], m["User:Fastily/Sandbox/Link/1"])
        self.assertFalse(m["User:Fastily/DoesNotExist789"])

        m = MQuery.what_links_here(self.wiki, ["User:Fastily/Sandbox/LinksHereTest", "User:Fastily/DoesNotExist1337"], ns=[NS.FILE, NS.USER])
        self.assertCountEqual(["File:Fastily Test Pie.svg", "User:Fastily/Sandbox/LinksHereTest2"], m["User:Fastily/Sandbox/LinksHereTest"])
        self.assertFalse(m["User:Fastily/DoesNotExist1337"])

        self.assertListEqual(["FastilyTest2"], MQuery.what_links_here(self.wiki, ["User:Fastily/Sandbox/LinksHereTest"], ns=NS.MAIN)["User:Fastily/Sandbox/LinksHereTest"])  # major corner case

    def test_what_transcludes_here(self):
        m = MQuery.what_transcludes_here(self.wiki, ["Template:FastilyTest", "User:Fastily/DoesNotExist789"])
        self.assertCountEqual(["User:Fastily/Sandbox/T", "FastilyTest"], m["Template:FastilyTest"])
        self.assertFalse(m["User:Fastily/DoesNotExist789"])

        m = MQuery.what_transcludes_here(self.wiki, ["Template:FastilyTest"], NS.MAIN)
        self.assertListEqual(["FastilyTest"], m["Template:FastilyTest"])
