#!/usr/bin/env python3
"""
Compress tool outputs before passing them to an AI session.

Implements the SmartCrusher pattern from headroom:
- JSON: drop null/empty fields, truncate arrays, remove boilerplate
- Logs: extract signal lines (errors, warnings, key events)
- Code: extract signatures, skip implementation bodies
- Diffs: keep ± context lines, skip unchanged hunks

Usage:
    python session/compress.py --type json < output.json
    python session/compress.py --type logs < server.log
    python session/compress.py --type diff < changes.patch
    python session/compress.py --type code < file.py
    cat output.json | python session/compress.py --type json --max-array 5
"""

import json
import re
import sys
from argparse import ArgumentParser


# ── JSON compression ───────────────────────────────────────────────────────────

def compress_json(data, max_array: int = 10, max_depth: int = 5, _depth: int = 0):
    if _depth > max_depth:
        return "..."

    if isinstance(data, dict):
        compressed = {}
        for k, v in data.items():
            if v is None or v == "" or v == [] or v == {}:
                continue  # drop empty fields
            compressed[k] = compress_json(v, max_array, max_depth, _depth + 1)
        return compressed

    if isinstance(data, list):
        if len(data) > max_array:
            truncated = [compress_json(x, max_array, max_depth, _depth + 1) for x in data[:max_array]]
            return truncated + [f"... ({len(data) - max_array} more)"]
        return [compress_json(x, max_array, max_depth, _depth + 1) for x in data]

    return data


def compress_json_text(text: str, max_array: int = 10) -> str:
    try:
        data = json.loads(text)
        compressed = compress_json(data, max_array=max_array)
        return json.dumps(compressed, indent=2, separators=(',', ': '))
    except json.JSONDecodeError:
        return text


# ── Log compression ────────────────────────────────────────────────────────────

LOG_SIGNAL_PATTERNS = [
    re.compile(r'\b(ERROR|FATAL|CRITICAL|EXCEPTION|PANIC)\b', re.IGNORECASE),
    re.compile(r'\b(WARN|WARNING)\b', re.IGNORECASE),
    re.compile(r'\b(failed|failure|error|exception|traceback|stacktrace)\b', re.IGNORECASE),
    re.compile(r'^\s+at\s+', re.MULTILINE),          # stack trace lines
    re.compile(r'File ".*", line \d+'),               # Python tracebacks
    re.compile(r'^\d{4}-\d{2}-\d{2}.*\b(ERROR|WARN)', re.MULTILINE),
]

LOG_NOISE_PATTERNS = [
    re.compile(r'^\s*(DEBUG|TRACE)\b', re.IGNORECASE),
    re.compile(r'health.?check|ping|heartbeat', re.IGNORECASE),
    re.compile(r'GET /health|POST /metrics', re.IGNORECASE),
]


def compress_logs(text: str, max_lines: int = 50) -> str:
    lines = text.splitlines()
    signal_lines = []
    noise_count = 0

    for i, line in enumerate(lines):
        is_noise = any(p.search(line) for p in LOG_NOISE_PATTERNS)
        is_signal = any(p.search(line) for p in LOG_SIGNAL_PATTERNS)

        if is_noise and not is_signal:
            noise_count += 1
            continue

        signal_lines.append((i + 1, line))

    if noise_count:
        signal_lines.insert(0, (0, f"[{noise_count} debug/health-check lines omitted]"))

    if len(signal_lines) > max_lines:
        kept = signal_lines[:max_lines]
        kept.append((0, f"[{len(signal_lines) - max_lines} more signal lines omitted]"))
        signal_lines = kept

    return "\n".join(f"{lineno:>5}  {line}" if lineno else f"       {line}"
                     for lineno, line in signal_lines)


# ── Diff compression ───────────────────────────────────────────────────────────

def compress_diff(text: str, context_lines: int = 3) -> str:
    lines = text.splitlines()
    output = []
    i = 0
    unchanged_streak = 0

    while i < len(lines):
        line = lines[i]
        if line.startswith(("+++", "---", "@@", "diff ", "index ")):
            if unchanged_streak > 0:
                output.append(f"   [... {unchanged_streak} unchanged lines ...]")
                unchanged_streak = 0
            output.append(line)
        elif line.startswith(("+", "-")):
            if unchanged_streak > 0:
                output.append(f"   [... {unchanged_streak} unchanged lines ...]")
                unchanged_streak = 0
            output.append(line)
        else:
            unchanged_streak += 1
            # Keep context around changes
            if i < len(lines) - 1 and lines[i + 1].startswith(("+", "-")):
                if unchanged_streak > context_lines:
                    output.append(f"   [... {unchanged_streak - context_lines} unchanged lines ...]")
                output.append(line)
                unchanged_streak = 0

        i += 1

    if unchanged_streak > 0:
        output.append(f"   [... {unchanged_streak} unchanged lines ...]")

    return "\n".join(output)


# ── Code signature extraction ──────────────────────────────────────────────────

def compress_code(text: str, lang: str = "auto") -> str:
    lines = text.splitlines()

    if lang == "auto":
        # Detect by content
        if "def " in text or "import " in text:
            lang = "python"
        elif "function " in text or "const " in text or "interface " in text:
            lang = "typescript"
        else:
            lang = "unknown"

    if lang == "python":
        return _compress_python(lines)
    if lang in ("typescript", "javascript"):
        return _compress_ts(lines)

    # Generic: first 30 + last 10
    if len(lines) > 40:
        return "\n".join(lines[:30]) + f"\n... ({len(lines) - 40} lines omitted) ...\n" + "\n".join(lines[-10:])
    return text


def _compress_python(lines: list[str]) -> str:
    out = []
    in_body = False
    indent_level = 0

    for line in lines:
        stripped = line.lstrip()

        # Always keep: imports, class/def signatures, decorators
        if (stripped.startswith(("import ", "from ", "@", "class ", "def "))
                or stripped.startswith(("__all__", "__version__", "logger = "))):
            out.append(line)
            in_body = False
            continue

        # Detect body start
        if out and out[-1].rstrip().endswith(":"):
            in_body = True
            indent_level = len(line) - len(line.lstrip())
            out.append(f"{' ' * indent_level}...")
            continue

        if in_body:
            current_indent = len(line) - len(line.lstrip()) if stripped else indent_level + 4
            if current_indent <= indent_level and stripped:
                in_body = False
                out.append(line)
        else:
            if stripped:
                out.append(line)

    return "\n".join(out)


def _compress_ts(lines: list[str]) -> str:
    out = []
    brace_depth = 0
    in_body = False

    for line in lines:
        stripped = line.strip()
        opens = line.count("{")
        closes = line.count("}")

        if re.match(r'^(export\s+)?(default\s+)?(async\s+)?function\s+\w+|'
                    r'^(export\s+)?(const|let|var)\s+\w+\s*=\s*(async\s+)?\(|'
                    r'^(export\s+)?(default\s+)?class\s+\w+|'
                    r'^(export\s+)?(type|interface)\s+\w+', stripped):
            out.append(line)
            in_body = False

        if stripped == "{" and brace_depth == 0 and out:
            out.append(line)
            out.append("  ...")
            in_body = True

        brace_depth += opens - closes

        if in_body and brace_depth == 0:
            out.append(line)
            in_body = False
        elif not in_body and not stripped.startswith("//"):
            if stripped.startswith(("import ", "export type", "export interface", "export {")):
                out.append(line)

    return "\n".join(out)


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = ArgumentParser(description="Compress tool outputs before AI reasoning")
    parser.add_argument("--type", choices=["json", "logs", "diff", "code"], default="json")
    parser.add_argument("--max-array", type=int, default=10, help="Max array length (json mode)")
    parser.add_argument("--max-lines", type=int, default=50, help="Max signal lines (logs mode)")
    parser.add_argument("--lang", default="auto", help="Language hint (code mode)")
    parser.add_argument("file", nargs="?", help="Input file (default: stdin)")
    args = parser.parse_args()

    text = open(args.file).read() if args.file else sys.stdin.read()

    if args.type == "json":
        result = compress_json_text(text, max_array=args.max_array)
    elif args.type == "logs":
        result = compress_logs(text, max_lines=args.max_lines)
    elif args.type == "diff":
        result = compress_diff(text)
    elif args.type == "code":
        result = compress_code(text, lang=args.lang)
    else:
        result = text

    original_tokens = len(text) // 4
    compressed_tokens = len(result) // 4
    reduction = (1 - compressed_tokens / original_tokens) * 100 if original_tokens else 0

    print(result)
    print(f"\n# compressed: ~{original_tokens} → ~{compressed_tokens} tokens ({reduction:.0f}% reduction)",
          file=sys.stderr)


if __name__ == "__main__":
    main()
