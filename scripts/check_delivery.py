"""Delivery self-check: line endings, patch/working-tree agreement, optional apply test.

Run this before publishing. It catches the three things that silently rot when a
module is edited but the patch is not regenerated.

Usage:
    python scripts/check_delivery.py
"""

from __future__ import annotations

import difflib
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "upstream_snapshot" / "maths" / "sieve_of_eratosthenes.py"
OPTIMIZED = ROOT / "maths" / "sieve_of_eratosthenes.py"
PATCH = ROOT / "patches" / "odd_only_bytearray.patch"


def main() -> None:
    failures: list[str] = []

    print("1. line endings")
    for path in (SNAPSHOT, OPTIMIZED, PATCH):
        data = path.read_bytes()
        ending = "CRLF" if b"\r\n" in data else "LF"
        if ending == "CRLF":
            failures.append(f"{path.relative_to(ROOT)} contains CRLF")
        print(f"   {path.relative_to(ROOT)}: {len(data)} bytes, {ending}")

    print("2. patch matches the working tree")
    before = SNAPSHOT.read_text(encoding="utf-8").splitlines(keepends=True)
    after = OPTIMIZED.read_text(encoding="utf-8").splitlines(keepends=True)
    expected = "".join(
        difflib.unified_diff(
            before,
            after,
            fromfile="a/maths/sieve_of_eratosthenes.py",
            tofile="b/maths/sieve_of_eratosthenes.py",
            n=3,
        )
    )
    actual = PATCH.read_text(encoding="utf-8")
    if expected != actual:
        failures.append("patch is stale: rerun scripts/make_patch.py")
        print("   STALE")
    else:
        print(f"   ok ({len(actual)} bytes)")

    print("3. patch applies back to the optimized file")
    patch_cmd = shutil.which("patch")
    if patch_cmd is None:
        print("   skipped: no `patch` binary on PATH")
    else:
        with tempfile.TemporaryDirectory() as tmp:
            work = pathlib.Path(tmp) / "maths"
            work.mkdir()
            shutil.copy2(SNAPSHOT, work / "sieve_of_eratosthenes.py")
            result = subprocess.run(
                [patch_cmd, "--binary", "-p1", "-i", str(PATCH)],
                cwd=tmp,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                failures.append(f"patch failed: {result.stdout}{result.stderr}")
                print("   FAILED")
            elif (
                work / "sieve_of_eratosthenes.py"
            ).read_bytes() != OPTIMIZED.read_bytes():
                failures.append(
                    "patched result differs from maths/sieve_of_eratosthenes.py"
                )
                print("   MISMATCH")
            else:
                print("   ok (byte-identical)")

    print()
    if failures:
        print("RESULT: FAIL")
        for line in failures:
            print("  -", line)
        sys.exit(1)
    print("RESULT: PASS")


if __name__ == "__main__":
    main()
