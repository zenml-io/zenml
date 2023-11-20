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

from scipy.sparse import coo_matrix

from tests.unit.test_general import _test_materializer
from zenml.integrations.scipy.materializers.sparse_materializer import (
    SparseMaterializer,
)


def test_scipy_sparse_matrix_materializer(clean_workspace):
    """Tests whether the steps work for the SciPy sparse matrix materializer."""
    sparse_matrix = _test_materializer(
        step_output=coo_matrix(
            ([1, 2, 3], ([0, 1, 2], [0, 1, 2])), shape=(3, 3)
        ),
        materializer_class=SparseMaterializer,
        expected_metadata_size=4,
    )

    assert sparse_matrix.format == "coo"
    assert sparse_matrix.shape == (3, 3)
    assert sparse_matrix.nnz == 3
    assert sparse_matrix.data.tolist() == [1, 2, 3]
    assert sparse_matrix.row.tolist() == [0, 1, 2]
    assert sparse_matrix.col.tolist() == [0, 1, 2]
