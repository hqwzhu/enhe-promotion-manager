#!/usr/bin/env python3
"""Generate deterministic SHA-256 checksum records for release artifacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True

import distribution_contract as contract


ROOT = Path(__file__).resolve().parents[1]


def _checksum_input(root: Path, name: str) -> Path:
    relative = Path(name)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise ValueError("checksum input must be a safe relative path")
    candidate = root / relative
    try:
        candidate.lstat()
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"checksum input is missing: {name}") from exc
    issue = contract._source_issue(root.resolve(strict=True), candidate)
    if issue:
        raise ValueError(f"checksum input is unsafe, linked, or outside root: {issue}")
    if not candidate.is_file():
        raise FileNotFoundError(f"checksum input is missing: {name}")
    return candidate


def _checksum_output(root: Path, output: Path) -> Path:
    root_absolute = root.absolute()
    root_resolved = contract._resolved_root(root_absolute)
    output_absolute = output.absolute() if output.is_absolute() else (root_absolute / output).absolute()
    try:
        relative = output_absolute.relative_to(root_absolute)
    except ValueError as exc:
        raise ValueError("checksum output is outside the distribution root") from exc
    current = root_absolute
    for part in relative.parts:
        current /= part
        try:
            current.lstat()
        except FileNotFoundError:
            continue
        if contract._is_link_or_reparse(current):
            raise ValueError("checksum output has an unsafe link or reparse ancestor")
        if not current.resolve(strict=True).is_relative_to(root_resolved):
            raise ValueError("checksum output escapes the distribution root")
    if output_absolute.exists() and not output_absolute.is_file():
        raise ValueError("checksum output is not a file")
    return output_absolute


def write_checksums(root: Path, relative_paths: list[str], output: Path) -> None:
    root = Path(root).absolute()
    output = _checksum_output(root, Path(output))
    lines: list[str] = []
    for name in sorted(relative_paths):
        path = _checksum_input(root, name)
        lines.append(f"{contract.sha256_file(path).upper()}  {name}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--output", default="SHA256SUMS")
    args = parser.parse_args()
    write_checksums(ROOT, args.paths, ROOT / args.output)


if __name__ == "__main__":
    main()
