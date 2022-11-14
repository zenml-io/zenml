"""Add unique MLMD ID constraints [1b6125964a2f].

Revision ID: 1b6125964a2f
Revises: 8a64fbfecda0
Create Date: 2022-11-14 10:42:41.034003

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.orm.session import Session

# revision identifiers, used by Alembic.
revision = "1b6125964a2f"
down_revision = "8a64fbfecda0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""

    # SQLite disables all foreign key constraints by default, so we need to
    # explicitly enable them if we want cascading deletes to work as expected.
    engine_name = op.get_bind().engine.name
    if engine_name == "sqlite":
        session = Session(bind=op.get_bind())
        session.execute("PRAGMA foreign_keys = ON;")  # type: ignore[arg-type]
        session.commit()

    # Delete all runs that have an MLMD ID so they are synced from scratch again
    # and have the unique constraint enforced.
    meta = sa.MetaData(bind=op.get_bind())
    meta.reflect(only=["pipeline_run"])
    runs_table = sa.Table("pipeline_run", meta)
    conn = op.get_bind()
    conn.execute(runs_table.delete().where(runs_table.c.mlmd_id.isnot(None)))

    # Add unique constraints to the MLMD ID columns.
    with op.batch_alter_table("artifacts", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "unique_mlmd_output_artifact", ["mlmd_id", "mlmd_parent_step_id"]
        )

    with op.batch_alter_table("pipeline_run", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "unique_pipeline_run_mlmd_id", ["mlmd_id"]
        )

    with op.batch_alter_table("step_run", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "unique_step_run_mlmd_id", ["mlmd_id"]
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""

    with op.batch_alter_table("step_run", schema=None) as batch_op:
        batch_op.drop_constraint("unique_step_run_mlmd_id", type_="unique")

    with op.batch_alter_table("pipeline_run", schema=None) as batch_op:
        batch_op.drop_constraint("unique_pipeline_run_mlmd_id", type_="unique")

    with op.batch_alter_table("artifacts", schema=None) as batch_op:
        batch_op.drop_constraint("unique_mlmd_output_artifact", type_="unique")
