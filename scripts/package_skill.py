#!/usr/bin/env python3
"""Build and verify a safe, single-root skill ZIP for ChatGPT Skills upload."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

ALLOWED_TOP = {"SKILL.md", "LICENSE", "requirements.txt", "agents",
               "assets", "references", "scripts", "tests"}
BLOCKED = {"__pycache__", ".git", ".DS_Store", ".pytest_cache"}
REQUIRED = {"SKILL.md", "LICENSE", "agents/openai.yaml",
            "scripts/run_store.py", "scripts/render_report.py",
            "scripts/quality_gate.py", "references/reporting.md",
            "references/web-evidence.md", "scripts/report_contract.py",
            "references/report-output-spec-v3.1.md", "assets/report-draft-template.json"}


def package(skill: Path, output: Path) -> dict:
    manifest = (skill / "SKILL.md").read_text(encoding="utf-8")
    match = re.search(r"(?m)^name:\s*(phd-deep-research-agent-v3-1)\s*$", manifest)
    if not match:
        raise ValueError("The skill manifest is not the expected v3.1 skill")
    top_folder = match.group(1)
    files = []
    for path in sorted(skill.rglob("*")):
        rel = path.relative_to(skill)
        if any(part in BLOCKED for part in rel.parts):
            continue
        if rel.parts[0] not in ALLOWED_TOP:
            raise ValueError("Unexpected package content: " + str(rel))
        if path.is_symlink():
            raise ValueError("Refusing symlink: " + str(rel))
        if path.is_file():
            files.append(path)
    relative = {p.relative_to(skill).as_posix() for p in files}
    if not REQUIRED.issubset(relative):
        raise ValueError("Required files missing: " + repr(sorted(REQUIRED - relative)))
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            rel = path.relative_to(skill).as_posix()
            archive.write(path, arcname=top_folder + "/" + rel)
    with zipfile.ZipFile(output) as archive:
        actual = archive.namelist()
        assert archive.testzip() is None
        assert sum(n.endswith("/SKILL.md") for n in actual) == 1
        assert all(n.startswith(top_folder + "/") and "../" not in n for n in actual)
    return {"zip": str(output), "files": len(files), "bytes": output.stat().st_size,
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(package(args.skill.resolve(), args.output.resolve()), indent=2))


if __name__ == "__main__":
    main()
