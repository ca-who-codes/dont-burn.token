#!/usr/bin/env python3
"""
Mine session logs for behavioral corrections and distill them into CLAUDE.md.

Inspired by headroom's `headroom learn` — finds patterns where the AI wasted
tokens (repeated reads, verbose responses, missed compressions) and converts
them into explicit rules.

Usage:
    # Analyze a session log file
    python session/learn.py path/to/session.jsonl

    # Analyze text from stdin (paste conversation excerpts)
    python session/learn.py -

    # Distill accumulated corrections/rules into CLAUDE.md appendix
    python session/learn.py --distill
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent.parent
CORRECTIONS_FILE = ROOT / "session" / "corrections.md"
CLAUDE_MD = ROOT / "CLAUDE.md"


# ── Waste patterns ────────────────────────────────────────────────────────────

WASTE_PATTERNS = [
    (r"(Sure|Of course|Great|Absolutely|Certainly)[,!]", "preamble"),
    (r"Let me (help|assist|look|check|read|go|now)", "preamble"),
    (r"I (have|will|can|am going to)", "preamble"),
    (r"I've (updated|changed|modified|added|removed|fixed)", "trailing_summary"),
    (r"I (made|applied|completed|implemented) the (change|fix|update)", "trailing_summary"),
    (r"To summarize|In summary|In conclusion", "trailing_summary"),
    (r"(That|This) (should|will) (work|do it|fix|resolve)", "trailing_summary"),
    (r"Let me know if you (have|need|want)", "trailing_cta"),
    (r"Feel free to ask", "trailing_cta"),
    (r"Is there anything else", "trailing_cta"),
    (r"Hope this helps", "trailing_cta"),
]

WASTE_RULES = {
    "preamble": "Never open a response with affirmations or 'Let me...' phrases. Start with the answer.",
    "trailing_summary": "Never summarize what you just did. The user can read the diff.",
    "trailing_cta": "Never end with 'Let me know if you need anything.' Stop when the task is done.",
}


# ── Token waste estimator ─────────────────────────────────────────────────────

def estimate_tokens(text: str) -> int:
    return len(text) // 4


def analyze_text(text: str) -> dict:
    findings = []
    total_waste_tokens = 0

    for pattern, waste_type in WASTE_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            waste = sum(estimate_tokens(m if isinstance(m, str) else " ".join(m)) for m in matches)
            total_waste_tokens += waste
            findings.append({
                "type": waste_type,
                "count": len(matches),
                "examples": matches[:3],
                "rule": WASTE_RULES[waste_type],
                "approx_tokens_wasted": waste,
            })

    # Detect repeated file reads (in JSONL sessions)
    return {"findings": findings, "total_waste_tokens": total_waste_tokens}


# ── JSONL session analysis ─────────────────────────────────────────────────────

def analyze_jsonl(path: Path) -> dict:
    reads = Counter()
    tool_output_sizes = []
    response_sizes = []
    findings = []

    with open(path) as f:
        for line in f:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Count file reads
            if entry.get("type") == "tool_use" and entry.get("name") == "Read":
                file_path = entry.get("input", {}).get("file_path", "")
                if file_path:
                    reads[file_path] += 1

            # Measure tool output sizes
            if entry.get("type") == "tool_result":
                content = str(entry.get("content", ""))
                size = estimate_tokens(content)
                tool_output_sizes.append(size)

            # Measure response sizes
            if entry.get("type") == "text":
                content = str(entry.get("text", ""))
                response_sizes.append(estimate_tokens(content))
                text_findings = analyze_text(content)
                findings.extend(text_findings["findings"])

    # Repeated reads → cache miss
    for file_path, count in reads.items():
        if count > 1:
            findings.append({
                "type": "repeated_read",
                "count": count,
                "file": file_path,
                "rule": f"Read `{file_path}` was called {count}× in one session. Store the relevant excerpt in context instead of re-reading.",
                "approx_tokens_wasted": estimate_tokens(Path(file_path).read_text()) * (count - 1) if Path(file_path).exists() else 0,
            })

    # Large tool outputs → should have been compressed
    large_outputs = [(i, s) for i, s in enumerate(tool_output_sizes) if s > 2000]
    for idx, size in large_outputs:
        findings.append({
            "type": "large_tool_output",
            "size_tokens": size,
            "rule": f"Tool output #{idx} was ~{size} tokens. Extract only the relevant fields before reasoning.",
            "approx_tokens_wasted": size - 500,
        })

    total_waste = sum(f.get("approx_tokens_wasted", 0) for f in findings)
    return {"findings": findings, "total_waste_tokens": total_waste, "reads": dict(reads)}


# ── Report ─────────────────────────────────────────────────────────────────────

def print_report(analysis: dict) -> None:
    findings = analysis["findings"]
    if not findings:
        print("No significant waste patterns found.")
        return

    print(f"\nFound {len(findings)} waste pattern(s), ~{analysis['total_waste_tokens']} tokens wasted:\n")
    by_type = {}
    for f in findings:
        t = f["type"]
        by_type.setdefault(t, []).append(f)

    for waste_type, items in sorted(by_type.items()):
        print(f"  [{waste_type}] × {len(items)}")
        for item in items[:2]:
            print(f"    Rule: {item.get('rule', '')}")
        print()


def append_corrections(analysis: dict) -> None:
    findings = analysis["findings"]
    if not findings:
        return

    from datetime import date
    today = date.today().isoformat()
    new_lines = []

    seen_rules = set()
    for f in findings:
        rule = f.get("rule", "")
        if rule and rule not in seen_rules:
            seen_rules.add(rule)
            waste = f.get("approx_tokens_wasted", 0)
            new_lines.append(f"- [{today}] rule: {rule}. reason: ~{waste} tokens wasted.")

    if new_lines:
        existing = CORRECTIONS_FILE.read_text()
        CORRECTIONS_FILE.write_text(existing + "\n".join(new_lines) + "\n")
        print(f"Appended {len(new_lines)} corrections to {CORRECTIONS_FILE}")


# ── Distill into CLAUDE.md ─────────────────────────────────────────────────────

def distill() -> None:
    if not CORRECTIONS_FILE.exists():
        print("No corrections file found.")
        return

    content = CORRECTIONS_FILE.read_text()
    rules = re.findall(r"- \[\d{4}-\d{2}-\d{2}\] rule: (.+?)\. reason:", content)

    if not rules:
        print("No corrections to distill.")
        return

    # Deduplicate and count frequency
    rule_counts = Counter(rules)
    top_rules = rule_counts.most_common(10)

    appendix = "\n\n---\n\n## Learned corrections (auto-generated)\n\n"
    for rule, count in top_rules:
        appendix += f"- {rule} _(seen {count}×)_\n"

    claude_content = CLAUDE_MD.read_text()
    marker = "## Learned corrections (auto-generated)"
    if marker in claude_content:
        claude_content = claude_content.split("\n\n---\n\n" + marker)[0]

    CLAUDE_MD.write_text(claude_content + appendix)
    print(f"Distilled {len(top_rules)} corrections into {CLAUDE_MD}")


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in {"-h", "--help"}:
        print(__doc__)
        sys.exit(0)

    if sys.argv[1] == "--distill":
        distill()
        sys.exit(0)

    source = sys.argv[1]
    if source == "-":
        text = sys.stdin.read()
        analysis = analyze_text(text)
    else:
        path = Path(source)
        if not path.exists():
            print(f"File not found: {path}")
            sys.exit(1)
        if path.suffix == ".jsonl":
            analysis = analyze_jsonl(path)
        else:
            analysis = analyze_text(path.read_text())

    print_report(analysis)
    append_corrections(analysis)
