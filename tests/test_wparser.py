from textwrap import dedent

from pwiki.wparser import WParser, WikiTemplate, WikiText

from .base import file_to_text, QueryTestCase

from unittest import TestCase


class TestElementHandling(QueryTestCase):
    """Tests WParser with simple snippets of wikitext"""

    def test_wikitext(self):
        expected = "The idea was to bring together a group of remarkable people, see if they could become something more."
        self.assertEqual(expected, str(WParser.parse(self.wiki, text=expected)))

        expected = "      If we can't protect the Earth you can be damn well sure we'll avenge it\n\n"
        raw_result = WParser.parse(self.wiki, text=expected)
        self.assertEqual(expected, raw_result.as_text())
        self.assertEqual(expected.strip(), str(raw_result))

    def test_template(self):
        expected = "{{Tlp|foo=I am|1=inevitable}}"
        raw_result = WParser.parse(self.wiki, text=expected)
        self.assertEqual(expected, str(raw_result))
        self.assertEqual(dedent("""\
            {{Tlp
            |foo=I am
            |1=inevitable
            }}"""), raw_result.templates[0].as_text(True))

        raw_result = WParser.parse(self.wiki, text="{{We|have a|Hulk}}")
        self.assertEqual("{{We|1=have a|2=Hulk}}", str(raw_result))
        self.assertEqual(dedent("""\
            {{We
            |1=have a
            |2=Hulk
            }}"""), raw_result.templates[0].as_text(True))

    def test_ext(self):
        expected = "Perfectly <nowiki>balanced, as all things</nowiki> should be."
        self.assertEqual(expected, str(WParser.parse(self.wiki, text=expected)))

        expected = "<ref>I can do this all day</ref>"
        self.assertEqual(expected, str(WParser.parse(self.wiki, text=expected)))

        expected = dedent("""\
            <syntaxhighlight lang="python" line='line'>
            print("A thing isn't beautiful because it lasts.")
            </syntaxhighlight>""")
        self.assertEqual(expected, str(WParser.parse(self.wiki, text=expected)))

    def test_comments(self):
        expected = "Dormammu,\n<!--\nI've come\n--> to bargain\n"
        self.assertEqual(expected, WParser.parse(self.wiki, text=expected).as_text())

    def test_h(self):
        expected = "== I am Groot ==\nI am Steve Rogers"
        self.assertEqual(expected, str(WParser.parse(self.wiki, text=expected)))

    def test_ignore(self):
        expected = "Whatever <includeonly>it</includeonly> takes."
        self.assertEqual(expected, str(WParser.parse(self.wiki, text=expected)))


class TestGeneral(QueryTestCase):
    """Tests WParser with more complex, mixed samples of wikitext"""

    def test_mixed_sets(self):
        for i in range(1, 6):
            self.assertEqual(file_to_text(f"parse-result-{i}"), str(WParser.parse(self.wiki, f"User:Fastily/Sandbox/TPTest{i}")))

    def test_sanity(self):
        self.assertTrue(WParser.parse(self.wiki, "Main Page"))
        self.assertTrue(WParser.parse(self.wiki, "Wikipedia:Requests"))


class TestWikiText(TestCase):
    """Tests instance methods of WikiText"""

    def test_iadd(self):

        parts = ("We have said goodbye before ", "so it stands to reason... ", "We'll say hello again.")
        expected = "".join(parts)

        # initializer
        self.assertEqual(expected, str(WikiText(*parts)))

        # Other WikiTexts
        result = WikiText()
        for t in (WikiText(s) for s in parts):
            result += t

        self.assertEqual(expected, str(result))

        # Mixed
        result = WikiText("No amount of money ever", " bought a second of time. \n", WikiTemplate("Wakanda", params={"1": "Forever!"}))
        self.assertEqual("No amount of money ever bought a second of time. \n{{Wakanda|1=Forever!}}", str(result))

    def test_bool(self):
        self.assertTrue(WikiText("I can do this all day"))
        self.assertFalse(WikiText())
