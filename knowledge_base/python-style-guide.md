# Python Style Guide & Conventions

## Type Hints & Annotations
All public functions, class methods, and module-level variables must include complete type annotations.
- Use native modern Python 3.10+ typing syntax (e.g., `list[str]`, `dict[str, Any]`, `str | None` instead of `Optional[str]`).
- Every function signature must explicitly declare return types, including `-> None` for procedures.
- Avoid raw untyped `Any` where a more specific type or generic TypeVar can be defined.

## Docstrings & Documentation
Every public module, class, method, and function must include a clear docstring conforming to PEP 257.
- Docstrings must state purpose, parameters, return values, and possible raised exceptions.
- Functions longer than 15 lines should document internal assumptions and algorithms.

## Naming Conventions
- Variables, functions, and module names must use `snake_case`.
- Classes and custom Exception types must use `PascalCase`.
- Constants must use `UPPER_SNAKE_CASE`.
- Private methods and internal variables must start with a leading underscore `_`.

## Error Handling & Defensive Programming
- Never catch generic `Exception` without re-raising or logging the full traceback with contextual metadata.
- Avoid bare `except:` blocks under all circumstances.
- All I/O operations (network, file, database) must specify timeouts and include explicit recovery or retry mechanisms.
- Functions must raise descriptive custom exceptions rather than generic `ValueError` or `RuntimeError` when failing domain validation.
