#!/usr/bin/env python3
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MASTER_PATH = ROOT / "ppl_oral_master_questions.md"
REPORT_PATH = ROOT / "qc_report_ppl_oral_master.md"

EXPECTED_MIN_Q = 1
EXPECTED_MAX_Q = 250


QUESTION_RE = re.compile(r"^## QUESTION (\d+):[^\n]*\n", re.M)

REQUIRED_LABELS = [
    "**Topic:**",
    "**Airports:**",
    "**Aircraft:**",
    "**Scenario:**",
    "**MODEL ANSWER:**",
    "**Trap Reasoning:**",
    "**Why This Matters:**",
    "**Cram Mode:**",
    "**Reference:**",
    "**Link:**",
]


@dataclass(frozen=True)
class QuestionBlock:
    number: int
    title: str
    start_offset: int
    text: str


def extract_questions(text: str) -> list[QuestionBlock]:
    matches = list(QUESTION_RE.finditer(text))
    blocks: list[QuestionBlock] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end].strip("\n") + "\n"
        number = int(m.group(1))
        first_line = block.splitlines()[0]
        title = first_line.split(":", 1)[1].strip() if ":" in first_line else ""
        blocks.append(QuestionBlock(number=number, title=title, start_offset=start, text=block))
    return blocks


def md_line_to_lineno(text: str, offset: int) -> int:
    # 1-based line number
    return text.count("\n", 0, offset) + 1


def find_airports_line(block: str) -> str | None:
    for line in block.splitlines():
        if line.startswith("**Airports:**"):
            return line
    return None


def extract_prompt_line(block: str) -> str | None:
    """
    Returns the first bolded prompt-ish line after **Scenario:** and before **MODEL ANSWER:**.
    Accepts both:
      - "**Question:** ..."
      - "**...**" lines
    """
    lines = block.splitlines()
    ignore = {
        "**Topic:**",
        "**Airports:**",
        "**Aircraft:**",
        "**Scenario:**",
        "**MODEL ANSWER:**",
        "**Trap Reasoning:**",
        "**Why This Matters:**",
        "**Cram Mode:**",
        "**Reference:**",
        "**Link:**",
        "---",
    }

    try:
        scenario_i = next(i for i, l in enumerate(lines) if l.strip() == "**Scenario:**")
    except StopIteration:
        scenario_i = 0

    try:
        model_i = next(i for i, l in enumerate(lines) if l.strip() == "**MODEL ANSWER:**")
    except StopIteration:
        model_i = len(lines)

    for l in lines[scenario_i:model_i]:
        s = l.strip()
        if not s:
            continue
        if s.startswith("**Question:**"):
            return s
        if any(s.startswith(prefix) for prefix in ignore):
            continue
        if s.startswith("**") and s.endswith("**") and len(s) > 10:
            return s
    return None


def reference_is_specific(block: str) -> bool:
    # Lightweight heuristic: a specific pointer (CFR section, AIM section, chapter/section).
    m = re.search(r"^\*\*Reference:\*\*\s*(.*)$", block, flags=re.M)
    if not m:
        return False
    ref = m.group(1)
    if re.search(r"\b14\s*CFR\b", ref):
        return True
    if re.search(r"\b(61|91|67)\.\d+\b", ref):
        return True
    if re.search(r"\bAIM\s*\d+[-.]\d+", ref):
        return True
    if re.search(r"\b(Chapter|Section)\s+\d+\b", ref, flags=re.I):
        return True
    return False


def airports_use_icao_codes(block: str) -> bool:
    # Enforce: identifiers immediately before "(" are 4 chars (e.g., KAPA, CYTZ).
    line = find_airports_line(block)
    if not line:
        return True
    content = line.split("**Airports:**", 1)[1]
    codes = re.findall(r"\b([A-Z0-9]{3,4})\s*\(", content)
    if not codes:
        return True
    return all(len(c) == 4 for c in codes)


def contains_time_sensitive_foreign_med_claims(block: str) -> bool:
    # This is the only category where "correctness" can drift over time.
    if "BasicMed" not in block:
        return False
    return any(word in block for word in ["Canada", "Mexico", "Bahamas", "ICAO", "reciprocal"])


def contains_personal_minimums_presented_as_rules(block: str) -> bool:
    # Flag common phrasing that can be misread as regulatory.
    return bool(re.search(r"\b(use|add)\s+1\.5x\b|\b(one and a half)\b", block, flags=re.I))


def required_labels_missing(block: str) -> list[str]:
    missing: list[str] = []
    for lbl in REQUIRED_LABELS:
        if lbl not in block:
            missing.append(lbl)
    return missing


def main() -> int:
    text = MASTER_PATH.read_text(errors="replace")
    blocks = extract_questions(text)
    if not blocks:
        raise SystemExit(f"No questions found in {MASTER_PATH.name}")

    # Basic integrity
    numbers = [b.number for b in blocks]
    if len(set(numbers)) != len(numbers):
        raise SystemExit("Duplicate question numbers detected.")
    if min(numbers) != EXPECTED_MIN_Q or max(numbers) != EXPECTED_MAX_Q:
        raise SystemExit(f"Unexpected question range: {min(numbers)}..{max(numbers)} (expected {EXPECTED_MIN_Q}..{EXPECTED_MAX_Q})")

    flagged_count = 0
    generic_refs: list[int] = []
    non_icao: list[int] = []
    time_sensitive: list[int] = []
    personal_minimums: list[int] = []

    lines_out: list[str] = []
    lines_out.append("# QC Report: PPL Oral Master Question Bank")
    lines_out.append("")
    lines_out.append(f"Input: `{MASTER_PATH.name}`")
    lines_out.append("")
    lines_out.append("## Summary")
    lines_out.append("")
    lines_out.append(f"- Questions found: {len(blocks)} (Q{min(numbers)}–Q{max(numbers)})")
    lines_out.append("")
    lines_out.append("## Flags (Per Question)")
    lines_out.append("")
    lines_out.append("| Q# | Status | Flags |")
    lines_out.append("|---:|:------:|:------|")

    for b in sorted(blocks, key=lambda x: x.number):
        block = b.text
        flags: list[str] = []

        missing = required_labels_missing(block)
        if missing:
            flags.append("missing template fields")

        if extract_prompt_line(block) is None:
            flags.append("missing explicit prompt line")

        if not reference_is_specific(block):
            flags.append("generic reference (add section/chapter)")
            generic_refs.append(b.number)

        if not airports_use_icao_codes(block):
            flags.append("non-ICAO airport identifiers in `**Airports:**`")
            non_icao.append(b.number)

        if contains_time_sensitive_foreign_med_claims(block):
            flags.append("time-sensitive foreign rule claim (verify periodically)")
            time_sensitive.append(b.number)

        if contains_personal_minimums_presented_as_rules(block):
            flags.append("personal-minimum phrasing (ensure labeled as recommendation)")
            personal_minimums.append(b.number)

        status = "PASS" if not flags else "FLAG"
        if flags:
            flagged_count += 1
        flags_text = "; ".join(flags) if flags else ""
        lines_out.append(f"| {b.number} | {status} | {flags_text} |")

    lines_out.append("")
    lines_out.append("## Rollups")
    lines_out.append("")
    lines_out.append(f"- Flagged questions: {flagged_count}")
    lines_out.append(f"- Generic references: {len(generic_refs)}")
    lines_out.append(f"- Non-ICAO airport identifiers: {len(non_icao)} ({', '.join('Q'+str(n) for n in non_icao) if non_icao else 'none'})")
    lines_out.append(f"- Time-sensitive foreign-rule claims: {len(time_sensitive)} ({', '.join('Q'+str(n) for n in time_sensitive) if time_sensitive else 'none'})")
    lines_out.append(f"- Personal-minimum phrasing: {len(personal_minimums)} ({', '.join('Q'+str(n) for n in personal_minimums) if personal_minimums else 'none'})")
    lines_out.append("")
    lines_out.append("## Notes")
    lines_out.append("")
    lines_out.append("- This script does not validate factual correctness of aviation content; it checks structure and common trust/ambiguity risks.")
    lines_out.append("- If you want ACS-standardization, add an `**ACS:**` field per question (Task + K/R/S element), then extend this script to enforce it.")
    lines_out.append("")

    REPORT_PATH.write_text("\n".join(lines_out).rstrip() + "\n")
    print(f"Wrote {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
