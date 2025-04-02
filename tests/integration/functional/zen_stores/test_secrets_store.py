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

import time
from contextlib import ExitStack as does_not_raise
from datetime import timedelta

import pytest

from tests.integration.functional.utils import sample_name
from tests.integration.functional.zen_stores.utils import (
    LoginContext,
    SecretContext,
    UserContext,
)
from zenml.client import Client
from zenml.enums import SecretsStoreType, StoreType
from zenml.exceptions import EntityExistsError, IllegalOperationError
from zenml.models import SecretFilter, SecretUpdate
from zenml.utils.string_utils import random_str


def _get_secrets_store_type() -> SecretsStoreType:
    """Returns the secrets store back-end type that is used by the test
    ZenML deployment.

    Returns:
        The secrets store type that is used by the test ZenML deployment.
    """
    store = Client().zen_store
    return store.get_store_info().secrets_store_type


# .---------.
# | SECRETS |
# '---------'


def test_get_secret_returns_values():
    """Tests that `get_secret` returns secret values."""
    client = Client()
    store = client.zen_store

    values = dict(
        aria="space cat",
        axl="space dog",
    )
    with SecretContext(values=values) as secret:
        assert secret.secret_values == values
        saved_secret = store.get_secret(secret_id=secret.id)
        assert saved_secret.secret_values == values


def test_list_secret_excludes_values():
    """Tests that `list_secret` does not return secret values."""
    client = Client()
    store = client.zen_store

    values = dict(
        aria="space cat",
        axl="space dog",
    )
    with SecretContext(values=values) as secret:
        assert secret.secret_values == values
        all_secrets = store.list_secrets(SecretFilter(id=secret.id)).items
        assert len(all_secrets) == 1
        assert secret.id == all_secrets[0].id
        assert len(all_secrets[0].values) == 0


def test_secret_empty_values():
    """Tests that secrets can hold empty values."""
    client = Client()
    store = client.zen_store

    values = dict(
        aria="space cat",
        axl="",
    )
    with SecretContext(values=values) as secret:
        saved_secret = store.get_secret(secret_id=secret.id)
        assert saved_secret.secret_values == values

        values["axl"] = "also space cat"
        updated_secret = store.update_secret(
            secret_id=secret.id,
            secret_update=SecretUpdate(
                values=dict(
                    axl=values["axl"],
                ),
            ),
        )

        assert updated_secret.secret_values == values

        saved_secret = store.get_secret(secret_id=secret.id)
        assert saved_secret.secret_values == values


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
        updated_secret = store.update_secret(
            secret_id=secret.id,
            secret_update=SecretUpdate(
                values=dict(
                    axl=values["axl"],
                ),
            ),
        )

        assert updated_secret.secret_values == values

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
        updated_secret = store.update_secret(
            secret_id=secret.id,
            secret_update=SecretUpdate(
                values=dict(
                    blupus=values["blupus"],
                ),
            ),
        )

        assert updated_secret.secret_values == values

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
        updated_secret = store.update_secret(
            secret_id=secret.id,
            secret_update=SecretUpdate(
                values=dict(
                    aria=None,
                ),
            ),
        )

        assert updated_secret.secret_values == values

        saved_secret = store.get_secret(secret_id=secret.id)
        assert saved_secret.secret_values == values


def test_update_secret_remove_nonexisting_values():
    """Tests that a secret can be updated to remove non-existing values."""
    client = Client()
    store = client.zen_store

    values = dict(
        aria="space cat",
        axl="the only space cat",
    )
    with SecretContext(values=values) as secret:
        saved_secret = store.get_secret(secret_id=secret.id)
        assert saved_secret.secret_values == values

        updated_secret = store.update_secret(
            secret_id=secret.id,
            secret_update=SecretUpdate(
                values=dict(
                    blupus=None,
                ),
            ),
        )

        assert updated_secret.secret_values == values

        saved_secret = store.get_secret(secret_id=secret.id)
        assert saved_secret.secret_values == values


def test_update_secret_values_sets_updated_date():
    """Tests that updating secret values sets the updated timestamp."""
    client = Client()
    store = client.zen_store

    values = dict(
        aria="space cat",
        axl="also space cat",
    )
    with SecretContext(values=values) as secret:
        assert secret.updated - secret.created < timedelta(seconds=1)

        saved_secret = store.get_secret(secret_id=secret.id)
        assert saved_secret.secret_values == values
        assert saved_secret.updated == secret.updated
        assert saved_secret.created == secret.created

        # Wait a second to ensure the updated timestamp is different.
        time.sleep(1)

        values["blupus"] = "another space cat"
        updated_secret = store.update_secret(
            secret_id=secret.id,
            secret_update=SecretUpdate(
                values=dict(
                    blupus=values["blupus"],
                ),
            ),
        )

        if _get_secrets_store_type() != SecretsStoreType.AWS:
            # The AWS secrets store returns before the secret is actually
            # updated in the backend.
            assert updated_secret.secret_values == values
            assert updated_secret.created == saved_secret.created
            assert (
                updated_secret.updated - updated_secret.created
                >= timedelta(seconds=1)
            )

        saved_secret = store.get_secret(secret_id=secret.id)
        assert saved_secret.secret_values == values
        assert saved_secret.updated == updated_secret.updated
        assert saved_secret.created == updated_secret.created


def test_update_secret_name_sets_updated_date():
    """Tests that updating the secret's name sets the updated timestamp."""
    client = Client()
    store = client.zen_store

    with SecretContext() as secret:
        assert secret.updated - secret.created < timedelta(seconds=1)

        saved_secret = store.get_secret(secret_id=secret.id)
        assert saved_secret.name == secret.name
        assert saved_secret.secret_values == secret.secret_values
        assert saved_secret.updated == secret.updated
        assert saved_secret.created == secret.created

        # Wait a second to ensure the updated timestamp is different.
        time.sleep(1)

        new_name = sample_name("arias-secrets")
        updated_secret = store.update_secret(
            secret_id=secret.id,
            secret_update=SecretUpdate(
                name=new_name,
            ),
        )

        if _get_secrets_store_type() != SecretsStoreType.AWS:
            # The AWS secrets store returns before the secret is actually
            # updated in the backend.
            assert updated_secret.name == new_name
            assert updated_secret.secret_values == secret.secret_values
            assert updated_secret.created == saved_secret.created
            assert (
                updated_secret.updated - updated_secret.created
                >= timedelta(seconds=1)
            )

        saved_secret = store.get_secret(secret_id=secret.id)
        assert saved_secret.name == new_name
        assert saved_secret.secret_values == secret.secret_values
        assert saved_secret.updated == updated_secret.updated
        assert saved_secret.created == updated_secret.created


def test_update_secret_name():
    """Tests that a secret name can be updated."""
    client = Client()
    store = client.zen_store

    with SecretContext() as secret:
        saved_secret = store.get_secret(secret_id=secret.id)
        assert saved_secret.name == secret.name
        all_secrets = store.list_secrets(SecretFilter(name=secret.name)).items
        assert len(all_secrets) == 1
        assert secret.id == all_secrets[0].id

        new_name = sample_name("arias-secrets")

        updated_secret = store.update_secret(
            secret_id=secret.id,
            secret_update=SecretUpdate(
                name=new_name,
            ),
        )

        assert updated_secret.name == new_name

        saved_secret = store.get_secret(secret_id=secret.id)
        assert saved_secret.name == new_name

        all_secrets = store.list_secrets(SecretFilter(name=new_name)).items
        assert len(all_secrets) == 1
        assert secret.id == all_secrets[0].id


def test_update_secret_name_fails_if_exists():
    """Tests that the name of a public secret cannot be changed if another secret has the same name."""
    client = Client()
    store = client.zen_store

    with SecretContext() as secret:
        with SecretContext() as other_secret:
            saved_secret = store.get_secret(secret_id=secret.id)
            assert saved_secret.name == secret.name

            saved_secret = store.get_secret(secret_id=other_secret.id)
            assert saved_secret.name == other_secret.name

            all_secrets = store.list_secrets(
                SecretFilter(name=secret.name)
            ).items
            assert len(all_secrets) == 1
            assert secret.id == all_secrets[0].id

            with pytest.raises(EntityExistsError):
                store.update_secret(
                    secret_id=secret.id,
                    secret_update=SecretUpdate(
                        name=other_secret.name,
                    ),
                )

            saved_secret = store.get_secret(secret_id=secret.id)
            assert saved_secret.name == secret.name

            all_secrets = store.list_secrets(
                SecretFilter(name=secret.name)
            ).items
            assert len(all_secrets) == 1
            assert secret.id == all_secrets[0].id


def test_update_private_secret_name_succeeds_if_public_secret_exists():
    """Tests that the name of a private secret can be changed if a public secret has the same name."""
    client = Client()
    store = client.zen_store

    with SecretContext(private=True) as secret:
        with SecretContext() as other_secret:
            saved_secret = store.get_secret(secret_id=secret.id)
            assert saved_secret.name == secret.name

            saved_secret = store.get_secret(secret_id=other_secret.id)
            assert saved_secret.name == other_secret.name

            all_secrets = store.list_secrets(
                SecretFilter(name=secret.name)
            ).items
            assert len(all_secrets) == 1
            assert secret.id == all_secrets[0].id

            with does_not_raise():
                updated_secret = store.update_secret(
                    secret_id=secret.id,
                    secret_update=SecretUpdate(
                        name=other_secret.name,
                    ),
                )

            assert updated_secret.name == other_secret.name

            saved_secret = store.get_secret(secret_id=secret.id)
            assert saved_secret.name == other_secret.name

            all_secrets = store.list_secrets(
                SecretFilter(name=secret.name)
            ).items
            assert len(all_secrets) == 0

            all_secrets = store.list_secrets(
                SecretFilter(name=other_secret.name)
            ).items
            assert len(all_secrets) == 2
            assert secret.id in [s.id for s in all_secrets]
            assert other_secret.id in [s.id for s in all_secrets]

            all_secrets = store.list_secrets(
                SecretFilter(name=other_secret.name, private=True)
            ).items
            assert len(all_secrets) == 1
            assert secret.id == all_secrets[0].id

            all_secrets = store.list_secrets(
                SecretFilter(name=other_secret.name, private=False)
            ).items
            assert len(all_secrets) == 1
            assert other_secret.id == all_secrets[0].id


def test_update_public_secret_name_succeeds_if_private_secret_exists():
    """Tests that the name of a public secret can be changed if a private secret has the same name for the same user."""
    client = Client()
    store = client.zen_store

    with SecretContext() as secret:
        with SecretContext(private=True) as other_secret:
            saved_secret = store.get_secret(secret_id=secret.id)
            assert saved_secret.name == secret.name

            saved_secret = store.get_secret(secret_id=other_secret.id)
            assert saved_secret.name == other_secret.name

            all_secrets = store.list_secrets(
                SecretFilter(name=secret.name)
            ).items
            assert len(all_secrets) == 1
            assert secret.id == all_secrets[0].id

            with does_not_raise():
                updated_secret = store.update_secret(
                    secret_id=secret.id,
                    secret_update=SecretUpdate(
                        name=other_secret.name,
                    ),
                )

            assert updated_secret.name == other_secret.name

            saved_secret = store.get_secret(secret_id=secret.id)
            assert saved_secret.name == other_secret.name

            all_secrets = store.list_secrets(
                SecretFilter(name=secret.name)
            ).items
            assert len(all_secrets) == 0

            all_secrets = store.list_secrets(
                SecretFilter(name=other_secret.name)
            ).items
            assert len(all_secrets) == 2
            assert secret.id in [s.id for s in all_secrets]
            assert other_secret.id in [s.id for s in all_secrets]

            all_secrets = store.list_secrets(
                SecretFilter(name=other_secret.name, private=False)
            ).items
            assert len(all_secrets) == 1
            assert secret.id == all_secrets[0].id

            all_secrets = store.list_secrets(
                SecretFilter(name=other_secret.name, private=True)
            ).items
            assert len(all_secrets) == 1
            assert other_secret.id == all_secrets[0].id


def test_reusing_private_secret_name_succeeds():
    """Tests that the name of a private secret can be reused for another user."""
    if Client().zen_store.type == StoreType.SQL:
        pytest.skip("SQL Zen Stores do not support user switching.")

    client = Client()
    store = client.zen_store

    with SecretContext(private=True) as secret:
        all_secrets = store.list_secrets(SecretFilter(name=secret.name)).items
        assert len(all_secrets) == 1
        assert secret.id == all_secrets[0].id

        public_secrets = store.list_secrets(
            SecretFilter(
                name=secret.name,
                private=False,
            )
        ).items
        assert len(public_secrets) == 0

        private_secrets = store.list_secrets(
            SecretFilter(
                name=secret.name,
                private=True,
            )
        ).items
        assert len(private_secrets) == 1
        assert secret.id == private_secrets[0].id

        with UserContext(login=True):
            #  Client() needs to be instantiated here with the new
            #  logged-in user
            other_client = Client()
            other_store = other_client.zen_store

            with SecretContext(
                secret_name=secret.name, private=True
            ) as other_secret:
                all_secrets = other_store.list_secrets(
                    SecretFilter(name=secret.name),
                ).items
                assert len(all_secrets) == 1
                assert secret.id not in [s.id for s in all_secrets]
                assert other_secret.id in [s.id for s in all_secrets]

                public_secrets = other_store.list_secrets(
                    SecretFilter(
                        name=secret.name,
                        private=False,
                    )
                ).items
                assert len(public_secrets) == 0

                private_secrets = other_store.list_secrets(
                    SecretFilter(
                        name=secret.name,
                        private=True,
                    ),
                ).items
                assert len(private_secrets) == 1
                assert other_secret.id == private_secrets[0].id

                other_private_secrets = store.list_secrets(
                    SecretFilter(
                        name=secret.name,
                        private=True,
                    ),
                ).items
                assert len(other_private_secrets) == 1
                assert secret.id == other_private_secrets[0].id


def test_update_scope_succeeds():
    """Tests that the scope of a secret can be changed."""
    client = Client()
    store = client.zen_store

    with SecretContext() as secret:
        saved_secret = store.get_secret(secret_id=secret.id)
        assert saved_secret.name == secret.name
        assert saved_secret.private is False

        all_secrets = store.list_secrets(SecretFilter(name=secret.name)).items
        assert len(all_secrets) == 1
        assert secret.id == all_secrets[0].id

        public_secrets = store.list_secrets(
            SecretFilter(name=secret.name, private=False)
        ).items
        assert len(public_secrets) == 1
        assert secret.id == public_secrets[0].id

        private_secrets = store.list_secrets(
            SecretFilter(name=secret.name, private=True)
        ).items
        assert len(private_secrets) == 0

        all_secrets = store.list_secrets(SecretFilter(private=False)).items
        assert len(all_secrets) >= 1
        assert secret.id in [s.id for s in all_secrets]

        all_secrets = store.list_secrets(SecretFilter(private=True)).items
        assert secret.id not in [s.id for s in all_secrets]

        with does_not_raise():
            updated_secret = store.update_secret(
                secret_id=secret.id,
                secret_update=SecretUpdate(
                    private=True,
                ),
            )

        assert updated_secret.name == secret.name
        assert updated_secret.private is True

        saved_secret = store.get_secret(secret_id=secret.id)
        assert saved_secret.name == secret.name
        assert saved_secret.private is True

        all_secrets = store.list_secrets(SecretFilter(name=secret.name)).items
        assert len(all_secrets) == 1
        assert secret.id == all_secrets[0].id

        public_secrets = store.list_secrets(
            SecretFilter(name=secret.name, private=False)
        ).items
        assert len(public_secrets) == 0

        private_secrets = store.list_secrets(
            SecretFilter(name=secret.name, private=True)
        ).items
        assert len(private_secrets) == 1
        assert secret.id == private_secrets[0].id

        all_secrets = store.list_secrets(SecretFilter(private=False)).items
        assert secret.id not in [s.id for s in all_secrets]

        all_secrets = store.list_secrets(SecretFilter(private=True)).items
        assert len(all_secrets) >= 1
        assert secret.id in [s.id for s in all_secrets]

        with does_not_raise():
            updated_secret = store.update_secret(
                secret_id=secret.id,
                secret_update=SecretUpdate(
                    private=False,
                ),
            )

        assert updated_secret.name == secret.name
        assert updated_secret.private is False

        saved_secret = store.get_secret(secret_id=secret.id)
        assert saved_secret.name == secret.name
        assert saved_secret.private is False

        all_secrets = store.list_secrets(SecretFilter(name=secret.name)).items
        assert len(all_secrets) == 1
        assert secret.id == all_secrets[0].id

        public_secrets = store.list_secrets(
            SecretFilter(name=secret.name, private=False)
        ).items
        assert len(public_secrets) == 1
        assert secret.id == public_secrets[0].id

        private_secrets = store.list_secrets(
            SecretFilter(name=secret.name, private=True)
        ).items
        assert len(private_secrets) == 0

        all_secrets = store.list_secrets(SecretFilter(private=False)).items
        assert len(all_secrets) >= 1
        assert secret.id in [s.id for s in all_secrets]

        all_secrets = store.list_secrets(SecretFilter(private=True)).items
        assert secret.id not in [s.id for s in all_secrets]


def test_update_scope_fails_if_name_already_in_scope():
    """Tests that the scope of a secret cannot be changed if another secret with the same name already exists in the target scope."""
    client = Client()
    store = client.zen_store

    with SecretContext() as secret:
        with SecretContext(
            secret_name=secret.name, private=True
        ) as other_secret:
            all_secrets = store.list_secrets(
                SecretFilter(name=secret.name)
            ).items
            assert len(all_secrets) == 2
            assert secret.id in [s.id for s in all_secrets]
            assert other_secret.id in [s.id for s in all_secrets]

            public_secrets = store.list_secrets(
                SecretFilter(name=secret.name, private=False)
            ).items
            assert len(public_secrets) == 1
            assert secret.id == public_secrets[0].id

            private_secrets = store.list_secrets(
                SecretFilter(name=secret.name, private=True)
            ).items
            assert len(private_secrets) == 1
            assert other_secret.id == private_secrets[0].id

            with pytest.raises(EntityExistsError):
                store.update_secret(
                    secret_id=secret.id,
                    secret_update=SecretUpdate(
                        private=True,
                    ),
                )

            saved_secret = store.get_secret(secret_id=secret.id)
            assert saved_secret.name == secret.name
            assert saved_secret.private is False

            with pytest.raises(EntityExistsError):
                store.update_secret(
                    secret_id=other_secret.id,
                    secret_update=SecretUpdate(
                        private=False,
                    ),
                )

            saved_secret = store.get_secret(secret_id=other_secret.id)
            assert saved_secret.name == secret.name
            assert saved_secret.private is True


def test_public_secret_is_visible_to_other_users():
    """Tests that a public secret is visible to other users."""
    if Client().zen_store.type == StoreType.SQL:
        pytest.skip("SQL Zen Stores do not support user switching.")

    client = Client()
    store = client.zen_store

    with SecretContext() as secret:
        all_secrets = store.list_secrets(SecretFilter(name=secret.name)).items
        assert len(all_secrets) == 1
        assert secret.id == all_secrets[0].id
        public_secrets = store.list_secrets(
            SecretFilter(
                name=secret.name,
                private=False,
            )
        ).items
        assert len(public_secrets) == 1
        assert secret.id == public_secrets[0].id
        private_secrets = store.list_secrets(
            SecretFilter(
                name=secret.name,
                private=True,
            )
        ).items
        assert len(private_secrets) == 0

        with UserContext(login=True):
            #  Client() needs to be instantiated here with the new
            #  logged-in user
            other_client = Client()
            other_store = other_client.zen_store

            all_secrets = other_store.list_secrets(
                SecretFilter(name=secret.name),
            ).items
            assert len(all_secrets) == 1
            assert secret.id == all_secrets[0].id
            public_secrets = other_store.list_secrets(
                SecretFilter(
                    name=secret.name,
                    private=False,
                )
            ).items
            assert len(public_secrets) == 1
            assert secret.id == public_secrets[0].id
            private_secrets = other_store.list_secrets(
                SecretFilter(
                    name=secret.name,
                    private=True,
                ),
            ).items
            assert len(private_secrets) == 0


def test_private_secret_is_not_visible_to_other_users():
    """Tests that a private secret is not visible to other users."""
    if Client().zen_store.type == StoreType.SQL:
        pytest.skip("SQL Zen Stores do not support user switching.")

    client = Client()
    store = client.zen_store

    with SecretContext() as public_secret:
        all_secrets = store.list_secrets(
            SecretFilter(name=public_secret.name)
        ).items
        assert len(all_secrets) == 1
        assert public_secret.id == all_secrets[0].id
        public_secrets = store.list_secrets(
            SecretFilter(
                name=public_secret.name,
                private=False,
            )
        ).items
        assert len(public_secrets) == 1
        assert public_secret.id == public_secrets[0].id
        private_secrets = store.list_secrets(
            SecretFilter(
                name=public_secret.name,
                private=True,
            )
        ).items
        assert len(private_secrets) == 0

        # Create a private secret
        with SecretContext(
            secret_name=public_secret.name, private=True
        ) as private_secret:
            all_secrets = store.list_secrets(
                SecretFilter(name=public_secret.name)
            ).items
            assert len(all_secrets) == 2
            assert public_secret.id in [s.id for s in all_secrets]
            assert private_secret.id in [s.id for s in all_secrets]
            public_secrets = store.list_secrets(
                SecretFilter(
                    name=public_secret.name,
                    private=False,
                )
            ).items
            assert len(public_secrets) == 1
            assert public_secret.id == public_secrets[0].id
            assert private_secret.id not in [s.id for s in public_secrets]
            public_secrets = store.list_secrets(
                SecretFilter(
                    name=public_secret.name,
                    private=True,
                )
            ).items
            assert len(public_secrets) == 1
            assert private_secret.id == public_secrets[0].id

            # Switch to a different user
            with UserContext(login=True):
                #  Client() needs to be instantiated here with the new
                #  logged-in user
                other_client = Client()
                other_store = other_client.zen_store

                all_secrets = other_store.list_secrets(
                    SecretFilter(name=public_secret.name)
                ).items
                assert len(all_secrets) == 1
                assert public_secret.id in [s.id for s in all_secrets]
                assert private_secret.id not in [s.id for s in all_secrets]
                public_secrets = other_store.list_secrets(
                    SecretFilter(
                        name=public_secret.name,
                        private=False,
                    )
                ).items
                assert len(public_secrets) == 1
                assert public_secret.id == public_secrets[0].id
                assert private_secret.id not in [s.id for s in public_secrets]
                public_secrets = other_store.list_secrets(
                    SecretFilter(
                        name=public_secret.name,
                        user=other_client.active_user.id,
                        private=True,
                    )
                ).items
                assert len(public_secrets) == 0


def test_list_secrets_filter():
    """Tests that listing secrets with various filters works."""
    client = Client()
    store = client.zen_store

    aria_secret_name = sample_name("arias-whiskers")
    axl_secret_name = sample_name("axls-whiskers")

    with (
        SecretContext(secret_name=aria_secret_name) as secret_one,
        SecretContext(
            secret_name=aria_secret_name, private=True
        ) as secret_two,
        SecretContext(secret_name=axl_secret_name) as secret_three,
        SecretContext(
            secret_name=axl_secret_name, private=True
        ) as secret_four,
    ):
        all_secrets = store.list_secrets(SecretFilter()).items
        assert len(all_secrets) >= 4
        assert set(
            [secret_one.id, secret_two.id, secret_three.id, secret_four.id]
        ) <= set(s.id for s in all_secrets)

        all_secrets = store.list_secrets(
            SecretFilter(name=aria_secret_name)
        ).items
        assert len(all_secrets) == 2
        assert set([secret_one.id, secret_two.id]) == set(
            s.id for s in all_secrets
        )

        all_secrets = store.list_secrets(
            SecretFilter(name=axl_secret_name)
        ).items
        assert len(all_secrets) == 2
        assert set([secret_three.id, secret_four.id]) == set(
            s.id for s in all_secrets
        )

        all_secrets = store.list_secrets(
            SecretFilter(name="startswith:aria")
        ).items
        assert len(all_secrets) >= 2
        assert set([secret_one.id, secret_two.id]) <= set(
            s.id for s in all_secrets
        )

        all_secrets = store.list_secrets(
            SecretFilter(name="startswith:axl")
        ).items
        assert len(all_secrets) >= 2
        assert set([secret_three.id, secret_four.id]) <= set(
            s.id for s in all_secrets
        )

        all_secrets = store.list_secrets(
            SecretFilter(name="contains:whiskers")
        ).items
        assert len(all_secrets) >= 4
        assert set(
            [secret_one.id, secret_two.id, secret_three.id, secret_four.id]
        ) <= set(s.id for s in all_secrets)

        all_secrets = store.list_secrets(
            SecretFilter(name=f"endswith:{aria_secret_name[-5:]}")
        ).items
        assert len(all_secrets) == 2
        assert set([secret_one.id, secret_two.id]) == set(
            s.id for s in all_secrets
        )

        all_secrets = store.list_secrets(
            SecretFilter(name=f"endswith:{axl_secret_name[-5:]}")
        ).items
        assert len(all_secrets) == 2
        assert set([secret_three.id, secret_four.id]) == set(
            s.id for s in all_secrets
        )

        all_secrets = store.list_secrets(SecretFilter(private=False)).items
        assert len(all_secrets) >= 2
        assert set([secret_one.id, secret_three.id]) <= set(
            s.id for s in all_secrets
        )

        all_secrets = store.list_secrets(SecretFilter(private=True)).items
        assert len(all_secrets) >= 2
        assert set([secret_two.id, secret_four.id]) <= set(
            s.id for s in all_secrets
        )

        all_secrets = store.list_secrets(SecretFilter(private=True)).items
        assert len(all_secrets) >= 2
        assert set([secret_two.id, secret_four.id]) <= set(
            s.id for s in all_secrets
        )

        all_secrets = store.list_secrets(
            SecretFilter(
                name=aria_secret_name,
            )
        ).items
        assert len(all_secrets) == 2
        assert set([secret_one.id, secret_two.id]) == set(
            s.id for s in all_secrets
        )

        all_secrets = store.list_secrets(
            SecretFilter(
                name=axl_secret_name,
            )
        ).items
        assert len(all_secrets) == 2
        assert set([secret_three.id, secret_four.id]) == set(
            s.id for s in all_secrets
        )

        all_secrets = store.list_secrets(
            SecretFilter(
                name=aria_secret_name,
                user=client.active_user.id,
            )
        ).items
        assert len(all_secrets) == 2
        assert set([secret_one.id, secret_two.id]) == set(
            s.id for s in all_secrets
        )

        all_secrets = store.list_secrets(
            SecretFilter(
                name=axl_secret_name,
                user=client.active_user.id,
            )
        ).items
        assert len(all_secrets) == 2
        assert set([secret_three.id, secret_four.id]) == set(
            s.id for s in all_secrets
        )


def test_list_secrets_pagination_and_sorting():
    """Tests that listing secrets with various pagination and sorting settings works."""
    client = Client()
    store = client.zen_store

    suffix = sample_name("")

    with (
        SecretContext(secret_name=f"arias-whiskers-{suffix}") as secret_one,
        SecretContext(
            secret_name=f"arias-spots-{suffix}",
            private=True,
        ) as secret_two,
        SecretContext(
            secret_name=f"axls-whiskers-{suffix}",
        ) as secret_three,
        SecretContext(
            secret_name=f"axls-spots-{suffix}",
            private=True,
        ) as secret_four,
    ):
        secrets = store.list_secrets(
            SecretFilter(
                name=f"endswith:{suffix}",
            )
        )
        assert len(secrets.items) == 4
        assert secrets.index == 1
        assert secrets.total_pages == 1
        assert secrets.total == 4

        assert set(
            [secret_one.id, secret_two.id, secret_three.id, secret_four.id]
        ) == set(s.id for s in secrets.items)

        secrets = store.list_secrets(
            SecretFilter(
                name=f"endswith:{suffix}",
                page=1,
                size=2,
                sort_by="asc:name",
            )
        )
        assert len(secrets.items) == 2
        assert secrets.index == 1
        assert secrets.total_pages == 2
        assert secrets.total == 4

        assert [secret_two.id, secret_one.id] == [s.id for s in secrets.items]

        secrets = store.list_secrets(
            SecretFilter(
                name=f"endswith:{suffix}",
                page=2,
                size=2,
                sort_by="asc:name",
            )
        )
        assert len(secrets.items) == 2
        assert secrets.index == 2
        assert secrets.total_pages == 2
        assert secrets.total == 4

        assert [secret_four.id, secret_three.id] == [
            s.id for s in secrets.items
        ]

        secrets = store.list_secrets(
            SecretFilter(
                name=f"endswith:{suffix}",
                page=1,
                size=2,
                sort_by="desc:name",
            )
        )
        assert len(secrets.items) == 2
        assert secrets.index == 1
        assert secrets.total_pages == 2
        assert secrets.total == 4

        assert [secret_three.id, secret_four.id] == [
            s.id for s in secrets.items
        ]

        secrets = store.list_secrets(
            SecretFilter(
                name=f"endswith:{suffix}",
                page=2,
                size=2,
                sort_by="desc:name",
            )
        )
        assert len(secrets.items) == 2
        assert secrets.index == 2
        assert secrets.total_pages == 2
        assert secrets.total == 4

        assert [secret_one.id, secret_two.id] == [s.id for s in secrets.items]

        secrets = store.list_secrets(
            SecretFilter(
                name=f"endswith:{suffix}",
                page=1,
                size=2,
                sort_by="asc:private",
            )
        )
        assert len(secrets.items) == 2
        assert secrets.index == 1
        assert secrets.total_pages == 2
        assert secrets.total == 4
        assert {secret_one.id, secret_three.id} == {
            s.id for s in secrets.items
        }

        secrets = store.list_secrets(
            SecretFilter(
                name=f"endswith:{suffix}",
                page=2,
                size=2,
                sort_by="asc:private",
            )
        )
        assert len(secrets.items) == 2
        assert secrets.index == 2
        assert secrets.total_pages == 2
        assert secrets.total == 4

        assert {secret_two.id, secret_four.id} == {s.id for s in secrets.items}

        secrets = store.list_secrets(
            SecretFilter(
                name=f"endswith:{suffix}",
                page=1,
                size=3,
                sort_by="asc:created",
            )
        )
        assert len(secrets.items) == 3
        assert secrets.index == 1
        assert secrets.total_pages == 2
        assert secrets.total == 4

        # NOTE: it's impossible to tell for sure which order these will be in,
        # because they could be created in less than one second and the
        # granularity of the sorting algorithm is one second, but we can at
        # least assert that they're all there
        page_one = [s.id for s in secrets.items]

        secrets = store.list_secrets(
            SecretFilter(
                name=f"endswith:{suffix}",
                page=2,
                size=3,
                sort_by="asc:created",
            )
        )
        assert len(secrets.items) == 1
        assert secrets.index == 2
        assert secrets.total_pages == 2
        assert secrets.total == 4

        page_two = [s.id for s in secrets.items]
        assert set(page_one + page_two) == {
            secret_one.id,
            secret_two.id,
            secret_three.id,
            secret_four.id,
        }

        # To give the updated time a chance to change
        time.sleep(1)

        secret_one = store.update_secret(
            secret_one.id,
            SecretUpdate(
                values={
                    "food": "birds",
                }
            ),
        )

        # To give the updated time a chance to change
        time.sleep(1)

        secret_two = store.update_secret(
            secret_two.id,
            SecretUpdate(
                values={
                    "food": "fish",
                }
            ),
        )

        assert secret_one.updated > secret_one.created
        assert secret_two.updated > secret_two.created

        secrets = store.list_secrets(
            SecretFilter(
                name=f"endswith:{suffix}",
                page=1,
                size=2,
                sort_by="desc:updated",
            )
        )
        assert len(secrets.items) == 2
        assert secrets.index == 1
        assert secrets.total_pages == 2
        assert secrets.total == 4

        assert [
            secret_two.id,
            secret_one.id,
        ] == [s.id for s in secrets.items]

        secrets = store.list_secrets(
            SecretFilter(
                name=f"endswith:{suffix}",
                page=2,
                size=2,
                sort_by="desc:updated",
            )
        )
        assert len(secrets.items) == 2
        assert secrets.index == 2
        assert secrets.total_pages == 2
        assert secrets.total == 4

        # NOTE: the second page of secrets were never updated, so they have
        # almost the same updated time (under one second difference). We can't
        # assert that they're in a specific order, but we can assert that they
        # are all there
        assert {
            secret_four.id,
            secret_three.id,
        } == {s.id for s in secrets.items}

        secrets = store.list_secrets(
            SecretFilter(
                updated=f"gte:{secret_one.updated.strftime('%Y-%m-%d %H:%M:%S')}",
                page=1,
                size=10,
                sort_by="desc:name",
            )
        )

        assert len(secrets.items) == 2
        assert secrets.index == 1
        assert secrets.total_pages == 1
        assert secrets.total == 2

        assert [
            secret_one.id,
            secret_two.id,
        ] == [s.id for s in secrets.items]

        secrets = store.list_secrets(
            SecretFilter(
                created=f"gte:{secret_one.updated.strftime('%Y-%m-%d %H:%M:%S')}",
                page=1,
                size=10,
                sort_by="desc:name",
            )
        )

        assert len(secrets.items) == 0


def test_delete_user_with_secrets():
    """Tests that deleting a user is not possible while it owns secrets."""
    client = Client()
    store = client.zen_store

    if store.type == StoreType.SQL:
        pytest.skip("SQL Zen Stores do not support switching users.")

    with SecretContext() as secret:
        all_secrets = store.list_secrets(SecretFilter(name=secret.name)).items
        assert len(all_secrets) == 1
        assert secret.id == all_secrets[0].id
        public_secrets = store.list_secrets(
            SecretFilter(
                name=secret.name,
                private=False,
            )
        ).items
        assert len(public_secrets) == 1
        assert secret.id == public_secrets[0].id
        private_secrets = store.list_secrets(
            SecretFilter(
                name=secret.name,
                private=True,
                user=client.active_user.id,
            )
        ).items
        assert len(private_secrets) == 0

        password = random_str(16)
        with UserContext(login=True, delete=False, password=password) as user:
            #  Client() needs to be instantiated here with the new
            #  logged-in user
            other_client = Client()
            other_store = other_client.zen_store

            with SecretContext(
                secret_name=secret.name,
                private=True,
                delete=False,
            ) as other_secret:
                with does_not_raise():
                    other_store.get_secret(other_secret.id)

                all_secrets = other_store.list_secrets(
                    SecretFilter(name=secret.name),
                ).items
                assert len(all_secrets) == 2
                assert secret.id in [s.id for s in all_secrets]
                assert other_secret.id in [s.id for s in all_secrets]

                private_secrets = other_store.list_secrets(
                    SecretFilter(
                        name=secret.name,
                        private=True,
                        user=user.id,
                    ),
                ).items
                assert len(private_secrets) == 1
                assert other_secret.id == private_secrets[0].id

        with pytest.raises(IllegalOperationError):
            store.delete_user(user.id)

        with pytest.raises(KeyError):
            store.get_secret(other_secret.id)

        all_secrets = store.list_secrets(
            SecretFilter(name=secret.name),
        ).items
        assert len(all_secrets) == 1
        assert secret.id in [s.id for s in all_secrets]
        assert other_secret.id not in [s.id for s in all_secrets]

        private_secrets = store.list_secrets(
            SecretFilter(
                name=secret.name,
                private=True,
                user=user.id,
            ),
        ).items
        assert len(private_secrets) == 0

        with LoginContext(user_name=user.name, password=password):
            #  Client() needs to be instantiated here with the new
            #  logged-in user
            other_client = Client()
            other_store = other_client.zen_store

            # Delete the secret
            other_store.delete_secret(other_secret.id)

        with does_not_raise():
            store.delete_user(user.id)

        with pytest.raises(KeyError):
            store.get_secret(other_secret.id)

        all_secrets = store.list_secrets(
            SecretFilter(name=secret.name),
        ).items
        assert len(all_secrets) == 1
        assert secret.id == all_secrets[0].id

        private_secrets = store.list_secrets(
            SecretFilter(
                name=secret.name,
                private=True,
                user=user.id,
            ),
        ).items
        assert len(private_secrets) == 0
