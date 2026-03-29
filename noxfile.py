"""Multi-python version testing.

Useful for validating free-threading support on local.
"""

import nox


@nox.session(
    venv_backend="uv", python=["3.10", "3.11", "3.12", "3.13", "3.13t", "3.14", "3.14t"]
)
def test(session: nox.Session) -> None:
    """Run the unit testing."""
    session.run_install(
        "uv",
        "sync",
        "--extra=tests",
        f"--python={session.virtualenv.location}",
        env={"UV_PROJECT_ENVIRONMENT": session.virtualenv.location},
    )
    session.run("pytest", "tests", "-vv")
