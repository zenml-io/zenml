# Plan: Add `__repr__` to `TagResponse`

## Root cause

`src/zenml/models/v2/core/tag.py` defines `TagResponse` (the client-facing
`Tag` model), which subclasses `UserScopedResponse` → `BaseIdentifiedResponse`
→ `BaseResponse` → `BaseZenModel` (Pydantic `BaseModel`). None of these base
classes define `__repr__` or `__str__`, so printing a `TagResponse` instance
falls back to Pydantic's default `BaseModel.__repr__`, which dumps every
field (`id`, `body`, `metadata`, `resources`, `permission_denied`, `name`,
etc.). That's noisy and unhelpful in a REPL — a `Tag` should print as
something short like `Tag(name=docs, color=purple)`.

The fix is localized: add a `__repr__` method directly on `TagResponse`. No
other model in `src/zenml/models/` currently overrides `__repr__`/`__str__`
(confirmed via grep), so this is a net-new, self-contained addition with no
risk of clashing with an existing override.

## Code changes

File: `src/zenml/models/v2/core/tag.py`

Add a `__repr__` method to the `TagResponse` class (after `get_hydrated_version`
or alongside the `color`/`exclusive`/`tagged_count` properties, ~line 166-193).
`color` is already exposed as a property on `TagResponse` that reads
`self.get_body().color` and returns a `ColorVariants` enum, so use
`self.color.value` to get the plain string value (e.g. `"purple"` instead of
`ColorVariants.PURPLE`):

```python
def __repr__(self) -> str:
    """String representation of the tag.

    Returns:
        A string representation of the tag.
    """
    return f"Tag(name={self.name}, color={self.color.value})"
```

Notes:
- Use `self.name` (a plain top-level field on `TagResponse`, always set —
  doesn't require hydration) and `self.color` (a property backed by
  `TagResponseBody`, which is populated even in the unhydrated response since
  `color` is a required field on `TagResponseBody`). Both are safe to access
  without triggering `get_hydrated_version()`.
- Follow the repo's docstring convention (Google style, `Returns:` section)
  per `CLAUDE.md`.
- No changes needed to `TagRequest`, `TagUpdate`, or `TagFilter` — the issue
  only asks for the response/`Tag` model's repr.

## Tests

New file: `tests/unit/models/test_tag_models.py`

Follow the construction pattern used in `tests/unit/models/test_model_models.py`
(directly instantiating a `*Response` with `id`, `name`, `body`, `metadata`
args) since there's no existing tag-specific test file or fixture.

```python
from datetime import datetime
from uuid import uuid4

from zenml.enums import ColorVariants
from zenml.models import TagResponse, TagResponseBody, TagResponseMetadata


def test_tag_response_repr():
    """Test that a tag's repr is short and human-readable."""
    tag = TagResponse(
        id=uuid4(),
        name="my_tag",
        body=TagResponseBody(
            created=datetime.now(),
            updated=datetime.now(),
            color=ColorVariants.PURPLE,
            exclusive=False,
        ),
        metadata=TagResponseMetadata(tagged_count=0),
    )

    assert repr(tag) == "Tag(name=my_tag, color=purple)"
```

Steps:
1. Verify `TagResponse`, `TagResponseBody`, `TagResponseMetadata` are exported
   from `zenml.models` (they should be, alongside the other `Tag*` models —
   confirm with `grep -n "Tag" src/zenml/models/__init__.py`; import from
   `zenml.models.v2.core.tag` directly if not exported at the top level).
2. Add the test above to the new `tests/unit/models/test_tag_models.py`,
   including the standard Apache license header used by sibling files in
   that directory.
3. Run `pytest tests/unit/models/test_tag_models.py -v` to confirm it passes.

## Validation checklist

- [ ] `bash scripts/format.sh`
- [ ] `pytest tests/unit/models/test_tag_models.py`
- [ ] `mypy src/zenml/models/v2/core/tag.py`
- [ ] Manually sanity check in a REPL: `TagResponse(...)` prints
      `Tag(name=..., color=...)` instead of the full Pydantic dump.
