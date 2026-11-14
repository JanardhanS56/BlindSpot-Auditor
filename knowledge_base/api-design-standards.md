# API Design Standards & REST Conventions

## Endpoint Routing & HTTP Methods
- URIs must use nouns in plural form for resource collections (e.g., `/api/v1/tasks`, `/api/v1/users`).
- HTTP verbs must map directly to semantic operations:
  - `GET`: Read-only, safe, and idempotent.
  - `POST`: Creation of a new sub-resource or non-idempotent action.
  - `PUT`: Complete idempotent replacement of an existing resource.
  - `PATCH`: Partial modification of an existing resource.
  - `DELETE`: Removal of a resource, idempotent.

## Status Codes & Responses
- Return `200 OK` for successful requests returning content.
- Return `201 Created` for successful resource creations, ideally with a `Location` header.
- Return `204 No Content` for successful requests returning no payload (e.g., DELETE).
- Return `400 Bad Request` for client input validation errors.
- Return `401 Unauthorized` for missing or invalid authentication credentials.
- Return `403 Forbidden` when the authenticated identity lacks necessary permissions.
- Return `404 Not Found` when a requested entity does not exist.

## Error Response Format
All error responses must return JSON conforming to RFC 7807 (Problem Details for HTTP APIs):
- Include `code`, `message`, `details`, and `timestamp` fields.
- Stack traces or internal system paths must never be exposed to clients in error bodies.
