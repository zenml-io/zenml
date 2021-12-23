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

import pandas as pd
from sklearn import datasets

from evidently.model_profile import Profile
from evidently.profile_sections import DataDriftProfileSection

iris = datasets.load_iris()
iris_frame = pd.DataFrame(iris.data, columns=iris.feature_names)

iris_data_drift_profile = Profile(sections=[DataDriftProfileSection()])
iris_data_drift_profile.calculate(iris_frame, iris_frame, column_mapping=None)
print(iris_data_drift_profile.json())
