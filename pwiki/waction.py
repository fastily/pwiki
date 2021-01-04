"""Classes and functions backing the actions API.  Not a stable API, should not be used outside of pwiki."""
from __future__ import annotations

import logging

from contextlib import suppress
from pathlib import Path
from time import sleep
from typing import TYPE_CHECKING, Union

from .utils import make_params

if TYPE_CHECKING:
    from .wiki import Wiki

_CHUNKSIZE = 1024 * 1024 * 4

log = logging.getLogger(__name__)


class WAction:
    """Collection of functions which can perform write actions on a Wiki"""

    @staticmethod
    def post_action(wiki: Wiki, action: str, form: dict = None, apply_token: bool = True, timeout: int = 5) -> dict:
        """Convienence method, performs the actual POST of the action to the server.

        Args:
            wiki (Wiki): The Wiki object to use
            action (str): The action to perform.
            form (dict, optional): The parameters to POST to the server, if applicable. Defaults to None.
            apply_token (bool, optional): Set `True` to also send the Wiki's csrf token in the POST. Defaults to True.

        Returns:
            dict: The response from the server.  Empty dict if there was error.
        """
        pl = make_params(action, form)
        if apply_token:
            pl["token"] = wiki.csrf_token

        try:
            return wiki.client.post(wiki.endpoint, data=pl, timeout=timeout).json()
        except Exception:
            log.error("Could not reach server or read response while performing %s with params %s", action, pl, exc_info=True)

        return {}

    @staticmethod
    def is_success(action: str, response: dict) -> bool:
        """Checks if the server responded with a `Success` message for the specified `response`.

        Args:
            action (str): The action which was just performed
            response (dict): The json response from the server

        Returns:
            bool: True if the server responded with a `Success` message.
        """
        with suppress(Exception):
            return response[action]["result"] == "Success"

        return False

    @staticmethod
    def read_error(action: str, response: dict) -> tuple[str, str]:
        """Reads the error or result from an action response.  Useful for logging.

        Args:
            action (str): The type of action that was just performed.
            response (dict): The json response from the server

        Returns:
            tuple[str, str]: A tuple such that the first element is the status code and the second element is the error description.
        """
        with suppress(Exception):
            if action in response:
                return response[action]["result"], response[action]["reason"]
            elif "error" in response:
                return response["error"]["code"], response["error"]["info"]

        log.warning("Unable to parse error which occurred while perfoming a '%s' action", action)
        log.debug(response)

        return None, None

    @staticmethod
    def edit(wiki: Wiki, title: str, text: str = None, summary: str = "", minor: bool = False, prepend: str = None, append: str = None) -> bool:
        """Attempts to edit a page on the Wiki.  Can replace text or append/prepend text.

        Args:
            wiki (Wiki): The Wiki to use.
            title (str): The title to edit.
            text (str, optional): Text to replace the current page's contents with. Mutually exclusive with `prepend`/`append`. Defaults to None.
            summary (str, optional): The edit summary to use. Defaults to "".
            minor (bool, optional): Set `True` to mark this edit as minor. Defaults to False.
            prepend (str, optional): Text to prepend to the page. Mutually exclusive with `text`. Defaults to None.
            append (str, optional): Text to append to the page.  Mutually exclusive with `text`. Defaults to None.

        Raises:
            ValueError: If `text`, `prepend`, `append` are all None OR if `text` and `prepend`/`append` were both specified.

        Returns:
            bool: `True` if the edit was successful.
        """
        log.info("%s: Editing '%s'", wiki, title)

        if text and (prepend or append):
            raise ValueError("Invalid arguemnts, cannot use text and prepend/append together.  Choose one or the other.")
        if not any((text, prepend, append)):
            raise ValueError("Invalid arguments - text, prepend, or append was not specified!")

        pl = {"title": title, "text": text, "summary": summary}

        if text:
            pl["text"] = text
        if append:
            pl["appendtext"] = append
        if prepend:
            pl["prependtext"] = prepend

        if minor:
            pl["minor"] = 1
        if wiki.is_bot:
            pl["bot"] = 1

        # TODO: Error cases
        response = WAction.post_action(wiki, "edit", pl)

        if WAction.is_success("edit", response):
            return True

        log.error("%s: Could not edit '%s', server said: %s", wiki, title, WAction.read_error("edit", response))
        return False

    def upload(wiki: Wiki, path: Path, title: str, desc: str = "", summary: str = "", unstash=True, max_retries=5) -> Union[bool, str]:
        """Uploads a file to the target Wiki.

        Args:
            path (Path): the local path on your computer pointing to the file to upload
            title (str): The title to upload the file to, excluding the "`File:`" namespace.
            desc (str, optional): The text to go on the file description page.  Does nothing if `unstash` is `False`. Defaults to "".
            summary (str, optional): The upload log summary to use. Does nothing if `unstash` is `False`. Defaults to "".
            unstash (bool, optional): Indicates if the file should be unstashed (published) after upload. Defaults to True.
            max_retries (int, optional): The maximum number of retry attempts in the event of an error. Defaults to 5.

        Returns:
            Union[bool, str]: 
                * `unstash=True`: returns a bool indicating if the unstash operation succeeded.
                * `unstash=False`: returns a str with the filekey
                * `None`: Error, something went wrong
        """
        fsize = path.stat().st_size
        total_chunks = fsize // _CHUNKSIZE + 1

        log.info("%s: Uploading '%s' to '%s'", wiki, path, title)

        payload = make_params("upload", {"filename": title, "offset": 0, "ignorewarnings": 1, "filesize": fsize, "token": wiki.csrf_token, "stash": 1})

        with path.open('rb') as f:
            buffer = f.read(_CHUNKSIZE)
            chunk_count = 0

            err_count = 0
            while True:
                if err_count > 5:
                    log.error("%s: Encountered %d errors, aborting", wiki, err_count)
                    return

                log.info("%s: Uploading chunk %d of %d from '%s'", wiki, chunk_count+1, total_chunks, path)

                response = wiki.client.post(wiki.endpoint, data=payload, files={'chunk': (path.name, buffer, "multipart/form-data")}, timeout=420)
                if not response:
                    log.warn("%s: Did not get response from server when uploading '%s', retrying...", wiki, path)
                    err_count += 1
                    continue

                response = response.json()
                if "error" in response:
                    log.error("%s: server responded with this error: '%s'", wiki, response['error']['info'])
                    err_count += 1
                    continue

                payload['filekey'] = response["upload"]["filekey"]
                chunk_count += 1
                payload['offset'] = _CHUNKSIZE * chunk_count

                if not (buffer := f.read(_CHUNKSIZE)):
                    break

        if "filekey" not in payload:
            log.error("%s: 'filekey' was not found in response body when uploading '%s': %s", wiki, path, payload)
        elif unstash:
            return WAction.unstash_upload(wiki, payload['filekey'], title, desc, summary, max_retries)
        else:
            return payload['filekey']

    def unstash_upload(wiki: Wiki, filekey: str, title: str, desc: str = "", summary: str = "", max_retries=5, retry_interval=5) -> bool:
        """Attempt to unstash a file uploaded to the file stash.

        Args:
            filekey (str): The filekey of the file in your file stash to unstash (publish).
            title (str): The title to publish the file in the stash to (excluding `File:` prefix).
            desc (str, optional): The text to go on the file description page. Defaults to "".
            summary (str, optional): The upload log summary to use. Defaults to "".
            max_retries (int, optional): The maximum number of retry in the event of failure (assuming the server expereinced an error). Defaults to 5.
            retry_interval (int, optional): The number of seconds to wait in between retries.  Set 0 to disable. Defaults to 5.

        Returns:
            bool: True if unstashing was successful
        """
        log.info("%s: Unstashing '%s' as '%s'", wiki, filekey, title)

        pl = make_params("upload", {"filename": title, "text": desc, "comment": summary, "filekey": filekey, "ignorewarnings": 1})

        tries = 0
        while tries < max_retries:
            response = WAction.post_action(wiki, "upload", pl, timeout=360)

            if WAction.is_success("upload", response):
                return True

            log.error("%s: Could not unstash, server said %s.  Attempt %d of %d. Sleeping %ds...", wiki, WAction.read_error("upload", response), tries+1, max_retries, retry_interval)
            log.debug(response)

            sleep(retry_interval)
            tries += 1

        return False
