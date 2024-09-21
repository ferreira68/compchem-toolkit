#  Copyright © 2024 Antonio M. Ferreira, Ph.D.
#
#  Project       : compchem-toolkit
#  File          : paths.py
#  Last Modified : 9/13/2024
#
#  This software is covered by the MIT License (see LICENSE file for details).
"""Custom path handling for CompChemToolkit code."""
from pathlib import Path
from typing import Optional
from typing import Union


# Define type alias for path specifications.
PathSpec = Optional[Union[str, Path]]


def set_pathspec(fpath: Union[PathSpec, None]) -> Path:
    """
    Standardize a filepath.

    Args:
        fpath (PathSpec): A path specification (str or pathlib.Path or None).

    Returns:
        Path: An absolute pathlib.Path object in standard form.

    Raises:
        ValueError: If fpath is not a string or Path.
    """
    if fpath is None:
        fpath = ""

    if not isinstance(fpath, (str, Path)):
        raise ValueError(f"Invalid fpath type: {type(fpath)}, must be str or Path")

    return Path(fpath).absolute().resolve()
