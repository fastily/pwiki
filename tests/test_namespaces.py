from pwiki.ns import NS

from .base import WikiTestCase


class TestNamespaces(WikiTestCase):
    """Tests pwiki's namespace handling"""

    def test_which_ns(self):
        self.assertEqual("User talk", self.wiki.which_ns("User talk:TestUser"))
        self.assertEqual("File", self.wiki.which_ns("File:Example.jpg"))
        self.assertEqual("Main", self.wiki.which_ns("Foobar"))
        self.assertEqual("Image", self.wiki.which_ns("Image:Example.jpg"))

    def test_nss(self):
        self.assertEqual("ABC.jpg", self.wiki.nss("File:ABC.jpg"))
        self.assertEqual("ABC.jpg", self.wiki.nss("fIlE:ABC.jpg"))
        self.assertEqual("TestUser", self.wiki.nss("user tALk:TestUser"))
        self.assertEqual("Foo", self.wiki.nss("Foo"))
        self.assertEqual("Example.jpg", self.wiki.nss("Image:Example.jpg"))

    def test_convert_ns(self):
        self.assertEqual("User:Abc", self.wiki.convert_ns("Category:Abc", "User"))
        self.assertEqual("User:Abc", self.wiki.convert_ns("Category:Abc", NS.USER))
        self.assertEqual("Foo", self.wiki.convert_ns("User:Foo", "Main"))
        self.assertEqual("Foo", self.wiki.convert_ns("Foo", "Main"))
        self.assertEqual("File talk:Example.jpg", self.wiki.convert_ns("File:Example.jpg", "File talk"))
        self.assertEqual("File talk:Example.jpg", self.wiki.convert_ns("Image:Example.jpg", NS.FILE_TALK))

    def test_filter_by_ns(self):
        self.assertListEqual(["Foo"], self.wiki.filter_by_ns(["User:Example", "Foo", "Talk:Hello"], NS.MAIN))
        self.assertCountEqual(["Copper", "Talk:Silver", "Gold"], self.wiki.filter_by_ns(["Copper", "Talk:Silver", "Gold", "User talk:Iridium"], "Main", NS.TALK))
        self.assertFalse(self.wiki.filter_by_ns(["Chicken", "Talk:Cow", "Pig"], NS.PROJECT))
        self.assertFalse(self.wiki.filter_by_ns(["Category:Sun", "Talk:Moon", "Template:Stars"]))

    def test_in_ns(self):
        self.assertTrue(self.wiki.in_ns("Help:Cats", NS.HELP))
        self.assertTrue(self.wiki.in_ns("User talk:Cats", "User talk"))
        self.assertTrue(self.wiki.in_ns("Image:Cats.jpg", NS.FILE))
        self.assertTrue(self.wiki.in_ns("Image:Cats.jpg", 6))
        self.assertTrue(self.wiki.in_ns("Wikipedia:Dogs", "Project"))
        self.assertTrue(self.wiki.in_ns("Category:Fastily", ("Category", NS.FILE)))
        self.assertTrue(self.wiki.in_ns("Category:Fastily", (NS.CATEGORY, NS.FILE)))
        self.assertTrue(self.wiki.in_ns("Special:ApiSandbox", -1))

        self.assertFalse(self.wiki.in_ns("File:Example.jpg", "Main"))
        self.assertFalse(self.wiki.in_ns("File:Example.jpg", "Project"))
        self.assertFalse(self.wiki.in_ns("Foobar", NS.TALK))
        self.assertFalse(self.wiki.in_ns("Template:Foobar", (4, NS.PROJECT_TALK)))

    def test_not_in_ns(self):
        self.assertTrue(self.wiki.not_in_ns("Category:Hello", "Main"))
        self.assertTrue(self.wiki.not_in_ns("Template:Foobar", (NS.MEDIAWIKI, NS.PROJECT_TALK)))

        self.assertFalse(self.wiki.not_in_ns("Fastily", NS.MAIN))

    def test_is_talk_page(self):
        self.assertTrue(self.wiki.is_talk_page("User talk:Fastily"))
        self.assertTrue(self.wiki.is_talk_page("Talk:Fastily"))
        self.assertTrue(self.wiki.is_talk_page("WT:Fastily"))

        self.assertFalse(self.wiki.is_talk_page("Main page"))
        self.assertFalse(self.wiki.is_talk_page("File:Fastily.jpg"))
        self.assertFalse(self.wiki.is_talk_page("WP:Fastily"))
        self.assertFalse(self.wiki.is_talk_page("Special:Contributions"))

    def test_talk_page_of(self):
        self.assertEqual("User talk:Me", self.wiki.talk_page_of("User:Me"))
        self.assertEqual("Talk:Hello", self.wiki.talk_page_of("Hello"))
        self.assertIsNone(self.wiki.talk_page_of("File talk:Derp.mp3"))

    def test_page_of(self):
        self.assertEqual("User:Me", self.wiki.page_of("User talk:Me"))
        self.assertEqual("Hello", self.wiki.page_of("Talk:Hello"))
        self.assertIsNone(self.wiki.page_of("File:Derp.mp3"))
