"""Load a bounded, versioned set of check options without executing code."""

import json
from pathlib import Path

from .core import InputError, _columns

MAX_CONTRACT_BYTES = 64 * 1024
COLUMN_OPTIONS = ("keys", "allow", "required", "decimals", "sums")
TEXT_OPTIONS = ("before_encoding", "after_encoding", "delimiter")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputError("contract contains a duplicate property")
        result[key] = value
    return result


def load_contract(path):
    """Return keyword arguments for check() from a UTF-8 JSON contract.

    Version 1 requires schema_version=1 and a nonempty keys array. Unknown,
    duplicate or incorrectly typed properties are errors, never ignored.
    Errors omit the contract's path and content.
    """
    try:
        with Path(path).open("rb") as stream:
            raw = stream.read(MAX_CONTRACT_BYTES + 1)
        if len(raw) > MAX_CONTRACT_BYTES:
            raise InputError("contract exceeds the 64 KiB limit")
        document = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        raise InputError("cannot load contract; check UTF-8 JSON, size, and unique properties") from exc
    if not isinstance(document, dict):
        raise InputError("contract must be a JSON object")
    version = document.get("schema_version")
    if type(version) is not int or version != 1:
        raise InputError("contract schema_version must be integer 1")
    allowed = set(COLUMN_OPTIONS + TEXT_OPTIONS + ("check_formulas", "schema_version"))
    if set(document) - allowed:
        raise InputError("contract contains an unknown property")
    if not document.get("keys"):
        raise InputError("contract requires a nonempty keys array")
    for name in COLUMN_OPTIONS:
        if name in document:
            if not isinstance(document[name], list):
                raise InputError("contract column options must be arrays")
            _columns(document[name], name)
    for name in TEXT_OPTIONS:
        if name in document and not isinstance(document[name], str):
            raise InputError("contract encoding and delimiter options must be strings")
    if "check_formulas" in document and type(document["check_formulas"]) is not bool:
        raise InputError("contract check_formulas must be a boolean")
    return {key: value for key, value in document.items() if key != "schema_version"}
