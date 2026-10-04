#!/usr/bin/env python3
"""Read-only comparison of actual OpenRefine CSV exports against frozen input.

This checks CSV semantics only. It does not establish UI execution, archive
restoration, workspace separation, independent-user acceptance, or a customer.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import time


HEADERS = ["id", "categoria", "descricao", "observacao"]
FROZEN_SOURCE_SHA256 = "95a95c965ffa599ade2e9b065f5283d2e6c96e89a41e1b1001988b6aec73ff42"


def load_csv(path):
    raw = path.read_bytes()
    # A UTF-8 BOM is allowed; cell contents and whitespace are never normalized.
    text = raw.decode("utf-8-sig", errors="strict")
    parsed = list(csv.reader(io.StringIO(text, newline=""), strict=True))
    if not parsed or parsed[0] != HEADERS:
        raise ValueError("header must contain the four original columns in order")
    rows = parsed[1:]
    for number, row in enumerate(rows, start=2):
        if len(row) != len(HEADERS):
            raise ValueError(f"CSV record {number}: expected four cells, got {len(row)}")
        if any(not isinstance(cell, str) for cell in row):
            raise ValueError(f"CSV record {number}: non-string cell")
    return rows, {
        "path": str(path),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "rows": len(rows),
        "utf8_bom": raw.startswith(b"\xef\xbb\xbf"),
    }


def difference(actual, expected):
    if len(actual) != len(expected):
        return {"kind": "row_count", "expected": len(expected), "actual": len(actual)}
    for index, (got, wanted) in enumerate(zip(actual, expected), start=1):
        for column, (got_cell, wanted_cell) in enumerate(zip(got, wanted)):
            if got_cell != wanted_cell:
                return {
                    "kind": "cell",
                    "record": index,
                    "column": HEADERS[column],
                    "expected": wanted_cell,
                    "actual": got_cell,
                }
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "filtered", "full", "restored", "undo"):
        parser.add_argument(f"--{name}", required=True, type=Path)
    args = parser.parse_args()
    started = time.perf_counter()
    paths = {name: getattr(args, name).resolve() for name in vars(args)}
    report = {
        "passed": False,
        "files": {},
        "checks": [],
        "limits": [
            "Finite comparison of these original fictitious CSV records only.",
            "CSV values and order are compared; CSV quoting, BOM and line-ending bytes may differ.",
            "No proof of archive import, separate workspace, UI history, publishing or independent executor.",
            "No customer, payment, economic advantage or general OpenRefine correctness established.",
        ],
    }
    try:
        if len(set(paths.values())) != len(paths):
            raise ValueError("each export and source must have a distinct path")
        inputs = {}
        for name, path in paths.items():
            rows, info = load_csv(path)
            inputs[name] = rows
            report["files"][name] = info
        source = inputs["source"]
        if report["files"]["source"]["sha256"] != FROZEN_SOURCE_SHA256:
            raise ValueError("source bytes do not match the source registered before execution")
        if len(source) != 48 or [row[0] for row in source] != [f"{i:05d}" for i in range(1, 49)]:
            raise ValueError("frozen source must contain 48 ordered original string IDs")
        if any(sum(row[1] == category for row in source) != 16 for category in "ABC"):
            raise ValueError("frozen source categories must have 16 records each")
        report["checks"].append({"name": "frozen_original_source", "passed": True})
        # Derive the sole declared transformation independently from source,
        # without importing any producer implementation or trusting its report.
        trimmed = [row[:2] + [row[2].strip(" \t\r\n")] + row[3:] for row in source]
        expectations = {
            "filtered": [row for row in trimmed if row[1] == "A"],
            "full": trimmed,
            "restored": trimmed,
            "undo": source,
        }
        for name, expected in expectations.items():
            error = difference(inputs[name], expected)
            check = {"name": name, "passed": error is None, "expected_rows": len(expected)}
            if error:
                check["first_difference"] = error
            report["checks"].append(check)
        report["passed"] = all(check["passed"] for check in report["checks"])
    except (OSError, UnicodeError, csv.Error, ValueError) as error:
        report["error"] = f"{type(error).__name__}: {error}"
    report["elapsed_seconds"] = round(time.perf_counter() - started, 6)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
