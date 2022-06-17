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
from contextlib import ExitStack as does_not_raise

from scipy.sparse import coo_matrix, spmatrix

from zenml.integrations.scipy.materializers.sparse_materializer import (
    SparseMaterializer,
)
from zenml.steps import step


def test_scipy_sparse_materializer():
    """Tests whether the steps work for the SciPy sparse materializer."""

    @step
    def some_step() -> spmatrix:
        # using a subclass (coo_matrix) since spmatrix is a base class
        # and cannot be directly instantiated
        return coo_matrix(([1, 2, 3], ([0, 1, 2], [0, 1, 2])), shape=(3, 3))

    with does_not_raise():
        some_step().with_return_materializers(SparseMaterializer)()
