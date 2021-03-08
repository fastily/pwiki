"""Methods and classes for parsing wikitext into a object-oriented format which is easier to work with."""

from __future__ import annotations

import logging

from collections import deque
from contextlib import suppress
from typing import Any, KeysView, TYPE_CHECKING, Union, ValuesView
from xml.etree import ElementTree

from .utils import make_params, mine_for

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
        self.l: list = []

        for e in elements:
            self += e

    def __bool__(self) -> bool:
        """Get a bool representation of this WikiText object.

        Returns:
            bool: `True` if this WikiText is not empty.
        """
        return bool(self.l)

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
            elif self.l and isinstance(self.l[-1], str):
                self.l[-1] += other
            else:
                self.l.append(other)
        elif isinstance(other, WikiTemplate):
            self.l.append(other)
            other.parent = self
        elif isinstance(other, WikiText):
            for e in other.l:
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

    @property
    def templates(self) -> list[WikiTemplate]:
        """Convenience property, gets the templates contained in this WikiText.  CAVEAT: this does not recursively search sub-templates, see `all_templates()` for more details.

        Returns:
            list[WikiTemplate]: A list of `WikiTemplate` objects contained in this `WikiText` (top level only)
        """
        return [x for x in self.l if isinstance(x, WikiTemplate)]

    def all_templates(self) -> list[WikiTemplate]:
        """Recursively finds all templates contained in this `WikiText` and their subtemplates.

        Returns:
            list[WikiTemplate]: all `WikiTemplate` objects contained in this `WikiText` and their subtemplates. 
        """
        out = []
        q = deque(self.templates)
        while q:
            q.extend((curr := q.pop()).templates)
            out.append(curr)

        return out

    def as_text(self, trim: bool = False) -> str:
        """Generate a `str` representation of this `WikiText`.

        Args:
            trim (bool, optional): Set `True` to remove leading & trailing whitespace. Defaults to False.

        Returns:
            str: A `str` representation of this `WikiText`.
        """
        out = "".join(str(x) for x in self.l)
        return out.strip() if trim else out


class WikiTemplate:
    """Represents a MediaWiki template.  These usually contain a title and parameters."""

    def __init__(self, title: str = None, parent: WikiText = None) -> None:
        """Initializer, creates a new `WikiTemplate` object

        Args:
            title (str, optional): The `name` of this WikiTemplate. Defaults to None.
            parent (WikiText, optional): The WikiText associated with this WikiTemplate.  Defaults to None.
        """
        self.parent: WikiText = parent
        self.title: str = title
        self.params: dict[str, WikiText] = {}

    def __contains__(self, item: Any) -> bool:
        """Check if the key `item` is the name of a parameter

        Args:
            item (Any): The key to check.  If this is not a `str`, then `False` will be returned.

        Returns:
            bool: `True` if the key `item` is the name of a parameter with a non-empty value in this WikiTemplate.
        """
        return item in self.params

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

        return self.params[key]

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

        self.params[key] = value if isinstance(value, WikiText) else WikiText(value)

    def __str__(self) -> str:
        """Generates a `str` representaiton of this WikiTemplate.

        Returns:
            str: The `str` representation of this `WikiTemplate`.  The result will not be indented, see `self.as_text()` for details.
        """
        return self.as_text()

    def has_key(self, key: str, empty_ok=True) -> bool:
        """Check if the key `item` is the name of a parameter in this WikiTemplate.

        Args:
            key (str): The key to check. 
            empty_ok (bool, optional): Set `False` to enable an additional check for whether the value assoaciated with `key` is non-empty. Defaults to True.

        Returns:
            bool: `True` if `key` exists in this `WikiTemplate`.  If `empty_ok` is `False`, then `True` will be returned if the value assoaciated with `key` is also non-empty.
        """
        return key in self and (empty_ok or bool(self.params.get(key)))

    def pop(self, k: str) -> WikiText:
        """Removes the key, `k`, and its associated value from this `WikiTemplate`'s parameters, and then return the value.

        Args:
            k (str): The key to lookup

        Returns:
            WikiText: The value formerly associated with `k`.  `None` if `k` is not in this `WikiTemplate`.
        """
        with suppress(KeyError):
            return self.params.pop(k)

    def drop(self) -> None:
        """If possible, remove this `WikiTemplate` from its parent `WikiText`."""
        if self.parent:
            self.parent.l.remove(self)
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
        return self.params.keys()

    def values(self) -> ValuesView:
        """Gets the parameter values in this WikiTemplate

        Returns:
            ValuesView: The values contained in this WikiTemplate
        """
        return self.params.values()

    def as_text(self, indent: bool = False) -> str:
        """Renders this `WikiTemplate` as wikitext, in `str` form.

        Args:
            indent (bool, optional): Set `True` to include newlines so as to 'pretty-print' this `WikiTemplate`. Defaults to False.

        Returns:
            str: The `WikiTemplate` rendered as wikitext.
        """
        prefix = ("\n" if indent else "") + "|"
        out = "".join(f"{prefix}{k}={v}" for k, v in self.params.items())
        if indent:
            out += "\n"

        return f"{{{{{self.title}{out}}}}}"

    # TODO: group normalize


class WParser:

    @staticmethod
    def parse(wiki: Wiki, title: str = None, text: str = None):

        if not any((title, text)):
            raise ValueError("Either title or text must be specified")

        pl = make_params("parse", {"prop": "parsetree"} | ({"page": title} if title else {"contentmodel": "wikitext", "text": text}))
        try:
            root = ElementTree.fromstring(mine_for(wiki.client.post(wiki.endpoint, data=pl).json(), "parse", "parsetree"))
            return root
        except Exception:
            log.error("%s: Error occured while querying server with params: %s", wiki, pl, exc_info=True)

    @staticmethod
    def parse_wiki_text(root: ElementTree.Element, flatten: bool = True) -> WikiText:
        out = WikiText()

        if root.text:
            out += root.text

        for x in root:
            if x.tag == "template":
                out += WParser.parse_wiki_template(x)
            elif flatten:
                out += x.text

            if x.tail:
                out += x.tail

        return out

    @staticmethod
    def parse_wiki_template(root: ElementTree.Element):
        out = WikiTemplate()

        for x in root:
            if x.tag == "title":
                out.title = str(WParser.parse_wiki_text(x, False))  # handle comments in template title
            elif x.tag == "part":
                out.set_param(*WParser.parse_template_parameter(x))

        return out

    @staticmethod
    def parse_template_parameter(root: ElementTree.Element) -> tuple[str, WikiText]:
        key = value = None

        for x in root:
            if x.tag == "name":
                key = x.get("index") or x.text.strip()
            elif x.tag == "value":
                value = WParser.parse_wiki_text(x)

        return key, value
