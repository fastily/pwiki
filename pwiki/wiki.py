"""Classes for use by a client to interact with a MediaWiki instance's API"""

import logging
import pickle
import re

from collections.abc import Callable, Iterable
from datetime import datetime
from pathlib import Path
from typing import Any, Union

from requests import Session

from .dwrap import Contrib, ImageInfo, Log, Revision
from .gquery import GQuery
from .mquery import MQuery
from .ns import MAIN_NAME, NS, NSManager
from .oquery import OQuery
from .query_constants import MAX
from .query_utils import flatten_generator
from .waction import WAction
from .wparser import WikiText, WParser


log = logging.getLogger(__name__)


class Wiki:
    """General wiki-interfacing functionality and config data"""

    def __init__(self, domain: str = "en.wikipedia.org", username: str = None, password: str = None, cookie_jar: Path = Path(".")):
        """Initializer, creates a new Wiki object.

        Args:
            domain (str): The shorthand domain of the Wiki to target (e.g. "en.wikipedia.org")
            username (str, optional): The username to login as. Does nothing if `password` is not set.  Defaults to None.
            password (str, optional): The password to use when logging in. Does nothing if `username` is not set.  Defaults to None.
            cookie_jar (Path, optional): The directory to save/read cookies to/from.  Disable by setting this to `None`.  Note that in order to save cookies you still have to call `self.save_cookies()`. Defaults to Path(".").
        """
        self.endpoint: str = f"https://{domain}/w/api.php"
        self.domain: str = domain
        self.client: Session = Session()
        self.client.headers.update({"User-Agent": "pwiki"})

        self.username: str = None
        self.cookie_jar: Path = cookie_jar
        self.is_logged_in: bool = False
        self.csrf_token: str = "+\\"

        self._refresh_rights()

        if not self._load_cookies(username):
            self.login(username, password)

        self.ns_manager: NSManager = OQuery.fetch_namespaces(self)

    def __del__(self) -> None:
        """Finalizer, releases resources used by the internal requests session"""
        self.client.close()

    def __repr__(self) -> str:
        """Generate a str representation of this Wiki object.  Useful for logging.

        Returns:
            str: A str representation of this Wiki object.
        """
        return f"[{self.username or '<Anonymous>'} @ {self.domain}]"

    def _refresh_rights(self) -> None:
        """Refreshes the cached user rights fields.  If not logged in, then set the user rights to the defaults (i.e. no rights)."""
        if not self.username:
            self.rights: list = []
            self.is_bot: bool = False
            self.prop_title_max: int = 50
        else:
            self.rights: list = self.list_user_rights()
            self.is_bot: bool = "bot" in self.rights
            self.prop_title_max: int = 500 if self.is_bot else 50

    ##################################################################################################
    ######################################## C O O K I E S ###########################################
    ##################################################################################################

    def _cookie_path(self, username: str = None) -> Path:
        """Determines the cookie save path and returns that.

        Args:
            username (str, optional): Force a search for this this username. If unset, then `self.username` will be used as the default.  Defaults to None.

        Returns:
            Path: The file `Path` to save the cookies of this instance to.  If no cookie_jar or username was set in the initializer, then return `None`.
        """
        return (self.cookie_jar / f"{self.domain}_{username}.pickle") if self.cookie_jar and (username := username or self.username) else None

    def _load_cookies(self, username: str = None) -> bool:
        """Load saved cookies from a file into this pwiki instance.

        Args:
            username (str, optional): The override username to use.  If unset, then `self.username` will be used as the default.  Defaults to None.

        Returns:
            bool: True if successful (confirmed with server that cookies are valid).
        """
        if not (cookie_path := self._cookie_path(username)) or not cookie_path.is_file():
            return False

        with cookie_path.open('rb') as f:
            self.client.cookies = pickle.load(f)

        self.csrf_token = OQuery.fetch_token(self)
        if self.csrf_token == "+\\":
            log.warning("Cookies loaded from '%s' are invalid!  Skipping cookies...", cookie_path)
            self.client.cookies.clear()
            return False

        self.username = self.whoami()
        self._refresh_rights()
        self.is_logged_in = True

        log.debug("%s: successfully loaded cookies from '%s'", self, cookie_path)

        return True

    def clear_cookies(self) -> None:
        """Deletes any saved cookies from disk."""
        (p := self._cookie_path()).unlink(True)
        log.info("%s: Removed cookies saved at '%s'", self, p)

    def save_cookies(self) -> None:
        """Write the cookies of the Wiki object to disk, so they can be used in the future.

        Raises:
            ValueError: If a directory for cookies was not specified (i.e. set to `None`) when initializing this Wiki.
        """
        if not (p := self._cookie_path()):
            raise ValueError("No cookie path is specified, unable to save cookies")

        if not self.is_logged_in:
            log.warning("%s: not logged in, no cookies to save", self)
            return

        log.info("%s: Saving cookies to '%s'", self, p)

        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open('wb') as f:
            pickle.dump(self.client.cookies, f)

    ##################################################################################################
    ##################################### N A M E S P A C E S ########################################
    ##################################################################################################

    def convert_ns(self, title: str, ns: Union[str, NS]) -> str:
        """Converts the namespace of the specified title to another namespace.  PRECONDITION: `title` is well-formed.

        Args:
            title (str): The title to convert
            ns (Union[str, NS]): The namespace to convert `title` to.

        Returns:
            str: `title`, converted to namespace `ns`
        """
        return self.ns_manager.batch_convert_ns([title], ns)[0]

    def filter_by_ns(self, titles: list[str], *nsl: Union[str, NS]) -> list[str]:
        """Creates a copy of `titles` and strips out any title that isn't in the namespaces specified in `nsl`.

        Args:
            titles (list[str]): The list of titles to process.

        Returns:
            list[str]: A copy of `titles` with any titles in `nsl` excluded.
        """
        nsl = {self.ns_manager.stringify(ns) for ns in nsl}
        return [s for s in titles if self.which_ns(s) in nsl]

    def in_ns(self, title: str, ns: Union[int, NS, str, tuple[Union[int, NS, str]]]) -> bool:
        """Checks if a title belongs to a namespace or namespaces.  This is a lexical operation only, so `title` must be well-formed.

        Args:
            title (str): The title to check.
            ns (Union[int, NS, str, tuple[Union[int, NS, str]]]): The namespace or namespaces (pass as a `tuple`) to check

        Returns:
            bool: True if `title` is a member of the namespace(s), `ns`.
        """
        target = self.ns_manager.intify(self.which_ns(title))
        return (target in {self.ns_manager.intify(x) for x in ns}) if isinstance(ns, tuple) else (target == self.ns_manager.intify(ns))

    def is_talk_page(self, title: str) -> bool:
        """Determines if `title` is part of a talk page namespace.  This is a lexical operation and does not perform an api query.

        Args:
            title (str): The title to check

        Returns:
            bool: `True` if `title` is a talk page.
        """
        return (id := self.ns_manager.intify(self.which_ns(title))) >= 0 and id % 2

    def not_in_ns(self, title: str, ns: Union[int, NS, str, tuple[Union[int, NS, str]]]) -> bool:
        """Checks if a title does not belong to a namespace or namespaces.  This is a lexical operation only, so `title` must be well-formed.

        Args:
            title (str): The title to check.
            ns (Union[int, NS, str, tuple[Union[int, NS, str]]]): The namespace or namespaces (pass as a `tuple`) to check

        Returns:
            bool: True if `title` is NOT a member of the namespace(s), `ns`.
        """
        return not self.in_ns(title, ns)

    def nss(self, title: str) -> str:
        """Strips the namespace prefix from a title.

        Args:
            title (str): The title to remove the namespace from.

        Returns:
            str: `title`, without a namespace.
        """
        return self.ns_manager.nss(title)

    def page_of(self, title: str) -> str:
        """Gets the content page associated with `title`.   If `title` is a content page, then `None` will be returned.

        Args:
            title (str): The content page associated with `title`.

        Returns:
            str: The content page associated with `title`, or `None` if `title` is already a content page.
        """
        if (ns_id := self.ns_manager.m.get(self.which_ns(title))) % 2:  # == 1
            return self.ns_manager.canonical_prefix(self.ns_manager.m.get(ns_id - 1)) + self.nss(title)

        log.debug("%s: could not get page of '%s' because it is not a talk page and has an id of %d", self, title, ns_id)

    def talk_page_of(self, title: str) -> str:
        """Gets the talk page of `title`.  If `title` is a talk page, then `None` will be returned.

        Args:
            title (str): The talk page associated with `title`.

        Returns:
            str: The talk page of `title`, or `None` if `title` is already a talk page.
        """
        if (ns_id := self.ns_manager.m.get(self.which_ns(title))) % 2 == 0:
            return f"{self.ns_manager.m.get(ns_id + 1)}:{self.nss(title)}"

        log.debug("%s: could not get talk page of '%s' because it is already a talk page with an id of %d", self, title, ns_id)

    def which_ns(self, title: str) -> str:
        """Determines which namespace a title belongs to.

        Args:
            title (str): The title to get the namespace of

        Returns:
            str: The namespace, without it's `:` suffix.  If main namespace, then `"Main"` will be returned
        """
        return result[0][:-1] if (result := self.ns_manager.ns_regex.match(title)) else MAIN_NAME

    ##################################################################################################
    ######################################## A C T I O N S ###########################################
    ##################################################################################################

    def delete(self, title: str, reason: str) -> bool:
        """Deletes a page.  PRECONDITION: `wiki` must be logged in and have the ability to delete pages for this to work.

        Args:
            title (str): The title to delete
            reason (str): The reason for deleting this page.

        Returns:
            bool: `True` if this action succeeded.
        """
        log.info("%s: Deleting '%s'...", self, title)
        return WAction.delete(self, title, reason)

    def edit(self, title: str, text: str = None, summary: str = "", prepend: str = None, append: str = None, minor: bool = False) -> bool:
        """Attempts to edit a page on the Wiki.  Can replace text or append/prepend text.

        Args:
            title (str): The title to edit.
            text (str, optional): Text to replace the current page's contents with. Mutually exclusive with `prepend`/`append`. Defaults to None.
            summary (str, optional): The edit summary to use. Defaults to "".
            prepend (str, optional): Text to prepend to the page. Mutually exclusive with `text`. Defaults to None.
            append (str, optional): Text to append to the page.  Mutually exclusive with `text`. Defaults to None.
            minor (bool, optional): Set `True` to mark this edit as minor. Defaults to False.

        Returns:
            bool: `True` if the edit was successful.
        """
        log.info("%s: Editing '%s'...", self, title)
        return WAction.edit(self, title, text, summary, prepend, append, minor)

    def login(self, username: str, password: str) -> bool:
        """Attempts to login this Wiki object.  If successful, all future calls will be automatically include authentication.  Immediately returns `False` if `username` or `password` is empty/`None`.

        Args:
            username (str): The username to login with
            password (str): The password to login with

        Returns:
            bool: `True` if logging in was successful.
        """
        if not (username and password):
            return False

        log.info("%s: Attempting login for %s", self, username)

        if result := WAction.login(self, username, password):
            log.info("%s: Successfully logged in as '%s'", self, username)
        else:
            log.error("%s: Failed to log in as '%s'", self, username)

        return result

    def purge(self, titles: Iterable[str]) -> bool:
        """Attempts to purge the server-side caches of `titles`.  Exits and outputs messages to standard out on the first failure.

        Args:
            titles (Iterable[str]): The titles to purge

        Returns:
            bool: `True` if all pages in `titles` were successfully purged. 
        """
        log.debug("Purging titles: %s", titles)
        return WAction.purge(self, titles)

    def replace_text(self, title: str, pattern: Union[re.Pattern, str], replacement: str = "", summary: str = "") -> bool:
        """Convenience method, edits `title` and replaces all instances of `target_text` with `replacement` in its text.

        Args:
            title (str): The page to edit.
            pattern (Union[re.Pattern, str]): The regular expression describing the text to replace on `title`.
            replacement (str, optional): The text to replace all matches of `pattern` with. Defaults to "".
            summary (str, optional): The edit summary to use. Defaults to "".

        Returns:
            bool: True if the operation was successful.
        """
        return (s := re.sub(pattern, replacement, original := self.page_text(title))) == original or self.edit(title, s, summary)

    def upload(self, path: Path, title: str, desc: str = "", summary: str = "", max_retries=5) -> bool:
        """Uploads a file to the target Wiki.

        Args:
            path (Path): the local path on your computer pointing to the file to upload
            title (str): The title to upload the file to, excluding the "`File:`" namespace.
            desc (str, optional): The text to go on the file description page.  Defaults to "".
            summary (str, optional): The upload log summary to use.  Defaults to "".
            max_retries (int, optional): The maximum number of retry attempts in the event of an error. Defaults to 5.

        Returns:
            bool: `True` if the upload was successful.
        """
        log.info("%s: Uploading '%s' to '%s'", self, path, title)
        return WAction.unstash(self, filekey, title, desc, summary, max_retries) if (filekey := WAction.upload_only(self, path, title, max_retries)) else False

    ##################################################################################################
    ######################################## Q U E R I E S ###########################################
    ##################################################################################################

    def _xq_simple(self, func: Callable[..., dict], title: str, *extra_args: Any) -> Any:
        """Convienence method which makes it easy to execute `MQuery` or `MQuery`-like functions with a single title.  Shorthand for `func(self, [title]).get(title)`.

        Args:
            func (Callable[..., dict]): The `MQuery` or `MQuery`-like method to call.
            title (str): The title to act on.

        Returns:
            Any: The value obtained by performing a `.get(title)` call on the `dict` returned by `func`.
        """
        return func(self, [title], *extra_args).get(title)

    def all_users(self, groups: Union[list[str], str] = []) -> list[str]:
        """Lists all users on a wiki.  Can filter users by right(s) they have been assigned.

        Args:
            groups (Union[list[str], str], optional): The group(s) to filter by (e.g. `sysop`, `bot`).  Optional, leave empty to disable. Defaults to [].

        Returns:
            list[str]: a `list` containing usernames (without the `User:` prefix) that match the specified crteria.
        """
        return flatten_generator(GQuery.all_users(self, groups, MAX))

    def categories_on_page(self, title: str) -> list[str]:
        """Fetch the categories used on a page.

        Args:
            title (str): The title to query.

        Returns:
            list[str]: The `list` of categories used on `title`.
        """
        log.info("%s: fetching categories on pages: %s", self, title)
        return self._xq_simple(MQuery.categories_on_page, title)

    def category_members(self, title: str, ns: Union[list[Union[NS, str]], NS, str] = []) -> list[str]:
        """Fetches the elements in a category.

        Args:
            title (str): The title of the category to fetch elements from.  Must include `Category:` prefix.
            ns (Union[list[Union[NS, str]], NS, str], optional): Only return results that are in these namespaces.  Optional, set empty list to disable. Defaults to [].

        Returns:
            list[str]: a `list` containing `title`'s category members.
        """
        log.info("%s: fetching category members of '%s'", self, title)
        return flatten_generator(GQuery.category_members(self, title, ns if isinstance(ns, list) else [ns], MAX))

    def category_size(self, title: str) -> int:
        """Queries the wiki and gets the number of pages categorized in `title`.

        Args:
            title (str): The category to get the size of.  Must start with `Category:` prefix.

        Returns:
            int: The number of pages in this category.
        """
        log.info("%s: fetching category size for: '%s'", self, title)
        return self._xq_simple(MQuery.category_size, title)

    def contribs(self, user: str, older_first: bool = False, ns: list[Union[NS, str]] = []) -> list[Contrib]:
        """Fetches contributions of a user.  Warning: this fetches all of `user`'s contributions!

        Args:
            user (str): The username to query, excluding the `User:` prefix.
            older_first (bool, optional): Set `True` to fetch older elements first. Defaults to False.
            ns (list[Union[NS, str]], optional): Only return results that are in these namespaces.  Optional, set empty list to disable.  Defaults to [].

        Returns:
            list[Contrib]: The contributions of `user`.
        """
        log.info("%s: fetching contributions of '%s'", self, user)
        return flatten_generator(GQuery.contribs(self, user, older_first, ns, MAX))

    def duplicate_files(self, title: str, local_only: bool = True) -> list[str]:
        """Find dupliates of `title` if possible.

        Args:
            title (str): The title to get duplicates of.  Must start with `File:` prefix.
            local_only (bool, optional): Set `False` to also search the associated shared media repository wiki.  If that sounded like a foreign language to you, then ignore this parameter. Defaults to True.

        Returns:
            list[str]: The `list` of files that duplicate `title`.
        """
        log.info("%s: fetching duplicates of %s", self, title)
        return self._xq_simple(MQuery.duplicate_files, title, local_only)

    def exists(self, title: str) -> bool:
        """Query the wiki and determine if `title` exists on the wiki.

        Args:
            title (str): the title to query.

        Returns:
            bool: `True` if `title` exists on the wiki.
        """
        log.info("%s: determining if '%s' exists", self, title)
        return self._xq_simple(MQuery.exists, title)

    def external_links(self, title: str) -> list[str]:
        """Fetches external links on a page.

        Args:
            title (str): The title to query

        Returns:
            list[str]: The `list` of external links contained in the text of `title`.
        """
        log.info("%s: fetching external links on %s", self, title)
        return self._xq_simple(MQuery.external_links, title)

    def file_usage(self, title: str) -> list[str]:
        """Fetch the titles of all pages embedding/displaying `title`.

        Args:
            title (str): The file to query.

        Returns:
            list[str]: The `list` of all pages displaying `title`.
        """
        log.info("%s: fetching file usage for '%s'", self, title)
        return self._xq_simple(MQuery.file_usage, title)

    def first_editor_of(self, title: str) -> str:
        """Gets the user who created `title`.

        Args:
            title (str): The title of the page to query

        Returns:
            str: The username of the user who created `title`.  Does not include `User:` prefix.  Returns `None` if the page does not exist.
        """
        return l[0].user if (l := next(GQuery.revisions(self, title, older_first=True), None)) else None

    def global_usage(self, title: str) -> list[tuple]:
        """Fetch the global file usage of a media file.  Only works with wikis that utilize a shared media respository wiki.

        Args:
            title (str): The file to get global usage usage of. Must start with `File:` prefix

        Returns:
            list[tuple]: A `list` of `tuple`s (page title, wiki hostname) containing the global usages of the file.
        """
        log.info("%s: fetching global usage of %s", self, title)
        return self._xq_simple(MQuery.global_usage, title)

    def image_info(self, title: str) -> list[ImageInfo]:
        """Fetch image (file) info for media files.  This is basically image metadata for each uploaded media file under the specified title. See `dwrap.ImageInfo` for details.

        Args:
            title (str): The file to get image info of.  Must start with the `File:` prefix

        Returns:
            list[ImageInfo]: The `list` of `ImageInfo` objects associated with `title`.
        """
        log.info("%s: fetching image info for %s", self, title)
        return self._xq_simple(MQuery.image_info, title)

    def images_on_page(self, title: str) -> list[str]:
        """Fetch images/media files used on a page.

        Args:
            title (str): The title to query

        Returns:
            list[str]: The `list` of images/files that are used on `title`.
        """
        log.info("%s: determining what files are embedded on %s", self, title)
        return self._xq_simple(MQuery.images_on_page, title)

    def last_editor_of(self, title: str) -> str:
        """Gets the user who most recently edited `title`.

        Args:
            title (str): The title of the page to query

        Returns:
            str: The username of the user who most recently edited `title`.  Does not include `User:` prefix.  Returns `None` if the page does not exist.
        """
        return l[0].user if (l := next(GQuery.revisions(self, title), None)) else None

    def links_on_page(self, title: str, ns: Union[list[Union[NS, str]], NS, str] = []) -> list[str]:
        """Fetch wiki links on a page.

        Args:
            title (str): The title to query
            ns (Union[list[Union[NS, str]], NS, str], optional): Restrict returned output to titles in these namespaces. Optional, set to empty list to disable. Defaults to [].

        Returns:
            list[str]: The `list` of wiki links contained in the text of `title`
        """
        log.info("%s: fetching wikilinks on '%s'", self, title)
        return self._xq_simple(MQuery.links_on_page, title, ns)

    def list_duplicate_files(self) -> list[str]:
        """List files on a wiki which have duplicates by querying the Special page `Special:ListDuplicatedFiles`.  This reads the entire list, and may return up to 5000 elements.

        Returns:
            list[str]: A `list` containing files that have duplicates on the wiki.
        """
        log.info("%s: getting files with duplicates from Special:ListDuplicatedFiles...", self)
        return flatten_generator(GQuery.list_duplicate_files(self, MAX))

    def list_user_rights(self, username: str = None) -> list[str]:
        """Lists user rights for the specified user.

        Args:
            username (str, optional): The user to get rights for.  Usernames must be well formed (e.g. no wacky capitalization), and must not contain the `User:` prefix.  If set to `None`, then Wiki's username will be used.  Defaults to None.

        Returns:
            list[str]: The rights for the specified user.  `None` if something went wrong.
        """
        log.info("%s: Fetching user rights for '%s'", self, u := username or self.username)
        return OQuery.list_user_rights(self, [u]).get(u) if u else []

    def logs(self, title: str = None, log_type: str = None, log_action: str = None, user: str = None, ns: Union[NS, str] = None, tag: str = None, start: datetime = None, end: datetime = None, older_first: bool = False) -> list[Log]:
        """Fetches `Special:Log` entries from a wiki. PRECONDITION: if `start` and `end` are both set, then `start` must occur before `end`.  WARNING: Not recommended to call this with no arguments on large Wikis, this methods returns all matching logs.

        Args:
            title (str, optional): The title of the page to get logs for, if applicable. Defaults to None.
            log_type (str, optional): The type of log to fetch (e.g. `"delete"`). Defaults to None.
            log_action (str, optional): The type and sub-action of the log to fetch (e.g. `"delete/restore"`).  Overrides `log_type`.  Defaults to None.
            user (str, optional): The user associated with the log action, if applicable.  Do not include `User:` prefix.  Defaults to None.
            ns (Union[NS, str], optional): Only return results that are in this namespace. Defaults to None.
            tag (str, optional): Only return results that are tagged with this tag. Defaults to None.
            start (datetime, optional): Set to filter out revisions older than this date.  If no timezone is specified in the datetime, then UTC is assumed. Defaults to None.
            end (datetime, optional): Set to filter out revisions newer than this date.  If no timezone is specified in the datetime, then UTC is assumed. Defaults to None.
            older_first (bool, optional): Set to `True` to fetch older log entries first. Defaults to False.

        Returns:
            list[Log]: A `list` of `Log` as specified.
        """
        log.info("%s: Fetching logs...", self)
        return flatten_generator(GQuery.logs(self, title, log_type, log_action, user, ns, tag, start, end, older_first, MAX))

    def normalize_title(self, title: str) -> str:
        """Normalizes titles to match their canonical versions.  Usually this means fixing capitalization or replacing underscores with spaces.

        Args:
            title (str): The title to normalize.

        Returns:
            str: The normalized version of `title`.
        """
        log.info("%s: Normalizing '%s'", self, title)
        return self._xq_simple(OQuery.normalize_titles, title)

    def page_text(self, title: str) -> str:
        """Queries the Wiki for the text of `title`.

        Args:
            title (str): The title to get page text of.

        Returns:
            str: The text of `title`.  `None` if `title` does not exist.
        """
        log.info("%s: fetching page text of '%s'", self, title)
        return self._xq_simple(MQuery.page_text, title)

    def parse(self, title: str = None, text: str = None) -> WikiText:
        """Parses the title or text into `WikiText`/`WTemplate` objects.  If `title` and `text` are both specified, then `text` will be parsed as if it was on `title`.

        Args:
            title (str, optional): The title to use.  If `text` is not specified, then the text of `title` will be automatically fetched and parsed. Defaults to None.
            text (str, optional): The text to parse. If `title` is specified, then the text will be parsed as if it is was published on `title`. Defaults to None.

        Returns:
            WikiText: The result of the parsing operation.  `None` if something went wrong.
        """
        return WParser.parse(self, title, text)

    def prefix_index(self, ns: Union[NS, str], prefix: str) -> list[str]:
        """Performs a prefix index query and returns all matching titles.

        Args:
            ns (Union[NS, str]): The namespace to search in.
            prefix (str): Fetches all titles in the specified namespace that start with this str.  To return subpages only, append a `/` character to this param.

        Returns:
            list[str]: A `list` containing files that match the specified prefix index.
        """
        log.info("%s: Getting prefix index for ns '%s' and prefix '%s'", ns, prefix)
        return flatten_generator(GQuery.prefix_index(self, ns, prefix, MAX))

    def random(self, ns: list[Union[NS, str]] = []) -> str:
        """Fetches a random page from the wiki.

        Args:
            ns (list[Union[NS, str]], optional): Only return results that are in these namespaces.  Optional, set empty list to disable. Defaults to [].

        Returns:
            str: A random page from the wiki as specified, or `None` if this was not possible.
        """
        log.info("%s: Fetching a random page", self)
        return result[0] if (result := next(GQuery.random(self, ns), None)) else None

    def resolve_redirect(self, title: str) -> str:
        """Fetch the target of a redirect page.

        Args:
            title (str): The title to query

        Returns:
            str: The redirect target.  If `title` was not a redirect, then `title` will be returned.
        """
        return self._xq_simple(OQuery.resolve_redirects, title)

    def revisions(self, title: str, older_first: bool = False, start: datetime = None, end: datetime = None, include_text: bool = False) -> list[Revision]:
        """Fetches all the revisions of `title`.  Plan accordingly when querying pages that have many revisions!

        Args:
            title (str): The title to get revisions for.
            older_first (bool, optional): Set `True` to get older revisions first. Defaults to False.
            start (datetime, optional): Set to filter out revisions older than this date.  If no timezone is specified in the datetime, then UTC is assumed. Defaults to None.
            end (datetime, optional): Set to filter out revisions newer than this date. If no timezone is specified in the datetime, then UTC is assumed. Defaults to None.
            include_text (bool, optional): If `True`, then also fetch the wikitext of each revision.  Will populate the `Revision.text` field.  Warning: enabling this is expensive for large pages with many revisions.  Defaults to False.

        Returns:
            list[Revision]: A `list` containing the `Revision` objects of `title`
        """
        log.info("%s: Fetching revisions of '%s'", self, title)
        return flatten_generator(GQuery.revisions(self, title, MAX, older_first, start, end, include_text))

    def search(self, phrase: str, ns: list[Union[NS, str]] = []) -> list[str]:
        """Perform a search on the wiki.

        Args:
            phrase (str): The phrase to query with
            ns (list[Union[NS, str]], optional): Only return results that are in these namespaces.  Optional, set empty list to disable. Defaults to [].

        Returns:
            list[str]: A `list` containing the results of the search.
        """
        log.info("%s: Searching the wiki for '%s'", self, phrase)
        return flatten_generator(GQuery.search(self, phrase, ns, MAX))

    def stashed_files(self) -> list[tuple[str, int, str]]:
        """Fetch the user's stashed files.  PRECONDITION: You must be logged in for this to work

        Returns:
            list[tuple[str, int]]: a `list` of 3-`tuple` where each tuple is of the form (file key, file size, status).  Known values for status: `"finished"`, `"chunks"`
        """
        log.info("%s: fetching user's stashed files...", self)
        return flatten_generator(GQuery.stashed_files(self, MAX))

    def templates_on_page(self, title: str) -> list[str]:
        """Fetch templates transcluded on a page.

        Args:
            title (str): The title to query

        Returns:
            list[str]: A list of tempalates transcluded on `title
        """
        log.info("%s: determining what templates are transcluded on %s", self, title)
        return self._xq_simple(MQuery.templates_on_page, title)

    def uploadable_filetypes(self) -> set:
        """Queries the Wiki for all acceptable file types which may be uploaded to this Wiki.  PRECONDITION: the target Wiki permits file uploads.

        Returns:
            set: A set containing all acceptable file types as their extensions ("." prefix is included) 
        """
        log.info("%s: Fetching a list of acceptable file upload extensions.", self)
        return OQuery.uploadable_filetypes(self)

    def user_uploads(self, user: str) -> list[str]:
        """Gets the uploads of a user.

        Args:
            user (str): The username to query, without the `User:` prefix.

        Returns:
            list[str]: A `list` containing the files uploaded by `user`.
        """
        log.info("%s: Fetching uploads for '%s'", self, user)
        return flatten_generator(GQuery.user_uploads(self, user, MAX))

    def what_links_here(self, title: str, redirects_only: bool = False, ns: Union[list[Union[NS, str]], NS, str] = []) -> list[str]:
        """Fetch pages that wiki link (locally) to a page.

        Args:
            title (str): The title to query
            redirects_only (bool, optional): Set `True` to get the titles that redirect to this page. Defaults to False.
            ns (Union[list[Union[NS, str]], NS, str], optional): Restrict returned output to titles in these namespaces. Optional, set to empty list to disable. Defaults to [].

        Returns:
            list[str]: The list of pages that link to `title`.
        """
        log.info("%s: determining what pages link to '%s'", self, title)
        return self._xq_simple(MQuery.what_links_here, title, redirects_only, ns)

    def what_transcludes_here(self, title: str, ns: Union[list[Union[NS, str]], NS, str] = []) -> list[str]:
        """Fetch pages that translcude a page.  If querying for templates, you must include the `Template:` prefix.

        Args:
            title (str): The title to query
            ns (Union[list[Union[NS, str]], NS, str], optional): Restrict returned output to titles in these namespaces. Optional, set to empty list to disable. Defaults to [].

        Returns:
            list[str]: The list of pages that transclude `title`.
        """
        log.info("%s: fetching transclusions of '%s'", self, title)
        return self._xq_simple(MQuery.what_transcludes_here, title, ns)

    def whoami(self) -> str:
        """Get this Wiki's username from the server.  If not logged in, then this will return your external IP address.

        Returns:
            str: If logged in, this Wiki's username.  Otherwise, the external IP address of your device.
        """
        log.info("%s: Asking the server who I am logged in as...", self)
        return OQuery.whoami(self)
