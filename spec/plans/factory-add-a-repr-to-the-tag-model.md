# Plan: Add `__repr__` to the Tag model

## Issue

`TagResponse` (`src/zenml/models/v2/core/tag.py`) has no custom `__repr__`.
Printing a `TagResponse` instance in a REPL falls back to Pydantic's default
`BaseModel.__repr__`, which dumps every field (`id`, `permission_denied`,
`body`, `metadata`, `resources`, `name`, ...) instead of a concise,
human-readable representation.

## Root cause

`TagResponse` inherits from `UserScopedResponse` → `BaseIdentifiedResponse` →
`BaseResponse` → `BaseZenModel` → Pydantic's `BaseModel`. None of these base
classes define `__repr__` (confirmed via `grep -n "__repr__|__str__"` across
`src/zenml/models/v2/base/base.py` and `scoped.py` — only `__hash__` and
`__eq__` are overridden on `BaseIdentifiedResponse`). No model in
`src/zenml/models/` currently defines a custom `__repr__`, so there's no
existing convention to reuse — this will be the first one.

`color` is a `@property` on `TagResponse` that proxies to
`self.get_body().color` (`tag.py:168-175`), so `__repr__` must go through
that property rather than reading `self.body` directly (body can be `None`
when the response is not hydrated with a body, though for a fully
constructed instance it will be present).

## Code changes

**File:** `src/zenml/models/v2/core/tag.py`

Add a `__repr__` method to `TagResponse`, placed after the existing
properties (after `tagged_count`, before the `# ------------------ Filter
Model ------------------` section, around line 193):

```python
def __repr__(self) -> str:
    """String representation of the tag.

    Returns:
        A string representation of the tag.
    """
    return f"Tag(name={self.name}, color={self.color.value})"
```

Notes on implementation details to settle while implementing:
- `self.color` returns a `ColorVariants` enum member. Use `self.color.value`
  so the repr shows the plain string (e.g. `red`) rather than
  `ColorVariants.RED`/`<ColorVariants.RED: 'red'>`. Confirm the desired
  output against the issue text (`Tag(name=<name>, color=<color>)`) — using
  `.value` matches the intent of a clean, readable repr.
- No need to override `__str__`; Python falls back to `__repr__` when
  `__str__` is not defined, so `str(tag_response)` and `print(tag_response)`
  will also use this new format.
- Do not add a docstring-only one-liner comment inside the method — the
  Google-style docstring above is sufficient per the project's commenting
  policy.

## Tests

**New file:** `tests/unit/models/test_tag_models.py` (no existing test file
for tag models; naming follows the convention of `test_model_models.py`,
`test_component_models.py`, etc. in the same directory).

Construct a `TagResponse` directly (mirroring the pattern used in
`tests/unit/models/test_model_models.py`, which builds `ModelResponse` /
`ModelVersionResponse` directly with `id`, `body`, `metadata`) and assert on
`repr()`:

```python
from datetime import datetime
from uuid import uuid4

from zenml.enums import ColorVariants
from zenml.models import TagResponse, TagResponseBody, TagResponseMetadata


def test_tag_response_repr():
    """Test that TagResponse has a concise, readable __repr__."""
    tag = TagResponse(
        id=uuid4(),
        name="my_tag",
        body=TagResponseBody(
            created=datetime.now(),
            updated=datetime.now(),
            color=ColorVariants.GREEN,
            exclusive=False,
        ),
        metadata=TagResponseMetadata(tagged_count=0),
    )

    assert repr(tag) == "Tag(name=my_tag, color=green)"
    assert str(tag) == "Tag(name=my_tag, color=green)"
```

Verify `TagResponse`, `TagResponseBody`, `TagResponseMetadata` are exported
from `zenml.models` (they are used elsewhere via `zenml.models` imports,
e.g. in `zen_stores/schemas/tag_schemas.py`); import from
`zenml.models.v2.core.tag` directly if they turn out not to be re-exported
at the `zenml.models` package level.

## Verification steps

1. `pytest tests/unit/models/test_tag_models.py -v`
2. `bash scripts/format.sh` to ensure formatting/lint compliance.
3. `mypy src/zenml/models/v2/core/tag.py` to confirm the new method type
   checks (return type `str`, no untyped access).
4. Manually sanity check in a Python shell:
   ```python
   from datetime import datetime
   from uuid import uuid4
   from zenml.enums import ColorVariants
   from zenml.models import TagResponse, TagResponseBody, TagResponseMetadata

   t = TagResponse(
       id=uuid4(), name="demo",
       body=TagResponseBody(created=datetime.now(), updated=datetime.now(),
                             color=ColorVariants.BLUE, exclusive=False),
       metadata=TagResponseMetadata(tagged_count=0),
   )
   print(t)  # Tag(name=demo, color=blue)
   ```

## Out of scope

- No changes to `TagRequest`, `TagUpdate`, or `TagFilter` — the issue only
  asks for `TagResponse`.
- No changes to CLI/dashboard tag display code — those don't rely on
  `repr()`/`str()` of `TagResponse`.
- This is a purely additive, non-breaking change (new dunder method only),
  so no deprecation handling is needed and it should be labeled
  `no-release-notes` unless the team wants it surfaced as a minor DX
  improvement.
