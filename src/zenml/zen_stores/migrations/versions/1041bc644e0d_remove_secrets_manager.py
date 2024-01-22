"""remove secrets manager [1041bc644e0d].

Revision ID: 1041bc644e0d
Revises: 4e1972485075
Create Date: 2023-12-18 18:40:26.612845

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "1041bc644e0d"
down_revision = "4e1972485075"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    conn = op.get_bind()
    meta = sa.MetaData(bind=op.get_bind())
    meta.reflect(only=("stack_component", "stack_composition"))
    components = sa.Table("stack_component", meta)
    compositions = sa.Table("stack_composition", meta)

    # Find all secrets manager components
    secrets_manager_components = conn.execute(
        sa.select([components.c.id]).where(
            components.c.type == "secrets_manager"
        )
    ).all()

    secrets_manager_ids = [i[0] for i in secrets_manager_components]

    # Remove all secrets manager compositions
    conn.execute(
        compositions.delete().where(
            compositions.c.component_id.in_(secrets_manager_ids)
        )
    )

    # Remove all secrets manager components
    conn.execute(
        components.delete().where(components.c.id.in_(secrets_manager_ids))
    )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    pass
