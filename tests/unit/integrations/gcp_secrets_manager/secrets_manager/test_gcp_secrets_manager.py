from typing import Dict, List, Optional, Type

import pytest
from pydantic import BaseModel

from zenml.integrations.gcp_secrets_manager.secrets_manager.gcp_secrets_manager import (
    prepend_group_name_to_keys,
    remove_group_name_from_key,
)
from zenml.secret import ArbitrarySecretSchema


class PrependedSecret(BaseModel):
    combined_key_name: str
    group_name: str
    expected_key: Optional[str]
    potential_error: Optional[Type[Exception]]


PREPENDED_SECRETS = [
    PrependedSecret(
        combined_key_name="aria_cat_age",
        group_name="aria",
        expected_key="cat_age",
    ),  # standard
    PrependedSecret(
        combined_key_name="axel__cat_age",
        group_name="axel",
        expected_key="_cat_age",
    ),  # key with leading _
    PrependedSecret(
        combined_key_name="kube_kube_", group_name="kube", expected_key="kube_"
    ),  # key same as group
    PrependedSecret(
        combined_key_name="kube_kube_kube",
        group_name="kube",
        expected_key="kube_kube",
    ),  # key contains group
    PrependedSecret(
        combined_key_name="square__square",
        group_name="square_",
        expected_key="square",
    ),  # group with trailing _
    PrependedSecret(
        combined_key_name="missing_group",
        group_name="rand",
        potential_error=RuntimeError,
    ),  # group not in combined key
    PrependedSecret(
        combined_key_name="missing_key_",
        group_name="missing_key_",
        potential_error=RuntimeError,
    ),  # no key in combined key
    PrependedSecret(
        combined_key_name="", group_name="", potential_error=RuntimeError
    ),  # empty inputs
    PrependedSecret(
        combined_key_name="", group_name="g", potential_error=RuntimeError
    ),  # empty combined key
    PrependedSecret(
        combined_key_name="g", group_name="", potential_error=RuntimeError
    ),  # empty group
]


@pytest.mark.parametrize("parametrized_input", PREPENDED_SECRETS)
def test_remove_group_name_from_key(parametrized_input: PrependedSecret):
    if not parametrized_input.potential_error:
        actual_key = remove_group_name_from_key(
            combined_key_name=parametrized_input.combined_key_name,
            group_name=parametrized_input.group_name,
        )

        assert actual_key == parametrized_input.expected_key
    else:
        with pytest.raises(parametrized_input.potential_error):
            remove_group_name_from_key(
                combined_key_name=parametrized_input.combined_key_name,
                group_name=parametrized_input.group_name,
            )


class ZenMLSecret(BaseModel):
    zenml_secret_name: str
    zenml_secret_keys: List[str]
    expected_combined_keys: Dict[str, str]


ZENML_SECRET = [
    ZenMLSecret(
        zenml_secret_name="secret",
        zenml_secret_keys=["key"],
        expected_combined_keys={"secret_key": ""},
    ),
    ZenMLSecret(
        zenml_secret_name="secret",
        zenml_secret_keys=["key1", "key2"],
        expected_combined_keys={"secret_key1": "", "secret_key2": ""},
    ),
    ZenMLSecret(
        zenml_secret_name="secret",
        zenml_secret_keys=[],
        expected_combined_keys={},
    ),
]


@pytest.mark.parametrize("parametrized_input", ZENML_SECRET)
def test_prepend_group_name_to_keys(parametrized_input: ZenMLSecret):
    secret_schema = ArbitrarySecretSchema(
        name=parametrized_input.zenml_secret_name
    )

    for k in parametrized_input.zenml_secret_keys:
        secret_schema.arbitrary_kv_pairs[k] = ""

    actual_result_key = prepend_group_name_to_keys(secret_schema)
    assert actual_result_key == parametrized_input.expected_combined_keys
