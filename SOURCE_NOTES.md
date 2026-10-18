# Source notes

- Upstream project: [TheAlgorithms/Python](https://github.com/TheAlgorithms/Python)
- Target file: `maths/sieve_of_eratosthenes.py`
- Ref used: `master`
- Blob SHA: `3923dc3e16120f4b5937ed41abab14ccc591a923`
- Blob size: 1717 bytes (CRLF line endings)
- Retrieved: 2026-10-18

## Line endings

The upstream blob uses CRLF. `upstream_snapshot/maths/sieve_of_eratosthenes.py`
stores the same bytes with `\r` removed, because the patch in `patches/` is a
unified diff with LF endings and `patch` would otherwise report success while
leaving the file one byte per line short.

Everything else in the snapshot is untouched: no reformatting, no comment
changes, no extra blank lines. After normalizing line endings, `cmp` against the
upstream blob passes.

## Reproducing the snapshot

```bash
gh api "repos/TheAlgorithms/Python/contents/maths/sieve_of_eratosthenes.py?ref=master" \
  --jq .content | base64 -d | tr -d '\r' > upstream_snapshot/maths/sieve_of_eratosthenes.py
```

If upstream moves, re-pin the blob SHA above and regenerate the patch with
`python scripts/make_patch.py`; the patch would otherwise no longer apply.
