from __future__ import annotations

import importlib.util
import inspect
import pathlib
import tracemalloc
import unittest
from typing import Callable

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_function(relative_path: str) -> Callable[[int], list[int]]:
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(path.stem + "_test", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.prime_sieve


baseline = load_function("upstream_snapshot/maths/sieve_of_eratosthenes.py")
optimized = load_function("maths/sieve_of_eratosthenes.py")


def peak_traced_bytes(func: Callable[[int], list[int]], n: int) -> int:
    tracemalloc.start()
    func(n)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak


class PrimeSieveBehaviourTests(unittest.TestCase):
    def test_documented_examples(self) -> None:
        expected = {
            50: [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47],
            25: [2, 3, 5, 7, 11, 13, 17, 19, 23],
            10: [2, 3, 5, 7],
            9: [2, 3, 5, 7],
            2: [2],
            1: [],
        }
        for n, primes in expected.items():
            with self.subTest(n=n):
                self.assertEqual(baseline(n), primes)
                self.assertEqual(optimized(n), primes)

    def test_matches_baseline_over_range(self) -> None:
        for n in range(1, 10_001):
            with self.subTest(n=n):
                self.assertEqual(optimized(n), baseline(n))

    def test_matches_baseline_at_boundaries(self) -> None:
        # Squares are where the marking start index p * p lands exactly on the
        # last slot; powers of two exercise the even-upper-bound arithmetic.
        cases: list[int] = []
        for k in range(2, 201):
            cases.extend(n for n in (k * k - 2, k * k - 1, k * k, k * k + 1) if n > 0)
        power = 2
        while power <= 1 << 17:
            cases.extend((power - 1, power, power + 1))
            power *= 2
        for n in sorted(set(cases)):
            with self.subTest(n=n):
                self.assertEqual(optimized(n), baseline(n))

    def test_invalid_inputs_preserve_value_error(self) -> None:
        for n in (-10, -1, 0):
            with self.subTest(n=n):
                with self.assertRaisesRegex(ValueError, str(n)):
                    baseline(n)
                with self.assertRaisesRegex(ValueError, str(n)):
                    optimized(n)

    def test_prime_output_invariants(self) -> None:
        values = optimized(20_000)
        self.assertEqual(values, sorted(set(values)))
        self.assertEqual(values[0], 2)
        self.assertEqual(values[-1], 19_997)
        for value in values:
            largest_divisor = int(value**0.5)
            self.assertTrue(all(value % d for d in range(2, largest_divisor + 1)))

    def test_known_prime_counts(self) -> None:
        known = {
            10: 4,
            100: 25,
            1_000: 168,
            10_000: 1229,
            100_000: 9592,
            1_000_000: 78_498,
        }
        for n, count in known.items():
            with self.subTest(n=n):
                self.assertEqual(len(optimized(n)), count)


class PrimeSieveStructureTests(unittest.TestCase):
    """Fail if the optimization itself is removed, not just if it breaks.

    The behaviour tests above pass for both implementations, because the
    optimization is output-preserving by design. Without the assertions below, a
    silent revert to the baseline would keep the whole suite green.
    """

    def test_optimized_uses_odd_only_bytearray(self) -> None:
        source = inspect.getsource(optimized)
        self.assertIn("bytearray", source, "odd-only bytearray storage is missing")
        self.assertIn("isqrt", source, "integer square root path is missing")
        self.assertNotIn("sieve = [True]", source, "baseline flag list is back")

    def test_optimized_peak_allocation_is_well_below_baseline(self) -> None:
        n = 200_000
        optimized_peak = peak_traced_bytes(optimized, n)
        baseline_peak = peak_traced_bytes(baseline, n)
        self.assertLess(
            optimized_peak,
            0.5 * baseline_peak,
            f"compact flag array expected: {optimized_peak} vs {baseline_peak} bytes",
        )


if __name__ == "__main__":
    unittest.main()
