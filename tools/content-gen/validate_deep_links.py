#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent.parent

INDEX_FILE = REPO_ROOT / "index.html"
PERFECT_JS_FILE = ROOT / "ppl_questions_250_PERFECT.js"
REPORT_FILE = ROOT / "deep_link_validation_report.json"

GENERIC_PATTERNS = [
    re.compile(r"/aim_html/index\.html/?$", re.I),
    re.compile(r"/regulations_policies/handbooks_manuals/aviation/phak/?$", re.I),
    re.compile(r"/regulations_policies/handbooks_manuals/aviation/airplane_handbook/?$", re.I),
    re.compile(r"/regulations_policies/handbooks_manuals/aviation/risk_management_handbook/?$", re.I),
    re.compile(r"/regulations_policies/handbooks_manuals/aviation/?$", re.I),
]


def extract_questions(text: str) -> List[Dict[str, str]]:
    pattern = re.compile(
        r'"id":\s*"(?P<id>Q\d+)".*?"reference":\s*"(?P<reference>[^"]*)".*?"link":\s*"(?P<link>[^"]*)"',
        re.S,
    )
    out: List[Dict[str, str]] = []
    for match in pattern.finditer(text):
        out.append(
            {
                "id": match.group("id"),
                "reference": match.group("reference"),
                "link": match.group("link"),
            }
        )
    return out


def validate_file(path: Path) -> Dict[str, object]:
    text = path.read_text(encoding="utf-8")
    questions = extract_questions(text)
    if len(questions) != 250:
        raise SystemExit(f"{path}: expected 250 questions, found {len(questions)}")

    failures: List[Dict[str, str]] = []
    for q in questions:
        for segment in [s.strip() for s in q["link"].split("|") if s.strip()]:
            if any(rx.search(segment) for rx in GENERIC_PATTERNS):
                failures.append(
                    {
                        "id": q["id"],
                        "reference": q["reference"],
                        "segment": segment,
                    }
                )

    return {
        "file": str(path),
        "question_count": len(questions),
        "failure_count": len(failures),
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate that all link segments are deep links.")
    parser.add_argument(
        "--files",
        nargs="*",
        default=[str(INDEX_FILE), str(PERFECT_JS_FILE)],
        help="Files to validate (default: index.html and ppl_questions_250_PERFECT.js)",
    )
    args = parser.parse_args()

    reports: List[Dict[str, object]] = []
    total_failures = 0
    for file_arg in args.files:
        report = validate_file(Path(file_arg).resolve())
        reports.append(report)
        total_failures += int(report["failure_count"])

    payload = {"reports": reports, "total_failures": total_failures}
    REPORT_FILE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    for report in reports:
        print(
            f"{report['file']}: {report['question_count']} questions checked, "
            f"{report['failure_count']} generic segments found"
        )

    if total_failures:
        print(f"Validation failed with {total_failures} generic segments. See {REPORT_FILE}")
        return 1

    print(f"Validation passed. Report: {REPORT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
