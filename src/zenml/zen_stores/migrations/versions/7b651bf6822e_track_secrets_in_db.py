"""track secrets in db [7b651bf6822e].

Revision ID: 7b651bf6822e
Revises: 1ac1b9c04da1
Create Date: 2023-12-22 20:56:18.131906

"""

import sqlalchemy as sa
from alembic import op

from zenml.enums import StoreType
from zenml.logger import get_logger

logger = get_logger(__name__)

# revision identifiers, used by Alembic.


revision = "7b651bf6822e"
down_revision = "1ac1b9c04da1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema and/or data, creating a new revision."""
    from zenml.config.global_config import GlobalConfiguration
    from zenml.enums import SecretsStoreType
    from zenml.zen_stores.sql_zen_store import SqlZenStore

    store_cfg = GlobalConfiguration().store

    if store_cfg is None or store_cfg.type != StoreType.SQL:
        return

    # We create a new SqlZenStore instance with the same configuration as the
    # one used to run migrations, but we skip the default registrations and
    # migrations. This is because we can't use the same store instance that is
    # used to run migrations because it would create an infinite loop.
    store = SqlZenStore(
        config=store_cfg,
        skip_default_registrations=True,
        skip_migrations=True,
    )

    secrets_store = store.secrets_store

    if secrets_store.TYPE == SecretsStoreType.SQL:
        # If the secrets store is already a SQL secrets store, we don't need
        # to transfer secrets from the external secrets store to the db.
        return

    # Transfer secrets from the external secrets store to the db

    external_secrets = secrets_store.list_secrets()

    conn = op.get_bind()
    meta = sa.MetaData(bind=op.get_bind())
    meta.reflect(only=("secret",))
    secrets = sa.Table("secret", meta)
    for secret in external_secrets:
        logger.info(
            f"Transferring secret '{secret.name}' from the "
            f"{secrets_store.type} secrets store to the db."
        )
        # First check if there is already a secret with the same ID in the db
        # and delete it if there is. This can happen for example if the user has
        # previously migrated the secrets from the db to an external secrets
        # store and forgot to delete the secrets from the db.
        conn.execute(
            secrets.delete().where(
                secrets.c.id == str(secret.id).replace("-", "")
            )
        )
        conn.execute(
            secrets.insert().values(
                id=str(secret.id).replace("-", ""),
                created=secret.created,
                updated=secret.updated,
                name=secret.name,
                scope=secret.scope.value,
                values=None,
                workspace_id=str(secret.workspace.id).replace("-", ""),
                user_id=str(secret.user.id).replace("-", "")
                if secret.user
                else None,
            )
        )


def downgrade() -> None:
    """Downgrade database schema and/or data back to the previous revision."""
    pass
