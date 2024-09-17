#  Copyright © 2024 Antonio M. Ferreira, Ph.D.
#
#  Project       : compchem-toolkit
#  File          : logger.py
#  Last Modified : 9/13/2024
#
#  This software is covered by the MIT License (see LICENSE file for details).
"""This module defines a custom logger for use across the entire module.  It is built
   on the standard python logging module, but provides greater flexibility for logging
   to both console and file targets.
"""
# TODO: Add support for AWS-based logging
import functools
import io
import logging
import logging.config
import pathlib
import platform
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Dict
from typing import Optional
from typing import TypeVar
from typing import Union
from typing import cast

from compchem_toolkit.utils.paths import PathSpec
from compchem_toolkit.utils.paths import set_pathspec


# pylint: disable=C0103
FuncType = TypeVar("FuncType", bound=Callable[..., Any])


class CompChemLogger:
    # pylint: disable=R0902
    """
    Base class for CompChemToolkit logger objects.

    Keyword Args:
        name (str): Name for the logger.
        console (int): Logging level for console stream; usually one of logging.DEBUG, logging.INFO, logging.WARNING,
            or logging.ERROR. None (default) suppresses console logging.
        file (int): Same function as console above, but for file stream. Default is to log to a file with the name
            pathlib.Path(__file__).stem.with_suffix('.log').
        logdir (str): The directory into which the log file will be written.
        fname (str): A filename (with optional path) to which logging will be sent. If both `logdir` and `fname` are
            specified, they will be concatenated.
        propagate (bool): Whether logging messages should be passed up the logging tree.
    """
    propagate: bool = False

    KNOWN_KEYWORDS = ["name", "console", "file", "logdir", "fname", "propagate"]
    DEFAULT_FNAME = "compchem_toolkit.log"
    OS_LOG_DIRS = {
        "Darwin": "~/Library/Logs/CompChemToolkit",
        "Linux": "/var/log/CompChemToolkit",
        "Windows": "C:\\Windows\\System32\\winevt\\Logs",  # Add a default for Windows if needed
    }

    def __init__(self, **kwargs: Any) -> None:
        """
        Initializes the logger configuration.

        Args:
            **kwargs: Arbitrary keyword arguments to configure the logger.
        """
        self.validate_keywords(kwargs)
        self.set_defaults(kwargs)
        self.setup_logging_path(kwargs)
        self.logger = logging.getLogger(self.name)

    def validate_keywords(self, kwargs: Dict[str, Any]) -> None:
        """
        Validates the given keywords against a set of known keywords.

        Args:
            kwargs (dict): A dictionary of keywords to validate.

        Raises:
            KeyError: If a keyword in `kwargs` is not recognized.
        """
        for key in kwargs:
            if key not in self.KNOWN_KEYWORDS:
                raise KeyError(f"Unknown keyword for logger initialization: '{key}'")

    def set_defaults(self, kwargs: Dict[str, Any]) -> None:
        """
        Sets default values for the logger attributes based on the provided keywords.

        Args:
            kwargs (dict): A dictionary containing keyword arguments to set logger attributes.
        """
        self.name = kwargs.get("name", "CompChemToolkit")
        self.console = kwargs.get("console", None)
        self.log_level_console = kwargs.get("log_level_console", logging.INFO)
        self.file = kwargs.get("file", logging.WARNING)
        self.logdir = kwargs.get(
            "logdir", self.OS_LOG_DIRS.get(platform.system(), Path.cwd())
        )
        self.fname = kwargs.get("fname", self.DEFAULT_FNAME)
        self.log_level_file = kwargs.get("log_level_file", logging.DEBUG)
        self.propagate = kwargs.get("propagate", True)
        self.logfile = set_pathspec(self.logdir).joinpath(self.fname)

    def _validate_fname(self, fname: PathSpec) -> pathlib.Path:
        """
        Validates the log file name.

        Args:
            fname (PathSpec): The log file name.

        Returns:
            bool: True if the filename is valid, False otherwise.

        Raises:
            ValueError: If `fname` is not an instance of `str` or `Path`.
        """
        if not isinstance(fname, (str, Path)):
            raise ValueError(
                f"`fname` should be of type `str` or `Path`, not {type(fname)}."
            )
        return set_pathspec(fname)

    def setup_logging_path(self, kwargs: Dict[str, Any]) -> None:
        """
        Sets up the logging path based on provided or default configurations.

        Args:
            kwargs (dict): Keyword arguments that may contain configurations for the logger, specifically:
                - `logdir`: Directory for logging. If not provided, defaults based on the operating system.
        """
        logdir = kwargs.get("logdir", tempfile.gettempdir())
        fname = kwargs.get("fname", "compchem_toolkit.log")
        self.logfile = set_pathspec(Path(logdir, fname))

        default_log_dir = self.OS_LOG_DIRS.get(platform.system(), Path.cwd())
        self.logdir = self._expand_user_path(kwargs.get("logdir", default_log_dir))
        self.logdir = set_pathspec(self.logdir)
        self._ensure_logdir_exists()

        self.fname = self._validate_fname(self.fname)
        self.fpath = set_pathspec(self.logdir.joinpath(self.fname.name))

    def _expand_user_path(self, path: str) -> Path:
        """
        Expands the tilde to the user's home directory.

        Args:
            path (str): The path to expand.

        Returns:
            Path: The expanded path.
        """
        return set_pathspec(Path(path).expanduser())

    def _ensure_logdir_exists(self) -> None:
        """Ensures that the log directory exists, creating it if necessary."""
        try:
            self.logdir = set_pathspec(self.logdir)
            self.logdir.mkdir(parents=True)
        except FileExistsError:
            logging.warning(f"The directory {self.logdir} already exists.")
        except PermissionError:
            logging.error(
                f"Permission denied: Unable to create directory {self.logdir}."
            )
            self.create_alternate_logdir()
        except OSError as err:
            logging.error(f"OSError occurred while creating {self.logdir}: {err}")

    def create_alternate_logdir(self) -> None:
        """
        Creates an alternate logging directory in the system's temporary directory.

        This method sets the logging directory to a temporary directory if the original
        logging directory cannot be created. If creating the temporary directory fails,
        it falls back to using the current working directory.
        """
        try:
            # Attempt to create a temporary directory
            exception_logdir = set_pathspec(tempfile.mkdtemp(dir=tempfile.gettempdir()))

            # Verify that the created path is indeed a directory
            if not exception_logdir.is_dir():
                raise OSError(f"Created path {exception_logdir} is not a directory.")

            logging.info(f"Using alternate logging directory: {exception_logdir}")
            self.logdir = exception_logdir

        except Exception as err:
            logging.error(
                f"Failed to create an alternate logging directory: {err}. Falling back to current working directory."
            )

            # Use the current working directory as a fallback
            self.logdir = set_pathspec(Path.cwd())
            logging.info(f"Using current working directory for logging: {self.logdir}")

    def handle_logdir_creation(self) -> None:
        """
        Attempts to create the logging directory.

        If the creation of the specified logging directory (`self.logdir`) fails for any reason,
        this method will create a temporary directory and set it as the logging directory.
        Both the failure reason and the path to the alternate logging directory will be printed.

        Attributes Modified:
            logdir (Path): If the directory creation fails, this is set to the path of the alternate logging directory.

        Example::

            >>> logger_obj = CompChemLogger()
            >>> logger_obj.handle_logdir_creation()

        Note:
            This method is typically called internally by `setup_logging_path` when the specified logging directory
            doesn't exist. It's not usually called directly.
        """
        # pylint: disable=W0718
        self.logdir = set_pathspec(self.logdir)
        self._ensure_logdir_exists()

    def create_logger(self, config: Optional[Dict[str, Any]] = None) -> logging.Logger:
        """
        Create a logger and return the Logger object.

        By default, logging is only done to a file.  The options are fully configurable through optional keyword
            arguments (**kwargs) or a custom configuration (if provided).

        Args:
            config (Optional): A custom configuration dictionary to modify the default configuration.

        Keyword Args:
            name: Name of the logger
            fname: The file name to which the log output will be written.
            logdir: The directory to contain the log file.
            log_level_console: The logging level for console output.
            log_level_file: The logging level for file output.

        Returns:
            logger: the configured logging object
        """
        # pylint: disable=no-member
        #
        # Check if the logger already exists
        existing_logger = logging.getLogger(self.name)
        if existing_logger.hasHandlers():
            print(f"Using existing logger: '{self.name}'")
            return existing_logger

        # Default logger configuration
        logger_config: Dict[str, Any] = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "{asctime} [{name}:{lineno}] {levelname}: {message}",
                    "style": "{",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
                "concise": {"format": "{levelname}: [{name}] {message}", "style": "{"},
            },
            "loggers": {
                self.name: {
                    "handlers": (
                        ["file"]
                        if (self.log_level_console is None)
                        else ["console", "file"]
                    ),
                    "propagate": True,
                }
            },
        }

        handlers = {}
        handlers_list = []
        if self.log_level_console is not None:
            handlers["console"] = {
                "level": self.log_level_console,
                "class": "logging.StreamHandler",
                "formatter": "concise",
            }
            handlers_list.append("console")
            print(f"Console logging enabled for '{self.name}'")

        if self.log_level_file is not None:
            handlers["file"] = {
                "level": self.log_level_file,
                "class": "logging.FileHandler",
                "filename": str(self.fpath),
                "formatter": "default",
            }
            handlers_list.append("file")
            print(f"Logger '{self.name}' logging to file {self.fpath}", file=sys.stderr)

        if handlers:
            logger_config["handlers"] = handlers
        logger_config["loggers"][self.name]["handlers"] = handlers_list

        # Apply a custom logger configuration if provided
        if config:
            for key, value in config.items():
                logger_config[key].update(value)

        # Set the logger configuration
        logging.config.dictConfig(logger_config)

        # Initiate the logger
        # Check if the parent exists
        parent_logger = None
        logger_name_parts = self.name.split(".")

        # Ensure the top-level logger is 'compchem_toolkit'
        logger_root_name = "compchem_toolkit"
        if logger_name_parts[0] != logger_root_name:
            logger_name_parts.insert(0, logger_root_name)

        if len(logger_name_parts) > 1:
            parent_name = ".".join(logger_name_parts[:-1])
            if parent_name in logging.root.manager.loggerDict.keys():
                parent_logger = logging.getLogger(parent_name)

        if parent_logger is not None:
            self.logger = parent_logger.getChild(logger_name_parts[-1])
        else:
            self.logger = logging.getLogger(self.name)
        self.logger.propagate = self.propagate

        return self.logger

    def log_exceptions(
        self: "CompChemLogger", func: Callable[..., Any]
    ) -> Callable[..., Any]:
        """
        A decorator to log exceptions that occur within the decorated function.
        This decorator wraps the target function. If an exception is raised within the function,
        it logs the exception message and the full traceback using the root logger, and then re-raises the exception.
        Args:
            func (Callable): The function to be wrapped.
        Returns:
            Callable: The wrapped function.
        Note:
            This decorator is typically used to wrap functions where exceptions are expected and need to be
            logged for debugging or monitoring purposes.
        """

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as err:
                self.logger.error(
                    "Exception occurred in %s: %s", func.__name__, str(err)
                )
                self.logger.error(traceback.format_exc())
                raise

        return cast(Callable[..., Any], wrapper)


def named_logging(
    _func: Optional[FuncType] = None,
    parent_logger: Optional[Union["CompChemLogger", logging.Logger]] = None,
    **kwargs: Any,
) -> Union[Callable[[FuncType], FuncType], FuncType]:
    # pylint: disable=W0613
    """Decorate a function with a self-named logger.

    Args:
        parent_logger (str): A parent logger object to which the new logger will be attached.
        **kwargs: Additional keyword arguments.

    Returns:
        logging.Logger: A decorated function with an attached logger.
    """

    def logger_decorator(func: FuncType) -> FuncType:
        @functools.wraps(func)
        def log_wrapper(*args: Any, **kwargs: Any) -> Any:
            nonlocal parent_logger

            func_name = func.__name__
            func_globals = func.__globals__

            if isinstance(parent_logger, (CompChemLogger, logging.Logger)):
                issue_warning = False
            else:
                issue_warning = True
                parent_logger = func_globals.get(
                    "logger",
                    CompChemLogger(
                        console=logging.DEBUG, file=logging.DEBUG
                    ).create_logger(),
                )

            parent_logger = cast(logging.Logger, parent_logger)
            named_logger = parent_logger.getChild(func_name)
            if issue_warning:
                named_logger.warning(
                    f"{func_name} called without a parent logger."
                    f"  Using {parent_logger.name} as parent."
                )

            # Create a list of the arguments passed to the function
            # - positional arguments
            args_passed_in_function = [repr(a) for a in args]
            # - keyword arguments
            kwargs_passed_in_function = [f"{k}={v!r}" for k, v in kwargs.items()]
            # - put them together
            formatted_arguments = ", ".join(
                args_passed_in_function + kwargs_passed_in_function
            )

            named_logger.debug(f"Begin function - Arguments: {formatted_arguments}")
            try:
                # func_globals.update(dict(logger=named_logger))
                func_globals.update({"logger": named_logger})
                value = func(*args, **kwargs)
                named_logger.debug(f"Returned: - return = {value!r}")
                # func_globals.update(dict(logger=logging.getLogger(parent_logger.name)))
                func_globals.update({"logger": logging.getLogger(parent_logger.name)})
                return value
            except Exception as err:
                named_logger.exception(
                    f"Logger '{func.__name__}' Raised an exception: {err}"
                )
                raise err

        return cast(FuncType, log_wrapper)

    return logger_decorator if _func is None else logger_decorator(_func)


def close_logger_handlers(logger: logging.Logger) -> Optional[bool]:
    try:
        if logger.handlers:
            for handler in logger.handlers:
                handler.close()
            logger.handlers = []
    except Exception as e:
        print(f"Error closing logger handlers: {str(e)}")
        return False
    return True


def remove_logger_from_root(logger: logging.Logger) -> None:
    """Remove logger from the root logger manager if it exists"""
    if logger.name in logging.root.manager.loggerDict:
        del logging.root.manager.loggerDict[logger.name]


def close_logger(logger: logging.Logger) -> bool:
    """Close all handlers on logger object and remove it from the root logger"""
    if logger is not None:
        try:
            close_logger_handlers(logger)
            remove_logger_from_root(logger)
        except KeyError:
            print(f"Logger named '{logger.name}' not found in loggerDict.")
            return False
        except Exception as err:
            print(f"Failed to close logger named '{logger.name}': {str(err)}")
            return False
    return True


class TqdmToLogger(io.StringIO):
    """
    Custom IO class to redirect the tqdm progress bar to a logger.

    This class is designed to capture the output of tqdm (typically printed to the console)
    and redirect it to a logging system. This is useful when you want to log the progress
    of operations in environments where standard output is not appropriate, such as in
    production systems or when logging to files.

    Attributes:
        buf (str): Buffer to store the current message before logging.
        logger (logging.Logger): Logger instance to which the tqdm output will be redirected.
        level (int): Logging level at which the tqdm messages will be logged.

    Example::

        >>> import logging
        >>> from tqdm import tqdm
        >>> logger = logging.getLogger(__name__)
        >>> for _ in tqdm(range(10), file=TqdmToLogger(logger)):
        ...     pass

        This will log the tqdm progress bar messages using the provided logger.

    Args:
        logger (logging.Logger): Logger instance to which the tqdm output will be redirected.
    """

    buf = ""

    def __init__(self, logger: logging.Logger) -> None:
        super().__init__()
        self.logger = logger
        self.level = logging.INFO

    def flush(self) -> None:
        if self.buf:
            self.logger.log(self.level, self.buf)
            self.buf = ""

    def write(self, buf: str) -> int:
        # self.buf = buf.strip('\r\n\t ')
        # print(f"{self.buf=}")
        self.buf = buf.strip("\r\n\t")
        return len(self.buf)
