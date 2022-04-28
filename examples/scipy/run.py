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

import numpy as np
from scipy.sparse import coo_matrix, csr_matrix

from zenml.integrations.constants import SCIPY
from zenml.pipelines import pipeline
from zenml.steps import step


@step
def importer() -> np.ndarray:
    return np.array([1, 2, 3] * 1000)


@step
def sparsifier(arr: np.ndarray) -> csr_matrix:
    return csr_matrix(arr)


@step
def reformatter(arr: csr_matrix) -> coo_matrix:
    return arr.tocoo()


@pipeline(required_integrations=[SCIPY])
def pipe(importer, sparsifier, reformatter):
    X = importer()
    X = sparsifier(X)
    X = reformatter(X)


run = pipe(
    importer(),
    sparsifier(),
    reformatter(),
)

if __name__ == "__main__":
    run.run()
