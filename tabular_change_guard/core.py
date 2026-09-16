"""Read both inputs once, then compare exact strings using explicit row keys."""

import codecs
import csv
import hashlib
import io
import re
from collections import Counter
from decimal import (MAX_EMAX, MIN_EMIN, ROUND_HALF_EVEN, Context, Decimal,
                     Inexact, InvalidOperation, Overflow, localcontext)
from pathlib import Path

MAX_BYTES = 10 * 1024 * 1024
MAX_ISSUES = 1000
NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)\Z")


class InputError(ValueError):
    """Invalid configuration or an unreadable/ambiguous CSV input."""


def _read(path, encoding, delimiter, max_bytes):
    try:
        codecs.lookup(encoding)
        with Path(path).open("rb") as stream:
            raw = stream.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raise InputError("input exceeds the configured byte limit")
        text = raw.decode(encoding)
    except (OSError, UnicodeError, LookupError) as exc:
        # Do not echo a sensitive filename, byte sequence, or input value.
        raise InputError("cannot read input; check file, permissions, and encoding") from exc
    if "\x00" in text:
        raise InputError("NUL characters are not supported")
    try:
        reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
        headers = next(reader, None)
        if not headers or any(not h.strip() for h in headers):
            raise InputError("CSV must have nonempty column names")
        if len(set(headers)) != len(headers):
            raise InputError("duplicate column names are ambiguous")
        rows = []
        for row in reader:
            if len(row) != len(headers):
                raise InputError("every record must have exactly the header's column count")
            rows.append(dict(zip(headers, row)))
    except csv.Error as exc:
        raise InputError("malformed CSV or field exceeds the CSV parser limit") from exc
    return headers, rows, hashlib.sha256(raw).hexdigest()


def _columns(value, name):
    if isinstance(value, str):
        raise InputError(name + " must be a sequence of column names, not a string")
    try:
        result = tuple(value)
    except TypeError as exc:
        raise InputError(name + " must be a sequence") from exc
    if any(not isinstance(x, str) or not x.strip() for x in result):
        raise InputError(name + " contains an empty or invalid column name")
    if len(set(result)) != len(result):
        raise InputError(name + " repeats a column")
    return result


def _index(rows, keys):
    result = {}
    for record, row in enumerate(rows, 1):
        key = tuple(row[k] for k in keys)
        if any(not value.strip() for value in key):
            raise InputError("key columns must not be blank")
        if key in result:
            raise InputError("key columns must uniquely identify every record")
        result[key] = (record, row)
    return result


def _decimal(value):
    # ASCII, plain decimal notation only; NaN, Infinity and exponents are rejected.
    if not NUMBER.fullmatch(value):
        return None
    return Decimal(value)


def _total(values):
    if not values:
        return Decimal(0)
    # Enough precision for the entire exact sum, including cancellation.
    digits = max(x.adjusted() for x in values) - min(x.as_tuple().exponent for x in values)
    # Never inherit the host application's exponent limits, clamp or traps.
    # Otherwise unequal totals can both overflow to Infinity (or underflow to 0).
    context = Context(prec=max(28, digits + len(str(len(values))) + 3),
                      Emin=MIN_EMIN, Emax=MAX_EMAX, rounding=ROUND_HALF_EVEN,
                      clamp=0, flags=[], traps=[InvalidOperation, Overflow, Inexact])
    with localcontext(context):
        return sum(values, Decimal(0))


def check(before, after, *, keys, allow=(), required=(), decimals=(), sums=(),
          before_encoding="utf-8-sig", after_encoding="utf-8-sig", delimiter=",",
          check_formulas=True, max_bytes=MAX_BYTES, max_issues=MAX_ISSUES):
    """Return a JSON-compatible report. Never modify files or return cell values.

    Invalid inputs raise InputError. Violations produce ok=False. Keys must be
    unique and nonblank in BOTH inputs. Record numbers are 1-based data records,
    not physical lines. Reordering rows/columns is allowed; schema changes are not.
    """
    if not isinstance(delimiter, str) or len(delimiter) != 1 or delimiter in '\r\n\x00"':
        raise InputError("delimiter must be one character other than quote, NUL or newline")
    if type(max_bytes) is not int or max_bytes < 1:
        raise InputError("max_bytes must be a positive integer")
    if type(max_issues) is not int or max_issues < 1:
        raise InputError("max_issues must be a positive integer")
    keys = _columns(keys, "keys")
    allow = _columns(allow, "allow")
    required = _columns(required, "required")
    decimals = _columns(decimals, "decimals")
    sums = _columns(sums, "sums")
    if not keys:
        raise InputError("at least one key column is required")
    if set(keys) & set(allow):
        raise InputError("key columns cannot be editable")
    bh, br, bsha = _read(before, before_encoding, delimiter, max_bytes)
    ah, ar, asha = _read(after, after_encoding, delimiter, max_bytes)
    configured = set(keys + allow + required + decimals + sums)
    if not configured <= set(bh):
        raise InputError("a configured column is missing from the baseline")
    counts = Counter()
    issues = []

    def add(code, *, column=None, before_record=None, after_record=None):
        counts[code] += 1
        if len(issues) < max_issues:
            item = {"code": code}
            for name, value in (("column", column), ("before_record", before_record),
                                ("after_record", after_record)):
                if value is not None:
                    item[name] = value
            issues.append(item)

    def report(comparison_performed):
        return {"schema_version": 1, "ok": not counts,
                "comparison_performed": comparison_performed,
                "before": {"sha256": bsha, "records": len(br)},
                "after": {"sha256": asha, "records": len(ar)},
                "issue_count": sum(counts.values()), "counts": dict(sorted(counts.items())),
                "issues": issues, "issues_truncated": sum(counts.values()) > len(issues)}

    for column in bh:
        if column not in ah:
            add("column_removed", column=column)
    for column in ah:
        if column not in bh:
            add("column_added", column=column)
    if counts:
        return report(False)
    bi, ai = _index(br, keys), _index(ar, keys)
    protected = [h for h in bh if h not in allow and h not in keys]
    for key, (record, row) in bi.items():
        if key not in ai:
            add("row_removed", before_record=record)
            continue
        after_record, updated = ai[key]
        for column in protected:
            if row[column] != updated[column]:
                add("protected_value_changed", column=column,
                    before_record=record, after_record=after_record)
    for key, (record, _) in ai.items():
        if key not in bi:
            add("row_added", after_record=record)
    for record, row in enumerate(ar, 1):
        for column in required:
            if not row[column].strip():
                add("required_value_missing", column=column, after_record=record)
        if check_formulas:
            for column, value in row.items():
                stripped = value.lstrip()
                if stripped.startswith(("=", "+", "-", "@")) and _decimal(stripped) is None:
                    add("formula_like_value", column=column, after_record=record)
    # Validate totals in both inputs, but other decimal constraints only after edits.
    for column in dict.fromkeys(decimals + sums):
        parsed = []
        for record, row in enumerate(ar, 1):
            value = _decimal(row[column])
            if value is None:
                add("invalid_decimal", column=column, after_record=record)
            else:
                parsed.append(value)
        if column in sums:
            baseline = []
            for record, row in enumerate(br, 1):
                value = _decimal(row[column])
                if value is None:
                    add("invalid_baseline_decimal", column=column, before_record=record)
                else:
                    baseline.append(value)
            if len(parsed) == len(ar) and len(baseline) == len(br):
                if _total(baseline) != _total(parsed):
                    add("total_changed", column=column)
    return report(True)
