"""Regenerate patches/odd_only_bytearray.patch from the two module trees.

Run this after touching either module; the patch must stay byte-exact with
respect to `maths/sieve_of_eratosthenes.py` when applied to the snapshot.
"""

from __future__ import annotations

import difflib
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "upstream_snapshot" / "maths" / "sieve_of_eratosthenes.py"
OPTIMIZED = ROOT / "maths" / "sieve_of_eratosthenes.py"
PATCH = ROOT / "patches" / "odd_only_bytearray.patch"


def main() -> None:
    before = SNAPSHOT.read_text(encoding="utf-8").splitlines(keepends=True)
    after = OPTIMIZED.read_text(encoding="utf-8").splitlines(keepends=True)
    diff = difflib.unified_diff(
        before,
        after,
        fromfile="a/maths/sieve_of_eratosthenes.py",
        tofile="b/maths/sieve_of_eratosthenes.py",
        n=3,
    )
    text = "".join(diff)
    if not text:
        raise SystemExit("no differences: the patch would be empty")
    PATCH.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {PATCH.relative_to(ROOT)} ({len(text)} bytes)")


if __name__ == "__main__":
    main()
