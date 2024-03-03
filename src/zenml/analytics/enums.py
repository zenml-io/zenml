#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Collection of analytics events for ZenML."""

from enum import Enum


class AnalyticsEvent(str, Enum):
    """Enum of events to track in segment."""

    # Login
    DEVICE_VERIFIED = "Device verified"

    # Pipelines
    RUN_PIPELINE = "Pipeline run"
    RUN_PIPELINE_ENDED = "Pipeline run ended"
    CREATE_PIPELINE = "Pipeline created"
    BUILD_PIPELINE = "Pipeline built"

    # Template
    GENERATE_TEMPLATE = "Template generated"

    # Components
    REGISTERED_STACK_COMPONENT = "Stack component registered"

    # Code repository
    REGISTERED_CODE_REPOSITORY = "Code repository registered"

    # Stack
    REGISTERED_STACK = "Stack registered"
    UPDATED_STACK = "Stack updated"

    # Trigger
    CREATED_TRIGGER = "Trigger created"
    UPDATED_TRIGGER = "Trigger updated"

    # Model Control Plane
    MODEL_DEPLOYED = "Model deployed"
    CREATED_MODEL = "Model created"
    CREATED_MODEL_VERSION = "Model Version created"

    # Analytics opt in and out
    OPT_IN_ANALYTICS = "Analytics opt-in"
    OPT_OUT_ANALYTICS = "Analytics opt-out"
    OPT_IN_OUT_EMAIL = "Response for Email prompt"

    # Examples
    RUN_ZENML_GO = "ZenML go"

    # Workspaces
    CREATED_WORKSPACE = "Workspace created"

    # Flavor
    CREATED_FLAVOR = "Flavor created"

    # Secret
    CREATED_SECRET = "Secret created"

    # Service connector
    CREATED_SERVICE_CONNECTOR = "Service connector created"

    # Service account and API keys
    CREATED_SERVICE_ACCOUNT = "Service account created"

    # Stack recipes
    RUN_STACK_RECIPE = "Stack recipe ran"
    DEPLOY_STACK = "Stack deployed"
    DESTROY_STACK = "Stack destroyed"

    # Stack component deploy
    DEPLOY_STACK_COMPONENT = "Stack component deployed"
    DESTROY_STACK_COMPONENT = "Stack component destroyed"

    # Tag created
    CREATED_TAG = "Tag created"

    # ZenML server events
    ZENML_SERVER_DEPLOYED = "ZenML server deployed"
    ZENML_SERVER_DESTROYED = "ZenML server destroyed"

    # ZenML Hub events
    ZENML_HUB_PLUGIN_INSTALL = "ZenML Hub plugin installed"
    ZENML_HUB_PLUGIN_UNINSTALL = "ZenML Hub plugin uninstalled"
    ZENML_HUB_PLUGIN_CLONE = "ZenML Hub plugin pulled"
    ZENML_HUB_PLUGIN_SUBMIT = "ZenML Hub plugin pushed"
