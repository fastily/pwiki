from textwrap import dedent

from pwiki.wparser import WikiExt, WikiTemplate, WikiText, WParser

from .base import file_to_text, WikiTestCase

from unittest import TestCase


class TestElementHandling(WikiTestCase):
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


class TestGeneral(WikiTestCase):
    """Tests WParser with more complex, mixed samples of wikitext"""

    def test_mixed_sets(self):
        for i in range(1, 6):
            self.assertEqual(file_to_text(f"parse-result-{i}"), str(WParser.parse(self.wiki, f"User:Fastily/Sandbox/TPTest{i}")))

    def test_sanity(self):
        self.assertTrue(WParser.parse(self.wiki, "Main Page"))
        self.assertTrue(WParser.parse(self.wiki, "Wikipedia:Requests"))

    def test_revision_metadata(self):
        revs = self.wiki.revisions("User:Fastily/Sandbox/RevisionParse")
        self.assertEqual(4, len(revs))

        self.assertDictEqual({
            "categories": ["Category:Fastily Test"],
            "external_links": ["https://github.com"],
            "images": ["File:FastilyTestCircle2.svg"],
            "links": ["User:Fastily"],
            "templates": ["Template:FastilyTest"]}, WParser.revision_metadata(self.wiki, revs[1], True, True, True, True, True))

        self.assertDictEqual({}, WParser.revision_metadata(self.wiki, revs[0]))
        self.assertDictEqual(dict.fromkeys(["categories", "external_links"], []), WParser.revision_metadata(self.wiki, revs[0], True, True))


class TestWikiText(TestCase):
    """Tests instance methods of `WikiText`"""

    def test_iadd(self):
        parts = ("We have said goodbye before ", "so it stands to reason... ", "We'll say hello again.")
        expected = "".join(parts)

        # Initializer
        self.assertEqual(expected, str(WikiText(*parts)))

        # Other WikiTexts
        result = WikiText()
        for t in (WikiText(s) for s in parts):
            result += t

        self.assertEqual(expected, str(result))

        # Mixed
        result = WikiText("No amount of money ever", " bought a second of time. \n", WikiTemplate("Wakanda", {"1": "Forever!"}))
        self.assertEqual("No amount of money ever bought a second of time. \n{{Wakanda|1=Forever!}}", str(result))

    def test_bool(self):
        self.assertTrue(WikiText("We are Groot"))
        self.assertFalse(WikiText())

    def test_str(self):
        raw = "\n\nI am Iron Man     "
        self.assertEqual(raw, WikiText(raw).as_text())
        self.assertEqual(raw.strip(), str(WikiText(raw)))

    def test_eq(self):
        raw1 = "I have nothing to prove to you."
        raw2 = "That's not a cat.  That's a Flerken!"
        self.assertEqual(WikiText(raw1), WikiText(raw1))
        self.assertNotEqual(WikiText(raw1), WikiText(raw2))

        self.assertEqual(WikiText(raw1, WikiTemplate("Iron", {"1": "Monger"})), WikiText(raw1, WikiTemplate("Iron", {"1": "Monger"})))
        self.assertNotEqual(WikiText(raw1, WikiTemplate("Iron", {"1": "Monger"})), WikiText(raw1, WikiTemplate("War", {"1": "Machine"})))

    def test_as_text(self):
        wt = WikiText(" Space ", WikiTemplate("Tesseract", {"1": "blue"}), WikiText(" Stone\n\n"))
        expected = " Space {{Tesseract|1=blue}} Stone\n\n"
        self.assertEqual(expected, wt.as_text())
        self.assertEqual(expected.strip(), wt.as_text(True))

    def test_templates(self):
        # no templates
        wt = WikiText()
        self.assertFalse(wt.templates)

        wt = WikiText("Groot")
        self.assertFalse(wt.templates)

        # multiples
        t1 = WikiTemplate("Sceptre", {"1": "yellow"})
        t2 = WikiTemplate("Eye of Agamotto", {"2": "green"})
        result = WikiText("You want my property? ", t1, "You can't have it!", t2).templates

        self.assertIn(t1, result)
        self.assertIn(t2, result)
        self.assertEqual(2, len(result))

        # nesting
        t1 = WikiTemplate("S.H.I.E.L.D.")
        t2 = WikiTemplate("Heli", {"carrier": WikiText(t1)})
        raw = WikiText("Avengers ", t2, " Initiative")
        result = raw.templates
        self.assertIn(t2, result)
        self.assertEqual(1, len(result))

        result = raw.all_templates()
        self.assertIn(t1, result)
        self.assertIn(t2, result)
        self.assertEqual(2, len(result))


class TestWikiTemplate(WikiTestCase):
    """Tests instance methods of `WikiTemplate`"""

    def test_bool(self):
        self.assertTrue(WikiTemplate("Secret Woods"))
        self.assertFalse(WikiTemplate(""))
        self.assertFalse(WikiTemplate())

    def test_contains(self):
        t = WikiTemplate("Saloon", {"1": "Stardrop", "host": "Gus"})

        self.assertIn("host", t)
        self.assertIn("1", t)
        self.assertNotIn("Penny", t)

    def test_get_item(self):
        t = WikiTemplate("Museum", {"curator": "Gunther"})
        self.assertEqual(WikiText("Gunther"), t["curator"])

        with self.assertRaises(KeyError):
            _ = t["junimo"]

    def test_set_item(self):
        t = WikiTemplate("Ginger Island", {"villager": "Leo"})

        self.assertNotIn("hut", t)
        t["hut"] = "Birdie"
        self.assertIn("hut", t)

        t1 = WikiTemplate("Host", {"1": "Mr. Qi"})
        self.assertNotIn("Walnut Room", t)
        t["Walnut Room"] = t1
        self.assertIn("Walnut Room", t)

        with self.assertRaises(TypeError):
            t["Volcano"] = 1

    def test_str(self):
        t = WikiTemplate("Community Center", {"status": "restored"})
        self.assertEqual("{{Community Center|status=restored}}", str(t))

        t["pantry"] = WikiTemplate("Bundle", {"reward": "Greenhouse"})

        self.assertEqual("{{Community Center|status=restored|pantry={{Bundle|reward=Greenhouse}}}}", str(t))

    def test_eq(self):
        t1 = WikiTemplate("General Store", {"owner": "Pierre"})
        t2 = WikiTemplate("Tower", {"owner": "Wizard", "Ex": WikiTemplate("NPC", {"1": "Witch"})})

        self.assertEqual(t1, WikiTemplate("General Store", {"owner": "Pierre"}))
        self.assertEqual(t2, WikiTemplate("Tower", {"owner": "Wizard", "Ex": WikiTemplate("NPC", {"1": "Witch"})}))
        self.assertNotEqual(t1, t2)

    def test_iter(self):
        t = WikiTemplate("Spring Crops", {"1": "Parsnip", "2": "Strawberry", "3": "Cauliflower", "4": "Blue Jazz"})
        self.assertCountEqual(t.keys(), [k for k in t])

    def test_has_key(self):
        t = WikiTemplate("Town", {"1": "Pelican Town", "2": ""})

        self.assertTrue(t.has_key("1"))
        self.assertTrue(t.has_key("1", False))
        self.assertTrue(t.has_key("2"))
        self.assertFalse(t.has_key("2", False))

        self.assertFalse(t.has_key("3"))
        self.assertFalse(t.has_key("3", False))

    def test_pop(self):
        t = WikiTemplate("Beach", {"1": "Willy", "2": "Elliot"})

        self.assertIn("1", t)
        self.assertEqual(WikiText("Willy"), t.pop("1"))
        self.assertNotIn("1", t)

        self.assertIsNone(t.pop("5"))

        self.assertIn("2", t)
        self.assertEqual(WikiText("Elliot"), t.pop())
        self.assertNotIn("2", t)

    def test_drop(self):
        t = WikiTemplate("Mountain", {"1": WikiTemplate("NPC", {"1": "Linus"}), "2": WikiTemplate("NPC", {"1": "Robin"}), "3": WikiTemplate("NPC", {"1": "Demetrius"})})

        target = t["2"].templates[0]
        self.assertEqual(t["2"], target.parent)
        self.assertIn("2", t)

        target.drop()

        self.assertIsNone(target.parent)
        self.assertIn("2", t)
        self.assertFalse(t["2"])

    def test_remap(self):
        t = WikiTemplate("Town", {"1": WikiTemplate("NPC", {"1": "Haley"}), "2": WikiTemplate("NPC", {"1": "Emily"}), "3": WikiTemplate("NPC", {"1": "Penny"})})

        target = t["3"]
        self.assertIn("3", t)

        t.remap("3", "teacher")

        self.assertNotIn("3", t)
        self.assertIn("teacher", t)
        self.assertEqual(target, t["teacher"])

        # should not fail
        t.remap("4", "?")

    def test_touch(self):
        t = WikiTemplate("General Store", {"1": WikiTemplate("NPC", {"1": "Abigail"}), "2": WikiTemplate("NPC", {"1": "Pierre"})})

        self.assertNotIn("3", t)

        t.touch("3")

        self.assertIn("3", t)
        self.assertTrue(t.has_key("3"))
        self.assertFalse(t.has_key("3", False))

    def test_append_to_params(self):
        t = WikiTemplate("NPC", {"name": "Le"})

        self.assertEqual(WikiText("Le"), t["name"])
        t.append_to_params("name", "ah")
        self.assertEqual(WikiText("Leah"), t["name"])

        self.assertNotIn("occupation", t)
        t.append_to_params("occupation", WikiText("Artist"))
        self.assertIn("occupation", t)
        self.assertEqual(WikiText("Artist"), t["occupation"])

        t["gifts"] = "truffle, "
        t.append_to_params("gifts", WikiTemplate("Item", {"name": "Wine"}))
        self.assertIn("gifts", t)
        self.assertEqual(WikiText("truffle, ", WikiTemplate("Item", {"name": "Wine"})), t["gifts"])

    def test_get_param(self):
        t = WikiTemplate("NPC", {"name": "Sandy", "location": "Oasis"})
        self.assertEqual("Sandy", str(t.get_param("name")))
        self.assertEqual("Sweet Pea", str(t.get_param("gifts", WikiText("Sweet Pea"))))
        self.assertEqual("Sweet Pea", t.get_param("gifts", "Sweet Pea"))

        self.assertIsNone(t.get_param("gifts"))

    def test_set_param(self):
        t = WikiTemplate("NPC", {"name": "Clint"})

        self.assertNotIn("birthday", t)
        t.set_param("birthday", "Winter 26")
        self.assertIn("birthday", t)

    def test_keys(self):
        self.assertCountEqual(("1", "2"), WikiTemplate("Mountain", {"1": WikiTemplate("NPC", {"1": "Dwarf"}), "2": WikiTemplate("NPC", {"1": "Maru"})}).keys())

    def test_values(self):
        t1 = WikiTemplate("NPC", {"1": "Dwarf"})
        t2 = WikiTemplate("NPC", {"1": "Maru"})
        self.assertCountEqual((WikiText(t1), WikiText(t2)), WikiTemplate("Mountain", {"1": t1, "2": t2}).values())

    def test_as_text(self):
        t = WikiTemplate("Town", {"1": WikiTemplate("NPC", {"1": "Kent"}), "2": WikiTemplate("NPC", {"1": "Vincent"})})

        self.assertEqual("{{Town|1={{NPC|1=Kent}}|2={{NPC|1=Vincent}}}}", t.as_text())
        self.assertEqual(dedent("""\
            {{Town
            |1={{NPC|1=Kent}}
            |2={{NPC|1=Vincent}}
            }}"""), t.as_text(True))

    def test_normalize(self):
        t1 = WikiTemplate("general_store", {"1": WikiTemplate("npc", {"1": "Abigail"})})
        t2 = WikiTemplate("pelIcaN tOWN")
        t3 = WikiTemplate("wikipedia Talk:pelIcaN tOWN")
        t4 = WikiTemplate("wp:sKull cavern")

        WikiTemplate.normalize(self.wiki, t1, t2, t3, t4)

        self.assertEqual("General store", t1.title)
        self.assertEqual(WikiText(WikiTemplate("npc", {"1": "Abigail"})), t1["1"])

        self.assertEqual("PelIcaN tOWN", t2.title)
        self.assertEqual("Wikipedia talk:PelIcaN tOWN", t3.title)
        self.assertEqual("Wikipedia:SKull cavern", t4.title)

    def test_normalize_bypass_redirect(self):
        t1 = WikiTemplate("user:fastily/Sandbox/Redirect2")
        t2 = WikiTemplate("user:Fastily/Sandbox/Redirect3")
        t3 = WikiTemplate("User:Fastily/DoesNotExist123")

        WikiTemplate.normalize(self.wiki, t1, t2, t3, bypass_redirects=True)

        self.assertEqual("User:Fastily/Sandbox/RedirectTarget", t1.title)
        self.assertEqual("User:Fastily/Sandbox/Redirect3", t2.title)
        self.assertEqual("User:Fastily/DoesNotExist123", t3.title)

        # namespace mangling in template namespace
        t = WikiTemplate("fastilyTest2")
        self.assertListEqual([t], WikiTemplate.normalize(self.wiki, t, bypass_redirects=True))
        self.assertEqual("FastilyTest", t.title)


class TestWikiExt(WikiTestCase):
    """Tests instance methods of `WikiExt`"""

    def test_sanity(self):
        self.assertEqual(WikiText("<nowiki>Execute Order 66</nowiki>"), WikiExt("nowiki", inner="Execute Order 66", close="</nowiki>")._squash())
        self.assertEqual(WikiText("<syntaxhighlight lang='python'>print('Luke, I am your father.')</syntaxhighlight>"), WikiExt("syntaxhighlight", " lang='python'", "print('Luke, I am your father.')", "</syntaxhighlight>")._squash())
