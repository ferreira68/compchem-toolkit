import pytest
import logging
from pathlib import Path
import tempfile
from compchem_toolkit.utils.logger import (
    CompChemLogger,
    named_logging,
    close_logger_handlers,
    remove_logger_from_root,
    close_logger,
    TqdmToLogger,
)

@pytest.fixture
def logger_instance():
    return CompChemLogger()

@pytest.mark.parametrize(
    "kwargs, expected_name, expected_console, expected_file, expected_logdir, expected_fname, expected_propagate",
    [
        ({"name": "TestLogger"}, "TestLogger", None, logging.WARNING, Path.cwd(), "compchem_toolkit.log", True),
        ({"console": logging.DEBUG}, "CompChemToolkit", logging.DEBUG, logging.WARNING, Path.cwd(), "compchem_toolkit.log", True),
        ({"file": logging.ERROR}, "CompChemToolkit", None, logging.ERROR, Path.cwd(), "compchem_toolkit.log", True),
        ({"logdir": "/tmp/logs"}, "CompChemToolkit", None, logging.WARNING, Path("/tmp/logs"), "compchem_toolkit.log", True),
        ({"fname": "test.log"}, "CompChemToolkit", None, logging.WARNING, Path.cwd(), "test.log", True),
        ({"propagate": False}, "CompChemToolkit", None, logging.WARNING, Path.cwd(), "compchem_toolkit.log", False),
    ],
    ids=[
        "name_only",
        "console_only",
        "file_only",
        "logdir_only",
        "fname_only",
        "propagate_only",
    ]
)
def test_compchem_logger_init(kwargs, expected_name, expected_console, expected_file, expected_logdir, expected_fname, expected_propagate):
    # Act
    logger = CompChemLogger(**kwargs)

    # Assert
    assert logger.name == expected_name
    assert logger.console == expected_console
    assert logger.file == expected_file
    # assert logger.logdir == expected_logdir
    assert logger.fname.name == expected_fname
    assert logger.propagate == expected_propagate

@pytest.mark.parametrize(
    "kwargs, expected_exception",
    [
        ({"unknown_key": "value"}, KeyError),
    ],
    ids=[
        "unknown_keyword",
    ]
)
def test_compchem_logger_init_invalid_keywords(kwargs, expected_exception):
    # Act & Assert
    with pytest.raises(expected_exception):
        CompChemLogger(**kwargs)

@pytest.mark.parametrize(
    "fname, expected_exception",
    [
        (123, ValueError),
        (None, ValueError),
    ],
    ids=[
        "invalid_type_int",
        "invalid_type_none",
    ]
)
def test_validate_fname_invalid(fname, expected_exception, logger_instance):
    # Act & Assert
    with pytest.raises(expected_exception):
        logger_instance._validate_fname(fname)

@pytest.mark.parametrize(
    "logdir, expected_logdir",
    [
        ("~/logs", Path.home() / "logs"),
        ("/tmp/logs", Path("/tmp/logs")),
    ],
    ids=[
        "expand_user_path",
        "absolute_path",
    ]
)
def test_expand_user_path(logdir, expected_logdir, logger_instance):
    # Act
    expanded_path = logger_instance._expand_user_path(logdir)

    # Assert
    assert expanded_path == expected_logdir

def test_ensure_logdir_exists(logger_instance):
    # Arrange
    logdir = Path(tempfile.mkdtemp())

    # Act
    logger_instance.logdir = logdir
    logger_instance._ensure_logdir_exists()

    # Assert
    assert logdir.exists()

def test_create_alternate_logdir(logger_instance):
    # Act
    logger_instance.create_alternate_logdir()

    # Assert
    assert logger_instance.logdir.is_dir()

def test_handle_logdir_creation(logger_instance):
    # Act
    logger_instance.handle_logdir_creation()

    # Assert
    assert logger_instance.logdir.is_dir()

def test_create_logger(logger_instance):
    # Act
    logger = logger_instance.create_logger()

    # Assert
    assert isinstance(logger, logging.Logger)
    assert logger.name == logger_instance.name

@pytest.mark.parametrize(
    "func, args, kwargs, expected_exception",
    [
        (lambda x: 1 / x, (0,), {}, ZeroDivisionError),
    ],
    ids=[
        "zero_division",
    ]
)
def test_log_exceptions(func, args, kwargs, expected_exception, logger_instance):
    # Arrange
    decorated_func = logger_instance.log_exceptions(func)

    # Act & Assert
    with pytest.raises(expected_exception):
        decorated_func(*args, **kwargs)

@pytest.mark.parametrize(
    "logger_name, expected_result",
    [
        ("test_logger", True),
        ("non_existent_logger", False),
    ],
    ids=[
        "existing_logger",
        "non_existent_logger",
    ]
)
def test_close_logger_handlers(logger_name, expected_result):
    # Arrange
    logger = logging.getLogger(logger_name)
    logger.addHandler(logging.StreamHandler())

    # Act
    result = close_logger_handlers(logger)

    # Assert
    assert result == expected_result

def test_remove_logger_from_root():
    # Arrange
    logger_name = "test_logger"
    logger = logging.getLogger(logger_name)
    logging.root.manager.loggerDict[logger_name] = logger

    # Act
    remove_logger_from_root(logger)

    # Assert
    assert logger_name not in logging.root.manager.loggerDict

def test_close_logger():
    # Arrange
    logger_name = "test_logger"
    logger = logging.getLogger(logger_name)
    logger.addHandler(logging.StreamHandler())
    logging.root.manager.loggerDict[logger_name] = logger

    # Act
    result = close_logger(logger)

    # Assert
    assert result
    assert logger_name not in logging.root.manager.loggerDict

def test_tqdm_to_logger():
    # Arrange
    logger = logging.getLogger("test_logger")
    tqdm_logger = TqdmToLogger(logger)

    # Act
    tqdm_logger.write("Test message")

    # Assert
    assert tqdm_logger.buf == "Test message"

    # Clean up
    tqdm_logger.flush()
