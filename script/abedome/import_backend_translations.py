#!/usr/bin/env python3
"""Import compatible backend translations from a pinned Core wheel."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
from typing import Any
import zipfile

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_COMPONENTS_ROOT = ROOT / "homeassistant" / "components"
MEMBER_PATTERN = re.compile(
    r"^homeassistant/components/(?P<domain>[a-z0-9_]+)/translations/"
    r"(?P<language>[A-Za-z0-9_-]+)\.json$"
)
MAX_TRANSLATION_FILE_SIZE = 8 * 1024 * 1024
REQUIRED_ONBOARDING_AREA_KEYS = frozenset({"bedroom", "kitchen", "living_room"})


@dataclass(frozen=True, slots=True)
class ImportSummary:
    """Summary of an imported translation wheel."""

    files: int
    components: int
    languages: frozenset[str]


def _sha256(path: Path) -> str:
    """Return the SHA-256 digest of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        while chunk := file_handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json_object(data: bytes, source: str) -> dict[str, Any]:
    """Load a JSON object from bytes."""
    try:
        value = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise ValueError(f"Invalid JSON in {source}") from err

    if not isinstance(value, dict):
        raise TypeError(f"Expected a JSON object in {source}")
    return value


def _load_json_file(path: Path) -> dict[str, Any]:
    """Load a JSON object from disk."""
    try:
        data = path.read_bytes()
    except OSError as err:
        raise ValueError(f"Unable to read {path}") from err
    return _load_json_object(data, str(path))


def _filter_compatible(
    translations: dict[str, Any], strings: dict[str, Any]
) -> dict[str, Any]:
    """Keep translated strings that exist in the current component schema."""
    filtered: dict[str, Any] = {}
    for key, value in translations.items():
        if key not in strings:
            continue

        current_value = strings[key]
        if isinstance(current_value, dict):
            if not isinstance(value, dict):
                continue
            if nested := _filter_compatible(value, current_value):
                filtered[key] = nested
        elif isinstance(current_value, str) and isinstance(value, str):
            filtered[key] = value

    return filtered


def _validate_member(info: zipfile.ZipInfo, seen_names: set[str]) -> None:
    """Reject unsafe or ambiguous wheel members."""
    member_path = PurePosixPath(info.filename)
    if member_path.is_absolute() or ".." in member_path.parts:
        raise ValueError(f"Unsafe wheel path: {info.filename}")
    if info.filename in seen_names:
        raise ValueError(f"Duplicate wheel member: {info.filename}")
    seen_names.add(info.filename)

    mode = (info.external_attr >> 16) & 0xFFFF
    if stat.S_ISLNK(mode):
        raise ValueError(f"Wheel symlink is not allowed: {info.filename}")
    if info.flag_bits & 0x1:
        raise ValueError(f"Encrypted wheel member is not allowed: {info.filename}")


def import_translations(
    wheel: Path,
    expected_sha256: str,
    components_root: Path = DEFAULT_COMPONENTS_ROOT,
) -> ImportSummary:
    """Import compatible non-English translation JSON files from a wheel."""
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise ValueError("Expected SHA-256 must be 64 lowercase hexadecimal characters")

    actual_sha256 = _sha256(wheel)
    if actual_sha256 != expected_sha256:
        raise ValueError(
            f"Wheel SHA-256 mismatch: expected {expected_sha256}, got {actual_sha256}"
        )

    strings_cache: dict[str, dict[str, Any]] = {}
    imported: list[tuple[str, str, Path]] = []
    languages: set[str] = set()
    seen_names: set[str] = set()
    seen_translations: set[tuple[str, str]] = set()

    with (
        tempfile.TemporaryDirectory(
            prefix=".abedome-translations-", dir=components_root.parent
        ) as temporary_directory,
        zipfile.ZipFile(wheel) as archive,
    ):
        staging_root = Path(temporary_directory)
        for info in archive.infolist():
            _validate_member(info, seen_names)
            if info.is_dir() or not (match := MEMBER_PATTERN.fullmatch(info.filename)):
                continue
            if info.file_size > MAX_TRANSLATION_FILE_SIZE:
                raise ValueError(f"Translation file is too large: {info.filename}")

            domain = match.group("domain")
            language = match.group("language")
            identity = (domain, language)
            if identity in seen_translations:
                raise ValueError(
                    f"Duplicate translation for component {domain}, language {language}"
                )
            seen_translations.add(identity)

            # English is generated from the current fork source in the Docker build.
            if language == "en":
                continue

            component_root = components_root / domain
            strings_path = component_root / "strings.json"
            if not component_root.is_dir() or not strings_path.is_file():
                continue

            if domain not in strings_cache:
                strings_cache[domain] = _load_json_file(strings_path)
            strings = strings_cache[domain]
            translations = _load_json_object(archive.read(info), info.filename)
            if not (filtered := _filter_compatible(translations, strings)):
                continue

            staged_path = staging_root / domain / "translations" / f"{language}.json"
            staged_path.parent.mkdir(parents=True, exist_ok=True)
            staged_path.write_text(
                json.dumps(filtered, ensure_ascii=False, indent=4, sort_keys=True)
                + "\n",
                encoding="utf-8",
            )
            imported.append((domain, language, staged_path))
            languages.add(language)

        if not imported:
            raise ValueError(
                "The wheel contained no compatible non-English translations"
            )

        # Commit only after the complete wheel has passed validation.
        for translations_root in components_root.glob("*/translations"):
            for existing_file in translations_root.glob("*.json"):
                if existing_file.stem != "en":
                    existing_file.unlink()

        for domain, language, staged_path in imported:
            target = components_root / domain / "translations" / f"{language}.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            staged_path.replace(target)

    return ImportSummary(
        files=len(imported),
        components=len({domain for domain, _, _ in imported}),
        languages=frozenset(languages),
    )


def verify_onboarding_translations(components_root: Path, languages: list[str]) -> None:
    """Verify required onboarding area keys for each packaged language."""
    for language in languages:
        translation_path = (
            components_root / "onboarding" / "translations" / f"{language}.json"
        )
        if not translation_path.is_file():
            raise ValueError(f"Missing onboarding translation file for {language}")
        translations = _load_json_file(translation_path)
        area = translations.get("area")
        if not isinstance(area, dict):
            raise TypeError(f"Missing onboarding area translations for {language}")
        if missing := REQUIRED_ONBOARDING_AREA_KEYS - area.keys():
            raise ValueError(
                f"Missing onboarding area keys for {language}: {', '.join(sorted(missing))}"
            )


def verify_onboarding_source_strings(components_root: Path) -> None:
    """Verify current English source strings used by the Docker generator."""
    strings = _load_json_file(components_root / "onboarding" / "strings.json")
    area = strings.get("area")
    if not isinstance(area, dict):
        raise TypeError("Missing onboarding area source strings")
    if missing := REQUIRED_ONBOARDING_AREA_KEYS - area.keys():
        raise ValueError(
            f"Missing onboarding area source keys: {', '.join(sorted(missing))}"
        )


def _parser() -> argparse.ArgumentParser:
    """Return the command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    import_parser = subparsers.add_parser("import")
    import_parser.add_argument("--wheel", type=Path, required=True)
    import_parser.add_argument("--expected-sha256", required=True)
    import_parser.add_argument(
        "--components-root", type=Path, default=DEFAULT_COMPONENTS_ROOT
    )
    import_parser.add_argument("--require-language", action="append", default=[])

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument(
        "--components-root", type=Path, default=DEFAULT_COMPONENTS_ROOT
    )
    verify_parser.add_argument("--language", action="append", required=True)
    return parser


def main() -> int:
    """Import or verify backend translations."""
    args = _parser().parse_args()
    if args.command == "verify":
        verify_onboarding_translations(args.components_root, args.language)
        print(
            f"Verified onboarding translations for {', '.join(sorted(args.language))}"
        )
        return 0

    summary = import_translations(
        args.wheel, args.expected_sha256, args.components_root
    )
    verify_onboarding_source_strings(args.components_root)
    if args.require_language:
        verify_onboarding_translations(args.components_root, args.require_language)
    print(
        f"Imported {summary.files} files for {summary.components} components "
        f"and {len(summary.languages)} languages"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
