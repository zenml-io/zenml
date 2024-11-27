"""Update step run input types [b557b2871693].

Revision ID: b557b2871693
Revises: 1cb6477f72d6
Create Date: 2024-10-30 13:06:55.147202

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "b557b2871693"
down_revision = "1cb6477f72d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    op.execute("""
        UPDATE step_run_input_artifact
        SET type = 'step_output'
        WHERE type = 'default'
    """)


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    op.execute("""
        UPDATE step_run_input_artifact
        SET type = 'default'
        WHERE type = 'step_output'
    """)
