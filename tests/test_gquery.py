from datetime import datetime, timezone
from unittest.mock import Mock, patch

from pwiki.gquery import GQuery
from pwiki.ns import NS
from pwiki.query_constants import MAX
from pwiki.query_utils import flatten_generator

from .base import file_to_json, WikiTestCase


class TestListCont(WikiTestCase):
    """Tests GQuery's list cont methods"""

    def test_all_users(self):
        self.assertTrue(next(GQuery.all_users(self.wiki)))
        self.assertTrue(next(GQuery.all_users(self.wiki, "sysop")))
        self.assertTrue(next(GQuery.all_users(self.wiki, ["bot", "bureaucrat"], 5)))

    def test_category_members(self):
        # test 1
        self.assertCountEqual(["User:Fastily/Sandbox/Page/2", "File:FastilyTest.png"], next(GQuery.category_members(self.wiki, "Category:Fastily Test2", limit=MAX)))

        # test 2
        self.assertListEqual(["File:FastilyTest.png"], next(GQuery.category_members(self.wiki, "Category:Fastily Test2", [NS.FILE], MAX)))

        # test 3
        with self.assertRaises(StopIteration):
            next(GQuery.category_members(self.wiki, "Category:DoesNotExist Fastily1234"))

    def test_contribs(self):
        # test 1
        l = next(GQuery.contribs(self.wiki, "FastilyClone", True, limit=2))

        self.assertEqual(2, len(l))
        self.assertEqual("File:FCTest1.png", l[0].title)
        self.assertFalse(l[0].is_minor)
        self.assertTrue(l[0].is_page_create)

        self.assertEqual("File:FCTest2.svg", l[1].title)
        self.assertFalse(l[1].is_minor)
        self.assertTrue(l[1].is_page_create)

        # test 2
        l = next(g := GQuery.contribs(self.wiki, "FastilyClone", ns=[NS.USER], limit=2))

        self.assertEqual(2, len(l))
        self.assertEqual("User:FastilyClone/Page/1", l[0].title)
        self.assertEqual("s2", l[0].summary)
        self.assertTrue(l[0].is_top)

        self.assertEqual("User:FastilyClone/Page/1", l[1].title)
        self.assertEqual("s1", l[1].summary)
        self.assertFalse(l[1].is_top)

        l = next(g)

        self.assertEqual(1, len(l))
        self.assertEqual("User:FastilyClone/Page/1", l[0].title)
        self.assertEqual("s0", l[0].summary)
        self.assertFalse(l[0].is_top)
        self.assertTrue(l[0].is_page_create)

        # test 3
        with self.assertRaises(StopIteration):
            next(GQuery.contribs(self.wiki, "NotARealAccountFastily"))

    def test_list_duplicate_files(self):
        self.assertTrue(l := next(GQuery.list_duplicate_files(self.wiki)))
        self.assertTrue(l[0].startswith("File:"))

    def test_prefix_index(self):
        self.assertCountEqual(["User:Fastily/Sandbox/Page/1", "User:Fastily/Sandbox/Page/2", "User:Fastily/Sandbox/Page/3"], flatten_generator(GQuery.prefix_index(self.wiki, NS.USER, "Fastily/Sandbox/Page/")))

        with self.assertRaises(StopIteration):
            next(GQuery.prefix_index(self.wiki, NS.USER, "Fastily/DoesNotExistEver1234"))

    def test_logs(self):
        l = next(GQuery.logs(self.wiki, log_type="delete", user="Fastily", ns=NS.FILE, limit=3))
        self.assertEqual(3, len(l))
        for e in l:
            self.assertEqual("Fastily", e.user)
            self.assertTrue(e.title.startswith("File:"))
            self.assertEqual("delete", e.action)

        l = next(GQuery.logs(self.wiki, "File:FCTest1.png", "upload"))
        self.assertEqual(1, len(l))
        self.assertEqual("FastilyClone", l[0].user)
        self.assertEqual(datetime.fromisoformat("2015-10-20T00:28:32+00:00"), l[0].timestamp)

    def test_random(self):
        l = next(GQuery.random(self.wiki))
        self.assertEqual(1, len(l))

        l = next(GQuery.random(self.wiki, [NS.FILE], 2))
        self.assertEqual(2, len(l))
        for e in l:
            self.assertTrue(e.startswith("File:"))

    def test_search(self):
        self.assertEqual(1, len(next(GQuery.search(self.wiki, "Fastily"))))

        l = next(GQuery.search(self.wiki, "FastilyClone", [NS.USER]))
        self.assertEqual(1, len(l))
        self.assertTrue(l[0].startswith("User:"))

    def test_user_uploads(self):
        self.assertCountEqual(["File:FCTest2.svg", "File:FCTest1.png"], flatten_generator(GQuery.user_uploads(self.wiki, "FastilyClone")))

        with self.assertRaises(StopIteration):
            next(GQuery.user_uploads(self.wiki, "DoesNotExistFastily"))


class TestPropCont(WikiTestCase):
    """Tests GQuery's prop cont methods"""

    def test_categories_on_page(self):
        self.assertCountEqual(["Category:Fastily Test", "Category:Fastily Test2"], next(GQuery.categories_on_page(self.wiki, "User:Fastily/Sandbox/Page/2", MAX)))

    @patch("pwiki.query_utils.basic_query", return_value=file_to_json("deleted-revisions"))
    def test_deleted_revisions(self, mock: Mock):
        result = next(GQuery.deleted_revisions(self.wiki, "User:Fastily/SomePageThatWasDeleted"))

        mock.assert_called_once()
        self.assertEqual(3, len(result))
        self.assertEqual("Fastily", result[0].user)
        self.assertEqual("test 1", result[1].summary)
        self.assertEqual(datetime(2022, 6, 21, 9, 38, 57, tzinfo=timezone.utc), result[2].timestamp)

    def test_revisions(self):
        # test 1 - base
        result = next(g := GQuery.revisions(self.wiki, "User:Fastily/Sandbox/RevisionTest", 2))
        self.assertEqual(2, len(result))
        self.assertEqual("FSock", result[0].user)
        self.assertEqual(465879, result[0].revid)
        self.assertEqual("b", result[1].summary)

        result = next(g)
        self.assertEqual(1, len(result))
        self.assertEqual("Fastily", result[0].user)
        self.assertIsNone(result[0].text)

        # test 2 - reversed, with text
        result = next(g := GQuery.revisions(self.wiki, "User:Fastily/Sandbox/RevisionTest", 2, True, include_text=True))
        self.assertEqual(2, len(result))
        self.assertEqual("hello!", result[0].text)
        self.assertEqual("Fastily", result[1].user)

        result = next(g)
        self.assertEqual(1, len(result))
        self.assertEqual("c", result[0].summary)

        # test 3 - dates
        result = next(GQuery.revisions(self.wiki, "User:Fastily/Sandbox/RevisionTest", 5, True, datetime(2021, 2, 9, 4, 32, tzinfo=timezone.utc)))
        self.assertEqual(1, len(result))
        self.assertEqual("c", result[0].summary)

        result = next(GQuery.revisions(self.wiki, "User:Fastily/Sandbox/RevisionTest", 5, start=datetime(2021, 2, 9, 4, 29, tzinfo=timezone.utc), end=datetime(2021, 2, 9, 4, 32, tzinfo=timezone.utc)))  # newer first
        self.assertEqual(2, len(result))
        self.assertEqual("b", result[0].summary)
        self.assertEqual("a", result[1].summary)

        result = next(GQuery.revisions(self.wiki, "User:Fastily/Sandbox/RevisionTest", 5, True, datetime(2021, 2, 9, 4, 29, tzinfo=timezone.utc), datetime(2021, 2, 9, 4, 32, tzinfo=timezone.utc)))  # older first
        self.assertEqual(2, len(result))
        self.assertEqual("a", result[0].summary)
        self.assertEqual("b", result[1].summary)

        with self.assertRaises(ValueError):
            GQuery.revisions(self.wiki, "Foobar", 99, True, datetime(2023, 2, 9, 4, 29, tzinfo=timezone.utc), datetime(2021, 2, 9, 4, 32, tzinfo=timezone.utc))

        # test 4 - non-existent
        with self.assertRaises(StopIteration):
            next(GQuery.revisions(self.wiki, "DoesNotExistFastily"))
