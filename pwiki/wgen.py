import base64
import re
import getpass

from pathlib import Path


class Wgen:

    @staticmethod
    def load_px(px_file=Path(".px.txt")):
        """Loads the specified password file if it exists.  Returns a dictionary with username/passwords that were found

        :param load_px: The path to the password file
        """
        pxf = Path.home() / px_file

        if not pxf.is_file():
            raise FileNotFoundError(f"{pxf} does not exist or is a directory. Did you run Wgen yet?  If there is a dir here, rename it first.")

        return dict([line.split("\t") for line in base64.b64decode(pxf.read_text().encode()).decode().strip().splitlines()])

    @staticmethod
    def setup(out_file=Path(".px.txt"), allow_continue=True):
        """Interactively creates a password file.

        :param out_file: The path to create the password file at.  CAVEAT: If a file exists at this location exists it will be overwritten.
        :param allow_continue: Set True to allow user to enter more than one user-pass combo.
        """
        pxl = {}

        while True:
            print("Please enter the username/password combo(s) you would like to use.")
            u = input("Username: ")
            p = getpass.getpass()
            confirm_p = getpass.getpass("Confirm Password: ")

            if p != confirm_p:
                print("ERROR: Entered passwords do not match")
                if not re.match("(?i)(y|yes)", input("Try again? (y/N): ")):
                    break
            else:
                pxl[u] = p

                if not allow_continue or not re.match("(?i)(y|yes)", input("Continue? (y/N): ")):
                    break

        if not pxl:
            print("WARNING: You did not make any entries.  Doing nothing.")
            return

        out_file.write_text(base64.b64encode("\n".join([f"{k}\t{v}" for k, v in pxl.items()]).encode()).decode())
        print(f"Successfully created '{out_file}'")
