"""Methods and classes for parsing wikitext into a object-oriented format which is easier to work with."""

from __future__ import annotations

import logging

from collections import deque
from contextlib import suppress
from typing import KeysView, TYPE_CHECKING, Union, ValuesView
from xml.etree import ElementTree

from .utils import make_params, mine_for

if TYPE_CHECKING:
    from .wiki import Wiki

log = logging.getLogger(__name__)


class WParser:

    @staticmethod
    def parse(wiki: Wiki, title: str = None, text: str = None):

        if not any((title, text)):
            raise ValueError("Either title or text must be specified")

        pl = make_params("parse", {"prop": "parsetree"} | ({"page": title} if title else {"contentmodel": "wikitext", "text": text}))
        try:
            root = ElementTree.fromstring(mine_for(wiki.client.post(wiki.endpoint, data=pl).json(), "parse", "parsetree"))
            return root
        except Exception as e:
            log.error("%s: Error occured while querying server with params: %s", wiki, pl, exc_info=True)


class WikiText:

    def __init__(self, *elements: Union[str, WikiTemplate]) -> None:
        self.l: list = list(elements)  # TODO FILL ME IN

    def __bool__(self) -> bool:
        return bool(self.l)

    def __iadd__(self, other) -> WikiText:
        if not isinstance(other, (str, WikiTemplate)):
            raise TypeError(f"'{other}' is not a valid type (str, WikiTemplate) for appending to this WikiText")

        if isinstance(other, str) and self.l and isinstance(self.l[-1], str):
            self.l[-1] += other
        else:
            self.l.append(other)

            if isinstance(other, WikiTemplate):
                other.parent = self

        return self

    def __str__(self) -> str:
        return self.as_text(True)

    @property
    def templates(self) -> list[WikiTemplate]:
        return [x for x in self.l if isinstance(x, WikiTemplate)]

    def all_templates(self) -> list[WikiTemplate]:
        out = []
        q = deque(self.templates)
        while q:
            q.extend((curr := q.pop()).templates)
            out.append(curr)

        return out

    def as_text(self, trim: bool = False) -> str:
        out = "".join(str(x) for x in self.l)
        return out.strip() if trim else out


class WikiTemplate:

    def __init__(self, title: str, parent: WikiText = None) -> None:
        self.parent: WikiText = parent
        self.title: str = title
        self.params: dict[str, WikiText] = {}

    def __contains__(self, item) -> bool:
        return isinstance(item, str) and bool(self.params.get(item))

    def __getitem__(self, key) -> WikiText:
        if key not in self:
            raise KeyError(f"'{key}' is not in this WikiText object!")

        return self.params.get(key)

    def __setitem__(self, key, value):
        if not isinstance(value, (str, WikiTemplate, WikiText)):
            raise TypeError(f"{value} is not an acceptable parameter type for WikiTemplate")

        self.params[key] = value if isinstance(value, WikiText) else WikiText(value)

    def __str__(self) -> str:
        return self.as_text()

    def pop(self, k: str) -> WikiText:
        with suppress(KeyError):
            return self.params.pop(k)

    def drop(self) -> None:
        if self.parent:
            self.parent.l.remove(self)
            self.parent = None

    def remap(self, old_key: str, new_key: str) -> None:
        if old_key in self.params:
            self.params[new_key] = self.params.pop(old_key)

    def append_to_params(self, k: str, e: Union[str, WikiTemplate, WikiText]):
        if k in self:
            self[k] += e
        else:
            self[k] = e

    def keys(self) -> KeysView:
        return self.params.keys()

    def values(self) -> ValuesView:
        return self.params.values()

    def as_text(self, indent: bool = False) -> str:
        prefix = ("\n" if indent else "") + "|"
        out = "".join(f"{prefix}{k}={v}" for k, v in self.params.items())
        if indent:
            out += "\n"

        return f"{{{{{self.title}{out}}}}}"

    # TODO: normalize
