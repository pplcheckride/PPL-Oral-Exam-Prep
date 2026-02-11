#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent.parent

INDEX_FILE = REPO_ROOT / "index.html"
PERFECT_JS_FILE = ROOT / "ppl_questions_250_PERFECT.js"
UNRESOLVED_REPORT = ROOT / "deep_link_unresolved.json"

AVIATION_WEATHER_PDF = "https://www.faa.gov/sites/faa.gov/files/FAA-H-8083-28A_FAA_Web.pdf"
RISK_MANAGEMENT_PDF = "https://www.faa.gov/sites/faa.gov/files/2022-06/risk_management_handbook_2A.pdf"

PHAK_CHAPTER_URLS: Dict[int, str] = {
    1: "https://www.faa.gov/regulationspolicies/handbooksmanuals/aviation/phak/chapter-1-introduction-flying",
    2: "https://www.faa.gov/regulationspolicies/handbooksmanuals/aviation/phak/chapter-2-aeronautical-decision-making",
    3: "https://www.faa.gov/regulationspolicies/handbooksmanuals/aviation/phak/chapter-3-aircraft-construction",
    4: "https://www.faa.gov/regulationspolicies/handbooksmanuals/aviation/phak/chapter-4-principles-flight",
    5: "https://www.faa.gov/regulationspolicies/handbooksmanuals/aviation/phak/chapter-5-aerodynamics-flight",
    6: "https://www.faa.gov/regulationspolicies/handbooksmanuals/aviation/phak/chapter-6-flight-controls",
    7: "https://www.faa.gov/regulationspolicies/handbooksmanuals/aviation/phak/chapter-7-aircraft-systems",
    8: "https://www.faa.gov/regulationspolicies/handbooksmanuals/aviation/phak/chapter-8-flight-instruments",
    9: "https://www.faa.gov/regulationspolicies/handbooksmanuals/aviation/phak/chapter-9-flight-manuals-and-other-documents",
    10: "https://www.faa.gov/regulationspolicies/handbooksmanuals/aviation/phak/chapter-10-weight-and-balance",
    11: "https://www.faa.gov/regulationspolicies/handbooksmanuals/aviation/phak/chapter-11-aircraft-performance",
    12: "https://www.faa.gov/regulationspolicies/handbooksmanuals/aviation/phak/chapter-12-weather-theory",
    13: "https://www.faa.gov/regulationspolicies/handbooksmanuals/aviation/phak/chapter-13-aviation-weather-services",
    14: "https://www.faa.gov/regulationspolicies/handbooksmanuals/aviation/phak/chapter-14-airport-operations",
    15: "https://www.faa.gov/regulationspolicies/handbooksmanuals/aviation/phak/chapter-15-airspace",
    16: "https://www.faa.gov/regulationspolicies/handbooksmanuals/aviation/phak/chapter-16-navigation",
    17: "https://www.faa.gov/regulationspolicies/handbooksmanuals/aviation/phak/chapter-17-aeromedical-factors",
}

GENERIC_RE = {
    "aim": re.compile(r"/aim_html/index\.html/?$", re.I),
    "phak": re.compile(r"/regulations_policies/handbooks_manuals/aviation/phak/?$", re.I),
    "afh": re.compile(r"/regulations_policies/handbooks_manuals/aviation/airplane_handbook/?$", re.I),
    "aviation_root": re.compile(r"/regulations_policies/handbooks_manuals/aviation/?$", re.I),
    "risk": re.compile(r"/regulations_policies/handbooks_manuals/aviation/risk_management_handbook/?$", re.I),
}


@dataclass
class QuestionRef:
    qid: str
    title: str
    topic: str
    reference: str
    link: str


def afh_chapter_url(chapter: int) -> str:
    chapter = max(1, min(chapter, 17))
    # FAA AFH chapter PDFs use file numbers offset by +1 from chapter number.
    file_num = chapter + 1
    return (
        "https://www.faa.gov/sites/faa.gov/files/regulations_policies/"
        f"handbooks_manuals/aviation/airplane_handbook/{file_num:02d}_afh_ch{chapter}.pdf"
    )


def weather_url(page: int) -> str:
    return f"{AVIATION_WEATHER_PDF}#page={max(1, page)}"


def risk_url(page: int) -> str:
    return f"{RISK_MANAGEMENT_PDF}#page={max(1, page)}"


def infer_chapter_from_text(text: str) -> int | None:
    m = re.search(r"chapter\s*(\d{1,2})", text, re.I)
    if not m:
        return None
    return int(m.group(1))


def aim_section_url(reference: str, topic: str, title: str) -> str:
    text = f"{reference} {topic} {title}".lower()

    if any(k in text for k in [
        "runway incursion", "taxi", "hold short", "hot spot", "airport signs",
        "airport markings", "surface movement", "non-towered", "runway marking",
        "airport lighting", "declared distances"
    ]):
        return "https://www.faa.gov/air_traffic/publications/atpubs/aim_html/chap2_section_3.html"
    if any(k in text for k in ["traffic pattern", "towered airport"]):
        return "https://www.faa.gov/air_traffic/publications/atpubs/aim_html/chap4_section_3.html"
    if any(k in text for k in ["radar services", "flight following", "vfr advisories"]):
        return "https://www.faa.gov/air_traffic/publications/atpubs/aim_html/chap4_section_1.html"
    if any(k in text for k in ["phraseology", "communications", "light gun", "comm failure"]):
        return "https://www.faa.gov/air_traffic/publications/atpubs/aim_html/chap4_section_2.html"
    if any(k in text for k in ["vor", "dme", "gps"]):
        return "https://www.faa.gov/air_traffic/publications/atpubs/aim_html/chap1_section_1.html"

    return "https://www.faa.gov/air_traffic/publications/atpubs/aim_html/chap2_section_3.html"


def phak_chapter(reference: str, topic: str, title: str) -> int:
    text = f"{reference} {topic} {title}".lower()
    chapter = infer_chapter_from_text(text)
    if chapter and chapter in PHAK_CHAPTER_URLS:
        return chapter

    if any(k in text for k in ["aeromedical", "hypoxia", "spatial disorientation"]):
        return 17
    if any(k in text for k in ["navigation", "vor", "gps", "dead reckoning", "pilotage"]):
        return 16
    if any(k in text for k in ["airspace", "mode c veil", "class b", "class c", "class d"]):
        return 15
    if any(k in text for k in ["airport ops", "airport operations", "taxi", "runway", "non-towered"]):
        return 14
    if any(k in text for k in ["metar", "taf", "weather services", "notam"]):
        return 13
    if "weather" in text:
        return 12
    if "performance" in text:
        return 11
    if any(k in text for k in ["weight", "balance", "cg"]):
        return 10
    if any(k in text for k in ["electrical", "pitot", "fuel", "engine", "avionics", "systems", "carb heat"]):
        return 7
    if "instrument" in text:
        return 8
    if any(k in text for k in ["aerodynamics", "stall", "spin", "load factor", "ground effect"]):
        return 5
    return 2


def phak_url(reference: str, topic: str, title: str) -> str:
    chapter = phak_chapter(reference, topic, title)
    return PHAK_CHAPTER_URLS.get(chapter, PHAK_CHAPTER_URLS[2])


def afh_chapter(reference: str, topic: str, title: str) -> int:
    text = f"{reference} {topic} {title}".lower()
    chapter = infer_chapter_from_text(text)
    if chapter:
        return chapter

    if any(k in text for k in ["emergency", "forced landing", "fire", "electrical fire", "ditch", "smoke"]):
        return 16
    if any(k in text for k in ["night", "runway incursion", "airport lighting"]):
        return 10
    if any(k in text for k in ["landing", "go-around", "approach", "flare"]):
        return 8
    if any(k in text for k in ["takeoff", "climb"]):
        return 6
    if any(k in text for k in ["crosswind", "traffic pattern"]):
        return 7
    if any(k in text for k in ["stall", "spin", "upset", "maneuvering speed", "coordination", "ground effect", "adverse yaw"]):
        return 5
    if any(k in text for k in ["engine", "mixture", "prop", "powerplant", "carb"]):
        return 6
    return 3


def afh_url(reference: str, topic: str, title: str) -> str:
    return afh_chapter_url(afh_chapter(reference, topic, title))


def weather_page(reference: str, topic: str, title: str) -> int:
    text = f"{reference} {topic} {title}".lower()
    if any(k in text for k in ["metar", "taf", "weather services", "prog"]):
        return 139
    if any(k in text for k in ["front", "airmass"]):
        return 41
    if "fog" in text:
        return 63
    if any(k in text for k in ["thunderstorm", "microburst", "windshear", "convective"]):
        return 93
    if any(k in text for k in ["icing", "freezing"]):
        return 111
    if any(k in text for k in ["mountain", "wave"]):
        return 121
    if any(k in text for k in ["altimeter", "pressure"]):
        return 22
    return 12


def risk_page(reference: str, topic: str, title: str) -> int:
    text = f"{reference} {topic} {title}".lower()
    if any(k in text for k in ["hazardous attitude", "attitude"]):
        return 21
    if any(k in text for k in ["personal minimum", "minimums"]):
        return 31
    if any(k in text for k in ["adm", "decision"]):
        return 13
    return 10


def parse_questions(file_path: Path) -> List[QuestionRef]:
    text = file_path.read_text(encoding="utf-8")
    pattern = re.compile(
        r'"id":\s*"(?P<id>Q\d+)".*?"title":\s*"(?P<title>[^"]*)".*?"topic":\s*"(?P<topic>[^"]*)".*?"reference":\s*"(?P<reference>[^"]*)".*?"link":\s*"(?P<link>[^"]*)"',
        re.S,
    )
    out: List[QuestionRef] = []
    for m in pattern.finditer(text):
        out.append(
            QuestionRef(
                qid=m.group("id"),
                title=m.group("title"),
                topic=m.group("topic"),
                reference=m.group("reference"),
                link=m.group("link"),
            )
        )
    return out


def normalize_segment(segment: str, q: QuestionRef) -> str:
    seg = segment.strip()
    if not seg:
        return seg

    if GENERIC_RE["aim"].search(seg):
        return aim_section_url(q.reference, q.topic, q.title)
    if GENERIC_RE["phak"].search(seg):
        return phak_url(q.reference, q.topic, q.title)
    if GENERIC_RE["afh"].search(seg):
        return afh_url(q.reference, q.topic, q.title)
    if GENERIC_RE["risk"].search(seg):
        return risk_url(risk_page(q.reference, q.topic, q.title))
    if GENERIC_RE["aviation_root"].search(seg):
        text = f"{q.reference} {q.topic} {q.title}".lower()
        if "weather" in text:
            return weather_url(weather_page(q.reference, q.topic, q.title))
        return risk_url(risk_page(q.reference, q.topic, q.title))
    return seg


def normalize_link(link: str, q: QuestionRef) -> str:
    segments = [normalize_segment(seg.strip(), q) for seg in link.split("|")]
    return " | ".join(segments)


def replace_links_in_text(text: str, new_links_by_id: Dict[str, str]) -> Tuple[str, int]:
    pattern = re.compile(r'("id":\s*"(?P<id>Q\d+)".*?"link":\s*")(?P<link>[^"]*)(")', re.S)
    updates = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal updates
        qid = match.group("id")
        old = match.group("link")
        new = new_links_by_id.get(qid, old)
        if old != new:
            updates += 1
        return f'{match.group(1)}{new}{match.group(4)}'

    return pattern.sub(repl, text), updates


def process_file(path: Path) -> Dict[str, object]:
    raw = path.read_text(encoding="utf-8")
    questions = parse_questions(path)
    if len(questions) != 250:
        raise SystemExit(f"{path}: expected 250 questions, found {len(questions)}")

    new_links_by_id: Dict[str, str] = {}
    unresolved: List[Dict[str, str]] = []
    for q in questions:
        new_link = normalize_link(q.link, q)
        new_links_by_id[q.qid] = new_link
        for segment in [s.strip() for s in new_link.split("|") if s.strip()]:
            if any(rx.search(segment) for rx in GENERIC_RE.values()):
                unresolved.append({"id": q.qid, "segment": segment, "reference": q.reference})

    updated, updates = replace_links_in_text(raw, new_links_by_id)
    if updated != raw:
        path.write_text(updated, encoding="utf-8")

    return {"file": str(path), "updates": updates, "unresolved": unresolved}


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize generic references to deep links.")
    parser.add_argument(
        "--files",
        nargs="*",
        default=[str(INDEX_FILE), str(PERFECT_JS_FILE)],
        help="Files to normalize (default: index.html and ppl_questions_250_PERFECT.js)",
    )
    args = parser.parse_args()

    reports: List[Dict[str, object]] = []
    unresolved: List[Dict[str, str]] = []
    for file_arg in args.files:
        report = process_file(Path(file_arg).resolve())
        reports.append(report)
        unresolved.extend(report["unresolved"])

    payload = {"reports": reports, "unresolved_count": len(unresolved), "unresolved": unresolved}
    UNRESOLVED_REPORT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    for report in reports:
        print(f"{report['file']}: updated {report['updates']} link fields")

    if unresolved:
        print(f"Unresolved generic links: {len(unresolved)} (see {UNRESOLVED_REPORT})")
        return 1

    print(f"All links normalized successfully. Report: {UNRESOLVED_REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
