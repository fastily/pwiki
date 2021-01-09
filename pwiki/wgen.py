"""Simple secret manager which provides an interactive way to input, save, and load credentials for use with pwiki."""
import argparse
import base64
import getpass

from pathlib import Path
from pprint import pprint

_DEFAULT_PX = Path.home() / ".px.txt"


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
        raise FileNotFoundError(f"'{px_file}' does not exist or is a directory. Did you run Wgen yet?  If there is a directory here, rename it before proceeding.")

    return dict([line.split("\t") for line in base64.b64decode(px_file.read_text().encode()).decode().strip().splitlines()])


def setup_px(out_file: Path = _DEFAULT_PX, allow_continue: bool = True, edit_mode: bool = False):
    """Interactively creates a credential save file.

    Args:
        out_file (Path, optional): The path to create the password file at.  CAVEAT: If a file exists at this location exists it will be overwritten. Defaults to _DEFAULT_PX.
        allow_continue (bool, optional): Set True to allow user to enter more than one user-pass combo. Defaults to True.
        edit_mode (bool, optional): Enables edit mode, meaning that entries of an existing file will be modified. Does nothing if `out_file` does not exist. Defaults to False.
    """
    pxl = load_px(out_file) if edit_mode and out_file.is_file() else {}

    while True:
        print("Please enter the username/password combo(s) you would like to use.")
        u = input("Username: ")
        p = getpass.getpass()
        confirm_p = getpass.getpass("Confirm Password: ")

        if p != confirm_p:
            print("ERROR: Entered passwords do not match")
            if _user_says_no("Try again?"):
                break
        else:
            pxl[u] = p

            if not allow_continue or _user_says_no("Continue?"):
                break

    if not pxl:
        print("WARNING: You did not make any entries.  Doing nothing.")
        return

    out_file.write_text(base64.b64encode("\n".join([f"{k}\t{v}" for k, v in pxl.items()]).encode()).decode())
    print(f"Entries successfully written out to '{out_file}'")


def _user_says_no(question: str) -> bool:
    """Ask the user a question via interactive command line.

    Args:
        question (str): The question to ask.  `" (y/N): "` will be automatically appended to the question.

    Returns:
        bool: True if the user responded with something other than `"y"` or `"yes"`.
    """
    return input(question + " (y/N): ").strip().lower() not in ("y", "yes")


def main():
    """Main driver, to be used when this module is invoked via CLI."""
    cli_parser = argparse.ArgumentParser(description="pwiki Wgen credential manager")
    cli_parser.add_argument('--px-path', type=Path, default=_DEFAULT_PX, dest="px_path", help="The local path to write the password file to")
    cli_parser.add_argument("-e", action='store_true', dest="edit_mode", help="Enables edit/append mode, instead of overwrite (the default)")
    cli_parser.add_argument("--show", action='store_true', help="Read and shows the contents of the px file instead of writing/editing.  This overrides the -e option.")
    args = cli_parser.parse_args()

    if args.show:
        try:
            pprint(load_px(args.px_path))
        except FileNotFoundError as e:
            print(e)
    else:
        try:
            setup_px(args.px_path, edit_mode=args.edit_mode)
        except KeyboardInterrupt:
            print("\nkeyboard interrupt, no changes will be made.")


if __name__ == "__main__":
    main()
