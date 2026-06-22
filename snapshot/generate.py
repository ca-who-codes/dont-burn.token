#!/usr/bin/env python3
"""
Generate a compressed project snapshot for AI sessions.

Inspired by graphify's knowledge-graph approach: build a map once,
query it instead of reading raw files repeatedly.

Usage:
    python snapshot/generate.py [project_root] [output_path]

    project_root  defaults to current directory
    output_path   defaults to snapshot/project.md
"""

import ast
import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────

SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__", ".next",
    "dist", "build", "target", ".cache", "coverage", ".pytest_cache",
    ".mypy_cache", "vendor", ".terraform", ".eggs", "htmlcov",
    "snapshot", "session",
}

IDENTITY_FILES = [
    "package.json", "pyproject.toml", "Cargo.toml", "go.mod",
    "requirements.txt", "composer.json", "build.gradle", "pom.xml",
    "CMakeLists.txt", "Makefile", "CLAUDE.md", "AGENTS.md", "README.md",
]

CODE_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".rb",
    ".java", ".kt", ".swift", ".c", ".cpp", ".h", ".cs", ".php",
    ".scala", ".ex", ".exs", ".clj", ".hs", ".vue", ".svelte", ".elm",
}

CONFIG_EXTENSIONS = {".json", ".toml", ".yaml", ".yml", ".env.example"}

MAX_FILES = 300
MAX_DEPTH = 5
MAX_FUNCTION_LINES = 4
MAX_SAMPLE_LINES = 30


# ── File collection ────────────────────────────────────────────────────────────

def collect_files(root: Path) -> list[Path]:
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel = Path(dirpath).relative_to(root)
        depth = len(rel.parts)

        if depth > MAX_DEPTH:
            dirnames.clear()
            continue

        dirnames[:] = [d for d in sorted(dirnames) if d not in SKIP_DIRS]

        for name in sorted(filenames):
            p = Path(dirpath) / name
            ext = p.suffix.lower()
            if ext in CODE_EXTENSIONS or ext in CONFIG_EXTENSIONS or name in IDENTITY_FILES:
                files.append(p)
            if len(files) >= MAX_FILES:
                return files
    return files


# ── Project identity ──────────────────────────────────────────────────────────

def detect_project(root: Path) -> dict:
    info = {"name": root.name, "type": "unknown", "language": "unknown", "deps": []}

    # package.json → Node/TypeScript
    pkg = root / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text())
            info["name"] = data.get("name", root.name)
            info["type"] = "node"
            info["language"] = "TypeScript" if (root / "tsconfig.json").exists() else "JavaScript"
            deps = list(data.get("dependencies", {}).keys())[:10]
            dev_deps = list(data.get("devDependencies", {}).keys())[:5]
            info["deps"] = deps
            info["dev_deps"] = dev_deps
            info["scripts"] = list(data.get("scripts", {}).keys())
        except Exception:
            pass
        return info

    # pyproject.toml → Python
    pyp = root / "pyproject.toml"
    if pyp.exists():
        content = pyp.read_text()
        info["type"] = "python"
        info["language"] = "Python"
        m = re.search(r'name\s*=\s*"([^"]+)"', content)
        if m:
            info["name"] = m.group(1)
        deps = re.findall(r'"([a-zA-Z0-9_-]+)(?:[>=<][^"]+)?"', content)
        info["deps"] = [d for d in deps[:10] if d != info["name"]]
        return info

    # Cargo.toml → Rust
    cargo = root / "Cargo.toml"
    if cargo.exists():
        content = cargo.read_text()
        info["type"] = "rust"
        info["language"] = "Rust"
        m = re.search(r'name\s*=\s*"([^"]+)"', content)
        if m:
            info["name"] = m.group(1)
        return info

    # go.mod → Go
    gomod = root / "go.mod"
    if gomod.exists():
        content = gomod.read_text()
        info["type"] = "go"
        info["language"] = "Go"
        m = re.search(r'^module\s+(\S+)', content, re.MULTILINE)
        if m:
            info["name"] = m.group(1).split("/")[-1]
        return info

    # Makefile → C/C++ or generic
    if (root / "Makefile").exists():
        info["type"] = "make"
        info["language"] = "C/C++" if any(root.glob("**/*.c")) else "unknown"

    return info


# ── Module extraction ─────────────────────────────────────────────────────────

def extract_python_symbols(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return []
    symbols = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                args = [a.arg for a in node.args.args[:3]]
                symbols.append(f"def {node.name}({', '.join(args)}{'...' if len(node.args.args) > 3 else ''})")
        elif isinstance(node, ast.ClassDef):
            if not node.name.startswith("_"):
                symbols.append(f"class {node.name}")
    return symbols[:15]


def extract_ts_symbols(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    symbols = []
    patterns = [
        r"export (?:default )?(?:async )?function\s+(\w+)",
        r"export (?:const|let|var)\s+(\w+)\s*[:=].*(?:=>|function)",
        r"export (?:default )?class\s+(\w+)",
        r"export (?:type|interface)\s+(\w+)",
    ]
    for pat in patterns:
        for m in re.finditer(pat, text):
            symbols.append(m.group(0)[:80].strip())
    return symbols[:15]


def extract_go_symbols(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    symbols = []
    for m in re.finditer(r"^func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\(", text, re.MULTILINE):
        if not m.group(1).startswith("_"):
            symbols.append(f"func {m.group(1)}(...)")
    for m in re.finditer(r"^type\s+(\w+)\s+(?:struct|interface)", text, re.MULTILINE):
        symbols.append(f"type {m.group(1)}")
    return symbols[:15]


def extract_rust_symbols(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    symbols = []
    for m in re.finditer(r"^pub (?:async )?fn\s+(\w+)", text, re.MULTILINE):
        symbols.append(f"pub fn {m.group(1)}(...)")
    for m in re.finditer(r"^pub struct\s+(\w+)", text, re.MULTILINE):
        symbols.append(f"pub struct {m.group(1)}")
    return symbols[:15]


def extract_symbols(path: Path) -> list[str]:
    ext = path.suffix.lower()
    if ext == ".py":
        return extract_python_symbols(path)
    if ext in {".ts", ".tsx", ".js", ".jsx"}:
        return extract_ts_symbols(path)
    if ext == ".go":
        return extract_go_symbols(path)
    if ext == ".rs":
        return extract_rust_symbols(path)
    return []


# ── Directory tree ────────────────────────────────────────────────────────────

def build_tree(root: Path, depth: int = 0, max_depth: int = 3) -> list[str]:
    if depth > max_depth:
        return []
    lines = []
    try:
        entries = sorted(root.iterdir(), key=lambda p: (p.is_file(), p.name))
    except PermissionError:
        return []
    for entry in entries:
        if entry.name.startswith(".") or entry.name in SKIP_DIRS:
            continue
        indent = "  " * depth
        if entry.is_dir():
            lines.append(f"{indent}{entry.name}/")
            lines.extend(build_tree(entry, depth + 1, max_depth))
        else:
            ext = entry.suffix.lower()
            if ext in CODE_EXTENSIONS or ext in CONFIG_EXTENSIONS or entry.name in IDENTITY_FILES:
                lines.append(f"{indent}{entry.name}")
    return lines


# ── Key file sampling ─────────────────────────────────────────────────────────

def sample_file(path: Path, max_lines: int = MAX_SAMPLE_LINES) -> str:
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        if len(lines) <= max_lines:
            return "\n".join(lines)
        head = lines[:max_lines // 2]
        tail = lines[-(max_lines // 4):]
        return "\n".join(head) + f"\n... ({len(lines) - max_lines // 2 - max_lines // 4} lines omitted) ...\n" + "\n".join(tail)
    except Exception:
        return ""


# ── Entry point detection ─────────────────────────────────────────────────────

ENTRY_PATTERNS = [
    "main.py", "app.py", "server.py", "cli.py", "run.py",
    "index.ts", "index.js", "server.ts", "app.ts", "main.ts",
    "src/main.py", "src/app.py", "src/index.ts", "src/main.ts",
    "cmd/main.go", "main.go",
    "src/main.rs", "src/lib.rs",
]

def find_entry_points(root: Path) -> list[Path]:
    found = []
    for pattern in ENTRY_PATTERNS:
        p = root / pattern
        if p.exists():
            found.append(p)
    return found


# ── Report generation ─────────────────────────────────────────────────────────

def generate(root: Path, output: Path) -> None:
    root = root.resolve()
    project = detect_project(root)
    files = collect_files(root)
    entry_points = find_entry_points(root)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Module map: group by top-level dir
    module_map: dict[str, list[tuple[Path, list[str]]]] = {}
    for f in files:
        rel = f.relative_to(root)
        parts = rel.parts
        top = parts[0] if len(parts) > 1 else "."
        if top not in module_map:
            module_map[top] = []
        symbols = extract_symbols(f)
        if symbols:
            module_map[top].append((rel, symbols))

    lines = [
        f"# Project Snapshot — {project['name']}",
        f"Generated: {generated_at}  |  Root: `{root}`",
        "",
        "---",
        "",
        "## Identity",
        f"- **Type**: {project['type']}",
        f"- **Language**: {project['language']}",
    ]

    if project.get("deps"):
        lines.append(f"- **Key deps**: {', '.join(project['deps'][:8])}")
    if project.get("scripts"):
        lines.append(f"- **Scripts**: {', '.join(project['scripts'][:6])}")

    lines += ["", "---", "", "## Directory tree"]
    tree = build_tree(root, max_depth=2)
    lines.append("```")
    lines.extend(tree[:60])
    if len(tree) > 60:
        lines.append(f"... ({len(tree) - 60} more entries)")
    lines.append("```")

    if entry_points:
        lines += ["", "---", "", "## Entry points"]
        for ep in entry_points:
            rel = ep.relative_to(root)
            lines.append(f"### `{rel}`")
            sample = sample_file(ep)
            if sample:
                lines.append(f"```{ep.suffix.lstrip('.')}")
                lines.append(sample)
                lines.append("```")

    if module_map:
        lines += ["", "---", "", "## Module map"]
        lines.append("Only modules with exported symbols are listed.")
        lines.append("")
        for top_dir, mod_files in sorted(module_map.items()):
            if not mod_files:
                continue
            lines.append(f"### `{top_dir}/`")
            for rel_path, symbols in mod_files[:20]:
                lines.append(f"**`{rel_path}`**")
                for sym in symbols:
                    lines.append(f"  - `{sym}`")
            if len(mod_files) > 20:
                lines.append(f"  ... ({len(mod_files) - 20} more files)")
            lines.append("")

    lines += ["---", "", "## Suggested queries"]
    lines += [
        "Use these prompts instead of exploring files:",
        f'- "What does `<module>` do?" → read the snapshot section for that module',
        f'- "Where is `<function>` defined?" → grep for it using the module map above',
        f'- "How does X connect to Y?" → trace through the module map',
        "",
        "_This file is a compressed index, not a full codebase read._",
        "_Run `python snapshot/generate.py` to regenerate after major changes._",
    ]

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n")
    print(f"Snapshot written to {output} ({len(files)} files indexed)")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    root_arg = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    out_arg = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).parent / "project.md"
    generate(root_arg, out_arg)
