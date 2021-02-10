import unittest

from datetime import datetime

from pwiki.wiki import Wiki


class TestWikiQuery(unittest.TestCase):
    """Tests pwiki's Wiki query methods"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.wiki = Wiki("test.wikipedia.org", cookie_jar=None)

    def test_first_editor_of(self):
        self.assertEqual("Fastily", self.wiki.first_editor_of("User:Fastily/Sandbox/RevisionTest"))

    def test_last_editor_of(self):
        self.assertEqual("FSock", self.wiki.last_editor_of("User:Fastily/Sandbox/RevisionTest"))

    def test_revisions(self):
        # newer first
        result = self.wiki.revisions("User:Fastily/Sandbox/RevisionTest")
        self.assertEqual(3, len(result))
        self.assertEqual("foo", result[1].text)
        self.assertEqual("a", result[2].summary)
        self.assertEqual(datetime.fromisoformat("2021-02-09T04:33:26Z+00:00"), result[0].timestamp)

        # older first
        result = self.wiki.revisions("User:Fastily/Sandbox/RevisionTest", True, False)
        self.assertEqual("c", result[2].summary)
        self.assertIsNone(result[0].text)
