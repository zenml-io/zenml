# ZenML Zen Stores — Agent Guidelines

Guidance for agents working with ZenML's data storage layer, including ORM schemas and database migrations.

## ORM Usage

ZenML uses **SQLModel** (SQLAlchemy-based) for all database operations. No raw SQL unless absolutely necessary.

### Database Column Limits

General string column limit: **~250 characters** (MySQL constraint). This affects:
- Orchestrator run IDs and similar identifier fields
- Any string field that might receive external system identifiers

When designing schemas, ensure string fields that store external IDs have appropriate length constraints.

---

## ⚠️ CRITICAL: Import Restriction for `zen_stores/`

**Rule:** Code outside `zen_stores/` should **NOT** import SQL-related code directly from this directory.

### Why This Matters

1. **Optional SQL dependencies**: SQL dependencies (SQLAlchemy, SQLModel) may not be installed in all environments
2. **Import check bypass**: Direct imports skip ZenML's dependency checking, leading to misleading error messages
3. **Abstraction violation**: External code should use the Client abstraction, not raw database access

### Correct Access Pattern

```python
# ❌ Bad - direct import from zen_stores
from zenml.zen_stores.schemas import PipelineRunSchema
from zenml.zen_stores.sql_zen_store import SqlZenStore

# ✅ Good - use the Client
from zenml.client import Client
client = Client()
runs = client.list_pipeline_runs()

# ✅ If you need lower-level access (rare)
client.zen_store  # Gives you access to the store with proper checks
```

### Why `client.zen_store` Is Better

- Import checks run properly before accessing the store
- Correct warnings are raised for missing dependencies
- The client handles connection management and authentication

---

## Migration Testing Workflow

When testing database migrations, follow this workflow:

1. **Check out `develop` branch** (or the relevant old release)
2. **Populate the database** from that version (create runs, stacks, etc.)
3. **Switch to your current branch**
4. **Test whether the migration works** — run `alembic upgrade head`

**Why this matters:** Migrations must handle existing data from older versions. Testing only with fresh databases misses edge cases.

**Note:** CI performs basic migration testing by creating runs on all versions, but local testing with realistic data is still recommended for complex migrations.

### Migration Best Practices

- Create migrations with descriptive names: `alembic revision -m "Add X to Y table"`
- Test upgrade path: `alembic upgrade head` (downgrade testing is optional—ZenML doesn't support downgrades in most cases)
- Never modify existing migrations that are already on main/develop branches
- Consider backward compatibility for rolling deployments
- Include both schema changes and data migrations when needed
- Run `scripts/check-alembic-branches.sh` to verify migration consistency

---

## ORM Schemas — Concise Guide

Scope and Location
- Applies to all ORM schemas in src/zenml/zen_stores/schemas and their exports in __init__.py.
- File naming: <concept>_schemas.py (e.g., stack_schemas.py). Prefer a single schema class per file unless multiple are needed for the same concept.
- Keep ORM fields and types aligned with their corresponding domain models. See domain models under src/zenml/models/v2 and related documentation.
- Schema changes typically require DB migrations. Update src/zenml/zen_stores/migrations accordingly and ensure domain models and exports stay in sync.

1) Base Classes and Table Declaration
- Inherit from BaseSchema or NamedSchema (defined in base_schemas.py):
  - BaseSchema: id: UUID (uuid4), created: datetime, updated: datetime
  - NamedSchema: extends BaseSchema with name: str
- Use declarative SQLModel style with explicit table naming:
```python
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from uuid import UUID
from zenml.zen_stores.schemas.base_schemas import NamedSchema

class ExampleSchema(NamedSchema, table=True):
    """SQLModel table for examples."""
    __tablename__ = "example"

    # attributes mirror domain model fields
    description: Optional[str] = None
```

2) Foreign Keys and Relationships
- Use schema_utils.build_foreign_key_field to define FKs consistently; define bidirectional relationships with matching back_populates.
- Always update both sides together when adding/changing relationships. Keep back_populates symmetric to maintain coherent bidirectional navigation.
```python
from typing import Optional
from uuid import UUID
from zenml.zen_stores.schemas.schema_utils import build_foreign_key_field

class ChildSchema(NamedSchema, table=True):
    __tablename__ = "child"

    parent_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__,
        target="parent",          # or ParentSchema.__tablename__
        source_column="parent_id",
        target_column="id",
        ondelete="SET NULL",
        nullable=True,
    )
    parent: Optional["ParentSchema"] = Relationship(back_populates="children")

class ParentSchema(NamedSchema, table=True):
    __tablename__ = "parent"

    children: List["ChildSchema"] = Relationship(back_populates="parent")
```

3) Many-to-Many via Association Table
- Use a link model with both FKs as composite primary keys; cascade deletes to keep the link table clean.
```python
class ExampleLinkSchema(SQLModel, table=True):
    """Join table between left and right."""
    __tablename__ = "example_link"

    left_id: UUID = build_foreign_key_field(
        source=__tablename__, target="left", source_column="left_id",
        target_column="id", ondelete="CASCADE", nullable=False, primary_key=True
    )
    right_id: UUID = build_foreign_key_field(
        source=__tablename__, target="right", source_column="right_id",
        target_column="id", ondelete="CASCADE", nullable=False, primary_key=True
    )

class LeftSchema(NamedSchema, table=True):
    __tablename__ = "left"
    rights: List["RightSchema"] = Relationship(
        back_populates="lefts", link_model=ExampleLinkSchema
    )

class RightSchema(NamedSchema, table=True):
    __tablename__ = "right"
    lefts: List["LeftSchema"] = Relationship(
        back_populates="rights", link_model=ExampleLinkSchema
    )
```

4) Indexes and Constraints
- Add indexes on frequently queried columns (via helpers in schema_utils when available) and/or SQLModel/SQLAlchemy features.
- Unique constraints: enforce uniqueness for fields like names/emails where required.
- Nullability: nullable=True/False must reflect business rules. Optional[T] signals nullable columns.
- Minimal example using SQLModel Field indexing:
```python
from sqlmodel import Field

class ExampleIndexSchema(NamedSchema, table=True):
    __tablename__ = "example_index"
    email: str = Field(index=True)  # simple index for faster lookups
```

5) Naming Conventions
- Classes: Singular, PascalCase (e.g., StackComponentSchema).
- Columns/attributes: snake_case aligned with domain model naming.
- __tablename__: singular, snake_case aligned with the entity.

6) Common Fields (inherited)
- id: UUID primary key (default uuid4) from BaseSchema.
- created, updated: datetimes from BaseSchema. Always refresh updated on mutations.

7) Model Conversion and Updates
- Provide to_model, class constructors (from_request/from_model), and update/update_from_model implementations.
- Keep relationships optional and include related resources only when explicitly requested.
- For structured fields serialized with base64/json, ensure decoding mirrors encoding in to_model or at the service layer to prevent subtle data mismatches.

Examples:
```python
from datetime import datetime
from typing import Any, Optional
import base64, json

class SecretSchema(NamedSchema, table=True):
    __tablename__ = "secret"

    user_id: Optional[UUID] = build_foreign_key_field(
        source=__tablename__, target="user",
        source_column="user_id", target_column="id",
        ondelete="SET NULL", nullable=True
    )
    user: Optional["UserSchema"] = Relationship(back_populates="secrets")
    configuration: bytes
    labels: Optional[bytes] = None

    def to_model(
        self,
        include_metadata: bool = False,
        include_resources: bool = False,
        **kwargs: Any,
    ) -> "SecretResponse":
        """Map ORM -> domain model. Only include extras when requested."""
        metadata = None
        if include_metadata:
            metadata = SecretResponseMetadata(workspace=self.workspace.to_model())
        body = SecretResponseBody(
            user=self.user.to_model() if include_resources and self.user else None,
            created=self.created,
            updated=self.updated,
        )
        return SecretResponse(id=self.id, name=self.name, body=body, metadata=metadata)

    @classmethod
    def from_request(cls, request: "SecretRequest") -> "SecretSchema":
        """Map domain request -> ORM. Serialize structures explicitly."""
        return cls(
            name=request.name,
            user_id=request.user,
            configuration=base64.b64encode(json.dumps(request.configuration).encode("utf-8")),
            labels=(base64.b64encode(json.dumps(request.labels).encode("utf-8"))
                    if request.labels is not None else None),
        )

    def update(self, update_obj: "SecretUpdate") -> "SecretSchema":
        """Apply only provided fields; handle structured fields; refresh updated."""
        for field, value in update_obj.model_dump(exclude_unset=True).items():
            if field == "configuration" and value is not None:
                self.configuration = base64.b64encode(json.dumps(value).encode("utf-8"))
            elif field == "labels":
                self.labels = (base64.b64encode(json.dumps(value).encode("utf-8"))
                               if value is not None else None)
            else:
                setattr(self, field, value)
        self.updated = datetime.utcnow()
        return self
```

8) Formatting and Documentation
- Docstrings are mandatory for all classes and methods; include arguments, returns, and raised exceptions where applicable.
- Comments where mapping/business rules are non-obvious; avoid redundant or change-log style comments.

Practical Checklist for New/Updated Schemas
- Pick BaseSchema vs. NamedSchema appropriately.
- Set table=True and __tablename__.
- Define fields mirroring domain model names/types; use Optional[T] for nullable columns.
- Add FKs with build_foreign_key_field; define Relationship on both sides with matching back_populates.
- For many-to-many, add a link model and set link_model on both sides.
- Add indexes/uniques/nullability aligned with usage and business rules.
- Implement to_model(...), from_request/from_model(...), and update/update_from_model(...).
- Update src/zenml/zen_stores/schemas/__init__.py to export new schema(s).
- Ensure updated is refreshed on mutations; avoid including heavy related resources unless requested via flags.
- Plan and apply DB migrations for schema changes; update src/zenml/zen_stores/migrations and test upgrade/downgrade paths.
- Consult domain models in src/zenml/models/v2 to keep names and types aligned.
