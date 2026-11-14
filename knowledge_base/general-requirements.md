# General System & Engineering Requirements

## Defensive Input Handling
- All public functions and entry points must validate inputs before processing.
- Functions accepting lists, iterables, or collections must gracefully handle empty collections without throwing unhandled exceptions.
- Functions processing string inputs must account for empty strings, null values, and leading/trailing whitespace.
- Optional parameters must have explicit, immutable defaults; never use mutable default arguments like `[]` or `{}` in Python function definitions.

## Determinism & Side Effect Control
- Pure functions should be preferred where possible to ensure testability and determinism.
- Functions modifying global state or external systems must be clearly documented with expected side effects.
- Randomness or time-dependent logic must allow seeding or clock injection for deterministic testing.

## Code Structure & Maintainability
- Keep cyclomatic complexity under 10 per function.
- Avoid deeply nested conditionals (maximum nesting depth of 3 levels). Use early guard clauses and returns.
- Keep individual functions focused on a single responsibility (Single Responsibility Principle).
