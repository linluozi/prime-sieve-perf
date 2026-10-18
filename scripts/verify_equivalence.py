"""Deep equivalence check between the snapshot and the optimized module.

Behavioural unit tests stop at n=10,000 because the baseline is slow. This script
goes further and uses evidence that does not depend on the baseline being right:

1. exhaustive comparison for every n in a contiguous range
2. boundaries where the marking start index lands on the last slot (squares) and
   where the even upper bound changes parity (powers of two)
3. random large inputs, with every reported prime re-checked by Miller-Rabin
4. published pi(x) values, which are independent of both implementations
5. the slice-arithmetic identity: mark_count must equal the true bytearray slice
   length, otherwise the assignment would silently resize the flag array

Usage:
    python scripts/verify_equivalence.py
    python scripts/verify_equivalence.py --max-n 2000000 --random 200 --identities
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import pathlib
import random
import sys
from typing import Callable

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_function(relative_path: str, tag: str) -> Callable[[int], list[int]]:
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(f"{path.stem}_{tag}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.prime_sieve


def is_prime(n: int) -> bool:
    """Deterministic Miller-Rabin for n < 3.3e24 with these bases."""
    if n < 2:
        return False
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if n % p == 0:
            return n == p
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for a in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def primes_upto(n: int) -> list[int]:
    flags = bytearray(b"\x01") * (n + 1)
    flags[0:2] = b"\x00\x00"
    for i in range(2, math.isqrt(n) + 1):
        if flags[i]:
            flags[i * i :: i] = b"\x00" * len(range(i * i, n + 1, i))
    return [i for i, flag in enumerate(flags) if flag]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exhaustive", type=int, default=6000)
    parser.add_argument("--random", type=int, default=60, dest="random_cases")
    parser.add_argument("--max-n", type=int, default=3_000_000)
    parser.add_argument(
        "--identities",
        action="store_true",
        help="also verify slice arithmetic up to --identity-limit",
    )
    parser.add_argument("--identity-limit", type=int, default=2_000_000)
    args = parser.parse_args()

    baseline = load_function("upstream_snapshot/maths/sieve_of_eratosthenes.py", "b")
    optimized = load_function("maths/sieve_of_eratosthenes.py", "o")
    failures: list[str] = []

    print(f"1. exhaustive comparison, n = 0..{args.exhaustive:,}")
    for n in range(args.exhaustive + 1):
        if n <= 0:
            messages = []
            for func in (baseline, optimized):
                try:
                    func(n)
                    messages.append(None)
                except Exception as exc:
                    messages.append(f"{type(exc).__name__}: {exc}")
            if messages[0] != messages[1] or messages[0] is None:
                failures.append(f"n={n}: error contract differs: {messages}")
        elif baseline(n) != optimized(n):
            failures.append(f"n={n}: output differs")
    print(f"   failures: {len(failures)}")

    print("2. square and power-of-two boundaries")
    before = len(failures)
    for k in range(2, 1200):
        for n in range(k * k - 2, k * k + 3):
            if n > 0 and baseline(n) != optimized(n):
                failures.append(f"n={n}: output differs at square boundary")
    power = 2
    while power <= 1 << 22:
        for n in (power - 1, power, power + 1):
            if baseline(n) != optimized(n):
                failures.append(f"n={n}: output differs at power-of-two boundary")
        power *= 2
    print(f"   failures added: {len(failures) - before}")

    print(
        f"3. {args.random_cases} random inputs up to {args.max_n:,}, values re-checked"
    )
    before = len(failures)
    rng = random.Random(20261018)
    for _ in range(args.random_cases):
        n = rng.randrange(1, args.max_n)
        got, expected = optimized(n), baseline(n)
        if got != expected:
            failures.append(f"n={n}: output differs")
            continue
        if got != sorted(set(got)) or (got and got[-1] > n):
            failures.append(f"n={n}: not a sorted unique subset of [1, n]")
        for value in got:
            if not is_prime(value):
                failures.append(f"n={n}: composite {value} reported as prime")
                break
    print(f"   failures added: {len(failures) - before}")

    print("4. published pi(x) reference values")
    before = len(failures)
    for n, expected_count in (
        (10, 4),
        (100, 25),
        (1_000, 168),
        (10_000, 1229),
        (100_000, 9592),
        (1_000_000, 78_498),
        (10_000_000, 664_579),
    ):
        count = len(optimized(n))
        status = "ok" if count == expected_count else "MISMATCH"
        print(f"   n={n:>9,}  pi={count:>7,}  expected={expected_count:>7,}  {status}")
        if count != expected_count:
            failures.append(f"n={n}: pi(x) {count} != {expected_count}")
    print(f"   failures added: {len(failures) - before}")

    if args.identities:
        limit = args.identity_limit
        print(f"5. slice arithmetic identity, every n <= {limit:,}")
        before = len(failures)
        odd_primes = [p for p in primes_upto(math.isqrt(limit) + 1) if p >= 3]
        for num in range(3, limit + 1):
            candidate_count = (num - 1) // 2
            limit_root = math.isqrt(num)
            last_index = (limit_root - 3) // 2
            reached = 2 * last_index + 3 if last_index >= 0 else 1
            for p in odd_primes:
                if p > limit_root:
                    break
                if p > reached:
                    failures.append(f"n={num}: prime {p} <= isqrt(n) never visited")
                    break
                start = (p * p - 3) // 2
                if start < candidate_count:
                    true_length = len(range(start, candidate_count, p))
                    mark_count = (candidate_count - start + p - 1) // p
                    if true_length != mark_count:
                        failures.append(
                            f"n={num} p={p}: mark_count {mark_count} != {true_length}"
                        )
            if len(failures) > 8:
                break
        print(f"   failures added: {len(failures) - before}")

    print()
    if failures:
        print("RESULT: FAIL")
        for line in failures[:10]:
            print("  -", line)
        sys.exit(1)
    print("RESULT: PASS (all checks clean)")


if __name__ == "__main__":
    main()
