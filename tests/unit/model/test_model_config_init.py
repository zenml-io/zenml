from unittest.mock import patch

import pytest

from zenml.model import ModelConfig


@pytest.mark.parametrize(
    "version_name,delete_new_version_on_failure,logger",
    [
        ["staging", False, "info"],
        ["1", False, "info"],
        [1, False, "info"],
    ],
    ids=[
        "Pick model by text stage",
        "Pick model by text version number",
        "Pick model by integer version number",
    ],
)
def test_init_warns(
    version_name,
    delete_new_version_on_failure,
    logger,
):
    with patch(f"zenml.model.model_version.logger.{logger}") as logger:
        ModelConfig(
            name="foo",
            version=version_name,
            delete_new_version_on_failure=delete_new_version_on_failure,
        )
        logger.assert_called_once()
