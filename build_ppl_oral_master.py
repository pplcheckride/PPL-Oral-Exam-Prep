import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple


ROOT = Path(__file__).resolve().parent
MASTER_PATH = ROOT / "ppl_oral_master_questions.md"
STRICT_1_50_PATH = ROOT / "questions_1_50_strict.md"


QUESTION_RE = re.compile(r"^## QUESTION (\d+):[^\n]*\n", re.M)


def extract_questions(text: str) -> Dict[int, str]:
    matches = list(QUESTION_RE.finditer(text))
    questions: Dict[int, str] = {}
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end].strip("\n") + "\n"
        num = int(m.group(1))
        questions[num] = block
    return questions


def trim_to_question_end(block: str) -> str:
    """
    Some source files contain interstitial headers (e.g., '# Questions 11-15: ...')
    inserted between question blocks. Because extraction slices until the next
    '## QUESTION', those headers can be appended to the previous question block.
    To keep blocks clean, trim everything after the last horizontal-rule line ('---').
    """
    lines = block.splitlines()
    link_idx = None
    for i, line in enumerate(lines):
        if line.startswith("**Link:**"):
            link_idx = i
            break

    if link_idx is not None:
        for j in range(link_idx + 1, len(lines)):
            if lines[j].strip() == "---":
                return "\n".join(lines[: j + 1]).strip("\n") + "\n"
            # If a top-level header starts (category/range headings), cut before it.
            if lines[j].startswith("# "):
                trimmed = "\n".join(lines[:j]).rstrip("\n")
                if not trimmed.endswith("\n---") and not trimmed.endswith("---"):
                    trimmed = trimmed.rstrip() + "\n\n---"
                return trimmed.strip("\n") + "\n"

    # Fallback: trim to last separator line
    last_sep = None
    for i, line in enumerate(lines):
        if line.strip() == "---":
            last_sep = i
    if last_sep is None:
        return block.strip("\n") + "\n"
    return "\n".join(lines[: last_sep + 1]).strip("\n") + "\n"


def normalize_why_sections(block: str) -> str:
    """
    Converts legacy headings:
      **Why Trap Fails:**, **Why It Matters:**, **Detailed Explanation:**
    into a single:
      **Why This Matters:**
    Keeps existing content (concatenated) and removes the old headings.
    """

    def _grab(b: str, section: str) -> Tuple[str, str]:
        """
        Returns (content, new_block_without_section).
        Supports content on the same line as the heading or on following lines.
        """
        pattern = re.compile(
            rf"(?:\n|^)\*\*{re.escape(section)}:\*\*\s*(?:\n)?(.*?)(?=(?:\n\*\*[\w ].+?:\*\*)|\n---\s*$|\Z)",
            re.S,
        )
        m = pattern.search(b)
        if not m:
            return "", b
        content = m.group(1).strip()
        new_block = b[: m.start()] + "\n" + b[m.end() :]
        return content, new_block

    b = block
    trap_fails, b = _grab(b, "Why Trap Fails")
    why_it_matters, b = _grab(b, "Why It Matters")
    detailed, b = _grab(b, "Detailed Explanation")

    if not (trap_fails or why_it_matters or detailed):
        return block

    combined_parts = [p for p in [trap_fails, why_it_matters, detailed] if p]
    combined = "\n\n".join(combined_parts).strip()

    # Remove any existing **Why This Matters:** to avoid duplicates
    b = re.sub(
        r"(?:\n|^)\*\*Why This Matters:\*\*\s*(?:\n)?(.*?)(?=(?:\n\*\*[\w ].+?:\*\*)|\n---\s*$|\Z)",
        "\n",
        b,
        flags=re.S,
    )

    # Insert after Trap Reasoning section if present; else after MODEL ANSWER; else near top.
    insert_after_patterns = [
        r"(\n\*\*Trap Reasoning:\*\*\s*\n.*?)(?=\n\*\*[\w ].+?:\*\*|\n---\s*$|\Z)",
        r"(\n\*\*MODEL ANSWER:\*\*\s*\n.*?)(?=\n\*\*[\w ].+?:\*\*|\n---\s*$|\Z)",
    ]

    inserted = False
    for pat in insert_after_patterns:
        m = re.search(pat, b, flags=re.S)
        if m:
            insertion = m.group(0) + f"\n\n**Why This Matters:**  \n{combined}\n"
            b = b[: m.start()] + insertion + b[m.end() :]
            inserted = True
            break

    if not inserted:
        # Fallback: insert after Scenario block
        m = re.search(r"(\n\*\*Scenario:\*\*\s*\n.*?)(?=\n\*\*MODEL ANSWER:\*\*)", b, flags=re.S)
        if m:
            insertion = m.group(0) + f"\n\n**Why This Matters:**  \n{combined}\n"
            b = b[: m.start()] + insertion + b[m.end() :]
        else:
            b = b.rstrip() + f"\n\n**Why This Matters:**  \n{combined}\n"

    # Clean up extra blank lines
    b = re.sub(r"\n{4,}", "\n\n\n", b).strip("\n") + "\n"
    return b


def make_block(
    num: int,
    title: str,
    topic: str,
    airports: str,
    aircraft: str,
    scenario: str,
    prompt: str,
    model_answer: str,
    trap_reasoning: str,
    why_this_matters: str,
    cram_mode: str,
    reference: str,
    link: str,
) -> str:
    def _clean(s: str) -> str:
        return s.strip().rstrip()

    return (
        f"## QUESTION {num}: {title}\n\n"
        f"**Topic:** {_clean(topic)}  \n"
        f"**Airports:** {_clean(airports)}  \n"
        f"**Aircraft:** {_clean(aircraft)}\n\n"
        f"**Scenario:**  \n{_clean(scenario)}\n\n"
        f"**{_clean(prompt)}**\n\n"
        f"**MODEL ANSWER:**  \n{_clean(model_answer)}\n\n"
        f"**Trap Reasoning:**  \n{_clean(trap_reasoning)}\n\n"
        f"**Why This Matters:**  \n{_clean(why_this_matters)}\n\n"
        f"**Cram Mode:**  \n{_clean(cram_mode)}\n\n"
        f"**Reference:** {_clean(reference)}  \n"
        f"**Link:** {_clean(link)}\n\n"
        f"---\n"
    )


def build_overrides() -> Dict[int, str]:
    aim_index = "https://www.faa.gov/air_traffic/publications/atpubs/aim_html/index.html"
    phak = "https://www.faa.gov/regulations_policies/handbooks_manuals/aviation/phak"
    afm = "https://www.faa.gov/regulations_policies/handbooks_manuals/aviation/airplane_handbook"
    afhandbook = "https://www.faa.gov/regulations_policies/handbooks_manuals/aviation/airplane_handbook"

    # Airport Ops/Signs: repurpose Q44–Q50
    overrides: Dict[int, str] = {}

    overrides[43] = make_block(
        43,
        "Airworthiness Directives - One-Time vs Recurring",
        "Airworthiness Directives - Compliance Types",
        "KCHD (Chandler) local",
        "Cessna 172",
        "You’re planning a local flight from Chandler (KCHD). You review the aircraft logbooks and find two AD entries:\n\n"
        "1. AD 2023-08-12 (Fuel selector valve inspection) — entry dated 14 months ago states “AD complied with, no defects found”\n"
        "2. AD 2024-15-03 (Alternator belt inspection) — entry dated 6 months ago states “AD complied with, recurring inspection required every 100 flight hours”\n\n"
        "The aircraft has flown 120 hours since the alternator belt AD compliance 6 months ago. The annual inspection is current (done 3 months ago). You feel pressure to go because the plane is booked after you.",
        "Is the aircraft airworthy for your flight today?",
        "No. If an AD requires recurring compliance every 100 hours and the aircraft has flown 120 hours since the last recorded compliance, it’s overdue and the aircraft is not airworthy until that AD is complied with and properly documented.",
        "“The annual was done 3 months ago, so the mechanic must have taken care of it.”",
        "ADs can be one-time or recurring. One-time ADs are done once; recurring ADs must be repeated at the specified interval. You can’t assume compliance without documentation. Legal vs safe: if it’s overdue, you don’t launch. If the aircraft must be moved to maintenance, that’s typically handled via a Special Flight Permit (ferry permit) if eligible—not by ‘just flying it anyway.’",
        "Recurring AD overdue = not airworthy. Don’t assume—verify the logbook entry. If it needs repositioning, think special flight permit.",
        "14 CFR 39.3, 14 CFR 91.403, 14 CFR 21.197",
        "https://www.ecfr.gov/current/title-14/chapter-I/subchapter-C/part-39/section-39.3 | https://www.ecfr.gov/current/title-14/chapter-I/subchapter-F/part-91/subpart-E/section-91.403 | https://www.ecfr.gov/current/title-14/chapter-I/subchapter-C/part-21/subpart-H/section-21.197",
    )

    overrides[44] = make_block(
        44,
        "Airport Ops/Signs - Hold Short Line vs ILS Critical Area (Towered)",
        "Airport Operations - Runway Incursion Avoidance",
        "KPDX (Portland)",
        "Cessna 172",
        "It’s a rainy evening and you’re taxiing for departure at Portland (KPDX). Ground clears you: "
        "“Taxi to Runway 28L via A, hold short of Runway 28L.” As you approach the runway, you see a set of "
        "yellow hold short lines, and farther ahead you also see a different set of ladder-style markings with "
        "an ILS sign nearby. You’re running late and feel pressure to “keep it moving” because airliners are behind you.",
        "Where do you stop, and what’s the practical difference between these two hold positions?",
        "I stop at the runway hold short lines when instructed to hold short of the runway. The ILS critical area hold "
        "position is a separate protected area used to prevent interference with the ILS signal; ATC will specifically "
        "instruct “hold short of ILS critical area” (or similar) if that applies. If I’m told to hold short of the runway, "
        "I hold short of the runway; I don’t roll past the runway hold line just because I’m “not on the runway yet.”",
        "“The ILS critical area line is the real runway hold line, so I can taxi past the first one if I’m careful.”",
        "Runway incursions happen on the ground, often due to rushing and assuming. The DPE wants disciplined taxi: "
        "read back hold short instructions, stop at the correct marking, and never “creep” across a runway hold line. "
        "Legal vs safe: even if you think you can stop quickly, crossing a hold line without clearance is both unsafe and "
        "potentially a violation depending on what you were cleared to do.",
        "Hold short means hold short. Stop at the runway hold line unless cleared to cross. ILS critical area is separate "
        "and requires specific instruction.",
        "AIM (Airport Marking Aids and Signs)",
        aim_index,
    )

    overrides[45] = make_block(
        45,
        "Airport Ops/Signs - Runway Status Lights / “It Looks Clear”",
        "Airport Operations - Visual Cues vs Clearance",
        "KSEA (Seattle Tacoma)",
        "PA-28-161",
        "You’re holding short at a runway at night. You see red in-pavement lights (runway status lights) ahead and a "
        "runway crossing sign. The controller is busy. Your passenger says, “It’s obviously clear—just go.” You’re feeling "
        "time pressure because you’re trying to make a reservation time.",
        "What do you do if lights/signs suggest “stop” but you’re tempted because the runway looks clear?",
        "I stop and wait for an explicit clearance. I don’t enter or cross a runway without a clearance at a towered airport, "
        "and I treat “stop” indications (including red runway status lights) as a strong safety cue. If I’m unsure, I ask ATC "
        "to clarify. The correct move is to pause, not to improvise.",
        "“If I can visually confirm it’s clear, I can cross and sort it out later.”",
        "Many runway incursions start with “it looked clear.” The checkride is testing disciplined surface ops: stop, ask, and "
        "comply with clearances—especially at night when depth perception and closure rates are worse. Legal vs safe: being "
        "right visually doesn’t replace a clearance and doesn’t protect you from an aircraft you didn’t see.",
        "On the surface: stop when unsure, ask ATC, and never assume a runway is yours because it looks clear.",
        "AIM (Runway Incursion Avoidance)",
        aim_index,
    )

    overrides[46] = make_block(
        46,
        "Airport Ops/Signs - Back-Taxi and CTAF Calls (Non-Towered)",
        "Airport Operations - Non-Towered Runway Use",
        "KBIH (Bishop, CA)",
        "Cessna 172",
        "You arrive at a non-towered airport with a single runway and limited taxiways. The only way to reach the departure end "
        "is to back-taxi on the runway. Winds are light. A faster aircraft announces inbound on a 2-mile final. You’re feeling "
        "pressure because you’ve been waiting a while and your passenger is impatient.",
        "How do you safely execute a back-taxi, and what do you do when someone is on short final?",
        "I treat the runway like an active movement area: I make clear CTAF calls (“entering runway, back-taxiing Runway …”), "
        "I visually clear both directions, and I keep my runway time as short as practical. If someone is on short final, I do not "
        "enter—I wait. If I’m already on the runway and an aircraft is suddenly short final, I expedite clear/off the runway only "
        "if safe; otherwise I stop and communicate.",
        "“Non-towered means no rules—just announce and go if you think you can make it.”",
        "Non-towered operations depend on communication and sequencing. The DPE wants you to prioritize collision avoidance and "
        "right-of-way, not ego or impatience. Legal vs safe: even if you could technically back-taxi quickly, the safe answer is to "
        "avoid creating a conflict with an aircraft on final.",
        "Back-taxi = runway time. Clear, announce, and don’t enter with traffic on short final.",
        "AIM (Non-Towered Airport Operations)",
        aim_index,
    )

    overrides[47] = make_block(
        47,
        "Airport Ops/Signs - “Taxi Into Position and Hold” vs “Line Up and Wait”",
        "Airport Operations - Phraseology Awareness",
        "KTPA (Tampa Intl)",
        "DA40",
        "During a towered departure briefing, your instructor mentions you might hear “line up and wait.” You’ve also heard older "
        "pilots say “position and hold.” You’re anxious because you don’t want to mess up comms on your checkride.",
        "If tower says “line up and wait,” what exactly are you cleared to do—and what are you not cleared to do?",
        "“Line up and wait” clears me to taxi onto the runway and line up on the centerline, then stop and wait for takeoff clearance. "
        "It does not clear me for takeoff. If anything is unclear, I ask before rolling.",
        "“Once I’m on the runway, I’m basically cleared—if it looks good I can just go.”",
        "This is a classic DPE surface-ops trap: correct readback and restraint. The safe/legal line is strict: runway entry only as cleared, "
        "and takeoff only with an explicit takeoff clearance at a towered airport.",
        "Line up and wait = enter runway and hold. Takeoff requires a separate takeoff clearance.",
        "AIM (ATC Phraseology)",
        aim_index,
    )

    overrides[48] = make_block(
        48,
        "Airport Ops/Signs - Closed Runway Markings and NOTAM Reality",
        "Airport Operations - Closed Runway / Construction",
        "KAPA (Centennial)",
        "Cessna 172",
        "You taxi out and notice large yellow “X” markings near a runway entrance. The airport diagram in your EFB also shows a runway closed "
        "segment, but you’re not sure if it’s “just for big jets.” You’re under pressure because you already delayed once and don’t want to return "
        "to parking.",
        "How do you treat runway closure markings, and what do you do if your clearance seems to conflict?",
        "A yellow “X” indicates a runway (or portion) is closed. I do not use a closed runway. If ATC gives an instruction that appears to conflict, "
        "I stop and clarify—controllers can make mistakes, and I’m still responsible as PIC. I verify with NOTAMs/ATIS and ask for alternate routing.",
        "“If tower cleared me, it must be open—so the X is probably old or for someone else.”",
        "Runway closures are safety-critical. The DPE wants you to show PIC responsibility: stop, verify, and resolve the conflict before moving into a hazard area. "
        "Legal vs safe: even with a clearance, operating on a closed surface can be unsafe and may violate local restrictions/NOTAMs.",
        "Yellow X = closed. Stop and clarify any conflict; PIC is still responsible.",
        "AIM (Airport Markings/NOTAMs), 14 CFR 91.103",
        f"https://www.ecfr.gov/current/title-14/chapter-I/subchapter-F/part-91/subpart-B/section-91.103 | {aim_index}",
    )

    overrides[49] = make_block(
        49,
        "Airport Ops/Signs - Hot Spots on Airport Diagrams",
        "Airport Operations - Pre-Taxi Briefing",
        "KPHX (Phoenix Sky Harbor)",
        "PA-28-161",
        "You’re at a complex airport for the first time. Your taxi clearance includes several intersections. The airport diagram shows “HS-1” and “HS-2” "
        "hot spot boxes near your route. You’re feeling pressure because you don’t want to sound confused on frequency.",
        "What is a hot spot, and how does it change how you taxi?",
        "A hot spot is a historically confusing or high-risk area for runway incursions. It doesn’t change the clearance, but it changes my mindset: I slow down, "
        "brief the route, verify signage/markings, and I’m ready to stop and ask for progressive taxi if needed. I prioritize accuracy over speed.",
        "“Hot spots are just informational—no action needed.”",
        "Hot spots are there because pilots have made mistakes there. The DPE is testing whether you use the airport diagram proactively and can manage workload on the ground.",
        "Hot spot = slow down, brief, verify, and ask if unsure. Taxi is a phase of flight.",
        "AIM (Hot Spots/Airport Diagrams), FAA Airport Diagram Symbology",
        aim_index,
    )

    overrides[50] = make_block(
        50,
        "Airport Ops/Signs - Runway Lighting: Edge vs Centerline vs REIL",
        "Airport Operations - Night Visual Cues",
        "KAVL (Asheville)",
        "Cessna 172",
        "Night arrival to a larger non-towered airport. You see white runway edge lights, a set of bright strobes at the threshold, and green lights near the start. "
        "Your passenger says, “Those flashing lights must mean the runway is closed.” You’re a little fatigued after a long day.",
        "Explain what REIL and runway edge/threshold lights tell you, and how you confirm you’re lined up on the correct runway.",
        "REIL (Runway End Identifier Lights) are flashing lights used to help identify the runway end/threshold. Runway edge lights outline the runway edges; threshold lights "
        "are green facing the approach side and help identify the runway beginning. To confirm correct runway: verify heading on final, match runway number/geometry to the diagram, "
        "and cross-check GPS/EFB (if used) without fixating.",
        "“Flashing lights mean closed runway—avoid it.”",
        "At night, misidentifying a runway is a real hazard. The DPE wants practical cross-checks (heading, diagram, visual cues) rather than guessing based on one cue.",
        "Night runway ID: verify heading, diagram, and cues. REIL helps identify the runway end; it doesn’t mean closed.",
        "AIM (Airport Lighting Aids), PHAK (Airport Operations)",
        f"{aim_index} | {phak}",
    )

    # Navigation: repurpose Q123–Q130 (remove from XC count)
    overrides[123] = make_block(
        123,
        "Navigation - Lost Procedure (VFR): “Confidently Lost”",
        "Navigation - VFR Lost Procedures",
        "KHSV (Huntsville) area",
        "Cessna 172",
        "You’re on a VFR cross-country and realize the ground features don’t match your planned checkpoints. Your passenger asks if you’re lost. You feel pressure because you "
        "don’t want to admit it and you’re close to a Class C shelf.",
        "What’s your immediate, step-by-step lost procedure?",
        "Aviate: stabilize, climb if appropriate for better reception/visibility, and conserve fuel. Navigate: use the “5 C’s” style process—Climb, Conserve, Communicate, Confess, "
        "Comply. I cross-check heading/time, use pilotage with prominent features, and use nav aids (VOR/GPS) to reorient. Communicate early with ATC/Flight Service if needed.",
        "“I’ll keep going a little longer until I recognize something.”",
        "The risk is drifting into airspace, terrain, or fuel trouble while denial builds. The DPE wants early admission and structured recovery, not hoping it fixes itself.",
        "Lost? Stabilize + climb + communicate early. Don’t delay the confession—fix it before it becomes an emergency.",
        "PHAK (Navigation), AIM (Radar Services/VFR Advisories)",
        f"{phak} | {aim_index}",
    )

    overrides[124] = make_block(
        124,
        "Navigation - VOR Check Requirements and Practical Options",
        "Navigation - VOR Operational Checks",
        "KAPA (Centennial) → KCOS (Colorado Springs)",
        "PA-28-161",
        "You plan to navigate primarily by VOR today to prove you can do it. A friend asks, “Did you do a VOR check?” You haven’t done one in a while, and you’re scheduled "
        "to meet your instructor for a stage check in an hour.",
        "When is a VOR check required, and how would you do it?",
        "A VOR check is required only if I plan to use VOR equipment for IFR operations. For VFR, it’s not required by regulation, but I still want reasonable confidence it’s "
        "working before I rely on it. Practical check methods include a VOT, a ground checkpoint, an airborne checkpoint, or a dual-VOR comparison (within tolerances).",
        "“Any time you use a VOR for navigation, you must do an official VOR check.”",
        "This tests regulatory precision: IFR has specific VOR check requirements, VFR doesn’t—yet ADM still says don’t blindly trust a nav source. Legal vs safe can differ.",
        "VOR check is an IFR requirement. VFR: not required, but verify equipment before you bet the flight on it.",
        "AIM (VOR Checks)",
        aim_index,
    )

    overrides[125] = make_block(
        125,
        "Navigation - GPS ‘Direct-To’ vs Flight Plan (Situational Awareness)",
        "Navigation - GPS/EFB Use and Monitoring",
        "KSQL (San Carlos) → KSTS (Santa Rosa)",
        "DA40",
        "You enter a direct-to to your destination while climbing out. Your passenger asks a question and you realize you haven’t verified airspace along the direct track. You’re "
        "under pressure because NorCal is busy and you don’t want to sound unsure.",
        "What’s the risk of ‘direct-to’ thinking, and how do you manage it safely?",
        "Direct-to can hide airspace, terrain, and alternates because you stop thinking in segments/checkpoints. I manage it by verifying the route on the chart, setting appropriate "
        "altitudes, using checkpoints anyway, and using flight following. GPS is a tool, not the plan.",
        "“GPS direct-to is always safer because it’s simpler.”",
        "This is about automation complacency. The DPE wants you to show you’re still navigating with the big picture: airspace, terrain, fuel, outs—while using GPS to assist.",
        "GPS helps, but you still plan: chart review, checkpoints, altitude, and outs. Don’t let direct-to erase situational awareness.",
        "PHAK (Navigation/Risk Management), AIM (GPS Basics)",
        f"{phak} | {aim_index}",
    )

    overrides[126] = make_block(
        126,
        "Navigation - Pilotage vs Dead Reckoning: When Each Breaks",
        "Navigation - Techniques and Failure Modes",
        "KSGJ (St. Augustine) area",
        "Cessna 172",
        "You planned a pilotage-heavy route using highways and shorelines. Halfway through, haze reduces visibility and the shoreline looks washed out. You’re trying to stay on schedule "
        "for a meeting.",
        "What’s your plan to stay oriented when pilotage degrades?",
        "I shift to a layered nav approach: verify time/fuel (dead reckoning), use headings with wind correction, and use nav aids (VOR/GPS) to back up what I see. If visibility is "
        "degrading toward my minimums, I divert early or return rather than pressing into worsening conditions.",
        "“Pilotage is what VFR pilots do—if I can’t see the landmarks, I’ll just keep looking harder.”",
        "Pilotage is great until it isn’t. The DPE wants you to demonstrate redundancy and conservative decision-making as visibility trends down.",
        "Use layers: pilotage + DR + nav aids. If visibility is trending down, divert early—don’t press.",
        "PHAK (Navigation), 14 CFR 91.103",
        f"{phak} | https://www.ecfr.gov/current/title-14/chapter-I/subchapter-F/part-91/subpart-B/section-91.103",
    )

    overrides[127] = make_block(
        127,
        "Navigation - Magnetic vs True: ‘Heading’ Errors in Practice",
        "Navigation - Practical Compass/Heading Concepts",
        "KICT (Wichita) area",
        "PA-28-161",
        "You’re briefing a cross-country and your buddy says, “Just fly the true course on the sectional.” You notice the variation in your area is significant. You’re under time pressure "
        "and tempted to skip the conversion steps.",
        "Explain what you actually set on the heading indicator and why variation matters.",
        "Sectionals show true course lines. To fly the correct magnetic heading, I apply variation (true to magnetic) and then apply wind correction. What I ‘set and fly’ is a magnetic "
        "heading on the DG/HSI, corrected for wind. Skipping variation can produce a meaningful off-course error over distance.",
        "“Variation is small—close enough doesn’t matter for PPL flights.”",
        "Over a longer leg, ‘small’ errors become big. The DPE wants you to show you understand the chain: True course → magnetic course → wind-corrected heading.",
        "True on the chart, magnetic in the cockpit. Apply variation, then wind correction, then fly the heading.",
        "PHAK (Navigation)",
        phak,
    )

    overrides[128] = make_block(
        128,
        "Navigation - Using a VOR Radial Correctly (FROM vs TO Trap)",
        "Navigation - VOR Interpretation",
        "KOKC (Oklahoma City) practice area",
        "Cessna 172",
        "You tune a VOR and set the OBS to 090. The needle centers with a FROM flag. Your passenger says, “Great—we’re on the 090 heading to the station.” You’re being evaluated and "
        "feel pressure to answer confidently.",
        "Explain what the radial means and what the FROM flag tells you.",
        "VOR radials are defined as courses *from* the station. If I have the 090 selected with a FROM indication and centered needle, I’m on the 090 radial—meaning I’m east of the "
        "station. If I want to fly *to* the station from there, I’d fly a 270 course to the station (with a TO indication when set correctly).",
        "“090 selected means fly heading 090 to the station.”",
        "This is a classic VOR trap. The DPE wants you to understand the geometry, not just twist knobs: radials are FROM; TO/FROM matters.",
        "Radials are FROM the station. To go TO, use the reciprocal course with a TO indication.",
        "AIM (VOR), PHAK (Navigation)",
        f"{aim_index} | {phak}",
    )

    overrides[129] = make_block(
        129,
        "Navigation - DME / GPS Distance: What It Actually Measures",
        "Navigation - Slant Range Concept",
        "KABQ (Albuquerque) area",
        "DA40",
        "You’re overhead a VOR/DME at 6,000 feet AGL and your distance readout shows about 1.0 NM. Your friend says, “That’s wrong—you’re directly over it.” You’re trying to sound "
        "confident on a stage check.",
        "Explain why DME/GPS distance can show a nonzero number when you’re overhead.",
        "DME and GPS show slant-range distance (the straight-line distance) to the station/waypoint. When you’re overhead, horizontal distance is near zero but you still have vertical "
        "distance, so the readout won’t be zero until you’re extremely low. This is normal.",
        "“Distance is measured along the ground only.”",
        "Understanding what the instrument is really telling you prevents bad decisions (like ‘chasing’ a distance number).",
        "Overhead doesn’t mean ‘0.0’—slant range includes altitude.",
        "AIM (DME/GPS Basics)",
        aim_index,
    )

    overrides[130] = make_block(
        130,
        "Navigation - Diversion on the Fly (Time/Fuel Math Under Pressure)",
        "Navigation - Diversion Planning",
        "KDSM (Des Moines) area",
        "Cessna 172",
        "Enroute, ceilings are lowering and you decide to divert. You’re stressed and tempted to ‘just follow the GPS’ without calculating anything. You have a passenger appointment you "
        "don’t want to miss.",
        "What’s the minimum diversion math you do before committing?",
        "I pick the divert airport, turn toward it, and immediately compute: new heading (rough), distance, groundspeed estimate, ETA, and fuel required. I verify terrain/airspace and "
        "I communicate early if I’m with ATC. Even with GPS, I confirm it makes sense.",
        "“If the GPS says it’s 20 minutes away, I don’t need to compute anything.”",
        "Diversions are where situational awareness collapses. The DPE wants you to show you can still do basic time/fuel/heading thinking under stress.",
        "Divert = turn + time/fuel/ETA check + airspace/terrain check + communicate. GPS assists, it doesn’t replace judgment.",
        "PHAK (Navigation), 14 CFR 91.103",
        f"{phak} | https://www.ecfr.gov/current/title-14/chapter-I/subchapter-F/part-91/subpart-B/section-91.103",
    )

    # New question blocks Q196–Q250 added later in a separate builder to keep this section readable.
    # Placeholder here: return overrides for repurposed numbers only.
    return overrides


@dataclass(frozen=True)
class Category:
    key: str
    title: str
    target: int
    nums: List[int]


def validate_questions(questions: Dict[int, str]) -> None:
    missing = [n for n in range(1, 251) if n not in questions]
    if missing:
        raise SystemExit(f"Missing question numbers: {missing[:20]}{'...' if len(missing) > 20 else ''}")

    # Ensure no placeholders and required fields
    bad_links = []
    bad_fields = []
    for n in range(1, 251):
        b = questions[n]
        if "**Link:**" not in b:
            bad_fields.append((n, "missing **Link:**"))
        if "**Reference:**" not in b:
            bad_fields.append((n, "missing **Reference:**"))
        m = re.search(r"^\*\*Link:\*\*\s*(.*)$", b, flags=re.M)
        if not m or not m.group(1).strip() or m.group(1).strip() == "#":
            bad_links.append(n)
    if bad_fields:
        raise SystemExit(f"Bad/missing fields examples: {bad_fields[:10]}")
    if bad_links:
        raise SystemExit(f"Placeholder/empty links: {bad_links[:20]}{'...' if len(bad_links) > 20 else ''}")


def build_new_questions_196_250() -> Dict[int, str]:
    phak = "https://www.faa.gov/regulations_policies/handbooks_manuals/aviation/phak"
    afhandbook = "https://www.faa.gov/regulations_policies/handbooks_manuals/aviation/airplane_handbook"
    aim_index = "https://www.faa.gov/air_traffic/publications/atpubs/aim_html/index.html"
    rmh = "https://www.faa.gov/regulations_policies/handbooks_manuals/aviation/risk_management_handbook"

    cfr_61_56 = "https://www.ecfr.gov/current/title-14/chapter-I/subchapter-D/part-61/subpart-A/section-61.56"
    cfr_61_57 = "https://www.ecfr.gov/current/title-14/chapter-I/subchapter-D/part-61/subpart-A/section-61.57"
    cfr_61_3 = "https://www.ecfr.gov/current/title-14/chapter-I/subchapter-D/part-61/subpart-A/section-61.3"
    cfr_91_103 = "https://www.ecfr.gov/current/title-14/chapter-I/subchapter-F/part-91/subpart-B/section-91.103"
    cfr_91_155 = "https://www.ecfr.gov/current/title-14/chapter-I/subchapter-F/part-91/subpart-B/section-91.155"
    cfr_91_113 = "https://www.ecfr.gov/current/title-14/chapter-I/subchapter-F/part-91/subpart-B/section-91.113"
    cfr_91_119 = "https://www.ecfr.gov/current/title-14/chapter-I/subchapter-F/part-91/subpart-B/section-91.119"
    cfr_91_151 = "https://www.ecfr.gov/current/title-14/chapter-I/subchapter-F/part-91/subpart-B/section-91.151"
    cfr_91_159 = "https://www.ecfr.gov/current/title-14/chapter-I/subchapter-F/part-91/subpart-B/section-91.159"
    cfr_91_205 = "https://www.ecfr.gov/current/title-14/chapter-I/subchapter-F/part-91/subpart-C/section-91.205"
    cfr_91_213 = "https://www.ecfr.gov/current/title-14/chapter-I/subchapter-F/part-91/subpart-C/section-91.213"
    cfr_91_126 = "https://www.ecfr.gov/current/title-14/chapter-I/subchapter-F/part-91/subpart-B/section-91.126"
    cfr_91_127 = "https://www.ecfr.gov/current/title-14/chapter-I/subchapter-F/part-91/subpart-B/section-91.127"
    cfr_91_129 = "https://www.ecfr.gov/current/title-14/chapter-I/subchapter-F/part-91/subpart-B/section-91.129"
    cfr_91_130 = "https://www.ecfr.gov/current/title-14/chapter-I/subchapter-F/part-91/subpart-B/section-91.130"
    cfr_91_131 = "https://www.ecfr.gov/current/title-14/chapter-I/subchapter-F/part-91/subpart-B/section-91.131"

    new: Dict[int, str] = {}

    # Pilot Privileges/ADM (Q196–Q204)
    new[196] = make_block(
        196,
        "Pilot Privileges/ADM - Flight Review: ‘I Flew Recently’",
        "Currency/Proficiency - Flight Review Requirements",
        "KSQL (San Carlos) local",
        "Cessna 172",
        "You have 30 hours in the last 90 days and flew with friends last weekend. Your friend says you don’t need a flight review because you’re obviously proficient. "
        "You’re planning to rent tomorrow and the FBO asks for your flight review date.",
        "Are you legal without a current flight review—and what satisfies the requirement?",
        "Without a flight review within the preceding 24 calendar months, I’m not legal to act as PIC. A flight review is not about recency of flying; it’s a specific requirement. "
        "Certain other activities can substitute (for example, a checkride or a practical test), but otherwise I need a flight review endorsement.",
        "“If I’ve flown a lot recently, that replaces the flight review.”",
        "This separates ‘current’ from ‘proficient.’ The DPE wants you to know the flight review is a regulatory requirement with specific timing, regardless of how much you’ve flown.",
        "Flight review is every 24 calendar months unless replaced by a practical test. Hours flown don’t substitute.",
        "14 CFR 61.56",
        cfr_61_56,
    )

    new[197] = make_block(
        197,
        "Pilot Privileges/ADM - Passenger Carrying: ‘3 Landings = Good’ (But Which Type?)",
        "Currency - Passenger Carrying Day vs Night",
        "KCRQ (McClellan-Palomar)",
        "PA-28-161",
        "You did three daytime touch-and-goes yesterday. Tonight you want to take your spouse for a sightseeing flight after dark. You’re feeling pressure because it’s a special occasion.",
        "Are your daytime landings enough to carry passengers at night?",
        "No. Night passenger currency requires three takeoffs and landings to a full stop at night (in the preceding 90 days). Daytime landings don’t satisfy the night requirement.",
        "“Three landings are three landings—currency is currency.”",
        "Night ops add risk (visual illusions, depth perception, workload). The regulations reflect that with a stricter requirement for night passenger carrying.",
        "Night passengers: 3 takeoffs/landings to a full stop at night within 90 days.",
        "14 CFR 61.57",
        cfr_61_57,
    )

    new[198] = make_block(
        198,
        "Pilot Privileges/ADM - ‘I’ll Just Log Dual’ (But Who’s PIC?)",
        "PIC Authority/Logging - Responsibilities vs Logging",
        "KDVT (Deer Valley)",
        "Cessna 172",
        "You and another private pilot go up together. You sit left seat and fly the whole time. The other pilot (right seat) says he’ll log PIC because ‘it’s his plane’ and he was "
        "watching for traffic. You’re both trying to build time for insurance.",
        "Who is actually the PIC, and why does it matter?",
        "PIC is the person who has final authority and responsibility for the operation and safety of the flight. Logging PIC time and being PIC are related but not identical. Before the "
        "flight, we must explicitly agree who is acting as PIC; that person is responsible for decisions, compliance, and enforcement exposure. If there’s an incident, ‘we both thought’ is "
        "not an acceptable answer.",
        "“PIC is whoever flies the most, and we can both log it however we want.”",
        "DPEs care that you understand responsibility doesn’t disappear because you’re ‘just helping.’ On the ramp, the FAA and insurance will want one clear PIC.",
        "Agree on acting PIC before engine start. Acting PIC = final authority and accountability.",
        "14 CFR 91.3, 14 CFR 61.3",
        f"https://www.ecfr.gov/current/title-14/chapter-I/subchapter-F/part-91/subpart-A/section-91.3 | {cfr_61_3}",
    )

    new[199] = make_block(
        199,
        "Pilot Privileges/ADM - ‘I Can Fly Any Airplane if I’m Rated ASEL’",
        "Pilot Privileges - Category/Class and Endorsements",
        "KFXE (Fort Lauderdale Executive)",
        "DA40",
        "A friend offers you their high-performance single-engine airplane for a weekend trip. You’re a private pilot ASEL. You feel pressure because it’s a rare opportunity.",
        "What determines whether you can act as PIC—category/class vs endorsements?",
        "Category/class on my certificate (ASEL) is necessary but not always sufficient. Certain aircraft require specific endorsements (for example, high-performance or complex if applicable). "
        "I also need to be current and meet any insurance/rental requirements.",
        "“ASEL means I can fly any single-engine land plane with no additional sign-offs.”",
        "This is a checkride classic: privileges have layers—certificate, endorsements, currency, and real-world requirements.",
        "Certificate category/class + endorsements + currency + aircraft requirements all matter.",
        "14 CFR 61.31, 14 CFR 61.3",
        "https://www.ecfr.gov/current/title-14/chapter-I/subchapter-D/part-61/subpart-E/section-61.31 | " + cfr_61_3,
    )

    new[200] = make_block(
        200,
        "Pilot Privileges/ADM - ‘Friends Want to Tip Me’",
        "Compensation/Compensation-Like Situations",
        "KJAC (Jackson Hole)",
        "Cessna 172",
        "After a fun flight, your friends offer to ‘tip’ you $100 for being a great pilot. You didn’t discuss money before the flight, but you feel social pressure not to be awkward.",
        "Can you accept it as a private pilot?",
        "I should treat it as compensation and decline. As a private pilot, I generally cannot accept compensation for acting as PIC. Even if it’s called a ‘tip,’ it can be viewed as compensation.",
        "“It’s after the flight, so it can’t be compensation.”",
        "This is a real-world trap: money around flights invites enforcement risk. The DPE wants conservative judgment—don’t take money that looks like payment for piloting.",
        "If money is tied to the flight, assume it’s compensation—don’t accept it as a private pilot.",
        "14 CFR 61.113",
        "https://www.ecfr.gov/current/title-14/chapter-I/subchapter-D/part-61/subpart-E/section-61.113",
    )

    new[201] = make_block(
        201,
        "Pilot Privileges/ADM - Personal Minimums: Turning Weather Data into a ‘No’",
        "ADM - Personal Minimums and Triggers",
        "KORL (Orlando Exec) → KSSI (Brunswick Golden Isles)",
        "PA-28-161",
        "Briefing shows: destination forecast 2,500 BKN with 5SM in light rain near your ETA; scattered convective build-ups inland. Legal VFR could still be possible. Your passenger has "
        "a nonrefundable hotel and keeps reminding you. You’re legal, but your gut says it’s tight.",
        "How do you apply personal minimums to make a decision?",
        "I compare the forecast/trends to pre-set minimums (not made up on the spot): ceilings/visibility, crosswind, convective risk, alternates, and ‘outs’ along the route. If conditions "
        "are at/near my trigger, I decide on the ground: delay, drive, or change the plan. I also set hard in-flight decision points (turn/divert) before takeoff.",
        "“I’ll launch because it’s legal, and I’ll see what happens.”",
        "Personal minimums are designed to prevent plan-continuation bias. Legal vs safe: being legal doesn’t mean you have adequate margin for your experience level.",
        "Use pre-set minimums and hard triggers. Don’t invent minimums mid-briefing to justify going.",
        "FAA Risk Management Handbook, 14 CFR 91.103",
        f"{rmh} | {cfr_91_103}",
    )

    new[202] = make_block(
        202,
        "Pilot Privileges/ADM - ‘Just One More’ (Hazardous Attitudes)",
        "ADM - Hazardous Attitudes and Antidotes",
        "KAPA (Centennial)",
        "Cessna 172",
        "You’re tired but want to squeeze in one more lap in the pattern before the sun sets because you feel behind in training. You catch yourself thinking, “Nothing ever happens here.”",
        "Which hazardous attitude is this and what’s the antidote you actually apply?",
        "That’s likely invulnerability (“it won’t happen to me”). The antidote is to consciously acknowledge risk and choose a safer action: stop early, brief, and come back rested—especially "
        "if conditions (light, fatigue, winds) are changing.",
        "“If I’m careful, hazardous attitudes don’t matter.”",
        "The DPE is testing self-management. Many accidents aren’t skill failures—they’re decision failures driven by attitude and pressure.",
        "Name the attitude, apply the antidote, and change the plan—don’t just ‘be careful.’",
        "FAA Risk Management Handbook",
        rmh,
    )

    new[203] = make_block(
        203,
        "Pilot Privileges/ADM - IMSAFE: ‘I’m Fine’ (But Are You?)",
        "ADM - Fitness for Flight",
        "KMYF (San Diego Montgomery)",
        "DA40",
        "You slept 4 hours, had a stressful workday, and you’re mildly dehydrated. You tell yourself you’re fine because you’re not sick. Your passenger expects you to go.",
        "How do you use IMSAFE to make a PIC decision?",
        "I deliberately assess IMSAFE (Illness, Medication, Stress, Alcohol, Fatigue, Eating/Emotion). If multiple items are degraded (stress + fatigue + dehydration), I treat it as a real risk "
        "and change the plan. A ‘legal’ pilot can still be unsafe.",
        "“If I’m under the legal alcohol limits, I’m good to go.”",
        "Physiology and judgment failures are common. The DPE wants you to demonstrate you’ll cancel for yourself, not just for weather.",
        "IMSAFE is a go/no-go tool. If multiple factors are off, don’t fly.",
        "FAA Risk Management Handbook",
        rmh,
    )

    new[204] = make_block(
        204,
        "Pilot Privileges/ADM - ‘I Don’t Want to File NASA’",
        "ADM - Reporting / Learning Culture",
        "KSDL (Scottsdale)",
        "Cessna 172",
        "You accidentally enter a Class C outer ring without establishing communication. Nothing happens in the moment, but you realize it later. You’re embarrassed and don’t want to “draw attention.”",
        "What’s a responsible next step, and why?",
        "I should learn from it immediately: debrief, identify root cause, and consider filing an ASRS (NASA) report promptly. The key goal is safety learning and documenting the event; it’s not "
        "a ‘get out of jail free’ card. I also review airspace procedures to prevent recurrence.",
        "“If nobody called me, it’s better to say nothing.”",
        "This tests maturity: pilots make mistakes; good pilots learn and build barriers. The DPE wants a safety-culture mindset.",
        "Own it, learn it, and build a fix. Consider ASRS promptly after a deviation.",
        "FAA Risk Management Handbook",
        rmh,
    )

    # Airspace & Regs (Q205–Q225)
    new[205] = make_block(
        205,
        "Airspace & Regs - VFR Cruising Altitudes (Odd/Even + 500)",
        "VFR Operations - Altitude Selection",
        "KELP (El Paso) → KABQ (Albuquerque)",
        "Cessna 172",
        "You’re planning a VFR cross-country on a magnetic course of 020°. Your passenger wants the smoothest ride and suggests 7,500 because it’s common. You’re also trying to stay clear "
        "of clouds and feel pressure to pick an altitude quickly.",
        "What altitude rule applies, and what altitude(s) are appropriate?",
        "For VFR cruising altitudes above 3,000 feet AGL, I use the hemispheric rule: magnetic course 000–179 uses odd thousands + 500 (e.g., 5,500, 7,500). For 180–359 it’s even + 500. "
        "I still choose an altitude that clears terrain, airspace, and weather.",
        "“It’s VFR—any altitude is fine as long as I’m legal for airspace.”",
        "This is a basic compliance item that prevents head-on conflicts. The DPE wants you to know the rule and apply it correctly.",
        "Above 3,000 AGL: 000–179 = odd + 500; 180–359 = even + 500.",
        "14 CFR 91.159",
        cfr_91_159,
    )

    new[206] = make_block(
        206,
        "Airspace & Regs - Minimum Safe Altitudes (City vs Rural)",
        "Operating Rules - Minimum Altitudes",
        "KPHL (Philadelphia) outskirts",
        "PA-28-161",
        "You’re sightseeing near a built-up area and your passenger wants a closer view of the skyline. You consider descending to 800 feet AGL because visibility is good and you’re not over "
        "the exact downtown core.",
        "What rule governs minimum altitudes, and what’s the safe answer?",
        "14 CFR 91.119 governs minimum safe altitudes. Over congested areas, I need at least 1,000 feet above the highest obstacle within a 2,000-foot radius. Over other than congested, I "
        "must stay 500 feet from any person/vessel/vehicle/structure. Regardless, I keep altitude for engine-out options and noise sensitivity.",
        "“If I’m not directly over the center of the city, the congested rule doesn’t apply.”",
        "This is legal-and-safe. Even if you could argue an area isn’t ‘congested,’ low flight reduces options and increases complaint/enforcement risk. The DPE wants conservative judgment.",
        "91.119: 1,000’ above congested, 500’ away elsewhere—plus keep engine-out options.",
        "14 CFR 91.119",
        cfr_91_119,
    )

    new[207] = make_block(
        207,
        "Airspace & Regs - Right-of-Way: Converging vs Overtaking",
        "Operating Rules - Right-of-Way",
        "KFLG (Flagstaff) area",
        "Cessna 172",
        "Two aircraft converge at similar altitude near a VFR corridor. You see the other airplane off your right side, same altitude, and closure is increasing. You feel pressure because you "
        "don’t want to make a ‘big deal’ on the radio.",
        "Who has the right-of-way, and what do you actually do?",
        "For converging aircraft, the one on the other’s right has the right-of-way, so I should give way. Practically, I take early, obvious action to avoid, maintain visual contact, and communicate "
        "as appropriate. Even if I have the right-of-way, I still avoid a collision.",
        "“If I have the right-of-way, I hold course and speed no matter what.”",
        "Right-of-way rules don’t prevent midairs if you rely on them like traffic laws. The DPE wants avoidance behavior, not ‘being right.’",
        "Right-of-way helps decision-making; collision avoidance is always required.",
        "14 CFR 91.113",
        cfr_91_113,
    )

    # ... due to space, remaining Q208–Q250 are generated in the real implementation below.
    # To keep this file maintainable in one patch, we’ll build the rest programmatically from a compact spec.

    # Compact spec for remaining questions (Q208–Q250)
    # Each tuple: (num, title, topic, airports, aircraft, scenario, prompt, model, trap, why, cram, ref, link)
    more_specs = [
        (
            208,
            "Airspace & Regs - Class D Entry: ‘I Called the Tower Once’",
            "Airspace - Class D Communications",
            "KDAY (Dayton Intl) Class D",
            "Cessna 172",
            "You’re inbound VFR to a Class D airport. You call tower: “Dayton Tower, Cessna 123AB, 10 miles west, inbound for full stop.” Tower replies: “Cessna 3AB, standby.” "
            "You’re tempted to continue because you ‘made contact.’",
            "Can you enter the Class D airspace on ‘standby’?",
            "No. For Class D, I need to establish two-way radio communications before entering. ‘Standby’ without my callsign acknowledged for my aircraft does not meet that. I remain outside until "
            "I get a response addressing me and I can comply with instructions.",
            "“I transmitted, so I’m good to enter.”",
            "This is a common bust. The DPE wants precise comm requirements and conservative boundary discipline.",
            "Class D: two-way comms before entry—wait for a response with your callsign.",
            "14 CFR 91.129",
            cfr_91_129,
        ),
        (
            209,
            "Airspace & Regs - Class C ‘Establish Communications’",
            "Airspace - Class C Entry Requirements",
            "KSJC (San Jose) Class C",
            "PA-28-161",
            "You call approach outside Class C and hear: “Aircraft calling San Jose Approach, standby.” You’re close to the boundary and feel pressure to keep your route simple.",
            "Are you cleared into Class C?",
            "No. For Class C, I must establish two-way radio communications with ATC before entry. That generally means they respond with my callsign. A generic ‘standby’ to unknown traffic isn’t it.",
            "“Any response on frequency counts as two-way.”",
            "Class C busts are common when pilots assume. The DPE is testing boundary discipline and callsign acknowledgment.",
            "Class C: don’t enter until ATC talks to you (callsign) and you can comply.",
            "14 CFR 91.130",
            cfr_91_130,
        ),
        (
            210,
            "Airspace & Regs - Class B Clearance: ‘Talking to Approach Is Enough’",
            "Airspace - Class B Requirements",
            "KATL (Atlanta) Class B",
            "DA40",
            "You’re getting flight following and ATC is busy. You’re approaching the Class B boundary. Your passenger says, “You’re already talking to them, so we’re cleared in.”",
            "What do you need to enter Class B?",
            "I need an explicit ATC clearance to enter Class B. Being in communication or on flight following is not the same as being cleared into Class B. If I don’t have the words, I stay out.",
            "“Flight following means I’m automatically cleared.”",
            "This is a high-frequency checkride point. The DPE wants the exact concept: ‘cleared into’ Class B is explicit.",
            "Class B: you must hear an explicit clearance to enter.",
            "14 CFR 91.131",
            cfr_91_131,
        ),
        (
            211,
            "Airspace & Regs - VFR Weather Minimums: Knowing When You’re ‘Marginal’",
            "Operating Rules - VFR Weather Minimums",
            "KROA (Roanoke) area",
            "Cessna 172",
            "You’re cruising in Class E below 10,000 MSL with 3SM visibility and a scattered layer at 2,000 AGL. You’re tempted because it’s technically legal and you want to get home.",
            "What are the basic Class E VFR minimums, and what’s the ADM call?",
            "Class E below 10,000 MSL: 3SM visibility and 500 below / 1,000 above / 2,000 horizontal from clouds. Legal doesn’t automatically mean safe; if you’re near minimums, you should expect "
            "rapid changes, reduced options, and higher workload—consider delaying or using a higher personal minimum.",
            "“If it’s legal, it’s safe.”",
            "The DPE is testing that you know the numbers and can separate legality from safety with personal minimums.",
            "Know 91.155 numbers, then add margin with personal minimums.",
            "14 CFR 91.155",
            cfr_91_155,
        ),
        (
            212,
            "Airspace & Regs - Fuel Reserves: ‘I’ll Make It With 20 Minutes’",
            "Operating Rules - VFR Fuel Requirements",
            "KHSV (Huntsville) → KBHM (Birmingham)",
            "PA-28-161",
            "Unexpected headwinds add 15 minutes. Your fuel estimate shows landing with ~20 minutes remaining in daytime VFR. You feel pressure because you don’t want to stop.",
            "Are you legal, and what’s the safe decision?",
            "Day VFR requires enough fuel to fly to the first point of intended landing plus 30 minutes at normal cruising speed. Landing with 20 minutes is not legal. Safe practice is more conservative—"
            "divert early while you still have options.",
            "“Fuel regs are just guidelines; I’ll stretch it.”",
            "Fuel exhaustion accidents often start with denial. The DPE wants clear compliance and early diversion behavior.",
            "Day VFR: land with 30-minute reserve minimum—divert early, not late.",
            "14 CFR 91.151",
            cfr_91_151,
        ),
        (
            213,
            "Airspace & Regs - Dashed Magenta: Class E to the Surface (No Radio Requirement)",
            "Airspace - Class E Surface Areas",
            "KMTN (Martin State) area",
            "Cessna 172",
            "You’re flying to a non-towered airport that sits under a **dashed magenta** airspace boundary on the sectional. It’s late afternoon and haze is increasing. Your passenger says, “That’s controlled airspace—"
            "we have to talk to someone to enter, right?” You feel pressure because you don’t want to sound unsure.",
            "What does dashed magenta mean, and what does it require for a VFR pilot?",
            "Dashed magenta indicates Class E airspace extending to the surface (often to protect IFR approaches). For VFR, it doesn’t create a radio-communication requirement by itself. I still must meet VFR weather minimums "
            "for the airspace and operate safely, but I don’t need a clearance just because it’s Class E.",
            "“Controlled airspace always means you must talk to ATC.”",
            "This tests that you can read the chart and separate ‘controlled’ from ‘communication required.’ The DPE wants you to apply the correct requirement: weather minimums and safe ops, not imaginary clearances.",
            "Dashed magenta = Class E to surface. No clearance/comm requirement just for Class E—meet VFR weather minimums.",
            "14 CFR 91.155, AIM (Airspace)",
            f"{cfr_91_155} | {aim_index}",
        ),
    ]

    for spec in more_specs:
        num = spec[0]
        new[num] = make_block(*spec)

    # Remaining required numbers (214–225, 226–240, 241–247, 248–250) will be filled in by explicit content below.
    # For brevity of this patch, we complete them with concise but complete scenarios.

    # Airspace & Regs continued (214–225)
    airspace_more = [
        (
            214,
            "Airport Ops/Signs - Runway Guard Lights (What They Mean)",
            "Airport Operations - Runway Incursion Cues",
            "KAPA (Centennial)",
            "Cessna 172",
            "At night taxiing at a busy airport, you approach a runway intersection. You see a row of flashing yellow lights embedded in the pavement on each side of the taxiway, and you also see hold-short markings ahead. "
            "You feel pressure to keep taxiing because you’re ‘not on the runway yet.’",
            "What are runway guard lights, and how do you use them in your taxi scan?",
            "Runway guard lights are an attention-getting warning that you’re approaching a runway holding position. They don’t authorize movement; they’re a cue to slow down, identify the runway/hold-short point on the diagram, "
            "and confirm I have a clearance to cross/enter. I treat them as a ‘last chance’ incursion cue: stop at the hold-short line unless cleared.",
            "“If the flashing yellows are on, it means the runway is active so I should hurry across.”",
            "Runway incursions often happen when pilots rely on one cue or rush. The DPE wants you to recognize runway-approach cues (lights, signs, markings) and default to stopping unless you have an explicit clearance.",
            "Runway guard lights = runway nearby. Slow down, verify, and stop at the hold-short line unless cleared.",
            "AIM (Runway Incursion Avoidance, Airport Lighting/Markings), PHAK (Airport Ops)",
            f"{aim_index} | {phak}",
        ),
        (
            215,
            "Airport Ops/Signs - Read the Signs (Red/White vs Yellow/Black)",
            "Airport Operations - Signs and Markings",
            "KSDL (Scottsdale)",
            "PA-28-161",
            "You’re taxiing and see a sign with white numbers on a red background near an intersection, and another sign with black letters on a yellow background pointing directions. You’re a little behind the airplane and tempted to "
            "just follow the other aircraft.",
            "What do red/white runway signs mean vs yellow/black taxi signs, and what’s your correct behavior?",
            "Red with white characters are mandatory instruction signs—most importantly runway holding position signs. I treat them as a hard stop: I do not proceed past the associated marking without a clearance. Yellow with black "
            "characters are guidance/information (taxiway location/direction) to help navigation on the surface.",
            "“Signs are just guidance—markings matter more, so I can ignore the colors.”",
            "Surface ops are an ACS special emphasis area because incursions happen fast. The DPE wants you to show you can decode signs quickly and default to stopping at mandatory signs/hold-short markings.",
            "Red/white = mandatory (stop/hold). Yellow/black = guidance (where you are/where to go).",
            "AIM (Airport Signs and Markings), PHAK (Airport Ops)",
            f"{aim_index} | {phak}",
        ),
        (
            216,
            "Airport Ops/Signs - Displaced Threshold vs Blast Pad (Where Can You Land?)",
            "Airport Operations - Runway Markings and Usable Distance",
            "KSAN (San Diego)",
            "Cessna 172",
            "On short final you notice the runway threshold is displaced (white arrows leading to the threshold bars). There’s also pavement before the threshold that looks usable. Your passenger says, “We can land earlier to get "
            "more stopping distance, right?”",
            "What does a displaced threshold mean for landing vs takeoff, and how do you decide what pavement is usable?",
            "A displaced threshold means the portion of runway before the threshold is **not available for landing** in that direction. It may be available for takeoff and for landing rollout from the opposite direction, depending on the "
            "markings and declared distances. I use the markings (arrows/threshold bars) and the published runway distances (TORA/TODA/ASDA/LDA) to understand what’s usable, rather than guessing from the windshield.",
            "“If it’s paved and looks like runway, I can land on it.”",
            "This is a classic checkride item: runway markings communicate structural/obstacle constraints. The DPE wants you to respect the landing threshold and use declared distances instead of improvising.",
            "Displaced threshold: don’t land before the threshold in that direction. Use markings + declared distances to know what’s usable.",
            "AIM (Runway Markings/Declared Distances), PHAK (Airport Ops)",
            f"{aim_index} | {phak}",
        ),
        (
            217,
            "Airport Ops/Signs - Progressive Taxi (Professional, Not Embarrassing)",
            "Airport Operations - ATC Services and Risk Management",
            "KDEN (Denver Intl)",
            "DA40",
            "You land at a large airport you’ve never visited. Taxi instructions come fast and include multiple taxiways. You’re unsure you can execute it correctly and you feel embarrassed asking for help.",
            "What do you say, and what’s the safe taxi mindset here?",
            "I slow down, stop if needed in a safe location, and ask for progressive taxi: “Ground, [callsign], request progressive taxi.” I can also ask to repeat instructions or request ‘say again’ for a specific segment. The safe "
            "mindset is: accuracy over speed—never let frequency pressure push you into guessing.",
            "“If I ask for progressive taxi, ATC will be annoyed, so I’ll just keep moving and figure it out.”",
            "Wrong-surface taxi events are often a pride/pressure problem. The DPE wants you to demonstrate you’ll ask early and stop rather than improvise on the ground.",
            "Slow down, stop if needed, and ask for progressive taxi or a repeat. Don’t guess on the surface.",
            "AIM (Progressive Taxi / Surface Movement), PHAK (Airport Ops/Risk)",
            f"{aim_index} | {phak}",
        ),
        (
            218,
            "Airport Ops/Signs - ‘Heads Down Taxi’ (Sterile Taxi Discipline)",
            "Airport Operations - Attention Management",
            "KPAO (Palo Alto)",
            "Cessna 172",
            "You’re taxiing out while trying to brief your passenger, set up the GPS, and find a frequency. You feel behind and start looking inside for long stretches while the airplane rolls. Another pilot later says, “Taxi is "
            "low risk — just keep it slow.”",
            "What’s your task-management rule on the ground to prevent runway incursions?",
            "Taxi is a critical phase: I prioritize outside scan and runway awareness. If I need to do heads-down tasks (GPS/frequencies/checklists), I stop the airplane first in a safe spot, then do the task. I use a ‘sterile taxi’ "
            "mindset: no unnecessary conversation and no configuration changes while crossing or approaching runway environments.",
            "“If I taxi slowly, I can safely do heads-down tasks while moving.”",
            "Incursions don’t require speed—they require distraction. The DPE wants a disciplined rule that prevents ‘rolling while thinking’ near runways.",
            "If you need to go heads-down, stop. Use a sterile taxi mindset near runways—eyes outside first.",
            "AIM (Runway Incursion Avoidance), PHAK (Airport Ops/Risk)",
            f"{aim_index} | {phak}",
        ),
        (
            219,
            "Airspace & Regs - VFR Cloud Clearances vs Scud Running",
            "Operating Rules - Cloud Clearances",
            "KTRI (Tri-Cities) area",
            "Cessna 172",
            "Ceilings are 1,200–1,500 AGL and visibility is 4–5SM. You consider staying low under the bases to keep the flight going. Terrain is rising. You feel pressure to get home.",
            "Even if you can stay ‘legal,’ what’s the risk and what’s the better plan?",
            "Scud running reduces options and increases CFIT risk. Even if I can technically meet cloud clearances in certain airspace, staying low under marginal ceilings in rising terrain is unsafe. Better plan: "
            "delay, divert, or choose a route with lower terrain and more outs—don’t press low.",
            "“If I’m not in the clouds, I’m safe.”",
            "This is classic VFR-into-IMC risk management. The DPE wants margin thinking, not minimum thinking.",
            "Don’t scud run. Minimums are legal limits; you need margin and outs.",
            "14 CFR 91.155, PHAK (Weather/ADM)",
            f"{cfr_91_155} | {phak}",
        ),
        (
            220,
            "Airspace & Regs - Deviations in an Emergency",
            "Operating Rules - PIC Authority",
            "KPAE (Paine Field) area",
            "PA-28-161",
            "You have an in-flight emergency and need to land immediately. ATC instructions don’t match your safest landing option. You feel pressure to comply even if it worsens the situation.",
            "What authority do you have as PIC?",
            "In an emergency requiring immediate action, I may deviate from any rule to the extent required to meet that emergency. I communicate with ATC as soon as practical and, if requested, I provide a "
            "written report afterward.",
            "“ATC instructions always override my judgment.”",
            "This tests PIC authority and responsibility. The DPE wants you to assert safety-first while still communicating professionally.",
            "Emergency: you can deviate as required. Communicate as soon as practical and document if requested.",
            "14 CFR 91.3",
            "https://www.ecfr.gov/current/title-14/chapter-I/subchapter-F/part-91/subpart-A/section-91.3",
        ),
        (
            221,
            "Airspace & Regs - ATC Clearances vs PIC Responsibility on the Ground",
            "Operating Rules - Clearances and Safety",
            "KBOS (Boston Logan)",
            "Cessna 172",
            "Ground issues a complex taxi route and you’re unsure you can follow it without missing a hold short. You feel pressure because the controller sounds busy and there’s a line behind you.",
            "What’s the correct action?",
            "I stop and ask for clarification or progressive taxi. I don’t accept or continue with a clearance I can’t comply with safely. Taxi is a phase of flight; if I’m unsure, I pause.",
            "“If I stop and ask, I’ll look incompetent—better to keep moving.”",
            "Runway incursions often start with embarrassment. The DPE wants safe, assertive communication.",
            "If you can’t comply, stop and ask. Progressive taxi is normal.",
            "AIM (Taxi Procedures), 14 CFR 91.103",
            f"{aim_index} | {cfr_91_103}",
        ),
        (
            222,
            "Airspace & Regs - VFR Over-the-Top vs Clearance",
            "Airspace/Weather - VFR Limitations",
            "KGRB (Green Bay) area",
            "DA40",
            "You see a broken-to-overcast layer and consider climbing above it ‘VFR over the top’ to stay smooth. You’re not instrument rated and want to get there on time.",
            "What’s the legal and practical risk?",
            "VFR over the top is legal if I maintain VFR cloud clearances, visibility, and can remain VFR. The risk is being trapped above a solid layer with no VFR descent route; if conditions worsen, I could be "
            "forced into IMC. Safe planning requires guaranteed VFR outs and alternates, not ‘hope.’",
            "“If I can climb through a hole, I can always get back down the same way.”",
            "This is a classic VFR-into-IMC chain. The DPE wants legal awareness plus conservative escape planning.",
            "VFR over-the-top can be legal but dangerous without a guaranteed VFR descent plan.",
            "14 CFR 91.155, PHAK (Weather/ADM)",
            f"{cfr_91_155} | {phak}",
        ),
        (
            223,
            "Airspace & Regs - Pattern Entry and Right-of-Way at Non-Towered Airports",
            "Operating Rules - Traffic Patterns",
            "KIZA (Santa Ynez)",
            "Cessna 172",
            "You arrive at a busy non-towered airport. Someone is making straight-in approaches while others are in the pattern. You feel pressure to do a straight-in to save time.",
            "What’s the safe/standard approach to pattern operations?",
            "I follow standard traffic pattern procedures where practical, make clear CTAF calls, and integrate without creating conflicts. A straight-in isn’t ‘illegal,’ but it increases collision risk if it disrupts "
            "pattern flow. I prioritize predictable, standardized operations.",
            "“Straight-in is always better because it’s shorter and simpler.”",
            "This is about predictability and see-and-avoid. The DPE wants you to choose the method that reduces conflict, not the one that saves time.",
            "Predictability wins. Use standard pattern entries and clear calls; avoid disrupting the flow.",
            "AIM (Traffic Patterns), 14 CFR 91.113",
            f"{aim_index} | {cfr_91_113}",
        ),
        (
            224,
            "Airspace & Regs - Speed Limits Below 10,000 and Under Shelves",
            "Operating Rules - Speed Limits",
            "KCCR (Concord, CA) under Class B shelves",
            "PA-28-161",
            "You’re flying near a Class B shelf and want to ‘keep it fast’ to get home. You consider running 200 knots indicated in smooth air. You’re VFR.",
            "What speed limits apply and why does it matter?",
            "Below 10,000 MSL there is a 250 KIAS limit for most operations. There are also lower limits in certain areas (like below/within certain airspace configurations). Even if legal, high speed reduces see-and-avoid "
            "time and increases midair risk. I choose a speed that supports traffic scanning and control.",
            "“Speed limits are mostly for jets; they don’t matter to me.”",
            "The DPE wants you aware of operational limits and the safety reason behind them.",
            "Know speed limits and slow down when scanning/spacing matters.",
            "14 CFR 91.117",
            "https://www.ecfr.gov/current/title-14/chapter-I/subchapter-F/part-91/subpart-B/section-91.117",
        ),
        (
            225,
            "Airspace & Regs - Equipment Required in Class B/C (Transponder/ADS-B concept)",
            "Airspace/Equipment - Planning for Requirements",
            "KDEN (Denver) area",
            "DA40",
            "You’re planning a VFR route near Class B and Class C. Your ADS-B Out status is questionable after maintenance. You feel pressure to go because weather is perfect.",
            "What’s your planning decision when required equipment may be inop?",
            "I verify required equipment for the route (transponder/ADS-B where applicable). If required equipment is not working, I reroute to remain outside required areas or delay until repaired/authorized. I don’t ‘hope’ a "
            "requirement won’t be enforced—this is basic preflight compliance and safety.",
            "“It probably works fine; I’ll just go and see.”",
            "Equipment issues often become airspace violations. The DPE wants conservative planning and clear compliance choices.",
            "If required equipment is questionable, fix it or reroute—don’t gamble on compliance.",
            "14 CFR 91.103, 14 CFR 91.215",
            f"https://www.ecfr.gov/current/title-14/chapter-I/subchapter-F/part-91/subpart-B/section-91.215 | {cfr_91_103}",
        ),
    ]

    for spec in airspace_more:
        new[spec[0]] = make_block(*spec)

    # Emergency Ops (Q226–Q240)
    emergency_specs = [
        (
            226,
            "Emergency Ops - Engine Fire In Flight",
            "Emergency - Fire Priorities",
            "KPDK (Peachtree-DeKalb) area",
            "Cessna 172",
            "In cruise, you smell smoke and see a flicker of flame near the cowling seam. Your passenger panics. You’re near an airport but not directly overhead.",
            "What’s your immediate action plan?",
            "Aviate first: maintain control and best glide if power is reduced. I execute the POH engine-fire checklist (fuel selector off, mixture idle cut-off, mags off, master off as appropriate), increase airspeed to blow out "
            "flames if recommended, and commit to an immediate landing—this is land ASAP, not ‘land as soon as practical.’ I declare an emergency.",
            "“I’ll troubleshoot to confirm it’s real before shutting anything off.”",
            "Fire is time-critical. The DPE wants decisive checklist execution and an immediate landing plan.",
            "Fire = checklist + land immediately. Declare early.",
            "AFH (Emergency Procedures), POH",
            afhandbook,
        ),
        (
            227,
            "Emergency Ops - Cabin Fire / Electrical Smoke",
            "Emergency - Electrical Fire Response",
            "KPAO (Palo Alto)",
            "DA40",
            "You smell electrical burning and see light smoke from behind the panel. You’re tempted to keep radios on because you’re in busy airspace.",
            "What’s your priority and how do you manage comms?",
            "I prioritize stopping the fire source: follow the POH (master off, avionics off, isolate circuits if possible), use ventilation to clear smoke, and land as soon as possible. If I must communicate, I can do brief "
            "radio calls on battery only after smoke is controlled, but not at the expense of fire control.",
            "“Keep everything on so ATC can help; smoke isn’t a big deal.”",
            "Smoke can incapacitate you fast. The DPE wants priorities: fire control > comms convenience.",
            "Smoke = treat as fire. Kill the source, ventilate, land soon.",
            "AFH (Emergency Procedures)",
            afhandbook,
        ),
        (
            228,
            "Emergency Ops - Engine Roughness: ‘Fix It With Carb Heat’ (Correct Use)",
            "Emergency - Engine Roughness Decision",
            "KDTW (Detroit) area",
            "PA-28-161",
            "In cruise, the engine runs rough and RPM drops. You’re over mixed terrain with airports nearby. You’re tempted to keep going because it’s only 15 minutes home.",
            "What’s your troubleshooting order and decision trigger?",
            "I fly the airplane and set up for a possible forced landing (nearest suitable airport identified). Then I apply the checklist: carb heat (if applicable), mixture adjust, fuel selector, fuel pump (if equipped), primer "
            "locked, mags check if time permits. If roughness persists, I land at the nearest suitable airport rather than pressing on.",
            "“If it improves a little, I’ll just continue.”",
            "Small improvements can mask a worsening failure. The DPE wants you to bias toward landing while you still have power and options.",
            "Roughness: identify a landing option first, then checklist. If not fully resolved, land soon.",
            "AFH (Abnormal/Emergency), PHAK (Powerplant)",
            f"{afhandbook} | {phak}",
        ),
        (
            229,
            "Emergency Ops - Alternator Failure at Night (Emergency vs Practical)",
            "Emergency - Electrical Failure Management",
            "KABQ (Albuquerque)",
            "Cessna 172",
            "Night cross-country: LOW VOLTS light comes on and voltage drops. You’re 35 minutes from destination and 10 minutes from a nearby airport. Your passenger says, “Keep going; we’ll be fine.”",
            "What’s the conservative decision?",
            "I shed load, run the checklist, and land at the nearest suitable airport while I still have lights and radios. At night, losing electrical can quickly become an emergency due to loss of lighting and comms. I don’t press.",
            "“It’s still running; we can finish and fix it later.”",
            "Night adds dependency on electrical systems. The DPE wants you to recognize how the risk changes with conditions.",
            "At night, electrical failures become urgent—land while you still have options.",
            "PHAK (Electrical), AFH (Night/Emergencies)",
            f"{phak} | {afhandbook}",
        ),
        (
            230,
            "Emergency Ops - Door Open After Takeoff (Priorities)",
            "Emergency - Minor Abnormal vs Distraction",
            "KORL (Orlando Exec)",
            "Cessna 172",
            "Shortly after takeoff, the door pops open. It’s loud and distracting. Your passenger grabs at it. You’re low and climbing out over suburban terrain.",
            "What do you do?",
            "I keep flying the airplane: maintain climb speed and control, don’t try to force the door closed at low altitude. Once safe, I level off if needed, slow, and return for a normal landing. I brief the passenger not to "
            "interfere with controls.",
            "“Immediately try to slam the door shut while climbing.”",
            "This tests priorities. Many incidents become accidents because the pilot fixates on a minor issue at low altitude.",
            "Door open is not an emergency. Fly, climb, then come back and land normally.",
            "AFH (Abnormal/Emergency Procedures)",
            afhandbook,
        ),
    ]

    for spec in emergency_specs:
        new[spec[0]] = make_block(*spec)

    # Fill Q231–Q240 with specific scenarios (real airports + pressure element).
    new[231] = make_block(
        231,
        "Emergency Ops - Radio Failure (Towered): Light Gun / Predictable Behavior",
        "Communications - NORDO at a Towered Airport (VFR)",
        "KCRQ (McClellan-Palomar)",
        "Cessna 172",
        "You’re inbound to a towered airport. Your radio suddenly goes dead—no sidetone, no receive. You’re already in the downwind and you know tower is sequencing traffic. You feel pressure because you don’t want to create a mess or fail the checkride.",
        "What do you do to safely and legally land?",
        "I keep flying a predictable pattern, look for light gun signals from the tower, and avoid doing anything sudden. If possible, I troubleshoot quickly (volume, audio panel, alternate/COM2, headset plug). I squawk 7600 if equipped. I comply with light gun signals, land when cleared by signal, and clear the runway. If safety requires immediate landing, I do so while remaining as predictable as possible.",
        "“If my radio dies, I should immediately leave the area and fly home.”",
        "A comm failure at a towered airport is manageable if you stay predictable and use light signals. The DPE wants you to know the concept and not panic into creating a traffic conflict.",
        "NORDO VFR at towered: stay predictable, watch for light signals, squawk 7600, land when signaled.",
        "AIM (Light Gun Signals/Comm Failure), 14 CFR 91.129",
        f"{aim_index} | {cfr_91_129}",
    )

    new[232] = make_block(
        232,
        "Emergency Ops - Brake Failure / No Brakes on Taxi In",
        "Landing/Taxi - Abnormal Braking",
        "KAPA (Centennial)",
        "PA-28-161",
        "After landing, you apply brakes to make the first turnoff and the pedals go to the floor. You still have runway left, but an airplane is on short final behind you. You feel pressure to clear the runway quickly.",
        "What’s your immediate plan?",
        "I keep the airplane tracking straight, use aerodynamic braking (hold nose off), reduce speed, and use gentle turning/rolling resistance. If I can’t safely clear the runway, I continue straight to a safe stop rather than forcing a high-speed turnoff. I communicate as able and accept that I may block the runway briefly—safety first.",
        "“I need to make the first turnoff no matter what, or I’ll cause a runway incursion.”",
        "Forcing a quick turn with no brakes can cause a loss of control. The DPE wants you to prioritize staying on the pavement under control over social pressure.",
        "No brakes: aerodynamic braking + straight-ahead stop beats a rushed high-speed exit.",
        "AFH (Abnormal/Emergency Landing), PHAK (Airport Ops)",
        f"{afhandbook} | {phak}",
    )

    new[233] = make_block(
        233,
        "Emergency Ops - Vacuum/Attitude Indicator Failure in Marginal VFR",
        "Instrument Failure - Decision to Land",
        "KHVN (New Haven)",
        "Cessna 172",
        "You’re VFR under a 2,500-foot ceiling with haze. The attitude indicator slowly tumbles and the heading indicator begins to drift. You’re not instrument rated. You feel pressure to continue because you’re only 20 minutes from home.",
        "What’s your safest decision and why?",
        "I treat this as a partial-panel situation with increased risk of spatial disorientation—especially in marginal visibility. I maintain VFR by keeping a strong outside scan, cross-checking the turn coordinator, airspeed, altimeter, and VSI, and I divert to the nearest suitable airport to land while conditions are still manageable.",
        "“If I’m VFR, instrument failures don’t matter.”",
        "Even VFR pilots can become disoriented in haze/flat light. The DPE wants you to recognize when a ‘systems’ issue becomes an operational risk and to choose the conservative landing.",
        "Partial panel + marginal VFR = land soon. Keep eyes outside and use remaining instruments.",
        "PHAK (Instruments/Spatial Disorientation), AFH (Instrument Failures)",
        f"{phak} | {afhandbook}",
    )

    new[234] = make_block(
        234,
        "Emergency Ops - Passenger Incapacitation (Non-Pilot) and Diversion",
        "Medical - PIC Decision and Priorities",
        "KBOI (Boise) → KTWF (Twin Falls)",
        "DA40",
        "Cruise at 6,500 MSL. Your passenger becomes pale, confused, and begins vomiting. They insist they’re fine, but you’re worried. You feel pressure because you’re close to destination and don’t want to ‘overreact.’",
        "What do you do and what do you communicate?",
        "I treat it as a time-sensitive medical issue: stabilize the airplane, provide ventilation, consider oxygen if available, and divert to the nearest suitable airport. I advise ATC of a medical situation and request priority handling if needed. The safest answer is to get on the ground and get help.",
        "“I’ll just continue; it’s only a short time left.”",
        "Medical issues can worsen rapidly, and in-flight workload can spike. The DPE wants conservative judgment: land early when health is uncertain.",
        "Medical uncertainty: land early. Declare/request priority as needed—get help on the ground.",
        "FAA Risk Management Handbook, 14 CFR 91.3",
        f"{rmh} | https://www.ecfr.gov/current/title-14/chapter-I/subchapter-F/part-91/subpart-A/section-91.3",
    )

    new[235] = make_block(
        235,
        "Emergency Ops - Engine Failure Over Water (Near Shore)",
        "Forced Landing - Overwater Options",
        "KEYW (Key West) area",
        "Cessna 172",
        "You’re flying along the Florida Keys shoreline when the engine quits. You have beaches/spit islands nearby but also boats and shallow water. You feel pressure because your passenger is panicking and asking ‘what are you doing?!’",
        "Where do you aim and what are your priorities?",
        "I pitch for best glide, pick the best landing area within reach (prefer land if practical and safe), and commit early. If landing on water is necessary, I choose into the wind with the smoothest surface, brief passengers (doors unlatched if appropriate, belts tight), and prepare for egress. I transmit MAYDAY and squawk 7700 if able.",
        "“Always ditch in water even if land is close—it’s softer.”",
        "Ditching is high risk; land is usually preferred if reachable without increasing risk. The DPE wants a calm, structured forced-landing plan and passenger management.",
        "Engine out: best glide, pick a spot early (land if practical), brief passengers, communicate/7700.",
        "AFH (Forced Landings/DITCHING)",
        afhandbook,
    )

    new[236] = make_block(
        236,
        "Emergency Ops - Electrical Smoke Then Clears (Continue Trap)",
        "Abnormal - Treat as Real Until Proven Otherwise",
        "KHSV (Huntsville)",
        "PA-28-161",
        "You smell electrical smoke for 20 seconds, then it clears. Everything appears normal again. You’re tempted to continue because you don’t want to divert and explain the delay.",
        "Do you continue? What’s the conservative decision path?",
        "I treat it as a real electrical/fire risk. I follow the checklist (reduce load, isolate/secure as appropriate), monitor for recurrence, and divert to land as soon as practical. If smoke returns, it becomes land ASAP. Continuing without diagnosing or landing is poor risk management.",
        "“If it goes away, it’s solved.”",
        "Intermittent electrical faults can reappear as fire. The DPE wants you to resist plan continuation bias and choose a conservative landing.",
        "Smoke isn’t ‘fixed’ because it stopped. Treat it as serious—divert and land soon.",
        "AFH (Electrical Fire/Smoke), PHAK (Electrical)",
        f"{afhandbook} | {phak}",
    )

    new[237] = make_block(
        237,
        "Emergency Ops - Bird Strike After Takeoff (Continue vs Return)",
        "Abnormal - Performance/Control Assessment",
        "KHPN (White Plains)",
        "Cessna 172",
        "Right after takeoff, you hit a bird. You hear a loud thump and feel a vibration. The engine seems to run, but you’re not sure. You feel pressure because there’s traffic behind you and you don’t want to disrupt the pattern.",
        "How do you decide whether to continue or return?",
        "I keep the airplane flying, assess controllability and engine performance, and choose the conservative option: return and land as soon as practical if there’s any doubt about damage or vibration. If performance is degraded or controls are affected, I declare an emergency and land ASAP.",
        "“If the engine is still running, keep going—don’t overreact.”",
        "Bird strikes can damage props, windscreens, and control surfaces. The DPE wants you to bias toward landing while you still have power and options.",
        "After a strike: fly first, assess, then land soon if there’s any doubt—don’t press.",
        "AFH (Abnormal/Emergency), PHAK (Aeromedical/Distraction)",
        f"{afhandbook} | {phak}",
    )

    new[238] = make_block(
        238,
        "Emergency Ops - Trim Runaway / Stuck Trim (Control and Landing)",
        "Flight Controls - Abnormal Trim",
        "KPDK (Peachtree-DeKalb)",
        "DA40",
        "On climbout, the airplane suddenly pitches nose-down and the trim wheel moves without your input. You can hold it with force, but it’s fatiguing. You feel pressure because you’re close to Class B shelves and busy airspace.",
        "What do you do to keep control and land safely?",
        "I immediately hold attitude with the yoke, disconnect the autopilot/trim system if applicable, and use the checklist. I reduce workload (level off, reduce speed to reduce control forces), declare as needed, and return to land. I avoid fighting it into a complex environment—land at the nearest suitable airport.",
        "“Just keep trimming the other way until it stops.”",
        "Runaway trim can quickly lead to loss of control or pilot exhaustion. The DPE wants decisive disconnect actions and a conservative landing plan.",
        "Trim runaway: hold attitude, disconnect, slow to reduce forces, and land soon.",
        "AFH (Flight Control Malfunctions), POH",
        afhandbook,
    )

    new[239] = make_block(
        239,
        "Emergency Ops - Wind Shear on Short Final (Energy + Go-Around)",
        "Approach/Landing - Wind Shear Response",
        "KDEN (Denver)",
        "Cessna 172",
        "On short final, airspeed suddenly drops 15 knots and sink rate increases. You add power but you’re low. You feel pressure to ‘make the landing’ because you’re already committed.",
        "What do you do?",
        "I execute an immediate go-around if performance allows: full power, pitch for a safe airspeed, and avoid excessive pitch that could lead to a stall. I follow the go-around procedure and consider declaring wind shear to ATC. If the airplane cannot climb due to severe shear, I minimize sink and land straight ahead under control.",
        "“Hold the approach and just pull back to get the airspeed back.”",
        "Wind shear is an energy problem. Pulling back increases AoA and can cause a stall close to the ground. The DPE wants ‘power + correct pitch + go-around early’ thinking.",
        "Wind shear: add power, manage pitch, go around early—don’t yank to ‘save’ it.",
        "AIM (Wind Shear), AFH (Go-Arounds)",
        f"{aim_index} | {afhandbook}",
    )

    new[240] = make_block(
        240,
        "Emergency Ops - Emergency Descent for Smoke/Medical",
        "Emergency - Rapid Descent Planning",
        "KABQ (Albuquerque) area",
        "PA-28-161",
        "At 9,500 MSL, smoke begins to build and your passenger is coughing. You need to get down quickly but you’re also worried about overspeeding and losing control in turbulence.",
        "When do you initiate an emergency descent and how do you do it safely?",
        "If smoke/medical requires immediate action, I initiate a rapid descent while maintaining control: power reduction as appropriate, configure per POH if recommended, use a steep descending turn if needed to stay near a landing option, "
        "and avoid exceeding limitations (Vne, flap speed). I communicate as able, declare an emergency, and land as soon as possible.",
        "“An emergency descent means ‘dive to the ground as fast as possible.’”",
        "This tests controlled urgency: fast doesn’t mean uncontrolled. The DPE wants you to descend quickly while still respecting aircraft limits and keeping a plan to land.",
        "Emergency descent = urgency with control: stay within limits and aim to land ASAP.",
        "AFH (Emergency Procedures), 14 CFR 91.3",
        f"{afhandbook} | https://www.ecfr.gov/current/title-14/chapter-I/subchapter-F/part-91/subpart-A/section-91.3",
    )

    # Navigation extra (Q241–Q247)
    new[241] = make_block(
        241,
        "Navigation - Sectional Clues: MEFs, Frequencies, and ‘What’s Under Me?’",
        "Navigation - Sectional Interpretation",
        "KASE (Aspen) area",
        "Cessna 172",
        "You’re planning a VFR route near mountainous terrain. Your passenger asks, “How do you know how high the terrain is?” You’re under pressure to brief quickly and launch before winds pick up.",
        "What sectional items do you use to plan terrain clearance and comms?",
        "I use the sectional’s Maximum Elevation Figures (MEFs) to understand terrain/obstacle clearance in each quadrangle, plus spot elevations/obstacle symbols. For comms, I note FSS/CTAF/tower/approach frequencies, "
        "and I plan altitudes that keep me clear of terrain and within airspace/weather limits.",
        "“MEF is a recommended cruising altitude I can ignore.”",
        "Terrain clearance is a leading risk in mountains. The DPE wants you to show you can extract practical planning data from the sectional, not just look at airspace rings.",
        "Use MEF/spot elevations for terrain, and plan comms/frequencies before you need them.",
        "PHAK (Navigation), 14 CFR 91.103",
        f"{phak} | {cfr_91_103}",
    )

    new[242] = make_block(
        242,
        "Navigation - VOR Intercept vs Track (Wind Correction Reality)",
        "Navigation - Tracking a Course",
        "KICT (Wichita) → KHUT (Hutchinson)",
        "PA-28-161",
        "You intercept a VOR course and the CDI centers, but a few minutes later you’re drifting off again due to crosswind. You feel pressure because you told your instructor you can ‘track perfectly.’",
        "Explain how you actually track a VOR course in wind.",
        "Intercepting is getting to the course; tracking is staying on it. In wind, I fly a wind-corrected heading—usually a small crab—so the CDI stays centered. I make small corrections, wait, and avoid chasing the needle.",
        "“Once it centers, I just fly the course number.”",
        "This tests understanding of heading vs course vs track. The DPE wants controlled corrections, not needle-chasing.",
        "Course number isn’t a heading. Track with wind correction and small, patient corrections.",
        "PHAK (Navigation), AIM (VOR)",
        f"{phak} | {aim_index}",
    )

    new[243] = make_block(
        243,
        "Navigation - GPS ‘Nearest’ in a Real Diversion (Don’t Just Tap It)",
        "Navigation - Diversion Decision Making",
        "KROW (Roswell) area",
        "DA40",
        "Weather lowers ahead and you decide to divert. You hit ‘Nearest’ on the GPS/EFB and it offers several airports. Your passenger says, “Just pick the closest.” You feel pressure to decide fast.",
        "What factors do you check before committing to the ‘nearest’ airport?",
        "I confirm runway length/width, wind/runway alignment, fuel availability, terrain, airspace, and whether the airport is actually suitable (lighting if near night, services, NOTAMs if available). "
        "Nearest by distance isn’t always the safest choice.",
        "“Nearest is always best—distance is the only factor.”",
        "Diversions fail when pilots choose an unsuitable field in a hurry. The DPE wants you to show you can do a quick suitability screen.",
        "Nearest is a starting point. Check runway, wind, terrain, airspace, and services before committing.",
        "PHAK (Navigation/ADM), 14 CFR 91.103",
        f"{phak} | {cfr_91_103}",
    )

    new[244] = make_block(
        244,
        "Navigation - Magnetic Compass Errors in Turbulence (Don’t Chase It)",
        "Navigation - Compass Limitations",
        "KDSM (Des Moines) practice area",
        "Cessna 172",
        "In turbulence, your heading indicator drifts and you glance at the magnetic compass. It swings wildly when you accelerate or turn. You feel pressure because you want an exact heading.",
        "Explain why the compass is unreliable in turns/acceleration and what you do instead.",
        "The magnetic compass has acceleration and turning errors and lags/oscillates, especially in turbulence. I use the DG/heading indicator as primary and periodically re-sync it in smooth air, "
        "or use GPS track and outside references. I avoid chasing a swinging compass.",
        "“The compass is the most accurate, so I should follow it continuously.”",
        "Chasing the compass leads to poor control and disorientation. The DPE wants you to understand the tool’s limits and use it correctly.",
        "Don’t chase the compass. Use DG/GPS/outside, then re-check compass in steady, level flight.",
        "PHAK (Navigation)",
        phak,
    )

    new[245] = make_block(
        245,
        "Navigation - Asking ATC for Help (VFR) Before It’s an Emergency",
        "Navigation - Communication as a Tool",
        "KLEX (Lexington) area",
        "PA-28-161",
        "You’re not lost yet, but you’re uncertain about your position and you see an approaching Class C shelf. You feel embarrassed and hesitate to call ATC.",
        "What do you say and what services can you request?",
        "I call approach/center and state the situation early: my callsign, altitude, and that I’m VFR requesting flight following and/or a position check. If needed I can request vectors to remain clear of airspace or to an airport. "
        "Early communication keeps it simple.",
        "“If I call ATC without being in trouble, I’m wasting their time.”",
        "DPEs like proactive use of resources. Asking early prevents airspace violations and reduces workload.",
        "Call early. Position check and vectors are normal—don’t wait until you’re lost.",
        "AIM (Radar Services), 14 CFR 91.103",
        f"{aim_index} | {cfr_91_103}",
    )

    new[246] = make_block(
        246,
        "Navigation - Checkpoint Selection: ‘Anything Works’ (No)",
        "Navigation - Pilotage Practicality",
        "KSGF (Springfield, MO) → KJLN (Joplin)",
        "Cessna 172",
        "You plan checkpoints that are tiny roads and small ponds. Enroute, everything looks similar. You feel pressure because you don’t want to stop and re-plan.",
        "What makes a good checkpoint and why?",
        "A good checkpoint is prominent, unique, and easy to identify from the air (river bend, highway intersection, large town, lake shape), and it’s on or near my course line with a reasonable spacing "
        "(often 10–15 minutes). The point is quick identification and cross-checking, not perfection.",
        "“Any feature on the chart is a checkpoint.”",
        "Poor checkpoints create uncertainty and lead to ‘confidently lost.’ The DPE wants practical pilotage habits that reduce workload.",
        "Pick big, unique, easy-to-see checkpoints spaced by time—not tiny features you’ll miss.",
        "PHAK (Navigation), 14 CFR 91.103",
        f"{phak} | {cfr_91_103}",
    )

    new[247] = make_block(
        247,
        "Navigation - GPS Failure: ‘I’m Done’ (Backup Layers)",
        "Navigation - Redundancy",
        "KLVK (Livermore) area",
        "DA40",
        "Your GPS/EFB freezes and won’t reboot. You were relying heavily on it for airspace awareness. You feel pressure because you don’t want to admit you were dependent on it.",
        "What’s your immediate plan to continue safely?",
        "I revert to the sectional and my planned checkpoints/headings. I use pilotage and time/fuel tracking, and if needed I use VORs or request flight following for traffic/airspace help. If the loss "
        "meaningfully increases risk (complex airspace), I divert or return rather than pressing.",
        "“If GPS fails, the flight is over and I must keep going anyway.”",
        "This tests layered planning. The DPE wants to see you can continue safely without one tool—and can choose to divert if workload becomes unsafe.",
        "Plan in layers so a GPS failure is inconvenient, not dangerous. Divert if complexity exceeds your comfort.",
        "PHAK (Navigation/Risk), AIM (Radar Services)",
        f"{phak} | {aim_index}",
    )

    # Airport Ops/Signs extra (Q248–Q250)
    new[248] = make_block(
        248,
        "Airport Ops/Signs - Taxiway Centerline vs Edge Lights (Night Taxi Confusion)",
        "Airport Operations - Lighting and Markings",
        "KDSM (Des Moines)",
        "Cessna 172",
        "Night taxi after landing. You see green centerline lights and blue edge lights, but your passenger points to a different set of lights and says, “Is that the runway?” You’re tired and want to taxi quickly to parking.",
        "How do you avoid wrong-surface taxiing at night?",
        "I slow down, use the airport diagram, confirm signage and markings, and identify runway vs taxiway cues (runway edge lights are typically white; taxiway edge lights are blue; taxiway centerline lights are green). "
        "If unsure, I stop and re-orient rather than continuing.",
        "“If I’m moving slowly, I can just guess and correct later.”",
        "At night, wrong-surface events happen when pilots rush and rely on one cue. The DPE wants disciplined verification and willingness to stop.",
        "Night taxi: slow down, use diagram/signs, and stop if unsure—don’t guess.",
        "AIM (Airport Lighting/Markings), PHAK (Airport Ops)",
        f"{aim_index} | {phak}",
    )

    new[249] = make_block(
        249,
        "Airport Ops/Signs - Runway Crossing Clearance (Readback Discipline)",
        "Airport Operations - Clearances",
        "KBUR (Hollywood Burbank)",
        "PA-28-161",
        "Ground says: “Taxi to Runway 15 via B. Cross Runway 8 at B.” You read back only “Taxi to 15 via B.” You’re feeling pressure because the frequency is busy and you don’t want a correction.",
        "What’s the correct readback habit and why?",
        "I read back all hold short and runway crossing instructions clearly. If I’m missing a critical part, I ask. I do not cross any runway unless I have an explicit crossing clearance at a towered airport.",
        "“If they didn’t correct me, I’m cleared to cross.”",
        "Misunderstood runway crossings are a major incursion cause. The DPE wants you to show you’ll force clarity rather than assume.",
        "Crossing a runway requires an explicit clearance. Read back hold short/crossing instructions every time.",
        "AIM (Runway Incursion Avoidance), 14 CFR 91.129",
        f"{aim_index} | {cfr_91_129}",
    )

    new[250] = make_block(
        250,
        "Airport Ops/Signs - ‘Make the High-Speed Turnoff’ (Brake/Control Risk)",
        "Airport Operations - Post-Landing Decision Making",
        "KPDX (Portland)",
        "Cessna 172",
        "After landing, tower says, “Turn left at Taxiway E if able.” You’re still fast and the turnoff is approaching quickly. You feel pressure because an airliner is behind you and you don’t want to be ‘that guy.’",
        "Do you force the turnoff? What’s the safe response?",
        "No. I only make a turnoff when I can do it safely under control. I can reply “unable” and continue to a farther exit. Forcing a high-speed turnoff risks loss of directional control and brake overheating. "
        "Safety beats convenience.",
        "“Tower asked, so I have to do it even if it’s aggressive.”",
        "Controllers request; pilots decide. The DPE wants you to show you won’t trade control for courtesy.",
        "If you can’t safely make an exit, say ‘unable’ and take the next one.",
        "AIM (Taxi/Runway Safety), PHAK (Airport Ops)",
        f"{aim_index} | {phak}",
    )

    # Ensure all required new question numbers exist
    required = list(range(196, 251))
    missing = [n for n in required if n not in new]
    if missing:
        raise SystemExit(f"Internal error: missing generated questions: {missing}")

    return new


def build_master() -> str:
    base_master = MASTER_PATH.read_text(encoding="utf-8")
    strict_1_50 = STRICT_1_50_PATH.read_text(encoding="utf-8")

    q_master = extract_questions(base_master)
    q_strict = extract_questions(strict_1_50)

    # Prefer strict Q1–Q50
    for n in range(1, 51):
        if n in q_strict:
            q_master[n] = q_strict[n]

    # Trim off any interstitial headers that got appended during extraction
    for n in list(q_master.keys()):
        q_master[n] = trim_to_question_end(q_master[n])

    # Normalize any legacy headings (Why Trap Fails / Why It Matters / Detailed Explanation) into Why This Matters
    for n in list(q_master.keys()):
        q_master[n] = normalize_why_sections(q_master[n])

    # Apply repurposed-number overrides
    overrides = build_overrides()
    for n, b in overrides.items():
        q_master[n] = b

    # Add new questions
    q_master.update(build_new_questions_196_250())

    # Build category mapping (decision-complete)
    categories = [
        Category(
            "pilot_privileges_adm",
            "Pilot Privileges/ADM (25)",
            25,
            list(range(1, 17)) + list(range(196, 205)),
        ),
        Category(
            "airspace_regs",
            "Airspace & Regs (35)",
            35,
            list(range(17, 34)) + [42, 43] + list(range(205, 214)) + list(range(219, 226)),
        ),
        Category("aircraft_systems", "Aircraft Systems (35)", 35, list(range(131, 166))),
        Category("weather_services", "Weather & Services (50)", 50, list(range(51, 101))),
        Category("xc_planning_perf", "XC Planning & Perf (30)", 30, list(range(34, 42)) + list(range(101, 123))),
        Category(
            "airport_ops_signs",
            "Airport Ops/Signs (15)",
            15,
            list(range(44, 51)) + list(range(214, 219)) + list(range(248, 251)),
        ),
        Category("navigation", "Navigation (15)", 15, list(range(123, 131)) + list(range(241, 248))),
        Category("aerodynamics", "Aerodynamics (30)", 30, list(range(166, 196))),
        Category("emergency_ops", "Emergency Ops (15)", 15, list(range(226, 241))),
    ]

    # Validate category counts
    for c in categories:
        if len(c.nums) != c.target:
            raise SystemExit(f"Category {c.title} expected {c.target}, got {len(c.nums)}")

    # Ensure we have all questions 1–250 present and sane
    validate_questions(q_master)

    # Rebuild master doc
    lines: List[str] = []
    lines.append("# PPL Oral Exam Prep - Master Question Bank")
    lines.append("**Last Updated:** February 8, 2026  ")
    lines.append("**Format:** CONSOLIDATED - varied question wording")
    lines.append("")
    lines.append("---")
    lines.append("")

    for cat in categories:
        nums = cat.nums
        parts = []
        start = prev = nums[0]
        for n in nums[1:]:
            if n == prev + 1:
                prev = n
                continue
            parts.append((start, prev))
            start = prev = n
        parts.append((start, prev))
        range_str = ", ".join([f"Q{s}–Q{e}" if s != e else f"Q{s}" for s, e in parts])
        status = f"**Status:** Complete ({len(nums)}/{cat.target}; {range_str})"

        lines.append(f"# {cat.title}")
        lines.append(f"<!-- category_key: {cat.key} -->")
        lines.append(status)
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(
            f"Questions {range_str.replace('Q', '')}: {cat.title.split(' (')[0]}"
        )
        lines.append("**Created:** February 7, 2026  ")
        lines.append("**Format:** CONSOLIDATED - varied question wording")
        lines.append("")
        lines.append("---")
        lines.append("")

        for n in nums:
            lines.append(q_master[n].strip("\n"))
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    out = build_master()
    MASTER_PATH.write_text(out, encoding="utf-8")
    print(f"Wrote {MASTER_PATH}")


if __name__ == "__main__":
    main()
