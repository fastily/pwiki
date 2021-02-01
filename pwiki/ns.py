import logging
import re

from enum import IntEnum
from typing import Union

log = logging.getLogger(__name__)


class NS(IntEnum):
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


class NSManager():
    def __init__(self, r: dict) -> None:

        self.m = {}

        l = []
        for v in r["namespaces"].values():
            id = v["id"]
            name = v["name"] or "Main"

            self.m[id] = name
            self.m[name] = id
            l.append(name)

        self.m |= {e["alias"]: e["id"] for e in r["namespacealiases"]}

        self.ns_regex = re.compile(f'(?i)^({"|".join([s.replace(" ", "[ |]") for s in l])}):')

    def create_filter(self, *args: Union[NS, str]) -> str:
        l = []

        for ns in args:
            if isinstance(ns, NS):
                l.append(ns.value)
            elif isinstance(ns, str):
                l.append(self.m[ns])
            else:
                log.debug("'%s' is not a recognized namespace, ignoring...")

        return "|".join(str(i) for i in l)

    def stringify(self, ns: Union[NS, str]) -> str:
        return self.m.get(ns) if isinstance(ns, NS) else ns
