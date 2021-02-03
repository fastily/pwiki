import unittest

from pwiki.ns import NS
from pwiki.wiki import Wiki


class TestNamespaces(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.wiki = Wiki("test.wikipedia.org", cookie_jar=None)

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
        self.assertEqual({"Foo"}, set(self.wiki.filter_by_ns(["User:Example", "Foo", "Talk:Hello"], NS.MAIN)))
        self.assertEqual({"Copper", "Talk:Silver", "Gold"}, set(self.wiki.filter_by_ns(["Copper", "Talk:Silver", "Gold", "User talk:Iridium"], "Main", NS.TALK)))
        self.assertEqual(set(), set(self.wiki.filter_by_ns(["Chicken", "Talk:Cow", "Pig"], NS.PROJECT)))
        self.assertEqual(set(), set(self.wiki.filter_by_ns(["Category:Sun", "Talk:Moon", "Template:Stars"])))

    def test_talk_page_of(self):
        self.assertEqual("User talk:Me", self.wiki.talk_page_of("User:Me"))
        self.assertEqual("Talk:Hello", self.wiki.talk_page_of("Hello"))
        self.assertIsNone(self.wiki.talk_page_of("File talk:Derp.mp3"))


if __name__ == '__main__':
    unittest.main()
