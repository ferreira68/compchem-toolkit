"""Nox sessions."""

import os
import shlex
import shutil
import sys
from pathlib import Path
from textwrap import dedent

import nox


try:
    from nox_poetry import Session
    from nox_poetry import session
except ImportError:
    message = f"""\
    Nox failed to import the 'nox-poetry' package.

    Please install it using the following command:

    {sys.executable} -m pip install nox-poetry"""
    raise SystemExit(dedent(message)) from None


package = "compchem_toolkit"

nox.needs_version = ">= 2021.6.6"
nox.options.sessions = (
    "poetry_lock_update",
    "pre-commit",
    "safety",
    "mypy",
    "typeguard",
    "tests",
    "xdoctest",
    "docs-build",
)


@session
def checks(session: Session) -> None:
    session.notify("poetry_lock_update")
    session.notify("pre-commit")
    session.notify("safety")
    session.notify("mypy")
    session.notify("typeguard")
    session.notify("xdoctest")


@session
def activate_virtualenv_in_precommit_hooks(session: Session) -> None:
    """Activate virtualenv in hooks installed by pre-commit.

    This function patches git hooks installed by pre-commit to activate the
    session's virtual environment. This allows pre-commit to locate hooks in
    that environment when invoked from git.

    Args:
        session: The Session object.
    """
    assert session.bin is not None  # nosec

    # Only patch hooks containing a reference to this session's bindir. Support
    # quoting rules for Python and bash, but strip the outermost quotes so we
    # can detect paths within the bindir, like <bindir>/python.
    bindirs = [
        bindir[1:-1] if bindir[0] in "'\"" else bindir
        for bindir in (repr(session.bin), shlex.quote(session.bin))
    ]

    virtualenv = session.env.get("VIRTUAL_ENV")
    if virtualenv is None:
        return

    headers = {
        # pre-commit < 2.16.0
        "python": f"""\
            import os
            os.environ["VIRTUAL_ENV"] = {virtualenv!r}
            os.environ["PATH"] = os.pathsep.join((
                {session.bin!r},
                os.environ.get("PATH", ""),
            ))
            """,
        # pre-commit >= 2.16.0
        "bash": f"""\
            VIRTUAL_ENV={shlex.quote(virtualenv)}
            PATH={shlex.quote(session.bin)}"{os.pathsep}$PATH"
            """,
        # pre-commit >= 2.17.0 on Windows forces sh shebang
        "/bin/sh": f"""\
            VIRTUAL_ENV={shlex.quote(virtualenv)}
            PATH={shlex.quote(session.bin)}"{os.pathsep}$PATH"
            """,
    }

    hookdir = Path(".git") / "hooks"
    if not hookdir.is_dir():
        return

    for hook in hookdir.iterdir():
        if hook.name.endswith(".sample") or not hook.is_file():
            continue

        if not hook.read_bytes().startswith(b"#!"):
            continue

        text = hook.read_text()

        if not any(
            Path("A") == Path("a") and bindir.lower() in text.lower() or bindir in text
            for bindir in bindirs
        ):
            continue

        lines = text.splitlines()

        for executable, header in headers.items():
            if executable in lines[0].lower():
                lines.insert(1, dedent(header))
                hook.write_text("\n".join(lines))
                break


@session(name="pre-commit")
def precommit(session: Session) -> None:
    """Lint using pre-commit."""
    args = session.posargs or [
        "run",
        "--all-files",
        "--hook-stage=manual",
        "--show-diff-on-failure",
    ]
    session.install(
        "bandit",
        "black",
        "darglint",
        "flake8",
        "flake8-bugbear",
        "flake8-docstrings",
        "flake8-rst-docstrings",
        "isort",
        "pre-commit",
        "pre-commit-hooks",
        "pyupgrade",
    )
    session.run("pre-commit", *args)
    if args and args[0] == "install":
        activate_virtualenv_in_precommit_hooks(session)


@session
def safety(session: Session) -> None:
    """Scan dependencies for insecure packages."""
    requirements = session.poetry.export_requirements()
    session.install("safety")
    session.run("safety", "check", "--full-report", f"--file={requirements}")


@session
def poetry_lock_update(session: Session) -> None:
    session.run("poetry", "lock", external=True)
    session.run(
        "poetry", "export", "--without-hashes", "-o", "requirements.txt", external=True
    )


@session
def mypy(session: Session) -> None:
    """Type-check using mypy."""
    session.install("mypy")
    session.run("mypy", "src")


@session
def tests(session: Session) -> None:
    """Run the test suite."""
    session.install(".")
    session.install("coverage[toml]", "pytest", "pygments", "mypy", "typeguard")
    try:
        session.run("coverage", "run", "--parallel", "-m", "pytest", *session.posargs)
    finally:
        if session.interactive:
            session.notify("coverage", posargs=[])


@session
def coverage(session: Session) -> None:
    """Produce the coverage report."""
    args = session.posargs or ["report"]

    session.install("coverage[toml]")

    if not session.posargs and any(Path().glob(".coverage.*")):
        session.run("coverage", "combine")

    session.run("coverage", *args)


@session
def typeguard(session: Session) -> None:
    """Runtime type checking using Typeguard."""
    session.install(".")
    session.install("pytest", "typeguard", "pygments", "mypy")
    session.run("pytest", f"--typeguard-packages={package}", *session.posargs)


@session
def xdoctest(session: Session) -> None:
    """Run examples with xdoctest."""
    if session.posargs:
        args = [package, *session.posargs]
    else:
        args = [f"--modname={package}", "--command=all"]
        if "FORCE_COLOR" in os.environ:
            args.append("--colored=1")

    session.install(".")
    session.install("xdoctest[colors]")
    session.install("mypy")
    session.run("python", "-m", "xdoctest", *args)


@session(name="docs-build")
def docs_build(session: Session) -> None:
    """Build the documentation."""
    session.install(".")
    session.install("sphinx", "sphinx-autobuild", "sphinx-theme-pd", "myst-parser")

    build_dir = Path("docs", "_build")
    if build_dir.exists():
        shutil.rmtree(build_dir)

    session.run(
        "sphinx-apidoc",
        "-f",
        "--ext-autodoc",
        "--ext-intersphinx",
        "--ext-viewcode",
        "--ext-todo",
        "-t",
        "docs/_templates",
        "-o",
        "docs/_source",
        "src",
    )
    session.run("sphinx-build", "-v", "-b", "html", "docs", "docs/_build")


@session
def view_docs(session: Session) -> None:
    """Build and serve the documentation with live reloading on file changes."""
    args = session.posargs or ["--open-browser", "docs", "docs/_build"]
    session.install(".")
    session.install(
        "sphinx", "sphinx-autobuild", "sphinx-click", "sphinx-theme-pd", "myst-parser"
    )

    build_dir = Path("docs", "_build")
    if build_dir.exists():
        shutil.rmtree(build_dir)

    session.run("sphinx-autobuild", *args)


@session(name="bump-version")
def bump_version(session: Session) -> None:
    """
    Kicks off an automated release process by creating and pushing a new tag.

    Usage:
    $ nox -s bump-version -- [major|minor|patch]
    """
    session.log(f"session.posargs: {session.posargs}")
    version: str = session.posargs.pop()

    def _get_current_version() -> str:
        result = session.run("poetry", "version", "-s", silent=True, log=False)
        return result.strip()  # type: ignore

    session.log(f"Bumping the {version!r} version")
    session.run("poetry", "version", version, external=True)

    new_version = _get_current_version()
    # session.log(f"Old version: {current_version}  ->  New version: {new_version}")

    if session.interactive():
        session.run("git", "add", "pyproject.toml", external=True)
        session.run("git", "commit", "-m", '"Automated version bump')
        session.run(
            "git",
            "tag",
            "-a",
            f"v{new_version}",
            "-m",
            f"{package} version {new_version}",
            external=True,
        )
        session.log("Pushing the new tag")
        session.run("git", "push", external=True)
        session.run("git", "push", "--tags", external=True)
