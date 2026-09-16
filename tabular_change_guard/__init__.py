"""Offline checks for tabular edits; no network or third-party runtime dependencies."""

from .core import InputError, check
from .contract import load_contract

__all__ = ["InputError", "check", "load_contract"]
__version__ = "0.1.0"
