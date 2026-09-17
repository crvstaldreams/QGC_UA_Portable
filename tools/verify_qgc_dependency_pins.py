#!/usr/bin/env python3
import argparse
import re
from pathlib import Path

PX4_GPSDRIVERS_PIN = "caf5158061bd10e79c9f042abb62c86bc6f3e7a7"
PACKAGE_RE = re.compile(r"CPMAddPackage\((?P<body>.*?)\)", re.DOTALL)
TAG_RE = re.compile(r"\bGIT_TAG\s+([^\s\)]+)")


def verify_px4_gpsdrivers(cmake_text: str) -> None:
    for match in PACKAGE_RE.finditer(cmake_text):
        body = match.group("body")
        if "GITHUB_REPOSITORY PX4/PX4-GPSDrivers" not in body:
            continue

        tag = TAG_RE.search(body)
        if not tag:
            raise ValueError("PX4-GPSDrivers CPM package has no GIT_TAG")

        actual = tag.group(1)
        if actual != PX4_GPSDRIVERS_PIN:
            raise ValueError(
                f"PX4-GPSDrivers must be pinned to {PX4_GPSDRIVERS_PIN}, got {actual}"
            )
        return

    raise ValueError("PX4-GPSDrivers CPM package not found")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify reproducible external dependency pins in the prepared QGC source tree."
    )
    parser.add_argument("--source-root", required=True, type=Path)
    args = parser.parse_args()

    cmake_path = args.source_root / "src" / "GPS" / "CMakeLists.txt"
    try:
        verify_px4_gpsdrivers(cmake_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"dependency pin verification failed: {exc}")
        return 1

    print(f"PX4-GPSDrivers pin verified: {PX4_GPSDRIVERS_PIN}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
