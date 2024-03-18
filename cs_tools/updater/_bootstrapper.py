"""
Contains code for the CS Tools Bootstrapper.

This code must stay within the python standard library and be python 3.7+ compliant.

Some of the imports look funny as hell, but essentially we delay them as late as
possible so we don't need to worry about something not being available on an
under-supported version of Python.
"""
from __future__ import print_function
from argparse import RawTextHelpFormatter
import datetime as dt
import sysconfig
import argparse
import platform
import tempfile
import logging
import shutil
import sys
import os

log = logging.getLogger("cs_tools.bootstrapper")
__version__ = "1.0.0"


def cli():
    parser = argparse.ArgumentParser(
        prog="CS Tools Bootstrapper",
        formatter_class=RawTextHelpFormatter,
        description=(
            "Installs, removes, or updates to the latest version of cs_tools"
            "\n "
            "\nFeeling lost? Try our tutorial!"
            "\n{c}https://thoughtspot.github.io/cs_tools/tutorial/{x}".format(c=_BLUE, x=_RESET)
        ),
    )
    parser.add_argument(
        "--offline-mode",
        metavar="DIRECTORY",
        help="install cs_tools from a distributable directory instead of from remote",
        dest="offline_mode",
        type=cli_type_filepath,
        default=None,
    )
    parser.add_argument(
        "--beta",
        help=argparse.SUPPRESS,  # "install a remote pre-release version of CS Tools"
        dest="beta",
        action="store_true",
    )
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument(
        "-i",
        "--install",
        help="install cs_tools to your system {c}(default option){x}".format(c=_GREEN, x=_RESET),
        dest="install",
        action="store_true",
        default=False,
    )
    operation.add_argument(
        "-r",
        "--reinstall",
        help="install on top of existing version",
        dest="reinstall",
        action="store_true",
        default=False,
    )
    operation.add_argument(
        "-u",
        "--uninstall",
        help="remove cs_tools from your system",
        dest="uninstall",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="increase terminal output level",
        dest="verbose",
        action="store_true",
        default=False,
    )

    args = parser.parse_args()
    _setup_logging(args.verbose)
    
    # remove any pre-existing work from a historical install
    if not args.offline_mode:
        _cleanup()

    log.info(
        "{g}Welcome to the CS Tools Bootstrapper!{x}"
        "\n"
        "Ideally, you will only need to run this one time, and then your environment can be fully managed by CS Tools "
        "itself."
        "\n{y}If you run into any issues, please reach out to us on GitHub Discussions below.{x}"
        "\n"
        "\n          GitHub: {b}{github_issues}{x}"
        "\n"
        .format(
            b=_BLUE, g=_GREEN, y=_YELLOW, x=_RESET,
            github_issues="https://github.com/ravikri-bh/cs_tools/issues/new/choose"
        )
    )

    log.debug(
        "\n    [PLATFORM DETAILS]"
        "\n    Python Version: {py_version}"
        "\n       System Info: {system} (detail: {detail})"
        "\n     Platform Tags: {platform_tag}"
        "\n            Ran at: {now}"
        "\n"
        .format(
            system=platform.system(), detail=platform.platform(),
            platform_tag=sysconfig.get_platform(),
            py_version=platform.python_version(),
            now=dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S %z"),
        ),
    )

    try:
        venv = get_cs_tools_venv(find_links=args.offline_mode)
        path = get_path_manipulator(venv)

        if args.install or args.reinstall:
            if not venv.exists:
                log.info("Creating the CS Tools virtual environment.")
                venv.make()

            if args.reinstall:
                log.info("Resetting the CS Tools virtual environment.")
                path.unset()
                venv.reset()

            requires = "cs_tools[cli]"

            if args.offline_mode:
                log.info("Using the offline binary found at {p}{off}{x}".format(p=_PURPLE, x=_RESET, off=venv.find_links))
            else:
                log.info("Getting the latest CS Tools {beta}release.".format(beta="beta " if args.beta else ""))
                release = get_latest_cs_tools_release(allow_beta=args.beta)
                log.info("Found version: {p}{tag}{x}".format(p=_PURPLE, x=_RESET, tag=release["tag_name"]))
                requires += " @ https://github.com/ravikri-bh/cs_tools/archive/{tag}.zip".format(tag=release["tag_name"])

            log.info("Installing CS Tools and its dependencies.")
            venv.pip("install", requires, "--upgrade", "--progress-bar", "on" if args.verbose else "off")
            path.add()

        if args.uninstall:
            log.info("Uninstalling CS Tools and its dependencies.")
            shutil.rmtree(venv.venv_path, ignore_errors=True)
            path.unset()

        log.info("{g}Done!{x} Thank you for trying CS Tools.".format(g=_GREEN, x=_RESET))

        if args.install or args.reinstall:
            log.info(
                "{y}You're almost there! Please {g}restart your shell{x} {y}and then execute the command below.{x}"
                "\n"
                "\n{b}cs_tools --version{x}"
                "\n".format(b=_BLUE, g=_GREEN, y=_YELLOW, x=_RESET)
            )

    finally:
        _cleanup()

    return 0


# ======================================================================================================================
# UTILITIES required only by bootstrapper
# ======================================================================================================================


def _create_color_code(color, bold=False):
    # types: (str, bool) -> str
    # See: https://stackoverflow.com/a/33206814
    escape_sequence = "\033["
    end_sequence = "m"

    foreground_color_map = {
        "reset": 0,
        "black": 30,  # dark gray
        "red": 31,
        "green": 32,
        "yellow": 33,
        "blue": 34,
        "magenta": 35,
        "cyan": 36,
        "white": 37,
    }

    if color not in foreground_color_map:
        raise ValueError("invalid terminal color code: '{color}'".format(color=color))

    to_bold = int(bold)  # 0 = reset , 1 = bold
    to_color = foreground_color_map[color]
    return escape_sequence + str(to_bold) + ";" + str(to_color) + end_sequence


_BLUE = _create_color_code("blue", bold=True)
_GREEN = _create_color_code("green", bold=True)
_RED = _create_color_code("red", bold=True)
_PURPLE = _create_color_code("magenta", bold=True)
_YELLOW = _create_color_code("yellow", bold=True)
_RESET = _create_color_code("reset")


def _setup_logging(verbose=True):
    import tempfile
    import pathlib

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # CONSOLE LOGGER IS PRETTY
    handler = logging.StreamHandler()
    handler.name = "console"

    format_ = ColorSupportedFormatter(datefmt="%H:%M:%S")
    handler.setFormatter(format_)
    handler.setLevel(logging.INFO if not verbose else logging.DEBUG)
    root.addHandler(handler)

    # FILE LOGGER IS VERBOSE
    random_dir  = tempfile.NamedTemporaryFile().name
    random_path = pathlib.Path.cwd() / f"cs_tools-bootstrap-error-{pathlib.Path(random_dir).name}.log"
    handler = InMemoryUntilErrorHandler(random_path)
    handler.name = "disk"

    format_ = logging.Formatter(fmt="%(levelname)-8s | %(asctime)s | %(filename)s:%(lineno)d | %(message)s")
    handler.setFormatter(format_)
    handler.setLevel(logging.DEBUG)
    root.addHandler(handler)


class ColorSupportedFormatter(logging.Formatter):
    """
    Fancy formatter, intended for output to a terminal.

    The log record format itself is fairly locked to look like..

     11:13:51 | Welcome to the CS Tools Installation script!
              |
              |     [PLATFORM DETAILS]
              |     system: Windows (detail: Windows-10-10.0.19041-SP0)
              |     platform tag 'win-amd64'
              |     python: 3.10.4
              |     ran at: 2022-06-12 11:13:51
              |

    Parameters
    ----------
    skip_common_time: bool  [default: True]
      whether or not to repeat the same time format for each line

    indent_amount: int  [default: 2]
      number of spaces to indent child messages by

    **passthru
      keywords to send to logging.Formatter
    """

    COLOR_CODES = {
        logging.CRITICAL: _create_color_code("magenta", bold=True),
        logging.ERROR: _create_color_code("red", bold=True),
        logging.WARNING: _create_color_code("yellow", bold=True),
        logging.INFO: _create_color_code("white"),
        logging.DEBUG: _create_color_code("black", bold=True),
    }

    def __init__(self, skip_common_time=True, **passthru):
        # types: (bool) ->  None
        passthru["fmt"] = "%(asctime)s %(color_code)s| %(indent)s%(message)s%(color_reset)s"
        super().__init__(**passthru)
        self._skip_common_time = skip_common_time
        self._last_time = None
        self._original_datefmt = str(self.datefmt)
        self._try_enable_ansi_terminal_mode()

    def _try_enable_ansi_terminal_mode(self):
        # See: https://stackoverflow.com/a/36760881
        if not sys.platform == "win32":
            return

        import ctypes

        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

    def format(self, record, *a, **kw):
        # types: (logging.LogRecord, a, **kw) -> str
        color = self.COLOR_CODES.get(record.levelno, _create_color_code("white"))
        record.color_code = color
        record.color_reset = _create_color_code("reset")
        record.indent = ""

        # skip repeating the time format if it hasn't changed since last log
        formatted_time = self.formatTime(record, self._original_datefmt)

        if self._skip_common_time:
            if self._last_time == formatted_time:
                self.datefmt = len(formatted_time) * " "
            else:
                self.datefmt = self._original_datefmt
                self._last_time = formatted_time

        # force newlines to respect indentation
        record.message = record.getMessage()
        record.asctime = formatted_time
        s = self.formatMessage(record)
        prefix, _, _ = s.partition(record.msg[:10])
        prefix = prefix.replace(formatted_time, len(formatted_time) * " ")
        record.msg = record.msg.replace("\n", "\n{0}".format(prefix))

        return super().format(record, *a, **kw)


class InMemoryUntilErrorHandler(logging.FileHandler):
    """
    A handler which stores lines in memory until an error is reached,
    and only then writes to file.

    If no error is reached during execution of the program, a logfile will not
    be generated. Once the first error is found, the entire buffer will drain
    into the logfile, with the error itself being the final stub of the file.

    Parameters
    ----------
    directory: pathlib.Path
      base directory to write the logfile to

    prefix: str
      filename identifier, this will have a random suffix attached

    **passthru
      keywords to send to logging.FileHandler
    """

    def __init__(self, filename, **passthru):
        # types: (pathlib.Path, str) -> None
        super().__init__(filename, delay=True, **passthru)
        self._buffer = []
        self._found_error = False

    def drain_buffer(self):
        self._found_error = True

        for prior_record in self._buffer:
            super().emit(prior_record)

    def emit(self, record):
        # types: (logging.LogRecord) -> None
        if self._found_error:
            super().emit(record)
            return

        if record.levelno < logging.ERROR:
            self._buffer.append(record)
            return

        # feed the buffer into the file
        self.drain_buffer()
        super().emit(record)


def cli_type_filepath(fp):
    # type: (str) -> pathlib.Path
    """
    Converts a string to a pathlib.Path.
    """
    import pathlib

    path = pathlib.Path(fp)

    if not path.exists():
        raise argparse.ArgumentTypeError("path '{fp}' does not exist".format(fp=fp))

    if path.is_file():
        raise argparse.ArgumentValueError("path must be a directory, got '{fp}'".format(fp=fp))

    return path


def get_cs_tools_venv(find_links):
    # type: () -> CSToolsVirtualEnvironment
    """Get the CS Tools Virtual Environment."""
    import pathlib

    here = pathlib.Path(__file__).parent
    updater_py = here / "_updater.py"

    if not updater_py.exists():
        log.info("Missing '{updater}', downloading from GitHub".format(updater=updater_py))
        url = "https://api.github.com/repos/ravikri-bh/cs_tools/contents/cs_tools/updater/_updater.py"
        data = http_request(url)
        data = http_request(data["download_url"], to_json=False)
        updater_py.write_text(data.decode())
        log.info("Downloaded as '{updater}'".format(updater=updater_py))

    # Hack the PATH var so we can import from _updater
    sys.path.insert(0, here.as_posix())

    try:
        from _updater import cs_tools_venv
    except ModuleNotFoundError:
        log.info(
            "Unable to find the CS Tools _updater.py, try getting at "
            "{b}https://github.com/ravikri-bh/cs_tools/releases/latest{x}"
            .format(b=_BLUE, x=_RESET)
        )
        raise SystemExit(1) from None

    if find_links is not None:
        cs_tools_venv.with_offline_mode(find_links=find_links)

    return cs_tools_venv


def _cleanup():
    # type: () -> None
    """Remove temporary files for bootstrapping the CS Tools environment."""
    import pathlib

    here = pathlib.Path(__file__).parent

    # don't run the cleanup step within the development environment
    if "updater" in here.as_posix():
        return

    for pathname in ("__pycache__", "_updater.py", "_bootstrapper.py"):
        path = here.joinpath(pathname)

        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)

        if path.is_file():
            try:
                path.unlink()
            except FileNotFoundError:
                pass


def get_path_manipulator(venv):
    # type: () -> _updater.ShellProfilePath
    """Get the system's ShellProfile. This is a CS Tools abstraction."""
    import _updater

    if "fish" in os.environ.get("SHELL", ""):
        return _updater.FishPath(venv)

    if sys.platform == "win32":
        return _updater.WindowsPath(venv)

    return _updater.UnixPath(venv)


def http_request(url, to_json=True, timeout=None):
    # type: (str, bool) -> Dict[str, Any]
    """
    Makes a GET request to <url>.
    """
    import urllib.request
    import json
    import ssl

    ctx = ssl.create_default_context()

    # OP_LEGACY_SERVER_CONNECT is missing until py3.12
    #
    # Further Reading:
    #   https://bugs.python.org/issue44888
    ssl.OP_LEGACY_SERVER_CONNECT = 0x4
    ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT

    # Disable SSL verfication checks.
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    with urllib.request.urlopen(url, timeout=timeout, context=ctx) as r:
        data = r.read()

    if to_json:
        data = json.loads(data)

    return data


def get_latest_cs_tools_release(allow_beta=False, timeout=None):
    # type: (bool) -> Dict[str, Any]
    """
    Get the latest CS Tools release.
    """
    releases = http_request("https://api.github.com/repos/ravikri-bh/cs_tools/releases", timeout=timeout)

    for release in releases:
        if release["prerelease"] and not allow_beta:
            continue
        break

    return release


# ======================================================================================================================
# MAIN PROGRAM
# ======================================================================================================================


def main():
    # type: () -> int
    if sys.version_info >= (3, 7):
        try:
            return_code = cli()

        except Exception as e:
            disk_handler = next(h for h in log.root.handlers if h.name == "disk")
            disk_handler.drain_buffer()
            log.debug("Error found: {err}".format(err=e), exc_info=True)
            log.warning(
                "Unexpected error in bootstrapper, see {b}{logfile}{x} for details.."
                .format(b=_BLUE, logfile=disk_handler.baseFilename, x=_RESET)
            )
            return_code = 1

        return return_code

    # =====================
    # VERSION CHECK FAILED
    # =====================

    args = " ".join(map(str, sys.argv))
    py_vers = ".".join(map(str, sys.version_info[:2]))

    msg = (
        "{y}It looks like you are running {r}Python v{version}{y}!{x}"
        "\n"
        "\nCS Tools supports {b}python version 3.7{x} or greater."
    )

    if sys.version_info <= (2, 7, 99) and not (sys.platform == "win32"):
        msg += "\n" "{b}Please re-run the following command..{x}" "\n" "\npython3 {args}" "\n"
    else:
        msg += (
            "\n"
            "\n{y}Python installers are available for download for all versions at..{x}"
            "\n{b}https://www.python.org/downloads/{x}"
            "\n"
        )

    formatting = {
        "b": _BLUE,
        "r": _RED,
        "y": _YELLOW,
        "x": _RESET,
        "version": py_vers,
        "args": args,
    }

    print(msg.format(**formatting))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
