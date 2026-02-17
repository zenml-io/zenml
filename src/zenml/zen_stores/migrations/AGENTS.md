# ZenML Migrations — Agent Guidelines

Guidance for agents writing or debugging Alembic migrations for ZenML's database schema.

## Useful SQL Queries for Migration Development

### Tracing Foreign Key Dependencies

When modifying tables (especially when changing or deleting columns, or deciding on `ON DELETE` behavior), you need to understand which tables reference yours.

**Query (MySQL):**

This query joins two MySQL system tables: `KEY_COLUMN_USAGE` (aliased as `kcu`) which tracks which columns participate in foreign keys, and `REFERENTIAL_CONSTRAINTS` (aliased as `rc`) which stores the ON DELETE/UPDATE rules for each constraint.

```sql
SELECT
  kcu.CONSTRAINT_NAME AS fk_name,
  kcu.TABLE_SCHEMA AS referencing_schema,
  kcu.TABLE_NAME AS referencing_table,
  kcu.COLUMN_NAME AS referencing_column,
  kcu.REFERENCED_TABLE_SCHEMA AS referenced_schema,
  kcu.REFERENCED_TABLE_NAME AS referenced_table,
  kcu.REFERENCED_COLUMN_NAME AS referenced_column,
  rc.UPDATE_RULE,
  rc.DELETE_RULE
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
JOIN INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
  ON rc.CONSTRAINT_SCHEMA = kcu.CONSTRAINT_SCHEMA
 AND rc.CONSTRAINT_NAME  = kcu.CONSTRAINT_NAME
WHERE kcu.REFERENCED_TABLE_SCHEMA = '<DB_NAME>'
  AND kcu.REFERENCED_TABLE_NAME IN ('table1', 'table2')
ORDER BY kcu.TABLE_NAME, kcu.CONSTRAINT_NAME, kcu.ORDINAL_POSITION;
```

**When to use this:**

1. **Before adding `ON DELETE CASCADE`** — Check what tables reference yours. A cascade delete on `user` might unexpectedly wipe out rows in `api_key`, `secret`, and other tables.

2. **Before dropping a column or table** — If other tables have FKs pointing to what you're removing, the migration will fail. This query tells you what needs to change first.

3. **Debugging migration failures** — If you see "Cannot delete or update a parent row: a foreign key constraint fails", this query helps you find all the referencing constraints.

4. **Reviewing `ON DELETE` choices** — When auditing existing schemas, you can check whether current `DELETE_RULE` values (`CASCADE`, `SET NULL`, `RESTRICT`, `NO ACTION`) match business requirements.

**Example output interpretation:**

```
fk_name           | referencing_table | referencing_column | referenced_table | DELETE_RULE
------------------+-------------------+--------------------+------------------+------------
fk_apikey_user    | api_key           | user_id            | user             | CASCADE
fk_secret_user    | secret            | user_id            | user             | SET NULL
```

This tells you:
- Deleting a `user` row will **automatically delete** related `api_key` rows (CASCADE)
- Deleting a `user` row will **set `user_id` to NULL** in related `secret` rows (SET NULL)

---

## Related Resources

- **ORM schema patterns:** See `schemas/AGENTS.md` for SQLModel conventions and FK definition patterns
- **Migration testing:** The `schemas/AGENTS.md` file includes a migration testing workflow
- **Alembic basics:** See CLAUDE.md section "Database and Migration Guidelines"

---

*This document is maintained to help agents write robust database migrations for ZenML.*
