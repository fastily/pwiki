"""Classes and methods for handling namespaces on a Wiki"""

import logging
import re

from collections.abc import Iterable
from enum import IntEnum
from typing import Union


log = logging.getLogger(__name__)

MAIN_NAME = "Main"


class NS(IntEnum):
    """Default namespace IDs, for convenience"""
    MAIN = 0
    TALK = 1
    USER = 2
    USER_TALK = 3
    PROJECT = 4
    PROJECT_TALK = 5
    FILE = 6
    FILE_TALK = 7
    MEDIAWIKI = 8
    MEDIAWIKI_TALK = 9
    TEMPLATE = 10
    TEMPLATE_TALK = 11
    HELP = 12
    HELP_TALK = 13
    CATEGORY = 14
    CATEGORY_TALK = 15


class NSManager:
    """Manages the pairings (id -> name) and (name -> id) of the namespaces on a Wiki.  Also contains methods for performing lexical operations with namespaces"""

    def __init__(self, r: dict) -> None:
        """Creates a new NSManager.

        Args:
            r (dict): The response from the server.  This should be the json object directly under the `"query"` object.
        """
        self.m = {}

        l = []
        for v in r["namespaces"].values():
            id = v["id"]
            name = v["name"] or MAIN_NAME

            self.m[id] = name
            self.m[name] = id
            l.append(name)

            # handle canonical namespaces (e.g. Project is also Wikipedia)
            if (canonical := v.get("canonical")) and canonical != v["name"]:
                self.m[canonical] = id
                l.append(canonical)

        # handle aliases
        self.m |= (aliases := {e["alias"]: e["id"] for e in r["namespacealiases"]})
        l += aliases.keys()

        self.ns_regex = re.compile(f'(?i)^({"|".join([s.replace(" ", "[ |]") for s in l])}):')

    def batch_convert_ns(self, titles: Iterable[str], ns: Union[str, NS], replace_underscores: bool = False) -> list[str]:
        """Convenience method, converts an Iterable of titles to another namespace.  PRECONDITION: titles in `titles` are well-formed.

        Args:
            titles (Iterable[str]): The titles to convert
            ns (Union[str, NS]): The namespace to convert the titles to
            replace_underscores (bool, optional): Set `True` to replace underscore characters with the space characters in the returned value. Defaults to False.

        Returns:
            list[str]: The titles converted to namespace `ns`.
        """
        prefix = self.canonical_prefix(ns)
        return [prefix + self.nss(t) for t in ([s.replace("_", " ") for s in titles] if replace_underscores else titles)]

    def canonical_prefix(self, ns: Union[NS, str]) -> str:
        """Gets the canonical prefix for the specified namespace.  This adds a `:` suffix to `ns`, or returns the empty string if `ns` is the Main namespace.

        Args:
            ns (Union[NS, str]): The namespace to get the canonical prefix for.

        Returns:
            str: The canonical prefix for the specified namepsace.
        """
        return "" if (ns := self.stringify(ns)) == MAIN_NAME else ns + ":"

    def create_filter(self, nsl: Union[list[Union[NS, str]], NS, str]) -> str:
        """Convenience method, creates a pipe-fenced namespace filter for sending with queries.

        Args:
            nsl (Union[list[Union[NS, str]], NS, str]): The namespace or namespaces to create a filter out of

        Raises:
            ValueError: If there is an invalid namespace in `nsl`

        Returns:
            str: The pipe-fenced namespace filter for sending with queries
        """
        if not isinstance(nsl, list):
            nsl = [nsl]

        if None in (l := [self.intify(ns) for ns in nsl]):
            raise ValueError(f"invalid namespace, one of these does not represent an actual namespace: {nsl}")

        return "|".join([str(i) for i in l])

    def intify(self, ns: Union[int, NS, str]) -> int:
        """Convienence method, converts the specified namespace to its `int` id if possible.  This is a lexical operation and does not check if the id actually exists on the server.

        Args:
            ns (Union[int, NS, str]): The namespace to get the `int` of.

        Returns:
            int: The int id of `ns`.  None if you passed a `str` and it does not exist in the lookup table.
        """
        if isinstance(ns, NS):
            return ns.value

        return ns if isinstance(ns, int) else self.m.get(ns)

    def nss(self, title: str) -> str:
        """Strips the namespace prefix from a title.

        Args:
            title (str): The title to remove the namespace from.

        Returns:
            str: `title`, without a namespace.
        """
        return self.ns_regex.sub("", title, 1)

    def stringify(self, ns: Union[int, NS, str]) -> str:
        """Convienence method, returns the name of a namespace as a `str`.  Does not perform any namespace validation whatsoever.

        Args:
            ns (Union[int, NS, str]): The namespace to get the name of.  If this is a `str`, then it will be returned.

        Returns:
            str: The name of `ns` as a `str`.
        """
        return self.m.get(ns) if isinstance(ns, int) else ns
