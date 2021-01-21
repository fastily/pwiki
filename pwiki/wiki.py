"""Classes for use by a client to interact with a MediaWiki instance's API"""
import logging
import pickle

from pathlib import Path
from typing import Union

from .oquery import OQuery
from .waction import WAction

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
        self.is_bot = False #TODO: set bot status on login

        if cookie_jar and cookie_jar.is_file():
            log.info("%s: Loading cookies from '%s'", self, cookie_jar)
            with cookie_jar.open('rb') as f:
                self.client.cookies = pickle.load(f)

            self.csrf_token = OQuery.fetch_token(self)
            self.username = self.whoami()

        self.is_logged_in = self.csrf_token != "+\\" or username and password and self.login(username, password)

    def __repr__(self) -> str:
        """Generate a str representation of this Wiki object.  Useful for logging.

        Returns:
            str: A str representation of this Wiki object.
        """
        return f"[{self.username or '<Anonymous>'} @ {self.domain}]"

    def clear_cookies(self, cookie_jar: Path = _DEFAULT_COOKIE_JAR):
        """Deletes any saved cookies from disk.

        Args:
            cookie_jar (Path, optional): The local Path to the cookie jar. Defaults to _DEFAULT_COOKIE_JAR.
        """
        log.info("%s: Removing cookie jar at '%s'", self, cookie_jar)

        cookie_jar.unlink(True)

    def save_cookies(self, output_path: Path = _DEFAULT_COOKIE_JAR):
        """Write the cookies of the Wiki object to disk, so they can be used in the future.

        Args:
            output_path (Path, optional): The local path to save the cookies at.  Defaults to _DEFAULT_COOKIE_JAR (`./pwiki.pickle`).
        """
        log.info("%s: Saving cookies to '%s'", self, output_path)

        with output_path.open('wb') as f:
            pickle.dump(self.client.cookies, f)

    ##################################################################################################
    ######################################## A C T I O N S ###########################################
    ##################################################################################################

    def login(self, username: str, password: str) -> bool:
        """Attempts to login this Wiki object.  If successful, all future calls will be automatically include authentication.

        Args:
            username (str): The username to login with
            password (str): The password to login with

        Returns:
            bool: True if successful
        """
        return WAction.login(self, username, password)

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
        return WAction.edit(self, title, text, summary, prepend, append, minor)

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
        return WAction.upload(self, path, title, desc, summary, unstash, max_retries)

    ##################################################################################################
    ######################################## Q U E R I E S ###########################################
    ##################################################################################################

    def uploadable_filetypes(self) -> set:
        """Queries the Wiki for all acceptable file types which may be uploaded to this Wiki.  PRECONDITION: the target Wiki permits file uploads.

        Returns:
            set: A set containing all acceptable file types as their extensions ("." prefix is included) 
        """
        return OQuery.uploadable_filetypes(self)

    def whoami(self) -> str:
        """Get this Wiki's username from the server.  If not logged in, then this will return your external IP address.

        Returns:
            str: If logged in, this Wiki's username.  Otherwise, the external IP address of your device.
        """
        return OQuery.whoami(self)
