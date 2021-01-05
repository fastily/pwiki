"""Classes for use by a client to interact with a MediaWiki instance's API"""
import logging
import pickle

from pathlib import Path

from .waction import WAction
from .utils import make_params

import requests


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
        self.is_bot = False

        if cookie_jar and cookie_jar.is_file():
            with cookie_jar.open('rb') as f:
                self.client.cookies = pickle.load(f)

            self.csrf_token = self._fetch_token()
            # TODO: Get username from API

        self.is_logged_in = self.csrf_token != "+\\" or username and password and self.login(username, password)

    def __repr__(self) -> str:
        """Generate a str representation of this Wiki object.  Useful for logging.

        Returns:
            str: A str representation of this Wiki object.
        """
        return f"[{self.username or '<Anonymous>'} @ {self.domain}]"

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

        response = self.client.get(self.endpoint, params=make_params("query", {"meta": "siteinfo", "siprop": "fileextensions"}))
        return {jo["ext"] for jo in response.json()["query"]['fileextensions']}

    def login(self, username: str, password: str) -> bool:
        """Attempts to login this Wiki object.  If successful, all future calls will be automatically include authentication.

        Args:
            username (str): The username to login with
            password (str): The password to login with

        Returns:
            bool: True if successful
        """
        return WAction.login(self, username, password)

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
            return self.client.get(self.endpoint, params=make_params("query", pl)).json()['query']['tokens']["logintoken" if login_token else "csrftoken"]
        except Exception as e:
            log.critical("Couldn't get tokens", exc_info=True)
            raise e
