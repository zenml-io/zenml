# zenml.hooks package

## Submodules

## zenml.hooks.alerter_hooks module

Functionality for standard hooks.

### zenml.hooks.alerter_hooks.alerter_failure_hook(exception: BaseException) → None

Standard failure hook that executes after step fails.

This hook uses any BaseAlerter that is configured within the active stack to post a message.

Args:
: exception: Original exception that lead to step failing.

### zenml.hooks.alerter_hooks.alerter_success_hook() → None

Standard success hook that executes after step finishes successfully.

This hook uses any BaseAlerter that is configured within the active stack to post a message.

## zenml.hooks.hook_validators module

Validation functions for hooks.

### zenml.hooks.hook_validators.resolve_and_validate_hook(hook: HookSpecification) → [Source](zenml.config.md#zenml.config.source.Source)

Resolves and validates a hook callback.

Args:
: hook: Hook function or source.

Returns:
: Hook source.

Raises:
: ValueError: If hook_func is not a valid callable.

## Module contents

The hooks package exposes some standard hooks that can be used in ZenML.

Hooks are functions that run after a step has exited.

### zenml.hooks.alerter_failure_hook(exception: BaseException) → None

Standard failure hook that executes after step fails.

This hook uses any BaseAlerter that is configured within the active stack to post a message.

Args:
: exception: Original exception that lead to step failing.

### zenml.hooks.alerter_success_hook() → None

Standard success hook that executes after step finishes successfully.

This hook uses any BaseAlerter that is configured within the active stack to post a message.

### zenml.hooks.resolve_and_validate_hook(hook: HookSpecification) → [Source](zenml.config.md#zenml.config.source.Source)

Resolves and validates a hook callback.

Args:
: hook: Hook function or source.

Returns:
: Hook source.

Raises:
: ValueError: If hook_func is not a valid callable.
