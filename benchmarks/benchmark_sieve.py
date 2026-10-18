"""Paired baseline/optimized benchmark for the odd-only bytearray sieve.

Each size is measured in one process, with both implementations interleaved
round by round and the arm order flipped every round. Medians are reported, and
every raw sample is written to JSON so the ratio can be re-derived.

Usage:
    python benchmarks/benchmark_sieve.py
    python benchmarks/benchmark_sieve.py --sizes 100000 --runs 7 --quick
    python benchmarks/benchmark_sieve.py --aa      # noise floor control
"""

from __future__ import annotations

import argparse
import csv
import gc
import importlib.util
import json
import pathlib
import platform
import statistics
import sys
import time
import tracemalloc
from typing import Callable

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_function(relative_path: str) -> Callable[[int], list[int]]:
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(path.stem + "_bench", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.prime_sieve


def timed_run(
    func: Callable[[int], list[int]], n: int
) -> tuple[float, tuple[int, int, int]]:
    start = time.perf_counter()
    primes = func(n)
    elapsed = time.perf_counter() - start
    return elapsed, (
        len(primes),
        primes[0] if primes else 0,
        primes[-1] if primes else 0,
    )


def peak_traced_bytes(func: Callable[[int], list[int]], n: int) -> int:
    gc.collect()
    tracemalloc.start()
    result = func(n)
    _, peak = tracemalloc.get_traced_memory()
    del result
    tracemalloc.stop()
    return peak


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", default="100000,500000,1000000")
    parser.add_argument("--runs", type=int, default=15)
    parser.add_argument(
        "--stat",
        choices=("median", "min"),
        default="median",
        help="statistic per arm; min is best-of-N and is more robust to CPU contention",
    )
    parser.add_argument(
        "--quick", action="store_true", help="smoke run; writes *_quick.json"
    )
    parser.add_argument(
        "--aa", action="store_true", help="compare baseline against a byte copy"
    )
    parser.add_argument("--out", default=None, help="output stem under benchmarks/")
    args = parser.parse_args()
    if args.runs < 3:
        parser.error("use at least 3 runs to obtain a meaningful median")
    sizes = [int(item) for item in args.sizes.split(",") if item.strip()]

    arm_a = load_function("upstream_snapshot/maths/sieve_of_eratosthenes.py")
    if args.aa:
        arm_b = load_function("upstream_snapshot/maths/_copy_of_baseline.py")
    else:
        arm_b = load_function("maths/sieve_of_eratosthenes.py")
    arms = {"baseline": arm_a, "optimized": arm_b}

    results = {
        "environment": {
            "python": sys.version,
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "runs_per_arm": args.runs,
            "statistic_per_arm": args.stat,
            "warmups_per_arm_and_size": 1,
            "order": "alternating, reversed every round",
            "timer": "time.perf_counter",
            "memory_method": (
                "tracemalloc peak traced allocation, measured outside the timing loop"
            ),
            "aa_control": args.aa,
            "sizes": sizes,
        },
        "benchmarks": [],
    }

    rows: list[dict[str, object]] = []
    for n in sizes:
        checksums: dict[str, tuple[int, int, int]] = {}
        for name, func in arms.items():
            _, checksums[name] = timed_run(func, n)
        if checksums["baseline"] != checksums["optimized"]:
            raise AssertionError(f"output mismatch for n={n}: {checksums}")

        samples: dict[str, list[float]] = {name: [] for name in arms}
        names = list(arms)
        for repeat in range(args.runs):
            ordered = names if repeat % 2 == 0 else list(reversed(names))
            for name in ordered:
                gc.collect()
                elapsed, checksum = timed_run(arms[name], n)
                if checksum != checksums[name]:
                    raise AssertionError(f"nondeterministic output for {name}, n={n}")
                samples[name].append(elapsed)

        peaks = {name: peak_traced_bytes(func, n) for name, func in arms.items()}
        aggregate = statistics.median if args.stat == "median" else min
        medians = {name: aggregate(values) for name, values in samples.items()}
        speedup = medians["baseline"] / medians["optimized"]
        per_round = statistics.median(
            [a / b for a, b in zip(samples["baseline"], samples["optimized"])]
        )
        reduction = 100 * (1 - peaks["optimized"] / peaks["baseline"])
        results["benchmarks"].append(
            {
                "n": n,
                "prime_count": checksums["baseline"][0],
                "last_prime": checksums["baseline"][2],
                "baseline_seconds_median": medians["baseline"],
                "baseline_seconds_samples": samples["baseline"],
                "optimized_seconds_median": medians["optimized"],
                "optimized_seconds_samples": samples["optimized"],
                "speedup_ratio_of_medians": speedup,
                "speedup_median_of_per_round_ratios": per_round,
                "baseline_peak_traced_bytes": peaks["baseline"],
                "optimized_peak_traced_bytes": peaks["optimized"],
                "peak_traced_reduction_percent": reduction,
            }
        )
        rows.append(
            {
                "n": n,
                "prime_count": checksums["baseline"][0],
                "baseline_median_ms": round(medians["baseline"] * 1000, 3),
                "optimized_median_ms": round(medians["optimized"] * 1000, 3),
                "speedup_x": round(speedup, 3),
                "speedup_per_round_median_x": round(per_round, 3),
                "baseline_peak_MiB": round(peaks["baseline"] / 1024**2, 3),
                "optimized_peak_MiB": round(peaks["optimized"] / 1024**2, 3),
                "peak_reduction_percent": round(reduction, 2),
            }
        )
        print(
            f"n={n:,}: baseline {medians['baseline'] * 1000:.3f} ms | "
            f"optimized {medians['optimized'] * 1000:.3f} ms | "
            f"speedup {speedup:.3f}x (per-round median {per_round:.3f}x) | "
            f"peak -{reduction:.2f}%"
        )

    suffix = "_quick" if args.quick else ""
    stem = args.out or f"results{suffix}"
    json_path = ROOT / "benchmarks" / f"{stem}.json"
    csv_path = ROOT / "benchmarks" / f"{stem}.csv"
    json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {json_path.relative_to(ROOT)} and {csv_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
