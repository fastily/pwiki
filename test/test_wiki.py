import unittest

from datetime import datetime

from pwiki.wiki import Wiki


class TestWikiQuery(unittest.TestCase):
    """Tests pwiki's Wiki query methods"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.wiki = Wiki("test.wikipedia.org", cookie_jar=None)

    def test_first_editor_of(self):
        self.assertEqual("FastilyClone", self.wiki.first_editor_of("User:FastilyClone/Page/1"))

    def test_last_editor_of(self):
        self.assertEqual("FastilyClone", self.wiki.last_editor_of("User:FastilyClone/Page/1"))

    def test_revisions(self):
        # newer first
        result = self.wiki.revisions("User:FastilyClone/Page/1")
        self.assertEqual(3, len(result))
        self.assertEqual("1", result[1].text)
        self.assertEqual("s0", result[2].summary)
        self.assertEqual(datetime.fromisoformat("2015-10-23T05:58:54Z+00:00"), result[0].timestamp)

        # older first
        result = self.wiki.revisions("User:FastilyClone/Page/1", True, False)
        self.assertEqual("s2", result[2].summary)
        self.assertIsNone(result[0].text)
