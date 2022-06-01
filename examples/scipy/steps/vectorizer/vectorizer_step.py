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
from scipy.sparse import csr_matrix
from sklearn.base import BaseEstimator
from sklearn.feature_extraction.text import CountVectorizer

from zenml.steps import Output, step


@step
def vectorizer(
    train: np.ndarray, test: np.ndarray
) -> Output(count_vec=BaseEstimator, X_train=csr_matrix, X_test=csr_matrix):
    count_vec = CountVectorizer(ngram_range=(1, 4), min_df=3)
    train = count_vec.fit_transform(train)
    test = count_vec.transform(test)
    return count_vec, train, test
