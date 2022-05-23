#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""
Feature stores allow data teams to serve data via an offline store and an online
low-latency store where data is kept in sync between the two. It also offers a
centralized registry where features (and feature schemas) are stored for use
within a team or wider organization.

As a data scientist working on training your model, your requirements for how
you access your batch / 'offline' data will almost certainly be different from
how you access that data as part of a real-time or online inference setting.
Feast solves the problem of developing train-serve skew where those two sources
of data diverge from each other.
"""
from zenml.feature_stores.base_feature_store import BaseFeatureStore

__all__ = ["BaseFeatureStore"]
