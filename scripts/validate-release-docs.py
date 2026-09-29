#!/usr/bin/env python3
"""Validate rendered SDK documentation against its public release marker."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.request
from pathlib import Path
from typing import Any

SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COORDINATE = {"group": "com.permate", "artifact": "permate-attribution"}
REPOSITORY_ROOT = "https://sdk.pmcdn1.com/maven/releases/"


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def expected_urls(version: str) -> set[str]:
    prefix = f"{REPOSITORY_ROOT}com/permate/permate-attribution/{version}/permate-attribution-{version}"
    return {
        f"{prefix}.{suffix}{sidecar}"
        for suffix in ("aar", "pom", "module")
        for sidecar in ("", ".sha256")
    }


def validate(root: Path, online: bool) -> None:
    state = load_object(root / "release-state.json")
    index = (root / "index.html").read_text(encoding="utf-8")
    if state.get("schemaVersion") != 1 or state.get("recordType") != "android-public-docs-release":
        raise ValueError("release state schema identity is invalid")
    version = state.get("version")
    if not isinstance(version, str) or not SEMVER_RE.fullmatch(version):
        raise ValueError("release state version must be stable SemVer")
    if state.get("coordinate") != COORDINATE or state.get("repositoryRoot") != REPOSITORY_ROOT:
        raise ValueError("release state stable contract differs")
    for field in ("markerSha256", "publicAuditSha256"):
        if not isinstance(state.get(field), str) or not SHA256_RE.fullmatch(state[field]):
            raise ValueError(f"release state {field} is invalid")

    marker_url = f"{REPOSITORY_ROOT}com/permate/permate-attribution/{version}/release.json"
    if state.get("markerUrl") != marker_url:
        raise ValueError("release state marker URL is invalid")
    required_text = [
        f"com.permate:permate-attribution:{version}",
        marker_url,
        version,
    ]
    for value in required_text:
        if value not in index:
            raise ValueError(f"rendered docs omit {value}")

    objects = state.get("publicObjects")
    if not isinstance(objects, list) or len(objects) != 6:
        raise ValueError("release state must contain exactly six Maven objects")
    observed = set()
    for item in objects:
        if not isinstance(item, dict):
            raise ValueError("release state object is invalid")
        url = item.get("downloadUrl")
        digest = item.get("sha256")
        size = item.get("sizeBytes")
        if not isinstance(url, str) or not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            raise ValueError("release state object URL or digest is invalid")
        if not isinstance(size, int) or size <= 0:
            raise ValueError("release state object size is invalid")
        observed.add(url)
        if not url.endswith(".sha256") and url not in index:
            raise ValueError(f"rendered docs omit public artifact {url}")
    if observed != expected_urls(version):
        raise ValueError("release state inventory is not the exact six-object Maven set")

    if not online:
        return
    with urllib.request.urlopen(marker_url, timeout=30) as response:
        marker_bytes = response.read()
    if hashlib.sha256(marker_bytes).hexdigest() != state["markerSha256"]:
        raise ValueError("public release marker digest differs from release state")
    marker = json.loads(marker_bytes)
    if marker.get("version") != version or marker.get("coordinate") != COORDINATE:
        raise ValueError("public release marker identity differs from release state")
    marker_objects = {
        (item.get("downloadUrl"), item.get("sha256"), item.get("sizeBytes"))
        for item in marker.get("publicObjects", [])
        if isinstance(item, dict)
    }
    state_objects = {
        (item["downloadUrl"], item["sha256"], item["sizeBytes"])
        for item in objects
    }
    if marker_objects != state_objects:
        raise ValueError("public release marker inventory differs from release state")
    for url in observed:
        request = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status != 200:
                raise ValueError(f"public artifact is unavailable: {url}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--online", action="store_true")
    args = parser.parse_args()
    validate(args.root, args.online)
    print("public release documentation is valid")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1)
