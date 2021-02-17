from datetime import datetime

from .base import QueryTestCase


class TestWikiQuery(QueryTestCase):
    """Tests pwiki's Wiki query methods"""

    def test_first_editor_of(self):
        self.assertEqual("Fastily", self.wiki.first_editor_of("User:Fastily/Sandbox/RevisionTest"))

    def test_last_editor_of(self):
        self.assertEqual("FSock", self.wiki.last_editor_of("User:Fastily/Sandbox/RevisionTest"))

    def test_list_user_rights(self):
        self.assertFalse(self.wiki.list_user_rights())
        self.assertIn("user", self.wiki.list_user_rights("FastilyClone"))

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
