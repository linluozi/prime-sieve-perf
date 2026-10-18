"""
Sieve of Eratosthones

The sieve of Eratosthenes is an algorithm used to find prime numbers, less than or
equal to a given value.
Illustration:
https://upload.wikimedia.org/wikipedia/commons/b/b9/Sieve_of_Eratosthenes_animation.gif
Reference: https://en.wikipedia.org/wiki/Sieve_of_Eratosthenes

doctest provider: Bruno Simas Hadlich (https://github.com/brunohadlich)
Also thanks to Dmitry (https://github.com/LizardWizzard) for finding the problem

Performance modification in this derivative: odd-only candidate storage in a
bytearray, with composite marking moved into C-level slice assignment.
Upstream: https://github.com/TheAlgorithms/Python/blob/master/maths/sieve_of_eratosthenes.py
"""

from __future__ import annotations

import math


def prime_sieve(num: int) -> list[int]:
    """
    Returns a list with all prime numbers up to n.

    >>> prime_sieve(50)
    [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]
    >>> prime_sieve(25)
    [2, 3, 5, 7, 11, 13, 17, 19, 23]
    >>> prime_sieve(10)
    [2, 3, 5, 7]
    >>> prime_sieve(9)
    [2, 3, 5, 7]
    >>> prime_sieve(2)
    [2]
    >>> prime_sieve(1)
    []
    """

    if num <= 0:
        msg = f"{num}: Invalid input, please enter a positive integer."
        raise ValueError(msg)

    if num < 2:
        return []
    if num == 2:
        return [2]

    # Index i stands for the odd integer 2 * i + 3, so the flag array holds about
    # half as many slots as a full [0, num] table, and each flag is one byte
    # instead of one pointer.
    candidate_count = (num - 1) // 2
    sieve = bytearray(b"\x01") * candidate_count
    limit = math.isqrt(num)

    # Mark composites from p * p onwards. Slice assignment performs the marking
    # loop in C, and the stride is p because odd indices advance by 2 in value.
    for index in range((limit - 3) // 2 + 1):
        if sieve[index]:
            p = 2 * index + 3
            start = (p * p - 3) // 2
            if start < candidate_count:
                mark_count = (candidate_count - start + p - 1) // p
                sieve[start::p] = b"\x00" * mark_count

    return [2, *(2 * index + 3 for index, is_prime in enumerate(sieve) if is_prime)]


if __name__ == "__main__":
    print(prime_sieve(int(input("Enter a positive integer: ").strip())))
