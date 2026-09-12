# Known fuzz-test contract mismatches

## Naive timestamps in API responses

ZenML's live OpenAPI document declares response timestamp fields such as `created` and `updated` with JSON Schema `format: date-time`. The API currently serializes those fields as naive timestamps without a UTC offset, for example `2026-09-12T11:52:44.045303`. RFC 3339 date-time validation therefore rejects otherwise structurally valid tag, user, project, pipeline, snapshot, stack, and run response bodies.

Tracked in [zenml-io/zenml#5270](https://github.com/zenml-io/zenml/issues/5270). The bounded API suite copies the live schema and removes only `format: date-time` keywords before loading the eight-operation allowlist. It retains every other format check, including UUID and URI validation, and leaves the fetched schema unchanged. It continues to validate response structure, content type, documented response headers, JSON decoding, and the absence of server errors. Remove the exclusion when API timestamps include an offset or the published response contract describes the serialized values accurately.

## Tag-name validation is narrower than OpenAPI

The tag request schema permits empty and UUID-like names, while ZenML's domain validator rejects them with a `400` response. Generated schema-positive cases classify these responses as expected domain rejections. The suite still requires parseable JSON and fails on any `5xx`. Extra request fields are also classified according to the base model's intentional forward-compatible `extra="ignore"` behavior.

## Malformed JSON uses an undocumented 422 response shape

An invalid request can produce a `422` JSON array containing the exception class and validation text. OpenAPI documents that status as an `ErrorModel` object with a `detail` property. Tracked in [zenml-io/zenml#5269](https://github.com/zenml-io/zenml/issues/5269). Live qualification confirmed this response across all eight operations in the fixed API allowlist. The suite skips structural response-schema validation only for a schema-negative allowlisted case whose `422` payload is a nonempty top-level array beginning with `"ValueError"`. Operations outside the allowlist, other modes, statuses, and array shapes retain structural validation. The suite continues to require parseable JSON, a `4xx` status, and no server error. Remove the exclusion when validation errors use the documented model.
