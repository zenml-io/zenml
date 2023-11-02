from unittest.mock import patch

import pytest

from zenml.enums import ModelStages
from zenml.model import ModelVersionConsumerConfig, ModelVersionProducerConfig


@pytest.mark.parametrize(
    "version_name,create_new_model_version,delete_new_version_on_failure,logger",
    [
        [None, True, False, "info"],
        ["staging", False, False, "info"],
        ["1", False, False, "info"],
        [1, False, False, "info"],
    ],
    ids=[
        "Default running version",
        "Pick model by text stage",
        "Pick model by text version number",
        "Pick model by integer version number",
    ],
)
def test_init_warns(
    version_name,
    create_new_model_version,
    delete_new_version_on_failure,
    logger,
):
    with patch(f"zenml.model.model_config.logger.{logger}") as logger:
        if create_new_model_version:
            ModelVersionProducerConfig(
                name="foo",
                version=version_name,
                delete_new_version_on_failure=delete_new_version_on_failure,
            )
        else:
            ModelVersionConsumerConfig(
                name="foo",
                version=version_name,
            )
        logger.assert_called_once()


@pytest.mark.parametrize(
    "version_name",
    [
        [1],
        ["1"],
        [ModelStages.PRODUCTION],
        ["production"],
    ],
    ids=[
        "Version number as integer and new version request",
        "Version number as string and new version request",
        "Version stage as instance and new version request",
        "Version stage as string and new version request",
    ],
)
def test_init_raises(
    version_name,
):
    with pytest.raises(ValueError):
        ModelVersionProducerConfig(
            name="foo",
            version=version_name,
        )
