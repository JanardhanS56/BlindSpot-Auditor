# Code Review Checklist & Audit Criteria

## Correctness & Edge Cases
- Check for zero or negative values in arithmetic operations, especially division and modulo.
- Verify behavior when sequences, strings, lists, or dictionaries are empty or None.
- Ensure loop boundary conditions (off-by-one errors) and index access boundaries are guarded.
- Check that recursion base cases terminate under all branch paths.

## Security & Injection Safeguards
- All SQL queries must use parameterized queries or ORM bindings; raw string interpolation with user input is forbidden.
- Command executions and subprocess calls must avoid `shell=True` and validate arguments.
- Sensitive information such as API keys, database credentials, and tokens must never be hardcoded in source code.
- File system access must prevent path traversal attacks by resolving and validating paths against an allowed base directory.

## Resource Management & Concurrency
- All file handles, database connections, and sockets must be enclosed in context managers (`with` or `async with`).
- Async functions must avoid blocking synchronous operations (e.g., standard `time.sleep()`, synchronous `requests.get()`); use `asyncio.sleep()` and async HTTP clients like `httpx.AsyncClient`.
- Shared mutable state in concurrent workflows must be protected by locks or queues.
