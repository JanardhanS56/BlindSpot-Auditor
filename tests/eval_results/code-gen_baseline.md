# Evaluation Prompt: code-gen (Single-Agent Baseline)

**Prompt:**
> Build a Python function that validates credit card numbers using the Luhn algorithm. Include error handling, type hints, and unit tests.

**Known Traps:**
- empty string input
- non-numeric characters
- single digit edge case

**Latency:** 4.59s

---

## Generated Output

Below is a **self‑contained** Python module that

1. Implements the Luhn algorithm in a function `is_valid_credit_card`.
2. Performs thorough **type‑checking** and **value‑checking** with clear error messages.
3. Includes **type hints** and a detailed docstring.
4. Comes with a suite of **unit tests** (using the standard library `unittest`).

You can copy the whole snippet into a file called `luhn.py` and run the tests with:

```bash
python -m unittest luhn.py
```

---

## `luhn.py`

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
luhn.py
=======

Utility for validating credit‑card numbers using the Luhn algorithm.

The public API consists of a single function:

    >>> is_valid_credit_card("4539 1488 0343 6467")
    True

The module also contains a comprehensive test‑suite that can be executed
with ``python -m unittest luhn.py``.
"""

from __future__ import annotations

import re
import unittest
from typing import Iterable


def _clean_number(number: str) -> str:
    """
    Remove spaces and hyphens from the input string.

    Parameters
    ----------
    number: str
        The raw credit‑card number as supplied by the caller.

    Returns
    -------
    str
        The number stripped of whitespace and hyphens.

    Raises
    ------
    TypeError
        If *number* is not a string.
    ValueError
        If the cleaned string contains any non‑digit characters.
    """
    if not isinstance(number, str):
        raise TypeError(f"Credit‑card number must be a string, got {type(number)!r}")

    # Allow common formatting characters (space, hyphen) but nothing else.
    cleaned = re.sub(r"[\s-]+", "", number)

    if not cleaned.isdigit():
        raise ValueError(
            "Credit‑card number must contain only digits (spaces and hyphens are allowed)."
        )
    return cleaned


def _digits_reverse_iterable(number: str) -> Iterable[int]:
    """
    Yield the digits of *number* from right‑to‑left as integers.

    This helper makes the Luhn calculation a little easier to read.
    """
    return (int(d) for d in reversed(number))


def is_valid_credit_card(number: str) -> bool:
    """
    Validate a credit‑card number using the Luhn algorithm.

    The function accepts a string that may contain spaces or hyphens
    (e.g. ``"4539 1488 0343 6467"`` or ``"4539-1488-0343-6467"``).  All
    other characters raise a :class:`ValueError`.  Passing a non‑string
    raises a :class:`TypeError`.

    Parameters
    ----------
    number: str
        The credit‑card number to validate.

    Returns
    -------
    bool
        ``True`` if the number passes the Luhn checksum, ``False`` otherwise.

    Examples
    --------
    >>> is_valid_credit_card("4539 1488 0343 6467")
    True
    >>> is_valid_credit_card("1234 5678 9012 3456")
    False
    """
    cleaned = _clean_number(number)

    # Luhn algorithm:
    # 1. Starting from the rightmost digit, double every second digit.
    # 2. If the doubling produces a number > 9, subtract 9 (or equivalently sum its digits).
    # 3. Sum all the digits (modified and untouched).
    # 4. The number is valid if the total modulo 10 is 0.
    total = 0
    for i, digit in enumerate(_digits_reverse_iterable(cleaned)):
        if i % 2 == 1:                     # every second digit (0‑based index)
            doubled = digit * 2
            total += doubled - 9 if doubled > 9 else doubled
        else:
            total += digit

    return total % 10 == 0


# ----------------------------------------------------------------------
# Unit tests
# ----------------------------------------------------------------------
class TestLuhnAlgorithm(unittest.TestCase):
    """Test suite for the Luhn validation function."""

    # ------------------------------------------------------------------
    # Positive (valid) test vectors – taken from real card prefixes
    # ------------------------------------------------------------------
    VALID_NUMBERS = [
        "4539 1488 0343 6467",   # Visa
        "6011 1111 1111 1117",   # Discover
        "3714 496353 98431",     # American Express (no spaces)
        "5555-5555-5555-4444",   # MasterCard (with hyphens)
        "4111111111111111",      # Visa (plain)
        "4222222222222",         # Visa 13‑digit
    ]

    # ------------------------------------------------------------------
    # Negative (invalid) test vectors
    # ------------------------------------------------------------------
    INVALID_NUMBERS = [
        "4539 1488 0343 6468",   # Same as first but last digit altered
        "6011 1111 1111 1110",
        "3714 496353 98432",
        "5555-5555-5555-4440",
        "4111111111111112",
        "1234567890123456",      # Random digits, fails Luhn
        "0000 0000 0000 0000",   # Edge case – passes Luhn but not a real card; we still treat it as valid
    ]

    # ------------------------------------------------------------------
    # Tests for correct handling of whitespace / hyphens
    # ------------------------------------------------------------------
    def test_cleaning_and_validation(self):
        for raw, expected in [
            ("4539 1488 0343 6467", True),
            ("4539-1488-0343-6467", True),
            ("  4539 1488 0343 6467  ", True),
            ("4539 1488 0343 6468", False),
        ]:
            self.assertEqual(is_valid_credit_card(raw), expected)

    # ------------------------------------------------------------------
    # Positive cases
    #
