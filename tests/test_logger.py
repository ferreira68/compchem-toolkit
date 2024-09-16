#  Copyright © 2024 Antonio M. Ferreira, Ph.D.
#
#  Project       : compchem-toolkit
#  File          : test_logger.py
#  Last Modified : 9/13/2024
#
#  This software is covered by the MIT License (see LICENSE file for details).
import logging
import pathlib
import sys

import pytest

from compchem_toolkit.utils.paths import set_pathspec


# Import the logger class from its module
sys.path.insert(0, "./src/compchem_toolkit/utils")
from logger import CompChemLogger  # noqa


@pytest.fixture
def logger_kwargs(tmpdir):
    logdir = tmpdir.mkdir("logs")
    return {
        "console": logging.DEBUG,
        "file": logging.DEBUG,
        "fname": set_pathspec("test.log"),
        "logdir": set_pathspec(str(logdir)),
        "name": "test_logger",
        "propagate": True,
    }


@pytest.fixture
def compchemlogger(logger_kwargs):
    return CompChemLogger(**logger_kwargs)


def test_compchemlogger_instantiation(compchemlogger):
    assert isinstance(compchemlogger, CompChemLogger)


def test_compchemlogger_has_correct_attributes(compchemlogger, logger_kwargs):
    for key, value in logger_kwargs.items():
        assert getattr(compchemlogger, key) == value


def test_compchemlogger_validate_keywords(compchemlogger):
    invalid_keywords = {"invalid": "value"}
    with pytest.raises(KeyError):
        compchemlogger.validate_keywords(invalid_keywords)


def test_compchemlogger_set_defaults(compchemlogger):
    default_kwargs = {
        "name": "test_logger",
        "console": None,
        "file": None,
        "logdir": None,
        "fname": CompChemLogger.DEFAULT_FNAME,
        "propagate": True,
    }
    compchemlogger.set_defaults(default_kwargs)
    for key, value in default_kwargs.items():
        assert getattr(compchemlogger, key) == value


def test_compchemlogger_validate_fname(compchemlogger, tmpdir):
    path = tmpdir.join("test.log")
    result = compchemlogger._validate_fname(str(path))
    assert result == pathlib.Path(str(path)).resolve()


def test_compchemlogger_setup_logging_path(compchemlogger, logger_kwargs):
    compchemlogger.setup_logging_path(logger_kwargs)
    assert (
        compchemlogger.logfile
        == pathlib.Path(logger_kwargs["logdir"], logger_kwargs["fname"]).resolve()
    )


def test_compchemlogger_expand_user_path(compchemlogger):
    path = "~/logs"
    expected_path = pathlib.Path.home() / "logs"
    assert compchemlogger._expand_user_path(path) == expected_path


def test_compchemlogger_ensure_logdir_exists(compchemlogger, logger_kwargs):
    logdir = pathlib.Path(logger_kwargs["logdir"])
    compchemlogger._ensure_logdir_exists()
    assert logdir.exists()


def test_compchemlogger_handle_logdir_creation(compchemlogger, logger_kwargs):
    logdir = pathlib.Path(logger_kwargs["logdir"])
    compchemlogger.handle_logdir_creation()
    assert logdir.exists()


def test_compchemlogger_create_logger(compchemlogger, logger_kwargs):
    created_logger = compchemlogger.create_logger(logger_kwargs)
    assert isinstance(created_logger, logging.Logger)
