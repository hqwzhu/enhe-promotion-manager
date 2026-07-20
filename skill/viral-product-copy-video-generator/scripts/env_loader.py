#!/usr/bin/env python3
"""Small .env loader for CLI scripts without storing secret values."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

YOUTUBE_ACCESS_TOKEN_ENVS = ("YOUTUBE_ACCESS_TOKEN", "YOUTUBE_OAUTH_ACCESS_TOKEN")
YOUTUBE_CLIENT_ID_ENVS = ("GOOGLE_OAUTH_CLIENT_ID", "YOUTUBE_CLIENT_ID")
YOUTUBE_CLIENT_SECRET_ENVS = ("GOOGLE_OAUTH_CLIENT_SECRET", "YOUTUBE_CLIENT_SECRET")
YOUTUBE_REFRESH_TOKEN_ENVS = ("YOUTUBE_REFRESH_TOKEN", "YOUTUBE_OAUTH_REFRESH_TOKEN")


def preparse_env_file(argv: Iterable[str] | None = None) -> str:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--env-file", default="")
    args, _ = parser.parse_known_args(list(argv) if argv is not None else None)
    return str(args.env_file or "")


def load_project_env(env_file: str = "", *, override: bool = False) -> dict[str, object]:
    candidates = candidate_env_files(env_file)
    loaded_files: list[str] = []
    loaded_keys: list[str] = []
    skipped_existing: list[str] = []
    missing_files: list[str] = []
    invalid_lines = 0
    for path in candidates:
        if not path.exists():
            missing_files.append(str(path))
            continue
        loaded_files.append(str(path))
        for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
            parsed = parse_env_line(raw_line)
            if parsed is None:
                if raw_line.strip() and not raw_line.lstrip().startswith("#"):
                    invalid_lines += 1
                continue
            key, value = parsed
            existing = os.environ.get(key)
            if not override and existing:
                skipped_existing.append(key)
                continue
            os.environ[key] = value
            loaded_keys.append(key)
    return {
        "envFiles": loaded_files,
        "missingEnvFiles": missing_files if env_file else [],
        "loadedKeys": sorted(set(loaded_keys)),
        "skippedExistingKeys": sorted(set(skipped_existing)),
        "invalidLines": invalid_lines,
        "valuesStored": False,
    }


def candidate_env_files(env_file: str) -> list[Path]:
    if env_file:
        path = Path(env_file)
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        return [path]
    candidates = [(Path.cwd() / ".env").resolve(), (ROOT / ".env").resolve()]
    result: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path).lower()
        if key not in seen:
            result.append(path)
            seen.add(key)
    return result


def parse_env_line(raw_line: str) -> tuple[str, str] | None:
    line = raw_line.strip()
    if not line or line.startswith("#"):
        return None
    if line.startswith("export "):
        line = line[7:].strip()
    if "=" not in line:
        return None
    key, value = line.split("=", 1)
    key = key.strip()
    if not KEY_RE.match(key):
        return None
    return key, clean_value(value)


def clean_value(value: str) -> str:
    text = value.strip()
    if not text:
        return ""
    quote = text[0]
    if quote in {"'", '"'}:
        end = text.rfind(quote)
        if end > 0:
            text = text[1:end]
        else:
            text = text[1:]
        if quote == '"':
            text = text.replace("\\n", "\n").replace("\\r", "\r").replace('\\"', '"').replace("\\\\", "\\")
        return text
    if " #" in text:
        text = text.split(" #", 1)[0].rstrip()
    return text


def first_env(names: Iterable[str]) -> str:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return ""


def present_env_names(names: Iterable[str]) -> list[str]:
    return [name for name in names if bool(os.environ.get(name))]


def blank_env_names(names: Iterable[str]) -> list[str]:
    return [name for name in names if name in os.environ and not os.environ.get(name)]


def grouped_env_ready(groups: Iterable[Iterable[str]]) -> bool:
    return all(any(os.environ.get(name) for name in group) for group in groups)
