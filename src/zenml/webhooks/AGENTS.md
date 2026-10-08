# ZenML Webhooks Agent Guidelines

This file applies to `src/zenml/webhooks/` and below. Webhooks turn untrusted
provider requests into authenticated `WebhookEvent` envelopes; registered
handlers perform downstream work after intake.

## Architecture

- `providers/base.py` defines the stateless provider contract, parsed delivery
  and intake response models, configuration, target-event filters, and shared
  authentication helpers.
- `providers/<provider>.py` owns provider-specific authentication, parsing,
  typed trigger configuration, semantic events, and matching.
- `providers/registry.py` lazily registers bundled providers.
- `events.py` contains the immutable, provider-neutral event dispatched after
  successful authentication.
- `handler.py` adapts the common `EventHandler` contract for webhook handlers.
- `zen_server/routers/webhook_endpoints.py` owns generic HTTP intake. Keep
  provider-specific behavior out of the route.

The intake order is significant: pre-validate cheap header metadata, resolve
the webhook, authenticate the exact raw body, verify that it is active, parse
the delivery, record acceptance, then return the provider-owned response with
any `WebhookEvent` dispatch attached as an in-process background task. Never
expose an unauthenticated payload to handlers or perform provider side effects
in intake.

A successful `2XX` intake response means only that ZenML accepted the trusted
delivery. The exact success status and payload may vary by integration. It does
not confirm trigger matching, queuing, or snapshot execution. Preserve this
boundary: return after intake and keep downstream handler failures isolated and
observable through handler logs and dispatch state. The background handoff is
not durable. A handler failure must not change an accepted delivery into an HTTP
intake failure or cause the provider to retry it.

## Adding a Provider

1. Add a provider module with a `WebhookConfiguration` subclass and a
   `BaseWebhookProvider` implementation.
2. Implement authentication, event-type extraction, optional delivery-ID
   extraction, and trigger matching. Override `parse_delivery`, `parse`, or
   `pre_validate` only when the generic behavior is insufficient. Use
   `parse_delivery` for successful control deliveries without events or
   provider-specific success responses.
3. Add bundled provider identifiers to `BuiltinWebhookType` and lazy
   registration to `WebhookProviderRegistry`. The enum is intentionally not an
   exhaustive list of externally registered provider types.
4. Export only shared contracts from `providers/__init__.py`. Import public
   provider-specific configuration and event classes from their provider
   module, not from `zenml.models`.
5. Cover registry lookup, authentication over exact bytes, malformed payloads,
   event metadata, configuration validation, and trigger matching in a focused
   provider test module. Integration-specific providers may keep this coverage
   under `tests/integration/functional/webhooks/`.
6. Update webhook and trigger SDK/CLI documentation and signed request examples.

Providers must be stateless: the registry creates a fresh instance for each
lookup. Raise `WebhookAuthenticationError` for failed credentials and
`WebhookPayloadError` for malformed provider metadata or payloads. Use
`WebhookPreValidationResult.IGNORE` only for valid deliveries ZenML deliberately
does not process; intake still returns a successful `2XX` response for these.

## Adding a Semantic Operation

For another operation or event supported by an existing provider, update the
complete provider-owned chain:

- raw event-family and semantic-event identifiers;
- a typed `WebhookTargetEvent` filter model and the discriminated target union;
- a normalized semantic event with explicit matching behavior;
- `pre_validate` support for any new raw family;
- payload-to-semantic-event parsing, returning `None` for valid but irrelevant
  payload variants;
- positive, negative, malformed, and filter-operator tests; and
- SDK, YAML, and CLI documentation examples.

Keep target models strict so misspelled filter fields fail writes. Keep the
configuration envelope tolerant of removed fields for stored-data
compatibility. Runtime matching must skip and log defective stored trigger
configuration rather than breaking delivery processing for every trigger.

## Handlers and Cross-Layer Changes

Downstream consumers subclass `WebhookEventHandler` and implement
`handle_webhook_event`; they do not re-authenticate or reparse the request.
Server-loaded handlers are configured through
`webhook_event_handler_sources` and registered with the common
`EventDispatcher`. Handler failures are isolated by the dispatcher.

Changes to persisted webhook or trigger shape may also require aligned updates
in `models`, client methods, CLI commands, server endpoints, stores/schemas,
tests, docs, and Pro handler implementations. Do not move provider logic into
those layers merely to avoid extending the provider contract.
