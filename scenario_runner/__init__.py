"""Shim package initializer to make `scenario_runner` importable as a package in-repo.

This allows imports such as `from scenario_runner.srunner...` to work when the
project is executed directly without an installed `scenario_runner` package.
"""

__all__ = ['srunner']

try:
    # nothing to initialize; presence of this file is enough
    pass
except Exception:
    pass
