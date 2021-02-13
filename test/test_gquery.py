import unittest

from pwiki.gquery import GQuery
from pwiki.ns import NS
from pwiki.query_utils import flatten_generator
from pwiki.wiki import Wiki


class TestPropNoCont(unittest.TestCase):
    """Tests pwiki's GQuery methods"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.wiki = Wiki("test.wikipedia.org", cookie_jar=None)

    def test_prefix_index(self):
        self.assertSetEqual({"User:Fastily/Sandbox/Page/1", "User:Fastily/Sandbox/Page/2", "User:Fastily/Sandbox/Page/3"}, set(flatten_generator(GQuery.prefix_index(self.wiki, NS.USER, "Fastily/Sandbox/Page/"))))

    def test_revisions(self):
        # base
        result = next(g := GQuery.revisions(self.wiki, "User:Fastily/Sandbox/RevisionTest", 2))
        self.assertEqual(2, len(result))
        self.assertEqual("FSock", result[0].user)
        self.assertEqual("b", result[1].summary)

        result = next(g)
        self.assertEqual(1, len(result))
        self.assertEqual("Fastily", result[0].user)
        self.assertIsNone(result[0].text)

        # reversed, with text
        result = next(g := GQuery.revisions(self.wiki, "User:Fastily/Sandbox/RevisionTest", 2, True, include_text=True))
        self.assertEqual(2, len(result))
        self.assertEqual("hello!", result[0].text)
        self.assertEqual("Fastily", result[1].user)

        result = next(g)
        self.assertEqual(1, len(result))
        self.assertEqual("c", result[0].summary)

    def test_user_uploads(self):
        self.assertSetEqual({"File:FCTest2.svg", "File:FCTest1.png"}, set(flatten_generator(GQuery.user_uploads(self.wiki, "FastilyClone"))))
