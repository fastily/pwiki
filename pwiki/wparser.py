"""Methods and classes for parsing wikitext into a object-oriented format which is easier to work with. BEWARE: This is an experimental module and may not work for 100% of cases; you have been warned..."""

from __future__ import annotations

import logging

from collections import deque
from contextlib import suppress
from typing import Any, Iterator, KeysView, TYPE_CHECKING, Union, ValuesView
from xml.etree import ElementTree

from .dwrap import Revision
from .ns import NS
from .oquery import OQuery
from .utils import has_error, make_params, mine_for, read_error

if TYPE_CHECKING:
    from .wiki import Wiki

log = logging.getLogger(__name__)


class WikiText:
    """Mutable representation of parsed WikiText.  This is basically a container which contains `str` and `WikiTemplate` objects"""

    def __init__(self, *elements: Union[str, WikiTemplate]) -> None:
        """Initializer, creates a new `WikiText` object.

        Args:
            elements (Union[str, WikiTemplate], optional): Default values to initialize this WikiText with.  These will be appended together in the order passed.
        """
        self._l: list = []

        for e in elements:
            self += e

    def __bool__(self) -> bool:
        """Get a bool representation of this WikiText object.

        Returns:
            bool: `True` if this WikiText is not empty.
        """
        return bool(self._l)

    def __iadd__(self, other: Any) -> WikiText:
        """Appends the specified element to the end of this WikiText object.  CAVEAT: if `other` is a `WikiText` object, then other's contents will be merged into this `WikiText`. 

        Args:
            other (Any): A `str` or `WikiTemplate` object

        Raises:
            TypeError: If `other` is not a `str` or `WikiTemplate`

        Returns:
            WikiText: A reference to original, now modified WikiText object
        """
        if isinstance(other, str):
            if not other:
                pass
            elif self._l and isinstance(self._l[-1], str):
                self._l[-1] += other
            else:
                self._l.append(other)
        elif isinstance(other, WikiTemplate):
            self._l.append(other)
            other.parent = self
        elif isinstance(other, WikiText):
            for e in other._l:
                self += e
        else:
            raise TypeError(f"'{other}' is not a valid type (str, WikiTemplate) for appending to this WikiText")

        return self

    def __str__(self) -> str:
        """Gets a `str` representation of this `WikiText` object.

        Returns:
            str: A `str` representation of this `WikiText` object.  Leading and trailing whitespace will be stripped.  If you don't want this, see `as_text()`.
        """
        return self.as_text(True)

    def __eq__(self, o: Any) -> bool:
        """Compares two `WikiText` objects for equality.

        Args:
            o (Any): The object to compare with self.

        Returns:
            bool: True if the objects are the same type and contain the same elements in the same order.
        """
        return isinstance(o, WikiText) and self._l == o._l

    @property
    def templates(self) -> list[WikiTemplate]:
        """Convenience property, gets the templates contained in this WikiText.  CAVEAT: this does not recursively search sub-templates, see `all_templates()` for more details.

        Returns:
            list[WikiTemplate]: A list of `WikiTemplate` objects contained in this `WikiText` (top level only)
        """
        return [x for x in self._l if isinstance(x, WikiTemplate)]

    def all_templates(self) -> list[WikiTemplate]:
        """Recursively finds all templates contained in this `WikiText` and their subtemplates.

        Returns:
            list[WikiTemplate]: all `WikiTemplate` objects contained in this `WikiText` and their subtemplates. 
        """
        out = []
        q = deque(self.templates)
        while q:
            out.append(curr := q.pop())
            for wt in curr.values():
                q.extend(wt.templates)

        return out

    def as_text(self, trim: bool = False) -> str:
        """Generate a `str` representation of this `WikiText`.

        Args:
            trim (bool, optional): Set `True` to remove leading & trailing whitespace. Defaults to False.

        Returns:
            str: A `str` representation of this `WikiText`.
        """
        out = "".join(str(x) for x in self._l)
        return out.strip() if trim else out


class WikiTemplate:
    """Represents a MediaWiki template.  These usually contain a title and parameters."""

    def __init__(self, title: str = None, params: dict[str, Union[str, WikiText]] = None, parent: WikiText = None) -> None:
        """Initializer, creates a new `WikiTemplate` object

        Args:
            title (str, optional): The `name` of this WikiTemplate. Defaults to None.
            params (dict[str, Union[str, WikiText]], optional): Default parameters to initialize this WikiTemplate with.  Defaults to None.
            parent (WikiText, optional): The WikiText associated with this WikiTemplate.  Defaults to None.
        """
        self.title: str = title
        self._params: dict[str, WikiText] = {}
        self.parent: WikiText = parent

        if params:
            for k, v in params.items():
                self[k] = v  # automatically ensure correct typing

    def __bool__(self) -> bool:
        """Get a bool representation of this WikiTemplate object.

        Returns:
            bool: `True` if this WikiTemplate is not empty.
        """
        return bool(self.title)

    def __contains__(self, item: Any) -> bool:
        """Check if the key `item` is the name of a parameter

        Args:
            item (Any): The key to check.  If this is not a `str`, then `False` will be returned.

        Returns:
            bool: `True` if the key `item` is the name of a parameter with a non-empty value in this WikiTemplate.
        """
        return item in self._params

    def __getitem__(self, key: Any) -> WikiText:
        """Returns the parameter value associated with `key` in this `WikiTemplate`'s params

        Args:
            key (Any): The key associated with the value to look up.

        Raises:
            KeyError: If `key` is not the name of a parameter in this WikiTemplate.

        Returns:
            WikiText: The `WikiText` associated with the spceified `key`
        """
        if key not in self:
            raise KeyError(f"'{key}' is not in this WikiTemplate object!")

        return self._params[key]

    def __setitem__(self, key: Any, value: Any):
        """Associates `key` and `value` as entries in this `WikiTemplate`'s parameter list.

        Args:
            key (Any): The key to use.  This must be a `str`.
            value (Any): The value to use.  This must be a `str`, `WikiTemplate`, or `WikiText`.

        Raises:
            TypeError: If `key` or `value` are not acceptable types.
        """
        if not isinstance(key, str):
            raise TypeError(f"{key} is not an acceptable key type for WikiTemplate")
        elif not isinstance(value, (str, WikiTemplate, WikiText)):
            raise TypeError(f"{value} is not an acceptable parameter type for WikiTemplate")

        self._params[key] = value if isinstance(value, WikiText) else WikiText(value)

    def __str__(self) -> str:
        """Generates a `str` representaiton of this WikiTemplate.

        Returns:
            str: The `str` representation of this `WikiTemplate`.  The result will not be indented, see `self.as_text()` for details.
        """
        return self.as_text()

    def __eq__(self, o: Any) -> bool:
        """Compares two `WikiTemplate`s for equality.  Checks for matching titles (does not automatically normalize, if you want this, then call normalize() before checking equality!) and matching parameters.  CAVEAT: does not compare order of parameters (not that it matters anyways)

        Args:
            o (Any): The other object to compare

        Returns:
            bool: True if the objects are simillar.
        """
        return isinstance(o, WikiTemplate) and self.title == o.title and self._params == o._params

    def __iter__(self) -> Iterator:
        """Returns an iterator that iterates over the keys of this WikiTemplate

        Returns:
            Iterator: An iterator with the keys of this WikiTemplate.
        """
        return iter(self.keys())

    def has_key(self, key: str, empty_ok=True) -> bool:
        """Check if the key `item` is the name of a parameter in this WikiTemplate.

        Args:
            key (str): The key to check. 
            empty_ok (bool, optional): Set `False` to enable an additional check for whether the value assoaciated with `key` is non-empty. Defaults to True.

        Returns:
            bool: `True` if `key` exists in this `WikiTemplate`.  If `empty_ok` is `False`, then `True` will be returned if the value assoaciated with `key` is also non-empty.
        """
        return key in self and (empty_ok or bool(self._params.get(key)))

    def pop(self, k: str = None) -> WikiText:
        """Removes the key, `k`, and its associated value from this `WikiTemplate`'s parameters, and then return the value.

        Args:
            k (str, optional): The key to lookup.  If `None`, then an arbitrary key-value pair will be popped.  Defaults to None.

        Returns:
            WikiText: The value formerly associated with `k`.  `None` if `k` is not in this `WikiTemplate`.
        """
        with suppress(KeyError):
            return self._params.pop(k) if k else self._params.popitem()[1]

    def drop(self) -> None:
        """If possible, remove this `WikiTemplate` from its parent `WikiText`."""
        if self.parent:
            self.parent._l.remove(self)
            self.parent = None

    def remap(self, old_key: str, new_key: str) -> None:
        """Remap a key in this `WikiTemplate`'s parameters.

        Args:
            old_key (str): The key to remap.  If this key does not exist in this WikiTemplate, then this method exits without making any changes.
            new_key (str): The key to remap the value associated with `old_key` to.
        """
        if old_key in self:
            self[new_key] = self.pop(old_key)

    def touch(self, k) -> None:
        """If `k` does not exist in this WikiTemplate, create a mapping for `k` to an empty `WikiText`

        Args:
            k ([type]): [description]
        """
        if k not in self:
            self[k] = WikiText()

    def append_to_params(self, k: str, e: Union[str, WikiTemplate, WikiText]):
        """Appends `e` to the value associated with `k`. If `k` does not exist in this WikiTemplate, then a new entry will be created.

        Args:
            k (str): The key to lookup
            e (Union[str, WikiTemplate, WikiText]): The element to append to the value associated with `k`.
        """
        if k in self:
            self[k] += e
        else:
            self[k] = e

    def get_param(self, k: str, default: Union[str, WikiText] = None) -> Union[str, WikiText]:
        """Returns the parameter value associated with `k` in this `WikiTemplate`'s params

        Args:
            k (str): The key associated with the value to look up.
            default (Union[str, WikiText], optional): The value to return if `k` is not a parameter in this `WikiTemplate`. Defaults to None.

        Returns:
            WikiText: The `WikiText` associated with the specified `k`, otherwise `default` 
        """
        return self._params.get(k, default)

    def set_param(self, k: str, v: Union[str, WikiText, WikiTemplate]) -> None:
        """Associates key `k` with value `v` in this `WikiTemplate`'s parameter list.  Alias of `self[k] = v`.

        Args:
            k (str): The key to use
            v (Union[str, WikiText, WikiTemplate]): The value to associate with `k`
        """
        self[k] = v

    def keys(self) -> KeysView:
        """Gets the parameter keys in this WikiTemplate

        Returns:
            KeysView: The keys in this WikiTemplate
        """
        return self._params.keys()

    def values(self) -> ValuesView:
        """Gets the parameter values in this WikiTemplate

        Returns:
            ValuesView: The values contained in this WikiTemplate
        """
        return self._params.values()

    def as_text(self, indent: bool = False) -> str:
        """Renders this `WikiTemplate` as wikitext, in `str` form.

        Args:
            indent (bool, optional): Set `True` to include newlines so as to 'pretty-print' this `WikiTemplate`. Defaults to False.

        Returns:
            str: The `WikiTemplate` rendered as wikitext.
        """
        prefix = ("\n" if indent else "") + "|"
        out = "".join(f"{prefix}{k}={v}" for k, v in self._params.items())
        if indent:
            out += "\n"

        return f"{{{{{self.title}{out}}}}}"

    @staticmethod
    def normalize(wiki: Wiki, *tl: WikiTemplate, bypass_redirects: bool = False) -> list[WikiTemplate]:
        """Normalizes titles of templates.  This usually fixes capitalization and removes random underscores.

        Args:
            wiki (Wiki): The `Wiki` object to use.  The `WikiTemplate` titles will be normalized against this `Wiki`.
            tl (WikiTemplate): The `WikiTemplate` objects to normalize.
            bypass_redirects (bool, optional): Set `True` to also bypass redirects. Defaults to False.

        Returns:
            list[WikiTemplate]: The WikiTemplates passed in as `tl`, for chaining convenience.
        """
        m = {t.title: t for t in tl}
        for k, v in OQuery.normalize_titles(wiki, list(m.keys())).items():
            m[k].title = wiki.nss(v) if wiki.in_ns(v, NS.TEMPLATE) else v

        if bypass_redirects:
            m = {(wiki.convert_ns(t.title, NS.TEMPLATE) if wiki.in_ns(t.title, NS.MAIN) else t.title): t for t in tl}
            for k, v in OQuery.resolve_redirects(wiki, list(m.keys())).items():
                m[k].title = wiki.nss(v) if wiki.in_ns(v, NS.TEMPLATE) else v

        return list(tl)


class WikiExt:
    """Represents an extension tag.  Extensions technically aren't supported, so this is a meta class which will be interpreted as WikiText during lexing."""

    def __init__(self, name: str = None, attr: str = None, inner: WikiText = None, close: str = None) -> None:
        """Creates a new `WikiExt` object

        Args:
            name (str, optional): The name of the extension tag. Defaults to None.
            attr (str, optional): The attribute str of the extension tag. Defaults to None.
            inner (WikiText, optional): The inner text of the tag. Defaults to None.
            close (str, optional): The closing tag (including carets). Defaults to None.
        """
        self.name: str = name
        self.attr: str = attr
        self.inner: WikiText = inner
        self.close: str = close

    def _squash(self) -> WikiText:
        """Converts this `WikiExt` to `WikiText`.  Specifically: converts the tag back into wikitext, and preserves `WikiTemplate` objects.

        Returns:
            WikiText: The resulting `WikiText` object
        """
        return WikiText(f"<{self.name}{self.attr or ''}>", self.inner, self.close)


class WParser:
    """Entry point for the WParser module"""

    @staticmethod
    def _basic_parse(wiki: Wiki, pl: dict = None, big_query: bool = False, desc: str = "perform a parse action") -> dict:
        """Template for performing a parse action on the server.  Also performs error checking on the result from the server.

        Args:
            wiki (Wiki): The Wiki object to use.
            pl (dict, optional): The parameter list to send.  Omit `&action=parse`, this will be applied automatically. Defaults to None.
            big_query (bool, optional): Set `True` to send the request as a `POST`. Useful for avoiding 414 errors. Defaults to False.
            desc (str, optional): A description to use when logging this call. Defaults to "perform a parse action".

        Returns:
            dict: The response from the server, without the parent `parse` object.
        """
        pl = make_params("parse", pl)
        try:
            if not (response := (wiki.client.post(wiki.endpoint, data=pl) if big_query else wiki.client.get(wiki.endpoint, params=pl)).json()):
                log.error("%s: No response from server while trying to %s", wiki, desc)
                log.debug("Sent parameters: %s", pl)
                return
        except Exception:
            log.error("Failed to reach server or recieved an invalid respnose while trying to %s.",  desc, exc_info=True)

        if not has_error(response):
            return mine_for(response, "parse")

        log.error("%s: encountered error while trying to %s, server said: %s", wiki, desc, read_error("parse", response))
        log.debug(response)

    @staticmethod
    def revision_metadata(wiki: Wiki, r: Revision, categories: bool = False, external_links: bool = False, images: bool = False, links: bool = False, templates: bool = False) -> dict:
        """Fetches metadata from the `Revision`, `r`.

        Args:
            wiki (Wiki): The Wiki object to use
            r (Revision): The `Revision` to get metadata of
            categories (bool, optional): Set `True` to get the categories contained in this `Revision`. Defaults to False.
            external_links (bool, optional): Set `True` to get the external links contained in this `Revision`. Defaults to False.
            images (bool, optional): Set `True` to get the files contained in this `Revision`. Defaults to False.
            links (bool, optional): Set `True` to get the links contained in this `Revision`. Defaults to False.
            templates (bool, optional): Set `True` to get the templates contained in this `Revision`. Defaults to False.

        Returns:
            dict: A `dict` where each key is the type of metadata (these match the `bool` parameters of this method), and each value is a `list` with the associated type of metadata.
        """
        props = []
        if categories:
            props.append("categories")
        if external_links:
            props.append("externallinks")
        if images:
            props.append("images")
        if links:
            props.append("links")
        if templates:
            props.append("templates")

        if not (result := WParser._basic_parse(wiki, {"prop": "|".join(props), "oldid": r.revid}, desc="retrieve revision metadata")):
            return

        out = {}
        for k, v in result.items():
            if k == "categories":
                out[k] = wiki.ns_manager.batch_convert_ns([e["category"] for e in v], NS.CATEGORY, True)
            elif k == "externallinks":
                out["external_links"] = v
            elif k == "images":
                out[k] = wiki.ns_manager.batch_convert_ns(v, NS.FILE, True)
            elif k in ("links", "templates"):
                out[k] = [e["title"] for e in v]

        return out

    @staticmethod
    def parse(wiki: Wiki, title: str = None, text: str = None) -> WikiText:
        """Parses the title or text into `WikiText`/`WTemplate` objects.  If `title` and `text` are both specified, then `text` will be parsed as if it was on `title`.

        Args:
            wiki (Wiki): The Wiki object to use.
            title (str, optional): The title to use.  If `text` is not specified, then the text of `title` will be automatically fetched and parsed. Defaults to None.
            text (str, optional): The text to parse. If `title` is specified, then the text will be parsed as if it is was published on `title`. Defaults to None.

        Raises:
            ValueError: If `title` and `text` are both `None`.

        Returns:
            WikiText: The result of the parsing operation.  `None` if something went wrong.
        """
        if not any((title, text)):
            raise ValueError("Either title or text must be specified")

        pl = {"prop": "parsetree"}
        if title:
            pl["title" if text else "page"] = title
        if text:
            pl |= {"contentmodel": "wikitext", "text": text}

        if not (response := WParser._basic_parse(wiki, pl, True)):
            return

        raw_xml = mine_for(response, "parsetree")
        # log.debug(raw_xml)
        return WParser._parse_wiki_text(ElementTree.fromstring(raw_xml))

    @staticmethod
    def _parse_wiki_text(root: ElementTree.Element, flatten: bool = True) -> WikiText:
        """Parses an XML `Element` as `WikiText`

        Args:
            root (ElementTree.Element): The `Element` to parse
            flatten (bool, optional): `True` causes flattening of (extract text only) non-`template` tags (e.g. `comment`, `h1`).  `False` causes these to be skipped completely. Defaults to True.

        Returns:
            WikiText: The resulting `WikiText` from parsing
        """
        out = WikiText()

        if root.text:
            out += root.text

        for x in root:
            if x.tag == "template":
                out += WParser._parse_wiki_template(x)
            elif x.tag == "ext":
                out += WParser._parse_wiki_ext(x)
            elif flatten:  # catches reamining tags and tries to make sense of them
                out += WParser._parse_wiki_text(x, flatten)  # handle templates in h1 tags

            if x.tail:
                out += x.tail

        return out

    @staticmethod
    def _parse_wiki_ext(root: ElementTree.Element) -> WikiText:
        """Parses an XML `Element` as a `WikiExt`, and then converts the result into a `WikiText` object.

        Args:
            root (ElementTree.Element): The `Element` to parse

        Returns:
            WikiText: The resulting `WikiText` from parsing
        """
        out = WikiExt()

        for x in root:
            if x.tag == "name":
                out.name = x.text
            elif x.tag == "attr":
                out.attr = x.text
            elif x.tag == "inner":
                out.inner = WParser._parse_wiki_text(x)
            elif x.tag == "close":
                out.close = x.text

        return out._squash()

    @staticmethod
    def _parse_wiki_template(root: ElementTree.Element) -> WikiTemplate:
        """Parses an XML `Element` as a `WikiTemplate`.

        Args:
            root (ElementTree.Element): The `Element` to parse

        Returns:
            WikiTemplate: The resulting `WikiTemplate` from parsing 
        """
        out = WikiTemplate()

        for x in root:
            if x.tag == "title":
                out.title = str(WParser._parse_wiki_text(x, False))  # handles comments in template title <_<
            elif x.tag == "part":
                out.set_param(*WParser._parse_template_parameter(x))

        return out

    @staticmethod
    def _parse_template_parameter(root: ElementTree.Element) -> tuple[str, WikiText]:
        """Parses an XML `Element` as the parameter of a `WikiTemplate`.

        Args:
            root (ElementTree.Element): The `Element` to parse 

        Returns:
            tuple[str, WikiText]:A tuple where the first element is the key of the parameter, and the second element of the tuple is the value of the parameter.
        """
        key = value = None

        for x in root:
            if x.tag == "name":
                key = x.get("index") or x.text.strip()
            elif x.tag == "value":
                value = WParser._parse_wiki_text(x)

        return key, value
