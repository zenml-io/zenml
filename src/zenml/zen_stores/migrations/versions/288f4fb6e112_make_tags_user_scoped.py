"""make tags user scoped [288f4fb6e112].

Revision ID: 288f4fb6e112
Revises: 3b1776345020
Create Date: 2025-02-19 15:16:42.954792

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.orm import Session

# revision identifiers, used by Alembic.
revision = "288f4fb6e112"
down_revision = "3b1776345020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    with op.batch_alter_table("tag", schema=None) as batch_op:
        # First add columns as nullable
        batch_op.add_column(
            sa.Column("user_id", sqlmodel.sql.sqltypes.GUID(), nullable=True)
        )

        # Add foreign key constraints
        batch_op.create_foreign_key(
            "fk_tag_user_id_user",
            "user",
            ["user_id"],
            ["id"],
            ondelete="SET NULL",
        )

    bind = op.get_bind()
    session = Session(bind=bind)

    tags = session.execute(
        sa.text("""
            SELECT t.id, tr.resource_id, tr.resource_type
            FROM tag t
            JOIN tag_resource tr ON t.id = tr.tag_id
        """)
    )

    tag_ids = []
    for tag_id, resource_id, resource_type in tags:
        if tag_id in tag_ids:
            continue
        tag_ids.append(tag_id)
        session.execute(
            sa.text(
                f"""
                    UPDATE tag
                    SET user_id = (
                        SELECT r.user_id
                        FROM {resource_type} r
                        WHERE r.id = :resource_id
                    )
                    WHERE id = :tag_id
                """  # nosec B608
            ),
            params={"resource_id": resource_id, "tag_id": tag_id},
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    with op.batch_alter_table("tag", schema=None) as batch_op:
        batch_op.drop_constraint("fk_tag_user_id_user", type_="foreignkey")
        batch_op.drop_column("user_id")
