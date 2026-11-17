# Evaluation Prompt: code-gen (AKILI-SPECS Triad)

**Prompt:**
> Build a Python function that validates credit card numbers using the Luhn algorithm. Include error handling, type hints, and unit tests.

**Known Traps:**
- empty string input
- non-numeric characters
- single digit edge case

**Expected Triad Advantage:**
Reviewer catches missing edge cases

**Latency:** 130.12s

**Tasks Decomposed:** 1
**Passed Directly:** 0
**Retried & Passed:** 0
**Force Merged:** 1
**Issues Resolved:** 5 / 8

**Grounding References Cited:**
- general best practices for Python module design
- general best practices for unit testing with unittest
- general best practices for implementing the Luhn algorithm
- general best practices for Python module design: provide the advertised public API and include tests (PEP 8, PEP 257, and typical unit‑test conventions).
- general best practices – Python module design, complete function implementations, and inclusion of unit tests

---

## Generated Output

# credit_card_validator.py
```python
"""Utility module for validating credit‑card numbers using the Luhn algorithm.

The public API consists of a single function:

```python
validate_credit_card(number: str) -> bool
```

It returns ``True`` when the supplied ``number`` passes the Luhn checksum and ``False`` otherwise.

The module also contains a small ``unittest`` test‑suite that can be executed with
``python -m unittest credit_card_validator.py``.
"""

from __future__ import annotations

import re
import unittest
from typing import Final

__all__: Final = ["validate_credit_card"]

# ---------------------------------------------------------------------------
# Helper functions (internal use only)
# ---------------------------------------------------------------------------

def _clean_number(number: str) -> str:
    """Return a digit‑only representation of *number*.

    The function removes spaces and hyphens – the two characters most commonly
    used to format credit‑card numbers for readability.  If any other non‑digit
    characters are present, a :class:`ValueError` is raised.

    Parameters
    ----------
    number:
        The raw credit‑card number supplied by the caller.

    Returns
    -------
    str
        A string containing only the numeric characters of ``number``.

    Raises
    ------
    ValueError
        If ``number`` contains characters other than digits, spaces or hyphens.
    """
    if not isinstance(number, str):
        raise TypeError("Credit‑card number must be provided as a string")

    # Remove common visual separators.
    cleaned = re.sub(r"[\s-]+", "", number)

    if not cleaned.isdigit():
        raise ValueError("Credit‑card number must contain only digits after cleaning")
    return cleaned


def _luhn_checksum(digits: str) -> int:
    """Calculate the Luhn checksum for a string of digits.

    The algorithm works as follows (see Wikipedia for the formal description):

    1. Starting from the rightmost digit and moving left, double every second
       digit.
    2. If the doubling produces a number greater than 9, subtract 9 from it.
    3. Sum all the resulting digits.
    4. The checksum is the sum modulo 10.

    A valid credit‑card number yields a checksum of ``0
