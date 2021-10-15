#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

from zenml.logger import get_logger
from zenml.materializers.beam_materializer import BeamMaterializer  # noqa
from zenml.materializers.built_in_materializer import (  # noqa
    BuiltInMaterializer,
)
from zenml.materializers.numpy_materializer import NumpyMaterializer  # noqa
from zenml.materializers.pandas_materializer import PandasMaterializer  # noqa

logger = get_logger(__name__)

try:
    from zenml.materializers.keras_meterializer import KerasMaterializer  # noqa
    from zenml.materializers.tf_dataset_materializer import (  # noqa
        TensorflowDatasetMaterializer,
    )
except ImportError:
    logger.debug("Tensorflow not installed.")

try:
    from zenml.materializers.pytorch_materializer import (  # noqa
        PyTorchMaterializer,
    )
except ImportError:
    logger.debug("PyTorch not installed.")

try:
    from zenml.materializers.pytorch_lightning_materializer import (  # noqa
        PyTorchLightningMaterializer,
    )
except ImportError:
    logger.debug("PyTorch Lightning not installed.")
