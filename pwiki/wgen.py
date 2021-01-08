import base64
# import re
import getpass

from pathlib import Path

_DEFAULT_PX = Path.home() / ".px.txt"

class Wgen:
    """Simple secret manager which provides an interactive way to input, save, and load credentials for use with pwiki."""
    @staticmethod
    def load_px(px_file: Path = _DEFAULT_PX) -> dict:
        """Loads the specified password file if it exists.  Returns a dictionary with username/passwords that were found

        Args:
            px_file (Path, optional): The path to the password file. Defaults to _DEFAULT_PX.

        Raises:
            FileNotFoundError: If a file at Path `px_file` does not exist on the local file system.

        Returns:
            dict: A dict with credentials such that each key is the username and each value is the password.
        """
        if not px_file.is_file():
            raise FileNotFoundError(f"'{px_file}' does not exist or is a directory. Did you run Wgen yet?  If there is a dir here, rename it first.")

        return dict([line.split("\t") for line in base64.b64decode(px_file.read_text().encode()).decode().strip().splitlines()])

    @staticmethod
    def setup(out_file: Path = _DEFAULT_PX, allow_continue: bool = True):
        """Interactively creates a credential save file.

        Args:
            out_file (Path, optional): The path to create the password file at.  CAVEAT: If a file exists at this location exists it will be overwritten. Defaults to _DEFAULT_PX.
            allow_continue (bool, optional): Set True to allow user to enter more than one user-pass combo. Defaults to True.
        """
        pxl = {}

        while True:
            print("Please enter the username/password combo(s) you would like to use.")
            u = input("Username: ")
            p = getpass.getpass()
            confirm_p = getpass.getpass("Confirm Password: ")

            if p != confirm_p:
                print("ERROR: Entered passwords do not match")
                if Wgen._user_says_no("Try again?"):
                    break
                # if not re.match("(?i)(y|yes)", input("Try again? (y/N): ")):
                #     break
            else:
                pxl[u] = p

                # if not allow_continue or not re.match("(?i)(y|yes)", input("Continue? (y/N): ")):
                if not allow_continue or Wgen._user_says_no("Continue?"):  # not re.match("(?i)(y|yes)", input("Continue? (y/N): ")):
                    break

        if not pxl:
            print("WARNING: You did not make any entries.  Doing nothing.")
            return

        out_file.write_text(base64.b64encode("\n".join([f"{k}\t{v}" for k, v in pxl.items()]).encode()).decode())
        print(f"Successfully created '{out_file}'")

    @staticmethod
    def _user_says_no(question: str) -> bool:
        """Ask the user a question via interactive command line.

        Args:
            question (str): The question to ask.  `" (y/N): "` will be automatically appended to the question.

        Returns:
            bool: True if the user responded with something other than `"y"` or `"yes"`.
        """
        return input(question + " (y/N): ").strip().lower() not in ("y", "yes")
