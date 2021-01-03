"""Classes for use by a client to interact with a MediaWiki instance's API"""
import logging
import pickle

from pathlib import Path
from time import sleep
from typing import Union

import requests

_API_DEFAULTS = {"format": "json", "formatversion": "2"}

_CHUNKSIZE = 1024 * 1024 * 4

_DEFAULT_COOKIE_JAR = Path("./pwiki.pickle")

log = logging.getLogger(__name__)


class Wiki:
    """General wiki-interfacing functionality and config data"""

    def __init__(self, domain: str = "en.wikipedia.org", username: str = None, password: str = None, cookie_jar: Path = _DEFAULT_COOKIE_JAR):
        """Initializer, creates a new Wiki object.

        Args:
            domain (str): The shorthand domain of the Wiki to target (e.g. "en.wikipedia.org")
            username (str, optional): The username to login as. Does nothing if `password` is not set.  Defaults to None.
            password (str, optional): The password to use when logging in. Does nothing if `username` is not set.  Defaults to None.
        """
        self.endpoint = f"https://{domain}/w/api.php"
        self.domain = domain
        self.client = requests.Session()
        self.csrf_token = "+\\"
        self.username = None

        if cookie_jar and cookie_jar.is_file():
            with cookie_jar.open('rb') as f:
                self.client.cookies = pickle.load(f)

            self.csrf_token = self._fetch_token()
            # TODO: Get username from API

        self.is_logged_in = self.csrf_token != "+\\" or username and password and self.login(username, password)

        # if username and password and self.csrf_token == "+\\":
        #     self.login(username, password)

    def __repr__(self) -> str:
        """Generate a str representation of this Wiki object.  Useful for logging.

        Returns:
            str: A str representation of this Wiki object.
        """
        return f"[{self.username or '<Anonymous>'} @ {self.domain}]"

    def _make_params(self, action: str, pl: dict = None) -> dict:
        """Convienence method to generate payload parameters.  Fills in useful details that should be submitted with every request.

        Args:
            action (str): The action value (e.g. "query", "edit", "purge")
            pl (dict, optional): Additional parameters besides the defaults in _API_DEFAULTS and the action parameter. Defaults to None.

        Returns:
            dict: A new dict with the parameters
        """
        return {**_API_DEFAULTS, **(pl or {}), "action": action}

    def save_cookies(self, output_path: Path = _DEFAULT_COOKIE_JAR):
        """Write the cookies of the Wiki object to disk, so they can be used in the future.

        Args:
            output_path (Path, optional): The local path to save the cookies at.  Defaults to _DEFAULT_COOKIE_JAR (`./pwiki.pickle`).
        """
        with output_path.open('wb') as f:
            pickle.dump(self.client.cookies, f)

    def uploadable_filetypes(self) -> set:
        """Queries the Wiki for all acceptable file types which may be uploaded to this Wiki.  PRECONDITION: the target Wiki permits file uploads.

        Returns:
            set: A set containing all acceptable file types as their extensions ("." prefix is included) 
        """
        log.info("%s: Fetching a list of acceptable file upload extensions", self)

        response = self.client.get(self.endpoint, params=self._make_params("query", {"meta": "siteinfo", "siprop": "fileextensions"}))
        return {jo["ext"] for jo in response.json()["query"]['fileextensions']}

    def login(self, username: str, password: str) -> bool:
        """Attempts to login this Wiki object.  If successful, all future calls will be automatically include authentication.

        Args:
            username (str): The username to login with
            password (str): The password to login with

        Returns:
            bool: True if successful
        """
        log.info("%s: Attempting login for %s", self, username)

        response = self.client.post(self.endpoint, params=self._make_params("login"), data={"lgname": username, "lgpassword": password, "lgtoken": self._fetch_token(login_token=True)})

        # TODO: Handle bad login
        self.username = response.json()["login"]["lgusername"]

        log.info("%s: Successfully logged in as %s", self, self.username)
        self.csrf_token = self._fetch_token()

        return True

    def _fetch_token(self, login_token: bool = False) -> str:
        """Fetch a csrf or login token from the server.  By default, this method will retrieve a csrf token.

        Args:
            login_token (bool, optional): Set `True` to get a login token instead of a csrf token. Defaults to False.

        Raises:
            Exception: if there was a server error or the token couldn't be retrieved.

        Returns:
            str: The token as a str.
        """
        pl = {"meta": "tokens"}
        if login_token:
            pl["type"] = "login"

        try:
            return self.client.get(self.endpoint, params=self._make_params("query", pl)).json()['query']['tokens']["logintoken" if login_token else "csrftoken"]
        except Exception as e:
            log.critical("Couldn't get tokens", exc_info=True)
            raise e

    def upload(self, path: Path, title: str, desc: str = "", summary: str = "", unstash=True, max_retries=5) -> Union[bool, str]:
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

        log.info("%s: Uploading '%s' to '%s'", self, path, title)

        payload = {**_API_DEFAULTS, "filename": title, "offset": 0, "ignorewarnings": 1, "filesize": fsize, "token": self.csrf_token, "stash": 1}

        with path.open('rb') as f:
            buffer = f.read(_CHUNKSIZE)
            chunk_count = 0

            err_count = 0
            while True:
                if err_count > 5:
                    log.error("%s: Encountered %d errors, aborting", self, err_count)
                    return

                log.info("%s: Uploading chunk %d of %d from '%s'", self, chunk_count+1, total_chunks, path)

                response = self.client.post(self.endpoint, params={"action": "upload"}, data=payload, files={'chunk': (path.name, buffer, "multipart/form-data")}, timeout=420)
                if not response:
                    log.warn("%s: Did not get response from server when uploading '%s', retrying...", self, path)
                    err_count += 1
                    continue

                response = response.json()
                if "error" in response:
                    log.error("%s: server responded with this error: '%s'", self, response['error']['info'])
                    err_count += 1
                    continue

                payload['filekey'] = response["upload"]["filekey"]
                chunk_count += 1
                payload['offset'] = _CHUNKSIZE * chunk_count

                if not (buffer := f.read(_CHUNKSIZE)):
                    break

        if "filekey" not in payload:
            log.error("%s: 'filekey' was not found in response body when uploading '%s': %s", self, path, payload)
        elif unstash:
            return self.unstash_upload(payload['filekey'], title, desc, summary, max_retries)
        else:
            return payload['filekey']

    def unstash_upload(self, filekey: str, title: str, desc: str = "", summary: str = "", max_retries=5, retry_interval=5) -> bool:
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
        log.info("%s: Unstashing '%s' as '%s'", self, filekey, title)

        pl = {**_API_DEFAULTS, "filename": title, "text": desc, "comment": summary, "filekey": filekey, "ignorewarnings": 1, "token": self.csrf_token}

        tries = 0
        while tries < max_retries:
            response = self.client.post(self.endpoint, params={"action": "upload"}, data=pl, timeout=420).json()
            if 'error' not in response and response['upload']['result'] == "Success":
                return True

            log.error("%s: got error from server on unstash attempt %d of %d.  Sleeping %ds...", self, tries+1, max_retries, retry_interval)
            log.debug(response)

            sleep(retry_interval)
            tries += 1

        return False
