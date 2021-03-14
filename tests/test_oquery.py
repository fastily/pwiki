from pwiki.oquery import OQuery

from .base import WikiTestCase


class TestOQuery(WikiTestCase):
    """Tests pwiki's OQuery methods"""

    def test_fetch_token(self):
        self.assertEqual("+\\", OQuery.fetch_token(self.wiki))
        self.assertTrue(OQuery.fetch_token(self.wiki, True))

    def test_list_user_rights(self):
        result = OQuery.list_user_rights(self.wiki, ["Fastily", "FSock", "127.0.0.1", "DoesNotExist23849723849"])
        self.assertIn("user", result["Fastily"])
        self.assertIn("user", result["FSock"])
        self.assertFalse(result["127.0.0.1"])
        self.assertFalse(result["DoesNotExist23849723849"])

    def test_normalize_titles(self):
        expected = {"lol": "Lol", "user talk:captain_america": "User talk:Captain america", "WP:AN": "Wikipedia:AN"}
        self.assertDictEqual(expected, OQuery.normalize_titles(self.wiki, list(expected.keys())))

    def test_resolve_redirects(self):
        expected = {"User:Fastily/Sandbox/Redirect2": "User:Fastily/Sandbox/RedirectTarget", "User:Fastily/Sandbox/Redirect3": "User:Fastily/Sandbox/Redirect3", "User:Fastily/DoesNotExist123": "User:Fastily/DoesNotExist123"}
        self.assertDictEqual(expected, OQuery.resolve_redirects(self.wiki, list(expected.keys())))

    def test_uploadable_filetypes(self):
        self.assertTrue(OQuery.uploadable_filetypes(self.wiki))

    def test_whoami(self):
        self.assertTrue(OQuery.whoami(self.wiki))
