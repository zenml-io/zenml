# Known fuzz-test contract mismatches

Each tracked mismatch has a narrow exclusion plus a strict `@pytest.mark.xfail(strict=True)` canary test so CI alerts maintainers to remove the exclusion as soon as the underlying bug is fixed.

## Naive timestamps in API responses (#5270)

ZenML's OpenAPI document declares response timestamp fields such as `created` and `updated` with `format: date-time`, while the server serializes timezone-less ISO-8601 strings (for example `2026-09-12T11:52:44.045303`).

Tracked in [zenml-io/zenml#5270](https://github.com/zenml-io/zenml/issues/5270). Request generation uses the unmodified live OpenAPI schema. Response schema validation strips `format: date-time` for Schemathesis, and `validate_naive_datetimes` still asserts that every stripped timestamp field parses via `datetime.fromisoformat(...)` so arbitrary strings cannot slip through. Canary: `test_known_issue_5270_timestamps_include_timezone`.

## Request validation errors return a two-element JSON list (#5269)

ZenML's global `RequestValidationError` handler in `zen_server_api.py` returns `["ValueError", "<message>"]` with status `422` for any FastAPI/Pydantic validation failure (both malformed requests and schema-valid inputs rejected by field validators such as `TagRequest.validate_name_not_uuid`), whereas OpenAPI documents `422` as an `ErrorModel` object.

Tracked in [zenml-io/zenml#5269](https://github.com/zenml-io/zenml/issues/5269). `is_known_request_validation_422` skips response-schema conformance only for allowlisted operations returning status `422` with `["ValueError", "<str>"]`. Canary: `test_known_issue_5269_validation_error_uses_error_model`.

## Unescaped SQL LIKE wildcards in `StrFilter`

`StrFilter` passes raw pattern values directly into `column.like(...)` without escaping `%` or `_`. Generated filter strings omit `%` and `_` from `PORTABLE_TEXT` so literal oracle checks stay accurate, while `test_like_wildcards_in_contains_are_treated_literally` pins the current behavior as a strict `xfail` canary.

## Undocumented `400 Bad Request` domain errors

ZenML's global exception handler maps `ValueError` and malformed-body parsing errors to HTTP `400` with `{"detail": ...}`, while most route decorators only document `200`, `401`, `403`, `404`/`409`, and `422`. `test_api.py` enforces `status_code_conformance` for every status other than a `400` JSON object containing `"detail"`.
