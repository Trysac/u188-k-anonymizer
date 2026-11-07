"""Check k-anonymity of tabular data and find minimal full-domain generalisation levels.

Legal Notice and Privacy Limits:
    k-Anonymity is a mathematical property ensuring each combination of
    quasi-identifiers appears at least k times in the dataset. It does NOT protect
    against homogeneity attacks or background-knowledge attacks (which require
    l-diversity or t-closeness). k-Anonymity alone does NOT guarantee that data
    is legally anonymised under GDPR Recital 26 or equivalent data protection laws.
    This library is a technical engineering tool and does NOT constitute legal advice.
"""

from __future__ import annotations

import logging
import math
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

__all__ = [
    "ErrorCode",
    "Hierarchy",
    "KAnonError",
    "KReport",
    "Result",
    "__version__",
    "anonymize",
    "check_k",
    "numeric_range",
    "prefix_mask",
]

__version__ = "0.1.0"

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

ErrorCode = Literal[
    "invalid_value",
    "invalid_column",
    "invalid_option",
    "search_too_large",
    "input_too_large",
]

_MAX_MSG_LEN = 200


def _truncate(val: str, max_len: int = _MAX_MSG_LEN) -> str:
    if len(val) <= max_len:
        return val
    return val[: max_len - 3] + "..."


class KAnonError(Exception):
    """Base exception for all k-anonymizer errors with stable error codes."""

    def __init__(self, message: str, code: ErrorCode) -> None:
        super().__init__(message)
        self.code: ErrorCode = code
        self.message = message


@dataclass(frozen=True)
class KReport:
    """Report summarizing the k-anonymity profile of a dataset."""

    k_actual: int
    classes: int
    smallest_classes: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class Result:
    """Result of full-domain generalisation with optional suppression."""

    rows: list[dict[str, str]]
    levels: dict[str, int]
    suppressed: int
    k_actual: int


class Hierarchy:
    """Base generalisation hierarchy with bounded levels."""

    def __init__(self, max_level: int) -> None:
        if max_level < 0:
            raise KAnonError("max_level must be non-negative", code="invalid_option")
        self.max_level: int = max_level

    def apply(self, value: str, level: int) -> str:
        """Apply generalisation of `level` to `value`."""
        raise NotImplementedError


class _NumericRangeHierarchy(Hierarchy):
    def __init__(self, widths: Sequence[int]) -> None:
        if not widths:
            raise KAnonError("widths must not be empty", code="invalid_option")
        prev = 0
        for w in widths:
            if not isinstance(w, int) or w <= 0:
                raise KAnonError(
                    f"widths must be positive integers, got {w}", code="invalid_option"
                )
            if w <= prev:
                raise KAnonError(
                    f"widths must be strictly increasing: {w} <= {prev}", code="invalid_option"
                )
            prev = w
        self._widths = tuple(widths)
        # Level 0: identity
        # Level 1..len(widths): range formatting
        # Level len(widths) + 1: '*'
        super().__init__(max_level=len(widths) + 1)

    def apply(self, value: str, level: int) -> str:
        if not (0 <= level <= self.max_level):
            raise KAnonError(
                f"Level {level} out of bounds [0, {self.max_level}]", code="invalid_option"
            )
        if level == 0:
            return value
        if level == self.max_level:
            return "*"
        try:
            int_val = int(value.strip())
        except (ValueError, TypeError) as err:
            safe_v = _truncate(str(value))
            raise KAnonError(
                f"Non-integer value '{safe_v}' cannot be generalised", code="invalid_value"
            ) from err

        w = self._widths[level - 1]
        lo = math.floor(int_val / w) * w
        hi = lo + w - 1
        return f"{lo}-{hi}"


def numeric_range(widths: Sequence[int]) -> Hierarchy:
    """Construct a numeric range hierarchy with strictly increasing positive widths."""
    return _NumericRangeHierarchy(widths)


class _PrefixMaskHierarchy(Hierarchy):
    def __init__(self, length: int) -> None:
        if not isinstance(length, int) or length <= 0:
            raise KAnonError("length must be a positive integer", code="invalid_option")
        super().__init__(max_level=length)

    def apply(self, value: str, level: int) -> str:
        if not (0 <= level <= self.max_level):
            raise KAnonError(
                f"Level {level} out of bounds [0, {self.max_level}]", code="invalid_option"
            )
        if level == 0:
            return value
        v_len = len(value)
        if level >= v_len:
            return "*" * v_len
        keep_len = v_len - level
        return value[:keep_len] + ("*" * level)


def prefix_mask(length: int) -> Hierarchy:
    """Construct a prefix masking hierarchy where level i masks the last i characters."""
    return _PrefixMaskHierarchy(length)


def _validate_qi(qi: Sequence[str]) -> tuple[str, ...]:
    if not qi:
        raise KAnonError("Quasi-identifiers list cannot be empty", code="invalid_option")
    seen: set[str] = set()
    for col in qi:
        if not isinstance(col, str) or not col:
            raise KAnonError(
                "Quasi-identifier column name must be non-empty string", code="invalid_option"
            )
        if col in seen:
            raise KAnonError(
                f"Duplicate quasi-identifier: '{_truncate(col)}'", code="invalid_option"
            )
        seen.add(col)
    return tuple(qi)


def check_k(rows: Sequence[Mapping[str, str]], qi: Sequence[str]) -> KReport:
    """Calculate k-actual, equivalence classes count, and smallest equivalence class keys."""
    cols = _validate_qi(qi)
    if not rows:
        return KReport(k_actual=0, classes=0, smallest_classes=())

    counts: Counter[tuple[str, ...]] = Counter()
    for row in rows:
        tup: list[str] = []
        for col in cols:
            if col not in row:
                raise KAnonError(f"Missing column '{_truncate(col)}' in row", code="invalid_column")
            tup.append(str(row[col]))
        counts[tuple(tup)] += 1

    if not counts:
        return KReport(k_actual=0, classes=0, smallest_classes=())

    k_actual = min(counts.values())
    smallest = [
        key
        for key, count in sorted(counts.items(), key=lambda item: (item[1], item[0]))
        if count == k_actual
    ][:10]

    return KReport(
        k_actual=k_actual,
        classes=len(counts),
        smallest_classes=tuple(smallest),
    )


def anonymize(
    rows: Sequence[Mapping[str, str]],
    hierarchies: Mapping[str, Hierarchy],
    k: int,
    *,
    max_suppression: float = 0.0,
    max_nodes: int = 10_000,
) -> Result:
    """Perform full-domain generalisation with bounded suppression."""
    if k < 2:
        raise KAnonError(f"k must be an integer >= 2, got {k}", code="invalid_option")
    if not (0.0 <= max_suppression < 1.0):
        raise KAnonError(
            f"max_suppression must be in [0.0, 1.0), got {max_suppression}", code="invalid_option"
        )
    qi_cols = tuple(hierarchies.keys())
    _validate_qi(qi_cols)

    # Check that quasi-identifier columns exist in all rows
    for row in rows:
        for col in qi_cols:
            if col not in row:
                raise KAnonError(f"Missing column '{_truncate(col)}' in row", code="invalid_column")

    if len(rows) < k:
        raise KAnonError(f"Number of rows ({len(rows)}) must be >= k ({k})", code="invalid_option")
    if not hierarchies:
        raise KAnonError("hierarchies mapping cannot be empty", code="invalid_option")

    # Check lattice size
    lattice_size = 1
    for col in qi_cols:
        h = hierarchies[col]
        lattice_size *= h.max_level + 1
        if lattice_size > max_nodes:
            raise KAnonError(
                f"Lattice size exceeds max_nodes ({max_nodes})", code="search_too_large"
            )

    max_levels = [hierarchies[c].max_level for c in qi_cols]
    num_cols = len(qi_cols)

    # Generate all level vectors
    def generate_vectors(idx: int) -> list[tuple[int, ...]]:
        if idx == num_cols:
            return [()]
        sub = generate_vectors(idx + 1)
        res: list[tuple[int, ...]] = []
        for lvl in range(max_levels[idx] + 1):
            for s in sub:
                res.append((lvl, *s))
        return res

    vectors = generate_vectors(0)
    # Enumerate level vectors in order of total sum, then lexicographical order
    vectors.sort(key=lambda vec: (sum(vec), vec))

    max_allowed_suppressed = math.floor(max_suppression * len(rows))

    # Pre-cache generalized column values for each column and level to avoid repeated calls
    # cache[col_idx][level][row_idx] = transformed_str
    transformed_cache: list[list[list[str]]] = []
    for col in qi_cols:
        h = hierarchies[col]
        col_lvls: list[list[str]] = []
        for lvl in range(h.max_level + 1):
            lvl_vals: list[str] = []
            for row in rows:
                val = str(row[col])
                lvl_vals.append(h.apply(val, lvl))
            col_lvls.append(lvl_vals)
        transformed_cache.append(col_lvls)

    best_vector: tuple[int, ...] | None = None
    best_suppressed_count = 0
    best_k_actual = 0
    best_suppressed_keys: set[tuple[str, ...]] = set()

    for vec in vectors:
        # Form tuples for each row
        row_keys: list[tuple[str, ...]] = []
        for r_idx in range(len(rows)):
            key = tuple(transformed_cache[c_idx][vec[c_idx]][r_idx] for c_idx in range(num_cols))
            row_keys.append(key)

        counts: Counter[tuple[str, ...]] = Counter(row_keys)
        under_k_keys = {key for key, cnt in counts.items() if cnt < k}
        suppressed_count = sum(cnt for key, cnt in counts.items() if key in under_k_keys)

        if suppressed_count <= max_allowed_suppressed:
            # Accept the first vector satisfying the condition
            best_vector = vec
            best_suppressed_count = suppressed_count
            best_suppressed_keys = under_k_keys
            remaining_counts = [cnt for key, cnt in counts.items() if key not in under_k_keys]
            best_k_actual = min(remaining_counts) if remaining_counts else 0
            break

    if best_vector is None:
        # Top vector (all '*') produces a single class of size len(rows) >= k,
        # so this is only a fallback guard.
        raise KAnonError(
            "No valid generalisation found within suppression bounds", code="invalid_option"
        )

    # Build output rows
    output_rows: list[dict[str, str]] = []
    for r_idx, orig_row in enumerate(rows):
        key = tuple(
            transformed_cache[c_idx][best_vector[c_idx]][r_idx] for c_idx in range(num_cols)
        )
        if key in best_suppressed_keys:
            continue
        new_row = dict(orig_row)
        for c_idx, col in enumerate(qi_cols):
            new_row[col] = transformed_cache[c_idx][best_vector[c_idx]][r_idx]
        output_rows.append(new_row)

    levels_dict = {col: best_vector[idx] for idx, col in enumerate(qi_cols)}
    return Result(
        rows=output_rows,
        levels=levels_dict,
        suppressed=best_suppressed_count,
        k_actual=best_k_actual,
    )
