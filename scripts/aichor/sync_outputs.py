#!/usr/bin/env python3
"""Sync a local output tree to an AIchor output destination."""

from __future__ import annotations

import argparse
import posixpath
import shutil
import sys
from pathlib import Path


def iter_files(source: Path) -> list[Path]:
    if not source.exists():
        return []
    return sorted(path for path in source.rglob("*") if path.is_file())


def sync_to_remote(source: Path, destination: str) -> int:
    import fsspec

    fs, root = fsspec.core.url_to_fs(destination)
    root = root.rstrip("/")
    count = 0
    for path in iter_files(source):
        rel = path.relative_to(source).as_posix()
        target = posixpath.join(root, rel)
        parent = posixpath.dirname(target)
        if parent:
            fs.makedirs(parent, exist_ok=True)
        fs.put_file(str(path), target)
        count += 1
        print(f"Uploaded {path} -> {destination.rstrip('/')}/{rel}")
    return count


def sync_to_local(source: Path, destination: Path) -> int:
    count = 0
    for path in iter_files(source):
        rel = path.relative_to(source)
        target = destination / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        count += 1
        print(f"Copied {path} -> {target}")
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--destination", required=True)
    args = parser.parse_args()

    if not args.source.exists():
        print(f"Source output directory does not exist: {args.source}", file=sys.stderr)
        return 0

    if "://" in args.destination:
        count = sync_to_remote(args.source, args.destination)
    else:
        count = sync_to_local(args.source, Path(args.destination))

    print(f"Synced {count} files from {args.source} to {args.destination}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
