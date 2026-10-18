# NOTICE

This repository contains a derivative work of
[`TheAlgorithms/Python`](https://github.com/TheAlgorithms/Python),
file `maths/sieve_of_eratosthenes.py`.

Upstream copyright and license terms are reproduced in `LICENSE.md` and are not
modified.

## Files and their status

| Path | Status |
|---|---|
| `upstream_snapshot/maths/sieve_of_eratosthenes.py` | Upstream file, **unmodified except for line endings** (CRLF → LF). Algorithm body is byte-identical. |
| `maths/sieve_of_eratosthenes.py` | **Modified.** Same public function, `prime_sieve(num: int) -> list[int]`. |
| `patches/odd_only_bytearray.patch` | Diff from the snapshot to the modified module. |
| everything else | Original work for this repository. |

## What was modified in `maths/sieve_of_eratosthenes.py`

1. Added a four-line provenance note to the module docstring identifying the
   upstream source and describing the performance change.
2. Replaced the full `[True] * (num + 1)` flag list with an odd-only
   `bytearray`, where index `i` represents `2i + 3`.
3. Replaced the per-multiple Python loop that marks composites with extended
   slice assignment on the `bytearray`.
4. Switched `math.sqrt` to `math.isqrt` so the loop bound is exact.
5. Added early returns for `num < 2` and `num == 2`.
6. Rewrote the result assembly to emit `2` followed by the surviving odd
   candidates.

The observable contract is unchanged: same signature, same return type, same
`ValueError` message for non-positive input, same doctests.

## Verification of the "unmodified apart from line endings" claim

```bash
gh api "repos/TheAlgorithms/Python/contents/maths/sieve_of_eratosthenes.py?ref=master" \
  --jq .content | base64 -d | tr -d '\r' > /tmp/upstream_lf.py
cmp /tmp/upstream_lf.py upstream_snapshot/maths/sieve_of_eratosthenes.py
```

`cmp` prints nothing and exits 0 when the two files are identical.
