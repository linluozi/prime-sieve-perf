"""Deterministic workload metric: Python-level line events executed by the sieve.

Wall-clock numbers move with CPU contention on a shared machine; the number of
bytecode lines CPython actually interprets for a given n does not. This script
counts `line` events with sys.settrace for both implementations, which shows the
mechanism behind the speedup: the baseline marks composites one Python statement
at a time, the optimized version hands each progression to bytearray slice
assignment and never enters a Python loop for it.

Usage:
    python benchmarks/work_count.py --sizes 100000,1000000
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import sys
from typing import Callable

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_function(relative_path: str) -> Callable[[int], list[int]]:
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(path.stem + "_wc", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.prime_sieve


def count_lines(func: Callable[[int], list[int]], n: int) -> int:
    target = func.__code__
    counter = [0]

    def tracer(frame: object, event: str, _arg: object) -> object:
        if getattr(frame, "f_code", None) is target:
            if event == "line":
                counter[0] += 1
            return tracer
        return None

    sys.settrace(tracer)
    try:
        func(n)
    finally:
        sys.settrace(None)
    return counter[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", default="100000,1000000")
    parser.add_argument("--out", default="work_count")
    args = parser.parse_args()
    sizes = [int(item) for item in args.sizes.split(",") if item.strip()]

    baseline = load_function("upstream_snapshot/maths/sieve_of_eratosthenes.py")
    optimized = load_function("maths/sieve_of_eratosthenes.py")

    rows = []
    for n in sizes:
        assert baseline(n) == optimized(n)
        base_lines = count_lines(baseline, n)
        opt_lines = count_lines(optimized, n)
        rows.append(
            {
                "n": n,
                "baseline_python_line_events": base_lines,
                "optimized_python_line_events": opt_lines,
                "ratio": base_lines / opt_lines,
                "baseline_events_per_output_prime": base_lines / len(optimized(n)),
                "optimized_events_per_output_prime": opt_lines / len(optimized(n)),
            }
        )
        print(
            f"n={n:,}: baseline {base_lines:,} line events | "
            f"optimized {opt_lines:,} | {base_lines / opt_lines:.1f}x fewer"
        )

    path = ROOT / "benchmarks" / f"{args.out}.json"
    path.write_text(
        json.dumps(
            {"measured_with": "sys.settrace line events", "rows": rows}, indent=2
        )
    )
    print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
