#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Alembic environment script.

This script is used by all Alembic CLI commands. It uses the SqlZenStore
currently configured in the global configuration, or the default store if
no store is configured, to get the SQLAlchemy engine and the context to run
migrations.
"""

from typing import cast

from alembic import context
from alembic.runtime.environment import EnvironmentContext

from zenml.config.global_config import GlobalConfiguration
from zenml.enums import StoreType
from zenml.zen_stores.migrations.alembic import Alembic
from zenml.zen_stores.sql_zen_store import SqlZenStore


def run_migrations() -> None:
    """Run migrations through the ZenML SqlZenStore and Alembic classes."""
    store_cfg = GlobalConfiguration().store

    if store_cfg is None or store_cfg.type != StoreType.SQL:
        store_cfg = GlobalConfiguration().get_default_store()

    store = SqlZenStore(  # type: ignore
        config=store_cfg,
        skip_default_registrations=True,
        skip_migrations=True,
    )

    a = Alembic(engine=store.engine, context=cast(EnvironmentContext, context))
    a.run_migrations(fn=None)


run_migrations()
