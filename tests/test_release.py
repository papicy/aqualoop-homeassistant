from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import pytest


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "release.py"
SPEC = spec_from_file_location("release", MODULE_PATH)
assert SPEC and SPEC.loader
release = module_from_spec(SPEC)
sys.modules[SPEC.name] = release
SPEC.loader.exec_module(release)


def test_version_bumps_patch_and_minor() -> None:
    version = release.Version.parse("1.0.0")

    assert str(version.bump("patch")) == "1.0.1"
    assert str(version.bump("minor")) == "1.1.0"


def test_version_rejects_non_semver() -> None:
    with pytest.raises(ValueError):
        release.Version.parse("1.0")


def test_version_references_are_updated(tmp_path, monkeypatch) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"version": "1.0.0"}\n', encoding="utf-8")
    metadata = tmp_path / "metadata.json"
    metadata.write_text('{"version": "1.0.0"}\n', encoding="utf-8")

    monkeypatch.setattr(release, "ROOT", tmp_path)
    monkeypatch.setattr(release, "MANIFEST", manifest)
    monkeypatch.setattr(
        release,
        "tracked_files",
        lambda: [manifest, metadata],
    )

    changed = release.update_version_references(
        release.Version.parse("1.0.0"),
        release.Version.parse("1.0.1"),
    )

    assert changed == [manifest, metadata]
    assert '"version": "1.0.1"' in manifest.read_text(encoding="utf-8")
    assert '"version": "1.0.1"' in metadata.read_text(encoding="utf-8")
