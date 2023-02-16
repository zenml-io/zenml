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

import pytest

from tests.integration.functional.zen_stores.utils import (
    SecretContext,
    UserContext,
    WorkspaceContext,
)
from zenml.client import Client
from zenml.enums import SecretScope, StoreType
from zenml.models.secret_models import SecretFilterModel, SecretUpdateModel

# .---------.
# | SECRETS |
# '---------'


def test_update_secret_existing_values():
    """Tests that existing values a secret can be updated."""
    client = Client()
    store = client.zen_store

    values = dict(
        aria="space cat",
        axl="space dog",
    )
    with SecretContext(values=values) as secret:
        saved_secret = store.get_secret(secret_id=secret.id)
        assert saved_secret.secret_values == values

        values["axl"] = "also space cat"
        store.update_secret(
            secret_id=secret.id,
            secret_update=SecretUpdateModel(
                values=dict(
                    axl=values["axl"],
                ),
            ),
        )

        saved_secret = store.get_secret(secret_id=secret.id)
        assert saved_secret.secret_values == values


def test_update_secret_add_new_values():
    """Tests that a secret can be updated with new values."""
    client = Client()
    store = client.zen_store

    values = dict(
        aria="space cat",
        axl="also space cat",
    )
    with SecretContext(values=values) as secret:
        saved_secret = store.get_secret(secret_id=secret.id)
        assert saved_secret.secret_values == values

        values["blupus"] = "another space cat"
        store.update_secret(
            secret_id=secret.id,
            secret_update=SecretUpdateModel(
                values=dict(
                    blupus=values["blupus"],
                ),
            ),
        )

        saved_secret = store.get_secret(secret_id=secret.id)
        assert saved_secret.secret_values == values


def test_update_secret_remove_values():
    """Tests that a secret can be updated to remove values."""
    client = Client()
    store = client.zen_store

    values = dict(
        aria="space cat",
        axl="the only space cat",
    )
    with SecretContext(values=values) as secret:
        saved_secret = store.get_secret(secret_id=secret.id)
        assert saved_secret.secret_values == values

        del values["aria"]
        store.update_secret(
            secret_id=secret.id,
            secret_update=SecretUpdateModel(
                values=dict(
                    aria=None,
                ),
            ),
        )

        saved_secret = store.get_secret(secret_id=secret.id)
        assert saved_secret.secret_values == values


def test_workspace_secret_is_visible_to_other_users():
    """Tests that a workspace scoped secret is visible to other users in the same workspace."""
    if Client().zen_store.type == StoreType.SQL:
        pytest.skip("SQL Zen Stores do not support user switching.")

    client = Client()
    store = client.zen_store

    with SecretContext() as secret:
        all_secrets = store.list_secrets(
            SecretFilterModel(name=secret.name)
        ).items
        assert len(all_secrets) == 1
        assert secret.id == all_secrets[0].id
        workspace_secrets = store.list_secrets(
            SecretFilterModel(
                name=secret.name,
                scope=SecretScope.WORKSPACE,
                workspace_id=client.active_workspace.id,
            )
        ).items
        assert len(workspace_secrets) == 1
        assert secret.id == workspace_secrets[0].id
        user_secrets = store.list_secrets(
            SecretFilterModel(
                name=secret.name,
                scope=SecretScope.USER,
                user_id=client.active_user.id,
                workspace_id=client.active_workspace.id,
            )
        ).items
        assert len(user_secrets) == 0

        with UserContext(login=True):
            #  Client() needs to be instantiated here with the new
            #  logged-in user
            other_client = Client()
            other_store = other_client.zen_store

            all_secrets = other_store.list_secrets(
                SecretFilterModel(name=secret.name),
            ).items
            assert len(all_secrets) == 1
            assert secret.id == all_secrets[0].id
            workspace_secrets = other_store.list_secrets(
                SecretFilterModel(
                    name=secret.name,
                    scope=SecretScope.WORKSPACE,
                    workspace_id=other_client.active_workspace.id,
                )
            ).items
            assert len(workspace_secrets) == 1
            assert secret.id == workspace_secrets[0].id
            user_secrets = other_store.list_secrets(
                SecretFilterModel(
                    name=secret.name,
                    scope=SecretScope.USER,
                    user_id=other_client.active_user.id,
                    workspace_id=other_client.active_workspace.id,
                ),
            ).items
            assert len(user_secrets) == 0


def test_user_secret_is_not_visible_to_other_users():
    """Tests that a user scoped secret is not visible to other users in the same workspace."""
    if Client().zen_store.type == StoreType.SQL:
        pytest.skip("SQL Zen Stores do not support user switching.")

    client = Client()
    store = client.zen_store

    with SecretContext() as secret:
        all_secrets = store.list_secrets(
            SecretFilterModel(name=secret.name)
        ).items
        assert len(all_secrets) == 1
        assert secret.id == all_secrets[0].id
        workspace_secrets = store.list_secrets(
            SecretFilterModel(
                name=secret.name,
                scope=SecretScope.WORKSPACE,
                workspace_id=client.active_workspace.id,
            )
        ).items
        assert len(workspace_secrets) == 1
        assert secret.id == workspace_secrets[0].id
        user_secrets = store.list_secrets(
            SecretFilterModel(
                name=secret.name,
                scope=SecretScope.USER,
                user_id=client.active_user.id,
                workspace_id=client.active_workspace.id,
            )
        ).items
        assert len(user_secrets) == 0

        # Create a user-scoped secret
        with SecretContext(
            scope=SecretScope.USER, secret_name=secret.name
        ) as user_secret:

            all_secrets = store.list_secrets(
                SecretFilterModel(name=secret.name)
            ).items
            assert len(all_secrets) == 2
            assert secret.id in [s.id for s in all_secrets]
            assert user_secret.id in [s.id for s in all_secrets]
            workspace_secrets = store.list_secrets(
                SecretFilterModel(
                    name=secret.name,
                    scope=SecretScope.WORKSPACE,
                    workspace_id=client.active_workspace.id,
                )
            ).items
            assert len(workspace_secrets) == 1
            assert secret.id == workspace_secrets[0].id
            assert user_secret.id not in [s.id for s in workspace_secrets]
            user_secrets = store.list_secrets(
                SecretFilterModel(
                    name=secret.name,
                    scope=SecretScope.USER,
                    user_id=client.active_user.id,
                    workspace_id=client.active_workspace.id,
                )
            ).items
            assert len(user_secrets) == 1
            assert user_secret.id == user_secrets[0].id

            # Switch to a different user
            with UserContext(login=True):
                #  Client() needs to be instantiated here with the new
                #  logged-in user
                other_client = Client()
                other_store = other_client.zen_store

                all_secrets = other_store.list_secrets(
                    SecretFilterModel(name=secret.name)
                ).items
                assert len(all_secrets) == 2
                assert secret.id in [s.id for s in all_secrets]
                assert user_secret.id in [s.id for s in all_secrets]
                workspace_secrets = other_store.list_secrets(
                    SecretFilterModel(
                        name=secret.name,
                        scope=SecretScope.WORKSPACE,
                        workspace_id=other_client.active_workspace.id,
                    )
                ).items
                assert len(workspace_secrets) == 1
                assert secret.id == workspace_secrets[0].id
                assert user_secret.id not in [s.id for s in workspace_secrets]
                user_secrets = other_store.list_secrets(
                    SecretFilterModel(
                        name=secret.name,
                        scope=SecretScope.USER,
                        user_id=other_client.active_user.id,
                        workspace_id=other_client.active_workspace.id,
                    )
                ).items
                assert len(user_secrets) == 0


def test_workspace_secret_is_not_visible_to_other_workspaces():
    """Tests that a workspace scoped secret is not visible to other workspaces."""
    if Client().zen_store.type == StoreType.SQL:
        pytest.skip("SQL Zen Stores do not support user switching.")

    client = Client()
    store = client.zen_store

    with SecretContext() as secret:
        all_secrets = store.list_secrets(
            SecretFilterModel(name=secret.name)
        ).items
        assert len(all_secrets) == 1
        assert secret.id == all_secrets[0].id
        workspace_secrets = store.list_secrets(
            SecretFilterModel(
                name=secret.name,
                scope=SecretScope.WORKSPACE,
                workspace_id=client.active_workspace.id,
            )
        ).items
        assert len(workspace_secrets) == 1
        assert secret.id == workspace_secrets[0].id
        user_secrets = store.list_secrets(
            SecretFilterModel(
                name=secret.name,
                scope=SecretScope.USER,
                user_id=client.active_user.id,
                workspace_id=client.active_workspace.id,
            )
        ).items
        assert len(user_secrets) == 0

        with WorkspaceContext(activate=True):

            all_secrets = store.list_secrets(
                SecretFilterModel(name=secret.name)
            ).items
            assert len(all_secrets) == 1
            assert secret.id == all_secrets[0].id
            workspace_secrets = store.list_secrets(
                SecretFilterModel(
                    name=secret.name,
                    scope=SecretScope.WORKSPACE,
                    workspace_id=client.active_workspace.id,
                )
            ).items
            assert len(workspace_secrets) == 0
            user_secrets = store.list_secrets(
                SecretFilterModel(
                    name=secret.name,
                    scope=SecretScope.USER,
                    user_id=client.active_user.id,
                    workspace_id=client.active_workspace.id,
                )
            ).items
            assert len(user_secrets) == 0

            with SecretContext(secret_name=secret.name) as other_secret:
                all_secrets = store.list_secrets(
                    SecretFilterModel(name=secret.name)
                ).items
                assert len(all_secrets) == 2
                assert secret.id in [s.id for s in all_secrets]
                assert other_secret.id in [s.id for s in all_secrets]
                workspace_secrets = store.list_secrets(
                    SecretFilterModel(
                        name=secret.name,
                        scope=SecretScope.WORKSPACE,
                        workspace_id=client.active_workspace.id,
                    )
                ).items
                assert len(workspace_secrets) == 1
                assert other_secret.id == workspace_secrets[0].id
                user_secrets = store.list_secrets(
                    SecretFilterModel(
                        name=secret.name,
                        scope=SecretScope.USER,
                        user_id=client.active_user.id,
                        workspace_id=client.active_workspace.id,
                    )
                ).items
                assert len(user_secrets) == 0


def test_user_secret_is_not_visible_to_other_workspaces():
    """Tests that a user scoped secret is not visible to other workspaces."""
    if Client().zen_store.type == StoreType.SQL:
        pytest.skip("SQL Zen Stores do not support user switching.")

    client = Client()
    store = client.zen_store

    with SecretContext() as secret:
        all_secrets = store.list_secrets(
            SecretFilterModel(name=secret.name)
        ).items
        assert len(all_secrets) == 1
        assert secret.id == all_secrets[0].id
        workspace_secrets = store.list_secrets(
            SecretFilterModel(
                name=secret.name,
                scope=SecretScope.WORKSPACE,
                workspace_id=client.active_workspace.id,
            )
        ).items
        assert len(workspace_secrets) == 1
        assert secret.id == workspace_secrets[0].id
        user_secrets = store.list_secrets(
            SecretFilterModel(
                name=secret.name,
                scope=SecretScope.USER,
                user_id=client.active_user.id,
                workspace_id=client.active_workspace.id,
            )
        ).items
        assert len(user_secrets) == 0

        # Create a user-scoped secret
        with SecretContext(
            scope=SecretScope.USER, secret_name=secret.name
        ) as user_secret:

            all_secrets = store.list_secrets(
                SecretFilterModel(name=secret.name)
            ).items
            assert len(all_secrets) == 2
            assert secret.id in [s.id for s in all_secrets]
            assert user_secret.id in [s.id for s in all_secrets]
            workspace_secrets = store.list_secrets(
                SecretFilterModel(
                    name=secret.name,
                    scope=SecretScope.WORKSPACE,
                    workspace_id=client.active_workspace.id,
                )
            ).items
            assert len(workspace_secrets) == 1
            assert secret.id == workspace_secrets[0].id
            assert user_secret.id not in [s.id for s in workspace_secrets]
            user_secrets = store.list_secrets(
                SecretFilterModel(
                    name=secret.name,
                    scope=SecretScope.USER,
                    user_id=client.active_user.id,
                    workspace_id=client.active_workspace.id,
                )
            ).items
            assert len(user_secrets) == 1
            assert user_secret.id == user_secrets[0].id

            with WorkspaceContext(activate=True) as workspace:

                all_secrets = store.list_secrets(
                    SecretFilterModel(name=secret.name)
                ).items
                assert len(all_secrets) == 2
                assert secret.id in [s.id for s in all_secrets]
                assert user_secret.id in [s.id for s in all_secrets]
                workspace_secrets = store.list_secrets(
                    SecretFilterModel(
                        name=secret.name,
                        scope=SecretScope.WORKSPACE,
                        workspace_id=client.active_workspace.id,
                    )
                ).items
                assert len(workspace_secrets) == 0
                user_secrets = store.list_secrets(
                    SecretFilterModel(
                        name=secret.name,
                        scope=SecretScope.USER,
                        user_id=client.active_user.id,
                        workspace_id=client.active_workspace.id,
                    )
                ).items
                assert len(user_secrets) == 0

                # Switch to a different user and activate the same workspace
                with UserContext(login=True):
                    with WorkspaceContext(workspace.name, activate=True):
                        #  Client() needs to be instantiated here with the new
                        #  logged-in user
                        other_client = Client()
                        other_store = other_client.zen_store

                        all_secrets = other_store.list_secrets(
                            SecretFilterModel(name=secret.name)
                        ).items
                        assert len(all_secrets) == 2
                        assert secret.id in [s.id for s in all_secrets]
                        assert user_secret.id in [s.id for s in all_secrets]
                        workspace_secrets = other_store.list_secrets(
                            SecretFilterModel(
                                name=secret.name,
                                scope=SecretScope.WORKSPACE,
                                workspace_id=other_client.active_workspace.id,
                            )
                        ).items
                        assert len(workspace_secrets) == 0
                        user_secrets = other_store.list_secrets(
                            SecretFilterModel(
                                name=secret.name,
                                scope=SecretScope.USER,
                                user_id=other_client.active_user.id,
                                workspace_id=other_client.active_workspace.id,
                            )
                        ).items
                        assert len(user_secrets) == 0
