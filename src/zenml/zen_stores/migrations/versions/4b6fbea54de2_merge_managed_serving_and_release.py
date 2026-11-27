"""Merge the managed-serving and 0.99.0 release migration histories."""

revision = "4b6fbea54de2"
down_revision = ("0.99.0", "d93d714aa621")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Join both histories after their schema changes have run."""


def downgrade() -> None:
    """Return to the two existing branch heads."""
