"""Generator-based query methods which can be used to fetch a limited number of results"""

from __future__ import annotations

import logging

from collections.abc import Generator
from typing import TYPE_CHECKING

from .query_constants import PropCont, QConstant
from .query_utils import get_continue_params, query_and_validate
from .utils import mine_for

if TYPE_CHECKING:
    from .wiki import Wiki

log = logging.getLogger(__name__)


class GQuery:

    @staticmethod
    def prop_cont(wiki: Wiki, title: str, limit_value: int, template: QConstant):
        params = {**template.pl_with_limit(limit_value), "prop": template.name, "titles": title}

        while True:
            if not (response := query_and_validate(wiki, params, desc=f"peform a prop_cont query with '{template.name}'")):
                raise OSError(f"Critical failure performing a prop_cont query with {template.name}, cannot proceed")

            if not ((l := mine_for(response, "query", "pages")) and template.name in (p := l[0])):
                break

            yield template.retrieve_results(p[template.name])

            if not (cont := get_continue_params(response)):
                break

            params.update(cont)

    @staticmethod
    def categories_on_page(wiki: Wiki, title: str, limit: int = 1) -> Generator:
        return GQuery.prop_cont(wiki, title, limit, PropCont.CATEGORIES)
