"""Unit tests for trysac-k-anonymizer exercising the public API and edge cases."""

from __future__ import annotations

import io
import os
from typing import Any

import pytest

from k_anonymizer import (
    Hierarchy,
    KAnonError,
    anonymize,
    check_k,
    numeric_range,
    prefix_mask,
)
from k_anonymizer.__main__ import MAX_CLI_FILE_SIZE, main


# Acceptance test rows fixtures
@pytest.fixture
def sample_rows_5() -> list[dict[str, str]]:
    return [
        {"name": "Alice", "age": "34", "zip": "28013"},
        {"name": "Bob", "age": "36", "zip": "28014"},
        {"name": "Charlie", "age": "38", "zip": "28015"},
        {"name": "David", "age": "52", "zip": "28100"},
        {"name": "Eve", "age": "55", "zip": "28101"},
    ]


def test_acceptance_item_1_check_k_and_empty() -> None:
    # check_k(rows, ['age', 'zip']).k_actual == 1 for rows with ages '34', '36', '38', '52', '55'
    # and zips '28013', '28014', '28015', '28100', '28101', and check_k([], ['age']).k_actual == 0
    rows = [
        {"age": "34", "zip": "28013"},
        {"age": "36", "zip": "28014"},
        {"age": "38", "zip": "28015"},
        {"age": "52", "zip": "28100"},
        {"age": "55", "zip": "28101"},
    ]
    report = check_k(rows, ["age", "zip"])
    assert report.k_actual == 1
    assert report.classes == 5
    assert len(report.smallest_classes) == 5

    empty_report = check_k([], ["age"])
    assert empty_report.k_actual == 0
    assert empty_report.classes == 0
    assert empty_report.smallest_classes == ()


def test_acceptance_item_2_hierarchies() -> None:
    # numeric_range([10, 20]) maps '34' to '34' at level 0, '30-39' at level 1,
    # '20-39' at level 2 and '*' at level 3; prefix_mask(5) maps '28013' to '2801*' at level 1
    # and '280**' at level 2
    nr = numeric_range([10, 20])
    assert nr.apply("34", 0) == "34"
    assert nr.apply("34", 1) == "30-39"
    assert nr.apply("34", 2) == "20-39"
    assert nr.apply("34", 3) == "*"

    pm = prefix_mask(5)
    assert pm.apply("28013", 0) == "28013"
    assert pm.apply("28013", 1) == "2801*"
    assert pm.apply("28013", 2) == "280**"
    assert pm.apply("28013", 5) == "*****"


def test_acceptance_item_3_anonymize_rows5(sample_rows_5: list[dict[str, str]]) -> None:
    # anonymize(rows5, {'age': numeric_range([10, 20]), 'zip': prefix_mask(5)},
    #           k=2, max_suppression=0.0) returns levels {'age': 1, 'zip': 1},
    # suppressed == 0 and rows whose age values are '30-39' or '50-59'
    # and zip values '2801*' or '2810*'
    res = anonymize(
        sample_rows_5,
        {"age": numeric_range([10, 20]), "zip": prefix_mask(5)},
        k=2,
        max_suppression=0.0,
    )
    assert res.levels == {"age": 1, "zip": 1}
    assert res.suppressed == 0
    assert res.k_actual >= 2
    for r in res.rows:
        assert r["age"] in ("30-39", "50-59")
        assert r["zip"] in ("2801*", "2810*")


def test_acceptance_item_4_sixth_row_suppression(sample_rows_5: list[dict[str, str]]) -> None:
    # Adding a sixth row age '70' zip '29000', max_suppression=0.0 returns
    # levels {'age': 3, 'zip': 4}, while max_suppression=0.2 returns levels {'age': 1, 'zip': 1}
    # with suppressed == 1 and five output rows
    rows6 = [*sample_rows_5, {"name": "Frank", "age": "70", "zip": "29000"}]
    hierarchies = {"age": numeric_range([10, 20]), "zip": prefix_mask(5)}

    res_no_supp = anonymize(rows6, hierarchies, k=2, max_suppression=0.0)
    assert res_no_supp.levels == {"age": 3, "zip": 4}
    assert res_no_supp.suppressed == 0
    assert len(res_no_supp.rows) == 6

    res_supp = anonymize(rows6, hierarchies, k=2, max_suppression=0.2)
    assert res_supp.levels == {"age": 1, "zip": 1}
    assert res_supp.suppressed == 1
    assert len(res_supp.rows) == 5


def test_acceptance_item_5_tie_breaking_and_unaffected_columns() -> None:
    # Among equal level sums the lexicographically smallest level tuple in quasi-identifier order
    # wins, and a non-quasi-identifier column 'name' keeps every value unchanged.
    rows = [
        {"name": "Alice", "col1": "10", "col2": "10"},
        {"name": "Bob", "col1": "10", "col2": "20"},
        {"name": "Charlie", "col1": "20", "col2": "10"},
        {"name": "David", "col1": "20", "col2": "20"},
    ]
    h1 = prefix_mask(2)
    h2 = prefix_mask(2)
    res = anonymize(rows, {"col1": h1, "col2": h2}, k=2, max_suppression=0.0)
    for r, orig in zip(res.rows, rows, strict=True):
        assert r["name"] == orig["name"]

    # Test tie-breaking explicitly between equal sum tuples:
    # At (0, 1): x='91', y='5*'; x='91', y='5*'; x='92', y='5*'; x='92', y='5*' -> two groups of 2!
    # At (1, 0): x='9*', y='51'; x='9*', y='52'; x='9*', y='51'; x='9*', y='52' -> two groups of 2!
    # Both have sum = 1. Lexicographically (0, 1) < (1, 0).
    rows_both_work = [
        {"name": "1", "x": "91", "y": "51"},
        {"name": "2", "x": "91", "y": "52"},
        {"name": "3", "x": "92", "y": "51"},
        {"name": "4", "x": "92", "y": "52"},
    ]
    res_both = anonymize(rows_both_work, {"x": prefix_mask(2), "y": prefix_mask(2)}, k=2)
    assert res_both.levels == {"x": 0, "y": 1}
    for r, orig in zip(res_both.rows, rows_both_work, strict=True):
        assert r["name"] == orig["name"]


def test_acceptance_item_6_errors() -> None:
    # A non-integer age 'n/a' at level >= 1 raises KAnonError with code 'invalid_value';
    # a missing column raises code 'invalid_column';
    # k=1 raises code 'invalid_option';
    # a lattice larger than 10_000 nodes raises code 'search_too_large'
    nr = numeric_range([10])
    # level 0 identity returns string
    assert nr.apply("n/a", 0) == "n/a"
    with pytest.raises(KAnonError) as exc_info:
        nr.apply("n/a", 1)
    assert exc_info.value.code == "invalid_value"

    # missing column in check_k
    with pytest.raises(KAnonError) as exc_col:
        check_k([{"age": "30"}], ["age", "zip"])
    assert exc_col.value.code == "invalid_column"

    # missing column in anonymize
    with pytest.raises(KAnonError) as exc_col_anon:
        anonymize([{"age": "30"}], {"age": nr, "zip": prefix_mask(2)}, k=2)
    assert exc_col_anon.value.code == "invalid_column"

    # k=1 raises invalid_option
    with pytest.raises(KAnonError) as exc_k:
        anonymize([{"age": "30"}, {"age": "30"}], {"age": nr}, k=1)
    assert exc_k.value.code == "invalid_option"

    # lattice larger than 10_000 nodes
    # prefix_mask(100) has max_level 100, so 101 levels
    # 101 * 101 = 10,201 > 10,000
    with pytest.raises(KAnonError) as exc_lattice:
        anonymize(
            [{"a": "1", "b": "2"}, {"a": "1", "b": "2"}],
            {"a": prefix_mask(100), "b": prefix_mask(100)},
            k=2,
            max_nodes=10_000,
        )
    assert exc_lattice.value.code == "search_too_large"


def test_acceptance_item_7_cli(tmp_path: Any) -> None:
    # CLI: main(['check', 'data.csv', '--qi', 'age,zip', '--k', '2']) prints 'k=1' and returns 1,
    # returns 0 when k_actual >= 2, and
    # main(['anonymize', 'data.csv', '--qi', 'age=range:10,20',
    #       '--qi', 'zip=mask:5', '--k', '2', '-o', 'out.csv'])
    # writes the CSV and returns 0
    data_file = tmp_path / "data.csv"
    data_file.write_text(
        "name,age,zip\n"
        "Alice,34,28013\nBob,36,28014\nCharlie,38,28015\nDavid,52,28100\nEve,55,28101\n",
        encoding="utf-8",
    )
    out_file = tmp_path / "out.csv"

    # check with k=2: k_actual is 1, so exits 1 and prints k=1
    stdout_capture = io.StringIO()
    import sys

    orig_stdout = sys.stdout
    try:
        sys.stdout = stdout_capture
        code1 = main(["check", str(data_file), "--qi", "age,zip", "--k", "2"])
    finally:
        sys.stdout = orig_stdout
    assert code1 == 1
    assert "k=1" in stdout_capture.getvalue()

    # check with k=1: exits 0
    code_pass = main(["check", str(data_file), "--qi", "age,zip", "--k", "1"])
    assert code_pass == 0

    # anonymize command
    code_anon = main(
        [
            "anonymize",
            str(data_file),
            "--qi",
            "age=range:10,20",
            "--qi",
            "zip=mask:5",
            "--k",
            "2",
            "-o",
            str(out_file),
        ]
    )
    assert code_anon == 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "30-39" in content or "50-59" in content
    assert "2801*" in content or "2810*" in content


def test_numeric_range_validation() -> None:
    with pytest.raises(KAnonError) as exc:
        numeric_range([])
    assert exc.value.code == "invalid_option"

    with pytest.raises(KAnonError) as exc:
        numeric_range([0, 10])
    assert exc.value.code == "invalid_option"

    with pytest.raises(KAnonError) as exc:
        numeric_range([10, 5])
    assert exc.value.code == "invalid_option"

    with pytest.raises(KAnonError) as exc:
        numeric_range([10, 10])
    assert exc.value.code == "invalid_option"

    nr = numeric_range([10, 20])
    with pytest.raises(KAnonError) as exc:
        nr.apply("30", -1)
    assert exc.value.code == "invalid_option"

    with pytest.raises(KAnonError) as exc:
        nr.apply("30", 4)
    assert exc.value.code == "invalid_option"

    # negative numbers
    assert nr.apply("-15", 1) == "-20--11"


def test_prefix_mask_validation() -> None:
    with pytest.raises(KAnonError) as exc:
        prefix_mask(0)
    assert exc.value.code == "invalid_option"

    pm = prefix_mask(3)
    with pytest.raises(KAnonError) as exc:
        pm.apply("abc", -1)
    assert exc.value.code == "invalid_option"

    with pytest.raises(KAnonError) as exc:
        pm.apply("abc", 4)
    assert exc.value.code == "invalid_option"

    # value shorter than level
    assert pm.apply("a", 2) == "*"


def test_anonymize_options_and_edge_cases() -> None:
    nr = numeric_range([10])
    # max_suppression out of bounds
    with pytest.raises(KAnonError) as exc:
        anonymize([{"age": "10"}, {"age": "20"}], {"age": nr}, k=2, max_suppression=1.0)
    assert exc.value.code == "invalid_option"

    with pytest.raises(KAnonError) as exc:
        anonymize([{"age": "10"}, {"age": "20"}], {"age": nr}, k=2, max_suppression=-0.1)
    assert exc.value.code == "invalid_option"

    # fewer rows than k
    with pytest.raises(KAnonError) as exc:
        anonymize([{"age": "10"}], {"age": nr}, k=2)
    assert exc.value.code == "invalid_option"

    # empty hierarchies
    with pytest.raises(KAnonError) as exc:
        anonymize([{"age": "10"}, {"age": "20"}], {}, k=2)
    assert exc.value.code == "invalid_option"

    # single QI column
    single_res = anonymize(
        [{"age": "12"}, {"age": "18"}, {"age": "25"}],
        {"age": numeric_range([10])},
        k=2,
        max_suppression=0.4,
    )
    assert single_res.levels == {"age": 1}
    assert single_res.suppressed == 1
    assert len(single_res.rows) == 2

    # empty string values and duplicate rows
    dup_rows = [
        {"name": "", "age": "0"},
        {"name": "", "age": "0"},
    ]
    dup_res = anonymize(dup_rows, {"age": numeric_range([10])}, k=2)
    assert dup_res.levels == {"age": 0}
    assert dup_res.suppressed == 0
    assert len(dup_res.rows) == 2

    # unicode values
    uni_rows = [
        {"city": "München", "code": "1"},
        {"city": "München", "code": "1"},
    ]
    uni_res = anonymize(uni_rows, {"city": prefix_mask(3)}, k=2)
    assert uni_res.levels == {"city": 0}


def test_hierarchy_abstract() -> None:
    h = Hierarchy(max_level=2)
    with pytest.raises(NotImplementedError):
        h.apply("val", 1)

    with pytest.raises(KAnonError):
        Hierarchy(max_level=-1)


def test_check_k_validation() -> None:
    with pytest.raises(KAnonError) as exc:
        check_k([{"a": "1"}], [])
    assert exc.value.code == "invalid_option"

    with pytest.raises(KAnonError) as exc:
        check_k([{"a": "1"}], ["a", "a"])
    assert exc.value.code == "invalid_option"

    with pytest.raises(KAnonError) as exc:
        check_k([{"a": "1"}], [""])
    assert exc.value.code == "invalid_option"


def test_cli_errors_and_stdout(tmp_path: Any, monkeypatch: Any) -> None:
    # No args
    assert main([]) == 2

    # Invalid spec in anonymize
    assert main(["anonymize", "fake.csv", "--qi", "badspec", "--k", "2"]) == 2
    assert main(["anonymize", "fake.csv", "--qi", "=range:10", "--k", "2"]) == 2
    assert main(["anonymize", "fake.csv", "--qi", "col=unknown:10", "--k", "2"]) == 2
    assert main(["anonymize", "fake.csv", "--qi", "col=range", "--k", "2"]) == 2

    # Missing file
    assert main(["check", "non_existent_file.csv", "--qi", "col", "--k", "2"]) == 2

    # Oversized file
    large_file = tmp_path / "large.csv"
    large_file.write_text("col\nval\n", encoding="utf-8")
    monkeypatch.setattr(os.path, "getsize", lambda _: MAX_CLI_FILE_SIZE + 10)
    stderr_cap = io.StringIO()
    monkeypatch.setattr("sys.stderr", stderr_cap)
    ret = main(["check", str(large_file), "--qi", "col", "--k", "2"])
    assert ret == 2
    assert "input_too_large" in stderr_cap.getvalue()
    monkeypatch.undo()

    # Output to stdout
    small_file = tmp_path / "small.csv"
    small_file.write_text("zip\n28013\n28014\n", encoding="utf-8")
    stdout_cap = io.StringIO()
    monkeypatch.setattr("sys.stdout", stdout_cap)
    ret_stdout = main(
        [
            "anonymize",
            str(small_file),
            "--qi",
            "zip=mask:2",
            "--k",
            "2",
        ]
    )
    assert ret_stdout == 0
    assert "2801*" in stdout_cap.getvalue()

    # CSV decoding error simulation
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_bytes(b"\xff\xfe\x00\x00invalid")
    assert main(["check", str(bad_csv), "--qi", "col", "--k", "2"]) == 2
