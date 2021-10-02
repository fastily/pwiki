"""Classes and functions backing the actions API.  Not a stable API, intended for internal use within pwiki only."""
from __future__ import annotations

import logging

from collections.abc import Iterable
from pathlib import Path
from time import sleep
from typing import TYPE_CHECKING

from .ns import NS
from .oquery import OQuery
from .query_utils import chunker
from .utils import has_error, make_params, mine_for, read_error

if TYPE_CHECKING:
    from .wiki import Wiki

_CHUNKSIZE = 1024 * 1024 * 4

log = logging.getLogger(__name__)


class WAction:
    """Collection of functions which can perform write actions on a Wiki"""

    @staticmethod
    def _action_and_validate(wiki: Wiki, action: str, form: dict = None, apply_token: bool = True, timeout: int = 15, success_vals: tuple = ("Success",), extra_args: dict = None) -> dict:
        """Performs a `_post_action()` and checks the results for errors.  If there is an error, it will be logged accordingly.

        Args:
            wiki (Wiki): The Wiki object to use
            action (str): The id of the action to perform.
            form (dict, optional): The parameters to POST to the server, if applicable. Defaults to None.
            apply_token (bool, optional): Set `True` to also send the Wiki's csrf token in the POST. Defaults to True.
            timeout (int, optional): The length of time (in seconds) to wait before marking the action as failed. Defaults to 15.
            success_vals (tuple, optional): The keyword responses returned by the server which indicate a successful action.  Optional, set `None` to skip this check.  Defaults to ("Success",).
            extra_args (dict, optional): Any `kwargs` that should be passed to the underlying requests Session object when performing a POST. Defaults to None.

        Returns:
            dict: The json response from the server, or `None` if something went wrong.
        """
        if not (response := WAction._post_action(wiki, action, form, apply_token, timeout, extra_args)):
            log.error("%s: No response from server while trying to perform action '%s'", wiki, action)
            log.debug("Sent parameters: %s", form)
            return

        if has_error(response):
            log.error("%s: Failed to perform action '%s', server said: %s", wiki, action, read_error(action, response))
            log.debug(response)
            return

        if not success_vals or (status := mine_for(response, action, "result")) in success_vals:
            return response

        log.error("%s: Failed to perform action '%s', got bad result from server: %s", wiki, action, status)
        log.debug(response)

    @staticmethod
    def _post_action(wiki: Wiki, action: str, form: dict = None, apply_token: bool = True, timeout: int = 15, extra_args: dict = None) -> dict:
        """Convienence method, performs the actual POST of the action to the server.

        Args:
            wiki (Wiki): The Wiki object to use
            action (str): The action to perform.
            form (dict, optional): The parameters to POST to the server, if applicable. Defaults to None.
            apply_token (bool, optional): Set `True` to also send the Wiki's csrf token in the POST. Defaults to True.
            timeout (int, optional): The length of time (in seconds) to wait before marking the action as failed. Defaults to 15.
            extra_args (dict, optional): Any `kwargs` that should be passed to the underlying requests Session object when performing a POST. Defaults to None.

        Returns:
            dict: The response from the server.  Empty dict if there was an error.
        """
        pl = make_params(action, form) | ({"token": wiki.csrf_token} if apply_token else {})

        try:
            return wiki.client.post(wiki.endpoint, data=pl, **({"timeout": timeout} | (extra_args or {}))).json()
        except Exception:
            log.error("%s: Could not reach server or read response while performing %s with params %s", wiki, action, pl, exc_info=True)

        return {}

    @staticmethod
    def delete(wiki: Wiki, title: str, reason: str) -> bool:
        """Deletes a page.  PRECONDITION: `wiki` must be logged in and have the ability to delete pages for this to work.

        Args:
            wiki (Wiki): The Wiki to use.
            title (str): The title to delete
            reason (str): The reason for deleting this page.

        Returns:
            bool: `True` if this action succeeded.
        """
        return bool(WAction._action_and_validate(wiki, "delete", {"title": title, "reason": reason}, success_vals=None))

    @staticmethod
    def edit(wiki: Wiki, title: str, text: str = None, summary: str = "", prepend: str = None, append: str = None, minor: bool = False) -> bool:
        """Attempts to edit a page on the Wiki.  Can replace text or append/prepend text.

        Args:
            wiki (Wiki): The Wiki to use.
            title (str): The title to edit.
            text (str, optional): Text to replace the current page's contents with.  Overrides `prepend`/`append`.  Defaults to None.
            summary (str, optional): The edit summary to use. Defaults to "".
            prepend (str, optional): Text to prepend to the page. Defaults to None.
            append (str, optional): Text to append to the page. Defaults to None.
            minor (bool, optional): Set `True` to mark this edit as minor. Defaults to False.

        Raises:
            ValueError: If `text`, `prepend`, `append` are all None OR if `text` and `prepend`/`append` were both specified.

        Returns:
            bool: `True` if the edit was successful.
        """
        pl = {"title": title, "summary": summary}

        if text:
            pl["text"] = text
        elif append or prepend:
            if append:
                pl["appendtext"] = append
            if prepend:
                pl["prependtext"] = prepend
        else:
            raise ValueError("Can't do anything: text, prepend, or append were not specified!")

        if minor:
            pl["minor"] = 1
        if wiki.is_bot:
            pl["bot"] = 1

        return bool(WAction._action_and_validate(wiki, "edit", pl))

    @staticmethod
    def login(wiki: Wiki, username: str, password: str) -> bool:
        """Attempts to login this Wiki object.  If successful, all future calls will be automatically include authentication.

        Args:
            wiki (Wiki): The Wiki object to use
            username (str): The username to login with
            password (str): The password to login with

        Returns:
            bool: True if successful
        """
        if not (response := WAction._action_and_validate(wiki, "login", {"lgname": username, "lgpassword": password, "lgtoken": OQuery.fetch_token(wiki, True)}, False)):
            return False

        wiki.username = mine_for(response, "login", "lgusername")
        wiki.csrf_token = OQuery.fetch_token(wiki)
        wiki._refresh_rights()
        wiki.is_logged_in = True

        return True

    @staticmethod
    def purge(wiki: Wiki, titles: Iterable[str]) -> bool:
        """Attempts to purge the server-side caches of `titles`.  Exits and outputs messages to standard out on the first failure.

        Args:
            wiki (Wiki): The Wiki object to use
            titles (Iterable[str]): The titles to purge

        Returns:
            bool: `True` if all pages in `titles` were successfully purged. 
        """
        return all(WAction._post_action(wiki, "purge", {"titles": "|".join(chunk)}) for chunk in chunker(titles, wiki.prop_title_max))

    @staticmethod
    def unstash(wiki: Wiki, filekey: str, title: str, desc: str = "", summary: str = "", max_retries: int = 5, retry_interval: int = 30) -> bool:
        """Attempt to unstash a file uploaded to the file stash.

        Args:
            wiki (Wiki): The Wiki object to use
            filekey (str): The filekey of the file in your file stash to unstash (publish).
            title (str): The title to publish the file in the stash to (excluding `File:` prefix).
            desc (str, optional): The text to go on the file description page. Defaults to "".
            summary (str, optional): The upload log summary to use. Defaults to "".
            max_retries (int, optional): The maximum number of retry in the event of failure (assuming the server expereinced an error). Defaults to 5.
            retry_interval (int, optional): The number of seconds to wait in between retries.  Set 0 to disable. Defaults to 30.

        Returns:
            bool: True if unstashing was successful
        """
        log.info("%s: Unstashing '%s' as '%s'", wiki, filekey, title)

        tries = 0
        status = False
        while tries < max_retries and not (status := bool(WAction._action_and_validate(wiki, "upload", {"filename": title, "text": desc, "comment": summary, "filekey": filekey, "ignorewarnings": 1}, timeout=360)) or wiki.exists(wiki.convert_ns(title, NS.FILE))):
            log.warning("%s: Unstash failed, this is a attempt %d of %d. Sleeping %ds...", wiki, tries + 1, max_retries, retry_interval)
            sleep(retry_interval)
            tries += 1

        return status

    @staticmethod
    def upload_only(wiki: Wiki, path: Path, title: str, max_retries: int = 5) -> str:
        """Uploads a file to the target Wiki.  Note: you will need to unstash (publish) your uploads post-upload in order for them to be visible on the wiki.

        Args:
            wiki (Wiki): The Wiki object to use
            path (Path): The local path on your computer pointing to the file to upload
            title (str): The title to upload the file to, excluding the "`File:`" namespace.
            max_retries (int, optional): The maximum number of retry attempts in the event of an error. Defaults to 5.

        Raises:
            OSError: if `path` does not exist or is an empty file.

        Returns:
            str: the filekey, or `None` if something went wrong.
        """
        if not path.is_file() or not (fsize := path.stat().st_size):
            raise OSError(f"Nothing to upload, '{path}' does not exist or is an empty file.")

        total_chunks = fsize // _CHUNKSIZE + 1
        pl = {"filename": title, "offset": 0, "ignorewarnings": 1, "filesize": fsize, "token": wiki.csrf_token, "stash": 1}
        chunk_count = err_count = 0

        with path.open('rb') as f:
            while buffer := f.read(_CHUNKSIZE):
                log.info("%s: Uploading chunk %d of %d from '%s'", wiki, chunk_count+1, total_chunks, path)

                if (response := WAction._action_and_validate(wiki, "upload", pl, timeout=420, success_vals=("Continue", "Success"), extra_args={"files": {'chunk': (path.name, buffer, "multipart/form-data")}})) and (filekey := mine_for(response, "upload", "filekey")):
                    chunk_count += 1
                    pl["offset"] = _CHUNKSIZE * chunk_count
                    pl["filekey"] = filekey
                else:
                    err_count += 1
                    log.warning("%s: Encountered error while uploading, this was %d/%d", wiki, err_count, max_retries)
                    if err_count > max_retries:
                        log.error("%s: Exceeded error threshold, abort.", wiki)
                        return

        if chunk_count == total_chunks - 1:  # a poorly configured MediaWiki installation may fail to acknowledge the final chunk, but we can attempt recovery on our end
            for i in range(max_retries):
                log.info("%s: Attempting to unmangle filekey, '%s'.  Attempt %d/%d, but first sleeping 30s...", wiki, pl["filekey"], i+1, max_retries)
                sleep(30)

                if t := next((e for e in wiki.stashed_files() if e[0] == pl["filekey"] or e[1] == fsize), None):
                    if t[2] == "finished":
                        log.info("%s: Found a matching filekey: '%s'", wiki, t[0])
                        return t[0]
                else:
                    log.error("No matching filekey found, unable to recover from MediaWiki error!")
                    return

        return pl.get("filekey")
