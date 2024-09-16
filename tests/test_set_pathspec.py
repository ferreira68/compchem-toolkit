#  Copyright © 2024 Antonio M. Ferreira, Ph.D.
#
#  Project       : compchem-toolkit
#  File          : test_set_pathspec.py
#  Last Modified : 9/13/2024
#
#  This software is covered by the MIT License (see LICENSE file for details).

from pathlib import Path

import pytest

from compchem_toolkit.utils.paths import (
    set_pathspec,  # Replace `your_module` with the actual name of your module
)


def test_set_pathspec_with_none() -> None:
    assert set_pathspec(None) == Path("").absolute().resolve()


def test_set_pathspec_with_valid_str() -> None:
    path_str = "some/relative/path"
    expected = Path(path_str).absolute().resolve()
    assert set_pathspec(path_str) == expected


def test_set_pathspec_with_valid_path() -> None:
    path_obj = Path("some/relative/path")
    expected = path_obj.absolute().resolve()
    assert set_pathspec(path_obj) == expected


def test_set_pathspec_with_empty_str() -> None:
    assert set_pathspec("") == Path("").absolute().resolve()


def test_set_pathspec_with_absolute_str() -> None:
    path_str = "/already/absolute/path"
    assert set_pathspec(path_str) == Path(path_str).absolute().resolve()


def test_set_pathspec_with_invalid_type() -> None:
    with pytest.raises(
        ValueError, match="Invalid fpath type: <class 'int'>, must be str or Path"
    ):
        set_pathspec(123)


@pytest.mark.parametrize("input_path", ["/absolute/path", "/another/absolute/path"])
def test_set_pathspec_with_parametrize(input_path) -> None:
    """Test with multiple absolute paths using parametrize."""
    assert set_pathspec(input_path) == Path(input_path).absolute().resolve()
