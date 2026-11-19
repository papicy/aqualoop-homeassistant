#!/usr/bin/env python3
"""Prepare and publish a repository release from the latest main branch."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "custom_components" / "aqualoop" / "manifest.json"
VERSION_PATTERN = re.compile(
    r'(?P<prefix>(?:"version"\s*:\s*"|version\s*=\s*"|^version\s*:\s*))'
    r"(?P<version>\d+\.\d+\.\d+)"
)


@dataclass(frozen=True, order=True)
class Version:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, value: str) -> "Version":
        match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", value)
        if not match:
            raise ValueError(f"invalid semantic version: {value}")
        return cls(*(int(part) for part in match.groups()))

    def bump(self, part: str) -> "Version":
        if part == "major":
            return Version(self.major + 1, 0, 0)
        if part == "minor":
            return Version(self.major, self.minor + 1, 0)
        if part == "patch":
            return Version(self.major, self.minor, self.patch + 1)
        raise ValueError(f"unsupported release part: {part}")

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


def run(*args: str, capture: bool = True) -> str:
    result = subprocess.run(
        args,
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=capture,
    )
    return result.stdout.strip() if capture else ""


def current_version() -> Version:
    with MANIFEST.open(encoding="utf-8") as file:
        return Version.parse(json.load(file)["version"])


def tracked_files() -> list[Path]:
    output = run("git", "ls-files", "-z")
    return [ROOT / path for path in output.split("\0") if path]


def update_version_references(old: Version, new: Version) -> list[Path]:
    changed: list[Path] = []
    for path in tracked_files():
        if path == MANIFEST or path.suffix.lower() not in {
            ".json",
            ".md",
            ".py",
            ".toml",
            ".yaml",
            ".yml",
        }:
            continue
        text = path.read_text(encoding="utf-8")
        updated, count = VERSION_PATTERN.subn(
            lambda match: f"{match.group('prefix')}{new}",
            text,
        )
        if count:
            path.write_text(updated, encoding="utf-8", newline="")
            changed.append(path)

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest["version"] != str(old):
        raise RuntimeError(
            f"{MANIFEST.relative_to(ROOT)} changed while preparing the release"
        )
    manifest["version"] = str(new)
    MANIFEST.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
        newline="",
    )
    if MANIFEST not in changed:
        changed.append(MANIFEST)
    return sorted(set(changed))


def ensure_latest_main() -> None:
    if run("git", "status", "--short"):
        raise RuntimeError("working tree is not clean")
    if run("git", "branch", "--show-current") != "main":
        raise RuntimeError("release publishing must run from the main branch")
    run("git", "fetch", "origin", "main", "--tags", capture=False)
    if run("git", "rev-parse", "HEAD") != run("git", "rev-parse", "origin/main"):
        raise RuntimeError("local main is not at the latest origin/main; pull first")


def run_quality_checks() -> None:
    run(sys.executable, "-m", "pytest", "-q", capture=False)
    run("git", "diff", "--check", capture=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bump all repository version metadata and publish a GitHub release."
    )
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument("--version", help="explicit release version, such as 1.0.1")
    choice.add_argument(
        "--bump",
        choices=("major", "minor", "patch"),
        help="release component to increment",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="tag the already-merged version and create the GitHub release",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show the next version without changing files",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    old = current_version()
    if not args.version and not args.bump and not args.publish:
        raise RuntimeError("provide --version, --bump, or --publish")
    new = Version.parse(args.version) if args.version else (
        old.bump(args.bump) if args.bump else old
    )
    if not args.publish and new <= old:
        raise RuntimeError(f"release version {new} must be greater than {old}")
    if args.publish and new != old:
        raise RuntimeError(
            f"publish mode expects the already-merged version {old}; "
            "prepare the version bump first"
        )

    if args.dry_run:
        print(f"{old} -> {new}")
        return 0

    ensure_latest_main()
    changed: list[Path] = []
    if new != old:
        changed = update_version_references(old, new)
        print(f"Updated {len(changed)} file(s) to {new}:")
        for path in changed:
            print(f"  {path.relative_to(ROOT)}")

    run_quality_checks()
    if not args.publish:
        print("Version bump prepared. Review the diff, commit it through a PR, then rerun with --publish.")
        return 0

    tag = f"v{new}"
    run("git", "tag", "-a", tag, "-m", f"Release {tag}", capture=False)
    run("git", "push", "origin", tag, capture=False)
    run(
        "gh",
        "release",
        "create",
        tag,
        "--repo",
        "papicy/aqualoop-homeassistant",
        "--target",
        "main",
        "--generate-notes",
        "--title",
        f"Aqualoop Water Heater {tag}",
        capture=False,
    )
    print(f"Published {tag}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        print(f"release failed: {error}", file=sys.stderr)
        raise SystemExit(1)
