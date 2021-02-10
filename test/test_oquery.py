import unittest

from pwiki.ns import NS
from pwiki.oquery import OQuery
from pwiki.wiki import Wiki


class TestOQuery(unittest.TestCase):
    """Tests pwiki's OQuery methods"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.wiki = Wiki("test.wikipedia.org", cookie_jar=None)

    def test_normalize_titles(self):
        expected = {"lol": "Lol", "user talk:captain_america": "User talk:Captain america", "WP:AN": "Wikipedia:AN"}
        self.assertDictEqual(expected, OQuery.normalize_titles(self.wiki, list(expected.keys())))

    def test_resolve_redirects(self):
        expected = {"User:Fastily/Sandbox/Redirect2": "User:Fastily/Sandbox/RedirectTarget", "User:Fastily/Sandbox/Redirect3": "User:Fastily/Sandbox/Redirect3"}
        self.assertDictEqual(expected, OQuery.resolve_redirects(self.wiki, list(expected.keys())))

    def test_fetch_token(self):
        self.assertEqual("+\\", OQuery.fetch_token(self.wiki))
        self.assertTrue(OQuery.fetch_token(self.wiki, True))

    def test_list_user_rights(self):
        result = OQuery.list_user_rights(self.wiki, ["Fastily", "FSock", "127.0.0.1", "DoesNotExist23849723849"])
        self.assertIn("user", result["Fastily"])
        self.assertIn("user", result["FSock"])
        self.assertFalse(result["127.0.0.1"])
        self.assertFalse(result["DoesNotExist23849723849"])

    def test_prefix_index(self):
        self.assertSetEqual({"User:Fastily/Sandbox/Page/1", "User:Fastily/Sandbox/Page/2", "User:Fastily/Sandbox/Page/3"}, set(OQuery.prefix_index(self.wiki, NS.USER, "Fastily/Sandbox/Page/")))

    def test_uploadable_filetypes(self):
        self.assertTrue(OQuery.uploadable_filetypes(self.wiki))

    def test_user_uploads(self):
        self.assertSetEqual({"File:FCTest2.svg", "File:FCTest1.png"}, set(OQuery.user_uploads(self.wiki, "FastilyClone")))

    def test_whoami(self):
        self.assertTrue(OQuery.whoami(self.wiki))
