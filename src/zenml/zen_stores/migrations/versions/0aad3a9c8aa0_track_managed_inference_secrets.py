"""Track managed inference secrets.

Revision ID: 0aad3a9c8aa0
Revises: f0ff77a22aef
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import MEDIUMTEXT

revision = "0aad3a9c8aa0"
down_revision = "f0ff77a22aef"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Track secret ownership without exposing plaintext in service records."""
    op.add_column(
        "managed_model_service",
        sa.Column(
            "inference_credentials",
            sa.Text().with_variant(MEDIUMTEXT(), "mysql"),
            nullable=False,
            server_default=sa.text("('{}')"),
        ),
    )
    # Preserve both issued and revoked legacy credentials on creation retries.
    services = sa.table(
        "managed_model_service",
        sa.column("inference_credentials", sa.Text()),
    )
    op.execute(
        services.update().values(inference_credentials='{"initialized":true}')
    )
