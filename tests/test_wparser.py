from unittest.case import expectedFailure
from textwrap import dedent

from pwiki.wparser import WParser

from .base import QueryTestCase


class TestSimple(QueryTestCase):
    """Tests WParser with simple snippets of wikitext"""

    def test_wikitext(self):
        expected = "Hello, World!"
        self.assertEqual(expected, str(WParser.parse(self.wiki, text=expected)))

        expected = "      So long, and thanks for all the fish!\n\n"
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

        raw_result = WParser.parse(self.wiki, text="{{Execute|order|66}}")
        self.assertEqual("{{Execute|1=order|2=66}}", str(raw_result))
        self.assertEqual(dedent("""\
            {{Execute
            |1=order
            |2=66
            }}"""), raw_result.templates[0].as_text(True))

    def test_ext(self):
        expected = "Perfectly <nowiki>balanced, as all things</nowiki> should be."
        self.assertEqual(expected, str(WParser.parse(self.wiki, text=expected)))

        expected = dedent("""\
            <syntaxhighlight lang="python" line='line'>
            print("A thing isn't beautiful because it lasts.")
            </syntaxhighlight>""")
        self.assertEqual(expected, str(WParser.parse(self.wiki, text=expected)))


class TestMixed(QueryTestCase):
    """Tests WParser with more complex, mixed samples of wikitext"""
    pass


class TestSanity(QueryTestCase):
    """Smoke tests of complex pages.  Just checking for crashes"""

    def test_sanity(self):
        pass
