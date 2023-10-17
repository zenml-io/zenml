from unittest.mock import patch

import pytest

from zenml.enums import ModelStages
from zenml.model import ModelConfig


@pytest.mark.parametrize(
    "version_name,create_new_model_version,delete_new_version_on_failure,logger",
    [
        [None, False, False, "warning"],
        [None, True, False, "info"],
        ["staging", False, False, "info"],
        ["1", False, False, "info"],
        [1, False, False, "info"],
    ],
    ids=[
        "No new version, but recovery",
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
        ModelConfig(
            name="foo",
            version=version_name,
            create_new_model_version=create_new_model_version,
            delete_new_version_on_failure=delete_new_version_on_failure,
        )
        logger.assert_called_once()


@pytest.mark.parametrize(
    "version_name,create_new_model_version",
    [
        [1, True],
        ["1", True],
        [ModelStages.PRODUCTION, True],
        ["production", True],
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
    create_new_model_version,
):
    with pytest.raises(ValueError):
        ModelConfig(
            name="foo",
            version=version_name,
            create_new_model_version=create_new_model_version,
        )
