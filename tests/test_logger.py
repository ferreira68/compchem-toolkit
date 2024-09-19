import logging
import tempfile
from pathlib import Path
from pathlib import PurePath

import pytest
from typeguard import suppress_type_checks

from compchem_toolkit.utils.logger import CompChemLogger
from compchem_toolkit.utils.logger import TqdmToLogger
from compchem_toolkit.utils.logger import close_logger
from compchem_toolkit.utils.logger import close_logger_handlers
from compchem_toolkit.utils.logger import named_logging
from compchem_toolkit.utils.logger import remove_logger_from_root


@pytest.fixture
def logger_class():
    return CompChemLogger()


@pytest.fixture
def logger_instance():
    logger = CompChemLogger(
        name="test_logger", console=logging.DEBUG, file=logging.DEBUG
    )
    return logger.create_logger()


@pytest.fixture
def decorated_function(logger_instance):
    @named_logging(parent_logger=logger_instance)
    def sample_function(x, y=1):
        return x / y

    return sample_function


@pytest.fixture(scope="module")
def testing_logdir():
    """
    Fixture to create and clean up a scratch directory for each test module.
    The directory is deleted automatically after the module's tests complete.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def caplog(caplog):
    caplog.set_level(logging.DEBUG)
    return caplog


@pytest.mark.parametrize(
    "kwargs, expected_name, expected_console, expected_file, expected_logdir, expected_fname, expected_propagate",
    [
        (
            {"name": "TestLogger"},
            "TestLogger",
            None,
            logging.WARNING,
            Path.cwd(),
            "compchem_toolkit.log",
            True,
        ),
        (
            {"console": logging.DEBUG},
            "CompChemToolkit",
            logging.DEBUG,
            logging.WARNING,
            Path.cwd(),
            "compchem_toolkit.log",
            True,
        ),
        (
            {"file": logging.ERROR},
            "CompChemToolkit",
            None,
            logging.ERROR,
            Path.cwd(),
            "compchem_toolkit.log",
            True,
        ),
        (
            {"logdir": "/tmp/logs"},
            "CompChemToolkit",
            None,
            logging.WARNING,
            Path("/tmp/logs"),
            "compchem_toolkit.log",
            True,
        ),
        (
            {"fname": "test.log"},
            "CompChemToolkit",
            None,
            logging.WARNING,
            Path.cwd(),
            "test.log",
            True,
        ),
        (
            {"propagate": False},
            "CompChemToolkit",
            None,
            logging.WARNING,
            Path.cwd(),
            "compchem_toolkit.log",
            False,
        ),
    ],
    ids=[
        "name_only",
        "console_only",
        "file_only",
        "logdir_only",
        "fname_only",
        "propagate_only",
    ],
)
def test_compchem_logger_init(
    kwargs,
    expected_name,
    expected_console,
    expected_file,
    expected_logdir,
    expected_fname,
    expected_propagate,
):
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
    "fname, expected_exception",
    [
        (123, ValueError),
        (None, ValueError),
    ],
    ids=[
        "invalid_type_int",
        "invalid_type_none",
    ],
)
@suppress_type_checks
def test_validate_fname_invalid(fname, expected_exception, logger_class):
    # Act & Assert
    if expected_exception:
        with pytest.raises(expected_exception):
            logger_class._validate_fname(fname)
    else:
        assert logger_class._validate_fname(fname) == fname


@pytest.mark.parametrize(
    "kwargs, expected_exception",
    [
        ({"unknown_key": "value"}, KeyError),
    ],
    ids=[
        "unknown_keyword",
    ],
)
def test_compchem_logger_init_invalid_keywords(kwargs, expected_exception):
    # Act & Assert
    with pytest.raises(expected_exception):
        CompChemLogger(**kwargs)


@pytest.mark.parametrize(
    "logdir, expected_logdir",
    [
        ("~/logs", Path.home() / "logs"),
        ("/tmp/logs", Path("/tmp/logs")),
    ],
    ids=[
        "expand_user_path",
        "absolute_path",
    ],
)
def test_expand_user_path(logdir, expected_logdir, logger_class):
    # Act
    expanded_path = logger_class._expand_user_path(logdir)

    # Resolve to handle symlinks and make absolute
    expanded_path = Path(expanded_path).resolve()
    expected_logdir = Path(expected_logdir).resolve()

    # Normalize paths for cross-platform compatibility
    expanded_path = PurePath(expanded_path).relative_to(expanded_path.anchor)
    expected_logdir = PurePath(expected_logdir).relative_to(expected_logdir.anchor)

    # Assert
    assert expanded_path == expected_logdir


def test_ensure_logdir_exists(logger_class):
    # Arrange
    logdir = Path(tempfile.mkdtemp())

    # Act
    logger_class.logdir = logdir
    logger_class._ensure_logdir_exists()

    # Assert
    assert logdir.exists()


def test_create_alternate_logdir(logger_class):
    # Act
    logger_class.create_alternate_logdir()

    # Assert
    assert logger_class.logdir.is_dir()


def test_handle_logdir_creation(logger_class):
    # Act
    logger_class.handle_logdir_creation()

    # Assert
    assert logger_class.logdir.is_dir()


def test_create_logger(logger_class):
    # Act
    logger = logger_class.create_logger()

    # Assert
    assert isinstance(logger, logging.Logger)
    assert logger.name == logger_class.name


@pytest.mark.parametrize(
    "func, args, kwargs, expected_exception",
    [
        (lambda x: 1 / x, (0,), {}, ZeroDivisionError),
    ],
    ids=[
        "zero_division",
    ],
)
def test_log_exceptions(func, args, kwargs, expected_exception, logger_class, caplog):
    # Arrange
    decorated_func = logger_class.log_exceptions(func)

    # Act & Assert
    with caplog.at_level(logging.ERROR):
        with pytest.raises(expected_exception):
            decorated_func(*args, **kwargs)

    # Assert that the exception was logged
    assert "Exception occurred in" in caplog.text
    assert "division by zero" in caplog.text


@pytest.mark.parametrize(
    "logger_name, expected_result",
    [
        ("test_logger", True),
        ("non_existent_logger", True),
    ],
    ids=[
        "existing_logger",
        "non_existent_logger",
    ],
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


@pytest.mark.parametrize(
    "args, expected_output",
    [
        ((2,), 2),  # Simple division (2/1)
        ((8, 4), 2),  # Another (8/4)
    ],
    ids=[
        "simple_addition",
        "another_addition",
    ],
)
def test_named_logging_happy_path(decorated_function, args, expected_output, caplog):
    # Act
    result = decorated_function(*args)

    # Assert
    assert result == expected_output
    assert "Begin function - Arguments:" in caplog.text


@pytest.mark.parametrize(
    "args, expected_exception",
    [
        ((1, 0), ZeroDivisionError),  # Division by zero
    ],
    ids=[
        "division_by_zero",
    ],
)
def test_named_logging_error_case(decorated_function, args, expected_exception, caplog):
    # Act & Assert
    with pytest.raises(expected_exception):
        decorated_function(*args)

    # Assert that the exception was logged
    assert "Raised an exception" in caplog.text
