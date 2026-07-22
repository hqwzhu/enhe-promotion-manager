#!/usr/bin/env python3
"""Build deterministic public release artifacts from the assembled repository."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

sys.dont_write_bytecode = True

import distribution_contract as contract
import generate_checksums
import verify_distribution


ROOT = Path(__file__).resolve().parents[1]
FIXED_ZIP_TIMESTAMP = contract.FIXED_ZIP_TIMESTAMP


def _json_bytes(payload: dict) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def add_bytes(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
    archive.writestr(
        contract.deterministic_zip_info(name),
        data,
        compress_type=contract.FIXED_ZIP_COMPRESSION,
        compresslevel=contract.FIXED_ZIP_COMPRESSLEVEL,
    )


def _validate_root_ancestors(root: Path) -> None:
    current = root.absolute()
    while True:
        try:
            current.lstat()
        except OSError as exc:
            raise RuntimeError("release root has an unreadable ancestor") from exc
        if contract._is_link_or_reparse(current):
            raise RuntimeError("release root has an unsafe link or reparse ancestor")
        if current.parent == current:
            return
        current = current.parent


def _validate_release_path(root: Path, path: Path, *, destination: bool = False) -> Path:
    root_absolute = root.absolute()
    _validate_root_ancestors(root_absolute)
    root_resolved = contract._resolved_root(root_absolute)
    path_absolute = path.absolute()
    try:
        relative = path_absolute.relative_to(root_absolute)
    except ValueError as exc:
        raise RuntimeError("release artifact path is outside the repository root") from exc
    current = root_absolute
    for part in relative.parts:
        current /= part
        try:
            current.lstat()
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise RuntimeError("release artifact path has an unreadable ancestor") from exc
        if contract._is_link_or_reparse(current):
            raise RuntimeError("release artifact path has an unsafe link or reparse point")
        is_destination = destination and current == path_absolute
        if is_destination:
            if not current.is_file():
                raise RuntimeError("release artifact destination is not a regular file")
        elif not current.is_dir():
            raise RuntimeError("release artifact ancestor is not a directory")
        if not current.resolve(strict=True).is_relative_to(root_resolved):
            raise RuntimeError("release artifact path escapes the repository root")
    return path_absolute


def _prepare_release_directory(root: Path) -> Path:
    dist_root = root / "dist"
    version_directory = dist_root / f"v{contract.VERSION}"
    _validate_release_path(root, dist_root)
    if not dist_root.exists():
        dist_root.mkdir()
    _validate_release_path(root, dist_root)
    _validate_release_path(root, version_directory)
    if not version_directory.exists():
        version_directory.mkdir()
    _validate_release_path(root, version_directory)
    return version_directory


def _new_temp_file(directory: Path, suffix: str) -> Path:
    descriptor, name = tempfile.mkstemp(prefix=".tmp-", suffix=suffix, dir=directory)
    os.close(descriptor)
    path = Path(name)
    if contract._is_link_or_reparse(path) or not path.is_file():
        path.unlink(missing_ok=True)
        raise RuntimeError("temporary release artifact is not a regular file")
    return path


def _new_temp_archive(directory: Path) -> Path:
    return _new_temp_file(directory, ".zip")


def _fsync_file(path: Path) -> None:
    with path.open("r+b") as handle:
        handle.flush()
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def _write_temp_bytes(path: Path, data: bytes) -> None:
    with path.open("r+b") as handle:
        handle.seek(0)
        handle.truncate()
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def _atomic_write_bytes(root: Path, path: Path, data: bytes) -> None:
    _validate_release_path(root, path.parent)
    _validate_release_path(root, path, destination=True)
    temporary = _new_temp_file(path.parent, ".publish")
    try:
        _write_temp_bytes(temporary, data)
        _validate_release_path(root, path.parent)
        _validate_release_path(root, path, destination=True)
        if contract._is_link_or_reparse(temporary) or not temporary.is_file():
            raise RuntimeError("publication temporary file is not a regular file")
        os.replace(temporary, path)
        temporary = None
        _fsync_directory(path.parent)
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def _snapshot_publication(paths: tuple[Path, ...]) -> dict[Path, bytes | None]:
    snapshots: dict[Path, bytes | None] = {}
    for path in paths:
        _validate_release_path(ROOT, path, destination=True)
        snapshots[path] = path.read_bytes() if path.exists() else None
    return snapshots


def _remove_publication_file(path: Path) -> None:
    _validate_release_path(ROOT, path.parent)
    try:
        path.lstat()
    except FileNotFoundError:
        return
    if contract._is_link_or_reparse(path):
        path.unlink()
    elif path.is_file():
        path.unlink()
    else:
        raise RuntimeError("rollback destination is not a regular file")
    _fsync_directory(path.parent)


def _restore_publication(snapshots: dict[Path, bytes | None]) -> None:
    failures: list[str] = []
    for path, data in snapshots.items():
        try:
            if data is None:
                _remove_publication_file(path)
            else:
                _atomic_write_bytes(ROOT, path, data)
        except Exception:
            failures.append(path.name)
    if failures:
        raise RuntimeError("release rollback failed for: " + ", ".join(failures))


def build_skill_zip(output: Path) -> None:
    source = ROOT / "skill" / "viral-product-copy-video-generator"
    output.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(
        contract._strict_files(ROOT, source),
        key=lambda path: path.relative_to(source).as_posix(),
    )
    with zipfile.ZipFile(
        output,
        "w",
        compression=contract.FIXED_ZIP_COMPRESSION,
        compresslevel=contract.FIXED_ZIP_COMPRESSLEVEL,
    ) as archive:
        archive.comment = b""
        for path in files:
            relative = path.relative_to(source).as_posix()
            add_bytes(
                archive,
                f"viral-product-copy-video-generator/{relative}",
                path.read_bytes(),
            )


def validate_skill_zip(path: Path) -> None:
    source = ROOT / "skill" / "viral-product-copy-video-generator"
    expected = {
        f"viral-product-copy-video-generator/{item.relative_to(source).as_posix()}": item
        for item in contract._strict_files(ROOT, source)
    }
    with zipfile.ZipFile(path) as archive:
        names = verify_distribution._safe_zip_members(archive)
        if len(names) != len(set(names)) or set(names) != set(expected):
            raise RuntimeError("staged Skill ZIP member list differs from public source")
        if contract.nondeterministic_zip_members(archive):
            raise RuntimeError("staged Skill ZIP metadata is not deterministic")
        for name, source_path in expected.items():
            if archive.read(name) != source_path.read_bytes():
                raise RuntimeError("staged Skill ZIP bytes differ from public source")


def _extension_source_files() -> dict[str, Path]:
    source = ROOT / "extension" / "chrome"
    return {
        path.relative_to(source).as_posix(): path
        for path in contract._strict_files(ROOT, source)
        if path.name != "component-manifest.json"
    }


def validate_extension_zip(source_zip: Path) -> None:
    expected = _extension_source_files()
    with zipfile.ZipFile(source_zip) as archive:
        try:
            names = verify_distribution._safe_zip_members(archive)
        except ValueError as exc:
            raise RuntimeError("validated extension ZIP contains an unsafe member path") from exc
        if (
            len(names) != len(set(names))
            or set(names) != set(expected)
            or "manifest.json" not in names
            or "component-manifest.json" in names
        ):
            raise RuntimeError("validated extension ZIP member list differs from public source")
        if contract.nondeterministic_zip_members(archive):
            raise RuntimeError("validated extension ZIP metadata is not deterministic")
        for name, path in expected.items():
            if archive.read(name) != path.read_bytes():
                raise RuntimeError(f"validated extension ZIP differs from public source: {name}")


def build_extension_zip_from_component(output: Path) -> None:
    expected = _extension_source_files()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        output,
        "w",
        compression=contract.FIXED_ZIP_COMPRESSION,
        compresslevel=contract.FIXED_ZIP_COMPRESSLEVEL,
    ) as archive:
        archive.comment = b""
        for name, path in sorted(expected.items()):
            add_bytes(archive, name, path.read_bytes())
    validate_extension_zip(output)


def copy_validated_extension(source_zip: Path, output: Path) -> None:
    validate_extension_zip(source_zip)
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_zip, output)


def canonical_tree_digest(release: dict) -> str:
    return verify_distribution.canonical_tree_digest(ROOT, release)


def build_release(
    validated_extension_zip: Path | None = None,
    *,
    build_extension_from_component: bool = False,
) -> Path:
    if (validated_extension_zip is None) == (not build_extension_from_component):
        raise ValueError(
            "select exactly one extension input: validated ZIP or public component bootstrap"
        )
    if validated_extension_zip is not None and not validated_extension_zip.is_file():
        raise FileNotFoundError(
            f"validated extension ZIP is missing: {validated_extension_zip}"
        )
    release_path = ROOT / "release-manifest.json"
    release = json.loads(release_path.read_text(encoding="utf-8"))
    if release.get("version") != contract.VERSION:
        raise RuntimeError("release version differs from distribution contract")
    if release.get("skillArchive") != verify_distribution.EXPECTED_SKILL_ARCHIVE:
        raise RuntimeError("release Skill archive name differs from the distribution contract")
    if release.get("extensionArchive") != verify_distribution.EXPECTED_EXTENSION_ARCHIVE:
        raise RuntimeError("release extension archive name differs from the distribution contract")
    component_errors = verify_distribution.verify_component_paths(ROOT)
    if component_errors:
        raise RuntimeError("public component contains generated or unsafe paths")

    dist = _prepare_release_directory(ROOT)
    skill_zip = dist / release["skillArchive"]
    extension_zip = dist / release["extensionArchive"]
    checksum_path = ROOT / "SHA256SUMS"
    snapshots = _snapshot_publication(
        (skill_zip, extension_zip, release_path, checksum_path)
    )
    _validate_release_path(ROOT, skill_zip, destination=True)
    _validate_release_path(ROOT, extension_zip, destination=True)
    skill_temp: Path | None = None
    extension_temp: Path | None = None
    try:
        skill_temp = _new_temp_archive(dist)
        extension_temp = _new_temp_archive(dist)
        build_skill_zip(skill_temp)
        validate_skill_zip(skill_temp)
        _fsync_file(skill_temp)
        if build_extension_from_component:
            build_extension_zip_from_component(extension_temp)
        else:
            assert validated_extension_zip is not None
            copy_validated_extension(validated_extension_zip, extension_temp)
            if extension_temp.read_bytes() != validated_extension_zip.read_bytes():
                raise RuntimeError("staged extension ZIP bytes differ from validated input")
        _fsync_file(extension_temp)

        _validate_release_path(ROOT, skill_zip, destination=True)
        _validate_release_path(ROOT, extension_zip, destination=True)
        if contract._is_link_or_reparse(skill_temp) or not skill_temp.is_file():
            raise RuntimeError("staged Skill ZIP is not a regular file")
        if contract._is_link_or_reparse(extension_temp) or not extension_temp.is_file():
            raise RuntimeError("staged extension ZIP is not a regular file")
        _validate_release_path(ROOT, skill_zip, destination=True)
        os.replace(skill_temp, skill_zip)
        skill_temp = None
        _validate_release_path(ROOT, extension_zip, destination=True)
        os.replace(extension_temp, extension_zip)
        extension_temp = None
        _fsync_directory(dist)

        release["artifacts"] = {
            path.name: {
                "bytes": path.stat().st_size,
                "sha256": contract.sha256_file(path).upper(),
            }
            for path in (skill_zip, extension_zip)
        }
        release["treeDigest"] = canonical_tree_digest(release)
        release["verification"]["status"] = "built"
        _atomic_write_bytes(ROOT, release_path, _json_bytes(release))

        errors = verify_distribution.validate(ROOT, check_checksums=False)
        if errors:
            raise RuntimeError("pre-checksum verification failed: " + "; ".join(errors))

        release["verification"]["status"] = "ready"
        _atomic_write_bytes(ROOT, release_path, _json_bytes(release))
        checksum_temp = _new_temp_file(ROOT, ".checksums")
        try:
            generate_checksums.write_checksums(
                ROOT,
                [
                    skill_zip.relative_to(ROOT).as_posix(),
                    extension_zip.relative_to(ROOT).as_posix(),
                    "release-manifest.json",
                ],
                checksum_temp,
            )
            _fsync_file(checksum_temp)
            _validate_release_path(ROOT, checksum_path, destination=True)
            if contract._is_link_or_reparse(checksum_temp) or not checksum_temp.is_file():
                raise RuntimeError("staged checksum file is not a regular file")
            os.replace(checksum_temp, checksum_path)
            checksum_temp = None
            _fsync_directory(ROOT)
        finally:
            if checksum_temp is not None:
                try:
                    checksum_temp.unlink(missing_ok=True)
                except OSError:
                    pass

        errors = verify_distribution.validate(ROOT)
        if errors:
            raise RuntimeError("final distribution verification failed: " + "; ".join(errors))
        return dist
    except BaseException as exc:
        try:
            _restore_publication(snapshots)
        except Exception as rollback_exc:
            raise RuntimeError("release failed and rollback could not restore prior publication") from rollback_exc
        raise
    finally:
        for temporary in (skill_temp, extension_temp):
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass


def main() -> None:
    parser = argparse.ArgumentParser()
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--validated-extension-zip")
    inputs.add_argument("--build-extension-from-component", action="store_true")
    args = parser.parse_args()
    validated = (
        Path(args.validated_extension_zip).resolve()
        if args.validated_extension_zip is not None
        else None
    )
    dist = build_release(
        validated,
        build_extension_from_component=args.build_extension_from_component,
    )
    print(f"Release assets ready: {dist}")


if __name__ == "__main__":
    main()
