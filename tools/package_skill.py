#!/usr/bin/env python3
"""Build a versioned, reproducible MATRIC skill ZIP and its SHA-256 checksum."""
import argparse
import hashlib
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/matric-decks"


def package(output_directory):
    """Package only the portable skill payload; refuse to overwrite release artifacts."""
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?", version):
        raise ValueError("VERSION must contain a semantic version")
    if (ROOT / "LICENSE").read_bytes() != (SKILL / "LICENSE.txt").read_bytes():
        raise ValueError("Repository and installable skill licenses differ")
    output_directory = Path(output_directory).resolve()
    if output_directory == SKILL.resolve() or SKILL.resolve() in output_directory.parents:
        raise ValueError("Release output must be outside the installable skill folder")
    output_directory.mkdir(parents=True, exist_ok=True)
    archive = output_directory / ("matric-decks-" + version + ".zip")
    checksum = archive.with_suffix(".zip.sha256")
    if archive.exists() or checksum.exists():
        raise FileExistsError("Release artifacts already exist; choose a new version or output directory")
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as zipped:
        for path in sorted(SKILL.rglob("*")):
            if path.is_symlink():
                raise ValueError("Linked skill resources cannot be distributed")
            if not path.is_file() or "__pycache__" in path.parts or path.suffix in (".pyc", ".pyo"):
                continue
            entry = zipfile.ZipInfo((Path(SKILL.name) / path.relative_to(SKILL)).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            zipped.writestr(entry, path.read_bytes())
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    with checksum.open("x", encoding="ascii", newline="\n") as output:
        output.write(digest + "  " + archive.name + "\n")
    return archive, checksum


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    for artifact in package(args.output_dir):
        print(artifact)
