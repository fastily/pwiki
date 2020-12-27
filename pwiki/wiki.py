"""Classes for use by a client to interact with a MediaWiki instance's API"""
import logging

from pathlib import Path

import requests

_API_DEFAULTS = {"format": "json", "formatversion": "2"}

_CHUNKSIZE = 1024 * 1024 * 4

log = logging.getLogger(__name__)


class Wiki:
    """General wiki-interfacing functionality and config data"""

    def __init__(self, domain: str = "en.wikipedia.org", username: str = None, password: str = None):
        """Initializer, creates a new Wiki object.

        Args:
            domain (str): The shorthand domain of the Wiki to target (e.g. "en.wikipedia.org")
            username (str, optional): The username to login as. Does nothing if password is not set.  Defaults to None.
            password (str, optional): The password to use when logging in. Does nothing if username is not set.  Defaults to None.
        """
        self.endpoint = f"https://{domain}/w/api.php"
        self.domain = domain
        self.client = requests.Session()
        self.username = username

        self.csrf_token = None

        if username and password:
            self.login(username, password)

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

        response = self.client.post(self.endpoint, params=self._make_params("login"), data={"lgname": username, "lgpassword": password, "lgtoken": self._get_tokens()["logintoken"]})

        # TODO: Handle bad login
        self.username = response.json()["login"]["lgusername"]
        self.csrf_token = self._get_tokens()['csrftoken']

        return True

    def _get_tokens(self) -> dict:
        """Retrieves CSRF and login tokens. 

        Returns:
            dict: a dict with two keys 'csrftoken' (for CSRF token) and 'logintoken' (for login tokens)
        """
        log.info("%s: Fetching tokens...", self)

        return self.client.get(self.endpoint, params=self._make_params("query", {"meta": "tokens", "type": "csrf|login"})).json()['query']['tokens']

    def upload(self, path: Path, title: str, desc: str, summary: str) -> bool:
        """Uploads a file to the target Wiki.

        Args:
            path (Path): the local path on your computer pointing to the file to upload.
            title (str): The title to upload the file to, excluding the "`File:`" namespace.
            desc (str): The text that should go on the file's description page.
            summary (str): The upload log summary to use.

        Returns:
            bool: True if the upload was successful.
        """

        # fsize = os.path.getsize(path)
        fsize = path.stat().st_size
        total_chunks = fsize // _CHUNKSIZE + 1

        log.info("%s: Uploading '%s' to '%s'", self, path, title)

        data = {**_API_DEFAULTS, "filename": title, "offset": '0', "ignorewarnings": "1", "filesize": str(fsize), "token": self.csrf_token, "stash": "1"}

        # with open(path, 'rb') as f:
        with path.open('rb') as f:
            buffer = f.read(_CHUNKSIZE)
            chunk_count = 0

            err_count = 0
            while True:
                if err_count > 5:
                    log.error("%s: Encountered %d errors, aborting", self, err_count)
                    return False

                log.info("%s: Uploading chunk %d of %d from '%s'", self, chunk_count+1, total_chunks, path)

                response = self.client.post(self.endpoint, params={"action": "upload"}, data=data, files={'chunk': (path.name, buffer, "multipart/form-data")}, timeout=420)
                if not response:
                    log.warn("%s: Did not get response from server when uploading '%s', retrying...", self, path)
                    err_count += 1
                    continue

                response = response.json()
                if "error" in response:
                    log.error("%s: server responded with this error: '%s'", self, response['error']['info'])
                    err_count += 1
                    continue

                data['filekey'] = response["upload"]["filekey"]
                chunk_count += 1
                data['offset'] = str(_CHUNKSIZE * chunk_count)

                # buffer = f.read(_CHUNKSIZE)
                if not (buffer := f.read(_CHUNKSIZE)):
                    break

        if "filekey" not in data:
            return False

        log.info("%s: Unstashing %s as %s", self, data['filekey'], title)
        pl = {"filename": title, "text": desc, "comment": summary, "filekey": data['filekey'], "ignorewarnings": "1", "token": self.csrf_token}
        pl.update(_API_DEFAULTS)
        response = self.client.post(self.endpoint, params={"action": "upload"}, data=pl, timeout=420).json()

        if 'error' in response:
            log.error("%s: got error from server: '%s'", self, response['error']['info'])
            return False

        return response['upload']['result'] == "Success"


    def unstash_upload(self, filekey: str, title: str, desc: str, summary: str, max_retries=5):
        log.info("%s: Unstashing %s as %s", self, filekey, title)

        pl = {**_API_DEFAULTS, "filename": title, "text": desc, "comment": summary, "filekey": filekey, "ignorewarnings": "1", "token": self.csrf_token}
        # pl.update(_API_DEFAULTS)

        tries = 0
        while tries < max_retries:
            response = self.client.post(self.endpoint, params={"action": "upload"}, data=pl, timeout=420).json()

            if 'error' in response:
                log.error("%s: got error from server on unstash attempt %d of %d: '%s'", self, tries+1, max_retries, response['error']['info'])
                tries += 1
            else:
                return response['upload']['result'] == "Success"
        
        return False