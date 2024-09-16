"""Pytest test for main entry point."""

import sys
from io import StringIO
from typing import Callable
from typing import Tuple
from unittest.mock import patch

import pytest

from compchem_toolkit import __main__


@pytest.fixture
def runner() -> Callable[[str], Tuple[int, str, str]]:
    """Fixture for invoking command-line interfaces."""

    def run(args: str) -> Tuple[int, str, str]:
        with patch.object(sys, "argv", args.split()):
            with patch("sys.stdout", new_callable=StringIO) as stdout:
                with patch("sys.stderr", new_callable=StringIO) as stderr:
                    try:
                        __main__.main(prog_name=args.split()[0])
                        return 0, stdout.getvalue(), stderr.getvalue()
                    except SystemExit as e:
                        exit_code = e.code if isinstance(e.code, int) else 1
                        return exit_code, stdout.getvalue(), stderr.getvalue()

    return run


def test_main_succeeds(runner: Callable[[str], Tuple[int, str, str]]) -> None:
    """It exits with a status code of zero."""
    exit_code, stdout, stderr = runner("program_name")
    assert exit_code == 0
