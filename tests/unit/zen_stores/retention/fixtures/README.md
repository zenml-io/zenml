# Archive format v1 compatibility fixtures

These immutable JSON documents were captured using the v1 capture/format code
at `923ce9f1c167cad196f2e5cdeba0588915965524` on September 12, 2026, from
synthetic static, dynamic, and legacy two-step executions. They contain no
customer data or credentials.

`test_compatibility.py` checks their recorded hashes, changes only project
identity to fit the disposable database, and compresses them independently of
the current archive encoder. The test seeds the retained SQL identities and
catalog directly, then restores into the current migrated MySQL schema. It
checks exact archived field restoration and current public model reads.

Do not regenerate these fixtures when models, capture code, or database
migrations change. Such changes must keep existing v1 archives readable. If a
payload or schema change requires transformation, add the specific v1 read or
restore conversion and preserve the historical fixture assertion. New write
formats get additional fixtures; replacing the v1 fixtures would remove the
compatibility evidence.

This guards restoration of previously written v1 data into the current schema.
It does not replace testing the actual populated upgrade path of a migration
that changes retained identities or payload interpretation.
