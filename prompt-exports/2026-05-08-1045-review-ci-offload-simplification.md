<file_map>
/Users/safoine/zenml-io/zenml
├── .github
│   ├── actions
│   │   └── setup_environment
│   │       └── action.yml *
│   ├── workflows
│   │   ├── base-package-functionality.yml *
│   │   ├── ci-fast.yml *
│   │   ├── ci-medium.yml *
│   │   ├── ci-slow-develop.yml *
│   │   ├── ci-slow.yml *
│   │   ├── develop-health-gate.yml *
│   │   ├── generate-test-duration.yml *
│   │   ├── integration-test-fast-services.yml *
│   │   ├── integration-test-fast.yml *
│   │   ├── integration-test-slow-services.yml *
│   │   ├── integration-test-slow.yml *
│   │   ├── linting.yml *
│   │   ├── linux-fast-offload.yml *
│   │   ├── modal-ci-image-warm.yml *
│   │   ├── offload-cache-warm.yml *
│   │   ├── release.yml *
│   │   ├── slow-ci-on-pr.yml *
│   │   ├── unit-test.yml *
│   │   ├── validate-quarantine.yml *
│   │   ├── validate-workspace-safety.yml *
│   │   └── vscode-tutorial-pipelines-test.yml *
│   ├── ISSUE_TEMPLATE
│   ├── blocks
│   ├── CLAUDE.md *
│   ├── ci-captains.yml *
│   ├── ci-phase-c-rollout.md *
│   ├── quarantined-tests.yml *
│   ├── workspace-safety-baseline.txt *
│   └── zizmor.yml *
├── scripts
│   ├── ci
│   │   ├── __init__.py *
│   │   ├── classify_offload_result.py * +
│   │   ├── compute_offload_cache_keys.py * +
│   │   ├── emit_timing_manifest.py * +
│   │   ├── export_offload_integration_requirements.py * +
│   │   ├── modal_sandbox_requirements.txt *
│   │   ├── normalize_offload_junit.py * +
│   │   ├── print_junit_failures.py * +
│   │   ├── print_junit_summary.py * +
│   │   └── run_mixed_environment_pytest.py * +
│   ├── audit_integration_workspace_safety.py * +
│   ├── check_known_good.py * +
│   ├── ci_matrix_hash.py * +
│   ├── ci_modal_mysql_sandbox.py * +
│   ├── develop_health_gate.py * +
│   ├── install-zenml-dev.sh *
│   ├── publish_ci_qualification.py * +
│   ├── run-ci-checks.sh *
│   ├── test-coverage-xml.sh *
│   ├── test-migrations.sh *
│   └── validate_quarantine.py * +
├── src
│   ├── zenml
│   │   ├── cli
│   │   │   └── integration.py * +
│   │   ├── integrations
│   │   │   ├── airflow
│   │   │   │   └── ...
│   │   │   ├── argilla
│   │   │   │   └── ...
│   │   │   ├── aws
│   │   │   │   └── ...
│   │   │   ├── azure
│   │   │   │   └── ...
│   │   │   ├── bentoml
│   │   │   │   └── ...
│   │   │   ├── comet
│   │   │   │   └── ...
│   │   │   ├── databricks
│   │   │   │   └── ...
│   │   │   ├── deepchecks
│   │   │   │   └── ...
│   │   │   ├── discord
│   │   │   │   └── ...
│   │   │   ├── evidently
│   │   │   │   └── ...
│   │   │   ├── facets
│   │   │   │   └── ...
│   │   │   ├── feast
│   │   │   │   └── ...
│   │   │   ├── gcp
│   │   │   │   └── ...
│   │   │   ├── github
│   │   │   │   └── ...
│   │   │   ├── gitlab
│   │   │   │   └── ...
│   │   │   ├── great_expectations
│   │   │   │   └── ...
│   │   │   ├── huggingface
│   │   │   │   └── ...
│   │   │   ├── hyperai
│   │   │   │   └── ...
│   │   │   ├── jax
│   │   │   ├── kaniko
│   │   │   │   └── ...
│   │   │   ├── kubeflow
│   │   │   │   └── ...
│   │   │   ├── kubernetes
│   │   │   │   └── ...
│   │   │   ├── label_studio
│   │   │   │   └── ...
│   │   │   ├── langchain
│   │   │   │   └── ...
│   │   │   ├── lightgbm
│   │   │   │   └── ...
│   │   │   ├── lightning
│   │   │   │   └── ...
│   │   │   ├── llama_index
│   │   │   │   └── ...
│   │   │   ├── mlflow
│   │   │   │   └── ...
│   │   │   ├── mlx
│   │   │   ├── modal
│   │   │   │   └── ...
│   │   │   ├── neptune
│   │   │   │   └── ...
│   │   │   ├── neural_prophet
│   │   │   │   └── ...
│   │   │   ├── numpy
│   │   │   │   └── ...
│   │   │   ├── openai
│   │   │   │   └── ...
│   │   │   ├── pandas
│   │   │   │   └── ...
│   │   │   ├── pigeon
│   │   │   │   └── ...
│   │   │   ├── pillow
│   │   │   │   └── ...
│   │   │   ├── polars
│   │   │   │   └── ...
│   │   │   ├── prodigy
│   │   │   │   └── ...
│   │   │   ├── pycaret
│   │   │   │   └── ...
│   │   │   ├── pytorch
│   │   │   │   └── ...
│   │   │   ├── pytorch_lightning
│   │   │   │   └── ...
│   │   │   ├── runai
│   │   │   │   └── ...
│   │   │   ├── s3
│   │   │   │   └── ...
│   │   │   ├── scipy
│   │   │   │   └── ...
│   │   │   ├── seldon
│   │   │   │   └── ...
│   │   │   ├── sklearn
│   │   │   │   └── ...
│   │   │   ├── skypilot
│   │   │   │   └── ...
│   │   │   ├── skypilot_aws
│   │   │   │   └── ...
│   │   │   ├── skypilot_azure
│   │   │   │   └── ...
│   │   │   ├── skypilot_gcp
│   │   │   │   └── ...
│   │   │   ├── skypilot_kubernetes
│   │   │   │   └── ...
│   │   │   ├── skypilot_lambda
│   │   │   │   └── ...
│   │   │   ├── slack
│   │   │   │   └── ...
│   │   │   ├── spark
│   │   │   │   └── ...
│   │   │   ├── tekton
│   │   │   │   └── ...
│   │   │   ├── tensorboard
│   │   │   │   └── ...
│   │   │   ├── tensorflow
│   │   │   │   └── ...
│   │   │   ├── vllm
│   │   │   │   └── ...
│   │   │   ├── whylogs
│   │   │   │   └── ...
│   │   │   ├── xgboost
│   │   │   │   └── ...
│   │   │   ├── integration.py * +
│   │   │   └── registry.py * +
│   │   ├── alerter
│   │   ├── analytics
│   │   ├── annotators
│   │   ├── artifact_stores
│   │   ├── artifacts
│   │   ├── code_repositories
│   │   │   └── git
│   │   ├── config
│   │   ├── container_engines
│   │   ├── container_registries
│   │   ├── data_validators
│   │   ├── deployers
│   │   │   ├── docker
│   │   │   ├── local
│   │   │   └── server
│   │   │       └── ...
│   │   ├── dispatcher
│   │   ├── entrypoints
│   │   ├── execution
│   │   │   ├── pipeline
│   │   │   │   └── ...
│   │   │   └── step
│   │   ├── experiment_trackers
│   │   ├── feature_stores
│   │   ├── hooks
│   │   ├── image_builders
│   │   ├── io
│   │   ├── log_stores
│   │   │   ├── artifact
│   │   │   ├── datadog
│   │   │   └── otel
│   │   ├── login
│   │   │   └── pro
│   │   │       └── ...
│   │   ├── materializers
│   │   ├── metadata
│   │   ├── model
│   │   ├── model_deployers
│   │   ├── model_registries
│   │   ├── models
│   │   │   └── v2
│   │   │       └── ...
│   │   ├── orchestrators
│   │   │   ├── local
│   │   │   └── local_docker
│   │   ├── pipelines
│   │   │   └── dynamic
│   │   ├── secret
│   │   │   └── schemas
│   │   ├── service_connectors
│   │   ├── services
│   │   │   ├── container
│   │   │   └── local
│   │   ├── stack
│   │   ├── stack_deployments
│   │   ├── step_operators
│   │   ├── steps
│   │   ├── triggers
│   │   ├── utils
│   │   │   └── warnings
│   │   ├── zen_server
│   │   │   ├── deploy
│   │   │   │   └── ...
│   │   │   ├── feature_gate
│   │   │   ├── pipeline_execution
│   │   │   ├── rbac
│   │   │   └── routers
│   │   └── zen_stores
│   │       ├── migrations
│   │       │   └── ...
│   │       ├── resource_pools
│   │       ├── schemas
│   │       └── secrets_stores
│   └── zenml_cli
├── tests
│   ├── harness
│   │   ├── cfg
│   │   │   ├── deployments.yaml *
│   │   │   └── environments.yaml *
│   │   ├── deployment
│   │   │   └── base.py * +
│   │   ├── cli
│   │   └── model
│   ├── integration
│   │   ├── examples
│   │   │   ├── bentoml
│   │   │   │   └── ...
│   │   │   ├── deepchecks
│   │   │   │   └── ...
│   │   │   ├── discord
│   │   │   │   └── ...
│   │   │   ├── evidently
│   │   │   │   └── ...
│   │   │   ├── facets
│   │   │   │   └── ...
│   │   │   ├── great_expectations
│   │   │   │   └── ...
│   │   │   ├── huggingface
│   │   │   │   └── ...
│   │   │   ├── lightgbm
│   │   │   │   └── ...
│   │   │   ├── mlflow
│   │   │   │   └── ...
│   │   │   ├── neural_prophet
│   │   │   │   └── ...
│   │   │   ├── pytorch
│   │   │   │   └── ...
│   │   │   ├── scipy
│   │   │   │   └── ...
│   │   │   ├── seldon
│   │   │   │   └── ...
│   │   │   ├── sklearn
│   │   │   │   └── ...
│   │   │   ├── slack
│   │   │   │   └── ...
│   │   │   ├── tensorflow
│   │   │   │   └── ...
│   │   │   ├── whylogs
│   │   │   │   └── ...
│   │   │   ├── xgboost
│   │   │   │   └── ...
│   │   │   └── utils.py * +
│   │   ├── functional
│   │   │   ├── cli
│   │   │   │   └── test_model.py * +
│   │   │   ├── artifacts
│   │   │   ├── deployers
│   │   │   │   └── ...
│   │   │   ├── materializers
│   │   │   ├── model
│   │   │   ├── models
│   │   │   ├── pipelines
│   │   │   ├── steps
│   │   │   ├── triggers
│   │   │   ├── utils
│   │   │   ├── zen_server
│   │   │   │   └── ...
│   │   │   └── zen_stores
│   │   ├── integrations
│   │   │   ├── airflow
│   │   │   │   └── ...
│   │   │   ├── aws
│   │   │   │   └── ...
│   │   │   ├── azure
│   │   │   │   └── ...
│   │   │   ├── deepchecks
│   │   │   │   └── ...
│   │   │   ├── evidently
│   │   │   │   └── ...
│   │   │   ├── facets
│   │   │   │   └── ...
│   │   │   ├── gcp
│   │   │   │   └── ...
│   │   │   ├── gitlab
│   │   │   │   └── ...
│   │   │   ├── great_expectations
│   │   │   │   └── ...
│   │   │   ├── huggingface
│   │   │   │   └── ...
│   │   │   ├── hyperai
│   │   │   │   └── ...
│   │   │   ├── kaniko
│   │   │   │   └── ...
│   │   │   ├── kubeflow
│   │   │   │   └── ...
│   │   │   ├── kubernetes
│   │   │   │   └── ...
│   │   │   ├── label_studio
│   │   │   │   └── ...
│   │   │   ├── langchain
│   │   │   │   └── ...
│   │   │   ├── lightgbm
│   │   │   │   └── ...
│   │   │   ├── llama_index
│   │   │   │   └── ...
│   │   │   ├── mlflow
│   │   │   │   └── ...
│   │   │   ├── mlx
│   │   │   ├── modal
│   │   │   │   └── ...
│   │   │   ├── neptune
│   │   │   │   └── ...
│   │   │   ├── neural_prophet
│   │   │   │   └── ...
│   │   │   ├── numpy
│   │   │   ├── pandas
│   │   │   ├── pillow
│   │   │   │   └── ...
│   │   │   ├── polars
│   │   │   │   └── ...
│   │   │   ├── pytorch
│   │   │   │   └── ...
│   │   │   ├── runai
│   │   │   ├── s3
│   │   │   │   └── ...
│   │   │   ├── scipy
│   │   │   │   └── ...
│   │   │   ├── sklearn
│   │   │   │   └── ...
│   │   │   ├── skypilot
│   │   │   ├── tensorflow
│   │   │   │   └── ...
│   │   │   ├── whylogs
│   │   │   │   └── ...
│   │   │   └── xgboost
│   │   │       └── ...
│   │   └── conftest.py * +
│   ├── unit
│   │   ├── scripts
│   │   │   ├── ci
│   │   │   │   ├── __init__.py *
│   │   │   │   ├── test_classify_offload_result.py * +
│   │   │   │   ├── test_compute_offload_cache_keys.py * +
│   │   │   │   ├── test_emit_timing_manifest.py * +
│   │   │   │   ├── test_export_offload_integration_requirements.py * +
│   │   │   │   ├── test_normalize_offload_junit.py * +
│   │   │   │   ├── test_offload_config.py * +
│   │   │   │   ├── test_print_junit_summary.py * +
│   │   │   │   └── test_run_mixed_environment_pytest.py * +
│   │   │   └── __init__.py *
│   │   ├── artifact_stores
│   │   ├── artifacts
│   │   ├── cli
│   │   ├── config
│   │   ├── container_engine
│   │   ├── container_registries
│   │   ├── deployers
│   │   │   └── server
│   │   ├── entrypoints
│   │   ├── image_builders
│   │   ├── integrations
│   │   ├── io
│   │   ├── materializers
│   │   ├── metadata
│   │   ├── model_registries
│   │   ├── models
│   │   ├── orchestrators
│   │   │   ├── local
│   │   │   └── local_docker
│   │   ├── pipelines
│   │   │   └── dynamic
│   │   ├── services
│   │   ├── stack
│   │   ├── steps
│   │   ├── utils
│   │   ├── zen_server
│   │   └── zen_stores
│   └── stress-test
├── .claude
│   └── skills
│       └── zenml-backport
├── .cursor
│   └── rules
├── .hyperlint
├── docker
├── docs
│   ├── _static
│   ├── _templates
│   ├── book
│   │   ├── .gitbook
│   │   │   ├── assets
│   │   │   └── includes
│   │   ├── api-docs
│   │   │   ├── .gitbook
│   │   │   │   └── ...
│   │   │   ├── oss-api
│   │   │   │   └── ...
│   │   │   ├── oss-api-docs
│   │   │   │   └── ...
│   │   │   ├── pro-api
│   │   │   │   └── ...
│   │   │   └── pro-api-docs
│   │   │       └── ...
│   │   ├── component-guide
│   │   │   ├── .gitbook
│   │   │   │   └── ...
│   │   │   ├── alerters
│   │   │   ├── annotators
│   │   │   ├── artifact-stores
│   │   │   ├── container-registries
│   │   │   ├── contribute
│   │   │   ├── data-validators
│   │   │   ├── deployers
│   │   │   ├── experiment-trackers
│   │   │   ├── feature-stores
│   │   │   ├── image-builders
│   │   │   ├── log-stores
│   │   │   ├── model-deployers
│   │   │   ├── model-registries
│   │   │   ├── orchestrators
│   │   │   ├── service-connectors
│   │   │   │   └── ...
│   │   │   └── step-operators
│   │   ├── getting-started
│   │   │   ├── deploying-zenml
│   │   │   └── zenml-pro
│   │   │       └── ...
│   │   ├── how-to
│   │   │   ├── artifacts
│   │   │   ├── code-repositories
│   │   │   ├── containerization
│   │   │   ├── contribute-to-zenml
│   │   │   ├── dashboard
│   │   │   ├── deployment
│   │   │   ├── environment-variables
│   │   │   ├── infrastructure-deployment
│   │   │   │   └── ...
│   │   │   ├── manage-zenml-server
│   │   │   │   └── ...
│   │   │   ├── metadata
│   │   │   ├── models
│   │   │   ├── popular-integrations
│   │   │   ├── secrets
│   │   │   ├── snapshots
│   │   │   ├── stack-components
│   │   │   ├── steps-pipelines
│   │   │   ├── tags
│   │   │   └── templates
│   │   ├── reference
│   │   ├── sdk-docs
│   │   │   └── .gitbook
│   │   │       └── ...
│   │   └── user-guide
│   │       ├── .gitbook
│   │       │   └── ...
│   │       ├── best-practices
│   │       ├── llmops-guide
│   │       │   └── ...
│   │       ├── production-guide
│   │       ├── starter-guide
│   │       └── tutorial
│   ├── changelog-items
│   └── mkdocs
│       ├── _assets
│       └── overrides
├── examples
│   ├── agent_comparison
│   │   ├── materializers
│   │   ├── pipelines
│   │   ├── prompts
│   │   └── steps
│   ├── agent_framework_integrations
│   │   ├── autogen
│   │   ├── aws_strands
│   │   ├── crewai
│   │   ├── google_adk
│   │   ├── haystack
│   │   ├── langchain
│   │   ├── langgraph
│   │   ├── llama_index
│   │   ├── openai_agents_sdk
│   │   │   └── ui
│   │   ├── pydanticai
│   │   ├── qwen-agent
│   │   └── semantic_kernel
│   ├── agent_outer_loop
│   │   ├── configs
│   │   ├── pipelines
│   │   ├── steps
│   │   └── visualizations
│   ├── computer_vision
│   │   ├── annotators
│   │   ├── assets
│   │   ├── materializers
│   │   ├── pipelines
│   │   ├── steps
│   │   └── ui
│   ├── deploying_agent
│   │   ├── assets
│   │   ├── pipelines
│   │   ├── steps
│   │   │   └── templates
│   │   └── ui
│   ├── deploying_ml_model
│   │   ├── assets
│   │   ├── pipelines
│   │   ├── steps
│   │   └── ui
│   ├── e2e
│   │   ├── .assets
│   │   ├── configs
│   │   ├── pipelines
│   │   ├── steps
│   │   │   ├── alerts
│   │   │   ├── data_quality
│   │   │   ├── deployment
│   │   │   ├── etl
│   │   │   ├── hp_tuning
│   │   │   ├── inference
│   │   │   ├── promotion
│   │   │   └── training
│   │   └── utils
│   ├── e2e_nlp
│   │   ├── .assets
│   │   ├── gradio
│   │   ├── pipelines
│   │   ├── steps
│   │   │   ├── alerts
│   │   │   ├── dataset_loader
│   │   │   ├── deploying
│   │   │   ├── promotion
│   │   │   ├── register
│   │   │   ├── tokenizer_loader
│   │   │   ├── tokenzation
│   │   │   └── training
│   │   └── utils
│   ├── hierarchical_doc_search_agent
│   │   ├── data
│   │   ├── pipelines
│   │   ├── steps
│   │   └── ui
│   ├── hydra_config_management
│   │   ├── conf
│   │   ├── pipelines
│   │   └── steps
│   ├── lakefs_data_versioning
│   │   ├── configs
│   │   ├── pipelines
│   │   ├── steps
│   │   └── utils
│   ├── llm_finetuning
│   │   ├── .assets
│   │   ├── configs
│   │   ├── materializers
│   │   ├── pipelines
│   │   ├── steps
│   │   └── utils
│   ├── mlops_starter
│   │   ├── .assets
│   │   ├── configs
│   │   ├── pipelines
│   │   ├── steps
│   │   └── utils
│   ├── optuna_hyperparameter_tuning
│   │   ├── config
│   │   ├── pipelines
│   │   └── steps
│   ├── quickstart
│   │   ├── pipelines
│   │   └── steps
│   ├── rlm_document_analysis
│   │   ├── data
│   │   ├── pipelines
│   │   ├── steps
│   │   ├── ui
│   │   └── utils
│   └── weather_agent
│       ├── assets
│       ├── pipelines
│       ├── steps
│       └── ui
├── helm
│   └── templates
│       └── tests
├── infra
│   ├── aws
│   ├── gcp
│   └── scripts
├── CONTRIBUTING.md *
├── Dockerfile.ci *
├── Dockerfile.ci.dockerignore *
├── offload-modal-server-mysql.toml *
├── offload.toml *
└── pyproject.toml *


(* denotes selected files)
(+ denotes code-map available)
Config: directory-only view; depth cap 3; selected files shown.

File: /Users/safoine/zenml-io/zenml/src/zenml/metadata/metadata_types.py
Imports:
  - import json
  - from typing import Any, Dict, List, Set, Tuple, Union
  - from pydantic import GetCoreSchemaHandler
  - from pydantic_core import CoreSchema, core_schema
  - from zenml.constants import STR_FIELD_MAX_LENGTH, TEXT_FIELD_MAX_LENGTH
  - from zenml.logger import get_logger
  - from zenml.utils.enum_utils import StrEnum
  - from zenml.utils.json_utils import pydantic_encoder
---
Classes:
  - Uri
    Methods:
      - L34: def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
  - Path
    Methods:
      - L53: def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
  - DType
    Methods:
      - L72: def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
  - StorageSize
    Methods:
      - L91: def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:

Functions:
  - L176: def get_metadata_type(
    object_: object,
) -> MetadataTypeEnum:
  - L196: def cast_to_metadata_type(
    value: object,
    type_: MetadataTypeEnum,
) -> MetadataType:
  - L214: def validate_metadata(
    metadata: Dict[str, MetadataType],
) -> Dict[str, MetadataType]:

Enums:
  - MetadataTypeEnum

Global vars:
  - logger
  - MetadataType
  - MetadataTypeTuple
  - metadata_type_to_enum_mapping
  - metadata_enum_to_type_mapping
---


File: /Users/safoine/zenml-io/zenml/tests/harness/model/deployment.py
Imports:
  - from enum import Enum
  - from typing import TYPE_CHECKING, Dict, Optional
  - from pydantic import ConfigDict, Field
  - from tests.harness.model.base import BaseTestConfigModel
  - from tests.harness.model.secret import BaseTestSecretConfigModel
  - from tests.harness.deployment import BaseTestDeployment
  - from tests.harness.harness import TestHarness
---
Classes:
  - DeploymentStoreConfig
    Properties:
      - url
      - model_config
  - DeploymentConfig
    Methods:
      - L65: def get_deployment(self) -> "BaseTestDeployment":
      - L75: def compile(self, harness: "TestHarness") -> None:
    Properties:
      - name
      - description
      - server
      - database
      - config
      - disabled
      - capabilities

Enums:
  - ServerType
  - DatabaseType
---


File: /Users/safoine/zenml-io/zenml/src/zenml/models/v2/core/pipeline_run.py
Imports:
  - from datetime import datetime
  - from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)
  - from uuid import UUID
  - from pydantic import ConfigDict, Field, model_validator
  - from zenml.config.pipeline_configurations import PipelineConfiguration
  - from zenml.constants import STR_FIELD_MAX_LENGTH
  - from zenml.enums import ExecutionStatus, PipelineRunTriggeredByType
  - from zenml.metadata.metadata_types import MetadataType
  - from zenml.models.v2.base.base import BaseUpdate, BaseZenModel
  - from zenml.models.v2.base.scoped import (
    ProjectScopedFilter,
    ProjectScopedRequest,
    ProjectScopedResponse,
    ProjectScopedResponseBody,
    ProjectScopedResponseMetadata,
    ProjectScopedResponseResources,
    RunMetadataFilterMixin,
    TaggableFilter,
)
  - from zenml.models.v2.core.logs import LogsRequest
  - from zenml.models.v2.core.model_version import ModelVersionResponse
  - from zenml.models.v2.core.tag import TagResponse
  - from zenml.models.v2.misc.exception_info import ExceptionInfo
  - from zenml.utils import pagination_utils
  - from zenml.utils.tag_utils import Tag
  - from sqlalchemy.sql.elements import ColumnElement
  - from zenml.models.v2.core.artifact_version import ArtifactVersionResponse
  - from zenml.models.v2.core.code_reference import CodeReferenceResponse
  - from zenml.models.v2.core.curated_visualization import (
        CuratedVisualizationResponse,
    )
  - from zenml.models.v2.core.logs import LogsResponse
  - from zenml.models.v2.core.pipeline import PipelineResponse
  - from zenml.models.v2.core.pipeline_build import (
        PipelineBuildResponse,
    )
  - from zenml.models.v2.core.pipeline_snapshot import PipelineSnapshotResponse
  - from zenml.models.v2.core.run_wait_condition import (
        RunWaitConditionResponse,
    )
  - from zenml.models.v2.core.schedule import ScheduleResponse
  - from zenml.models.v2.core.stack import StackResponse
  - from zenml.models.v2.core.step_run import StepRunResponse
  - from zenml.models.v2.core.triggers import (
        TRIGGER_RETURN_TYPE_UNION,
        TriggerExecutionInfo,
    )
  - from zenml.zen_stores.schemas.base_schemas import BaseSchema
  - from zenml.client import Client
  - from zenml.artifacts.utils import (
            get_artifacts_versions_of_pipeline_run,
        )
  - from sqlmodel import and_, col, or_
  - from zenml.zen_stores.schemas import (
            CodeReferenceSchema,
            CodeRepositorySchema,
            DeploymentSchema,
            ModelSchema,
            ModelVersionPipelineRunSchema,
            ModelVersionSchema,
            PipelineBuildSchema,
            PipelineRunSchema,
            PipelineSchema,
            PipelineSnapshotSchema,
            ScheduleSchema,
            StackComponentSchema,
            StackCompositionSchema,
            StackSchema,
            StepRunSchema,
            TriggerExecutionSchema,
        )
  - from sqlmodel import asc, desc
  - from zenml.enums import SorterOps
  - from zenml.zen_stores.schemas import (
            ModelSchema,
            ModelVersionSchema,
            PipelineRunSchema,
            PipelineSchema,
            PipelineSnapshotSchema,
            StackSchema,
        )
---
Classes:
  - PipelineRunTriggerInfo
    Properties:
      - step_run_id
      - deployment_id
  - PipelineRunRequest
    Methods:
      - L161: def is_placeholder_request(self) -> bool:
      - L173: def _validate_status(self) -> "PipelineRunRequest":
    Properties:
      - name
      - snapshot
      - orchestrator_run_id
      - start_time
      - end_time
      - status
      - status_reason
      - orchestrator_environment
      - trigger_info
      - tags
      - logs
      - exception_info
      - original_run_id
      - model_config
  - PipelineRunUpdate
    Properties:
      - status
      - status_reason
      - orchestrator_run_id
      - exception_info
      - add_tags
      - remove_tags
      - add_logs
      - model_config
  - PipelineRunResponseBody
    Properties:
      - status
      - in_progress
      - status_reason
      - index
      - pipeline_id
      - model_config
  - PipelineRunResponseMetadata
    Properties:
      - __zenml_skip_dehydration__
      - run_metadata
      - config
      - start_time
      - end_time
      - client_environment
      - orchestrator_environment
      - orchestrator_run_id
      - code_path
      - template_id
      - is_templatable
      - trigger_info
      - enable_heartbeat
      - exception_info
      - trigger_execution_info
  - PipelineRunResponseResources
    Properties:
      - snapshot
      - source_snapshot
      - stack
      - pipeline
      - build
      - schedule
      - code_reference
      - model_version
      - tags
      - log_collection
      - visualizations
      - trigger
      - original_run
      - active_wait_condition
      - model_config
  - PipelineRunResponse
    Methods:
      - L396: def get_hydrated_version(self) -> "PipelineRunResponse":
      - L408: def artifact_versions(self) -> List["ArtifactVersionResponse"]:
      - L421: def produced_artifact_versions(self) -> List["ArtifactVersionResponse"]:
      - L435: def status(self) -> ExecutionStatus:
      - L444: def index(self) -> int:
      - L453: def run_metadata(self) -> Dict[str, MetadataType]:
      - L462: def steps(self) -> Dict[str, "StepRunResponse"]:
      - L481: def config(self) -> PipelineConfiguration:
      - L490: def start_time(self) -> Optional[datetime]:
      - L499: def end_time(self) -> Optional[datetime]:
      - L508: def in_progress(self) -> bool:
      - L517: def client_environment(self) -> Dict[str, Any]:
      - L526: def orchestrator_environment(self) -> Dict[str, Any]:
      - L535: def orchestrator_run_id(self) -> Optional[str]:
      - L544: def code_path(self) -> Optional[str]:
      - L553: def template_id(self) -> Optional[UUID]:
      - L562: def is_templatable(self) -> bool:
      - L571: def trigger_info(self) -> Optional[PipelineRunTriggerInfo]:
      - L580: def enable_heartbeat(self) -> bool:
      - L589: def exception_info(self) -> Optional[ExceptionInfo]:
      - L598: def triggered_by_deployment(self) -> bool:
      - L610: def snapshot(self) -> Optional["PipelineSnapshotResponse"]:
      - L619: def source_snapshot(self) -> Optional["PipelineSnapshotResponse"]:
      - L628: def stack(self) -> Optional["StackResponse"]:
      - L637: def pipeline(self) -> Optional["PipelineResponse"]:
      - L646: def build(self) -> Optional["PipelineBuildResponse"]:
      - L655: def schedule(self) -> Optional["ScheduleResponse"]:
      - L664: def code_reference(self) -> Optional["CodeReferenceResponse"]:
      - L673: def model_version(self) -> Optional[ModelVersionResponse]:
      - L682: def tags(self) -> List[TagResponse]:
      - L691: def log_collection(self) -> Optional[List["LogsResponse"]]:
      - L700: def trigger(self) -> Optional["TRIGGER_RETURN_TYPE_UNION"]:
      - L709: def trigger_execution_info(self) -> Optional["TriggerExecutionInfo"]:
      - L718: def original_run(self) -> Optional["PipelineRunResponse"]:
      - L727: def active_wait_condition(self) -> Optional["RunWaitConditionResponse"]:
      - L736: def pipeline_id(self) -> UUID | None:
    Properties:
      - name
  - PipelineRunFilter
    Methods:
      - L925: def get_custom_filters(
        self,
        table: Type["AnySchema"],
    ) -> List["ColumnElement[bool]"]:
      - L1162: def apply_sorting(
        self,
        query: AnyQuery,
        table: Type["AnySchema"],
    ) -> AnyQuery:
    Properties:
      - CUSTOM_SORTING_OPTIONS
      - FILTER_EXCLUDE_FIELDS
      - CLI_EXCLUDE_FIELDS
      - API_MULTI_INPUT_PARAMS
      - name
      - index
      - orchestrator_run_id
      - pipeline_id
      - stack_id
      - schedule_id
      - build_id
      - snapshot_id
      - code_repository_id
      - template_id
      - source_snapshot_id
      - model_version_id
      - linked_to_model_version_id
      - status
      - in_progress
      - start_time
      - end_time
      - pipeline_name
      - pipeline
      - stack
      - code_repository
      - model
      - stack_component
      - templatable
      - triggered_by_step_run_id
      - triggered_by_deployment_id
      - trigger_id
      - model_config

Global vars:
  - AnyQuery
---


File: /Users/safoine/zenml-io/zenml/src/zenml/container_engines/docker_engine.py
Imports:
  - import json
  - import re
  - import shutil
  - import subprocess
  - import tempfile
  - from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    cast,
)
  - from docker.client import DockerClient
  - from docker.errors import DockerException
  - from zenml.constants import DOCKERHUB_REGISTRY_URI
  - from zenml.container_engines import ContainerEngine
  - from zenml.enums import ContainerEngineType
  - from zenml.exceptions import AuthorizationException
  - from zenml.logger import get_logger
  - from zenml.config.docker_settings import DockerBuildOptions
  - from zenml.container_registries.base_container_registry import (
        BaseContainerRegistry,
    )
  - from zenml.image_builders import BuildContext
---
Classes:
  - DockerContainerEngine
    Methods:
      - L54: def __init__(self) -> None:
      - L59: def engine_type(self) -> ContainerEngineType:
      - L67: def check_availability(self) -> Tuple[bool, str | None]:
      - L105: def client(self) -> DockerClient:
      - L127: def login_client(
        self,
        username: str,
        password: str,
        registry: str,
    ) -> None:
      - L158: def login_cli(
        username: str,
        password: str,
        registry: str,
    ) -> None:
      - L195: def process_docker_stream(stream: Iterable[bytes]) -> List[Dict[str, Any]]:
      - L236: def login(
        self,
        username: str,
        password: str,
        registry: str,
    ) -> None:
      - L260: def build(
        self,
        image_name: str,
        build_context: "BuildContext",
        docker_build_options: Optional["DockerBuildOptions"] = None,
        container_registry: Optional["BaseContainerRegistry"] = None,
        **kwargs: Any,
    ) -> None:
      - L303: def _build_cli(
        self,
        image_name: str,
        build_context: "BuildContext",
        docker_build_options: Optional["DockerBuildOptions"] = None,
    ) -> None:
      - L333: def tag_image(self, source: str, target: str) -> None:
      - L343: def push_image(
        self,
        image_name: str,
        container_registry: Optional["BaseContainerRegistry"] = None,
    ) -> str:
      - L402: def is_image_local(self, image_name: str) -> bool:
      - L420: def get_image_repo_digest(
        self,
        image_name: str,
        container_registry: Optional["BaseContainerRegistry"] = None,
    ) -> Optional[str]:
      - L448: def close(self) -> None:

Global vars:
  - logger
---


File: /Users/safoine/zenml-io/zenml/src/zenml/stack/flavor.py
Imports:
  - import os
  - from abc import abstractmethod
  - from typing import Any, Dict, Optional, Type, cast
  - from zenml.enums import StackComponentType
  - from zenml.exceptions import CustomFlavorImportError
  - from zenml.models import (
    FlavorRequest,
    FlavorResponse,
    ServiceConnectorRequirements,
)
  - from zenml.stack.stack_component import StackComponent, StackComponentConfig
  - from zenml.utils import source_utils
  - from zenml import __version__
  - from zenml.stack.stack_component import (
        StackComponent,
        StackComponentConfig,
    )
---
Classes:
  - Flavor
    Methods:
      - L36: def name(self) -> str:
      - L44: def display_name(self) -> Optional[str]:
      - L57: def docs_url(self) -> Optional[str]:
      - L66: def sdk_docs_url(self) -> Optional[str]:
      - L75: def logo_url(self) -> Optional[str]:
      - L85: def type(self) -> StackComponentType:
      - L94: def implementation_class(self) -> Type[StackComponent]:
      - L103: def config_class(self) -> Type[StackComponentConfig]:
      - L111: def config_schema(self) -> Dict[str, Any]:
      - L120: def service_connector_requirements(
        self,
    ) -> Optional[ServiceConnectorRequirements]:
      - L135: def from_model(cls, flavor_model: FlavorResponse) -> "Flavor":
      - L171: def to_model(
        self,
        integration: Optional[str] = None,
        is_custom: bool = True,
    ) -> FlavorRequest:
      - L219: def generate_default_docs_url(self) -> str:
      - L234: def generate_default_sdk_docs_url(self) -> str:

Functions:
  - L269: def validate_flavor_source(
    source: str, component_type: StackComponentType
) -> Type["Flavor"]:
---

</file_map>
<file_contents>
File: /Users/safoine/Library/Application Support/RepoPrompt/Workspaces/Workspace-zenml-7750E617-34D0-483E-88E9-2A39A0619DB2/_git_data/repos/zenml-2aefb64b/2026-05-08/1045/MAP.txt
```txt
# MAP.txt v1
# (grep tip: search for "SNAPSHOT_" or "SECTION:")

SECTION: SNAPSHOT_META
SNAPSHOT_ID: 2026-05-08/1045
SNAPSHOT_DIR: repos/zenml-2aefb64b/2026-05-08/1045
SNAPSHOT_GENERATED_AT: 2026-05-08T09:45:51Z
SNAPSHOT_MODE: standard
SNAPSHOT_MODE_DETAILS: standard: full diff patches (all.patch + per-file when size allows)
SNAPSHOT_COMPARE: develop
SNAPSHOT_SCOPE: all
SNAPSHOT_CHANGED_FILES: 64
SNAPSHOT_INSERTIONS: 10572
SNAPSHOT_DELETIONS: 130

SECTION: REPOSITORY
REPO_KEY: zenml-2aefb64b
REPO_ROOT: /Users/safoine/zenml-io/zenml

SECTION: FINGERPRINT
FINGERPRINT_HEAD_SHA: d13c19f81d980dba02d19877087907e8c5e54b3e
FINGERPRINT_BASE_REF: develop
FINGERPRINT_STATUS_HASH: revspec:develop

SECTION: ADVANCED
ADV_CONTEXT_LINES: 3
ADV_DETECT_RENAMES: false

SECTION: ARTIFACTS
ARTIFACT_MANIFEST: manifest.json
ARTIFACT_MAP: MAP.txt
ARTIFACT_FILES_TSV: index/files.tsv
ARTIFACT_CHANGED_LINES: index/changed_lines.tsv
ARTIFACT_TREE: index/files.tree.txt
ARTIFACT_ALL_PATCH: diff/all.patch

SECTION: CHANGED_LINES_FORMAT
index/changed_lines.tsv: TSV columns: path, line_number, change_type(+/-), content
  - line_number: new-file line for '+', old-file line for '-'

SECTION: COMMIT_GRAPH
* d13c19f81d (HEAD -> feature/new-ci-architecture, origin/feature/new-ci-architecture) tests
* b55e4c72a2 improe tests
* d1a2967268 remove buffer docs
* 7155e2554c improe slow tests
*   10a0ba3fe2 Merge branch 'develop' into feature/new-ci-architecture
|\  
| * 76fc664a59 (origin/develop, develop) Fix notify projects backend zizmor scan (#4808)
| * 98e95520a4 bugfix (#4803)
* | 3146d004ce fixes
* | e1f6ef54b2 amnother try
* | 776fee95d6 more improv
* | ea276e3e2e extra fixes
* | 07db76a6a7 fix the fialing modal
* | e293f8db7f fixes
* | 6f47c30321 Remove concurrency settings from the Linux fast offload workflow
* | 9b375b1630 Refactor CI workflow by removing Modal MySQL sandbox jobs and adjusting dependencies
* | 4d4b428372 cleanup
* | a3563e7f2b Update CI workflows to refine offload conditions and adjust exit codes
* |   e08c7333ed Merge branch 'feature/new-ci-architecture' of github.com:zenml-io/zenml into feature/new-ci-architecture
|\ \  
| * | 53ae95fb7a test offload
* | | c2a18bc90f test offload
|/ /

SECTION: CHANGED_FILE_TREE
.github/
  workflows/
    base-package-functionality.yml  [05] M +1 -1
    ci-fast.yml  [06] M +59 -57
    ci-medium.yml  [07] A +194 -0
    ci-slow-develop.yml  [08] A +349 -0
    ci-slow.yml  [09] M +0 -18
    develop-health-gate.yml  [10] A +21 -0
    integration-test-fast.yml  [11] M +42 -5
    integration-test-slow.yml  [12] M +7 -0
    linting.yml  [13] M +1 -1
    linux-fast-offload.yml  [14] A +408 -0
    modal-ci-image-warm.yml  [15] A +22 -0
    offload-cache-warm.yml  [16] A +30 -0
    release.yml  [17] M +23 -2
    slow-ci-on-pr.yml  [18] A +51 -0
    unit-test.yml  [19] M +1 -1
    validate-quarantine.yml  [20] A +19 -0
    validate-workspace-safety.yml  [21] A +20 -0
    vscode-tutorial-pipelines-test.yml  [22] M +7 -0
  ci-captains.yml  [01] A +2 -0
  ci-phase-c-rollout.md  [02] A +104 -0
  CLAUDE.md  [03] M +9 -0
  quarantined-tests.yml  [04] A +3 -0
  workspace-safety-baseline.txt  [23] A +763 -0
  zizmor.yml  [24] M +4 -2
scripts/
  ci/
    __init__.py  [32] A +0 -0
    classify_offload_result.py  [33] A +185 -0
    compute_offload_cache_keys.py  [34] A +229 -0
    emit_timing_manifest.py  [35] A +150 -0
    export_offload_integration_requirements.py  [36] A +69 -0
    modal_sandbox_requirements.txt  [37] A +3 -0
    normalize_offload_junit.py  [38] A +70 -0
    print_junit_failures.py  [39] A +52 -0
    print_junit_summary.py  [40] A +100 -0
    run_mixed_environment_pytest.py  [41] A +147 -0
  audit_integration_workspace_safety.py  [30] A +132 -0
  check_known_good.py  [31] A +103 -0
  ci_matrix_hash.py  [42] A +56 -0
  ci_modal_mysql_sandbox.py  [43] A +317 -0
  develop_health_gate.py  [44] A +216 -0
  publish_ci_qualification.py  [45] A +124 -0
  test-migrations.sh  [46] M +15 -1
  validate_quarantine.py  [47] A +71 -0
tests/
  harness/
    cfg/
      deployments.yaml  [48] M +11 -0
      environments.yaml  [49] M +12 -0
    deployment/
      base.py  [50] M +1 -1
  integration/
    examples/
      utils.py  [52] M +6 -2
    functional/
      cli/
        test_model.py  [53] M +40 -39
    conftest.py  [51] A +109 -0
  unit/
    scripts/
      ci/
        __init__.py  [55] A +0 -0
        test_classify_offload_result.py  [56] A +158 -0
        test_compute_offload_cache_keys.py  [57] A +154 -0
        test_emit_timing_manifest.py  [58] A +37 -0
        test_export_offload_integration_requirements.py  [59] A +45 -0
        test_normalize_offload_junit.py  [60] A +45 -0
        test_offload_config.py  [61] A +55 -0
        test_print_junit_summary.py  [62] A +44 -0
        test_run_mixed_environment_pytest.py  [63] A +84 -0
      __init__.py  [54] A +0 -0
CONTRIBUTING.md  [25] M +4 -0
Dockerfile.ci  [26] A +56 -0
Dockerfile.ci.dockerignore  [27] A +35 -0
offload-modal-server-mysql.toml  [28] A +32 -0
offload.toml  [29] A +32 -0
uv.lock  [64] A +5433 -0

SECTION: JUMP_TABLE
[01] A +2 -0  .github/ci-captains.yml -> diff/per-file/.github__ci-captains.yml.patch
[02] A +104 -0  .github/ci-phase-c-rollout.md -> diff/per-file/.github__ci-phase-c-rollout.md.patch
[03] M +9 -0  .github/CLAUDE.md -> diff/per-file/.github__CLAUDE.md.patch
[04] A +3 -0  .github/quarantined-tests.yml -> diff/per-file/.github__quarantined-tests.yml.patch
[05] M +1 -1  .github/workflows/base-package-functionality.yml -> diff/per-file/.github__workflows__base-package-functionality.yml.patch
[06] M +59 -57  .github/workflows/ci-fast.yml -> diff/per-file/.github__workflows__ci-fast.yml.patch
[07] A +194 -0  .github/workflows/ci-medium.yml -> diff/per-file/.github__workflows__ci-medium.yml.patch
[08] A +349 -0  .github/workflows/ci-slow-develop.yml -> diff/per-file/.github__workflows__ci-slow-develop.yml.patch
[09] M +0 -18  .github/workflows/ci-slow.yml -> diff/per-file/.github__workflows__ci-slow.yml.patch
[10] A +21 -0  .github/workflows/develop-health-gate.yml -> diff/per-file/.github__workflows__develop-health-gate.yml.patch
[11] M +42 -5  .github/workflows/integration-test-fast.yml -> diff/per-file/.github__workflows__integration-test-fast.yml.patch
[12] M +7 -0  .github/workflows/integration-test-slow.yml -> diff/per-file/.github__workflows__integration-test-slow.yml.patch
[13] M +1 -1  .github/workflows/linting.yml -> diff/per-file/.github__workflows__linting.yml.patch
[14] A +408 -0  .github/workflows/linux-fast-offload.yml -> diff/per-file/.github__workflows__linux-fast-offload.yml.patch
[15] A +22 -0  .github/workflows/modal-ci-image-warm.yml -> diff/per-file/.github__workflows__modal-ci-image-warm.yml.patch
[16] A +30 -0  .github/workflows/offload-cache-warm.yml -> diff/per-file/.github__workflows__offload-cache-warm.yml.patch
[17] M +23 -2  .github/workflows/release.yml -> diff/per-file/.github__workflows__release.yml.patch
[18] A +51 -0  .github/workflows/slow-ci-on-pr.yml -> diff/per-file/.github__workflows__slow-ci-on-pr.yml.patch
[19] M +1 -1  .github/workflows/unit-test.yml -> diff/per-file/.github__workflows__unit-test.yml.patch
[20] A +19 -0  .github/workflows/validate-quarantine.yml -> diff/per-file/.github__workflows__validate-quarantine.yml.patch
[21] A +20 -0  .github/workflows/validate-workspace-safety.yml -> diff/per-file/.github__workflows__validate-workspace-safety.yml.patch
[22] M +7 -0  .github/workflows/vscode-tutorial-pipelines-test.yml -> diff/per-file/.github__workflows__vscode-tutorial-pipelines-test.yml.patch
[23] A +763 -0  .github/workspace-safety-baseline.txt -> diff/per-file/.github__workspace-safety-baseline.txt.patch
[24] M +4 -2  .github/zizmor.yml -> diff/per-file/.github__zizmor.yml.patch
[25] M +4 -0  CONTRIBUTING.md -> diff/per-file/CONTRIBUTING.md.patch
[26] A +56 -0  Dockerfile.ci -> diff/per-file/Dockerfile.ci.patch
[27] A +35 -0  Dockerfile.ci.dockerignore -> diff/per-file/Dockerfile.ci.dockerignore.patch
[28] A +32 -0  offload-modal-server-mysql.toml -> diff/per-file/offload-modal-server-mysql.toml.patch
[29] A +32 -0  offload.toml -> diff/per-file/offload.toml.patch
[30] A +132 -0  scripts/audit_integration_workspace_safety.py -> diff/per-file/scripts__audit_integration_workspace_safety.py.patch
[31] A +103 -0  scripts/check_known_good.py -> diff/per-file/scripts__check_known_good.py.patch
[32] A +0 -0  scripts/ci/__init__.py -> diff/per-file/scripts__ci____init__.py.patch
[33] A +185 -0  scripts/ci/classify_offload_result.py -> diff/per-file/scripts__ci__classify_offload_result.py.patch
[34] A +229 -0  scripts/ci/compute_offload_cache_keys.py -> diff/per-file/scripts__ci__compute_offload_cache_keys.py.patch
[35] A +150 -0  scripts/ci/emit_timing_manifest.py -> diff/per-file/scripts__ci__emit_timing_manifest.py.patch
[36] A +69 -0  scripts/ci/export_offload_integration_requirements.py -> diff/per-file/scripts__ci__export_offload_integration_requirements.py.patch
[37] A +3 -0  scripts/ci/modal_sandbox_requirements.txt -> diff/per-file/scripts__ci__modal_sandbox_requirements.txt.patch
[38] A +70 -0  scripts/ci/normalize_offload_junit.py -> diff/per-file/scripts__ci__normalize_offload_junit.py.patch
[39] A +52 -0  scripts/ci/print_junit_failures.py -> diff/per-file/scripts__ci__print_junit_failures.py.patch
[40] A +100 -0  scripts/ci/print_junit_summary.py -> diff/per-file/scripts__ci__print_junit_summary.py.patch
[41] A +147 -0  scripts/ci/run_mixed_environment_pytest.py -> diff/per-file/scripts__ci__run_mixed_environment_pytest.py.patch
[42] A +56 -0  scripts/ci_matrix_hash.py -> diff/per-file/scripts__ci_matrix_hash.py.patch
[43] A +317 -0  scripts/ci_modal_mysql_sandbox.py -> diff/per-file/scripts__ci_modal_mysql_sandbox.py.patch
[44] A +216 -0  scripts/develop_health_gate.py -> diff/per-file/scripts__develop_health_gate.py.patch
[45] A +124 -0  scripts/publish_ci_qualification.py -> diff/per-file/scripts__publish_ci_qualification.py.patch
[46] M +15 -1  scripts/test-migrations.sh -> diff/per-file/scripts__test-migrations.sh.patch
[47] A +71 -0  scripts/validate_quarantine.py -> diff/per-file/scripts__validate_quarantine.py.patch
[48] M +11 -0  tests/harness/cfg/deployments.yaml -> diff/per-file/tests__harness__cfg__deployments.yaml.patch
[49] M +12 -0  tests/harness/cfg/environments.yaml -> diff/per-file/tests__harness__cfg__environments.yaml.patch
[50] M +1 -1  tests/harness/deployment/base.py -> diff/per-file/tests__harness__deployment__base.py.patch
[51] A +109 -0  tests/integration/conftest.py -> diff/per-file/tests__integration__conftest.py.patch
[52] M +6 -2  tests/integration/examples/utils.py -> diff/per-file/tests__integration__examples__utils.py.patch
[53] M +40 -39  tests/integration/functional/cli/test_model.py -> diff/per-file/tests__integration__functional__cli__test_model.py.patch
[54] A +0 -0  tests/unit/scripts/__init__.py -> diff/per-file/tests__unit__scripts____init__.py.patch
[55] A +0 -0  tests/unit/scripts/ci/__init__.py -> diff/per-file/tests__unit__scripts__ci____init__.py.patch
[56] A +158 -0  tests/unit/scripts/ci/test_classify_offload_result.py -> diff/per-file/tests__unit__scripts__ci__test_classify_offload_result.py.patch
[57] A +154 -0  tests/unit/scripts/ci/test_compute_offload_cache_keys.py -> diff/per-file/tests__unit__scripts__ci__test_compute_offload_cache_keys.py.patch
[58] A +37 -0  tests/unit/scripts/ci/test_emit_timing_manifest.py -> diff/per-file/tests__unit__scripts__ci__test_emit_timing_manifest.py.patch
[59] A +45 -0  tests/unit/scripts/ci/test_export_offload_integration_requirements.py -> diff/per-file/tests__unit__scripts__ci__test_export_offload_integration_requirements.py.patch
[60] A +45 -0  tests/unit/scripts/ci/test_normalize_offload_junit.py -> diff/per-file/tests__unit__scripts__ci__test_normalize_offload_junit.py.patch
[61] A +55 -0  tests/unit/scripts/ci/test_offload_config.py -> diff/per-file/tests__unit__scripts__ci__test_offload_config.py.patch
[62] A +44 -0  tests/unit/scripts/ci/test_print_junit_summary.py -> diff/per-file/tests__unit__scripts__ci__test_print_junit_summary.py.patch
[63] A +84 -0  tests/unit/scripts/ci/test_run_mixed_environment_pytest.py -> diff/per-file/tests__unit__scripts__ci__test_run_mixed_environment_pytest.py.patch
[64] A +5433 -0  uv.lock -> diff/per-file/uv.lock.patch

SECTION: PER_FILE_PATCH_SELECTION_PATHS
(selection-ready `_git_data/...` paths for direct selection; no manual snapshot-dir reconstruction or `__` filename encoding required)
[01] A +2 -0  .github/ci-captains.yml -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/.github__ci-captains.yml.patch
[02] A +104 -0  .github/ci-phase-c-rollout.md -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/.github__ci-phase-c-rollout.md.patch
[03] M +9 -0  .github/CLAUDE.md -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/.github__CLAUDE.md.patch
[04] A +3 -0  .github/quarantined-tests.yml -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/.github__quarantined-tests.yml.patch
[05] M +1 -1  .github/workflows/base-package-functionality.yml -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/.github__workflows__base-package-functionality.yml.patch
[06] M +59 -57  .github/workflows/ci-fast.yml -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/.github__workflows__ci-fast.yml.patch
[07] A +194 -0  .github/workflows/ci-medium.yml -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/.github__workflows__ci-medium.yml.patch
[08] A +349 -0  .github/workflows/ci-slow-develop.yml -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/.github__workflows__ci-slow-develop.yml.patch
[09] M +0 -18  .github/workflows/ci-slow.yml -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/.github__workflows__ci-slow.yml.patch
[10] A +21 -0  .github/workflows/develop-health-gate.yml -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/.github__workflows__develop-health-gate.yml.patch
[11] M +42 -5  .github/workflows/integration-test-fast.yml -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/.github__workflows__integration-test-fast.yml.patch
[12] M +7 -0  .github/workflows/integration-test-slow.yml -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/.github__workflows__integration-test-slow.yml.patch
[13] M +1 -1  .github/workflows/linting.yml -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/.github__workflows__linting.yml.patch
[14] A +408 -0  .github/workflows/linux-fast-offload.yml -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/.github__workflows__linux-fast-offload.yml.patch
[15] A +22 -0  .github/workflows/modal-ci-image-warm.yml -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/.github__workflows__modal-ci-image-warm.yml.patch
[16] A +30 -0  .github/workflows/offload-cache-warm.yml -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/.github__workflows__offload-cache-warm.yml.patch
[17] M +23 -2  .github/workflows/release.yml -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/.github__workflows__release.yml.patch
[18] A +51 -0  .github/workflows/slow-ci-on-pr.yml -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/.github__workflows__slow-ci-on-pr.yml.patch
[19] M +1 -1  .github/workflows/unit-test.yml -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/.github__workflows__unit-test.yml.patch
[20] A +19 -0  .github/workflows/validate-quarantine.yml -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/.github__workflows__validate-quarantine.yml.patch
[21] A +20 -0  .github/workflows/validate-workspace-safety.yml -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/.github__workflows__validate-workspace-safety.yml.patch
[22] M +7 -0  .github/workflows/vscode-tutorial-pipelines-test.yml -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/.github__workflows__vscode-tutorial-pipelines-test.yml.patch
[23] A +763 -0  .github/workspace-safety-baseline.txt -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/.github__workspace-safety-baseline.txt.patch
[24] M +4 -2  .github/zizmor.yml -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/.github__zizmor.yml.patch
[25] M +4 -0  CONTRIBUTING.md -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/CONTRIBUTING.md.patch
[26] A +56 -0  Dockerfile.ci -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/Dockerfile.ci.patch
[27] A +35 -0  Dockerfile.ci.dockerignore -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/Dockerfile.ci.dockerignore.patch
[28] A +32 -0  offload-modal-server-mysql.toml -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/offload-modal-server-mysql.toml.patch
[29] A +32 -0  offload.toml -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/offload.toml.patch
[30] A +132 -0  scripts/audit_integration_workspace_safety.py -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/scripts__audit_integration_workspace_safety.py.patch
[31] A +103 -0  scripts/check_known_good.py -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/scripts__check_known_good.py.patch
[32] A +0 -0  scripts/ci/__init__.py -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/scripts__ci____init__.py.patch
[33] A +185 -0  scripts/ci/classify_offload_result.py -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/scripts__ci__classify_offload_result.py.patch
[34] A +229 -0  scripts/ci/compute_offload_cache_keys.py -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/scripts__ci__compute_offload_cache_keys.py.patch
[35] A +150 -0  scripts/ci/emit_timing_manifest.py -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/scripts__ci__emit_timing_manifest.py.patch
[36] A +69 -0  scripts/ci/export_offload_integration_requirements.py -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/scripts__ci__export_offload_integration_requirements.py.patch
[37] A +3 -0  scripts/ci/modal_sandbox_requirements.txt -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/scripts__ci__modal_sandbox_requirements.txt.patch
[38] A +70 -0  scripts/ci/normalize_offload_junit.py -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/scripts__ci__normalize_offload_junit.py.patch
[39] A +52 -0  scripts/ci/print_junit_failures.py -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/scripts__ci__print_junit_failures.py.patch
[40] A +100 -0  scripts/ci/print_junit_summary.py -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/scripts__ci__print_junit_summary.py.patch
[41] A +147 -0  scripts/ci/run_mixed_environment_pytest.py -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/scripts__ci__run_mixed_environment_pytest.py.patch
[42] A +56 -0  scripts/ci_matrix_hash.py -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/scripts__ci_matrix_hash.py.patch
[43] A +317 -0  scripts/ci_modal_mysql_sandbox.py -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/scripts__ci_modal_mysql_sandbox.py.patch
[44] A +216 -0  scripts/develop_health_gate.py -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/scripts__develop_health_gate.py.patch
[45] A +124 -0  scripts/publish_ci_qualification.py -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/scripts__publish_ci_qualification.py.patch
[46] M +15 -1  scripts/test-migrations.sh -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/scripts__test-migrations.sh.patch
[47] A +71 -0  scripts/validate_quarantine.py -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/scripts__validate_quarantine.py.patch
[48] M +11 -0  tests/harness/cfg/deployments.yaml -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/tests__harness__cfg__deployments.yaml.patch
[49] M +12 -0  tests/harness/cfg/environments.yaml -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/tests__harness__cfg__environments.yaml.patch
[50] M +1 -1  tests/harness/deployment/base.py -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/tests__harness__deployment__base.py.patch
[51] A +109 -0  tests/integration/conftest.py -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/tests__integration__conftest.py.patch
[52] M +6 -2  tests/integration/examples/utils.py -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/tests__integration__examples__utils.py.patch
[53] M +40 -39  tests/integration/functional/cli/test_model.py -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/tests__integration__functional__cli__test_model.py.patch
[54] A +0 -0  tests/unit/scripts/__init__.py -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/tests__unit__scripts____init__.py.patch
[55] A +0 -0  tests/unit/scripts/ci/__init__.py -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/tests__unit__scripts__ci____init__.py.patch
[56] A +158 -0  tests/unit/scripts/ci/test_classify_offload_result.py -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/tests__unit__scripts__ci__test_classify_offload_result.py.patch
[57] A +154 -0  tests/unit/scripts/ci/test_compute_offload_cache_keys.py -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/tests__unit__scripts__ci__test_compute_offload_cache_keys.py.patch
[58] A +37 -0  tests/unit/scripts/ci/test_emit_timing_manifest.py -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/tests__unit__scripts__ci__test_emit_timing_manifest.py.patch
[59] A +45 -0  tests/unit/scripts/ci/test_export_offload_integration_requirements.py -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/tests__unit__scripts__ci__test_export_offload_integration_requirements.py.patch
[60] A +45 -0  tests/unit/scripts/ci/test_normalize_offload_junit.py -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/tests__unit__scripts__ci__test_normalize_offload_junit.py.patch
[61] A +55 -0  tests/unit/scripts/ci/test_offload_config.py -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/tests__unit__scripts__ci__test_offload_config.py.patch
[62] A +44 -0  tests/unit/scripts/ci/test_print_junit_summary.py -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/tests__unit__scripts__ci__test_print_junit_summary.py.patch
[63] A +84 -0  tests/unit/scripts/ci/test_run_mixed_environment_pytest.py -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/tests__unit__scripts__ci__test_run_mixed_environment_pytest.py.patch
[64] A +5433 -0  uv.lock -> _git_data/repos/zenml-2aefb64b/2026-05-08/1045/diff/per-file/uv.lock.patch

SECTION: NOTES
NOTE_PATCH_OMITTED_COUNT: 0
NOTE_QUICK_MODE: false
```

File: /Users/safoine/zenml-io/zenml/tests/unit/scripts/ci/test_normalize_offload_junit.py
```py
"""Tests for offload JUnit normalization."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from scripts.ci.normalize_offload_junit import normalize_junit


def test_normalize_junit_rewrites_function_test_name(tmp_path: Path) -> None:
    """Pytest JUnit names are converted to collect node IDs."""
    junit = tmp_path / "junit.xml"
    junit.write_text(
        """
<testsuite>
  <testcase classname="tests.unit.foo.test_bar" name="test_baz" time="1" />
</testsuite>
"""
    )

    assert normalize_junit(junit) == 1

    testcase = next(ET.parse(junit).getroot().iter("testcase"))
    assert testcase.attrib["name"] == "tests/unit/foo/test_bar.py::test_baz"


def test_normalize_junit_rewrites_class_test_name(tmp_path: Path) -> None:
    """Class-based pytest names keep the class in the node ID."""
    junit = tmp_path / "junit.xml"
    junit.write_text(
        """
<testsuite>
  <testcase classname="tests.integration.foo.test_bar.TestThing" name="test_baz[x]" time="1" />
</testsuite>
"""
    )

    normalize_junit(junit)

    testcase = next(ET.parse(junit).getroot().iter("testcase"))
    assert (
        testcase.attrib["name"]
        == "tests/integration/foo/test_bar.py::TestThing::test_baz[x]"
    )

```

File: /Users/safoine/zenml-io/zenml/.github/workflows/modal-ci-image-warm.yml
```yml
---
name: Warm Modal CI image
on:
  schedule:
    - cron: 30 23 * * *
  workflow_dispatch:
permissions:
  contents: read
jobs:
  warm-modal-ci-image:
    if: vars.ZENML_CI_MODAL_DISABLED != 'true'
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
      - name: Install Modal SDK
        run: python -m pip install --upgrade 'modal>=1.0.0'
      - name: Build and warm Modal CI image
        env:
          MODAL_TOKEN_ID: ${{ secrets.MODAL_TOKEN_ID }}
          MODAL_TOKEN_SECRET: ${{ secrets.MODAL_TOKEN_SECRET }}
        run: python scripts/ci_modal_mysql_sandbox.py warm-image

```

File: /Users/safoine/zenml-io/zenml/Dockerfile.ci
```ci
ARG PYTHON_VERSION=3.13
ARG UV_VERSION=0.8.22

FROM python:${PYTHON_VERSION}-slim-bookworm AS builder
ARG UV_VERSION

RUN set -ex \
  && apt-get update \
  && apt-get install -y --no-install-recommends git graphviz build-essential libgomp1 \
  && apt-get clean -y \
  && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade wheel pip "uv==${UV_VERSION}"

WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY .ci/offload/integration-requirements.txt /tmp/integration-requirements.txt

RUN uv export --frozen --format requirements.txt --no-emit-project --no-hashes --no-header \
    --extra server \
    --extra templates \
    --extra terraform \
    --extra secrets-aws \
    --extra secrets-gcp \
    --extra secrets-azure \
    --extra secrets-hashicorp \
    --extra s3fs \
    --extra gcsfs \
    --extra adlfs \
    --extra dev \
    --extra connectors-aws \
    --extra connectors-gcp \
    --extra connectors-azure \
    --extra azureml \
    --extra sagemaker \
    --extra vertex \
    --output-file /tmp/zenml-requirements.txt \
  && uv pip install --system -r /tmp/zenml-requirements.txt \
  && uv pip install --system -r /tmp/integration-requirements.txt \
  && uv pip install --system 'setuptools<82' \
  && { uv pip uninstall --system multipart || true; } \
  && uv pip install --system --force-reinstall --no-deps "docstring_parser_fork" \
  && { pip cache purge 2>/dev/null || true; } \
  && rm -f /tmp/zenml-requirements.txt /tmp/integration-requirements.txt

FROM python:${PYTHON_VERSION}-slim-bookworm

RUN set -ex \
  && apt-get update \
  && apt-get install -y --no-install-recommends git graphviz libgomp1 \
  && apt-get clean -y \
  && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local /usr/local

WORKDIR /app

```

File: /Users/safoine/zenml-io/zenml/tests/unit/scripts/ci/test_export_offload_integration_requirements.py
```py
"""Tests for offload integration requirement export."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

from pytest import MonkeyPatch
from scripts.ci.export_offload_integration_requirements import (
    export_requirements,
)


class _FakeRegistry:
    integrations = {"aws": object, "tensorflow": object}

    def select_integration_requirements(
        self, integration_name: str
    ) -> list[str]:
        return [f"{integration_name}-requirement"]


def test_export_requirements_uses_registry_and_ignores_blocked_integrations(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """Generated requirements come from ZenML metadata, not a fixed file."""
    registry_module = ModuleType("zenml.integrations.registry")
    registry_module.integration_registry = _FakeRegistry()
    monkeypatch.setitem(sys.modules, "zenml", ModuleType("zenml"))
    monkeypatch.setitem(
        sys.modules, "zenml.integrations", ModuleType("zenml.integrations")
    )
    monkeypatch.setitem(
        sys.modules, "zenml.integrations.registry", registry_module
    )

    output_file = tmp_path / "integration-requirements.txt"
    export_requirements(output_file)

    requirements = output_file.read_text()
    assert "aws-requirement" in requirements
    assert "tensorflow-requirement" not in requirements
    assert "pyyaml>=6.0.1" in requirements

```

File: /Users/safoine/zenml-io/zenml/tests/harness/cfg/environments.yaml
```yaml
---
# Environments couple together a deployment with an optional set of
# requirements to be configured on the deployment. The deployment entry
# can be a reference to a global deployment entry by name or an inline
# deployment configuration. Same for the requirements: they can be
# specified either inline using the same format as the global requirements
# file or by referencing a global requirements entry by name.
#
# Two sets of requirements can be specified for each environment:
# - `requirements`: these stack requirements are provisioned and used as
#  options from which the tests can choose as they see fit. If the tests don't
#  specify any requirements that match these stack components, they will not
#  be included in the stacks automatically provisioned for tests by the
#  framework.
# - `mandatory_requirements`: these stack requirements are provisioned
#  and they are enforced on the tests. Stacks automatically provisioned for
#  tests by the framework are guaranteed to include stack components configured
#  as mandatory in the environment (one of each component type).
#
# Other fields:
# - `name`: the name of the environment. This is used to reference the
#    environment in the CLI and pytest runs.
# - `description`: a description of the environment.
# - disabled: A boolean flag that can be used to administratively disable an
#   environment. A disabled environment will not be checked for operational
#   readiness and will not be usable to run tests. This is useful to temporarily
#   disable an environment that is not operational without having to remove it
#   from the configuration.
# - capabilities: A list of custom capabilities that the environment supports or
#   does not support. This is compared against the capabilities required by the
#   tests to determine if the deployment is suitable to run the tests. A `true`
#   value indicates that the environment supports the capability, while a
#   `false` value indicates that it doesn't. Capabilities configured at the
#   environment level override those configured at the deployment level or
#   inherited from environment requirements.
#
environments:
  - name: default
    description: >-
      Default deployment with local orchestrator and all local
      components.
    deployment: default
    requirements:
      - data-validators
      - mlflow-local-tracker
      - mlflow-local-registry
      - mlflow-local-deployer
    capabilities:
      synchronized: true
  - name: default-docker-orchestrator
    description: >-
      Default deployment with docker orchestrator and all local
      components.
    deployment: default
    requirements:
      - data-validators
      - mlflow-local-tracker
      - mlflow-local-registry
      - mlflow-local-deployer
    mandatory_requirements: [docker-local]
  - name: default-airflow-orchestrator
    description: >-
      Default server deployment with airflow local orchestrator and all local
      components.
    deployment: default
    requirements:
      - data-validators
      - mlflow-local-tracker
      - mlflow-local-deployer
      - mlflow-local-registry
    mandatory_requirements:
      - airflow-local

    # IMPORTANT: don't use this with pytest auto-provisioning. Running forked
    # daemons in pytest leads to serious issues because the whole test process
    # is forked. As a workaround, the deployment can be started separately,
    # before pytest is invoked.
  - name: local-server
    description: >-
      Local server deployment with local orchestrator and all local
      components.
    deployment: local-server
    requirements:
      - data-validators
      - mlflow-local-tracker
      - mlflow-local-registry
      - mlflow-local-deployer
    capabilities:
      synchronized: true

    # IMPORTANT: don't use this with pytest auto-provisioning. Running forked
    # daemons in pytest leads to serious issues because the whole test process
    # is forked. As a workaround, the deployment can be started separately,
    # before pytest is invoked.
  - name: local-server-docker-orchestrator
    description: >-
      Local server deployment with docker orchestrator and all local
      components.
    deployment: local-server
    requirements:
      - data-validators
      - mlflow-local-tracker
      - mlflow-local-registry
      - mlflow-local-deployer
    mandatory_requirements:
      - docker-local

    # IMPORTANT: don't use this with pytest auto-provisioning. Running forked
    # daemons in pytest leads to serious issues because the whole test process
    # is forked. As a workaround, the deployment can be started separately,
    # before pytest is invoked.
  - name: local-server-airflow-orchestrator
    description: >-
      Local server deployment with local airflow orchestrator and all local
      components.
    deployment: local-server
    requirements:
      - data-validators
      - mlflow-local-tracker
      - mlflow-local-registry
      - mlflow-local-deployer
    mandatory_requirements: [airflow-local]
  - name: docker-server-mysql
    description: >-
      Server docker-compose deployment with local orchestrator and all local
      components, using a MySQL database.
    deployment: docker-server-mysql
    requirements:
      - data-validators
      - mlflow-local-tracker
      - mlflow-local-registry
      - mlflow-local-deployer
    capabilities:
      synchronized: true
  - name: remote-mysql-modal
    description: >-
      Modal-hosted ZenML server with local orchestrator and all local
      components, using a MySQL database.
    deployment: modal-mysql-server
    requirements:
      - data-validators
      - mlflow-local-tracker
      - mlflow-local-registry
      - mlflow-local-deployer
    capabilities:
      synchronized: true
  - name: docker-server-docker-orchestrator-mysql
    description: >-
      Server docker-compose deployment with docker orchestrator and all local
      components, using a MySQL database.
    deployment: docker-server-mysql
    requirements:
      - data-validators
      - mlflow-local-tracker
      - mlflow-local-registry
      - mlflow-local-deployer
    mandatory_requirements: [docker-local]
  - name: docker-server-airflow-orchestrator-mysql
    description: >-
      Server docker-compose deployment with local airflow orchestrator and all
      local components, using a MySQL database.
    deployment: docker-server-mysql
    requirements:
      - data-validators
      - mlflow-local-tracker
      - mlflow-local-registry
      - mlflow-local-deployer
    mandatory_requirements: [airflow-local]
  - name: docker-server-mariadb
    description: >-
      Server docker-compose deployment with local orchestrator and all local
      components, using a MariaDB database.
    deployment: docker-server-mariadb
    requirements:
      - data-validators
      - mlflow-local-tracker
      - mlflow-local-registry
      - mlflow-local-deployer
    capabilities:
      synchronized: true
  - name: docker-server-docker-orchestrator-mariadb
    description: >-
      Server docker-compose deployment with docker orchestrator and all local
      components, using a MariaDB database.
    deployment: docker-server-mariadb
    requirements:
      - data-validators
      - mlflow-local-tracker
      - mlflow-local-registry
      - mlflow-local-deployer
    mandatory_requirements: [docker-local]
  - name: docker-server-airflow-orchestrator-mariadb
    description: >-
      Server docker-compose deployment with local airflow orchestrator and all
      local components, using a MariaDB database.
    deployment: docker-server-mariadb
    requirements:
      - data-validators
      - mlflow-local-tracker
      - mlflow-local-registry
      - mlflow-local-deployer
    mandatory_requirements: [airflow-local]
  - name: github-actions-server-docker-orchestrator
    description: >-
      Server using GitHub Actions services with docker orchestrator and all
      local components.
    deployment: github-actions-server
    requirements:
      - data-validators
      - mlflow-local-tracker
      - mlflow-local-registry
      - mlflow-local-deployer
    mandatory_requirements: [docker-local]

```

File: /Users/safoine/zenml-io/zenml/.github/workflows/vscode-tutorial-pipelines-test.yml
```yml
---
# Regression testing workflow that runs all tutorial pipelines from the
# zenml-io/vscode-tutorial-extension repository to ensure ZenML core changes
# don't break the user-facing tutorial examples
name: VSCode Tutorial Pipelines Test
on:
  workflow_call:
    inputs:
      git-ref:
        description: Git branch or ref
        type: string
        required: false
        default: ''
  workflow_dispatch:
    inputs:
      python-version:
        description: Python version
        type: choice
        options: ['3.12']
        required: false
        default: '3.12'
      enable_tmate:
        description: Enable tmate session for debugging
        type: choice
        options: [no, on-failure, always, before-tests]
        required: false
        default: 'no'
jobs:
  test-tutorial-pipelines:
    name: test-tutorial-pipelines
    runs-on: ubuntu-latest
    env:
      ZENML_DEBUG: true
      ZENML_ANALYTICS_OPT_IN: false
      ZENML_LOGGING_VERBOSITY: INFO
      MLSTACKS_ANALYTICS_OPT_OUT: true
      AUTO_OPEN_DASHBOARD: false
      ZENML_ENABLE_RICH_TRACEBACK: false
      TOKENIZERS_PARALLELISM: false
      PYTHONIOENCODING: utf-8
      UV_HTTP_TIMEOUT: 600
    steps:
      - name: Checkout ZenML code
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
        with:
          ref: ${{ inputs.git-ref || github.event.pull_request.head.sha || github.sha }}
          fetch-depth: 0
      - name: Set up Python 3.12
        uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405  # v6.2.0
        with:
          python-version: '3.12'
      - name: Install uv
        run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          source $HOME/.cargo/env
          echo "$HOME/.cargo/bin" >> $GITHUB_PATH
      - name: Cache UV dependencies
        uses: actions/cache@27d5ce7f107fe9357f9df03efb73ab90386fccae  # v5.0.5
        with:
          path: ~/.cache/uv
          key: uv-tutorial-${{ runner.os }}-3.12-${{ github.run_id }}
          restore-keys: |
            uv-tutorial-${{ runner.os }}-3.12-
      - name: Setup tmate session before tests
        if: ${{ inputs.enable_tmate == 'before-tests' }}
        uses: mxschmitt/action-tmate@c0afd6f790e3a5564914980036ebf83216678101  # v3.23
      - name: Clone tutorial repository
        run: |
          # Clone with retry logic for network resilience
          for i in {1..3}; do
            if git clone --branch develop https://github.com/zenml-io/vscode-tutorial-extension.git tutorial-repo; then
              break
            elif [ $i -lt 3 ]; then
              echo "Clone attempt $i failed, retrying in 5 seconds..."
              sleep 5
            else
              echo "Failed to clone tutorial repository after 3 attempts"
              exit 1
            fi
          done
      - name: Create virtual environment
        run: |
          uv venv
      - name: Install ZenML from current branch
        run: |
          source .venv/bin/activate
          uv pip install "git+https://github.com/${{ github.repository }}@${{ github.sha }}[server,templates,dev]"
      - name: Install tutorial requirements
        run: |
          source .venv/bin/activate
          # Validate requirements.txt exists and is readable
          if [ ! -f "tutorial-repo/requirements.txt" ]; then
            echo "Error: requirements.txt not found in tutorial repository"
            exit 1
          fi
          uv pip install -r tutorial-repo/requirements.txt
      - name: Run tutorial pipelines test script
        run: |
          source .venv/bin/activate
          bash scripts/test-tutorial-pipelines.sh
      - name: Setup tmate session after tests
        if: ${{ inputs.enable_tmate == 'always' || (inputs.enable_tmate == 'on-failure' && failure()) }}
        uses: mxschmitt/action-tmate@c0afd6f790e3a5564914980036ebf83216678101  # v3.23

```

File: /Users/safoine/zenml-io/zenml/.github/workflows/offload-cache-warm.yml
```yml
---
name: Offload cache warm
on:
  workflow_dispatch:
  schedule:
    - cron: 0 2 * * 1
permissions:
  contents: read
concurrency:
  group: offload-cache-warm-${{ github.ref }}
  cancel-in-progress: true
jobs:
  warm-default-offload:
    if: vars.ZENML_CI_MODAL_DISABLED != 'true'
    uses: ./.github/workflows/linux-fast-offload.yml
    with:
      backend: modal
      python-version: '3.13'
      use-offload: true
      test_environment: default
    secrets: inherit
  warm-modal-mysql-offload:
    if: vars.ZENML_CI_MODAL_DISABLED != 'true'
    uses: ./.github/workflows/linux-fast-offload.yml
    with:
      backend: modal
      python-version: '3.13'
      use-offload: true
      test_environment: modal-server-mysql
    secrets: inherit

```

File: /Users/safoine/zenml-io/zenml/.github/workflows/unit-test.yml
```yml
---
name: Setup Python Environment, Lint and Unit Test
on:
  workflow_call:
    inputs:
      os:
        description: OS
        type: string
        required: true
      python-version:
        description: Python version
        type: string
        required: true
      enable_tmate:
        description: Enable tmate session for debugging
        type: string
        required: false
        default: never
      install_integrations:
        description: Install ZenML integrations
        type: string
        required: false
        default: 'yes'
      git-ref:
        description: Git branch or ref
        type: string
        required: false
        default: ''
      reruns:
        description: Pytest rerun count (0 disables)
        type: number
        required: false
        default: 3
  workflow_dispatch:
    inputs:
      os:
        description: OS
        type: choice
        options: [ubuntu-latest, macos-13, windows-latest]
        required: false
        default: ubuntu-latest
      python-version:
        description: Python version
        type: choice
        options: ['3.10', '3.11', '3.12', '3.13']
        required: false
        default: '3.11'
      enable_tmate:
        description: Enable tmate session for debugging
        type: choice
        options: [no, on-failure, always, before-tests]
        required: false
        default: 'no'
      git-ref:
        description: Git branch or ref
        type: string
        required: false
        default: ''
      reruns:
        description: Pytest rerun count (0 disables)
        type: number
        required: false
        default: 3
jobs:
  unit-test:
    name: unit-test
    runs-on: ${{ inputs.os }}
    env:
      ZENML_DEBUG: 1
      ZENML_ANALYTICS_OPT_IN: false
      PYTHONIOENCODING: utf-8
      UV_HTTP_TIMEOUT: 600
      OBJC_DISABLE_INITIALIZE_FORK_SAFETY: 'YES'
      PYTEST_RERUNS: ${{ inputs.reruns }}
    if: ${{ ! startsWith(github.event.head_commit.message, 'GitBook:') && ! (inputs.os == 'windows-latest' && inputs.python-version == '3.11') && ! (inputs.os == 'windows-latest' && inputs.python-version == '3.12') && ! (inputs.os == 'windows-latest' && inputs.python-version == '3.13') }}
    defaults:
      run:
        shell: bash
    steps:
      - name: Free disk space (Ubuntu)
        if: inputs.os == 'ubuntu-latest'
        run: |
          set -euxo pipefail
          echo "Before cleanup:"
          df -h
          sudo rm -rf /usr/share/dotnet || true
          sudo rm -rf /usr/local/lib/android || true
          sudo rm -rf /opt/ghc || true
          sudo rm -rf /opt/hostedtoolcache/CodeQL || true
          sudo docker image prune --all --force || true
          echo "After cleanup:"
          df -h
      - name: Set uv cache + temp dirs (/opt)
        if: inputs.os == 'ubuntu-latest'
        run: |
          sudo mkdir -p /opt/uv-cache /opt/tmp
          sudo chown -R "$(id -u)":"$(id -g)" /opt/uv-cache /opt/tmp
          echo "UV_CACHE_DIR=/opt/uv-cache" >> "$GITHUB_ENV"
          echo "TMPDIR=/opt/tmp" >> "$GITHUB_ENV"
          echo "TMP=/opt/tmp" >> "$GITHUB_ENV"
          echo "TEMP=/opt/tmp" >> "$GITHUB_ENV"
      - name: Checkout code
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
        with:
          repository: ${{ github.repository }}
          ref: ${{ inputs.git-ref || github.event.pull_request.head.sha || github.sha }}
          fetch-depth: 0  # Fetch all history for all branches and tags
      - name: Restore uv cache
        uses: actions/cache@27d5ce7f107fe9357f9df03efb73ab90386fccae  # v5.0.5
        with:
          path: ${{ inputs.os == 'ubuntu-latest' && '/opt/uv-cache' || '~/.cache/uv' }}
          key: |
            uv-${{ runner.os }}-${{ inputs.python-version }}-${{ hashFiles('src/zenml/integrations/*/__init__.py') }}
          restore-keys: |
            uv-${{ runner.os }}-${{ inputs.python-version }}-${{ hashFiles('src/zenml/integrations/*/__init__.py') }}
      - name: Install libomp
        if: ${{ inputs.os == 'macos-latest' || inputs.os == 'macos-13' }}
        run: brew install libomp
      - name: Setup environment
        uses: ./.github/actions/setup_environment
        with:
          cache_version: ${{ secrets.GH_ACTIONS_CACHE_KEY }}
          python-version: ${{ inputs.python-version }}
          os: ${{ inputs.os }}
          install_integrations: ${{ inputs.install_integrations }}
      - name: Setup tmate session before tests
        if: ${{ inputs.enable_tmate == 'before-tests' }}
        uses: mxschmitt/action-tmate@c0afd6f790e3a5564914980036ebf83216678101  # v3.23
      - name: Run unit tests
        run: |
          bash scripts/test-coverage-xml.sh unit
        env:
          ZENML_ANALYTICS_OPT_IN: false
          ZENML_DEBUG: true
      - name: Setup tmate session after tests
        if: ${{ inputs.enable_tmate == 'always' || (inputs.enable_tmate == 'on-failure' && failure()) }}
        uses: mxschmitt/action-tmate@c0afd6f790e3a5564914980036ebf83216678101  # v3.23
      - name: Verify Python Env unaffected
        run: |-
          zenml integration list
          uv pip list
          uv pip check || true

```

File: /Users/safoine/zenml-io/zenml/tests/unit/scripts/ci/test_emit_timing_manifest.py
```py
"""Tests for offload timing manifest generation."""

from __future__ import annotations

from pathlib import Path

from scripts.ci.emit_timing_manifest import build_manifest


def test_build_manifest_includes_duration_and_artifacts(
    tmp_path: Path,
) -> None:
    """Manifest captures timing and artifact presence."""
    (tmp_path / "junit.xml").write_text("<testsuite />")
    (tmp_path / "junit.seed.xml").write_text("<testsuite />")
    (tmp_path / "junit.stale.xml").write_text("<testsuite />")
    (tmp_path / "run-start.marker").write_text("start")

    manifest = build_manifest(
        lane="default",
        output_dir=tmp_path,
        started_at="10",
        completed_at="15",
        classification="success",
        phases=["setup=1,3,success", "test_execution=3,15,exit_0"],
    )

    assert manifest["duration_seconds"] == 5
    assert manifest["classification"] == "success"
    assert manifest["phases"]["setup"]["duration_seconds"] == 2
    assert manifest["phases"]["test_execution"]["status"] == "exit_0"
    assert manifest["artifacts"]["junit_xml"]["exists"] is True
    assert manifest["artifacts"]["junit_seed_xml"]["exists"] is True
    assert manifest["artifacts"]["junit_stale_xml"]["exists"] is True
    assert manifest["artifacts"]["run_start_marker"]["exists"] is True
    assert manifest["artifacts"]["offload_log"]["exists"] is False
    assert manifest["cache"]["uv_cache_hit"] == ""

```

File: /Users/safoine/zenml-io/zenml/.github/ci-captains.yml
```yml
---
rotation: []

```

File: /Users/safoine/zenml-io/zenml/tests/harness/deployment/base.py
```py
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
"""Base ZenML deployment."""

import logging
import os
import sys
from abc import ABC, abstractmethod
from contextlib import contextmanager
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generator,
    Optional,
    Tuple,
    Type,
    cast,
)

from docker.client import DockerClient

import zenml
from tests.harness.model import (
    DatabaseType,
    DeploymentConfig,
    DeploymentStoreConfig,
    ServerType,
)
from zenml.config.docker_settings import DockerBuildOptions
from zenml.constants import ENV_ZENML_CONFIG_PATH
from zenml.container_engines import DockerContainerEngine, get_container_engine
from zenml.enums import ContainerEngineType, StoreType
from zenml.image_builders import BuildContext

if TYPE_CHECKING:
    from zenml.client import Client

LOCAL_ZENML_SERVER_DEFAULT_PORT = 9000
MYSQL_DOCKER_IMAGE = "mysql:8.0"
MYSQL_DEFAULT_PASSWORD = "zenml"
MYSQL_DEFAULT_PORT = 3306
MARIADB_DOCKER_IMAGE = "mariadb:10.6"
MARIADB_ROOT_PASSWORD = "zenml"
MARIADB_DEFAULT_PORT = 3306
ZENML_SERVER_IMAGE_NAME = "localhost/zenml-server"
ZENML_IMAGE_NAME = (
    f"zenmldocker/zenml:{zenml.__version__}-"
    f"py{sys.version_info.major}.{sys.version_info.minor}"
)
DEFAULT_DEPLOYMENT_ROOT_DIR = "zenml-test"
ENV_DEPLOYMENT_ROOT_PATH = "ZENML_TEST_DEPLOYMENT_ROOT_PATH"
DEPLOYMENT_START_TIMEOUT = 60


class BaseTestDeployment(ABC):
    """Base class for ZenML test deployments."""

    DEPLOYMENTS: Dict[
        Tuple[ServerType, DatabaseType], Type["BaseTestDeployment"]
    ] = {}

    def __init__(self, config: DeploymentConfig) -> None:
        """Initializes the deployment.

        Args:
            config: The configuration for the deployment.
        """
        self.config = config
        self._container_engine: Optional[DockerContainerEngine] = None

    @classmethod
    def register_deployment_class(
        cls, server_type: ServerType, database_type: DatabaseType
    ) -> None:
        """Registers the deployment in the global registry.

        Args:
            server_type: The server deployment type.
            database_type: The database deployment type.

        Raises:
            ValueError: If a deployment class is already registered for the
                given server and database types.
        """
        if cls.get_deployment_class(server_type, database_type) is not None:
            raise ValueError(
                f"Deployment class for type '{server_type}' and setup "
                f"'{database_type}' already registered"
            )
        BaseTestDeployment.DEPLOYMENTS[(server_type, database_type)] = cls

    @classmethod
    def get_deployment_class(
        cls, server_type: ServerType, database_type: DatabaseType
    ) -> Optional[Type["BaseTestDeployment"]]:
        """Returns the deployment class for the given server and database types.

        Args:
            server_type: The server deployment type.
            database_type: The database deployment type.

        Returns:
            The deployment class registered for the given server and database
            types, if one exists.
        """
        return cls.DEPLOYMENTS.get((server_type, database_type))

    @classmethod
    def from_config(cls, config: DeploymentConfig) -> "BaseTestDeployment":
        """Creates a deployment from a deployment config.

        Args:
            config: The deployment config.

        Returns:
            The deployment instance.

        Raises:
            ValueError: If no deployment class is registered for the given
                deployment type and setup method.
        """
        deployment_class = cls.get_deployment_class(
            config.server, config.database
        )
        if deployment_class is None:
            raise ValueError(
                f"No deployment class registered for type '{config.server}' "
                f"and setup '{config.database}'"
            )
        return deployment_class(config)

    @property
    @abstractmethod
    def is_running(self) -> bool:
        """Returns whether the deployment is running.

        Returns:
            Whether the deployment is running.
        """

    @abstractmethod
    def up(self) -> None:
        """Starts up the deployment."""

    @abstractmethod
    def down(self) -> None:
        """Tears down the deployment."""

    @abstractmethod
    def get_store_config(self) -> Optional[DeploymentStoreConfig]:
        """Returns the client store configuration needed to connect to the deployment.

        Returns:
           The store configuration, if one is required to connect to the
           deployment.
        """

    def cleanup(self) -> None:
        """Tears down the deployment and cleans up all local files."""
        from tests.harness.utils import cleanup_folder

        self.down()

        runtime_path = self.get_runtime_path()
        if not runtime_path.exists():
            return

        cleanup_folder(str(runtime_path))

    @property
    def container_engine(self) -> DockerContainerEngine:
        """Returns the Docker container engine.

        Returns:
            The Docker container engine.
        """
        if self._container_engine is None:
            self._container_engine = cast(
                DockerContainerEngine,
                get_container_engine(ContainerEngineType.DOCKER),
            )
        return self._container_engine

    @property
    def docker_client(self) -> DockerClient:
        """Returns the docker client.

        Returns:
            The docker client
        """
        return self.container_engine.client

    def build_image(
        self,
        image_name: str,
        dockerfile: str,
        build_context_root: str,
        **custom_build_options: Any,
    ) -> None:
        """Builds a docker image.

        Args:
            image_name: The name to use for the built docker image.
            dockerfile: Path to a dockerfile.
            build_context_root: Path to a directory that will be sent to
                the Docker daemon as build context.
            **custom_build_options: Additional build options (for example
                ``platform``, ``buildargs`` / ``build_args``, ``target``).
        """
        dockerfile_contents = Path(dockerfile).read_text()
        logging.info("Using Dockerfile `%s`.", os.path.abspath(dockerfile))

        build_context = BuildContext(
            root=build_context_root,
        )
        build_context.add_file(dockerfile_contents, "Dockerfile")

        build_option_kwargs = {
            "rm": False,
            "pull": True,
            **custom_build_options,
        }
        docker_build_options = DockerBuildOptions(**build_option_kwargs)

        logging.info("Building Docker image `%s`.", image_name)
        logging.debug("Docker build options: %s", docker_build_options)

        logging.info("Building the image might take a while...")

        self.container_engine.build(
            image_name=image_name,
            build_context=build_context,
            docker_build_options=docker_build_options,
        )

        logging.info("Finished building Docker image `%s`.", image_name)

    def build_server_image(self) -> None:
        """Builds the server image locally."""
        logging.info(
            f"Building ZenML server image '{ZENML_SERVER_IMAGE_NAME}' locally"
        )

        context_root = Path(__file__).parents[3]
        docker_file_path = (
            context_root / "docker" / "zenml-server-dev.Dockerfile"
        )
        self.build_image(
            image_name=ZENML_SERVER_IMAGE_NAME,
            dockerfile=str(docker_file_path),
            build_context_root=str(context_root),
            platform="linux/amd64",
        )

    def build_base_image(self) -> None:
        """Builds the base image locally."""
        logging.info(f"Building ZenML base image '{ZENML_IMAGE_NAME}' locally")

        context_root = Path(__file__).parents[3]
        docker_file_path = context_root / "docker" / "zenml-dev.Dockerfile"
        self.build_image(
            image_name=ZENML_IMAGE_NAME,
            dockerfile=str(docker_file_path),
            build_context_root=str(context_root),
            platform="linux/amd64",
            # Use the same Python version as the current environment
            buildargs={
                "PYTHON_VERSION": f"{sys.version_info.major}.{sys.version_info.minor}"
            },
        )

    @classmethod
    def get_root_path(cls) -> Path:
        """Returns the root path used for test deployments.

        Returns:
            The root path for test deployments.
        """
        import click

        if ENV_DEPLOYMENT_ROOT_PATH in os.environ:
            return Path(os.environ[ENV_DEPLOYMENT_ROOT_PATH]).resolve()

        return Path(click.get_app_dir(DEFAULT_DEPLOYMENT_ROOT_DIR)).resolve()

    def get_runtime_path(self) -> Path:
        """Returns the runtime path used for the deployment.

        Returns:
            The runtime path for the deployment.
        """
        return self.get_root_path() / self.config.name

    def global_config_path(self) -> Path:
        """Returns the global config path used for the deployment.

        Returns:
            The global config path for the deployment.
        """
        return self.get_runtime_path() / ".zenconfig"

    @contextmanager
    def connect(
        self,
        global_config_path: Optional[Path] = None,
        custom_username: Optional[str] = None,
        custom_password: Optional[str] = None,
    ) -> Generator["Client", None, None]:
        """Context manager to create a client and connect it to the deployment.

        Call this method to configure zenml to connect to this deployment,
        run some code in the context of this configuration and then
        switch back to the previous configuration.

        Args:
            global_config_path: Custom global config path. If not provided,
                the global config path where the deployment is provisioned
                is used.
            custom_username: Custom username to use for the connection.
            custom_password: Custom password to use for the connection.

        Yields:
            A ZenML Client configured to connect to this deployment.

        Raises:
            RuntimeError: If the deployment is disabled.
        """
        from zenml.client import Client
        from zenml.config.global_config import GlobalConfiguration
        from zenml.config.store_config import StoreConfiguration
        from zenml.login.credentials_store import CredentialsStore
        from zenml.zen_stores.base_zen_store import BaseZenStore

        if self.config.disabled:
            raise RuntimeError(
                "Cannot connect to a disabled deployment. "
                "Please enable the deployment in the configuration first."
            )

        # set the ZENML_CONFIG_PATH environment variable to ensure that the
        # deployment uses a config isolated from the main config
        config_path = global_config_path or self.global_config_path()
        if not config_path.exists():
            config_path.mkdir(parents=True)

        # save the current global configuration and client singleton instances
        # to restore them later, then reset them
        original_config = GlobalConfiguration.get_instance()
        original_client = Client.get_instance()
        orig_config_path = os.getenv(ENV_ZENML_CONFIG_PATH)
        original_credentials = CredentialsStore.get_instance()

        CredentialsStore.reset_instance()
        GlobalConfiguration._reset_instance()
        Client._reset_instance()

        os.environ[ENV_ZENML_CONFIG_PATH] = str(config_path)
        os.environ["ZENML_ANALYTICS_OPT_IN"] = "false"
        os.environ["ZENML_ENABLE_REPO_INIT_WARNINGS"] = "false"

        # initialize the global config and client at the new path
        gc = GlobalConfiguration()
        gc.analytics_opt_in = False

        store_config = self.get_store_config()
        if store_config is not None:
            store_type = BaseZenStore.get_store_type(store_config.url)
            store_config_dict = store_config.dict()
            if store_type == StoreType.REST:
                if custom_username is not None:
                    store_config_dict["username"] = custom_username
                if custom_password is not None:
                    store_config_dict["password"] = custom_password
            gc.store = StoreConfiguration(
                type=store_type,
                **store_config_dict,
            )

        client = Client()

        yield client

        # restore the global configuration path
        if orig_config_path:
            os.environ[ENV_ZENML_CONFIG_PATH] = orig_config_path
        else:
            del os.environ[ENV_ZENML_CONFIG_PATH]

        # restore the global configuration, the client and the credentials store
        GlobalConfiguration._reset_instance(original_config)
        Client._reset_instance(original_client)
        CredentialsStore.reset_instance(original_credentials)

```

File: /Users/safoine/zenml-io/zenml/scripts/ci/__init__.py
```py

```

File: /Users/safoine/zenml-io/zenml/tests/unit/scripts/ci/test_compute_offload_cache_keys.py
```py
"""Tests for offload cache key computation."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from scripts.ci.compute_offload_cache_keys import compute_offload_cache_keys

REQUIRED_FILES = [
    "Dockerfile.ci",
    "Dockerfile.ci.dockerignore",
    "pyproject.toml",
    "uv.lock",
    "scripts/install-zenml-dev.sh",
    "scripts/ci/export_offload_integration_requirements.py",
    "scripts/ci/modal_sandbox_requirements.txt",
    "src/zenml/cli/integration.py",
    "src/zenml/integrations/integration.py",
    "src/zenml/integrations/registry.py",
    "src/zenml/integrations/sklearn/__init__.py",
    "offload.toml",
    "offload-modal-server-mysql.toml",
]


def _copy_key_inputs(tmp_path: Path) -> Path:
    for file_name in REQUIRED_FILES:
        source = Path(file_name)
        destination = tmp_path / file_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    return tmp_path


def _keys(root: Path, lane: str = "default"):
    return compute_offload_cache_keys(
        lane=lane,
        runner_os="Linux",
        python_version="3.13",
        run_id="123",
        run_attempt="1",
        root=root,
    )


def test_image_fingerprint_changes_when_dockerfile_changes(
    tmp_path: Path,
) -> None:
    """Docker image build inputs invalidate the image cache."""
    root = _copy_key_inputs(tmp_path)
    before = _keys(root).image_key

    (root / "Dockerfile.ci").write_text("FROM python:3.13\n")

    assert _keys(root).image_key != before


def test_image_fingerprint_changes_when_prepare_command_changes(
    tmp_path: Path,
) -> None:
    """Prepare command changes affect Modal image creation."""
    root = _copy_key_inputs(tmp_path)
    before = _keys(root).image_key

    config = root / "offload.toml"
    config.write_text(
        config.read_text().replace("--cached", "--cached --force-build")
    )

    assert _keys(root).image_key != before


def test_image_fingerprint_ignores_create_command_resources(
    tmp_path: Path,
) -> None:
    """Sandbox runtime resources do not invalidate image cache."""
    root = _copy_key_inputs(tmp_path)
    before = _keys(root).image_key

    config = root / "offload.toml"
    config.write_text(config.read_text().replace("--cpu 4", "--cpu 8"))

    assert _keys(root).image_key == before


def test_image_fingerprint_ignores_max_parallel(tmp_path: Path) -> None:
    """Scheduling settings do not invalidate image cache."""
    root = _copy_key_inputs(tmp_path)
    before = _keys(root).image_key

    config = root / "offload.toml"
    config.write_text(
        config.read_text().replace("max_parallel = 20", "max_parallel = 12")
    )

    assert _keys(root).image_key == before


def test_junit_fingerprint_changes_when_filters_change(
    tmp_path: Path,
) -> None:
    """Duration caches are tied to the selected test set."""
    root = _copy_key_inputs(tmp_path)
    before = _keys(root).junit_restore_prefix

    config = root / "offload.toml"
    config.write_text(
        config.read_text().replace("tests/unit", "tests/unit tests/core")
    )

    assert _keys(root).junit_restore_prefix != before


def test_junit_save_key_includes_run_id_and_attempt(tmp_path: Path) -> None:
    """Reruns should not collide with previous duration cache saves."""
    root = _copy_key_inputs(tmp_path)

    first = compute_offload_cache_keys(
        lane="default",
        runner_os="Linux",
        python_version="3.13",
        run_id="123",
        run_attempt="1",
        root=root,
    )
    second = compute_offload_cache_keys(
        lane="default",
        runner_os="Linux",
        python_version="3.13",
        run_id="123",
        run_attempt="2",
        root=root,
    )

    assert first.junit_save_key.endswith("-123-1")
    assert second.junit_save_key.endswith("-123-2")
    assert first.junit_save_key != second.junit_save_key


def test_unsupported_lane_raises_clear_error(tmp_path: Path) -> None:
    """Unknown lanes should fail before producing misleading cache keys."""
    root = _copy_key_inputs(tmp_path)

    with pytest.raises(ValueError, match="Unsupported offload lane"):
        compute_offload_cache_keys(
            lane="postgres",
            runner_os="Linux",
            python_version="3.13",
            run_id="123",
            run_attempt="1",
            root=root,
        )

```

File: /Users/safoine/zenml-io/zenml/.github/workflows/ci-medium.yml
```yml
---
name: ci-medium
on:
  workflow_dispatch:
  merge_group:
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
jobs:
  modal-enabled:
    runs-on: ubuntu-latest
    steps:
      - name: Verify Modal CI is enabled
        run: |
          if [ "${ZENML_CI_MODAL_DISABLED}" = "true" ]; then
            echo "Modal CI is disabled. Medium CI must not silently degrade."
            exit 1
          fi
        env:
          ZENML_CI_MODAL_DISABLED: ${{ vars.ZENML_CI_MODAL_DISABLED }}
  sqlite-db-migration-testing-random:
    runs-on: ubuntu-latest
    env:
      ZENML_ANALYTICS_OPT_IN: false
      ZENML_DEBUG: true
      RANDOM_MIGRATION_COUNT: 5
      RANDOM_MIGRATION_SEED: ${{ github.run_id }}
    steps:
      - name: Checkout code
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
        with:
          fetch-depth: 0
      - name: Set up Python 3.12
        uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405  # v6.2.0
        with:
          python-version: '3.12'
      - name: Test migrations across versions
        run: bash scripts/test-migrations.sh sqlite random
  mysql-db-migration-testing-random:
    needs: modal-enabled
    runs-on: ubuntu-latest
    env:
      ZENML_ANALYTICS_OPT_IN: false
      ZENML_DEBUG: true
      RANDOM_MIGRATION_COUNT: 5
      RANDOM_MIGRATION_SEED: ${{ github.run_id }}
    steps:
      - name: Checkout code
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
        with:
          fetch-depth: 0
      - name: Set up Python 3.12
        uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405  # v6.2.0
        with:
          python-version: '3.12'
      - name: Login to Docker Hub
        uses: docker/login-action@4907a6ddec9925e35a0a9e82d7399ccc52663121  # v4.1.0
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}
      - name: Test migrations across versions
        run: bash scripts/test-migrations.sh mysql random
  mariadb-db-migration-testing-random:
    needs: modal-enabled
    runs-on: ubuntu-latest
    env:
      ZENML_ANALYTICS_OPT_IN: false
      ZENML_DEBUG: true
      RANDOM_MIGRATION_COUNT: 5
      RANDOM_MIGRATION_SEED: ${{ github.run_id }}
    steps:
      - name: Checkout code
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
        with:
          fetch-depth: 0
      - name: Set up Python 3.12
        uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405  # v6.2.0
        with:
          python-version: '3.12'
      - name: Login to Docker Hub
        uses: docker/login-action@4907a6ddec9925e35a0a9e82d7399ccc52663121  # v4.1.0
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}
      - name: Test migrations across versions
        run: bash scripts/test-migrations.sh mariadb random
  linting:
    needs: modal-enabled
    strategy:
      matrix:
        os: [ubuntu-latest]
        python-version: ['3.12']
      fail-fast: false
    uses: ./.github/workflows/linting.yml
    with:
      python-version: ${{ matrix.python-version }}
      os: ${{ matrix.os }}
    secrets: inherit
  unit-test:
    needs: [modal-enabled, linting]
    strategy:
      matrix:
        os: [ubuntu-latest]
        python-version: ['3.12']
      fail-fast: false
    uses: ./.github/workflows/unit-test.yml
    with:
      python-version: ${{ matrix.python-version }}
      os: ${{ matrix.os }}
    secrets: inherit
  start-modal-mysql-sandbox:
    needs: modal-enabled
    runs-on: ubuntu-latest
    timeout-minutes: 15
    outputs:
      server-url: ${{ steps.start.outputs.server_url }}
      server-username: ${{ steps.start.outputs.server_username }}
      sandbox-id: ${{ steps.start.outputs.sandbox_id }}
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
      - name: Install Modal SDK
        run: python -m pip install --upgrade 'modal>=1.0.0'
      - id: start
        name: Start Modal MySQL sandbox
        env:
          ZENML_CI_MODAL_DISABLED: ${{ vars.ZENML_CI_MODAL_DISABLED }}
          MODAL_TOKEN_ID: ${{ secrets.MODAL_TOKEN_ID }}
          MODAL_TOKEN_SECRET: ${{ secrets.MODAL_TOKEN_SECRET }}
          ZENML_CI_CHECKOUT_REF: ${{ github.sha }}
        run: python scripts/ci_modal_mysql_sandbox.py start
  remote-mysql-modal-integration-test:
    needs: [modal-enabled, linting, start-modal-mysql-sandbox]
    strategy:
      matrix:
        os: [ubuntu-latest]
        python-version: ['3.12']
        test_environment: [remote-mysql-modal]
      fail-fast: false
    uses: ./.github/workflows/integration-test-fast.yml
    with:
      os: ${{ matrix.os }}
      python-version: ${{ matrix.python-version }}
      test_environment: ${{ matrix.test_environment }}
      ci_tier: medium
      modal_ci_server_url: ${{ needs.start-modal-mysql-sandbox.outputs.server-url }}
      modal_ci_server_username: ${{ needs.start-modal-mysql-sandbox.outputs.server-username }}
    secrets: inherit
  stop-modal-mysql-sandbox:
    needs: [start-modal-mysql-sandbox, remote-mysql-modal-integration-test]
    if: always() && needs.start-modal-mysql-sandbox.result == 'success'
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
      - name: Install Modal SDK
        run: python -m pip install --upgrade 'modal>=1.0.0'
      - name: Stop Modal MySQL sandbox
        env:
          MODAL_TOKEN_ID: ${{ secrets.MODAL_TOKEN_ID }}
          MODAL_TOKEN_SECRET: ${{ secrets.MODAL_TOKEN_SECRET }}
          SANDBOX_ID: ${{ needs.start-modal-mysql-sandbox.outputs.sandbox-id }}
        run: python scripts/ci_modal_mysql_sandbox.py stop --sandbox-id "$SANDBOX_ID"
  ci-medium-required:
    runs-on: ubuntu-latest
    needs:
      - sqlite-db-migration-testing-random
      - mysql-db-migration-testing-random
      - mariadb-db-migration-testing-random
      - linting
      - unit-test
      - start-modal-mysql-sandbox
      - remote-mysql-modal-integration-test
      - stop-modal-mysql-sandbox
    if: always()
    steps:
      - name: Verify required medium CI jobs
        env:
          NEEDS_CONTEXT: ${{ toJSON(needs) }}
        run: |-
          python - <<'PY'
          import json
          import os
          import sys
          failed = []
          for name, data in json.loads(os.environ["NEEDS_CONTEXT"]).items():
              result = data["result"]
              if result not in {"success", "skipped"}:
                  failed.append(f"{name}: {result}")
          if failed:
              print("Medium CI dependencies failed:")
              print("\n".join(failed))
              sys.exit(1)
          print("All medium CI dependencies passed or were skipped by design.")
          PY

```

File: /Users/safoine/zenml-io/zenml/scripts/ci/normalize_offload_junit.py
```py
"""Normalize pytest JUnit testcase names for offload duration lookup."""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def _node_id_from_pytest_junit(classname: str, name: str) -> str | None:
    parts = classname.split(".")
    module_end = next(
        (
            index
            for index, part in enumerate(parts)
            if part.startswith("test_")
        ),
        None,
    )
    if module_end is None:
        return None

    module_parts = parts[: module_end + 1]
    class_parts = parts[module_end + 1 :]
    path = "/".join(module_parts) + ".py"
    return "::".join([path, *class_parts, name])


def normalize_junit(path: Path) -> int:
    """Rewrite testcase names to pytest node IDs and return changed count."""
    tree = ET.parse(path)
    root = tree.getroot()
    changed = 0

    for testcase in root.iter("testcase"):
        classname = testcase.attrib.get("classname")
        name = testcase.attrib.get("name")
        if not classname or not name:
            continue
        node_id = _node_id_from_pytest_junit(classname, name)
        if node_id is None or node_id == name:
            continue
        testcase.set("name", node_id)
        changed += 1

    if changed:
        tree.write(path, encoding="utf-8", xml_declaration=True)
    return changed


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI."""
    args = _build_parser().parse_args(argv)
    if not args.path.exists():
        print(f"JUnit file does not exist: {args.path}")
        return 0
    changed = normalize_junit(args.path)
    print(f"Normalized {changed} JUnit testcase names in {args.path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

```

File: /Users/safoine/zenml-io/zenml/.github/ci-phase-c-rollout.md
```md
# Phase C rollout checklist

This checklist keeps the merge-queue cutover separate from the CI code review.
Do not enable merge queue on `develop` until the validation PR is green and the
team has reviewed the rollout plan.

## Validation PR

1. Push the CI changes to a normal branch and open a PR into `develop`.
2. Confirm regular PR checks pass, especially `ci-fast-required`.
3. Manually run the new workflows from the PR branch:

   ```bash
   gh workflow run ci-medium.yml --ref <branch-name>
   gh workflow run develop-health-gate.yml --ref <branch-name>
   ```

4. Run the Modal lane locally against the same pushed branch if needed:

   ```bash
   export GITHUB_REPOSITORY=zenml-io/zenml
   export ZENML_CI_CHECKOUT_REF=<branch-name>
   export GITHUB_SHA=$(git rev-parse HEAD)

   tmp=$(mktemp)
   GITHUB_OUTPUT=$tmp uv run scripts/ci_modal_mysql_sandbox.py start

   server_url=$(grep '^server_url=' "$tmp" | cut -d= -f2-)
   server_username=$(grep '^server_username=' "$tmp" | cut -d= -f2-)
   sandbox_id=$(grep '^sandbox_id=' "$tmp" | cut -d= -f2-)

   export MODAL_CI_SERVER_URL="$server_url"
   export MODAL_CI_SERVER_USERNAME="$server_username"
   export MODAL_CI_SERVER_PASSWORD=$(uv run python - <<'PY'
   from scripts.ci_modal_mysql_sandbox import derive_server_password
   print(derive_server_password())
   PY
   )
   export ZENML_CI_TIER=medium

   uv run pytest tests/integration/functional/test_client.py \
     --environment remote-mysql-modal \
     --no-provision \
     -q

   uv run scripts/ci_modal_mysql_sandbox.py stop --sandbox-id "$sandbox_id"
   ```

5. Share these results in the PR description:
   - `ci-fast-required` result
   - manual `ci-medium.yml` run link
   - manual `develop-health-gate.yml` run link
   - local Modal smoke-test result

## Pre-cutover validation after merge

After the validation PR merges to `develop`, but before branch protection is
changed:

1. Run slow qualification on `develop`:

   ```bash
   gh workflow run ci-slow-develop.yml --ref develop -f git-ref=develop
   ```

2. Wait for the qualification Check Run to be published on the `develop` SHA.
3. Run the health gate from `develop`:

   ```bash
   gh workflow run develop-health-gate.yml --ref develop
   ```

4. Run medium CI from `develop`:

   ```bash
   gh workflow run ci-medium.yml --ref develop
   ```

## Admin cutover request

Only after the checks above are green, ask an admin to update `develop` branch
protection:

- Enable GitHub merge queue.
- Start with `max_group_size = 1` and `build_concurrency = 1`.
- Require exactly these aggregate checks:
  - `ci-fast-required`
  - `ci-medium-required`
  - `develop-health-gate`
- Do not require individual matrix jobs.
- Do not require slow CI on PRs.

## Rollback

If the queue blocks normal development:

1. Disable merge queue on `develop` branch protection.
2. Set the Modal kill switch if the issue is Modal-related:

   ```bash
   gh variable set ZENML_CI_MODAL_DISABLED --body true
   ```

3. Open a follow-up issue with failing queue run links and the rollback time.

```

File: /Users/safoine/zenml-io/zenml/.github/workflows/linting.yml
```yml
---
name: Linting
on:
  workflow_call:
    inputs:
      os:
        description: OS
        type: string
        required: true
      python-version:
        description: Python version
        type: string
        required: true
      enable_tmate:
        description: Enable tmate session for debugging
        type: string
        required: false
        default: never
      install_integrations:
        description: Install ZenML integrations
        type: string
        required: false
        default: 'yes'
      git-ref:
        description: Git branch or ref
        type: string
        required: false
        default: ''
  workflow_dispatch:
    inputs:
      os:
        description: OS
        type: choice
        options: [ubuntu-latest, macos-13, windows-latest]
        required: false
        default: ubuntu-latest
      python-version:
        description: Python version
        type: choice
        options: ['3.10', '3.11', '3.12', '3.13']
        required: false
        default: '3.11'
      enable_tmate:
        description: Enable tmate session for debugging
        type: choice
        options: [no, on-failure, always, before-tests]
        required: false
        default: 'no'
      git-ref:
        description: Git branch or ref
        type: string
        required: false
        default: ''
jobs:
  linting:
    name: linting
    runs-on: ${{ inputs.os }}
    env:
      ZENML_DEBUG: 1
      ZENML_ANALYTICS_OPT_IN: false
      PYTHONIOENCODING: utf-8
      UV_HTTP_TIMEOUT: 600
      OBJC_DISABLE_INITIALIZE_FORK_SAFETY: 'YES'
    if: ${{ ! startsWith(github.event.head_commit.message, 'GitBook:') && ! (inputs.os == 'windows-latest' && inputs.python-version == '3.11') && ! (inputs.os == 'windows-latest' && inputs.python-version == '3.12') }}
    defaults:
      run:
        shell: bash
    steps:
      - name: Free disk space (Ubuntu)
        if: inputs.os == 'ubuntu-latest'
        run: |
          set -euxo pipefail
          echo "Before cleanup:"
          df -h
          sudo rm -rf /usr/share/dotnet || true
          sudo rm -rf /usr/local/lib/android || true
          sudo rm -rf /opt/ghc || true
          sudo rm -rf /opt/hostedtoolcache/CodeQL || true
          sudo docker image prune --all --force || true
          echo "After cleanup:"
          df -h
      - name: Set uv cache + temp dirs (/opt)
        if: inputs.os == 'ubuntu-latest'
        run: |
          sudo mkdir -p /opt/uv-cache /opt/tmp
          sudo chown -R "$(id -u)":"$(id -g)" /opt/uv-cache /opt/tmp
          echo "UV_CACHE_DIR=/opt/uv-cache" >> "$GITHUB_ENV"
          echo "TMPDIR=/opt/tmp" >> "$GITHUB_ENV"
          echo "TMP=/opt/tmp" >> "$GITHUB_ENV"
          echo "TEMP=/opt/tmp" >> "$GITHUB_ENV"
      - name: Checkout code
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
        with:
          repository: ${{ github.repository }}
          ref: ${{ inputs.git-ref || github.event.pull_request.head.sha || github.sha }}
          fetch-depth: 0  # Fetch all history for all branches and tags
      - name: Restore uv cache
        uses: actions/cache@27d5ce7f107fe9357f9df03efb73ab90386fccae  # v5.0.5
        with:
          path: ${{ inputs.os == 'ubuntu-latest' && '/opt/uv-cache' || '~/.cache/uv' }}
          key: |
            uv-${{ runner.os }}-${{ inputs.python-version }}-${{ hashFiles('src/zenml/integrations/*/__init__.py') }}
          restore-keys: |
            uv-${{ runner.os }}-${{ inputs.python-version }}-${{ hashFiles('src/zenml/integrations/*/__init__.py') }}
      - name: Install libomp
        if: ${{ inputs.os == 'macos-latest' || inputs.os == 'macos-13' }}
        run: brew install libomp
      - name: Setup environment
        uses: ./.github/actions/setup_environment
        with:
          cache_version: ${{ secrets.GH_ACTIONS_CACHE_KEY }}
          python-version: ${{ inputs.python-version }}
          os: ${{ inputs.os }}
          install_integrations: ${{ inputs.install_integrations }}
      - name: Setup tmate session before tests
        if: ${{ inputs.enable_tmate == 'before-tests' }}
        uses: mxschmitt/action-tmate@c0afd6f790e3a5564914980036ebf83216678101  # v3.23
      - name: Lint check
        env:
          OS: ${{ inputs.os }}
        run: |
          bash scripts/lint.sh
      - name: Setup tmate session after tests
        if: ${{ inputs.enable_tmate == 'always' || (inputs.enable_tmate == 'on-failure' && failure()) }}
        uses: mxschmitt/action-tmate@c0afd6f790e3a5564914980036ebf83216678101  # v3.23
      - name: Verify Python Env unaffected
        run: |-
          zenml integration list
          uv pip list
          uv pip check || true

```

File: /Users/safoine/zenml-io/zenml/tests/unit/scripts/ci/__init__.py
```py

```

File: /Users/safoine/zenml-io/zenml/tests/unit/scripts/ci/test_classify_offload_result.py
```py
"""Tests for offload result classification."""

from __future__ import annotations

import os
from pathlib import Path

from scripts.ci.classify_offload_result import classify_offload_result

PASSING_JUNIT = '<testsuite tests="2" failures="0" errors="0" skipped="0" />'
FAILING_JUNIT = """
<testsuite tests="1" failures="1" errors="0">
  <testcase classname="tests.test_example" name="test_failure">
    <failure message="boom" />
  </testcase>
</testsuite>
"""


def test_classifies_success_when_junit_passes(tmp_path: Path) -> None:
    """Passing JUnit reports produce a success classification."""
    junit = tmp_path / "junit.xml"
    junit.write_text(PASSING_JUNIT)

    result = classify_offload_result(exit_code=0, junit_path=junit)

    assert result.conclusion == "success"
    assert result.offload_infra_failed is False
    assert result.tests_failed is False
    assert result.junit_current is True
    assert result.junit_cacheable is True


def test_classifies_junit_failures_as_test_failures(tmp_path: Path) -> None:
    """Failing JUnit reports are treated as test failures."""
    junit = tmp_path / "junit.xml"
    junit.write_text(FAILING_JUNIT)

    result = classify_offload_result(exit_code=1, junit_path=junit)

    assert result.conclusion == "test_failure"
    assert result.offload_infra_failed is False
    assert result.tests_failed is True
    assert result.junit_current is True
    assert result.junit_cacheable is True


def test_exit_code_two_with_passing_junit_is_success(tmp_path: Path) -> None:
    """Offload exit code 2 means flakes passed on retry."""
    junit = tmp_path / "junit.xml"
    junit.write_text(PASSING_JUNIT)

    result = classify_offload_result(exit_code=2, junit_path=junit)

    assert result.conclusion == "success"
    assert result.offload_infra_failed is False
    assert result.tests_failed is False
    assert result.junit_current is True
    assert result.junit_cacheable is True


def test_missing_junit_is_infrastructure_failure(tmp_path: Path) -> None:
    """Missing JUnit output means the offload backend failed early."""
    log = tmp_path / "offload.log"
    log.write_text("Modal sandbox timeout")

    result = classify_offload_result(
        exit_code=1,
        junit_path=tmp_path / "missing.xml",
        log_path=log,
    )

    assert result.conclusion == "infra_failure"
    assert result.offload_infra_failed is True
    assert result.tests_failed is False
    assert result.junit_current is False
    assert result.junit_cacheable is False


def test_setup_failure_is_infrastructure_failure(tmp_path: Path) -> None:
    """Driver setup failures trigger fallback instead of test failure."""
    junit = tmp_path / "junit.xml"
    junit.write_text(PASSING_JUNIT)

    result = classify_offload_result(
        exit_code=1,
        junit_path=junit,
        setup_failed=True,
    )

    assert result.conclusion == "infra_failure"
    assert result.offload_infra_failed is True
    assert result.tests_failed is False
    assert result.junit_current is False
    assert result.junit_cacheable is False


def test_stale_restored_junit_with_nonzero_exit_is_infra_failure(
    tmp_path: Path,
) -> None:
    """Restored duration seeds are not current test results."""
    junit = tmp_path / "junit.xml"
    junit.write_text(PASSING_JUNIT)
    marker_ns = junit.stat().st_mtime_ns

    result = classify_offload_result(
        exit_code=1,
        junit_path=junit,
        junit_min_mtime_ns=marker_ns,
    )

    assert result.conclusion == "infra_failure"
    assert result.junit_current is False
    assert result.junit_cacheable is False


def test_stale_restored_junit_with_zero_exit_is_infra_failure(
    tmp_path: Path,
) -> None:
    """A successful exit still needs fresh JUnit output."""
    junit = tmp_path / "junit.xml"
    junit.write_text(PASSING_JUNIT)
    marker_ns = junit.stat().st_mtime_ns

    result = classify_offload_result(
        exit_code=0,
        junit_path=junit,
        junit_min_mtime_ns=marker_ns,
    )

    assert result.conclusion == "infra_failure"
    assert result.junit_current is False
    assert result.junit_cacheable is False


def test_current_invalid_junit_is_not_cacheable(tmp_path: Path) -> None:
    """Invalid current JUnit is an infrastructure failure."""
    marker = tmp_path / "marker"
    marker.write_text("start")
    junit = tmp_path / "junit.xml"
    junit.write_text("<testsuite")
    os.utime(
        junit,
        ns=(
            marker.stat().st_mtime_ns + 1_000_000,
            marker.stat().st_mtime_ns + 1_000_000,
        ),
    )

    result = classify_offload_result(
        exit_code=1,
        junit_path=junit,
        junit_min_mtime_ns=marker.stat().st_mtime_ns,
    )

    assert result.conclusion == "infra_failure"
    assert result.junit_current is True
    assert result.junit_cacheable is False

```

File: /Users/safoine/zenml-io/zenml/.github/workflows/ci-slow.yml
```yml
---
name: ci-slow
on:
  workflow_dispatch:
  workflow_call:
concurrency:
  # New commit on branch cancels running workflows of the same branch
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
jobs:
  run-slow-ci-label-is-set:
    runs-on: ubuntu-latest
    if: github.event.pull_request.draft == false
    steps:
      # using this instead of contains(github.event.pull_request.labels.*.name, 'run-slow-ci')
      # to make it dynamic, otherwise github context is fixed at the moment of trigger event.
      # With dynamic approach dev can set label and rerun this flow to make it running.
      - name: Get PR labels
        id: pr-labels
        uses: actions/github-script@ed597411d8f924073f98dfc5c65a23a2325f34cd  # v8.0.0
        with:
          script: |
            const prNumber = ${{ github.event.pull_request.number }};
            const { data: labels } = await github.rest.issues.listLabelsOnIssue({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: prNumber,
            });
            const labelNames = labels.map(label => label.name);
            core.setOutput('all-labels', labelNames.join(','));
      - name: Slow CI label not set
        if: ${{ !contains(steps.pr-labels.outputs.all-labels, 'run-slow-ci') }}
        run: |
          echo "Please add the 'run-slow-ci' label to this PR before merging."
          exit 1
  mysql-db-migration-testing-full:
    if: github.event.pull_request.draft == false
    needs: run-slow-ci-label-is-set
    env:
      ZENML_ANALYTICS_OPT_IN: false
      ZENML_DEBUG: true
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
        with:
          fetch-depth: 0
      - name: Set up Python 3.10
        uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405  # v6.2.0
        with:
          python-version: '3.10'
      - name: Login to Docker Hub
        uses: docker/login-action@4907a6ddec9925e35a0a9e82d7399ccc52663121  # v4.1.0
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}
        if: github.event.pull_request.head.repo.fork == false
      - name: Test migrations across versions
        run: bash scripts/test-migrations.sh mysql full
  mysql-db-migration-testing-random:
    if: github.event.pull_request.draft == false
    needs: run-slow-ci-label-is-set
    env:
      ZENML_ANALYTICS_OPT_IN: false
      ZENML_DEBUG: true
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
        with:
          fetch-depth: 0
      - name: Set up Python 3.10
        uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405  # v6.2.0
        with:
          python-version: '3.10'
      - name: Login to Docker Hub
        uses: docker/login-action@4907a6ddec9925e35a0a9e82d7399ccc52663121  # v4.1.0
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}
        if: github.event.pull_request.head.repo.fork == false
      - name: Test migrations across versions
        run: bash scripts/test-migrations.sh mysql random
  sqlite-db-migration-testing-full:
    needs: run-slow-ci-label-is-set
    runs-on: ubuntu-latest
    env:
      ZENML_ANALYTICS_OPT_IN: false
      ZENML_DEBUG: true
    if: github.event.pull_request.draft == false
    steps:
      - name: Checkout code
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
        with:
          fetch-depth: 0
      - name: Set up Python 3.10
        uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405  # v6.2.0
        with:
          python-version: '3.10'
      - name: Test migrations across versions
        run: bash scripts/test-migrations.sh sqlite full
  mariadb-db-migration-testing:
    if: github.event.pull_request.draft == false
    needs: run-slow-ci-label-is-set
    env:
      ZENML_ANALYTICS_OPT_IN: false
      ZENML_DEBUG: true
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
        with:
          fetch-depth: 0
      - name: Set up Python 3.10
        uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405  # v6.2.0
        with:
          python-version: '3.10'
      - name: Login to Docker Hub
        uses: docker/login-action@4907a6ddec9925e35a0a9e82d7399ccc52663121  # v4.1.0
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}
        if: github.event.pull_request.head.repo.fork == false
      - name: Test migrations across versions
        run: bash scripts/test-migrations.sh mariadb full
  small-checks:
    if: github.event.pull_request.draft == false
    needs: run-slow-ci-label-is-set
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
      - name: Set up Python
        uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405  # v6.2.0
        with:
          python-version: '3.11'
      - name: Install uv
        run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          source $HOME/.cargo/env
      - name: Create virtual environment
        run: |
          uv venv
      - name: Check for broken dependencies
        run: |
          source .venv/bin/activate
          uv pip check
      - name: Markdown link check
        uses: gaurav-nelson/github-action-markdown-link-check@3c3b66f1f7d0900e37b71eca45b63ea9eedfce31  # 1.0.17
        with:
          use-quiet-mode: 'yes'
          use-verbose-mode: 'no'
          folder-path: ./examples, ./docs/book, ./src
          file-path: ./README.md, ./LICENSE, ./RELEASE_NOTES.md, CODE-OF-CONDUCT.md,
            CONTRIBUTING.md, CLA.md, RELEASE_NOTES.md, ROADMAP.md
          config-file: .github/workflows/markdown_check_config.json
        continue-on-error: true
      - name: Security check
        run: |
          source .venv/bin/activate
          uv pip install bandit
          bash scripts/check-security.sh
      - name: Check for alembic branch divergence
        env:
          ZENML_DEBUG: 0
        run: |
          source .venv/bin/activate
          uv pip install alembic
          bash scripts/check-alembic-branches.sh
      - name: Install latest dashboard (test gitignore)
        run: bash scripts/install-dashboard.sh
  ubuntu-linting:
    needs: run-slow-ci-label-is-set
    if: github.event.pull_request.draft == false
    strategy:
      matrix:
        os: [ubuntu-latest]
        python-version: ['3.10', '3.12', '3.13']
      fail-fast: false
    uses: ./.github/workflows/linting.yml
    with:
      python-version: ${{ matrix.python-version }}
      os: ${{ matrix.os }}
    secrets: inherit
  ubuntu-unit-test:
    if: github.event.pull_request.draft == false
    needs: [run-slow-ci-label-is-set, ubuntu-linting]
    strategy:
      matrix:
        os: [ubuntu-latest]
        python-version: ['3.10', '3.12', '3.13']
      fail-fast: false
    uses: ./.github/workflows/unit-test.yml
    with:
      python-version: ${{ matrix.python-version }}
      os: ${{ matrix.os }}
    secrets: inherit
  windows-linting:
    needs: run-slow-ci-label-is-set
    if: github.event.pull_request.draft == false
    strategy:
      matrix:
        os: [windows-latest]
        python-version: ['3.10', '3.11', '3.12', '3.13']
      fail-fast: false
    uses: ./.github/workflows/linting.yml
    with:
      python-version: ${{ matrix.python-version }}
      os: ${{ matrix.os }}
    secrets: inherit
  windows-unit-test:
    if: github.event.pull_request.draft == false
    needs: [run-slow-ci-label-is-set, windows-linting]
    strategy:
      matrix:
        os: [windows-latest]
        python-version: ['3.10', '3.11', '3.12', '3.13']
      fail-fast: false
    uses: ./.github/workflows/unit-test.yml
    with:
      python-version: ${{ matrix.python-version }}
      os: ${{ matrix.os }}
    secrets: inherit
  macos-linting:
    needs: run-slow-ci-label-is-set
    if: github.event.pull_request.draft == false
    strategy:
      matrix:
        os: [macos-latest]
        python-version: ['3.10', '3.11', '3.12', '3.13']
      fail-fast: false
    uses: ./.github/workflows/linting.yml
    with:
      python-version: ${{ matrix.python-version }}
      os: ${{ matrix.os }}
    secrets: inherit
  macos-unit-test:
    if: github.event.pull_request.draft == false
    needs: [run-slow-ci-label-is-set, macos-linting]
    strategy:
      matrix:
        os: [macos-latest]
        python-version: ['3.10', '3.11', '3.12', '3.13']
      fail-fast: false
    uses: ./.github/workflows/unit-test.yml
    with:
      python-version: ${{ matrix.python-version }}
      os: ${{ matrix.os }}
      install_integrations: 'yes'
      reruns: 1
    secrets: inherit
  windows-integration-test:
    if: github.event.pull_request.draft == false
    needs: [run-slow-ci-label-is-set, windows-unit-test]
    strategy:
      matrix:
        os: [windows-latest]
        python-version: ['3.10', '3.11', '3.12', '3.13']
        test_environment: [default]
      fail-fast: false
    uses: ./.github/workflows/integration-test-slow.yml
    with:
      os: ${{ matrix.os }}
      python-version: ${{ matrix.python-version }}
      test_environment: ${{ matrix.test_environment }}
    secrets: inherit
  macos-integration-test:
    if: github.event.pull_request.draft == false
    needs: [run-slow-ci-label-is-set, macos-unit-test]
    strategy:
      matrix:
        os: [macos-latest]
        python-version: ['3.10', '3.11', '3.12', '3.13']
        test_environment: [default]
      fail-fast: false
    uses: ./.github/workflows/integration-test-slow.yml
    with:
      os: ${{ matrix.os }}
      python-version: ${{ matrix.python-version }}
      test_environment: ${{ matrix.test_environment }}
    secrets: inherit
  ubuntu-latest-integration-test:
    if: github.event.pull_request.draft == false
    needs: [run-slow-ci-label-is-set, ubuntu-unit-test]
    strategy:
      matrix:
        os: [ubuntu-latest]
        python-version: ['3.10', '3.12', '3.13']
        test_environment:
          - default
          - docker-server-docker-orchestrator-mysql
          - docker-server-docker-orchestrator-mariadb
        exclude:
          # docker is time-consuming to run, so we only run it on 3.11
          - test_environment: docker-server-docker-orchestrator-mysql
            python-version: '3.10'
          - test_environment: docker-server-docker-orchestrator-mysql
            python-version: '3.12'
          - test_environment: docker-server-docker-orchestrator-mysql
            python-version: '3.13'
          - test_environment: docker-server-docker-orchestrator-mariadb
            python-version: '3.10'
          - test_environment: docker-server-docker-orchestrator-mariadb
            python-version: '3.12'
          - test_environment: docker-server-docker-orchestrator-mariadb
            python-version: '3.13'
      fail-fast: false
    uses: ./.github/workflows/integration-test-slow.yml
    with:
      os: ${{ matrix.os }}
      python-version: ${{ matrix.python-version }}
      test_environment: ${{ matrix.test_environment }}
    secrets: inherit
  vscode-tutorial-pipelines-test:
    if: github.event.pull_request.draft == false
    needs: run-slow-ci-label-is-set
    uses: ./.github/workflows/vscode-tutorial-pipelines-test.yml
    secrets: inherit
  ubuntu-base-package-functionality:
    needs: run-slow-ci-label-is-set
    if: github.event.pull_request.draft == false
    strategy:
      matrix:
        os: [ubuntu-latest]
        python-version: ['3.11']
      fail-fast: false
    uses: ./.github/workflows/base-package-functionality.yml
    with:
      python-version: ${{ matrix.python-version }}
      os: ${{ matrix.os }}
    secrets: inherit

```

File: /Users/safoine/zenml-io/zenml/tests/unit/scripts/__init__.py
```py

```

File: /Users/safoine/zenml-io/zenml/.github/zizmor.yml
```yml
---
rules:
  # impostor-commit: Skip verification for repos that block git-upload-pack
  # mheap/github-action-required-labels returns 401 when zizmor tries to
  # list tags, causing the audit to fail. The SHA is verified manually.
  impostor-commit:
    ignore:
      - require-release-label.yml

  # Require SHA pinning for all actions (security best practice)
  # Ignores: First-party template repos that need to stay on main branch
  # These are ZenML's own templates and are intentionally unpinned
  unpinned-uses:
    ignore:
      - update-templates-to-examples.yml:44  # zenml-io/template-e2e-batch
      - update-templates-to-examples.yml:120  # zenml-io/template-nlp
      - update-templates-to-examples.yml:195  # zenml-io/template-starter
      - update-templates-to-examples.yml:272  # zenml-io/template-llm-finetuning
      - weekly-agent-pipelines-test.yml:101  # Ilshidur/action-discord uses @master, can't be SHA-pinned

  # excessive-permissions: These workflows use default permissions.
  # While explicit permissions are recommended, these are internal workflows
  # with controlled triggers. Address permissions incrementally in future PRs.
  # TODO: Audit workflows and add explicit permissions blocks
  excessive-permissions:
    disable: true

  # artipacked: Require persist-credentials: false on checkout
  # Disabled: Many ZenML workflows need credentials for pushing commits back to PRs
  # (template updates, auto-formatting). Address incrementally in future PRs.
  # TODO: Audit workflows and add persist-credentials: false where safe
  artipacked:
    disable: true

  # secrets-outside-env: Secrets used without dedicated GitHub Environments.
  # Disabled: 89 findings across 15+ workflows. Adding GitHub Environments
  # requires coordinating environment protection rules and is a significant
  # change. Address incrementally in a dedicated PR.
  # TODO: Add GitHub Environments to workflows that use secrets (see  # 4664)
  secrets-outside-env:
    disable: true

  # superfluous-actions: Actions that duplicate built-in runner functionality.
  # These are peter-evans/create-or-update-comment and peter-evans/find-comment
  # which could be replaced with `gh pr comment` / `gh issue comment`.
  # TODO: Replace with gh CLI equivalents (see  # 4664)
  superfluous-actions:
    disable: true

  # Detect dangerous template expansions
  # Ignores: Low-confidence findings for step outputs used in github-script
  # (step outputs within same workflow are trusted)
  template-injection:
    ignore:
      - snack-it.yml:352  # issue_number from step output
      - snack-it.yml:353  # continuation of above
      - snack-it.yml:354  # project_added from step output
      - validate-changelog.yml:37  # step output
      - notify-changelog.yml:27  # inputs.release_tag is workflow_dispatch input (authorized users only)

  # Detect cache poisoning vulnerabilities
  # Ignores: Low-confidence findings for protected publish workflows
  cache-poisoning:
    ignore:
      - publish_api_docs.yml:24  # Protected release branch, docs only (setup-node caching)
      - publish_api_docs.yml:27  # Protected release branch, docs only

  # Detect malformed conditionals
  unsound-condition: {}

  # PyPI publishing suggestions (informational)
  # Ignored: release.yml uses OIDC trusted publishing; nightly/reusable workflows are pre-configured
  use-trusted-publishing:
    ignore:
      - publish_to_pypi_nightly.yml
      - publish_to_pypi.yml

  # secrets-inherit: Intentional for ZenML's internal reusable workflow pattern
  # All ignored files are first-party workflows calling other first-party workflows
  secrets-inherit:
    ignore:
      - ci-fast.yml
      - ci-slow.yml
      - linting.yml
      - unit-test.yml
      - integration-test-fast.yml
      - integration-test-fast-services.yml
      - integration-test-slow.yml
      - integration-test-slow-services.yml
      - base-package-functionality.yml
      - update-templates-to-examples.yml
      - templates-test.yml
      - vscode-tutorial-pipelines-test.yml
      - weekly-agent-pipelines-test.yml
      - nightly_build.yml
      - release.yml
      - ci-medium.yml
      - ci-slow-develop.yml
      - slow-ci-on-pr.yml
      - offload-cache-warm.yml

```

File: /Users/safoine/zenml-io/zenml/scripts/test-migrations.sh
```sh
#!/bin/bash

DB="sqlite"
DB_STARTUP_DELAY=30 # Time in seconds to wait for the database container to start
RANDOM_MIGRATION_COUNT="${RANDOM_MIGRATION_COUNT:-3}"
RANDOM_MIGRATION_SEED="${RANDOM_MIGRATION_SEED:-${GITHUB_RUN_ID:-}}"

export ZENML_ANALYTICS_OPT_IN=false
export ZENML_DEBUG=true

# Use a temporary directory for the config path
export ZENML_CONFIG_PATH=/tmp/upgrade-tests

if [ -z "$1" ]; then
  echo "No database argument passed, using default: $DB"
else
  DB="$1"
fi

if [ -z "$2" ]; then
  echo "No migration type argument passed, defaulting to full"
  MIGRATION_TYPE="full"
else
  MIGRATION_TYPE="$2"
fi

# List of versions to test
VERSIONS=("0.43.0" "0.44.3" "0.45.6" "0.47.0" "0.50.0" "0.51.0" "0.52.0" "0.53.1" "0.54.1" "0.55.5" "0.56.4" "0.57.1" "0.60.0" "0.61.0" "0.62.0" "0.63.0" "0.64.0" "0.65.0" "0.68.0" "0.70.0" "0.71.0" "0.72.0" "0.74.0" "0.80.0" "0.80.1" "0.80.2" "0.81.0" "0.83.1" "0.84.0" "0.84.1" "0.85.0" "0.90.0" "0.91.0" "0.91.1" "0.91.2" "0.92.0" "0.93.0" "0.93.1" "0.93.2" "0.93.3" "0.94.0" "0.94.1" "0.94.3")

# Try to get the latest version using pip index
version=$(pip index versions zenml 2>/dev/null | grep -v YANKED | head -n1 | awk '{print $2}' | tr -d '()')

# Verify we got a version
if [ -z "$version" ]; then
    echo "Error: Could not find the latest version for zenml" >&2
    return 1
fi

LATEST_VERSION=$(echo $version | xargs)

if [[ ! " ${VERSIONS[@]} " =~ " ${LATEST_VERSION} " ]]; then
   VERSIONS+=("${LATEST_VERSION}")
fi

# Function to compare semantic versions
function version_compare() {
    local regex="^([0-9]+)\.([0-9]+)\.([0-9]+)(-([0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*))?(\\+([0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*))?$"
    local ver1="$1"
    local ver2="$2"

    if [[ "$ver1" == "$ver2" ]]; then
        echo "="
        return
    fi

    if [[ $ver1 == "current" ]]; then
        echo ">"
        return
    fi

    if [[ $ver2 == "current" ]]; then
        echo "<"
        return
    fi

    if ! [[ $ver1 =~ $regex ]]; then
        echo "First argument does not conform to semantic version format" >&2
        return 1
    fi

    if ! [[ $ver2 =~ $regex ]]; then
        echo "Second argument does not conform to semantic version format" >&2
        return 1
    fi

    # Compare major, minor, and patch versions
    IFS='.' read -ra ver1_parts <<< "$ver1"
    IFS='.' read -ra ver2_parts <<< "$ver2"

    for ((i=0; i<3; i++)); do
        if ((ver1_parts[i] > ver2_parts[i])); then
            echo ">"
            return
        elif ((ver1_parts[i] < ver2_parts[i])); then
            echo "<"
            return
        fi
    done

    # Extend comparison to pre-release versions if necessary
    # This is a simplified comparison that may need further refinement
    if [[ -n ${ver1_parts[3]} && -z ${ver2_parts[3]} ]]; then
        echo "<"
        return
    elif [[ -z ${ver1_parts[3]} && -n ${ver2_parts[3]} ]]; then
        echo ">"
        return
    elif [[ -n ${ver1_parts[3]} && -n ${ver2_parts[3]} ]]; then
        if [[ ${ver1_parts[3]} > ${ver2_parts[3]} ]]; then
            echo ">"
            return
        elif [[ ${ver1_parts[3]} < ${ver2_parts[3]} ]]; then
            echo "<"
            return
        fi
    fi

    echo "="
}

function run_tests_for_version() {
    set -e  # Exit immediately if a command exits with a non-zero status
    local VERSION=$1

    echo "===== Testing version $VERSION ====="

    rm -rf test_starter template-starter

    # Check if the version supports templates via zenml init (> 0.43.0)
    if [ "$(version_compare "$VERSION" "0.43.0")" == ">" ]; then
        mkdir test_starter
        zenml init --template starter --path test_starter --template-with-defaults <<< $'my@mail.com\n'
    else
        copier copy -l --trust -r release/0.43.0 https://github.com/zenml-io/template-starter.git test_starter
    fi

    cd test_starter

    echo "===== Installing required integrations ====="
    # TODO: REMOVE BEFORE MERGE
    if [ "$VERSION" == "current" ]; then
        zenml integration export-requirements sklearn pandas --output-file integration-requirements.txt
    elif [ "$(version_compare "$VERSION" "0.66.0")" == "<" ]; then
        zenml integration export-requirements sklearn --output-file integration-requirements.txt
    else
        zenml integration export-requirements sklearn pandas --output-file integration-requirements.txt
    fi

    uv pip install -r integration-requirements.txt
    rm integration-requirements.txt

    echo "===== Running starter template pipeline ====="
    # Check if the version supports templates with arguments (> 0.52.0)
    if [ "$(version_compare "$VERSION" "0.52.0")" == ">" ]; then
        python3 run.py --feature-pipeline --training-pipeline --no-cache
        python3 run.py --feature-pipeline --training-pipeline # run with cache
    else
        python3 run.py --no-cache
        python3 run.py # run with cache
    fi
    # Add additional CLI tests here
    zenml version

    # Confirm DB works and is accessible
    ZENML_LOGGING_VERBOSITY=INFO zenml pipeline runs list

    # The database backup and restore feature is available since 0.55.1.
    # However, it has been broken for various reasons up to and including
    # 0.57.0, so we skip this test for those versions.
    if [ "$VERSION" == "current" ] || [ "$(version_compare "$VERSION" "0.57.0")" == ">" ]; then
        echo "===== Testing database backup and restore (file dump) ====="

        pipelines_before_restore=$(ZENML_LOGGING_VERBOSITY=INFO zenml pipeline runs list --size 5000)

        # Perform a DB backup and restore using a dump file
        rm -f /tmp/zenml-backup.sql
        zenml backup-database -s dump-file --location /tmp/zenml-backup.sql --overwrite
        zenml restore-database -s dump-file --location /tmp/zenml-backup.sql

        # Check that DB still works after restore and the content is the same
        pipelines_after_restore=$(ZENML_LOGGING_VERBOSITY=INFO zenml pipeline runs list --size 5000)
        if [ "$pipelines_before_restore" != "$pipelines_after_restore" ]; then
            echo "----- Before restore -----"
            echo "$pipelines_before_restore"
            echo "----- After restore -----"
            echo "$pipelines_after_restore"
            echo "ERROR: database backup and restore (file dump) test failed!"
            exit 1
        fi

        # Run the pipeline again to check if the restored database is working
        echo "===== Running starter template pipeline after DB restore (file dump) ====="
        python3 run.py --feature-pipeline --training-pipeline --no-cache
        python3 run.py --feature-pipeline --training-pipeline # run with cache

        # For a mysql compatible database, perform a DB backup and restore using
        # the backup database
        if [ "$DB" == "mysql" ] || [ "$DB" == "mariadb" ]; then
            echo "===== Testing database backup and restore (backup database) ====="

            pipelines_before_restore=$(ZENML_LOGGING_VERBOSITY=INFO zenml pipeline runs list --size 5000)

            # Perform a DB backup and restore
            zenml backup-database -s database --location zenml-backup --overwrite
            zenml restore-database -s database --location zenml-backup

            # Check that DB still works after restore and the content is the
            # same
            pipelines_after_restore=$(ZENML_LOGGING_VERBOSITY=INFO zenml pipeline runs list --size 5000)
            if [ "$pipelines_before_restore" != "$pipelines_after_restore" ]; then
                echo "----- Before restore -----"
                echo "$pipelines_before_restore"
                echo "----- After restore -----"
                echo "$pipelines_after_restore"
                echo "ERROR: database backup and restore (backup database) test failed!"
                exit 1
            fi

            # Run the pipeline again to check if the restored database is working
            echo "===== Running starter template pipeline after DB restore (backup database) ====="
            python3 run.py --feature-pipeline --training-pipeline --no-cache
            python3 run.py --feature-pipeline --training-pipeline # run with cache
        fi

    else
        echo "Skipping database backup and restore test for version $VERSION"
    fi

    cd ..
    rm -rf test_starter template-starter
    echo "===== Finished testing version $VERSION ====="
}

function test_upgrade_to_version() {
    set -e  # Exit immediately if a command exits with a non-zero status
    local VERSION=$1

    echo "===== Testing upgrade to version $VERSION ====="

    # (re)create a virtual environment
    rm -rf ".venv-upgrade"
    uv venv ".venv-upgrade"
    source ".venv-upgrade/bin/activate"

    # Install the specific version
    if [ "$VERSION" == "current" ]; then
        uv pip install -U setuptools wheel pip
        uv pip install -e ".[templates,server]"
    else
        # Old ZenML versions use pkg_resources, removed in setuptools 82+
        uv pip install -U "setuptools<82" wheel pip
        uv pip install "zenml[templates,server]==$VERSION"
        if [ "$(version_compare "$VERSION" "0.60.0")" == "<" ]; then
            # handles unpinned sqlmodel dependency in older versions
            uv pip install "sqlmodel==0.0.8" "bcrypt==4.0.1" "pyyaml-include<2.0" "numpy<2.0.0" "tenacity!=8.4.0"
        fi
    fi

    # Get the major and minor version of Python
    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')

    if [ "$DB" == "mysql" ] || [ "$DB" == "mariadb" ]; then

        if [ "$(version_compare "$VERSION" "0.68.1")" == ">" ]; then
            zenml login mysql://root:password@127.0.0.1/zenml
        else
            zenml connect --url mysql://root:password@127.0.0.1/zenml --username root --password password
        fi
    fi

    # Run the tests for this version
    run_tests_for_version "$VERSION"

    deactivate
    rm -rf ".venv-upgrade"

    echo "===== Finished testing upgrade to version $VERSION ====="
}

function start_db() {
    set -e  # Exit immediately if a command exits with a non-zero status

    if [ "$DB" == "sqlite" ]; then
        return
    fi

    stop_db    

    echo "===== Starting $DB database ====="
    if [ "$DB" == "mysql" ]; then
        # run a mysql instance in docker
        docker run --name mysql --rm -d -p 3306:3306 -e MYSQL_ROOT_PASSWORD=password mysql:8
    elif [ "$DB" == "mariadb" ]; then
        # run a mariadb instance in docker
        docker run --name mariadb --rm -d -p 3306:3306 -e MYSQL_ROOT_PASSWORD=password mariadb:10.6
    fi

    # the database container takes a while to start up
    sleep $DB_STARTUP_DELAY
    echo "===== Finished starting $DB database ====="

}

function stop_db() {
    set -e  # Exit immediately if a command exits with a non-zero status

    if [ "$DB" == "sqlite" ]; then
        return
    fi

    echo "===== Stopping $DB database ====="

    if [ "$DB" == "mysql" ]; then
        docker stop mysql || true
    elif [ "$DB" == "mariadb" ]; then
        docker stop mariadb || true
    fi

    echo "===== Finished stopping $DB database ====="
}

# If testing the mariadb database, we remove versions older than 0.54.0 because
# we only started supporting mariadb from that version onwards
if [ "$DB" == "mariadb" ]; then
    MARIADB_VERSIONS=()
    for VERSION in "${VERSIONS[@]}"
    do
        if [ "$(version_compare "$VERSION" "0.54.0")" == "<" ]; then
            continue
        fi
        MARIADB_VERSIONS+=("$VERSION")
    done
    VERSIONS=("${MARIADB_VERSIONS[@]}")
fi

echo "Testing database: $DB"
echo "Testing versions: ${VERSIONS[@]}"
echo "Migration type: $MIGRATION_TYPE"

if [ "$MIGRATION_TYPE" == "random" ]; then
    if ! [[ "$RANDOM_MIGRATION_COUNT" =~ ^[0-9]+$ ]] || [ "$RANDOM_MIGRATION_COUNT" -lt 1 ]; then
        echo "RANDOM_MIGRATION_COUNT must be a positive integer" >&2
        exit 1
    fi
    if [ -n "$RANDOM_MIGRATION_SEED" ]; then
        RANDOM="$RANDOM_MIGRATION_SEED"
        echo "Random migration seed: $RANDOM_MIGRATION_SEED"
    fi
    echo "Random migration count: $RANDOM_MIGRATION_COUNT"
fi

# Start completely fresh
rm -rf "$ZENML_CONFIG_PATH"

pip install -U uv

# Start the database
start_db

if [ "$MIGRATION_TYPE" == "full" ]; then
    for VERSION in "${VERSIONS[@]}"
    do
        test_upgrade_to_version "$VERSION"
    done

    # Test the most recent migration with MySQL
    test_upgrade_to_version "current"
elif [ "$MIGRATION_TYPE" == "latest" ]; then
    test_upgrade_to_version "$LATEST_VERSION"
    test_upgrade_to_version "current"
else
    # Test the most recent migration with MySQL
    test_upgrade_to_version "current"

    # Start fresh again for this part
    rm -rf "$ZENML_CONFIG_PATH"

    # Fresh database for sequential testing
    stop_db
    start_db

    # Test random migrations across multiple versions
    echo "===== TESTING RANDOM MIGRATIONS ====="
    set -e

    function test_random_migrations() {
        set -e  # Exit immediately if a command exits with a non-zero status

        echo "===== TESTING RANDOM MIGRATIONS ====="

        # Randomly select versions for random migrations
        MIGRATION_VERSIONS=()
        while [ ${#MIGRATION_VERSIONS[@]} -lt "$RANDOM_MIGRATION_COUNT" ]; do
            VERSION=${VERSIONS[$RANDOM % ${#VERSIONS[@]}]}
            if [[ ! " ${MIGRATION_VERSIONS[@]} " =~ " $VERSION " ]]; then
                MIGRATION_VERSIONS+=("$VERSION")
            fi
        done

        # Sort the versions in ascending order using semantic version comparison
        sorted_versions=()
        for version in "${MIGRATION_VERSIONS[@]}"; do
            inserted=false
            for i in "${!sorted_versions[@]}"; do
                if [ "$(version_compare "$version" "${sorted_versions[$i]}")" == "<" ]; then
                    sorted_versions=("${sorted_versions[@]:0:$i}" "$version" "${sorted_versions[@]:$i}")
                    inserted=true
                    break
                fi
            done
            if [ "$inserted" == false ]; then
                sorted_versions+=("$version")
            fi
        done
        MIGRATION_VERSIONS=("${sorted_versions[@]}")

        # Echo the sorted list of migration versions
        echo "============================="
        echo "TESTING MIGRATION_VERSIONS: ${MIGRATION_VERSIONS[@]}"
        echo "============================="

        for i in "${!MIGRATION_VERSIONS[@]}"; do
            test_upgrade_to_version "${MIGRATION_VERSIONS[$i]}"
        done

        # Test the most recent migration with MySQL
        test_upgrade_to_version "current"
    }

    test_random_migrations
fi

# Stop the database
stop_db

# Clean up
rm -rf "$ZENML_CONFIG_PATH"
```

File: /Users/safoine/zenml-io/zenml/scripts/check_known_good.py
```py
#!/usr/bin/env python3
"""Verify a release tag has a recent slow-CI qualification Check Run."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from ci_matrix_hash import compute_matrix_hash

CHECK_NAME = "ci-slow-develop/qualification"


def _github_request(url: str) -> dict:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required")

    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _tagged_sha() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD^{commit}"], text=True
    ).strip()


def _verify(repository: str, sha: str, max_age_hours: int) -> str:
    owner, repo = repository.split("/", 1)
    url = (
        f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}"
        f"/check-runs?check_name={CHECK_NAME}&status=completed"
    )
    payload = _github_request(url)
    expected_hash = compute_matrix_hash(
        Path(".github/workflows/ci-slow-develop.yml")
    )

    for check_run in payload.get("check_runs", []):
        if check_run.get("conclusion") != "success":
            continue
        external_id = check_run.get("external_id") or ""
        try:
            run_id, matrix_hash, completed_at = external_id.split(":", 2)
        except ValueError:
            continue
        if matrix_hash != expected_hash:
            raise RuntimeError(
                "Matrix hash mismatch: "
                f"qualification={matrix_hash}, current={expected_hash}"
            )
        completed = dt.datetime.fromisoformat(
            completed_at.replace("Z", "+00:00")
        )
        age_hours = (
            dt.datetime.now(dt.timezone.utc) - completed
        ).total_seconds() / 3600
        if age_hours > max_age_hours:
            raise RuntimeError(
                f"Qualification too stale ({age_hours:.1f}h old)"
            )
        return f"Qualification OK: run {run_id}, {age_hours:.1f}h old"

    raise RuntimeError(f"No green {CHECK_NAME} Check Run found on {sha}")


def main() -> None:
    """Run the CLI."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-age-hours", type=int, default=168)
    parser.add_argument("--warn-only", action="store_true")
    args = parser.parse_args()

    try:
        repository = os.environ["GITHUB_REPOSITORY"]
        message = _verify(repository, _tagged_sha(), args.max_age_hours)
        print(message)
    except Exception as exc:
        if args.warn_only:
            print(f"::warning::{exc}")
            return
        print(f"::error::{exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()

```

File: /Users/safoine/zenml-io/zenml/scripts/ci/print_junit_summary.py
```py
"""Print concise summaries for JUnit XML files."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

try:
    from scripts.ci.print_junit_failures import print_failures
except ModuleNotFoundError:
    from print_junit_failures import print_failures


@dataclass(frozen=True)
class JUnitSummary:
    """Aggregated JUnit counts."""

    tests: int
    failures: int
    errors: int
    skipped: int
    time: float

    @property
    def failed(self) -> bool:
        """Whether the summary contains failed or errored tests."""
        return self.failures > 0 or self.errors > 0


def _int_attr(element: ET.Element, name: str) -> int:
    value = element.attrib.get(name, "0")
    try:
        return int(value)
    except ValueError:
        return 0


def _float_attr(element: ET.Element, name: str) -> float:
    value = element.attrib.get(name, "0")
    try:
        return float(value)
    except ValueError:
        return 0.0


def parse_junit_summary(path: str | Path) -> JUnitSummary:
    """Parse aggregate counts from a JUnit XML file."""
    root = ET.parse(path).getroot()
    if root.tag == "testsuite":
        suites = [root]
    elif root.tag == "testsuites":
        suites = list(root.iter("testsuite"))
    else:
        raise ValueError(f"Unsupported JUnit root tag: {root.tag}")

    return JUnitSummary(
        tests=sum(_int_attr(suite, "tests") for suite in suites),
        failures=sum(_int_attr(suite, "failures") for suite in suites),
        errors=sum(_int_attr(suite, "errors") for suite in suites),
        skipped=sum(_int_attr(suite, "skipped") for suite in suites),
        time=sum(_float_attr(suite, "time") for suite in suites),
    )


def print_parsed_summary(summary: JUnitSummary) -> None:
    """Print a human-readable JUnit summary."""
    print(
        "JUnit summary: "
        f"tests={summary.tests}, failures={summary.failures}, "
        f"errors={summary.errors}, skipped={summary.skipped}, "
        f"time={summary.time:.2f}s"
    )


def print_summary(path: str | Path) -> JUnitSummary:
    """Parse and print a JUnit summary plus failure details."""
    summary = parse_junit_summary(path)
    print_parsed_summary(summary)
    if summary.failed:
        print_failures(path)
    return summary


def main(argv: list[str]) -> int:
    """CLI entrypoint."""
    if len(argv) != 2:
        print(f"Usage: {argv[0]} <junit.xml>", file=sys.stderr)
        return 2
    path = Path(argv[1])
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        return 2
    print_summary(path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

```

File: /Users/safoine/zenml-io/zenml/offload.toml
```toml
[offload]
max_parallel = 20
test_timeout_secs = 960
max_batch_duration_secs = 320
sandbox_project_root = "/app"

[provider]
type = "default"
prepare_command = "uv run @modal_sandbox.py prepare Dockerfile.ci --cached --include-cwd --sandbox-init-cmd 'cd /app && pip install --no-deps -e . -q'"
create_command = "uv run @modal_sandbox.py create {image_id} --cpu 4 --memory-gb 8 --env PYTHONDONTWRITEBYTECODE=1 --env PYTHONUNBUFFERED=1 --env ZENML_DEBUG=true --env ZENML_ANALYTICS_OPT_IN=false --env AUTO_OPEN_DASHBOARD=false"
exec_command = "python3 @modal_sandbox.py exec {sandbox_id} {command}"
destroy_command = "uv run @modal_sandbox.py destroy {sandbox_id}"
download_command = "printf '[offload] exec_and_fetch returned no inline artifacts; falling back to download_command.\\n' >&2; python3 @modal_sandbox.py download {sandbox_id} {paths}"
exec_and_fetch_command = "python3 @modal_sandbox.py exec-and-fetch {sandbox_id} {command} --fetch {fetch}"
timeout_secs = 960

[framework]
type = "pytest"
paths = []
command = "python -m pytest -p no:pytest_postgresql"
run_args = "--no-provision --environment default -p no:randomly -p no:rerunfailures"

[groups.unit]
retry_count = 0
filters = "tests/unit"

[groups.integration]
retry_count = 0
filters = "tests/integration -m 'not slow'"

[report]
output_dir = ".ci/offload"

```

File: /Users/safoine/zenml-io/zenml/scripts/develop_health_gate.py
```py
#!/usr/bin/env python3
"""Evaluate whether the merge queue can proceed while develop is healthy."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from ci_matrix_hash import compute_matrix_hash

CHECK_NAME = "ci-slow-develop/qualification"
DEFAULT_MAX_AGE_HOURS = 30
DEFAULT_GRACE_AFTER_SCHEDULE_HOURS = 6
DEVELOP_BRANCH = "develop"
FIX_DEVELOP_LABEL = "fix-develop"


def _github_request(
    path: str, query: dict[str, str] | None = None
) -> dict[str, Any]:
    """Send an authenticated GitHub API request."""
    token = os.environ["GITHUB_TOKEN"]
    repository = os.environ["GITHUB_REPOSITORY"]
    query_string = urllib.parse.urlencode(query or {})
    suffix = f"?{query_string}" if query_string else ""
    url = f"https://api.github.com/repos/{repository}{path}{suffix}"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _parse_datetime(value: str) -> dt.datetime:
    """Parse a GitHub timestamp."""
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def _current_develop_sha() -> str:
    """Return the current develop branch SHA."""
    branch = _github_request(f"/branches/{DEVELOP_BRANCH}")
    return str(branch["commit"]["sha"])


def _commit_datetime(sha: str) -> dt.datetime:
    """Return the commit timestamp for a SHA."""
    commit = _github_request(f"/commits/{sha}")
    return _parse_datetime(str(commit["commit"]["committer"]["date"]))


def _qualification_check_runs(sha: str) -> list[dict[str, Any]]:
    """Return qualification Check Runs for a SHA, newest first."""
    payload = _github_request(
        f"/commits/{sha}/check-runs",
        {"check_name": CHECK_NAME, "status": "completed"},
    )
    check_runs = list(payload.get("check_runs", []))
    return sorted(
        check_runs,
        key=lambda item: item.get("completed_at") or "",
        reverse=True,
    )


def _extract_pr_numbers_from_event() -> set[int]:
    """Extract PR numbers from the current GitHub event payload."""
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path or not Path(event_path).exists():
        return set()

    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    numbers: set[int] = set()

    for pr in event.get("pull_requests", []) or []:
        if number := pr.get("number"):
            numbers.add(int(number))

    merge_group = event.get("merge_group") or {}
    for candidate in [merge_group.get("head_ref"), merge_group.get("ref")]:
        if not candidate:
            continue
        match = re.search(r"/pr-(\d+)-", str(candidate))
        if match:
            numbers.add(int(match.group(1)))

    return numbers


def _labels_for_pr(number: int) -> set[str]:
    """Return labels for a PR number."""
    payload = _github_request(f"/issues/{number}/labels", {"per_page": "100"})
    return {str(label["name"]) for label in payload}


def _merge_group_labels() -> set[str]:
    """Return labels for PRs represented by the merge-group event."""
    labels: set[str] = set()
    for number in _extract_pr_numbers_from_event():
        labels.update(_labels_for_pr(number))
    return labels


def _latest_nightly_schedule(now: dt.datetime) -> dt.datetime:
    """Return the latest expected nightly slow-CI schedule time."""
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _external_id_parts(
    check_run: dict[str, Any],
) -> tuple[str, str, dt.datetime]:
    """Parse the qualification Check Run external ID."""
    external_id = str(check_run.get("external_id") or "")
    try:
        run_id, matrix_hash, completed_at = external_id.split(":", 2)
    except ValueError as exc:
        raise RuntimeError(
            f"Qualification Check Run has invalid external_id: {external_id!r}"
        ) from exc
    return run_id, matrix_hash, _parse_datetime(completed_at)


def _pass(message: str) -> None:
    """Pass the gate with a message."""
    print(message)


def _fail(message: str) -> None:
    """Fail the gate with a message."""
    print(f"::error::{message}")
    sys.exit(1)


def main() -> None:
    """Run the health gate."""
    max_age_hours = int(os.environ.get("MAX_AGE_HOURS", DEFAULT_MAX_AGE_HOURS))
    grace_hours = int(
        os.environ.get(
            "GRACE_AFTER_SCHEDULE_HOURS", DEFAULT_GRACE_AFTER_SCHEDULE_HOURS
        )
    )
    now = dt.datetime.now(dt.timezone.utc)
    develop_sha = _current_develop_sha()
    expected_matrix_hash = compute_matrix_hash(
        Path(".github/workflows/ci-slow-develop.yml")
    )
    check_runs = _qualification_check_runs(develop_sha)

    if not check_runs:
        latest_schedule = _latest_nightly_schedule(now)
        develop_commit_time = _commit_datetime(develop_sha)
        if develop_commit_time > latest_schedule:
            _pass(
                "No develop qualification exists yet, but develop HEAD is "
                "newer than the latest nightly schedule. Passing under grace."
            )
            return
        if now <= latest_schedule + dt.timedelta(hours=grace_hours):
            _pass(
                "No develop qualification exists yet, but the nightly grace "
                "window is still open. Passing under grace."
            )
            return
        _fail(
            f"No {CHECK_NAME} Check Run exists on develop SHA {develop_sha}."
        )

    latest = check_runs[0]
    conclusion = latest.get("conclusion")
    if conclusion == "failure":
        labels = _merge_group_labels()
        if FIX_DEVELOP_LABEL in labels:
            _pass("Develop is red, but this PR carries fix-develop.")
            return
        _fail(
            "Develop is red. Add fix-develop only to the PR that repairs "
            "the failing develop state."
        )

    if conclusion != "success":
        _fail(f"Latest {CHECK_NAME} conclusion is {conclusion!r}.")

    run_id, matrix_hash, completed_at = _external_id_parts(latest)
    if matrix_hash != expected_matrix_hash:
        _fail(
            "Slow-CI matrix hash changed since the latest develop "
            f"qualification. qualification={matrix_hash}, "
            f"current={expected_matrix_hash}"
        )

    age_hours = (now - completed_at).total_seconds() / 3600
    if age_hours > max_age_hours:
        _fail(
            f"Develop qualification is stale ({age_hours:.1f}h old). "
            "Trigger ci-slow-develop manually."
        )

    _pass(
        f"Develop qualification OK: sha={develop_sha}, run={run_id}, "
        f"age={age_hours:.1f}h."
    )


if __name__ == "__main__":
    main()

```

File: /Users/safoine/zenml-io/zenml/scripts/ci/export_offload_integration_requirements.py
```py
"""Export integration requirements for the offload CI image."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

IGNORED_INTEGRATIONS = {
    "feast",
    "label_studio",
    "bentoml",
    "seldon",
    "pycaret",
    "skypilot_aws",
    "skypilot_gcp",
    "skypilot_azure",
    "skypilot_kubernetes",
    "skypilot_lambda",
    "pigeon",
    "prodigy",
    "argilla",
    "vllm",
    "tensorflow",
    "deepchecks",
}

SUPPLEMENTAL_REQUIREMENTS = [
    "pyyaml>=6.0.1",
    "pyopenssl",
    "typing-extensions",
    "maison<2",
]


def export_requirements(output_file: Path) -> None:
    """Export the requirements used by the offload Modal image."""
    from zenml.integrations.registry import integration_registry

    output_file.parent.mkdir(parents=True, exist_ok=True)
    requirements: list[str] = []
    for integration_name in sorted(integration_registry.integrations):
        if integration_name in IGNORED_INTEGRATIONS:
            continue
        requirements.extend(
            integration_registry.select_integration_requirements(
                integration_name
            )
        )

    requirements.extend(SUPPLEMENTAL_REQUIREMENTS)
    output_file.write_text("\n".join(requirements) + "\n", encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_file", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI."""
    args = _build_parser().parse_args(argv)
    export_requirements(args.output_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())

```

File: /Users/safoine/zenml-io/zenml/.github/workflows/validate-workspace-safety.yml
```yml
---
name: Validate integration workspace safety
on:
  pull_request:
    paths:
      - tests/integration/**
      - scripts/audit_integration_workspace_safety.py
      - .github/workspace-safety-baseline.txt
  workflow_dispatch:
jobs:
  validate-workspace-safety:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
      - name: Set up Python
        uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405  # v6.2.0
        with:
          python-version: '3.11'
      - name: Validate workspace-safety classification
        run: python scripts/audit_integration_workspace_safety.py --enforce

```

File: /Users/safoine/zenml-io/zenml/scripts/ci/emit_timing_manifest.py
```py
"""Emit lightweight timing metadata for offloaded CI lanes."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _phase_manifest(phases: list[str]) -> dict[str, dict[str, Any]]:
    manifest: dict[str, dict[str, Any]] = {}
    for phase in phases:
        name, separator, payload = phase.partition("=")
        if not separator:
            continue
        started_raw, _, remainder = payload.partition(",")
        completed_raw, _, status = remainder.partition(",")
        started = _parse_timestamp(started_raw)
        completed = _parse_timestamp(completed_raw)
        manifest[name] = {
            "started_at_unix": started,
            "completed_at_unix": completed,
            "duration_seconds": completed - started
            if started is not None
            and completed is not None
            and completed >= started
            else None,
            "status": status,
        }
    return manifest


def _parse_timestamp(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _file_metadata(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    stat = path.stat()
    return {
        "exists": True,
        "size_bytes": stat.st_size,
        "modified_at_utc": datetime.fromtimestamp(
            stat.st_mtime,
            tz=timezone.utc,
        ).isoformat(),
    }


def build_manifest(
    *,
    lane: str,
    output_dir: Path,
    started_at: str | None,
    completed_at: str | None,
    classification: str,
    phases: list[str] | None = None,
) -> dict[str, Any]:
    """Build a JSON-serializable timing manifest."""
    started = _parse_timestamp(started_at)
    completed = _parse_timestamp(completed_at)
    duration_seconds = (
        completed - started
        if started is not None
        and completed is not None
        and completed >= started
        else None
    )

    return {
        "schema_version": "ci-offload-timing/v1",
        "lane": lane,
        "classification": classification,
        "started_at_unix": started,
        "completed_at_unix": completed,
        "duration_seconds": duration_seconds,
        "phases": _phase_manifest(phases or []),
        "github": {
            "workflow": os.environ.get("GITHUB_WORKFLOW", ""),
            "job": os.environ.get("GITHUB_JOB", ""),
            "run_id": os.environ.get("GITHUB_RUN_ID", ""),
            "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
            "ref": os.environ.get("GITHUB_REF", ""),
            "event_name": os.environ.get("GITHUB_EVENT_NAME", ""),
        },
        "artifacts": {
            "junit_xml": _file_metadata(output_dir / "junit.xml"),
            "junit_seed_xml": _file_metadata(output_dir / "junit.seed.xml"),
            "junit_stale_xml": _file_metadata(output_dir / "junit.stale.xml"),
            "run_start_marker": _file_metadata(
                output_dir / "run-start.marker"
            ),
            "coverage_xml": _file_metadata(output_dir / "coverage.xml"),
            "offload_log": _file_metadata(output_dir / "offload.log"),
        },
        "cache": {
            "uv_cache_hit": os.environ.get("OFFLOAD_UV_CACHE_HIT", ""),
            "image_cache_hit": os.environ.get("OFFLOAD_IMAGE_CACHE_HIT", ""),
            "junit_cache_hit": os.environ.get("OFFLOAD_JUNIT_CACHE_HIT", ""),
            "junit_current": os.environ.get("OFFLOAD_JUNIT_CURRENT", ""),
            "junit_cacheable": os.environ.get("OFFLOAD_JUNIT_CACHEABLE", ""),
        },
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lane", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--started-at")
    parser.add_argument("--completed-at")
    parser.add_argument("--classification", default="unknown")
    parser.add_argument(
        "--phase",
        action="append",
        default=[],
        help="Phase timing as name=start_unix,end_unix,status.",
    )
    return parser


def main() -> None:
    """Run the CLI."""
    args = _build_parser().parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(
        lane=args.lane,
        output_dir=args.output_dir,
        started_at=args.started_at,
        completed_at=args.completed_at,
        classification=args.classification,
        phases=args.phase,
    )
    (args.output_dir / "timing-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

```

File: /Users/safoine/zenml-io/zenml/tests/integration/functional/cli/test_model.py
```py
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
"""Test zenml Model Control Plane CLI commands."""

from uuid import uuid4

from click.testing import CliRunner

from tests.integration.functional.cli.conftest import NAME, PREFIX
from zenml.cli.cli import cli
from zenml.client import Client


def test_model_list(clean_client: "Client"):
    """Test that zenml model list does not fail."""
    runner = CliRunner(mix_stderr=False)
    list_command = cli.commands["model"].commands["list"]
    result = runner.invoke(list_command)
    assert result.exit_code == 0, result.stderr


def test_model_create_short_names(clean_client: "Client"):
    """Test that zenml model create does not fail with short names."""
    runner = CliRunner(mix_stderr=False)
    create_command = cli.commands["model"].commands["register"]
    model_name = PREFIX + str(uuid4())
    result = runner.invoke(
        create_command,
        args=[
            "-n",
            model_name,
            "-l",
            "a",
            "-d",
            "b",
            "-a",
            "c",
            "-u",
            "d",
            "--tradeoffs",
            "f",
            "-e",
            "g",
            "--limitations",
            "e",
            "-t",
            "i",
            "-t",
            "j",
            "-t",
            "k",
            "-s",
            "true",
        ],
    )
    assert result.exit_code == 0, result.stderr

    model = clean_client.get_model(model_name)
    assert model.name == model_name
    assert model.license == "a"
    assert model.description == "b"
    assert model.audience == "c"
    assert model.use_cases == "d"
    assert model.trade_offs == "f"
    assert model.ethics == "g"
    assert model.limitations == "e"
    assert model.save_models_to_registry
    assert {t.name for t in model.tags} == {"i", "j", "k"}


def test_model_create_full_names(clean_client: "Client"):
    """Test that zenml model create does not fail with full names."""
    runner = CliRunner(mix_stderr=False)
    create_command = cli.commands["model"].commands["register"]
    model_name = PREFIX + str(uuid4())
    result = runner.invoke(
        create_command,
        args=[
            "--name",
            model_name,
            "--license",
            "a",
            "--description",
            "b",
            "--audience",
            "c",
            "--use-cases",
            "d",
            "--tradeoffs",
            "f",
            "--ethical",
            "g",
            "--limitations",
            "e",
            "--tag",
            "i",
            "--tag",
            "j",
            "--tag",
            "k",
            "--save-models-to-registry",
            "false",
        ],
    )
    assert result.exit_code == 0, result.stderr

    model = clean_client.get_model(model_name)
    assert model.name == model_name
    assert model.license == "a"
    assert model.description == "b"
    assert model.audience == "c"
    assert model.use_cases == "d"
    assert model.trade_offs == "f"
    assert model.ethics == "g"
    assert model.limitations == "e"
    assert not model.save_models_to_registry
    assert {t.name for t in model.tags} == {"i", "j", "k"}


def test_model_create_only_required(clean_client: "Client"):
    """Test that zenml model create does not fail."""
    runner = CliRunner(mix_stderr=False)
    create_command = cli.commands["model"].commands["register"]
    model_name = PREFIX + str(uuid4())
    result = runner.invoke(
        create_command,
        args=["--name", model_name],
    )
    assert result.exit_code == 0, result.stderr

    model = clean_client.get_model(model_name)
    assert model.name == model_name
    assert model.license is None
    assert model.description is None
    assert model.audience is None
    assert model.use_cases is None
    assert model.trade_offs is None
    assert model.ethics is None
    assert model.limitations is None
    assert model.save_models_to_registry
    assert len(model.tags) == 0


def test_model_update(clean_client: "Client"):
    """Test that zenml model update does not fail."""
    clean_client.create_model(name=NAME)
    runner = CliRunner(mix_stderr=False)
    update_command = cli.commands["model"].commands["update"]
    result = runner.invoke(
        update_command,
        args=[NAME, "--tradeoffs", "foo", "-t", "a"],
    )
    assert result.exit_code == 0, result.stderr

    model = clean_client.get_model(NAME)
    assert model.trade_offs == "foo"
    assert {t.name for t in model.tags} == {"a"}
    assert model.description is None

    result = runner.invoke(
        update_command,
        args=[NAME, "-d", "bar", "-r", "a", "-t", "b", "-s", "false"],
    )
    assert result.exit_code == 0, result.stderr

    model = clean_client.get_model(NAME)
    assert model.trade_offs == "foo"
    assert {t.name for t in model.tags} == {"b"}
    assert model.description == "bar"
    assert not model.save_models_to_registry


def test_model_create_without_required_fails(clean_client: "Client"):
    """Test that zenml model create fails."""
    runner = CliRunner(mix_stderr=False)
    create_command = cli.commands["model"].commands["register"]
    result = runner.invoke(
        create_command,
    )
    assert result.exit_code != 0, result.stderr


def test_model_delete_found(clean_client: "Client"):
    """Test that zenml model delete does not fail."""
    runner = CliRunner(mix_stderr=False)
    name = PREFIX + str(uuid4())
    create_command = cli.commands["model"].commands["register"]
    runner.invoke(
        create_command,
        args=["--name", name],
    )
    delete_command = cli.commands["model"].commands["delete"]
    result = runner.invoke(
        delete_command,
        args=[name, "-y"],
    )
    assert result.exit_code == 0, result.stderr


def test_model_delete_not_found(clean_client: "Client"):
    """Test that zenml model delete fail."""
    runner = CliRunner(mix_stderr=False)
    name = PREFIX + str(uuid4())
    delete_command = cli.commands["model"].commands["delete"]
    result = runner.invoke(
        delete_command,
        args=[name],
    )
    assert result.exit_code != 0, result.stderr


def test_model_version_list(clean_client: "Client"):
    """Test that zenml model version list does not fail."""
    clean_client.create_model(name=NAME)
    runner = CliRunner(mix_stderr=False)
    list_command = cli.commands["model"].commands["version"].commands["list"]
    result = runner.invoke(list_command, args=[f"--model={NAME}"])
    assert result.exit_code == 0, result.stderr


def test_model_version_delete_found(clean_client: "Client"):
    """Test that zenml model version delete does not fail."""
    runner = CliRunner(mix_stderr=False)
    model_name = PREFIX + str(uuid4())
    model_version_name = PREFIX + str(uuid4())
    model = clean_client.create_model(
        name=model_name,
    )
    clean_client.create_model_version(
        name=model_version_name,
        model_name_or_id=model.id,
    )
    delete_command = (
        cli.commands["model"].commands["version"].commands["delete"]
    )
    result = runner.invoke(
        delete_command,
        args=[model_name, model_version_name, "-y"],
    )
    assert result.exit_code == 0, result.stderr


def test_model_version_delete_not_found(clean_client: "Client"):
    """Test that zenml model version delete fail."""
    runner = CliRunner(mix_stderr=False)
    model_name = PREFIX + str(uuid4())
    model_version_name = PREFIX + str(uuid4())
    clean_client.create_model(
        name=model_name,
    )
    delete_command = (
        cli.commands["model"].commands["version"].commands["delete"]
    )
    result = runner.invoke(
        delete_command,
        args=[model_name, model_version_name, "-y"],
    )
    assert result.exit_code != 0, result.stderr


def test_model_version_links_list(clean_client_with_models: "Client"):
    """Test that zenml model version link lists do not fail."""
    runner = CliRunner(mix_stderr=False)
    for command in (
        "data_artifacts",
        "deployment_artifacts",
        "model_artifacts",
        "runs",
    ):
        list_command = cli.commands["model"].commands[command]
        result = runner.invoke(
            list_command,
            args=[NAME],
        )
        assert result.exit_code == 0, result.stderr


def test_model_version_update(clean_client: "Client"):
    """Test that zenml model version stage update pass."""
    clean_client.create_model(name=NAME)
    clean_client.create_model_version(model_name_or_id=NAME)
    runner = CliRunner(mix_stderr=False)
    update_command = (
        cli.commands["model"].commands["version"].commands["update"]
    )
    result = runner.invoke(
        update_command,
        args=[NAME, "1", "-s", "production"],
    )
    assert result.exit_code == 0, result.stderr

```

File: /Users/safoine/zenml-io/zenml/.github/workflows/validate-quarantine.yml
```yml
---
name: Validate test quarantine
on:
  pull_request:
    paths: [.github/quarantined-tests.yml, scripts/validate_quarantine.py]
  workflow_dispatch:
jobs:
  validate-quarantine:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
      - name: Set up Python
        uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405  # v6.2.0
        with:
          python-version: '3.11'
      - name: Install validation dependencies
        run: python -m pip install pyyaml
      - name: Validate quarantine registry
        run: python scripts/validate_quarantine.py

```

File: /Users/safoine/zenml-io/zenml/offload-modal-server-mysql.toml
```toml
[offload]
max_parallel = 20
test_timeout_secs = 960
max_batch_duration_secs = 320
sandbox_project_root = "/app"

[provider]
type = "default"
prepare_command = "uv run @modal_sandbox.py prepare Dockerfile.ci --cached --include-cwd --sandbox-init-cmd 'cd /app && pip install --no-deps -e . -q'"
create_command = "uv run @modal_sandbox.py create {image_id} --cpu 4 --memory-gb 8 --env PYTHONDONTWRITEBYTECODE=1 --env PYTHONUNBUFFERED=1 --env ZENML_DEBUG=true --env ZENML_ANALYTICS_OPT_IN=false --env AUTO_OPEN_DASHBOARD=false --env MODAL_CI_SERVER_URL=${MODAL_CI_SERVER_URL} --env MODAL_CI_SERVER_USERNAME=${MODAL_CI_SERVER_USERNAME} --env MODAL_CI_SERVER_PASSWORD=${MODAL_CI_SERVER_PASSWORD} --env MODAL_TOKEN_SECRET=${MODAL_TOKEN_SECRET} --env ZENML_CI_CHECKOUT_REF=${ZENML_CI_CHECKOUT_REF}"
exec_command = "python3 @modal_sandbox.py exec {sandbox_id} {command}"
destroy_command = "uv run @modal_sandbox.py destroy {sandbox_id}"
download_command = "printf '[offload] exec_and_fetch returned no inline artifacts; falling back to download_command.\\n' >&2; python3 @modal_sandbox.py download {sandbox_id} {paths}"
exec_and_fetch_command = "python3 @modal_sandbox.py exec-and-fetch {sandbox_id} {command} --fetch {fetch}"
timeout_secs = 960

[framework]
type = "pytest"
paths = []
command = "python scripts/ci/run_mixed_environment_pytest.py -p no:pytest_postgresql"
run_args = "--no-provision --environment default -p no:randomly -p no:rerunfailures"

[groups.unit]
retry_count = 0
filters = "tests/unit"

[groups.integration]
retry_count = 0
filters = "tests/integration --ignore=tests/integration/examples -m 'not slow'"

[report]
output_dir = ".ci/offload"

```

File: /Users/safoine/zenml-io/zenml/tests/unit/scripts/ci/test_run_mixed_environment_pytest.py
```py
"""Tests for mixed-environment pytest routing."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.ci import run_mixed_environment_pytest


def test_extract_args_routes_test_ids_and_environment() -> None:
    """Wrapper strips the caller environment and keeps common pytest args."""
    common_args, test_ids, junit_path = (
        run_mixed_environment_pytest._extract_args(
            [
                "-p",
                "no:pytest_postgresql",
                "--environment",
                "default",
                "--junitxml=/tmp/result.xml",
                "tests/unit/test_a.py::test_a",
                "tests/integration/test_b.py::test_b",
            ]
        )
    )

    assert common_args == ["-p", "no:pytest_postgresql"]
    assert test_ids == [
        "tests/unit/test_a.py::test_a",
        "tests/integration/test_b.py::test_b",
    ]
    assert junit_path == Path("/tmp/result.xml")


def test_collect_only_passes_through_to_pytest() -> None:
    """Offload discovery does not provide a JUnit path to the wrapper."""
    completed_process = Mock(returncode=0)

    with patch.object(
        run_mixed_environment_pytest.subprocess,
        "run",
        return_value=completed_process,
    ) as run_mock:
        exit_code = run_mixed_environment_pytest.main(
            ["-p", "no:pytest_postgresql", "--collect-only", "tests/unit"]
        )

    assert exit_code == 0
    run_mock.assert_called_once_with(
        [
            run_mixed_environment_pytest.sys.executable,
            "-m",
            "pytest",
            "-p",
            "no:pytest_postgresql",
            "--collect-only",
            "tests/unit",
        ]
    )


def test_merge_junit_combines_testcases(tmp_path: Path) -> None:
    """Split pytest invocations still produce one offload JUnit file."""
    first = tmp_path / "first.xml"
    first.write_text(
        '<testsuite tests="1" failures="0" errors="0" skipped="0" time="1">'
        '<testcase classname="a" name="test_a" time="1" />'
        "</testsuite>"
    )
    second = tmp_path / "second.xml"
    second.write_text(
        '<testsuite tests="1" failures="1" errors="0" skipped="0" time="2">'
        '<testcase classname="b" name="test_b" time="2"><failure /></testcase>'
        "</testsuite>"
    )
    output = tmp_path / "merged.xml"

    run_mixed_environment_pytest._merge_junit(output, [first, second])

    root = ET.parse(output).getroot()
    assert root.attrib["tests"] == "2"
    assert root.attrib["failures"] == "1"
    assert len(list(root.iter("testcase"))) == 2

```

File: /Users/safoine/zenml-io/zenml/tests/harness/cfg/deployments.yaml
```yaml
---
# A list of ZenML deployments, either local or remote (external), that
# can be included in test environments to be used to run automated tests or
# passed to pytest directly using the `--deployment` command line argument.
#
# Local deployments are provisioned by the test framework on the fly in the test
# preparation phase, and are torn down after the tests have finished. Remote
# deployments are assumed to be already provisioned and ready to use.
#
# A deployment has the following properties:
#
# - name: The name of the deployment. This is used to refer to the deployment
#   in test environments and in the test framework CLI. It is also used to
#   generate unique names for resources that may need to be deployed locally.
# - server: The method used to deploy the ZenML server used in the tests. It can
#   take one of the following values:
#   -  none: A deployment that uses a local client that is not connected to
#      any ZenML Server. The client connects directly to a database, which is
#      either local or remote.
#   -  local: A deployment that uses a ZenML server running locally as a
#      daemon process (similar to running `zenml login --local`). The test
#      framework takes care of starting and stopping the server process.
#   -  docker: A deployment that uses a ZenML server running locally as a
#      docker container (similar to running `zenml login --local --docker`). The
#      test framework takes care of starting and stopping the server container. It
#      also takes care of building and using a `zenml-server` Docker image with
#      the latest code available in the local zenml code repository clone.
#      When used with a dockerized database server like MySQL or MariaDB, the
#      test framework uses Docker Compose to start and stop both containers.
#   -  external: A deployment that uses a ZenML server running remotely. The
#      test framework will not provision or manage this server.
#      The test framework will only connect to the server and run tests against
#      it. A `config` section must be provided in the deployment configuration
#      to specify the connection details.
# - database: The type of database used by the deployment. It can take one of
#   the following values:
#   -  sqlite: Indicates that the default SQLite database is used. For `local`
#      and `docker` server deployments, this is equivalent to deploying the
#      ZenML server with `zenml login --local` or `zenml login --local --docker`.
#   -  mysql: Uses a MySQL database server running locally as a Docker
#      container.
#   -  mariadb: Uses a MariaDB database server running locally as a Docker
#      container.
#   -  external: A 3rd party ZenML server that is installed and maintained
#      externally. The test framework will not provision or manage this server.
#      The test framework will only connect to the server and run tests against
#      it. A `config` section must be provided in the deployment configuration
#      to specify the connection details.
# - config: A dictionary of configuration parameters that are used to initialize
#   the ZenML store to connect to a remote ZenML server or database. The values
#   may reference secrets that are defined in the test configuration or as
#   environment variables using the `{{SECRET_NAME_OR_ENV_VAR}}` syntax.
# - disabled: A boolean flag that can be used to administratively disable a
#   deployment. A disabled deployment will not be checked for operational
#   readiness and will not be usable to run tests. This is useful to temporarily
#   disable a deployment that is not operational without having to remove it
#   from the configuration.
# - capabilities: A list of custom capabilities that the deployment supports or
#   does not support. This is compared against the capabilities required by the
#   tests to determine if the deployment is suitable to run the tests. A `true`
#   value indicates that the deployment supports the capability, while a `false`
#   value indicates that it doesn't.
#
deployments:
  - name: default
    description: >-
      Default deployment.
    server: none
    database: sqlite
  - name: client-mysql
    description: >-
      Local client connected directly to MySQL running in container.
    server: none
    database: mysql
  - name: client-mariadb
    description: >-
      Local client connected directly to MariaDB running in container.
    server: none
    database: mariadb

    # IMPORTANT: don't use this with pytest auto-provisioning. Running forked
    # daemons in pytest leads to serious issues because the whole test process
    # is forked. As a workaround, the deployment can be started separately,
    # before pytest is invoked.
  - name: local-server
    description: >-
      Local ZenML server running as daemon process using the default SQLite
      database.
    server: local
    database: sqlite
    capabilities:
      server: true
  - name: docker-server
    description: >-
      Local ZenML server running in docker using the default SQLite database.
    server: docker
    database: sqlite
    capabilities:
      server: true
  - name: docker-server-mysql
    description: >-
      Local ZenML server and MySQL both running in docker with docker-compose.
    server: docker
    database: mysql
    capabilities:
      server: true
  - name: docker-server-mariadb
    description: >-
      Local ZenML server and MariaDB both running in docker with docker-compose.
    server: docker
    database: mariadb
    capabilities:
      server: true
  - name: github-actions-server
    description: >-
      Local ZenML server and MariaDB both running in docker with docker-compose.
    server: external
    database: external
    capabilities:
      server: true
    config:
      url: http://127.0.0.1:8080/
      username: default
      password: ''
  - name: modal-mysql-server
    description: >-
      Modal-hosted ZenML server backed by MySQL for CI integration tests.
    server: external
    database: external
    capabilities:
      server: true
    config:
      url: '{{MODAL_CI_SERVER_URL}}'
      username: '{{MODAL_CI_SERVER_USERNAME}}'
      password: '{{MODAL_CI_SERVER_PASSWORD}}'

```

File: /Users/safoine/zenml-io/zenml/scripts/ci_modal_mysql_sandbox.py
```py
#!/usr/bin/env python3
"""Manage the per-run Modal MySQL CI sandbox."""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import os
import secrets
import shlex
import string
import textwrap
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

GITHUB_OUTPUT = os.environ.get("GITHUB_OUTPUT")
DEFAULT_USERNAME = "default"
SERVER_PORT = 8080
START_TIMEOUT_SECONDS = 600
SANDBOX_TIMEOUT_SECONDS = 3600


def _is_sensitive_output_name(name: str) -> bool:
    """Return whether an output name likely carries sensitive data."""
    lowered = name.lower()
    return any(
        token in lowered for token in ("password", "token", "secret", "key")
    )


def _write_output(name: str, value: str) -> None:
    """Write a GitHub Actions output."""
    if not GITHUB_OUTPUT:
        safe_value = (
            "***REDACTED***" if _is_sensitive_output_name(name) else value
        )
        print(f"{name}={safe_value}")
        return
    with Path(GITHUB_OUTPUT).open("a", encoding="utf-8") as output_file:
        output_file.write(f"{name}={value}\n")


def _get_required_env(name: str) -> str:
    """Read a required environment variable."""
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Environment variable {name} is required")
    return value


def _generate_password() -> str:
    """Generate a URL-safe password for internal sandbox services."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(32))


def _password_context() -> str:
    """Return the stable per-run context used to derive the server password."""
    return ":".join(
        [
            _get_required_env("GITHUB_REPOSITORY"),
            os.environ.get("ZENML_CI_CHECKOUT_REF")
            or _get_required_env("GITHUB_SHA"),
            os.environ.get("GITHUB_RUN_ID", "local"),
        ]
    )


def derive_server_password() -> str:
    """Derive the per-run server password without storing it as job output."""
    seed = _get_required_env("MODAL_TOKEN_SECRET").encode("utf-8")
    digest = hmac.new(
        seed, _password_context().encode("utf-8"), hashlib.sha256
    ).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")[:32]


def _build_server_command(repository: str, checkout_ref: str) -> str:
    """Build the command that runs inside the Modal sandbox."""
    quoted_repository = shlex.quote(repository)
    quoted_checkout_ref = shlex.quote(checkout_ref)
    return textwrap.dedent(
        f"""
        set -euo pipefail

        mkdir -p /workspace
        service mariadb start || service mysql start
        for _ in $(seq 1 60); do
          mysqladmin ping --silent && break
          sleep 1
        done

        mysql -uroot <<SQL
        CREATE DATABASE IF NOT EXISTS zenml;
        CREATE USER IF NOT EXISTS 'zenml'@'%'
          IDENTIFIED BY '${{ZENML_DB_PASSWORD}}';
        CREATE USER IF NOT EXISTS 'zenml'@'localhost'
          IDENTIFIED BY '${{ZENML_DB_PASSWORD}}';
        GRANT ALL PRIVILEGES ON zenml.* TO 'zenml'@'%';
        GRANT ALL PRIVILEGES ON zenml.* TO 'zenml'@'localhost';
        FLUSH PRIVILEGES;
        SQL

        git clone --depth 1 https://github.com/{quoted_repository}.git /workspace/zenml
        cd /workspace/zenml
        git fetch --depth 1 origin {quoted_checkout_ref}
        git checkout FETCH_HEAD

        uv venv /workspace/venv
        . /workspace/venv/bin/activate
        uv pip install -e '.[server]'

        export ZENML_ANALYTICS_OPT_IN=false
        export ZENML_DEBUG=true
        export ZENML_STORE_URL=mysql://zenml:${{ZENML_DB_PASSWORD}}@127.0.0.1/zenml
        export ZENML_SERVER_DEPLOYMENT_TYPE=docker
        export ZENML_SERVER_AUTO_ACTIVATE=True
        export ZENML_SERVER_AUTO_CREATE_DEFAULT_USER=True
        export ZENML_DEFAULT_USER_NAME={DEFAULT_USERNAME}
        export ZENML_DEFAULT_USER_PASSWORD=${{ZENML_DEFAULT_USER_PASSWORD}}
        export AUTO_OPEN_DASHBOARD=false

        uvicorn zenml.zen_server.zen_server_api:app \
          --no-server-header \
          --proxy-headers \
          --forwarded-allow-ips '*' \
          --host 0.0.0.0 \
          --port {SERVER_PORT}
        """
    ).strip()


def _get_modal() -> Any:
    """Import Modal with an actionable error message."""
    try:
        import modal
    except ImportError as exc:
        raise RuntimeError(
            "The 'modal' package is required. Install it with "
            "`python -m pip install --upgrade 'modal>=1.0.0'`."
        ) from exc
    return modal


def _modal_app() -> Any:
    """Return the Modal app used by CI sandboxes."""
    modal = _get_modal()
    return modal.App.lookup("zenml-ci-mysql-sandbox", create_if_missing=True)


def _modal_image() -> Any:
    """Return the Modal image used by CI sandboxes."""
    modal = _get_modal()
    return (
        modal.Image.debian_slim(python_version="3.11")
        .apt_install(
            "default-mysql-server",
            "default-libmysqlclient-dev",
            "build-essential",
            "pkg-config",
            "git",
            "curl",
        )
        .pip_install("uv")
    )


def _create_modal_sandbox(command: str, environment: dict[str, str]) -> Any:
    """Create a Modal sandbox running the ZenML server command."""
    modal = _get_modal()
    image = _modal_image()
    app = _modal_app()

    try:
        return modal.Sandbox.create(
            "bash",
            "-lc",
            command,
            app=app,
            image=image,
            env=environment,
            encrypted_ports=[SERVER_PORT],
            timeout=SANDBOX_TIMEOUT_SECONDS,
        )
    except TypeError as exc:
        raise RuntimeError(
            "This Modal SDK does not support the Sandbox.create arguments used "
            "by the CI sandbox. Please use a Modal version that supports "
            "encrypted_ports on sandboxes."
        ) from exc


def _get_tunnel_url(sandbox: Any) -> str:
    """Wait for Modal to expose the ZenML server tunnel."""
    deadline = time.time() + START_TIMEOUT_SECONDS
    while time.time() < deadline:
        return_code = sandbox.poll()
        if return_code is not None:
            raise RuntimeError(
                f"Modal sandbox exited before becoming ready: {return_code}"
            )

        tunnels = sandbox.tunnels()
        tunnel = tunnels.get(SERVER_PORT) if tunnels else None
        url = getattr(tunnel, "url", None) if tunnel else None
        if url:
            return str(url).rstrip("/")
        time.sleep(5)

    raise RuntimeError("Timed out waiting for Modal sandbox tunnel")


def _wait_until_ready(server_url: str) -> None:
    """Wait until the ZenML server responds to readiness checks."""
    deadline = time.time() + START_TIMEOUT_SECONDS
    ready_url = f"{server_url}/ready"
    last_error: Exception | None = None

    while time.time() < deadline:
        try:
            with urllib.request.urlopen(ready_url, timeout=10) as response:
                if response.status == 200:
                    return
        except (
            ConnectionError,
            OSError,
            urllib.error.URLError,
            TimeoutError,
        ) as exc:
            last_error = exc
        time.sleep(5)

    raise RuntimeError(
        f"Timed out waiting for ZenML server readiness at {ready_url}: "
        f"{last_error}"
    )


def start() -> None:
    """Start the per-run Modal sandbox and emit connection details."""
    if os.environ.get("ZENML_CI_MODAL_DISABLED") == "true":
        _write_output("server_url", "")
        _write_output("server_username", "")
        _write_output("sandbox_id", "")
        return

    repository = _get_required_env("GITHUB_REPOSITORY")
    checkout_ref = os.environ.get(
        "ZENML_CI_CHECKOUT_REF"
    ) or _get_required_env("GITHUB_SHA")
    password = derive_server_password()
    db_password = _generate_password()
    sandbox = _create_modal_sandbox(
        _build_server_command(repository, checkout_ref),
        environment={
            "ZENML_DEFAULT_USER_PASSWORD": password,
            "ZENML_DB_PASSWORD": db_password,
        },
    )
    try:
        server_url = _get_tunnel_url(sandbox)
        _wait_until_ready(server_url)
    except (
        ConnectionError,
        OSError,
        RuntimeError,
        TimeoutError,
        urllib.error.URLError,
    ):
        sandbox.terminate()
        raise

    _write_output("server_url", server_url)
    _write_output("server_username", DEFAULT_USERNAME)
    _write_output("sandbox_id", sandbox.object_id)


def stop(sandbox_id: str) -> None:
    """Stop the per-run Modal sandbox."""
    if not sandbox_id:
        return

    modal = _get_modal()
    sandbox = modal.Sandbox.from_id(sandbox_id)
    sandbox.terminate()


def warm_image() -> None:
    """Build and warm the Modal image used by CI sandboxes."""
    _modal_image().build(app=_modal_app())


def main() -> None:
    """Run the CLI."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("start")
    subparsers.add_parser("warm-image")
    stop_parser = subparsers.add_parser("stop")
    stop_parser.add_argument("--sandbox-id", required=True)
    args = parser.parse_args()

    if args.command == "start":
        start()
    elif args.command == "warm-image":
        warm_image()
    elif args.command == "stop":
        stop(args.sandbox_id)


if __name__ == "__main__":
    main()

```

File: /Users/safoine/zenml-io/zenml/scripts/ci/compute_offload_cache_keys.py
```py
"""Compute cache keys for offloaded CI lanes."""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tomllib

SUPPORTED_LANES = {"default", "modal-server-mysql"}
ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class OffloadCacheKeys:
    """Cache key family used by the offload workflow."""

    uv_key: str
    uv_restore_prefix: str
    legacy_uv_restore_prefix: str
    image_key: str
    image_restore_prefix: str
    legacy_image_restore_prefix: str
    junit_restore_key: str
    junit_restore_prefix: str
    legacy_junit_restore_prefix: str
    junit_save_key: str


def _read_file(path: Path) -> bytes:
    return path.read_bytes() if path.exists() else b""


def _hash_parts(parts: list[tuple[str, str | bytes]]) -> str:
    digest = hashlib.sha256()
    for name, value in parts:
        digest.update(name.encode())
        digest.update(b"\0")
        if isinstance(value, str):
            value = value.encode()
        digest.update(value)
        digest.update(b"\0")
    return digest.hexdigest()


def _load_toml(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _config_for_lane(lane: str) -> str:
    if lane == "default":
        return "offload.toml"
    if lane == "modal-server-mysql":
        return "offload-modal-server-mysql.toml"
    raise ValueError(
        f"Unsupported offload lane '{lane}'. Expected one of: "
        f"{', '.join(sorted(SUPPORTED_LANES))}."
    )


def _uv_fingerprint(root: Path) -> str:
    return _hash_parts(
        [
            ("pyproject.toml", _read_file(root / "pyproject.toml")),
            ("uv.lock", _read_file(root / "uv.lock")),
            (
                "scripts/ci/modal_sandbox_requirements.txt",
                _read_file(root / "scripts/ci/modal_sandbox_requirements.txt"),
            ),
        ]
    )


def _image_fingerprint(root: Path) -> str:
    default_config = _load_toml(root / "offload.toml")
    mysql_config = _load_toml(root / "offload-modal-server-mysql.toml")
    parts: list[tuple[str, str | bytes]] = [
        ("Dockerfile.ci", _read_file(root / "Dockerfile.ci")),
        (
            "Dockerfile.ci.dockerignore",
            _read_file(root / "Dockerfile.ci.dockerignore"),
        ),
        ("pyproject.toml", _read_file(root / "pyproject.toml")),
        ("uv.lock", _read_file(root / "uv.lock")),
        (
            "scripts/ci/export_offload_integration_requirements.py",
            _read_file(
                root / "scripts/ci/export_offload_integration_requirements.py"
            ),
        ),
        (
            "src/zenml/cli/integration.py",
            _read_file(root / "src/zenml/cli/integration.py"),
        ),
        (
            "src/zenml/integrations/integration.py",
            _read_file(root / "src/zenml/integrations/integration.py"),
        ),
        (
            "src/zenml/integrations/registry.py",
            _read_file(root / "src/zenml/integrations/registry.py"),
        ),
        (
            "offload.toml:provider.prepare_command",
            default_config["provider"]["prepare_command"],
        ),
        (
            "offload-modal-server-mysql.toml:provider.prepare_command",
            mysql_config["provider"]["prepare_command"],
        ),
        (
            "offload.toml:offload.sandbox_project_root",
            default_config["offload"]["sandbox_project_root"],
        ),
        (
            "offload-modal-server-mysql.toml:offload.sandbox_project_root",
            mysql_config["offload"]["sandbox_project_root"],
        ),
    ]
    for path in sorted(
        (root / "src/zenml/integrations").glob("*/__init__.py")
    ):
        parts.append((str(path.relative_to(root)), _read_file(path)))
    return _hash_parts(parts)


def _junit_fingerprint(root: Path, lane: str) -> str:
    config_name = _config_for_lane(lane)
    config = _load_toml(root / config_name)
    parts: list[tuple[str, str | bytes]] = [
        ("config_filename", config_name),
        ("framework.command", config["framework"]["command"]),
        ("framework.run_args", config["framework"]["run_args"]),
    ]
    for group_name in sorted(config["groups"]):
        parts.append(
            (
                f"groups.{group_name}.filters",
                config["groups"][group_name]["filters"],
            )
        )
    return _hash_parts(parts)


def compute_offload_cache_keys(
    *,
    lane: str,
    runner_os: str,
    python_version: str,
    run_id: str,
    run_attempt: str,
    root: Path = ROOT,
) -> OffloadCacheKeys:
    """Compute deterministic offload cache keys."""
    if lane not in SUPPORTED_LANES:
        _config_for_lane(lane)

    uv_fingerprint = _uv_fingerprint(root)
    image_fingerprint = _image_fingerprint(root)
    junit_fingerprint = _junit_fingerprint(root, lane)

    uv_prefix = f"offload-uv-v1-{runner_os}-py{python_version}-"
    image_prefix = f"offload-image-v2-{runner_os}-"
    junit_prefix = f"offload-junit-v2-{lane}-{junit_fingerprint}-"

    return OffloadCacheKeys(
        uv_key=f"{uv_prefix}{uv_fingerprint}",
        uv_restore_prefix=uv_prefix,
        legacy_uv_restore_prefix=f"uv-{runner_os}-{python_version}-",
        image_key=f"{image_prefix}{image_fingerprint}",
        image_restore_prefix=image_prefix,
        legacy_image_restore_prefix=f"offload-image-v1-{runner_os}-{python_version}-",
        junit_restore_key=junit_prefix,
        junit_restore_prefix=junit_prefix,
        legacy_junit_restore_prefix=f"offload-junit-{lane}-{runner_os}-",
        junit_save_key=f"{junit_prefix}{run_id}-{run_attempt}",
    )


def _write_github_outputs(keys: OffloadCacheKeys) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as output_file:
        for field_name, value in keys.__dict__.items():
            output_file.write(f"{field_name}={value}\n")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lane", required=True)
    parser.add_argument("--runner-os", required=True)
    parser.add_argument("--python-version", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-attempt", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI."""
    args = _build_parser().parse_args(argv)
    try:
        keys = compute_offload_cache_keys(
            lane=args.lane,
            runner_os=args.runner_os,
            python_version=args.python_version,
            run_id=args.run_id,
            run_attempt=args.run_attempt,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print("Computed offload cache keys:")
    print(f"  uv_key={keys.uv_key}")
    print(f"  image_key={keys.image_key}")
    print(f"  junit_restore_prefix={keys.junit_restore_prefix}")
    print(f"  junit_save_key={keys.junit_save_key}")
    _write_github_outputs(keys)
    return 0


if __name__ == "__main__":
    sys.exit(main())

```

File: /Users/safoine/zenml-io/zenml/scripts/ci/modal_sandbox_requirements.txt
```txt
modal==1.4.1
click>=8.0
dockerfile-parse>=2.0.0

```

File: /Users/safoine/zenml-io/zenml/scripts/publish_ci_qualification.py
```py
#!/usr/bin/env python3
"""Publish slow-CI qualification results to GitHub Checks."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import urllib.request
from pathlib import Path

from ci_matrix_hash import compute_matrix_hash

CHECK_NAME = "ci-slow-develop/qualification"


def _github_request(url: str, method: str, payload: dict) -> dict:
    token = os.environ["GITHUB_TOKEN"]
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _develop_sha() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()


def main() -> None:
    """Run the CLI."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--conclusion", choices=["success", "failure"], required=True
    )
    parser.add_argument("--incident", action="store_true")
    args = parser.parse_args()

    repository = os.environ["GITHUB_REPOSITORY"]
    owner, repo = repository.split("/", 1)
    run_id = os.environ["GITHUB_RUN_ID"]
    server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    completed_at = (
        dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    )
    matrix_hash = compute_matrix_hash(
        Path(".github/workflows/ci-slow-develop.yml")
    )
    sha = _develop_sha()
    run_url = f"{server_url}/{repository}/actions/runs/{run_id}"

    title = (
        "Slow CI passed on develop"
        if args.conclusion == "success"
        else "Slow CI failed on develop"
    )
    summary = "\n".join(
        [
            f"| Field | Value |",
            f"| --- | --- |",
            f"| SHA | `{sha}` |",
            f"| Run | [{run_id}]({run_url}) |",
            f"| Matrix hash | `{matrix_hash}` |",
            f"| Completed at | `{completed_at}` |",
        ]
    )

    _github_request(
        f"https://api.github.com/repos/{owner}/{repo}/check-runs",
        "POST",
        {
            "name": CHECK_NAME,
            "head_sha": sha,
            "status": "completed",
            "conclusion": args.conclusion,
            "completed_at": completed_at,
            "external_id": f"{run_id}:{matrix_hash}:{completed_at}",
            "details_url": run_url,
            "output": {"title": title, "summary": summary},
        },
    )

    if args.incident and args.conclusion == "failure":
        today = dt.datetime.now(dt.timezone.utc).date().isoformat()
        body = "\n".join(
            [
                f"Nightly slow CI failed on `{sha}`.",
                "",
                f"Workflow run: {run_url}",
                f"Matrix hash: `{matrix_hash}`",
                "",
                (
                    "Please triage failing jobs, identify the suspect PR "
                    "range from the last green qualification, and update "
                    "this issue with the owner and remediation plan."
                ),
            ]
        )
        _github_request(
            f"https://api.github.com/repos/{owner}/{repo}/issues",
            "POST",
            {
                "title": f"develop is red — {today} — slow CI failed",
                "body": body,
                "labels": ["develop-red", "incident", "priority/critical"],
            },
        )


if __name__ == "__main__":
    main()

```

File: /Users/safoine/zenml-io/zenml/.github/workflows/linux-fast-offload.yml
```yml
---
name: Linux fast offload
on:
  workflow_call:
    inputs:
      backend:
        description: Offload backend to use
        type: string
        required: false
        default: modal
      python-version:
        description: Python version used by fallback runner jobs
        type: string
        required: false
        default: '3.13'
      use-offload:
        description: Attempt remote offload before falling back
        type: boolean
        required: false
        default: true
      test_environment:
        description: Test environment to execute remotely
        type: string
        required: false
        default: default
  workflow_dispatch:
    inputs:
      backend:
        description: Offload backend to use
        type: choice
        options: [modal]
        required: false
        default: modal
      python-version:
        description: Python version used by fallback runner jobs
        type: choice
        options: ['3.11', '3.12', '3.13']
        required: false
        default: '3.13'
      use-offload:
        description: Attempt remote offload before falling back
        type: boolean
        required: false
        default: true
      test_environment:
        description: Test environment to execute remotely
        type: choice
        options: [default, modal-server-mysql]
        required: false
        default: default
jobs:
  offload-fast-tests:
    name: offload-fast-tests
    runs-on: ubuntu-latest
    timeout-minutes: 75
    outputs:
      offload-infra-failed: ${{ steps.classify.outputs.offload_infra_failed }}
      tests-failed: ${{ steps.classify.outputs.tests_failed }}
      conclusion: ${{ steps.classify.outputs.conclusion }}
    env:
      MODAL_TOKEN_ID: ${{ secrets.MODAL_TOKEN_ID }}
      MODAL_TOKEN_SECRET: ${{ secrets.MODAL_TOKEN_SECRET }}
      ZENML_ANALYTICS_OPT_IN: false
      ZENML_DEBUG: 1
      ZENML_ENABLE_RICH_TRACEBACK: false
      PYTHONDONTWRITEBYTECODE: 1
      UV_CACHE_DIR: /opt/uv-cache
      TMPDIR: /opt/tmp
      TMP: /opt/tmp
      TEMP: /opt/tmp
    steps:
      - name: Checkout code
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
        with:
          fetch-depth: 0
      - name: Set up Python
        uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405  # v6.2.0
        with:
          python-version: ${{ inputs.python-version }}
      - name: Prepare result directory
        run: mkdir -p .ci/offload
      - name: Prepare uv cache directories
        run: |
          sudo mkdir -p /opt/uv-cache /opt/tmp
          sudo chown -R "$USER:$USER" /opt/uv-cache /opt/tmp
      - name: Check offload eligibility
        id: eligibility
        env:
          BACKEND: ${{ inputs.backend }}
          USE_OFFLOAD: ${{ inputs.use-offload }}
        run: |
          set -euo pipefail
          eligible=true
          reason="eligible"
          if [ "$USE_OFFLOAD" != "true" ]; then
            eligible=false
            reason="offload disabled by input"
          elif [ "$BACKEND" != "modal" ]; then
            eligible=false
            reason="unsupported backend: $BACKEND"
          elif [ -z "${MODAL_TOKEN_ID}" ] || [ -z "${MODAL_TOKEN_SECRET}" ]; then
            eligible=false
            reason="Modal credentials unavailable"
          fi
          echo "eligible=$eligible" >> "$GITHUB_OUTPUT"
          echo "reason=$reason" >> "$GITHUB_OUTPUT"
          echo "$reason"
          echo "started_at=$(date +%s)" >> "$GITHUB_OUTPUT"
      - name: Compute offload cache keys
        id: cache-keys
        env:
          OFFLOAD_LANE: ${{ inputs.test_environment }}
          RUNNER_OS_NAME: ${{ runner.os }}
          PYTHON_VERSION: ${{ inputs.python-version }}
          GITHUB_RUN_ID_VALUE: ${{ github.run_id }}
          GITHUB_RUN_ATTEMPT_VALUE: ${{ github.run_attempt }}
        run: |
          python3 scripts/ci/compute_offload_cache_keys.py \
            --lane "$OFFLOAD_LANE" \
            --runner-os "$RUNNER_OS_NAME" \
            --python-version "$PYTHON_VERSION" \
            --run-id "$GITHUB_RUN_ID_VALUE" \
            --run-attempt "$GITHUB_RUN_ATTEMPT_VALUE"
      - name: Cache cargo/offload binary
        if: steps.eligibility.outputs.eligible == 'true'
        uses: actions/cache@27d5ce7f107fe9357f9df03efb73ab90386fccae  # v5.0.5
        with:
          path: |
            ~/.cargo/bin/offload
            ~/.cargo/bin/offload.rev
            ~/.cargo/registry
            ~/.cargo/git
          key: offload-${{ runner.os }}-a43298e03113c39e7c0bb4cf1d5f6f72d2c86584-v1
      - name: Restore offload uv cache
        id: restore-uv-cache
        if: steps.eligibility.outputs.eligible == 'true'
        uses: actions/cache/restore@27d5ce7f107fe9357f9df03efb73ab90386fccae  # v5.0.5
        with:
          path: /opt/uv-cache
          key: ${{ steps.cache-keys.outputs.uv_key }}
          restore-keys: |
            ${{ steps.cache-keys.outputs.uv_restore_prefix }}
            ${{ steps.cache-keys.outputs.legacy_uv_restore_prefix }}
      - name: Install driver dependencies
        id: setup
        if: steps.eligibility.outputs.eligible == 'true'
        continue-on-error: true
        env:
          OFFLOAD_GIT_REPO: https://github.com/safoinme/offload.git
          OFFLOAD_GIT_REV: a43298e03113c39e7c0bb4cf1d5f6f72d2c86584
        run: |
          set -euo pipefail
          echo "started_at=$(date +%s)" >> "$GITHUB_OUTPUT"
          trap 'echo "completed_at=$(date +%s)" >> "$GITHUB_OUTPUT"' EXIT
          python3 -m pip install --user "uv==0.8.22"
          python3 -m uv pip install --system -e ".[server,templates,dev]" -r scripts/ci/modal_sandbox_requirements.txt
          if ! command -v cargo >/dev/null 2>&1; then
            echo "cargo is required to install the pinned offload binary"
            exit 1
          fi
          installed_rev=""
          if [ -f ~/.cargo/bin/offload.rev ]; then
            installed_rev="$(cat ~/.cargo/bin/offload.rev)"
          fi
          if ! command -v offload >/dev/null 2>&1 || [ "$installed_rev" != "$OFFLOAD_GIT_REV" ]; then
            cargo install --git "$OFFLOAD_GIT_REPO" --rev "$OFFLOAD_GIT_REV" offload
            echo "$OFFLOAD_GIT_REV" > ~/.cargo/bin/offload.rev
          fi
          offload --version
      - name: Generate offload integration requirements
        if: steps.eligibility.outputs.eligible == 'true' && steps.setup.outcome ==
          'success'
        run: |
          python3 scripts/ci/export_offload_integration_requirements.py \
            .ci/offload/integration-requirements.txt
      - name: Save offload uv cache
        if: steps.eligibility.outputs.eligible == 'true' && steps.setup.outcome ==
          'success' && steps.restore-uv-cache.outputs.cache-hit != 'true'
        continue-on-error: true
        uses: actions/cache/save@27d5ce7f107fe9357f9df03efb73ab90386fccae  # v5.0.5
        with:
          path: /opt/uv-cache
          key: ${{ steps.cache-keys.outputs.uv_key }}
      - name: Restore offload image cache
        id: restore-image-cache
        if: steps.eligibility.outputs.eligible == 'true' && steps.setup.outcome ==
          'success'
        uses: actions/cache/restore@27d5ce7f107fe9357f9df03efb73ab90386fccae  # v5.0.5
        with:
          path: .offload-image-cache
          key: ${{ steps.cache-keys.outputs.image_key }}
          restore-keys: |
            ${{ steps.cache-keys.outputs.image_restore_prefix }}
            ${{ steps.cache-keys.outputs.legacy_image_restore_prefix }}
      - name: Restore JUnit duration cache
        id: restore-junit-cache
        if: steps.eligibility.outputs.eligible == 'true' && steps.setup.outcome ==
          'success'
        uses: actions/cache/restore@27d5ce7f107fe9357f9df03efb73ab90386fccae  # v5.0.5
        with:
          path: .ci/offload/junit.xml
          key: ${{ steps.cache-keys.outputs.junit_restore_key }}
          restore-keys: |
            ${{ steps.cache-keys.outputs.junit_restore_prefix }}
            ${{ steps.cache-keys.outputs.legacy_junit_restore_prefix }}
      - name: Preserve restored JUnit duration seed
        if: steps.restore-junit-cache.outputs.cache-hit != '' && hashFiles('.ci/offload/junit.xml')
          != ''
        run: |
          cp .ci/offload/junit.xml .ci/offload/junit.seed.xml
          python3 scripts/ci/normalize_offload_junit.py .ci/offload/junit.xml
      - name: Start Modal MySQL server
        id: modal-server
        if: steps.eligibility.outputs.eligible == 'true' && steps.setup.outcome ==
          'success' && inputs.test_environment == 'modal-server-mysql'
        continue-on-error: true
        env:
          ZENML_CI_MODAL_DISABLED: ${{ vars.ZENML_CI_MODAL_DISABLED }}
          ZENML_CI_CHECKOUT_REF: ${{ github.event.pull_request.head.sha || github.sha }}
        run: |
          echo "started_at=$(date +%s)" >> "$GITHUB_OUTPUT"
          trap 'echo "completed_at=$(date +%s)" >> "$GITHUB_OUTPUT"' EXIT
          python3 scripts/ci_modal_mysql_sandbox.py start
      - name: Run offload
        id: run-offload
        if: steps.eligibility.outputs.eligible == 'true' && steps.setup.outcome ==
          'success' && steps.modal-server.outcome != 'failure'
        continue-on-error: true
        env:
          OFFLOAD_COMMAND: ${{ vars.ZENML_CI_OFFLOAD_COMMAND }}
          TEST_ENVIRONMENT: ${{ inputs.test_environment }}
          MODAL_CI_SERVER_URL: ${{ steps.modal-server.outputs.server_url }}
          MODAL_CI_SERVER_USERNAME: ${{ steps.modal-server.outputs.server_username }}
          ZENML_CI_CHECKOUT_REF: ${{ github.event.pull_request.head.sha || github.sha }}
        run: |
          set -o pipefail
          original_offload=""
          original_dockerignore="$(mktemp)"
          cp .dockerignore "$original_dockerignore"
          cp Dockerfile.ci.dockerignore .dockerignore
          restore_config() {
            if [ -n "$original_offload" ] && [ -f "$original_offload" ]; then
              cp "$original_offload" offload.toml
              rm -f "$original_offload"
            fi
            if [ -f "$original_dockerignore" ]; then
              cp "$original_dockerignore" .dockerignore
              rm -f "$original_dockerignore"
            fi
          }
          trap restore_config EXIT
          if [ "$TEST_ENVIRONMENT" = "modal-server-mysql" ]; then
            export MODAL_CI_SERVER_PASSWORD
            MODAL_CI_SERVER_PASSWORD=$(python3 - <<'PY'
          from scripts.ci_modal_mysql_sandbox import derive_server_password
          print(derive_server_password())
          PY
          )
            original_offload="$(mktemp)"
            cp offload.toml "$original_offload"
            cp offload-modal-server-mysql.toml offload.toml
          fi
          find . -type d -name __pycache__ -prune -exec rm -rf {} +
          find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
          rm -f .ci/offload/run-start.marker
          python3 - <<'PY' >> "$GITHUB_OUTPUT"
          from pathlib import Path
          marker = Path('.ci/offload/run-start.marker')
          marker.parent.mkdir(parents=True, exist_ok=True)
          marker.write_text('start\n', encoding='utf-8')
          print(f"junit_marker_mtime_ns={marker.stat().st_mtime_ns}")
          PY
          command=${OFFLOAD_COMMAND:-"offload -v run --parallel 20"}
          echo "started_at=$(date +%s)" >> "$GITHUB_OUTPUT"
          echo "Running: $command"
          bash -lc "$command" 2>&1 | tee .ci/offload/offload.log
          echo "exit_code=${PIPESTATUS[0]}" >> "$GITHUB_OUTPUT"
          echo "completed_at=$(date +%s)" >> "$GITHUB_OUTPUT"
      - name: Mark skipped offload as infrastructure failure
        if: steps.eligibility.outputs.eligible != 'true' || steps.setup.outcome ==
          'failure' || steps.modal-server.outcome == 'failure'
        env:
          ELIGIBILITY_REASON: ${{ steps.eligibility.outputs.reason }}
          SETUP_OUTCOME: ${{ steps.setup.outcome }}
          SERVER_OUTCOME: ${{ steps.modal-server.outcome }}
        run: |
          {
            echo "Offload did not run."
            echo "Eligibility: $ELIGIBILITY_REASON"
            echo "Setup outcome: $SETUP_OUTCOME"
            echo "Server outcome: $SERVER_OUTCOME"
          } | tee .ci/offload/offload.log
      - name: Classify offload result
        id: classify
        env:
          SETUP_FAILED: ${{ steps.eligibility.outputs.eligible != 'true' || steps.setup.outcome == 'failure' || steps.modal-server.outcome == 'failure' }}
          OFFLOAD_EXIT_CODE: ${{ steps.run-offload.outputs.exit_code || '1' }}
          JUNIT_MARKER_MTIME_NS: ${{ steps.run-offload.outputs.junit_marker_mtime_ns || '0' }}
        run: |
          echo "started_at=$(date +%s)" >> "$GITHUB_OUTPUT"
          trap 'echo "completed_at=$(date +%s)" >> "$GITHUB_OUTPUT"' EXIT
          python3 scripts/ci/classify_offload_result.py \
            --exit-code "$OFFLOAD_EXIT_CODE" \
            --junit .ci/offload/junit.xml \
            --log .ci/offload/offload.log \
            --setup-failed "$SETUP_FAILED" \
            --junit-min-mtime-ns "$JUNIT_MARKER_MTIME_NS"
      - name: Quarantine stale restored JUnit
        if: always() && steps.classify.outputs.junit_current != 'true' && hashFiles('.ci/offload/junit.xml')
          != ''
        run: mv .ci/offload/junit.xml .ci/offload/junit.stale.xml
      - name: Stop Modal MySQL server
        id: teardown
        if: always() && steps.modal-server.outputs.sandbox_id != ''
        env:
          SANDBOX_ID: ${{ steps.modal-server.outputs.sandbox_id }}
        run: |
          echo "started_at=$(date +%s)" >> "$GITHUB_OUTPUT"
          trap 'echo "completed_at=$(date +%s)" >> "$GITHUB_OUTPUT"' EXIT
          python3 scripts/ci_modal_mysql_sandbox.py stop --sandbox-id "$SANDBOX_ID"
      - name: Emit timing manifest
        if: always()
        env:
          CLASSIFICATION: ${{ steps.classify.outputs.conclusion || 'unknown' }}
          LANE: ${{ inputs.test_environment }}
          STARTED_AT: ${{ steps.run-offload.outputs.started_at || steps.eligibility.outputs.started_at }}
          COMPLETED_AT: ${{ steps.run-offload.outputs.completed_at }}
          SETUP_STARTED_AT: ${{ steps.setup.outputs.started_at }}
          SETUP_COMPLETED_AT: ${{ steps.setup.outputs.completed_at }}
          SETUP_OUTCOME: ${{ steps.setup.outcome }}
          SERVER_STARTED_AT: ${{ steps.modal-server.outputs.started_at }}
          SERVER_COMPLETED_AT: ${{ steps.modal-server.outputs.completed_at }}
          SERVER_OUTCOME: ${{ steps.modal-server.outcome }}
          TEST_STARTED_AT: ${{ steps.run-offload.outputs.started_at }}
          TEST_COMPLETED_AT: ${{ steps.run-offload.outputs.completed_at }}
          TEST_EXIT_CODE: ${{ steps.run-offload.outputs.exit_code || 'missing' }}
          CLASSIFY_STARTED_AT: ${{ steps.classify.outputs.started_at }}
          CLASSIFY_COMPLETED_AT: ${{ steps.classify.outputs.completed_at }}
          CLASSIFY_OUTCOME: ${{ steps.classify.outcome }}
          TEARDOWN_STARTED_AT: ${{ steps.teardown.outputs.started_at }}
          TEARDOWN_COMPLETED_AT: ${{ steps.teardown.outputs.completed_at }}
          TEARDOWN_OUTCOME: ${{ steps.teardown.outcome }}
          OFFLOAD_UV_CACHE_HIT: ${{ steps.restore-uv-cache.outputs.cache-hit }}
          OFFLOAD_IMAGE_CACHE_HIT: ${{ steps.restore-image-cache.outputs.cache-hit }}
          OFFLOAD_JUNIT_CACHE_HIT: ${{ steps.restore-junit-cache.outputs.cache-hit }}
          OFFLOAD_JUNIT_CURRENT: ${{ steps.classify.outputs.junit_current }}
          OFFLOAD_JUNIT_CACHEABLE: ${{ steps.classify.outputs.junit_cacheable }}
        run: |
          python3 scripts/ci/emit_timing_manifest.py \
            --lane "$LANE" \
            --output-dir .ci/offload \
            --started-at "$STARTED_AT" \
            --completed-at "${COMPLETED_AT:-$(date +%s)}" \
            --classification "$CLASSIFICATION" \
            --phase "setup=$SETUP_STARTED_AT,$SETUP_COMPLETED_AT,$SETUP_OUTCOME" \
            --phase "server_provision=$SERVER_STARTED_AT,$SERVER_COMPLETED_AT,$SERVER_OUTCOME" \
            --phase "test_execution=$TEST_STARTED_AT,$TEST_COMPLETED_AT,exit_$TEST_EXIT_CODE" \
            --phase "classification=$CLASSIFY_STARTED_AT,$CLASSIFY_COMPLETED_AT,$CLASSIFY_OUTCOME" \
            --phase "teardown=$TEARDOWN_STARTED_AT,$TEARDOWN_COMPLETED_AT,$TEARDOWN_OUTCOME"
      - name: Check offload image cache path
        id: image-cache-path
        if: always()
        run: |
          if [ -e .offload-image-cache ]; then
            echo "exists=true" >> "$GITHUB_OUTPUT"
          else
            echo "exists=false" >> "$GITHUB_OUTPUT"
          fi
      - name: Save offload image cache
        if: always() && steps.eligibility.outputs.eligible == 'true' && steps.setup.outcome
          == 'success' && steps.restore-image-cache.outputs.cache-hit != 'true' &&
          steps.image-cache-path.outputs.exists == 'true'
        continue-on-error: true
        uses: actions/cache/save@27d5ce7f107fe9357f9df03efb73ab90386fccae  # v5.0.5
        with:
          path: .offload-image-cache
          key: ${{ steps.cache-keys.outputs.image_key }}
      - name: Normalize current JUnit for duration cache
        if: always() && steps.classify.outputs.junit_cacheable == 'true' && hashFiles('.ci/offload/junit.xml')
          != ''
        run: python3 scripts/ci/normalize_offload_junit.py .ci/offload/junit.xml
      - name: Check JUnit duration cache path
        id: junit-cache-path
        if: always()
        run: |
          if [ -s .ci/offload/junit.xml ]; then
            echo "exists=true" >> "$GITHUB_OUTPUT"
          else
            echo "exists=false" >> "$GITHUB_OUTPUT"
          fi
      - name: Save JUnit duration cache
        if: always() && steps.classify.outputs.junit_cacheable == 'true' && steps.junit-cache-path.outputs.exists
          == 'true'
        continue-on-error: true
        uses: actions/cache/save@27d5ce7f107fe9357f9df03efb73ab90386fccae  # v5.0.5
        with:
          path: .ci/offload/junit.xml
          key: ${{ steps.cache-keys.outputs.junit_save_key }}
      - name: Upload offload artifacts
        if: always()
        uses: actions/upload-artifact@2848b2cda0e5190984587ec6bb1f36730ca78d50  # untagged
        with:
          name: linux-fast-offload-artifacts
          path: .ci/offload
          if-no-files-found: warn
      - name: Fail on unsuccessful offload
        if: steps.classify.outputs.conclusion != 'success'
        run: exit 1

```

File: /Users/safoine/zenml-io/zenml/scripts/ci_matrix_hash.py
```py
#!/usr/bin/env python3
"""Compute a deterministic hash for CI matrix definitions."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def _extract_strategy_blocks(workflow: Path) -> list[str]:
    """Extract strategy blocks without requiring a YAML parser in CI."""
    lines = workflow.read_text(encoding="utf-8").splitlines()
    blocks: list[str] = []

    for index, line in enumerate(lines):
        if line.strip() != "strategy:":
            continue

        indent = len(line) - len(line.lstrip(" "))
        block = [line[indent:]]
        for candidate in lines[index + 1 :]:
            if not candidate.strip():
                block.append("")
                continue
            candidate_indent = len(candidate) - len(candidate.lstrip(" "))
            if candidate_indent <= indent:
                break
            block.append(candidate[indent:])
        blocks.append("\n".join(block).rstrip())

    return blocks


def compute_matrix_hash(workflow: Path) -> str:
    """Compute the SHA256 hash for matrix-bearing strategy blocks."""
    blocks = _extract_strategy_blocks(workflow)
    payload = json.dumps(blocks, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main() -> None:
    """Run the CLI."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "workflow",
        nargs="?",
        default=".github/workflows/ci-slow-develop.yml",
    )
    args = parser.parse_args()
    print(compute_matrix_hash(Path(args.workflow)))


if __name__ == "__main__":
    main()

```

File: /Users/safoine/zenml-io/zenml/.github/workspace-safety-baseline.txt
```txt
# Integration tests pending workspace-safety audit.
# These tests existed before the Modal shared-sandbox contract and are
# grandfathered temporarily. New tests must not be added to this baseline.
tests/integration/examples/test_deepchecks.py::test_example
tests/integration/examples/test_facets.py::test_example
tests/integration/examples/test_great_expectations.py::test_example
tests/integration/examples/test_huggingface.py::test_token_classification
tests/integration/examples/test_huggingface.py::test_sequence_classification
tests/integration/examples/test_huggingface_deployment.py::test_huggingface_deployment
tests/integration/examples/test_lightgbm.py::test_example
tests/integration/examples/test_mlflow_deployment.py::test_example
tests/integration/examples/test_mlflow_registry.py::test_example
tests/integration/examples/test_mlflow_tracking.py::test_example
tests/integration/examples/test_neural_prophet.py::test_example
tests/integration/examples/test_pytorch.py::test_example
tests/integration/examples/test_rlm_document_analysis.py::test_rlm_fallback_mode
tests/integration/examples/test_scipy.py::test_example
tests/integration/examples/test_seldon.py::test_example
tests/integration/examples/test_sklearn.py::test_example
tests/integration/examples/test_slack.py::test_example
tests/integration/examples/test_tensorflow.py::test_example
tests/integration/examples/test_whylogs.py::test_example
tests/integration/examples/test_xgboost.py::test_example
tests/integration/functional/artifacts/test_artifact_config.py::test_link_minimalistic
tests/integration/functional/artifacts/test_artifact_config.py::test_link_multiple_named_outputs
tests/integration/functional/artifacts/test_artifact_config.py::test_link_multiple_named_outputs_without_links
tests/integration/functional/artifacts/test_artifact_config.py::test_link_multiple_named_outputs_with_mixed_linkage
tests/integration/functional/artifacts/test_artifact_config.py::test_artifacts_linked_from_cache_steps
tests/integration/functional/artifacts/test_artifact_config.py::test_update_of_has_custom_name
tests/integration/functional/artifacts/test_artifact_store.py::test_artifact_store_remove_on_folders
tests/integration/functional/artifacts/test_artifacts_linage.py::test_that_cached_artifact_versions_are_created_properly
tests/integration/functional/artifacts/test_artifacts_linage.py::test_that_cached_artifact_versions_are_created_properly_for_second_step
tests/integration/functional/artifacts/test_artifacts_linage.py::test_that_cached_artifact_versions_are_created_properly_for_model_version
tests/integration/functional/artifacts/test_artifacts_linage.py::test_that_cached_artifact_versions_are_created_properly_for_multiple_version_producer
tests/integration/functional/artifacts/test_artifacts_linage.py::test_input_artifacts_typing
tests/integration/functional/artifacts/test_artifacts_linage.py::test_that_cached_manual_artifact_has_proper_type_on_second_run
tests/integration/functional/artifacts/test_base_artifact_store.py::test_files_outside_of_artifact_store_are_not_reachable_by_it
tests/integration/functional/artifacts/test_utils.py::test_save_load_artifact_outside_run
tests/integration/functional/artifacts/test_utils.py::test_save_load_artifact_in_run
tests/integration/functional/artifacts/test_utils.py::test_log_metadata_existing
tests/integration/functional/artifacts/test_utils.py::test_log_metadata_single_output
tests/integration/functional/artifacts/test_utils.py::test_log_metadata_multi_output
tests/integration/functional/artifacts/test_utils.py::test_log_metadata_raises_error_if_output_name_unclear
tests/integration/functional/artifacts/test_utils.py::test_download_artifact_files_from_response
tests/integration/functional/artifacts/test_utils.py::test_download_artifact_files_from_response_fails_if_exists
tests/integration/functional/artifacts/test_utils.py::test_download_artifact_files_with_large_file
tests/integration/functional/artifacts/test_utils.py::test_parallel_artifact_creation
tests/integration/functional/artifacts/test_utils.py::test_register_artifact
tests/integration/functional/artifacts/test_utils.py::test_register_artifact_out_of_bounds
tests/integration/functional/artifacts/test_utils.py::test_register_artifact_between_steps
tests/integration/functional/cli/test_artifact.py::test_artifact_list
tests/integration/functional/cli/test_artifact.py::test_artifact_version_list
tests/integration/functional/cli/test_artifact.py::test_artifact_update
tests/integration/functional/cli/test_artifact.py::test_artifact_version_update
tests/integration/functional/cli/test_artifact.py::test_artifact_prune
tests/integration/functional/cli/test_base.py::test_init_creates_zen_folder
tests/integration/functional/cli/test_base.py::test_init_creates_from_templates
tests/integration/functional/cli/test_base.py::test_clean_user_config
tests/integration/functional/cli/test_cli.py::test_cli_command_defines_a_cli_group
tests/integration/functional/cli/test_cli.py::test_cli
tests/integration/functional/cli/test_cli.py::test_ZenMLCLI_formatter
tests/integration/functional/cli/test_cli.py::test_cli_sets_custom_source_root_if_outside_of_repository
tests/integration/functional/cli/test_cli.py::test_cli_does_not_set_custom_source_root_if_inside_repository
tests/integration/functional/cli/test_cli.py::test_connect_to_server_sets_project_after_success
tests/integration/functional/cli/test_cli.py::test_connect_to_server_does_not_set_project_on_failure
tests/integration/functional/cli/test_config.py::test_analytics_opt_in_amends_global_config
tests/integration/functional/cli/test_config.py::test_analytics_opt_out_amends_global_config
tests/integration/functional/cli/test_config.py::test_set_logging_verbosity_stops_when_not_real_level
tests/integration/functional/cli/test_formatter.py::test_write_zen_dl
tests/integration/functional/cli/test_formatter.py::test_measure_table
tests/integration/functional/cli/test_integration.py::test_integration_list
tests/integration/functional/cli/test_integration.py::test_integration_get_requirements_inexistent_integration
tests/integration/functional/cli/test_integration.py::test_integration_get_requirements_specific_integration
tests/integration/functional/cli/test_integration.py::test_integration_get_requirements_all
tests/integration/functional/cli/test_integration.py::test_integration_install_inexistent_integration
tests/integration/functional/cli/test_integration.py::test_integration_install_specific_integration
tests/integration/functional/cli/test_integration.py::test_integration_install_multiple_integrations
tests/integration/functional/cli/test_integration.py::test_integration_install_all
tests/integration/functional/cli/test_integration.py::test_integration_uninstall_inexistent_integration
tests/integration/functional/cli/test_integration.py::test_integration_uninstall_specific_integration
tests/integration/functional/cli/test_integration.py::test_integration_uninstall_all
tests/integration/functional/cli/test_integration.py::test_integration_requirements_exporting
tests/integration/functional/cli/test_model.py::test_model_list
tests/integration/functional/cli/test_model.py::test_model_create_short_names
tests/integration/functional/cli/test_model.py::test_model_create_full_names
tests/integration/functional/cli/test_model.py::test_model_create_only_required
tests/integration/functional/cli/test_model.py::test_model_update
tests/integration/functional/cli/test_model.py::test_model_create_without_required_fails
tests/integration/functional/cli/test_model.py::test_model_delete_found
tests/integration/functional/cli/test_model.py::test_model_delete_not_found
tests/integration/functional/cli/test_model.py::test_model_version_list
tests/integration/functional/cli/test_model.py::test_model_version_delete_found
tests/integration/functional/cli/test_model.py::test_model_version_delete_not_found
tests/integration/functional/cli/test_model.py::test_model_version_links_list
tests/integration/functional/cli/test_model.py::test_model_version_update
tests/integration/functional/cli/test_model_registry.py::test_list_models
tests/integration/functional/cli/test_model_registry.py::test_update_model
tests/integration/functional/cli/test_model_registry.py::test_get_model
tests/integration/functional/cli/test_model_registry.py::test_list_model_versions
tests/integration/functional/cli/test_model_registry.py::test_get_model_version
tests/integration/functional/cli/test_pipeline.py::test_pipeline_list
tests/integration/functional/cli/test_pipeline.py::test_pipeline_delete
tests/integration/functional/cli/test_pipeline.py::test_pipeline_run_list
tests/integration/functional/cli/test_pipeline.py::test_pipeline_run_delete
tests/integration/functional/cli/test_pipeline.py::test_pipeline_schedule_list
tests/integration/functional/cli/test_pipeline.py::test_pipeline_schedule_delete
tests/integration/functional/cli/test_pipeline.py::test_pipeline_registration_without_repo
tests/integration/functional/cli/test_pipeline.py::test_pipeline_registration_with_repo
tests/integration/functional/cli/test_pipeline.py::test_pipeline_build_without_repo
tests/integration/functional/cli/test_pipeline.py::test_pipeline_build_with_invalid_pipeline_source__fails
tests/integration/functional/cli/test_pipeline.py::test_pipeline_build_writes_output_file
tests/integration/functional/cli/test_pipeline.py::test_pipeline_build_doesnt_write_output_file_if_no_build_needed
tests/integration/functional/cli/test_pipeline.py::test_pipeline_build_with_config_file
tests/integration/functional/cli/test_pipeline.py::test_pipeline_build_with_different_stack
tests/integration/functional/cli/test_pipeline.py::test_pipeline_run_without_repo
tests/integration/functional/cli/test_pipeline.py::test_pipeline_run_with_wrong_source_fails
tests/integration/functional/cli/test_pipeline.py::test_pipeline_run_with_config_file
tests/integration/functional/cli/test_pipeline.py::test_pipeline_run_with_different_stack
tests/integration/functional/cli/test_pipeline.py::test_pipeline_run_with_invalid_build_id_fails
tests/integration/functional/cli/test_pipeline.py::test_pipeline_run_with_custom_build_id
tests/integration/functional/cli/test_pipeline.py::test_pipeline_run_with_custom_build_file
tests/integration/functional/cli/test_pipeline.py::test_pipeline_build_list
tests/integration/functional/cli/test_pipeline.py::test_pipeline_build_delete
tests/integration/functional/cli/test_pipeline.py::test_pipeline_snapshot_delete
tests/integration/functional/cli/test_secret.py::test_create_secret
tests/integration/functional/cli/test_secret.py::test_create_private_secret
tests/integration/functional/cli/test_secret.py::test_create_secret_with_values
tests/integration/functional/cli/test_secret.py::test_list_secret_works
tests/integration/functional/cli/test_secret.py::test_get_secret_works
tests/integration/functional/cli/test_secret.py::test_get_secret_with_prefix_works
tests/integration/functional/cli/test_secret.py::test_get_private_secret
tests/integration/functional/cli/test_secret.py::test_delete_secret_works
tests/integration/functional/cli/test_secret.py::test_rename_secret_works
tests/integration/functional/cli/test_secret.py::test_update_secret_works
tests/integration/functional/cli/test_secret.py::test_export_import_secret
tests/integration/functional/cli/test_server.py::test_server_cli_up_down
tests/integration/functional/cli/test_stack.py::test_describe_stack_contains_local_stack
tests/integration/functional/cli/test_stack.py::test_describe_stack_bad_input_fails
tests/integration/functional/cli/test_stack.py::test_update_stack_update_on_default_fails
tests/integration/functional/cli/test_stack.py::test_update_stack_active_stack_succeeds
tests/integration/functional/cli/test_stack.py::test_updating_non_active_stack_succeeds
tests/integration/functional/cli/test_stack.py::test_update_stack_adding_component_succeeds
tests/integration/functional/cli/test_stack.py::test_update_stack_adding_to_default_stack_fails
tests/integration/functional/cli/test_stack.py::test_update_stack_nonexistent_stack_fails
tests/integration/functional/cli/test_stack.py::test_rename_stack_nonexistent_stack_fails
tests/integration/functional/cli/test_stack.py::test_rename_stack_new_name_with_existing_name_fails
tests/integration/functional/cli/test_stack.py::test_rename_stack_default_stack_fails
tests/integration/functional/cli/test_stack.py::test_rename_stack_active_stack_succeeds
tests/integration/functional/cli/test_stack.py::test_rename_stack_non_active_stack_succeeds
tests/integration/functional/cli/test_stack.py::test_remove_component_from_nonexistent_stack_fails
tests/integration/functional/cli/test_stack.py::test_remove_component_core_component_fails
tests/integration/functional/cli/test_stack.py::test_remove_component_non_core_component_succeeds
tests/integration/functional/cli/test_stack.py::test_delete_stack_with_flag_succeeds
tests/integration/functional/cli/test_stack.py::test_delete_stack_default_stack_fails
tests/integration/functional/cli/test_stack.py::test_delete_stack_recursively_with_flag_succeeds
tests/integration/functional/cli/test_stack.py::test_stack_export
tests/integration/functional/cli/test_stack.py::test_stack_export_delete_import
tests/integration/functional/cli/test_stack.py::test_stack_export_import_reuses_components
tests/integration/functional/cli/test_stack_components.py::test_update_stack_component_succeeds
tests/integration/functional/cli/test_stack_components.py::test_update_stack_component_for_nonexistent_component_fails
tests/integration/functional/cli/test_stack_components.py::test_update_stack_component_with_non_configured_property_fails
tests/integration/functional/cli/test_stack_components.py::test_remove_attribute_component_succeeds
tests/integration/functional/cli/test_stack_components.py::test_remove_attribute_component_non_existent_attributes_fail
tests/integration/functional/cli/test_stack_components.py::test_remove_attribute_component_nonexistent_component_fails
tests/integration/functional/cli/test_stack_components.py::test_remove_attribute_component_required_attribute_fails
tests/integration/functional/cli/test_stack_components.py::test_rename_stack_component_to_preexisting_name_fails
tests/integration/functional/cli/test_stack_components.py::test_rename_stack_component_nonexistent_component_fails
tests/integration/functional/cli/test_stack_components.py::test_renaming_non_core_component_succeeds
tests/integration/functional/cli/test_stack_components.py::test_renaming_core_component_succeeds
tests/integration/functional/cli/test_stack_components.py::test_renaming_default_component_fails
tests/integration/functional/cli/test_stack_components.py::test_delete_default_component_fails
tests/integration/functional/cli/test_stack_components.py::test_set_labels_on_register
tests/integration/functional/cli/test_stack_components.py::test_set_labels_on_update
tests/integration/functional/cli/test_stack_components.py::test_remove_labels
tests/integration/functional/cli/test_tag.py::test_tag_list
tests/integration/functional/cli/test_tag.py::test_tag_create_short_names
tests/integration/functional/cli/test_tag.py::test_tag_create_full_names
tests/integration/functional/cli/test_tag.py::test_tag_create_only_required
tests/integration/functional/cli/test_tag.py::test_tag_update
tests/integration/functional/cli/test_tag.py::test_tag_create_without_required_fails
tests/integration/functional/cli/test_tag.py::test_tag_delete_found
tests/integration/functional/cli/test_tag.py::test_tag_delete_not_found
tests/integration/functional/cli/test_user_management.py::test_create_user_with_password_succeeds
tests/integration/functional/cli/test_user_management.py::test_create_user_that_exists_fails
tests/integration/functional/cli/test_user_management.py::test_update_user_with_new_name_succeeds
tests/integration/functional/cli/test_user_management.py::test_update_user_with_new_full_name_succeeds
tests/integration/functional/cli/test_user_management.py::test_update_user_with_new_email
tests/integration/functional/cli/test_user_management.py::test_delete_user_succeeds
tests/integration/functional/cli/test_utils.py::test_error_raises_exception
tests/integration/functional/cli/test_utils.py::test_file_expansion_works
tests/integration/functional/cli/test_utils.py::test_parsing_name_and_arguments
tests/integration/functional/cli/test_utils.py::test_converting_structured_str_to_dict
tests/integration/functional/cli/test_utils.py::test_validate_keys
tests/integration/functional/cli/test_utils.py::test_requires_mac_env_var_warning
tests/integration/functional/cli/test_utils.py::test_requires_mac_env_var_warning_non_mac
tests/integration/functional/cli/test_version.py::test_version_outputs_running_version_number
tests/integration/functional/materializers/test_base_materializer.py::test_immediate_temporary_directory_cleanup_inside_step
tests/integration/functional/materializers/test_base_materializer.py::test_delayed_temporary_directory_cleanup_inside_step
tests/integration/functional/materializers/test_base_materializer.py::test_materializer_temporary_directory_cleanup_outside_step
tests/integration/functional/model/test_model_version.py::TestModel::test_model_created_with_warning
tests/integration/functional/model/test_model_version.py::TestModel::test_model_exists
tests/integration/functional/model/test_model_version.py::TestModel::test_model_create_model_and_version
tests/integration/functional/model/test_model_version.py::TestModel::test_create_model_version_makes_proper_tagging
tests/integration/functional/model/test_model_version.py::TestModel::test_model_fetch_model_and_version_by_number
tests/integration/functional/model/test_model_version.py::TestModel::test_model_fetch_model_and_version_by_number_not_found
tests/integration/functional/model/test_model_version.py::TestModel::test_model_fetch_model_and_version_by_stage
tests/integration/functional/model/test_model_version.py::TestModel::test_model_fetch_model_and_version_by_stage_not_found
tests/integration/functional/model/test_model_version.py::TestModel::test_model_fetch_model_and_version_latest
tests/integration/functional/model/test_model_version.py::TestModel::test_init_stage_logic
tests/integration/functional/model/test_model_version.py::TestModel::test_recovery_flow
tests/integration/functional/model/test_model_version.py::TestModel::test_tags_properly_created
tests/integration/functional/model/test_model_version.py::TestModel::test_tags_properly_updated
tests/integration/functional/model/test_model_version.py::TestModel::test_model_version_config_differs_from_db_warns
tests/integration/functional/model/test_model_version.py::TestModel::test_metadata_logging
tests/integration/functional/model/test_model_version.py::TestModel::test_metadata_logging_functional
tests/integration/functional/model/test_model_version.py::TestModel::test_metadata_logging_in_steps
tests/integration/functional/model/test_model_version.py::TestModel::test_deletion_of_links
tests/integration/functional/model/test_model_version.py::TestModel::test_that_artifacts_are_not_linked_to_models_outside_of_the_context
tests/integration/functional/model/test_model_version.py::TestModel::test_link_artifact_via_function
tests/integration/functional/model/test_model_version.py::TestModel::test_link_artifact_via_save_artifact
tests/integration/functional/models/test_artifact.py::test_default_artifact_name
tests/integration/functional/models/test_artifact.py::test_custom_artifact_name
tests/integration/functional/models/test_artifact.py::test_multi_output_artifact_names
tests/integration/functional/models/test_artifact.py::test_artifact_versioning
tests/integration/functional/models/test_artifact.py::test_artifact_versioning_duplication
tests/integration/functional/models/test_artifact.py::test_artifact_tagging
tests/integration/functional/models/test_artifact.py::test_artifact_step_run_linkage
tests/integration/functional/models/test_artifact.py::test_disabling_artifact_visualization
tests/integration/functional/models/test_artifact.py::test_load_artifact_visualization
tests/integration/functional/models/test_artifact.py::test_disabling_artifact_metadata
tests/integration/functional/models/test_pipeline.py::test_pipeline_run_linkage
tests/integration/functional/models/test_pipeline_run.py::test_pipeline_run_artifacts
tests/integration/functional/models/test_pipeline_run.py::test_pipeline_run_has_client_and_orchestrator_environment
tests/integration/functional/models/test_pipeline_run.py::test_scheduled_pipeline_run_has_schedule_id
tests/integration/functional/models/test_sorting.py::test_sorting_entities
tests/integration/functional/models/test_step_run.py::test_step_run_linkage
tests/integration/functional/models/test_step_run.py::test_step_run_and_dag_include_step_type
tests/integration/functional/models/test_step_run.py::test_step_run_parent_steps_linkage
tests/integration/functional/models/test_step_run.py::test_step_run_has_source_code
tests/integration/functional/models/test_step_run.py::test_step_run_with_too_long_source_code_is_truncated
tests/integration/functional/models/test_step_run.py::test_step_run_has_docstring
tests/integration/functional/models/test_step_run.py::test_step_run_with_too_long_docstring_is_truncated
tests/integration/functional/models/test_step_run.py::test_disabling_step_logs
tests/integration/functional/pipelines/test_multi_user_crud.py::test_multi_user_pipeline_executions
tests/integration/functional/pipelines/test_pipeline_config.py::test_pipeline_with_model_from_yaml
tests/integration/functional/pipelines/test_pipeline_config.py::test_pipeline_config_from_file_not_overridden_for_extra
tests/integration/functional/pipelines/test_pipeline_config.py::test_pipeline_config_from_file_not_overridden_for_model
tests/integration/functional/pipelines/test_pipeline_config.py::test_pipeline_config_from_file_appended_by_code
tests/integration/functional/pipelines/test_pipeline_config.py::test_pipeline_config_from_file_not_warns_on_new_value
tests/integration/functional/pipelines/test_pipeline_config.py::test_pipeline_config_from_file_works_with_pipeline_parameters
tests/integration/functional/pipelines/test_pipeline_config.py::test_pipeline_config_from_file_fails_with_pipeline_parameters_on_conflict_with_step_parameters
tests/integration/functional/pipelines/test_pipeline_config.py::test_pipeline_config_from_file_fails_with_pipeline_parameters_on_conflict_with_pipeline_parameters
tests/integration/functional/pipelines/test_pipeline_config.py::test_pipeline_config_from_file_works_with_pipeline_parameters_on_conflict_with_default_parameters
tests/integration/functional/pipelines/test_pipeline_context.py::test_pipeline_context
tests/integration/functional/pipelines/test_pipeline_context.py::test_pipeline_context_available_as_config_yaml
tests/integration/functional/pipelines/test_pipeline_context.py::test_that_argument_can_be_a_get_artifact_of_model_in_pipeline_context
tests/integration/functional/pipelines/test_pipeline_context.py::test_that_argument_as_get_artifact_of_model_in_pipeline_context_fails_if_not_found
tests/integration/functional/pipelines/test_pipeline_context.py::test_pipeline_context_can_load_model_artifacts_and_metadata_in_lazy_mode
tests/integration/functional/pipelines/test_pipeline_naming.py::test_that_naming_is_consistent_across_the_board
tests/integration/functional/pipelines/test_pipeline_parallel.py::TestArtifactsManagement::test_parallel_runs_can_register_same_artifact
tests/integration/functional/pipelines/test_pipeline_parallel.py::test_parallel_runs_get_different_run_indexes
tests/integration/functional/pipelines/test_pipeline_run.py::test_pipeline_run_returns_up_to_date_run_info
tests/integration/functional/pipelines/test_pipeline_run.py::test_pipeline_run_computes_clientside_cache
tests/integration/functional/pipelines/test_pipeline_run.py::test_fully_cached_pipeline_doesnt_call_orchestrator_implementation
tests/integration/functional/pipelines/test_pipeline_run.py::test_environment_variable_can_be_used_to_disable_clientside_caching
tests/integration/functional/pipelines/test_pipeline_run.py::test_duplicate_pipeline_run_name_raises_improved_error
tests/integration/functional/pipelines/test_pipeline_run.py::test_cache_expiration
tests/integration/functional/steps/test_dynamic_artifact_names.py::test_various_naming_scenarios
tests/integration/functional/steps/test_dynamic_artifact_names.py::test_sequential_executions_have_different_names
tests/integration/functional/steps/test_dynamic_artifact_names.py::test_sequential_executions_have_different_names_in_pipeline_context
tests/integration/functional/steps/test_dynamic_artifact_names.py::test_execution_fails_on_custom_but_not_provided_name
tests/integration/functional/steps/test_dynamic_artifact_names.py::test_stored_info_not_affected_by_dynamic_naming
tests/integration/functional/steps/test_dynamic_artifact_names.py::test_that_overrides_work_as_expected
tests/integration/functional/steps/test_dynamic_artifact_names.py::test_dynamically_named_artifacts_in_downstream_steps
tests/integration/functional/steps/test_external_artifact.py::test_external_artifact_by_value
tests/integration/functional/steps/test_external_artifact.py::test_external_artifact_by_id
tests/integration/functional/steps/test_heartbeat.py::test_heartbeat_rest_functionality
tests/integration/functional/steps/test_heartbeat.py::test_disabled_heartbeat_functionality
tests/integration/functional/steps/test_heartbeat.py::test_heartbeat_null_value_set_default
tests/integration/functional/steps/test_heartbeat.py::test_heartbeat_functionality_on_disable
tests/integration/functional/steps/test_model_version.py::test_model_passed_to_step_context_via_step
tests/integration/functional/steps/test_model_version.py::test_model_passed_to_step_context_via_pipeline
tests/integration/functional/steps/test_model_version.py::test_model_passed_to_step_context_via_step_and_pipeline
tests/integration/functional/steps/test_model_version.py::test_model_passed_to_step_context_and_switches
tests/integration/functional/steps/test_model_version.py::test_create_new_versions_both_pipeline_and_step
tests/integration/functional/steps/test_model_version.py::test_create_new_version_only_in_step
tests/integration/functional/steps/test_model_version.py::test_create_new_version_only_in_pipeline
tests/integration/functional/steps/test_model_version.py::test_recovery_of_steps
tests/integration/functional/steps/test_model_version.py::test_pipeline_run_link_attached_from_pipeline_context
tests/integration/functional/steps/test_model_version.py::test_pipeline_run_link_attached_from_step_context
tests/integration/functional/steps/test_model_version.py::test_pipeline_run_link_attached_from_mixed_context
tests/integration/functional/steps/test_model_version.py::test_that_consumption_also_registers_run_in_model
tests/integration/functional/steps/test_model_version.py::test_that_if_some_steps_request_new_version_but_cached_new_version_is_still_created
tests/integration/functional/steps/test_model_version.py::test_that_pipeline_run_is_removed_on_deletion_of_pipeline_run
tests/integration/functional/steps/test_model_version.py::test_that_pipeline_run_is_removed_on_deletion_of_pipeline
tests/integration/functional/steps/test_model_version.py::test_that_artifact_is_removed_on_deletion
tests/integration/functional/steps/test_model_version.py::test_pipeline_context_pass_artifact_from_model_and_link_run
tests/integration/functional/steps/test_model_version.py::test_pipeline_use_same_model_version_even_if_it_was_promoted_during_run
tests/integration/functional/steps/test_model_version.py::test_templated_names_for_model_version
tests/integration/functional/steps/test_model_version.py::test_model_version_creation
tests/integration/functional/steps/test_model_version.py::test_model_version_fetching_by_stage
tests/integration/functional/steps/test_step_context.py::test_materializer_can_access_step_context
tests/integration/functional/steps/test_step_context.py::test_step_can_access_step_context
tests/integration/functional/steps/test_step_context.py::test_input_artifacts_property
tests/integration/functional/steps/test_step_context.py::test_metadata_and_tags_set_from_context
tests/integration/functional/steps/test_utils.py::test_log_metadata_within_step
tests/integration/functional/steps/test_utils.py::test_log_metadata_using_latest_run
tests/integration/functional/steps/test_utils.py::test_log_metadata_using_specific_params
tests/integration/functional/test_client.py::test_repository_detection
tests/integration/functional/test_client.py::test_initializing_repo_creates_directory_and_uses_default_stack
tests/integration/functional/test_client.py::test_initializing_repo_twice_fails
tests/integration/functional/test_client.py::test_freshly_initialized_repo_attributes
tests/integration/functional/test_client.py::test_finding_repository_directory_with_explicit_path
tests/integration/functional/test_client.py::test_activating_nonexisting_stack_fails
tests/integration/functional/test_client.py::test_activating_a_stack_updates_the_config_file
tests/integration/functional/test_client.py::test_registering_a_stack
tests/integration/functional/test_client.py::test_registering_a_stack_with_existing_name
tests/integration/functional/test_client.py::test_updating_a_stack_with_new_component_succeeds
tests/integration/functional/test_client.py::test_renaming_stack_with_update_method_succeeds
tests/integration/functional/test_client.py::test_register_a_stack_with_unregistered_component_fails
tests/integration/functional/test_client.py::test_deregistering_the_active_stack
tests/integration/functional/test_client.py::test_deregistering_a_non_active_stack
tests/integration/functional/test_client.py::test_getting_a_stack_component
tests/integration/functional/test_client.py::test_getting_a_nonexisting_stack_component
tests/integration/functional/test_client.py::test_registering_a_stack_component_with_existing_name
tests/integration/functional/test_client.py::test_registering_a_new_stack_component_succeeds
tests/integration/functional/test_client.py::test_deregistering_a_stack_component_in_stack_fails
tests/integration/functional/test_client.py::test_deregistering_a_stack_component_that_is_part_of_a_registered_stack
tests/integration/functional/test_client.py::test_getting_a_pipeline
tests/integration/functional/test_client.py::test_listing_pipelines
tests/integration/functional/test_client.py::test_create_run_metadata_for_pipeline_run
tests/integration/functional/test_client.py::test_create_run_metadata_for_step_run
tests/integration/functional/test_client.py::test_create_run_metadata_for_artifact
tests/integration/functional/test_client.py::test_create_run_metadata_overwrite
tests/integration/functional/test_client.py::test_create_run_metadata_dict_merge
tests/integration/functional/test_client.py::test_create_secret_default_scope
tests/integration/functional/test_client.py::test_create_private_secret
tests/integration/functional/test_client.py::test_create_secret_existing_name_scope
tests/integration/functional/test_client.py::test_create_private_secret_existing_name
tests/integration/functional/test_client.py::test_create_secret_existing_name_different_scope
tests/integration/functional/test_client.py::test_listing_builds
tests/integration/functional/test_client.py::test_getting_builds
tests/integration/functional/test_client.py::test_deleting_builds
tests/integration/functional/test_client.py::test_listing_snapshots
tests/integration/functional/test_client.py::test_getting_snapshots
tests/integration/functional/test_client.py::test_deleting_snapshots
tests/integration/functional/test_client.py::test_get_run
tests/integration/functional/test_client.py::test_get_run_fails_for_non_existent_run
tests/integration/functional/test_client.py::test_basic_crud_for_entity
tests/integration/functional/test_client.py::TestArtifact::test_prune_full
tests/integration/functional/test_client.py::TestArtifact::test_prune_data_and_version
tests/integration/functional/test_client.py::TestArtifact::test_prune_only_artifact_version
tests/integration/functional/test_client.py::TestArtifact::test_pipeline_can_load_in_lazy_mode
tests/integration/functional/test_client.py::TestModel::test_get_model_found
tests/integration/functional/test_client.py::TestModel::test_get_model_not_found
tests/integration/functional/test_client.py::TestModel::test_create_model_pass
tests/integration/functional/test_client.py::TestModel::test_create_model_duplicate_fail
tests/integration/functional/test_client.py::TestModel::test_delete_model_found
tests/integration/functional/test_client.py::TestModel::test_delete_model_not_found
tests/integration/functional/test_client.py::TestModel::test_update_model
tests/integration/functional/test_client.py::TestModel::test_name_is_mutable
tests/integration/functional/test_client.py::TestModel::test_latest_version_retrieval
tests/integration/functional/test_client.py::TestModel::test_list_by_tags
tests/integration/functional/test_client.py::TestModelVersion::test_get_model_version_by_name_found
tests/integration/functional/test_client.py::TestModelVersion::test_get_model_version_by_id_found
tests/integration/functional/test_client.py::TestModelVersion::test_get_model_version_by_index_found
tests/integration/functional/test_client.py::TestModelVersion::test_get_model_version_by_stage_found
tests/integration/functional/test_client.py::TestModelVersion::test_get_model_version_by_stage_not_found
tests/integration/functional/test_client.py::TestModelVersion::test_get_model_version_not_found
tests/integration/functional/test_client.py::TestModelVersion::test_create_model_version_pass
tests/integration/functional/test_client.py::TestModelVersion::test_create_model_version_duplicate_fails
tests/integration/functional/test_client.py::TestModelVersion::test_update_model_version
tests/integration/functional/test_client.py::TestModelVersion::test_list_model_version
tests/integration/functional/test_client.py::TestModelVersion::test_delete_model_version_found
tests/integration/functional/test_client.py::TestModelVersion::test_delete_model_version_not_found
tests/integration/functional/test_client.py::TestModelVersion::test_get_by_latest
tests/integration/functional/test_client.py::TestModelVersion::test_get_by_stage
tests/integration/functional/test_client.py::TestModelVersion::test_stage_not_found
tests/integration/functional/test_client.py::TestModelVersion::test_name_and_description_is_mutable
tests/integration/functional/test_client.py::test_attach_and_detach_tag_pipeline_run
tests/integration/functional/test_zen_server_api.py::test_list_stacks_endpoint
tests/integration/functional/test_zen_server_api.py::test_list_users_endpoint
tests/integration/functional/test_zen_server_api.py::test_server_requires_auth
tests/integration/functional/triggers/test_crud.py::test_schedule_crud_happy_path
tests/integration/functional/triggers/test_crud.py::test_event_crud_happy_path
tests/integration/functional/triggers/test_crud.py::test_snapshot_associations
tests/integration/functional/triggers/test_crud.py::test_run_associations
tests/integration/functional/triggers/test_crud.py::test_sdk_utilities
tests/integration/functional/utils/test_metadata_utils.py::test_metadata_utils
tests/integration/functional/utils/test_run_utils.py::test_build_dag
tests/integration/functional/utils/test_run_utils.py::test_find_all_downstream_steps
tests/integration/functional/utils/test_run_utils.py::test_dag_with_failed_step
tests/integration/functional/utils/test_run_utils.py::test_execution_mode_fail_fast
tests/integration/functional/utils/test_run_utils.py::test_execution_mode_stop_on_failure
tests/integration/functional/utils/test_run_utils.py::test_execution_mode_continue_on_failure
tests/integration/functional/utils/test_tag_utils.py::test_tag_utils
tests/integration/functional/utils/test_tag_utils.py::test_cascade_tags_for_output_artifacts_of_cached_pipeline_run
tests/integration/functional/utils/test_tag_utils.py::test_tags_with_special_characters
tests/integration/functional/zen_server/api/test_schedules.py::test_step
tests/integration/functional/zen_server/api/test_schedules.py::test_pipeline
tests/integration/functional/zen_server/api/test_schedules.py::test_crud_cycle
tests/integration/functional/zen_server/pipeline_execution/test_pipeline_execution_utils.py::test_creating_snapshot_request_from_template
tests/integration/functional/zen_server/test_zen_server.py::test_server_up_down
tests/integration/functional/zen_server/test_zen_server.py::test_rate_limit_is_not_impacted_by_successful_requests
tests/integration/functional/zen_stores/test_secrets_store.py::test_get_secret_returns_values
tests/integration/functional/zen_stores/test_secrets_store.py::test_list_secret_excludes_values
tests/integration/functional/zen_stores/test_secrets_store.py::test_secret_empty_values
tests/integration/functional/zen_stores/test_secrets_store.py::test_update_secret_existing_values
tests/integration/functional/zen_stores/test_secrets_store.py::test_update_secret_add_new_values
tests/integration/functional/zen_stores/test_secrets_store.py::test_update_secret_remove_values
tests/integration/functional/zen_stores/test_secrets_store.py::test_update_secret_remove_nonexisting_values
tests/integration/functional/zen_stores/test_secrets_store.py::test_update_secret_values_sets_updated_date
tests/integration/functional/zen_stores/test_secrets_store.py::test_update_secret_name_sets_updated_date
tests/integration/functional/zen_stores/test_secrets_store.py::test_update_secret_name
tests/integration/functional/zen_stores/test_secrets_store.py::test_update_secret_name_fails_if_exists
tests/integration/functional/zen_stores/test_secrets_store.py::test_update_private_secret_name_succeeds_if_public_secret_exists
tests/integration/functional/zen_stores/test_secrets_store.py::test_update_public_secret_name_succeeds_if_private_secret_exists
tests/integration/functional/zen_stores/test_secrets_store.py::test_reusing_private_secret_name_succeeds
tests/integration/functional/zen_stores/test_secrets_store.py::test_update_scope_succeeds
tests/integration/functional/zen_stores/test_secrets_store.py::test_update_scope_fails_if_name_already_in_scope
tests/integration/functional/zen_stores/test_secrets_store.py::test_public_secret_is_visible_to_other_users
tests/integration/functional/zen_stores/test_secrets_store.py::test_private_secret_is_not_visible_to_other_users
tests/integration/functional/zen_stores/test_secrets_store.py::test_list_secrets_filter
tests/integration/functional/zen_stores/test_secrets_store.py::test_list_secrets_pagination_and_sorting
tests/integration/functional/zen_stores/test_secrets_store.py::test_delete_user_with_secrets
tests/integration/functional/zen_stores/test_zen_store.py::test_basic_crud_for_entity
tests/integration/functional/zen_stores/test_zen_store.py::test_create_entity_twice_fails
tests/integration/functional/zen_stores/test_zen_store.py::test_get_nonexistent_entity_fails
tests/integration/functional/zen_stores/test_zen_store.py::test_updating_nonexisting_entity_raises_error
tests/integration/functional/zen_stores/test_zen_store.py::test_deleting_nonexistent_entity_raises_error
tests/integration/functional/zen_stores/test_zen_store.py::test_only_one_default_project_present
tests/integration/functional/zen_stores/test_zen_store.py::test_updating_default_project_fails
tests/integration/functional/zen_stores/test_zen_store.py::test_deleting_default_project_fails
tests/integration/functional/zen_stores/test_zen_store.py::TestAdminUser::test_creation_as_admin_and_non_admin
tests/integration/functional/zen_stores/test_zen_store.py::TestAdminUser::test_listing_users
tests/integration/functional/zen_stores/test_zen_store.py::TestAdminUser::test_get_users
tests/integration/functional/zen_stores/test_zen_store.py::TestAdminUser::test_update_users
tests/integration/functional/zen_stores/test_zen_store.py::TestAdminUser::test_deactivate_users
tests/integration/functional/zen_stores/test_zen_store.py::TestAdminUser::test_delete_users
tests/integration/functional/zen_stores/test_zen_store.py::TestAdminUser::test_update_self_via_normal_endpoint
tests/integration/functional/zen_stores/test_zen_store.py::TestAdminUser::test_update_self_via_current_user_endpoint
tests/integration/functional/zen_stores/test_zen_store.py::test_active_user
tests/integration/functional/zen_stores/test_zen_store.py::test_creating_user_with_existing_name_fails
tests/integration/functional/zen_stores/test_zen_store.py::test_creating_users_in_parallel_do_not_duplicate_fails
tests/integration/functional/zen_stores/test_zen_store.py::test_creating_service_accounts_in_parallel_do_not_duplicate_fails
tests/integration/functional/zen_stores/test_zen_store.py::test_get_user
tests/integration/functional/zen_stores/test_zen_store.py::test_delete_user_with_resources_fails
tests/integration/functional/zen_stores/test_zen_store.py::test_updating_user_with_existing_name_fails
tests/integration/functional/zen_stores/test_zen_store.py::test_create_user_no_password
tests/integration/functional/zen_stores/test_zen_store.py::test_reactivate_user
tests/integration/functional/zen_stores/test_zen_store.py::test_create_service_account
tests/integration/functional/zen_stores/test_zen_store.py::test_delete_service_account
tests/integration/functional/zen_stores/test_zen_store.py::test_delete_service_account_with_resources_fails
tests/integration/functional/zen_stores/test_zen_store.py::test_create_service_account_used_name_fails
tests/integration/functional/zen_stores/test_zen_store.py::test_get_service_account
tests/integration/functional/zen_stores/test_zen_store.py::test_list_service_accounts
tests/integration/functional/zen_stores/test_zen_store.py::test_update_service_account_name
tests/integration/functional/zen_stores/test_zen_store.py::test_update_service_account_used_name_fails
tests/integration/functional/zen_stores/test_zen_store.py::test_deactivate_service_account
tests/integration/functional/zen_stores/test_zen_store.py::test_update_service_account_description
tests/integration/functional/zen_stores/test_zen_store.py::test_create_api_key
tests/integration/functional/zen_stores/test_zen_store.py::test_delete_api_key
tests/integration/functional/zen_stores/test_zen_store.py::test_create_api_key_used_name_fails
tests/integration/functional/zen_stores/test_zen_store.py::test_list_api_keys
tests/integration/functional/zen_stores/test_zen_store.py::test_update_key_name
tests/integration/functional/zen_stores/test_zen_store.py::test_update_api_key_used_name_fails
tests/integration/functional/zen_stores/test_zen_store.py::test_deactivate_api_key
tests/integration/functional/zen_stores/test_zen_store.py::test_update_api_key_description
tests/integration/functional/zen_stores/test_zen_store.py::test_rotate_api_key
tests/integration/functional/zen_stores/test_zen_store.py::test_login_api_key
tests/integration/functional/zen_stores/test_zen_store.py::test_login_inactive_api_key
tests/integration/functional/zen_stores/test_zen_store.py::test_login_inactive_service_account
tests/integration/functional/zen_stores/test_zen_store.py::test_login_deleted_api_key
tests/integration/functional/zen_stores/test_zen_store.py::test_login_rotate_api_key
tests/integration/functional/zen_stores/test_zen_store.py::test_login_rotate_api_key_retain_period
tests/integration/functional/zen_stores/test_zen_store.py::test_update_default_stack_component_fails
tests/integration/functional/zen_stores/test_zen_store.py::test_delete_default_stack_component_fails
tests/integration/functional/zen_stores/test_zen_store.py::test_count_stack_components
tests/integration/functional/zen_stores/test_zen_store.py::test_stack_component_create_fails_with_invalid_name
tests/integration/functional/zen_stores/test_zen_store.py::test_updating_default_stack_fails
tests/integration/functional/zen_stores/test_zen_store.py::test_deleting_default_stack_fails
tests/integration/functional/zen_stores/test_zen_store.py::test_get_stack_fails_with_nonexistent_stack_id
tests/integration/functional/zen_stores/test_zen_store.py::test_filter_stack_succeeds
tests/integration/functional/zen_stores/test_zen_store.py::test_crud_on_stack_succeeds
tests/integration/functional/zen_stores/test_zen_store.py::test_name_uniqueness_checks_on_stack_crud
tests/integration/functional/zen_stores/test_zen_store.py::test_register_stack_fails_with_invalid_name
tests/integration/functional/zen_stores/test_zen_store.py::test_updating_nonexistent_stack_fails
tests/integration/functional/zen_stores/test_zen_store.py::test_deleting_nonexistent_stack_fails
tests/integration/functional/zen_stores/test_zen_store.py::test_deleting_a_stack_succeeds
tests/integration/functional/zen_stores/test_zen_store.py::test_deleting_a_stack_recursively_succeeds
tests/integration/functional/zen_stores/test_zen_store.py::test_deleting_a_stack_recursively_with_some_stack_components_present_in_another_stack_succeeds
tests/integration/functional/zen_stores/test_zen_store.py::test_stacks_are_accessible_by_other_users
tests/integration/functional/zen_stores/test_zen_store.py::test_list_runs_is_ordered
tests/integration/functional/zen_stores/test_zen_store.py::test_count_runs
tests/integration/functional/zen_stores/test_zen_store.py::test_filter_runs_by_code_repo
tests/integration/functional/zen_stores/test_zen_store.py::test_deleting_run_deletes_steps
tests/integration/functional/zen_stores/test_zen_store.py::test_filters_with_oneof_tags_and_run_metadata
tests/integration/functional/zen_stores/test_zen_store.py::test_run_metadata_filtering
tests/integration/functional/zen_stores/test_zen_store.py::test_finalize_wait_condition_lease_pauses_run_if_wait_condition_pending
tests/integration/functional/zen_stores/test_zen_store.py::test_finalize_wait_condition_does_not_resume_run_from_server
tests/integration/functional/zen_stores/test_zen_store.py::test_abandon_wait_condition_lease_pauses_run_if_wait_condition_pending
tests/integration/functional/zen_stores/test_zen_store.py::test_abandon_wait_condition_lease_attempts_resume_for_resolved_run
tests/integration/functional/zen_stores/test_zen_store.py::test_create_wait_condition_is_idempotent_while_pending
tests/integration/functional/zen_stores/test_zen_store.py::test_resolve_wait_condition_rejects_result_without_schema
tests/integration/functional/zen_stores/test_zen_store.py::test_get_run_step_outputs_succeeds
tests/integration/functional/zen_stores/test_zen_store.py::test_get_run_step_inputs_succeeds
tests/integration/functional/zen_stores/test_zen_store.py::test_list_unused_artifacts
tests/integration/functional/zen_stores/test_zen_store.py::test_list_custom_named_artifacts
tests/integration/functional/zen_stores/test_zen_store.py::test_artifacts_are_not_deleted_with_run
tests/integration/functional/zen_stores/test_zen_store.py::test_artifact_create_fails_with_invalid_name
tests/integration/functional/zen_stores/test_zen_store.py::test_artifact_fetch_works_with_invalid_name
tests/integration/functional/zen_stores/test_zen_store.py::test_logs_are_recorded_properly
tests/integration/functional/zen_stores/test_zen_store.py::test_logs_dont_exist_when_disabled
tests/integration/functional/zen_stores/test_zen_store.py::test_connector_with_no_secrets
tests/integration/functional/zen_stores/test_zen_store.py::test_connector_with_secrets
tests/integration/functional/zen_stores/test_zen_store.py::test_connector_with_no_config_no_secrets
tests/integration/functional/zen_stores/test_zen_store.py::test_connector_with_labels
tests/integration/functional/zen_stores/test_zen_store.py::test_connector_secret_share_lifespan
tests/integration/functional/zen_stores/test_zen_store.py::test_connector_name_reuse_for_same_user_fails
tests/integration/functional/zen_stores/test_zen_store.py::test_connector_name_reuse_for_different_user_fails
tests/integration/functional/zen_stores/test_zen_store.py::test_connector_list
tests/integration/functional/zen_stores/test_zen_store.py::test_connector_update_name
tests/integration/functional/zen_stores/test_zen_store.py::test_connector_update_resource_types
tests/integration/functional/zen_stores/test_zen_store.py::test_connector_update_resource_id
tests/integration/functional/zen_stores/test_zen_store.py::test_connector_update_auth_method
tests/integration/functional/zen_stores/test_zen_store.py::test_connector_update_config
tests/integration/functional/zen_stores/test_zen_store.py::test_connector_update_expiration
tests/integration/functional/zen_stores/test_zen_store.py::test_connector_update_expires_at
tests/integration/functional/zen_stores/test_zen_store.py::test_connector_update_labels
tests/integration/functional/zen_stores/test_zen_store.py::test_connector_name_update_fails_if_exists
tests/integration/functional/zen_stores/test_zen_store.py::test_connector_type_register
tests/integration/functional/zen_stores/test_zen_store.py::test_connector_validation
tests/integration/functional/zen_stores/test_zen_store.py::TestModel::test_latest_version_properly_fetched
tests/integration/functional/zen_stores/test_zen_store.py::TestModel::test_update_name
tests/integration/functional/zen_stores/test_zen_store.py::TestModel::test_list_by_tag
tests/integration/functional/zen_stores/test_zen_store.py::TestModel::test_create_fails_with_invalid_name
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersion::test_create_pass
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersion::test_create_fail_with_invalid_name
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersion::test_create_duplicated
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersion::test_create_no_model
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersion::test_get_not_found
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersion::test_get_found
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersion::test_list_empty
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersion::test_list_not_empty
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersion::test_list_by_tags
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersion::test_delete_not_found
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersion::test_delete_found
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersion::test_update_not_found
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersion::test_update_not_forced
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersion::test_update_name_and_description
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersion::test_in_stage_not_found
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersion::test_latest_found
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersion::test_update_forced
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersion::test_update_public_interface
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersion::test_update_public_interface_bad_stage
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersion::test_model_bad_stage
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersion::test_model_ok_stage
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersion::test_increments_version_number
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersion::test_get_found_by_number
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersion::test_get_not_found_by_number
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersionArtifactLinks::test_link_create_pass
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersionArtifactLinks::test_link_create_versioned
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersionArtifactLinks::test_link_create_duplicated_by_id
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersionArtifactLinks::test_link_create_single_version_of_same_output_name_from_different_steps
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersionArtifactLinks::test_link_delete_found
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersionArtifactLinks::test_link_delete_all
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersionArtifactLinks::test_link_delete_not_found
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersionArtifactLinks::test_link_list_empty
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersionArtifactLinks::test_link_list_populated
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersionPipelineRunLinks::test_link_create_pass
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersionPipelineRunLinks::test_link_create_duplicated
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersionPipelineRunLinks::test_linked_pipeline_run_fetching
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersionPipelineRunLinks::test_link_delete_found
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersionPipelineRunLinks::test_link_delete_not_found
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersionPipelineRunLinks::test_link_list_empty
tests/integration/functional/zen_stores/test_zen_store.py::TestModelVersionPipelineRunLinks::test_link_list_populated
tests/integration/functional/zen_stores/test_zen_store.py::TestTag::test_create_pass
tests/integration/functional/zen_stores/test_zen_store.py::TestTag::test_create_bad_input
tests/integration/functional/zen_stores/test_zen_store.py::TestTag::test_create_fails_with_invalid_name
tests/integration/functional/zen_stores/test_zen_store.py::TestTag::test_create_duplicate
tests/integration/functional/zen_stores/test_zen_store.py::TestTag::test_get_tag_found
tests/integration/functional/zen_stores/test_zen_store.py::TestTag::test_get_tag_not_found
tests/integration/functional/zen_stores/test_zen_store.py::TestTag::test_list_tags
tests/integration/functional/zen_stores/test_zen_store.py::TestTag::test_update_tag
tests/integration/functional/zen_stores/test_zen_store.py::TestTagResource::test_create_tag_resource_pass
tests/integration/functional/zen_stores/test_zen_store.py::TestTagResource::test_create_tag_resource_pass_on_duplicate
tests/integration/functional/zen_stores/test_zen_store.py::TestTagResource::test_batch_create_tag_resource_pass
tests/integration/functional/zen_stores/test_zen_store.py::TestTagResource::test_delete_tag_resource_pass
tests/integration/functional/zen_stores/test_zen_store.py::TestTagResource::test_delete_tag_resource_pass_on_non_existing
tests/integration/functional/zen_stores/test_zen_store.py::TestTagResource::test_batch_delete_tag_resource_pass
tests/integration/functional/zen_stores/test_zen_store.py::TestTagResource::test_delete_tag_resource_mismatch
tests/integration/functional/zen_stores/test_zen_store.py::TestTagResource::test_cascade_deletion
tests/integration/functional/zen_stores/test_zen_store.py::TestRunMetadata::test_metadata_full_cycle_with_cascade_deletion
tests/integration/functional/zen_stores/test_zen_store.py::test_updating_the_pipeline_run_status
tests/integration/functional/zen_stores/test_zen_store.py::test_tag_filter_with_resource_type
tests/integration/functional/zen_stores/test_zen_store.py::TestCuratedVisualizations::test_curated_visualizations_across_resources
tests/integration/functional/zen_stores/test_zen_store.py::TestCuratedVisualizations::test_curated_visualizations_project_only
tests/integration/integrations/airflow/orchestrators/test_airflow_orchestrator.py::test_airflow_orchestrator_attributes
tests/integration/integrations/airflow/orchestrators/test_airflow_orchestrator.py::test_resource_appliciation
tests/integration/integrations/airflow/orchestrators/test_dag_generator.py::test_dag_generator_constants
tests/integration/integrations/airflow/orchestrators/test_dag_generator.py::test_class_importing_by_path
tests/integration/integrations/aws/deployers/test_app_runner_deployer.py::test_aws_app_runner_deployer_flavor_attributes
tests/integration/integrations/aws/deployers/test_app_runner_deployer.py::test_aws_app_runner_deployer_flavor_resource_combinations
tests/integration/integrations/aws/orchestrators/test_sagemaker_orchestrator.py::test_sagemaker_orchestrator_flavor_attributes
tests/integration/integrations/azure/artifact_stores/test_azure_artifact_store.py::test_azure_artifact_store_attributes
tests/integration/integrations/azure/artifact_stores/test_azure_artifact_store.py::test_must_be_azure_path
tests/integration/integrations/deepchecks/data_validators/test_deepchecks_data_validator.py::test_deepchecks_data_validator_attributes
tests/integration/integrations/deepchecks/materializers/test_deepchecks_dataset_materializer.py::test_deepchecks_dataset_materializer
tests/integration/integrations/deepchecks/materializers/test_deepchecks_result_materializer.py::test_deepchecks_dataset_materializer_with_check_result
tests/integration/integrations/deepchecks/materializers/test_deepchecks_result_materializer.py::test_deepchecks_dataset_materializer_with_suite_result
tests/integration/integrations/deepchecks/test_validation_checks.py::test_validation_check_fails_when_checking_name
tests/integration/integrations/evidently/data_validators/test_evidently_data_validator.py::test_evidently_data_validator_attributes
tests/integration/integrations/facets/materializers/test_facets_materializer.py::test_facets_materializer
tests/integration/integrations/gcp/artifact_stores/test_gcp_artifact_store.py::test_must_be_gcs_path
tests/integration/integrations/gcp/experiment_trackers/test_vertex_experiment_tracker.py::test_vertex_experiment_tracker_stack_validation
tests/integration/integrations/gcp/experiment_trackers/test_vertex_experiment_tracker.py::test_vertex_experiment_tracker_attributes
tests/integration/integrations/gcp/experiment_trackers/test_vertex_experiment_tracker.py::test_format_name
tests/integration/integrations/gcp/experiment_trackers/test_vertex_experiment_tracker.py::test_get_experiment_name
tests/integration/integrations/gcp/experiment_trackers/test_vertex_experiment_tracker.py::test_get_run_name
tests/integration/integrations/gcp/image_builders/test_gcp_image_builder.py::test_stack_validation
tests/integration/integrations/gcp/orchestrators/test_vertex_orchestrator.py::test_vertex_orchestrator_stack_validation
tests/integration/integrations/gcp/orchestrators/test_vertex_orchestrator.py::test_vertex_orchestrator_configure_container_resources
tests/integration/integrations/gitlab/code_repositories/test_gitlab_code_repository.py::test_check_remote_url
tests/integration/integrations/great_expectations/materializers/test_ge_materializer.py::test_great_expectations_materializer
tests/integration/integrations/huggingface/materializers/test_huggingface_datasets_materializer.py::test_huggingface_datasets_materializer
tests/integration/integrations/huggingface/materializers/test_huggingface_datasets_materializer.py::test_extract_repo_name
tests/integration/integrations/huggingface/materializers/test_huggingface_datasets_materializer.py::test_extract_repo_name_edge_cases
tests/integration/integrations/huggingface/materializers/test_huggingface_datasets_materializer.py::test_extract_repo_name_exceptions
tests/integration/integrations/huggingface/materializers/test_huggingface_pt_model_materializer.py::test_huggingface_pretrained_model_materializer
tests/integration/integrations/huggingface/materializers/test_huggingface_tf_model_materializer.py::test_huggingface_tf_pretrained_model_materializer
tests/integration/integrations/huggingface/materializers/test_huggingface_tokenizer_materializer.py::test_huggingface_tokenizer_materializer
tests/integration/integrations/huggingface/steps/test_accelerate_runner.py::test_accelerate_runner_on_cpu_with_toy_model
tests/integration/integrations/huggingface/steps/test_accelerate_runner.py::test_accelerate_runner_fails_on_functional_use
tests/integration/integrations/hyperai/orchestrators/test_hyperai_orchestrator.py::test_hyperai_orchestrator_attributes
tests/integration/integrations/hyperai/orchestrators/test_hyperai_orchestrator.py::test_validate_mount_path
tests/integration/integrations/kaniko/image_builders/test_kaniko_image_builder.py::test_stack_validation
tests/integration/integrations/kubeflow/orchestrators/test_kubeflow_orchestrator.py::test_kubeflow_orchestrator_remote_stack
tests/integration/integrations/kubeflow/orchestrators/test_kubeflow_orchestrator.py::test_kubeflow_orchestrator_local_stack
tests/integration/integrations/kubernetes/orchestrators/test_kubernetes_orchestrator.py::test_kubernetes_orchestrator_remote_stack
tests/integration/integrations/kubernetes/orchestrators/test_kubernetes_orchestrator.py::test_kubernetes_orchestrator_local_stack
tests/integration/integrations/kubernetes/orchestrators/test_kubernetes_orchestrator.py::test_kubernetes_orchestrator_uses_service_account_from_settings
tests/integration/integrations/kubernetes/orchestrators/test_kubernetes_orchestrator.py::test_concurrency_policy_validation_accepts_valid_values
tests/integration/integrations/kubernetes/orchestrators/test_kubernetes_orchestrator.py::test_concurrency_policy_validation_rejects_invalid_values
tests/integration/integrations/kubernetes/orchestrators/test_manifest_utils.py::test_build_pod_manifest_metadata
tests/integration/integrations/kubernetes/orchestrators/test_manifest_utils.py::test_build_pod_manifest_pod_settings
tests/integration/integrations/kubernetes/orchestrators/test_manifest_utils.py::test_build_cron_job_manifest_with_cronjob_spec_fields
tests/integration/integrations/kubernetes/orchestrators/test_manifest_utils.py::test_build_cron_job_manifest_defaults_none
tests/integration/integrations/kubernetes/step_operators/test_kubernetes_step_operator.py::test_kubernetes_orchestrator_stack_validation
tests/integration/integrations/kubernetes/test_k8s_applier.py::test_flatten_items_expands_kind_list_and_leaves_others
tests/integration/integrations/kubernetes/test_k8s_applier.py::test_normalize_resource_to_dict_with_dict_returns_same_instance
tests/integration/integrations/kubernetes/test_k8s_applier.py::test_normalize_resource_to_dict_with_model_uses_sanitize_and_normalizes_api_version
tests/integration/integrations/kubernetes/test_k8s_applier.py::test_normalize_resource_to_dict_with_model_wrapping_api_version_key
tests/integration/integrations/kubernetes/test_k8s_applier.py::test_normalize_resource_to_dict_with_model_returning_non_dict_raises
tests/integration/integrations/kubernetes/test_k8s_applier.py::test_normalize_resource_to_dict_with_unsupported_type_raises
tests/integration/integrations/kubernetes/test_k8s_applier.py::test_apply_resource_namespaced_and_cluster_scoped
tests/integration/integrations/kubernetes/test_k8s_applier.py::test_provision_orders_namespaces_and_builds_inventory
tests/integration/integrations/kubernetes/test_k8s_applier.py::test_provision_stop_on_error_true_raises_with_partial_inventory
tests/integration/integrations/kubernetes/test_k8s_applier.py::test_provision_stop_on_error_false_collects_all_errors
tests/integration/integrations/kubernetes/test_k8s_applier.py::test_delete_from_inventory_deletes_in_reverse_order_and_skips_namespaces
tests/integration/integrations/kubernetes/test_k8s_applier.py::test_delete_from_inventory_404_is_skipped_and_other_errors_are_failed
tests/integration/integrations/kubernetes/test_k8s_applier.py::test_get_resource_found_and_not_found
tests/integration/integrations/kubernetes/test_k8s_applier.py::test_get_resource_propagates_non_404_api_errors
tests/integration/integrations/kubernetes/test_k8s_applier.py::test_list_resources_returns_items
tests/integration/integrations/kubernetes/test_k8s_applier.py::test_list_resources_raises_when_items_attribute_missing
tests/integration/integrations/kubernetes/test_k8s_applier.py::test_list_resources_raises_when_items_is_not_list
tests/integration/integrations/kubernetes/test_k8s_applier.py::test_wait_for_deployment_ready_happy_path
tests/integration/integrations/kubernetes/test_k8s_applier.py::test_wait_for_deployment_ready_times_out
tests/integration/integrations/kubernetes/test_k8s_applier.py::test_wait_for_service_loadbalancer_ip_happy_path
tests/integration/integrations/kubernetes/test_k8s_applier.py::test_wait_for_service_loadbalancer_ip_but_no_host_raises
tests/integration/integrations/kubernetes/test_k8s_applier.py::test_svc_lb_host_handles_ip_hostname_and_absence
tests/integration/integrations/kubernetes/test_k8s_template_engine.py::test_load_yaml_documents_multi_doc
tests/integration/integrations/kubernetes/test_k8s_template_engine.py::test_load_yaml_documents_list_format
tests/integration/integrations/kubernetes/test_k8s_template_engine.py::test_load_yaml_documents_empty_returns_empty_list
tests/integration/integrations/kubernetes/test_k8s_template_engine.py::test_load_yaml_documents_single_resource
tests/integration/integrations/kubernetes/test_k8s_template_engine.py::test_load_yaml_documents_invalid_yaml_raises_value_error
tests/integration/integrations/kubernetes/test_k8s_template_engine.py::test_load_yaml_documents_non_dict_or_list_doc_raises
tests/integration/integrations/kubernetes/test_k8s_template_engine.py::test_load_yaml_documents_list_with_non_dict_item_raises
tests/integration/integrations/kubernetes/test_k8s_template_engine.py::test_render_template_with_templating
tests/integration/integrations/kubernetes/test_k8s_template_engine.py::test_render_template_strict_undefined_raises_for_missing_variable
tests/integration/integrations/kubernetes/test_k8s_template_engine.py::test_render_template_non_strict_undefined_renders_blank_for_missing_variable
tests/integration/integrations/kubernetes/test_k8s_template_engine.py::test_render_template_invalid_yaml_after_rendering_raises
tests/integration/integrations/kubernetes/test_k8s_template_engine.py::test_render_template_round_trips_to_yaml_and_back
tests/integration/integrations/kubernetes/test_k8s_template_engine.py::test_render_template_does_not_autoescape_strings
tests/integration/integrations/kubernetes/test_serialization_utils.py::test_model_serialization_and_deserialization
tests/integration/integrations/kubernetes/test_serialization_utils.py::test_get_model_class
tests/integration/integrations/kubernetes/test_serialization_utils.py::test_serializing_invalid_model
tests/integration/integrations/kubernetes/test_serialization_utils.py::test_deserializing_invalid_model
tests/integration/integrations/label_studio/label_config_generators/test_label_config_generators.py::test_text_classification_label_config_generator
tests/integration/integrations/label_studio/label_config_generators/test_label_config_generators.py::test_image_classification_label_config_generator
tests/integration/integrations/label_studio/label_config_generators/test_label_config_generators.py::test_object_detection_label_config_generator
tests/integration/integrations/label_studio/label_config_generators/test_label_config_generators.py::test_ocr_label_config_generator
tests/integration/integrations/label_studio/label_config_generators/test_label_config_generators.py::test_config_generator_raises_with_empty_list
tests/integration/integrations/label_studio/test_label_studio_utils.py::test_is_s3_url
tests/integration/integrations/label_studio/test_label_studio_utils.py::test_is_azure_url
tests/integration/integrations/label_studio/test_label_studio_utils.py::test_is_gcs_url
tests/integration/integrations/label_studio/test_label_studio_utils.py::test_getting_file_extension
tests/integration/integrations/langchain/materializers/test_langchain_document_materializer.py::test_langchain_document_materializer
tests/integration/integrations/langchain/materializers/test_openai_embedding_materializer_materializer.py::test_langchain_openai_embedding_materializer
tests/integration/integrations/langchain/materializers/test_vector_store_materializer.py::test_langchain_vectorstore_materializer
tests/integration/integrations/lightgbm/materializers/test_lightgbm_booster_materializer.py::test_lightgbm_booster_materializer
tests/integration/integrations/lightgbm/materializers/test_lightgbm_dataset_materializer.py::test_lightgbm_dataset_materializer
tests/integration/integrations/mlflow/experiment_trackers/test_mlflow_experiment_tracker.py::test_mlflow_experiment_tracker_attributes
tests/integration/integrations/mlflow/experiment_trackers/test_mlflow_experiment_tracker.py::test_mlflow_experiment_tracker_stack_validation
tests/integration/integrations/mlflow/experiment_trackers/test_mlflow_experiment_tracker.py::test_mlflow_experiment_tracker_authentication
tests/integration/integrations/mlflow/experiment_trackers/test_mlflow_experiment_tracker.py::test_mlflow_experiment_tracker_set_config
tests/integration/integrations/mlflow/experiment_trackers/test_mlflow_experiment_tracker.py::test_mlflow_experiment_tracker_handles_missing_run
tests/integration/integrations/mlx/test_mlx_array_materializer.py::test_mlx_array_materializer
tests/integration/integrations/modal/step_operators/test_modal_step_operator.py::test_get_gpu_values
tests/integration/integrations/neptune/experiment_tracker/test_neptune_experiment_tracker.py::test_neptune_experiment_tracker_attributes
tests/integration/integrations/neptune/experiment_tracker/test_neptune_experiment_tracker.py::test_neptune_experiment_tracker_stack_validation
tests/integration/integrations/neptune/experiment_tracker/test_neptune_experiment_tracker.py::test_neptune_experiment_tracker_does_not_need_explicit_api_token_or_project
tests/integration/integrations/neural_prophet/materializers/test_neural_prophet_materializer.py::test_neural_prophet_booster_materializer
tests/integration/integrations/numpy/test_numpy_materializer.py::test_numpy_materializer
tests/integration/integrations/numpy/test_numpy_materializer.py::test_object_array_handling
tests/integration/integrations/numpy/test_numpy_materializer.py::test_numpy2_compatibility
tests/integration/integrations/numpy/test_numpy_materializer.py::test_integer_type_handling
tests/integration/integrations/pandas/test_pandas_materializer.py::test_pandas_materializer
tests/integration/integrations/pandas/test_pandas_materializer.py::test_pandas_materializer_with_index
tests/integration/integrations/pillow/materializers/test_pillow_image_materializer.py::test_materializer_works_for_pillow_image_objects
tests/integration/integrations/polars/materializers/test_polars_materializer.py::test_polars_materializer
tests/integration/integrations/pytorch/materializers/test_pytorch_dataloader_materializer.py::test_pytorch_dataloader_materializer
tests/integration/integrations/pytorch/materializers/test_pytorch_module_materializer.py::test_pytorch_module_materializer
tests/integration/integrations/runai/test_runai_step_operator.py::test_submit_publishes_workload_metadata
tests/integration/integrations/runai/test_runai_step_operator.py::test_get_status_maps_runai_status
tests/integration/integrations/runai/test_runai_step_operator.py::test_get_status_returns_failed_for_missing_status
tests/integration/integrations/runai/test_runai_step_operator.py::test_get_status_returns_failed_for_workload_not_found
tests/integration/integrations/runai/test_runai_step_operator.py::test_cancel_suspends_workload
tests/integration/integrations/runai/test_runai_step_operator.py::test_wait_returns_completed_on_success_status
tests/integration/integrations/runai/test_runai_step_operator.py::test_wait_preserves_failure_cleanup_behavior
tests/integration/integrations/runai/test_runai_step_operator.py::test_wait_preserves_timeout_cleanup_behavior
tests/integration/integrations/runai/test_runai_step_operator_flavor.py::test_runai_base_url_accepts_valid_urls
tests/integration/integrations/runai/test_runai_step_operator_flavor.py::test_runai_base_url_rejects_invalid_urls
tests/integration/integrations/s3/artifact_stores/test_s3_artifact_store.py::test_s3_artifact_store_attributes
tests/integration/integrations/s3/artifact_stores/test_s3_artifact_store.py::test_must_be_s3_path
tests/integration/integrations/s3/artifact_stores/test_s3_artifact_store.py::test_boto3_resource_receives_client_kwargs
tests/integration/integrations/s3/artifact_stores/test_s3_artifact_store.py::test_remove_previous_versions_uses_client_kwargs
tests/integration/integrations/s3/artifact_stores/test_s3_artifact_store.py::test_client_kwargs_region_overrides_credentials_region
tests/integration/integrations/s3/artifact_stores/test_s3_artifact_store.py::test_explicit_close_then_finalizer_does_not_raise
tests/integration/integrations/s3/artifact_stores/test_s3_artifact_store.py::test_close_session_called_twice_does_not_raise
tests/integration/integrations/s3/artifact_stores/test_s3_artifact_store.py::test_safe_aexit_propagates_unrelated_assertion_errors
tests/integration/integrations/s3/test_utils.py::test_split_s3_path_on_good_paths
tests/integration/integrations/s3/test_utils.py::test_split_s3_path_on_bad_paths
tests/integration/integrations/scipy/materializers/test_sparse_materializer.py::test_scipy_sparse_matrix_materializer
tests/integration/integrations/sklearn/materializers/test_sklearn_materializer.py::test_sklearn_materializer
tests/integration/integrations/skypilot/test_skypilot_orchestrator_entrypoint.py::test_generate_cluster_name_is_deterministic_and_bounded
tests/integration/integrations/skypilot/test_skypilot_orchestrator_entrypoint.py::test_resolve_pipeline_run_prefers_explicit_run_id
tests/integration/integrations/skypilot/test_skypilot_orchestrator_entrypoint.py::test_resolve_pipeline_run_raises_for_missing_explicit_run_id
tests/integration/integrations/skypilot/test_skypilot_orchestrator_entrypoint.py::test_resolve_pipeline_run_fallback_uses_latest_initializing_run
tests/integration/integrations/skypilot/test_skypilot_orchestrator_entrypoint.py::test_resolve_pipeline_run_fallback_raises_for_empty_results
tests/integration/integrations/skypilot/test_skypilot_utils.py::test_prepare_docker_setup_uses_password_stdin
tests/integration/integrations/skypilot/test_skypilot_utils.py::test_create_docker_run_command_uses_env_names_not_values
tests/integration/integrations/skypilot/test_skypilot_utils.py::test_create_docker_run_command_rejects_invalid_env_names
tests/integration/integrations/skypilot/test_skypilot_utils.py::test_prepare_resources_kwargs_omits_cloud_region_zone_when_infra_is_set
tests/integration/integrations/skypilot/test_skypilot_utils.py::test_prepare_resources_kwargs_rejects_conflicting_resources_settings
tests/integration/integrations/skypilot/test_skypilot_utils.py::test_prepare_launch_kwargs_filters_unsupported_keys
tests/integration/integrations/skypilot/test_skypilot_utils.py::test_sky_job_get_returns_waiter_when_streaming
tests/integration/integrations/skypilot/test_skypilot_utils.py::test_sky_job_get_is_non_blocking_without_streaming
tests/integration/integrations/skypilot/test_skypilot_utils.py::test_sky_job_get_rejects_malformed_response
tests/integration/integrations/skypilot/test_skypilot_utils.py::test_sky_job_get_rejects_non_integer_job_id
tests/integration/integrations/tensorflow/materializers/test_keras_materializer.py::test_tensorflow_keras_materializer
tests/integration/integrations/tensorflow/materializers/test_tf_dataset_materializer.py::test_tensorflow_tf_dataset_materializer
tests/integration/integrations/whylogs/materializers/test_whylogs_materializer.py::test_whylogs_materializer
tests/integration/integrations/xgboost/materializers/test_xgboost_dmatrix_materializer.py::test_xgboost_dmatrix_materializer

```

File: /Users/safoine/zenml-io/zenml/CONTRIBUTING.md
```md
# 🧑‍💻 Contributing to ZenML

A big welcome and thank you for considering contributing to ZenML! It’s people
like you that make it a reality for users
in our community.

Reading and following these guidelines will help us make the contribution
process easy and effective for everyone
involved. It also communicates that you agree to respect the developers' time
management and develop these open-source projects. In return, we will reciprocate that respect by reading your
issue, assessing changes, and helping
you finalize your pull requests.

## ⚡️ Quicklinks

- [🧑‍💻 Contributing to ZenML](#-contributing-to-zenml)
  - [⚡️ Quicklinks](#-quicklinks)
  - [🧑‍⚖️ Code of Conduct](#-code-of-conduct)
  - [🛫 Getting Started](#-getting-started)
    - [⁉️ Issues](#-issues)
    - [🏷 Pull Requests: When to make one](#-pull-requests-when-to-make-one)
    - [💯 Pull Requests: Workflow to Contribute](#-pull-requests-workflow-to-contribute)
    - [🧱 Pull Requests: Rebase on develop](#-pull-requests-rebase-your-branch-on-develop)
    - [🧐 Linting, formatting, and tests](#-linting-formatting-and-tests)
    - [🚨 Reporting a Vulnerability](#-reporting-a-vulnerability)
  - [Coding Conventions](#coding-conventions)
  - [👷 Creating a new Integration](#-creating-a-new-integration)
  - [🆘 Getting Help](#-getting-help)

## 🧑‍⚖️ Code of Conduct

We take our open-source community seriously and hold ourselves and other
contributors to high standards of communication.
By participating and contributing to this project, you agree to uphold
our [Code of Conduct](https://github.com/zenml-io/zenml/blob/master/CODE-OF-CONDUCT.md)
.

## 🛫 Getting Started

Contributions are made to this repo via Issues and Pull Requests (PRs). A few
general guidelines that cover both:

- To report security vulnerabilities, please get in touch
  at [support@zenml.io](mailto:support@zenml.io), monitored by
  our security team.
- Search for existing Issues and PRs before creating your own.
- We work hard to make sure issues are handled on time, but it could take a
  while to investigate the root cause depending on the impact.

A friendly ping in the comment thread to the submitter or a contributor can help
draw attention if your issue is blocking.

### Good First Issues for New Contributors

The best way to start is to check the
[`good-first-issue`](https://github.com/issues?q=is%3Aopen+is%3Aissue+archived%3Afalse+user%3Azenml-io+label%3A%22good+first+issue%22)
label on the issue board. The core team creates these issues as necessary
smaller tasks that you can work on to get deeper into ZenML internals. These
should generally require relatively simple changes, probably affecting just one
or two files which we think are ideal for people new to ZenML.

The next step after that would be to look at the
[`good-second-issue`](https://github.com/issues?q=is%3Aopen+is%3Aissue+archived%3Afalse+user%3Azenml-io+label%3A%22good+second+issue%22)
label on the issue board. These are a bit more complex, might involve more
files, but should still be well-defined and achievable to people relatively new
to ZenML.

### ⁉️ Issues

Issues should be used to report problems with the library, request a new
feature, or to discuss potential changes before
a PR is created. When you create a new Issue, a template will be loaded that
will guide you through collecting and
providing the information we need to investigate.

If you find an Issue that addresses your problem, please add your own
reproduction information to the
existing issue rather than creating a new one. Adding
a [reaction](https://github.blog/2016-03-10-add-reactions-to-pull-requests-issues-and-comments/)
can also help by
indicating to our maintainers that a particular issue is affecting more than
just the reporter.

### 🏷 Pull Requests: When to make one

Pull Requests (PRs) to ZenML are always welcome and can be a quick way to get your fix or
improvement slated for the next release. In
general, PRs should:

- Only fix/add the functionality in question **OR** address widespread
  whitespace/style issues, not both.
- Add unit or integration tests for fixed or changed functionality (if a test
  suite already exists).
- Address a single concern in the least number of changed lines as possible.
- Include documentation in the repo or in your Pull Request.
- Be accompanied by a filled-out Pull Request template (loaded automatically when
  a PR is created).

For changes that address core functionality or would require breaking changes (e.g. a major release), it's best to open
an Issue to discuss your proposal first. This is not required but can save time
creating and reviewing changes.

### 💯 Pull Requests: Workflow to Contribute

<p class="callout warning">Please note that development in ZenML happens off of the <b>develop</b> branch, <b>not main</b>, 
which is the default branch on GitHub. Therefore, please pay particular attention to step 5 and step 9 below. </p>

In general, we follow
the ["fork-and-pull" Git workflow](https://github.com/susam/gitpr)

1. Review and sign
   the [Contributor License Agreement](https://cla-assistant.io/zenml-io/zenml) (
   CLA).
2. Fork the repository to your own Github account.
3. Clone the project to your machine.
4. Checkout the **develop** branch <- `git checkout develop`.
5. Create a branch (again, off of the develop branch) locally with a succinct but descriptive name.
6. Commit changes to the branch
7. Follow the `Linting, formatting, and tests` guide to make sure your code adheres to the ZenML coding style (see below).
8. Push changes to your fork.
9. Open a PR in our repository (to the `develop` branch, **NOT** `main`) and
   follow the PR template so that we can efficiently review the changes.

### 🧱 Pull Requests: Rebase Your Branch on Develop

1. When making pull requests to ZenML, you should always make your changes on a branch that is based on `develop`. You can create a new branch based on `develop` by running the following command:
   ```
   git checkout -b <new-branch-name> develop
   ```
2. Fetch the latest changes from the remote `develop` branch:
   ```
   git fetch origin develop
   ```
3. Switch to your branch:
   ```
   git checkout <your-branch-name>
   ```
4. Rebase your branch on `develop`:
   ```
   git rebase origin/develop
   ```
   This will apply your branch's changes on top of the latest changes in `develop`, one commit at a time.
5. Resolve any conflicts that may arise during the rebase. Git will notify you if there are any conflicts that need to be resolved. Use a text editor to manually resolve the conflicts in the affected files.
6. After resolving the conflicts, stage the changes:
   ```
   git add .
   ```
7. Continue the rebase for all of your commits and go to 5) if there are conflicts.
   ```
   git rebase --continue
   ```
8. Push the rebased branch to your remote repository:
   ```
   git push origin --force <your-branch-name>
   ```
9. Open a pull request targeting the `develop` branch. The changes from your rebased branch will now be based on the latest `develop` branch.

### 🧐 Linting, formatting, and tests

To install ZenML from your local checked out files including all core dev-dependencies, run:

```
pip install -e ".[server,dev]"
```

Optionally, you might want to run the following commands to ensure you have all
integrations for `mypy` checks:

```
zenml integration install -y -i feast
pip install click~=8.0.3
mypy --install-types
```

Warning: This might take a while for both (~ 15 minutes each, depending on your machine), however if you have
time, please run it as it will make the
next commands error-free. Note that the `zenml integration install` command
might also fail on account of dependency conflicts so you can just install the
specific integration you're working on and manually run the mypy command for the
files you've been working on.

You can now run the following scripts to automatically format your
code and to check whether the code formatting, linting, docstrings, and
spelling is in order:

```
bash scripts/format.sh
bash scripts/run-ci-checks.sh
```

If you're on Windows you might have to run the formatting script as `bash
scripts/format.sh --no-yamlfix` and run the yamlfix command separately as
`yamlfix .github -v`.

Tests can be run as follows:

```
bash scripts/test-coverage-xml.sh
```

Please note that it is good practice to run the above commands before submitting
any Pull Request: The CI GitHub Action
will run it anyway, so you might as well catch the errors locally!

The CI captain rotation lives in `.github/ci-captains.yml`. The weekly captain
is the first responder for `develop-red` incidents opened by nightly slow CI and
backs up the authors identified in the suspect commit range.

### 🚨 Reporting a Vulnerability

Please refer to [our security / reporting instructions](./SECURITY.md) for
details on reporting vulnerabilities.


## Coding Conventions

The code within the repository is structured in the following way - 
the most relevant places for contributors are highlighted with a `<-` arrow:

```
├── .github           -- Definition of the GH action workflows
├── docker            -- Dockerfiles used to build ZenML docker images
├── docs              <- The ZenML docs, CLI docs and API docs live here
│   ├── book          <- In case you make user facing changes, update docs here
│   └── mkdocs        -- Some configurations for the API/CLI docs
├── examples          <- When adding an integration, add an example here
├── scripts           -- Scripts used by Github Actions or for local linting/testing
├── src/zenml         <- The heart of ZenML
│   ├── <stack_component>   <- Each stack component has its own directory 
│   ├── cli                 <- Change and improve the CLI here
│   ├── config              -- The ZenML config methods live here
│   ├── integrations        <- Add new integrations here
│   ├── io                  -- File operation implementations
│   ├── materializers       <- Materializers responsible for reading/writing artifacts
│   ├── pipelines           <- The base pipeline and its decorator
│   ├── services            -- Code responsible for managing services
│   ├── stack               <- Stack, Stack Components and the flavor registry
│   ├── steps               <- Steps and their decorators are defined here
│   ├── utils               <- Collection on useful utils
│   ├── zen_server          -- Code for running the Zen Server
│   └── zen_stores          -- Code for storing stacks in multiple settings
└── test              <- Don't forget to write unit tests for your code
```

## 👷 Creating a new Integration

In case you want to create an entirely new integration that you would like to 
see supported by ZenML there are a few steps that you should follow:

1. Create the actual integration. Check out the 
[Integrations README](src/zenml/integrations/README.md)
for detailed step-by-step instructions.
2. Create an example of how to use the integration. Check out the 
[Examples README](examples/README.md) 
to find out what to do.
3. All integrations deserve to be documented. Make sure to pay a visit to the
[Component Guide](https://docs.zenml.io/stack-components/component-guide)
in the docs and add your implementations. 

## 🆘 Getting Help

Join us in the [ZenML Slack Community](https://zenml.io/slack-invite/) to 
interact directly with the core team and community at large. This is a good 
place to ideate, discuss concepts or ask for help.

```

File: /Users/safoine/zenml-io/zenml/.github/workflows/ci-fast.yml
```yml
---
name: ci-fast
on:
  workflow_dispatch:
  workflow_call:
  merge_group:
  push:
    branches: [develop]
  pull_request:
    types: [opened, synchronize, ready_for_review]
concurrency:
  # New commit on branch cancels running workflows of the same branch.
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
jobs:
  sqlite-db-migration-testing-random:
    runs-on: ubuntu-latest
    env:
      ZENML_ANALYTICS_OPT_IN: false
      ZENML_DEBUG: true
    if: github.event_name != 'pull_request' || github.event.pull_request.draft ==
      false
    steps:
      - name: Checkout code
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
        with:
          fetch-depth: 0
      - name: Set up Python 3.10
        uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405  # v6.2.0
        with:
          python-version: '3.10'
      - name: Test migrations across versions
        run: bash scripts/test-migrations.sh sqlite random
  spellcheck:
    if: github.event_name != 'pull_request' || github.event.pull_request.draft ==
      false
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
      - name: Spelling checker
        uses: crate-ci/typos@7c572958218557a3272c2d6719629443b5cc26fd  # v1.45.2
        with:
          files: .
          config: ./.typos.toml
  api-docs-test:
    if: github.event_name != 'pull_request' || github.event.pull_request.draft ==
      false
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
      - name: Set up Python 3.11
        uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405  # v6.2.0
        with:
          python-version: '3.11'
      - name: Test API docs buildable
        run: bash scripts/generate-docs.sh -v DUMMY -c
  update-templates-to-examples:
    if: github.event_name == 'pull_request' && github.event.pull_request.head.repo.full_name
      == 'zenml-io/zenml' && github.event.pull_request.draft == false
    uses: ./.github/workflows/update-templates-to-examples.yml
    with:
      python-version: '3.11'
      os: ubuntu-latest
    secrets: inherit
  linting:
    if: github.event_name != 'pull_request' || github.event.pull_request.draft ==
      false
    strategy:
      matrix:
        os: [ubuntu-latest]
        python-version: ['3.11']
      fail-fast: false
    uses: ./.github/workflows/linting.yml
    with:
      python-version: ${{ matrix.python-version }}
      os: ${{ matrix.os }}
    secrets: inherit
  linux-fast-offload:
    if: github.event_name != 'pull_request' || github.event.pull_request.draft ==
      false
    uses: ./.github/workflows/linux-fast-offload.yml
    with:
      backend: modal
      python-version: '3.13'
      use-offload: true
    secrets: inherit
  linux-fast-offload-modal-mysql:
    if: github.event_name != 'pull_request' || (github.event.pull_request.draft ==
      false && github.event.pull_request.head.repo.full_name == github.repository)
    uses: ./.github/workflows/linux-fast-offload.yml
    with:
      backend: modal
      python-version: '3.13'
      use-offload: true
      test_environment: modal-server-mysql
    secrets: inherit
  ci-fast-required:
    runs-on: ubuntu-latest
    needs:
      - sqlite-db-migration-testing-random
      - spellcheck
      - api-docs-test
      - update-templates-to-examples
      - linting
      - linux-fast-offload
      - linux-fast-offload-modal-mysql
    if: always()
    steps:
      - name: Verify required fast CI jobs
        env:
          NEEDS_CONTEXT: ${{ toJSON(needs) }}
        run: |-
          python - <<'PY'
          import json
          import os
          import sys
          failed = []
          for name, data in json.loads(os.environ["NEEDS_CONTEXT"]).items():
              result = data["result"]
              if result not in {"success", "skipped"}:
                  failed.append(f"{name}: {result}")
          if failed:
              print("Fast CI dependencies failed:")
              print("\n".join(failed))
              sys.exit(1)
          print("All fast CI dependencies passed or were skipped by design.")
          PY

```

File: /Users/safoine/zenml-io/zenml/.github/workflows/base-package-functionality.yml
```yml
---
name: Test base package functionality
on:
  workflow_call:
    inputs:
      os:
        description: OS
        type: string
        required: true
      python-version:
        description: Python version
        type: string
        required: true
      git-ref:
        description: Git branch or ref
        type: string
        required: false
        default: ''
  workflow_dispatch:
    inputs:
      os:
        description: OS
        type: choice
        options: [ubuntu-latest, macos-13, windows-latest]
        required: false
        default: ubuntu-latest
      python-version:
        description: Python version
        type: choice
        options: ['3.10', '3.11', '3.12', '3.13']
        required: false
        default: '3.11'
      git-ref:
        description: Git branch or ref
        type: string
        required: true
jobs:
  test-base-package-functionality:
    name: test-base-package-functionality
    runs-on: ${{ inputs.os }}
    env:
      ZENML_DEBUG: 1
      ZENML_ANALYTICS_OPT_IN: false
      PYTHONIOENCODING: utf-8
      UV_HTTP_TIMEOUT: 600
      OBJC_DISABLE_INITIALIZE_FORK_SAFETY: 'YES'
    if: ${{ ! startsWith(github.event.head_commit.message, 'GitBook:') && ! (inputs.os == 'windows-latest' && inputs.python-version == '3.11') && ! (inputs.os == 'windows-latest' && inputs.python-version == '3.12') }}
    defaults:
      run:
        shell: bash
    steps:
      - name: Checkout code
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
        with:
          repository: ${{ github.repository }}
          ref: ${{ inputs.git-ref || github.event.pull_request.head.sha || github.sha }}
      - name: Set up Python
        uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405  # v6.2.0
        with:
          python-version: ${{ inputs.python-version }}
      - name: Install uv
        uses: astral-sh/setup-uv@08807647e7069bb48b6ef5acd8ec9567f424441b  # v8.1.0
        with:
          version: 0.8.14
      - name: Build server image
        run: |
          docker build -t zenml-server-dev -f docker/zenml-server-dev.Dockerfile .
      - name: Install base package
        run: |
          uv pip install --system .
      - name: Start local server
        run: |
          docker run -d -p 8080:8080 -e ZENML_SERVER_AUTH_SCHEME=NO_AUTH -e ZENML_SERVER_AUTO_ACTIVATE=True zenml-server-dev
      - name: Test server connection works
        env:
          ZENML_STORE_URL: http://localhost:8080
        run: |-
          zenml stack list

```

File: /Users/safoine/zenml-io/zenml/scripts/ci/print_junit_failures.py
```py
"""Print failed test cases from JUnit XML files."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def _case_label(case: ET.Element) -> str:
    classname = case.attrib.get("classname", "")
    name = case.attrib.get("name", "<unknown>")
    return f"{classname}.{name}" if classname else name


def _print_outcome(case: ET.Element, outcome: ET.Element) -> None:
    message = outcome.attrib.get("message", "")
    outcome_type = outcome.attrib.get("type", outcome.tag)
    print(f"- {_case_label(case)} [{outcome_type}] {message}".rstrip())
    if outcome.text and outcome.text.strip():
        print(outcome.text.strip())


def print_failures(path: str | Path, *, limit: int = 50) -> int:
    """Print failed and errored test cases and return the number printed."""
    root = ET.parse(path).getroot()
    printed = 0
    for case in root.iter("testcase"):
        for outcome in list(case):
            if outcome.tag not in {"failure", "error"}:
                continue
            if printed == 0:
                print("Failed tests:")
            if printed >= limit:
                print(f"... truncated after {limit} failures/errors")
                return printed
            _print_outcome(case, outcome)
            printed += 1
    return printed


def main(argv: list[str]) -> int:
    """CLI entrypoint."""
    if len(argv) != 2:
        print(f"Usage: {argv[0]} <junit.xml>", file=sys.stderr)
        return 2
    print_failures(argv[1])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

```

File: /Users/safoine/zenml-io/zenml/.github/workflows/slow-ci-on-pr.yml
```yml
---
name: slow-ci-on-pr
on:
  pull_request:
    types: [opened, synchronize, ready_for_review, labeled]
  workflow_dispatch:
    inputs:
      git-ref:
        description: Git branch, tag, or SHA to test
        type: string
        required: false
        default: ''
concurrency:
  group: ${{ github.workflow }}-${{ github.event.pull_request.number || inputs.git-ref
    || github.ref }}
  cancel-in-progress: true
jobs:
  run-slow-ci-label-is-set:
    runs-on: ubuntu-latest
    if: github.event_name != 'pull_request' || github.event.pull_request.draft ==
      false
    outputs:
      should-run: ${{ steps.decision.outputs.should-run }}
    steps:
      - name: Decide whether advisory slow CI should run
        id: decision
        uses: actions/github-script@ed597411d8f924073f98dfc5c65a23a2325f34cd  # v8.0.0
        with:
          script: |
            if (context.eventName !== 'pull_request') {
              core.setOutput('should-run', 'true');
              return;
            }
            const prNumber = context.payload.pull_request.number;
            const { data: labels } = await github.rest.issues.listLabelsOnIssue({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: prNumber,
            });
            const hasLabel = labels.some(label => label.name === 'run-slow-ci');
            core.setOutput('should-run', hasLabel ? 'true' : 'false');
            if (!hasLabel) {
              core.notice('Skipping advisory slow CI because run-slow-ci is not set.');
            }
  advisory-slow-ci:
    needs: run-slow-ci-label-is-set
    if: needs.run-slow-ci-label-is-set.outputs.should-run == 'true'
    uses: ./.github/workflows/ci-slow-develop.yml
    with:
      git-ref: ${{ inputs.git-ref || github.event.pull_request.head.sha }}
    secrets: inherit

```

File: /Users/safoine/zenml-io/zenml/tests/unit/scripts/ci/test_offload_config.py
```py
"""Tests for offload CI configuration files."""

from __future__ import annotations

from pathlib import Path

import tomllib


def test_fast_offload_config_is_valid() -> None:
    """Default fast offload config has the expected shape."""
    config = tomllib.loads(Path("offload.toml").read_text())

    assert config["offload"]["max_parallel"] == 20
    assert config["offload"]["max_batch_duration_secs"] == 320
    assert config["provider"]["type"] == "default"
    assert config["report"]["output_dir"] == ".ci/offload"
    assert set(config["groups"]) == {"unit", "integration"}
    assert config["groups"]["unit"]["filters"] == "tests/unit"
    assert "tests/integration" in config["groups"]["integration"]["filters"]
    assert "not slow" in config["groups"]["integration"]["filters"]
    assert config["framework"]["run_args"].startswith(
        "--no-provision --environment default"
    )


def test_offload_dockerfile_does_not_bake_source_before_dependencies() -> None:
    """Code-only changes should not invalidate the dependency image layer."""
    dockerfile = Path("Dockerfile.ci").read_text()
    dockerignore = Path("Dockerfile.ci.dockerignore").read_text()

    assert "COPY . ." not in dockerfile
    assert "integration-requirements.txt" in dockerfile
    assert "!.ci/offload/integration-requirements.txt" in dockerignore


def test_modal_mysql_offload_config_is_valid() -> None:
    """Modal/MySQL offload config targets the remote server environment."""
    config = tomllib.loads(Path("offload-modal-server-mysql.toml").read_text())

    assert config["offload"]["max_parallel"] == 20
    assert config["offload"]["max_batch_duration_secs"] == 320
    assert config["provider"]["type"] == "default"
    assert config["report"]["output_dir"] == ".ci/offload"
    assert set(config["groups"]) == {"unit", "integration"}
    assert config["groups"]["unit"]["filters"] == "tests/unit"
    assert "tests/integration" in config["groups"]["integration"]["filters"]
    assert "not slow" in config["groups"]["integration"]["filters"]
    assert config["framework"]["command"].startswith(
        "python scripts/ci/run_mixed_environment_pytest.py"
    )
    assert config["framework"]["run_args"].startswith(
        "--no-provision --environment default"
    )
    assert "MODAL_CI_SERVER_URL" in config["provider"]["create_command"]

```

File: /Users/safoine/zenml-io/zenml/tests/unit/scripts/ci/test_print_junit_summary.py
```py
"""Tests for JUnit summary parsing."""

from __future__ import annotations

from pathlib import Path

from scripts.ci.print_junit_summary import parse_junit_summary


def test_parse_single_testsuite(tmp_path: Path) -> None:
    """A single testsuite root is parsed directly."""
    junit = tmp_path / "junit.xml"
    junit.write_text(
        '<testsuite tests="3" failures="1" errors="0" skipped="1" time="2.5" />'
    )

    summary = parse_junit_summary(junit)

    assert summary.tests == 3
    assert summary.failures == 1
    assert summary.errors == 0
    assert summary.skipped == 1
    assert summary.time == 2.5


def test_parse_testsuites(tmp_path: Path) -> None:
    """Multiple testsuite children are aggregated."""
    junit = tmp_path / "junit.xml"
    junit.write_text(
        """
        <testsuites>
          <testsuite tests="2" failures="0" errors="1" skipped="0" time="1.0" />
          <testsuite tests="4" failures="1" errors="0" skipped="2" time="3.0" />
        </testsuites>
        """
    )

    summary = parse_junit_summary(junit)

    assert summary.tests == 6
    assert summary.failures == 1
    assert summary.errors == 1
    assert summary.skipped == 2
    assert summary.time == 4.0

```

File: /Users/safoine/zenml-io/zenml/Dockerfile.ci.dockerignore
```dockerignore
*
!.dockerignore
!Dockerfile.ci
!Dockerfile.ci.dockerignore
!.ci
!.ci/offload
!.ci/offload/integration-requirements.txt
!examples
!examples/**
!LICENSE
!README.md
!alembic.ini
!offload-modal-server-mysql.toml
!offload.toml
!pyproject.toml
!scripts
!scripts/**
!src
!src/**
!tests
!tests/**
!uv.lock
!zen-dev
!zen-dev/**
!zen-test
!zen-test/**
**/__pycache__
**/__pycache__/**
**/*.py[cod]
**/.pytest_cache
**/.pytest_cache/**
**/.mypy_cache
**/.mypy_cache/**
**/.ruff_cache
**/.ruff_cache/**

```

File: /Users/safoine/zenml-io/zenml/.github/workflows/ci-slow-develop.yml
```yml
---
name: ci-slow-develop
on:
  schedule:
    - cron: 0 0 * * *
  workflow_dispatch:
    inputs:
      git-ref:
        description: Git branch or ref to qualify
        type: string
        required: false
        default: develop
permissions:
  contents: read
  checks: write
  issues: write
concurrency:
  group: ${{ github.workflow }}-${{ inputs.git-ref || 'develop' }}
  cancel-in-progress: false
jobs:
  resolve-ref:
    runs-on: ubuntu-latest
    outputs:
      git-ref: ${{ steps.ref.outputs.git-ref }}
    steps:
      - id: ref
        env:
          GIT_REF: ${{ inputs.git-ref || 'develop' }}
        run: echo "git-ref=${GIT_REF}" >> "$GITHUB_OUTPUT"
  mysql-db-migration-testing-random:
    needs: resolve-ref
    env:
      ZENML_ANALYTICS_OPT_IN: false
      ZENML_DEBUG: true
      RANDOM_MIGRATION_COUNT: 5
      RANDOM_MIGRATION_SEED: ${{ github.run_number }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
        with:
          ref: ${{ needs.resolve-ref.outputs.git-ref }}
          fetch-depth: 0
      - name: Set up Python 3.10
        uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405  # v6.2.0
        with:
          python-version: '3.10'
      - name: Login to Docker Hub
        uses: docker/login-action@4907a6ddec9925e35a0a9e82d7399ccc52663121  # v4.1.0
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}
      - name: Test random migrations
        run: bash scripts/test-migrations.sh mysql random
  sqlite-db-migration-testing-random:
    needs: resolve-ref
    env:
      ZENML_ANALYTICS_OPT_IN: false
      ZENML_DEBUG: true
      RANDOM_MIGRATION_COUNT: 5
      RANDOM_MIGRATION_SEED: ${{ github.run_number }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
        with:
          ref: ${{ needs.resolve-ref.outputs.git-ref }}
          fetch-depth: 0
      - name: Set up Python 3.10
        uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405  # v6.2.0
        with:
          python-version: '3.10'
      - name: Test random migrations
        run: bash scripts/test-migrations.sh sqlite random
  mariadb-db-migration-testing-random:
    needs: resolve-ref
    env:
      ZENML_ANALYTICS_OPT_IN: false
      ZENML_DEBUG: true
      RANDOM_MIGRATION_COUNT: 5
      RANDOM_MIGRATION_SEED: ${{ github.run_number }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
        with:
          ref: ${{ needs.resolve-ref.outputs.git-ref }}
          fetch-depth: 0
      - name: Set up Python 3.10
        uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405  # v6.2.0
        with:
          python-version: '3.10'
      - name: Login to Docker Hub
        uses: docker/login-action@4907a6ddec9925e35a0a9e82d7399ccc52663121  # v4.1.0
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}
      - name: Test random migrations
        run: bash scripts/test-migrations.sh mariadb random
  small-checks:
    needs: resolve-ref
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
        with:
          ref: ${{ needs.resolve-ref.outputs.git-ref }}
      - name: Set up Python
        uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405  # v6.2.0
        with:
          python-version: '3.11'
      - name: Install uv
        run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          source $HOME/.cargo/env
      - name: Create virtual environment
        run: uv venv
      - name: Check for broken dependencies
        run: |
          source .venv/bin/activate
          uv pip check
      - name: Markdown link check
        uses: gaurav-nelson/github-action-markdown-link-check@3c3b66f1f7d0900e37b71eca45b63ea9eedfce31  # 1.0.17
        with:
          use-quiet-mode: 'yes'
          use-verbose-mode: 'no'
          folder-path: ./examples, ./docs/book, ./src
          file-path: ./README.md, ./LICENSE, ./RELEASE_NOTES.md, CODE-OF-CONDUCT.md,
            CONTRIBUTING.md, CLA.md, RELEASE_NOTES.md, ROADMAP.md
          config-file: .github/workflows/markdown_check_config.json
        continue-on-error: true
      - name: Security check
        run: |
          source .venv/bin/activate
          uv pip install bandit
          bash scripts/check-security.sh
      - name: Check for alembic branch divergence
        env:
          ZENML_DEBUG: 0
        run: |
          source .venv/bin/activate
          uv pip install alembic
          bash scripts/check-alembic-branches.sh
      - name: Install latest dashboard (test gitignore)
        run: bash scripts/install-dashboard.sh
  ubuntu-linting:
    needs: resolve-ref
    strategy:
      matrix:
        os: [ubuntu-latest]
        python-version: ['3.10', '3.12', '3.13']
      fail-fast: false
    uses: ./.github/workflows/linting.yml
    with:
      python-version: ${{ matrix.python-version }}
      os: ${{ matrix.os }}
      git-ref: ${{ needs.resolve-ref.outputs.git-ref }}
    secrets: inherit
  ubuntu-unit-test:
    needs: [resolve-ref, ubuntu-linting]
    strategy:
      matrix:
        os: [ubuntu-latest]
        python-version: ['3.10', '3.12', '3.13']
      fail-fast: false
    uses: ./.github/workflows/unit-test.yml
    with:
      python-version: ${{ matrix.python-version }}
      os: ${{ matrix.os }}
      git-ref: ${{ needs.resolve-ref.outputs.git-ref }}
    secrets: inherit
  windows-linting:
    needs: resolve-ref
    strategy:
      matrix:
        os: [windows-latest]
        python-version: ['3.10', '3.11', '3.12', '3.13']
      fail-fast: false
    uses: ./.github/workflows/linting.yml
    with:
      python-version: ${{ matrix.python-version }}
      os: ${{ matrix.os }}
      git-ref: ${{ needs.resolve-ref.outputs.git-ref }}
    secrets: inherit
  windows-unit-test:
    needs: [resolve-ref, windows-linting]
    strategy:
      matrix:
        os: [windows-latest]
        python-version: ['3.10', '3.11', '3.12', '3.13']
      fail-fast: false
    uses: ./.github/workflows/unit-test.yml
    with:
      python-version: ${{ matrix.python-version }}
      os: ${{ matrix.os }}
      git-ref: ${{ needs.resolve-ref.outputs.git-ref }}
    secrets: inherit
  macos-linting:
    needs: resolve-ref
    strategy:
      matrix:
        os: [macos-latest]
        python-version: ['3.10', '3.11', '3.12', '3.13']
      fail-fast: false
    uses: ./.github/workflows/linting.yml
    with:
      python-version: ${{ matrix.python-version }}
      os: ${{ matrix.os }}
      git-ref: ${{ needs.resolve-ref.outputs.git-ref }}
    secrets: inherit
  macos-unit-test:
    needs: [resolve-ref, macos-linting]
    strategy:
      matrix:
        os: [macos-latest]
        python-version: ['3.10', '3.11', '3.12', '3.13']
      fail-fast: false
    uses: ./.github/workflows/unit-test.yml
    with:
      python-version: ${{ matrix.python-version }}
      os: ${{ matrix.os }}
      install_integrations: 'yes'
      reruns: 1
      git-ref: ${{ needs.resolve-ref.outputs.git-ref }}
    secrets: inherit
  windows-integration-test:
    needs: [resolve-ref, windows-unit-test]
    strategy:
      matrix:
        os: [windows-latest]
        python-version: ['3.10', '3.11', '3.12', '3.13']
        test_environment: [default]
      fail-fast: false
    uses: ./.github/workflows/integration-test-slow.yml
    with:
      os: ${{ matrix.os }}
      python-version: ${{ matrix.python-version }}
      test_environment: ${{ matrix.test_environment }}
      git-ref: ${{ needs.resolve-ref.outputs.git-ref }}
    secrets: inherit
  macos-integration-test:
    needs: [resolve-ref, macos-unit-test]
    strategy:
      matrix:
        os: [macos-latest]
        python-version: ['3.10', '3.11', '3.12', '3.13']
        test_environment: [default]
      fail-fast: false
    uses: ./.github/workflows/integration-test-slow.yml
    with:
      os: ${{ matrix.os }}
      python-version: ${{ matrix.python-version }}
      test_environment: ${{ matrix.test_environment }}
      git-ref: ${{ needs.resolve-ref.outputs.git-ref }}
    secrets: inherit
  ubuntu-latest-integration-test:
    needs: [resolve-ref, ubuntu-unit-test]
    strategy:
      matrix:
        os: [ubuntu-latest]
        python-version: ['3.10', '3.11', '3.13']
        test_environment:
          - default
          - docker-server-docker-orchestrator-mysql
          - docker-server-docker-orchestrator-mariadb
        exclude:
          - test_environment: docker-server-docker-orchestrator-mysql
            python-version: '3.10'
          - test_environment: docker-server-docker-orchestrator-mysql
            python-version: '3.13'
          - test_environment: docker-server-docker-orchestrator-mariadb
            python-version: '3.10'
          - test_environment: docker-server-docker-orchestrator-mariadb
            python-version: '3.13'
      fail-fast: false
    uses: ./.github/workflows/integration-test-slow.yml
    with:
      os: ${{ matrix.os }}
      python-version: ${{ matrix.python-version }}
      test_environment: ${{ matrix.test_environment }}
      git-ref: ${{ needs.resolve-ref.outputs.git-ref }}
    secrets: inherit
  vscode-tutorial-pipelines-test:
    needs: resolve-ref
    uses: ./.github/workflows/vscode-tutorial-pipelines-test.yml
    with:
      git-ref: ${{ needs.resolve-ref.outputs.git-ref }}
    secrets: inherit
  ubuntu-base-package-functionality:
    needs: resolve-ref
    strategy:
      matrix:
        os: [ubuntu-latest]
        python-version: ['3.11']
      fail-fast: false
    uses: ./.github/workflows/base-package-functionality.yml
    with:
      python-version: ${{ matrix.python-version }}
      os: ${{ matrix.os }}
      git-ref: ${{ needs.resolve-ref.outputs.git-ref }}
    secrets: inherit
  publish-qualification-success:
    needs:
      - resolve-ref
      - mysql-db-migration-testing-random
      - sqlite-db-migration-testing-random
      - mariadb-db-migration-testing-random
      - small-checks
      - ubuntu-unit-test
      - windows-unit-test
      - macos-unit-test
      - windows-integration-test
      - macos-integration-test
      - ubuntu-latest-integration-test
      - vscode-tutorial-pipelines-test
      - ubuntu-base-package-functionality
    if: success()
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
        with:
          ref: ${{ needs.resolve-ref.outputs.git-ref }}
          fetch-depth: 0
      - name: Publish qualification Check Run
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: python scripts/publish_ci_qualification.py --conclusion success
  publish-qualification-failure:
    needs:
      - resolve-ref
      - mysql-db-migration-testing-random
      - sqlite-db-migration-testing-random
      - mariadb-db-migration-testing-random
      - small-checks
      - ubuntu-unit-test
      - windows-unit-test
      - macos-unit-test
      - windows-integration-test
      - macos-integration-test
      - ubuntu-latest-integration-test
      - vscode-tutorial-pipelines-test
      - ubuntu-base-package-functionality
    if: failure()
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
        with:
          ref: ${{ needs.resolve-ref.outputs.git-ref }}
          fetch-depth: 0
      - name: Publish failure Check Run and incident
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: python scripts/publish_ci_qualification.py --conclusion failure --incident

```

File: /Users/safoine/zenml-io/zenml/scripts/validate_quarantine.py
```py
#!/usr/bin/env python3
"""Validate the CI quarantine registry."""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import yaml

REQUIRED_FIELDS = {
    "test_id",
    "owner",
    "quarantined_at",
    "expiry",
    "tracking_issue",
    "reason",
    "skip_in",
}


def _parse_date(value: object) -> dt.date:
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(str(value))


def main() -> None:
    """Run the CLI."""
    path = Path(".github/quarantined-tests.yml")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    errors: list[str] = []

    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")

    for index, entry in enumerate(data.get("quarantined", [])):
        missing = REQUIRED_FIELDS - set(entry)
        if missing:
            errors.append(
                f"entry {index} is missing fields: {sorted(missing)}"
            )
            continue
        quarantined_at = _parse_date(entry["quarantined_at"])
        expiry = _parse_date(entry["expiry"])
        if expiry <= dt.date.today():
            errors.append(f"{entry['test_id']} has an expired quarantine")
        if expiry > quarantined_at + dt.timedelta(days=30):
            errors.append(
                f"{entry['test_id']} expiry is more than 30 days out"
            )
        if not str(entry["owner"]).strip():
            errors.append(f"{entry['test_id']} owner is empty")
        if not str(entry["tracking_issue"]).startswith("https://github.com/"):
            errors.append(
                f"{entry['test_id']} tracking_issue must be a GitHub URL"
            )
        if "medium" not in entry.get("skip_in", []):
            errors.append(
                f"{entry['test_id']} must declare where it is skipped"
            )

    if errors:
        for error in errors:
            print(f"::error::{error}")
        sys.exit(1)


if __name__ == "__main__":
    main()

```

File: /Users/safoine/zenml-io/zenml/tests/integration/examples/utils.py
```py
"""Utilities for running integration example tests."""

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
import logging
import os
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Generator, List, Optional, Set, Tuple

import pytest

from zenml.client import Client
from zenml.enums import ExecutionStatus
from zenml.models import PipelineRunResponse
from zenml.utils.pagination_utils import depaginate

if TYPE_CHECKING:
    from uuid import UUID

    from zenml.models import PipelineBuildResponse, PipelineResponse


DEFAULT_PIPELINE_RUN_START_TIMEOUT = 30
DEFAULT_PIPELINE_RUN_FINISH_TIMEOUT = 300


class IntegrationTestExample:
    """Class to encapsulate an integration test example."""

    def __init__(self, path: Path, name: str) -> None:
        """Create a new example instance.

        Args:
            name: The name to the example
            path: Path at which the example code lives.
        """
        self.name = name
        self.path = path

        # Make sure the example has a `run.py` file
        self.run_dot_py_file = os.path.join(self.path, "run.py")
        if not os.path.exists(self.run_dot_py_file):
            raise RuntimeError(
                f"No `run.py` file found in example {self.name}. "
                f"{self.run_dot_py_file} does not exist."
            )

    def __call__(self, *args: str) -> None:
        """Runs the example directly without going through setup/teardown.

        Args:
            *args: Arguments to pass to the example.

        Raises:
            RuntimeError: If running the example fails.
        """
        env = os.environ.copy()
        # Disable Rich traceback in subprocesses so that if an exception
        # occurs during interpreter shutdown, the default excepthook
        # writes the traceback before the pipe closes (Rich's handler
        # can fail with "Error in sys.excepthook:" on Python 3.10).
        env.setdefault("ZENML_ENABLE_RICH_TRACEBACK", "false")
        # Disable whylogs anonymous usage stats to avoid background HTTP
        # threads that can raise exceptions during interpreter shutdown.
        env.setdefault("WHYLOGS_NO_ANALYTICS", "True")
        result = subprocess.run(
            [sys.executable, self.run_dot_py_file, *args],
            cwd=str(self.path),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            error_msg = (
                f"Example {self.name} failed with exit code "
                f"{result.returncode}"
            )
            if result.stdout:
                error_msg += f"\n=== STDOUT ===\n{result.stdout}"
            if result.stderr:
                error_msg += f"\n=== STDERR ===\n{result.stderr}"
            logging.error(error_msg)
            raise subprocess.CalledProcessError(
                result.returncode,
                result.args,
                output=result.stdout,
                stderr=result.stderr,
            )


def copy_example_files(example_dir: str, dst_dir: str) -> None:
    """Copy example files into a temporary test repository."""
    for item in os.listdir(example_dir):
        if item == ".zen":
            # don't copy any existing ZenML repository
            continue

        s = os.path.join(example_dir, item)
        d = os.path.join(dst_dir, item)
        if os.path.isdir(s):
            shutil.copytree(s, d)
        else:
            shutil.copy2(s, d)


@contextmanager
def run_example(
    request: pytest.FixtureRequest,
    name: str,
    example_args: Optional[List[str]] = None,
    pipelines: Optional[Dict[str, Tuple[int, int]]] = None,
    timeout_limit: int = DEFAULT_PIPELINE_RUN_FINISH_TIMEOUT,
    is_public_example: bool = False,
) -> Generator[Dict[str, List[PipelineRunResponse]], None, None]:
    """Runs the given example and validates it ran correctly.

    Args:
        request: The pytest request object.
        name: The name (=directory name) of the example.
        example_args: Additional arguments to pass to the example
        pipelines: Validate that the pipelines were executed during the example
            run. Maps pipeline names to a Tuple (run_count, step_count) that
            specifies the expected number of runs (and their steps) to validate.
        timeout_limit: The maximum time to wait for the pipeline run to finish.
        is_public_example: Whether the example is a public example that lives
            in `examples/` (True) or a test-only example that lives in
            `tests/integration/examples/` (False).

    Yields:
        The example and the pipeline runs that were executed and validated.
    """
    # Copy all example files into the repository directory
    if is_public_example:  # examples/<name>
        examples_directory = str(Path(__file__).parents[3] / "examples" / name)
    else:  # tests/integration/examples/<name>
        examples_directory = str(Path(__file__).parents[0] / name)
    dst_dir = Path(os.getcwd())
    copy_example_files(examples_directory, str(dst_dir))

    # Get the existing pipelines and builds
    existing_pipeline_ids = {pipe.id for pipe in get_pipelines()}
    existing_build_ids = {build.id for build in get_builds()}
    now = datetime.utcnow()

    # Run the example
    example = IntegrationTestExample(name=name, path=dst_dir)
    example_args = example_args or []
    example(*example_args)

    # Validate the pipelines
    runs = wait_and_validate_pipeline_runs(
        pipelines=pipelines,
        older_than=now,
        timeout_limit=timeout_limit,
    )

    yield runs

    pipeline_names = list(pipelines.keys()) if pipelines else []
    cleanup_pipelines(existing_pipeline_ids, pipeline_names)

    if request.config.getoption("cleanup_docker", False):
        cleanup_docker_files(existing_build_ids)


def get_pipelines() -> List["PipelineResponse"]:
    """Get the existing pipelines."""
    from zenml.client import Client

    client = Client()
    return depaginate(list_method=client.list_pipelines)


def get_builds() -> List["PipelineBuildResponse"]:
    """Get the existing builds."""
    from zenml.client import Client

    client = Client()
    return depaginate(list_method=client.list_builds)


def wait_and_validate_pipeline_runs(
    pipelines: Optional[Dict[str, Tuple[int, int]]] = None,
    older_than: Optional[datetime] = None,
    timeout_limit: int = DEFAULT_PIPELINE_RUN_FINISH_TIMEOUT,
) -> Dict[str, List[PipelineRunResponse]]:
    """Wait for and validate pipeline runs."""
    pipelines = pipelines or {}
    runs: Dict[str, List[PipelineRunResponse]] = {}
    for pipeline_name, (run_count, step_count) in pipelines.items():
        runs[pipeline_name] = wait_and_validate_pipeline_run(
            pipeline_name=pipeline_name,
            run_count=run_count,
            step_count=step_count,
            older_than=older_than,
            finish_timeout=timeout_limit,
        )
    return runs


def wait_and_validate_pipeline_run(
    pipeline_name: str,
    run_count: Optional[int] = None,
    step_count: Optional[int] = None,
    older_than: Optional[datetime] = None,
    start_timeout: int = DEFAULT_PIPELINE_RUN_START_TIMEOUT,
    finish_timeout: int = DEFAULT_PIPELINE_RUN_FINISH_TIMEOUT,
    poll_period: int = 1,
) -> List[PipelineRunResponse]:
    """A basic example validation function.

    This function makes sure that a pipeline is registered and optionally waits
    until a number of pipeline runs have executed by checking the run status as
    well as making sure all steps were executed.

    Args:
        pipeline_name: The name of the pipeline to verify.
        run_count: The amount of pipeline runs to verify.
        step_count: The amount of steps inside the pipeline.
        older_than: Only look at runs older than this datetime. If not supplied
            all runs will be checked.
        start_timeout: The timeout in seconds to wait for a single pipeline run
            to be recorded. Set to 0 or a negative number to disable.
        finish_timeout: The timeout in seconds to wait for a single pipeline run
            to finish.
        poll_period: The period in seconds to wait between polling the pipeline
            run status. Keep this low: local examples often finish between
            polling intervals, so a long default adds pure idle time.

    Returns:
        A list of pipeline runs that were validated.

    Raises:
        AssertionError: If the validation failed.
    """
    # Not all orchestrators support synchronous execution, and some may not
    # even be configured to do that. In other cases, we may have to wait for
    # scheduled pipeline runs. So we need to poll for `run_count` pipeline
    # runs older than the supplied timestamp to be recorded and finish before
    # we can validate them.

    pipeline = Client().get_pipeline(pipeline_name)
    assert pipeline

    if not run_count:
        return []

    runs: List[PipelineRunResponse] = []

    # Wait for all pipeline runs to be recorded and complete. We assume the
    # runs will be executed in sequence, so we wait for an increasing number
    # of runs to be recorded and complete.
    for run_no in range(1, run_count + 1):
        logging.info(f"Waiting for {run_no} pipeline runs to complete...")

        # Wait for the current number of runs (run_no) to be recorded for
        # a maximum of `start_timeout` seconds
        wait_start = start_timeout
        while True:
            logging.debug(
                f"Waiting for {run_no} pipeline runs to be recorded..."
            )

            runs = pipeline.runs[:run_no]

            if older_than is not None:
                runs = [r for r in runs if r.created >= older_than]

            if len(runs) >= run_no:
                # We have at least `run_no` runs recorded
                break
            if wait_start <= 0:
                raise AssertionError(
                    f"Timed out waiting for {run_no} pipeline runs to be "
                    f"recorded"
                )
            wait_start -= poll_period
            time.sleep(poll_period)

        # After they are recorded, wait for the current number of runs (run_no)
        # to complete or fail for a maximum of `finish_timeout` seconds
        wait_finish = finish_timeout
        while True:
            logging.debug(f"Waiting for {run_no} pipeline runs to complete...")

            runs = pipeline.runs[:run_no]

            if older_than is not None:
                runs = [r for r in runs if r.created >= older_than]

            runs = [r for r in runs if r.status.is_finished]

            if len(runs) >= run_no:
                # We have at least `run_no` runs completed or failed
                break
            if wait_finish <= 0:
                raise AssertionError(
                    f"Timed out waiting for {run_no} pipeline runs to be "
                    f"completed or failed"
                )
            wait_finish -= poll_period
            time.sleep(poll_period)

    assert len(runs) >= run_count

    for run in runs[:run_count]:
        assert run.status == ExecutionStatus.COMPLETED
        if step_count:
            assert len(run.steps) == step_count

    return runs[:run_count]


def cleanup_pipelines(
    existing_pipeline_ids: Set["UUID"],
    pipeline_names: List[str],
) -> None:
    """Cleanup pipelines, so they don't cause trouble in future example runs."""
    client = Client()
    pipelines = get_pipelines()
    for pipeline in pipelines:
        if (
            pipeline.id not in existing_pipeline_ids
            and pipeline.name in pipeline_names
        ):
            client.delete_pipeline(pipeline.id)


def cleanup_docker_files(existing_build_ids: Set["UUID"]) -> None:
    """Clean up more expensive Docker resources if any were created.

    Cleans up containers, volumes and images.
    """
    builds = get_builds()

    image_names = set()
    for build in builds:
        if build.id in existing_build_ids:
            continue

        image_names.update(item.image for item in build.images.values())

    try:
        from docker.client import DockerClient
        from docker.errors import ImageNotFound

        # Try to ping Docker, to see if it's installed and running
        docker_client = DockerClient.from_env()
        docker_client.ping()
    except Exception:
        # Docker is not installed or running
        pass
    else:
        docker_client.containers.prune()
        docker_client.volumes.prune()
        for image_name in image_names:
            try:
                logging.debug(f"Removing Docker image {image_name}")
                image = docker_client.images.get(image_name)
                docker_client.images.remove(image.id, force=True)
            except ImageNotFound:
                pass

        docker_client.images.prune()

```

File: /Users/safoine/zenml-io/zenml/.github/workflows/develop-health-gate.yml
```yml
---
name: develop-health-gate
on:
  merge_group:
  workflow_dispatch:
permissions:
  contents: read
  checks: read
  issues: read
  pull-requests: read
jobs:
  develop-health-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
      - name: Evaluate develop health
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          MAX_AGE_HOURS: 30
          GRACE_AFTER_SCHEDULE_HOURS: 6
        run: python scripts/develop_health_gate.py

```

File: /Users/safoine/zenml-io/zenml/.github/workflows/release.yml
```yml
---
name: Release Package & Docker Image
on:
  push:
    tags: ['*']
permissions:
  contents: read
  checks: read
jobs:
  verify-known-good:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
        with:
          fetch-depth: 0
      - name: Verify slow CI qualification (warn-only)
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: python scripts/check_known_good.py --warn-only
  setup-and-test:
    needs: verify-known-good
    uses: ./.github/workflows/unit-test.yml
    with:
      os: ubuntu-latest
      python-version: '3.11'
    secrets: inherit
  # We only run the `latest` DB migration test here, as the other previous steps in the release flow already
  # test full migrations.
  mysql-db-migration-testing:
    needs: verify-known-good
    runs-on: ubuntu-latest
    env:
      ZENML_ANALYTICS_OPT_IN: false
      ZENML_DEBUG: true
    steps:
      - name: Checkout code
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
        with:
          fetch-depth: 0
      - name: Set up Python 3.10
        uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405  # v6.2.0
        with:
          python-version: '3.10'
      - name: Login to Docker Hub
        uses: docker/login-action@4907a6ddec9925e35a0a9e82d7399ccc52663121  # v4.1.0
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}
      - name: Test migrations across versions
        run: bash scripts/test-migrations.sh mysql latest
  sqlite-db-migration-testing:
    needs: verify-known-good
    runs-on: ubuntu-latest
    env:
      ZENML_ANALYTICS_OPT_IN: false
      ZENML_DEBUG: true
    steps:
      - name: Checkout code
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
        with:
          fetch-depth: 0
      - name: Set up Python 3.10
        uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405  # v6.2.0
        with:
          python-version: '3.10'
      - name: Test migrations across versions
        run: bash scripts/test-migrations.sh sqlite latest
  mariadb-db-migration-testing:
    needs: verify-known-good
    runs-on: ubuntu-latest
    env:
      ZENML_ANALYTICS_OPT_IN: false
      ZENML_DEBUG: true
    steps:
      - name: Checkout code
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
        with:
          fetch-depth: 0
      - name: Set up Python 3.10
        uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405  # v6.2.0
        with:
          python-version: '3.10'
      - name: Login to Docker Hub
        uses: docker/login-action@4907a6ddec9925e35a0a9e82d7399ccc52663121  # v4.1.0
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}
      - name: Test migrations across versions
        run: bash scripts/test-migrations.sh mariadb latest
  publish-python-package:
    # This previously used the publish_to_pypi.yml workflow, but PyPI
    # doesn't support trusted publishing with reusable workflows yet.
    # See https://github.com/pypi/warehouse/issues/11096
    if: github.repository == 'zenml-io/zenml'
    name: Publish Python 🐍 package 📦 to PyPI
    needs:
      - setup-and-test
      - sqlite-db-migration-testing
      - mysql-db-migration-testing
      - mariadb-db-migration-testing
    runs-on: ubuntu-latest
    environment: release
    permissions:
      # This permission is required for trusted publishing.
      id-token: write
      contents: read
    env:
      ZENML_DEBUG: 1
      ZENML_ANALYTICS_OPT_IN: false
      PYTHONIOENCODING: utf-8
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
      - name: Get the version from the github tag ref
        id: get_version
        run: echo "VERSION=${GITHUB_REF/refs\/tags\//}" >> "$GITHUB_OUTPUT"
      - name: Set up Python 3.11
        uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405  # v6.2.0
        with:
          python-version: '3.11'
      - name: Install uv
        uses: astral-sh/setup-uv@08807647e7069bb48b6ef5acd8ec9567f424441b  # v8.1.0
        with:
          version: 0.8.14
          enable-cache: false
      - name: Include latest dashboard
        run: bash scripts/install-dashboard.sh
      - name: Verify version
        run: |-
          if [ "$(cat src/zenml/VERSION)" != "$(echo ${GITHUB_REF} | sed 's|refs/tags/||g')" ]; then
            echo "Version mismatch between src/zenml/VERSION and git tag"
            exit 1
          fi
      - name: Build package
        run: uv build
      - name: Publish package distributions to PyPI
        uses: pypa/gh-action-pypi-publish@cef221092ed1bacb1cc03d23a2d87d1d172e277b  # release/v1
  wait-for-package-release:
    runs-on: ubuntu-latest
    needs: publish-python-package
    steps:
      - name: Sleep for 4 minutes
        run: sleep 240
        shell: bash
  publish-docker-image:
    if: github.repository == 'zenml-io/zenml'
    needs: wait-for-package-release
    uses: ./.github/workflows/publish_docker_image.yml
    secrets: inherit
  publish-helm-chart:
    if: github.repository == 'zenml-io/zenml'
    needs: publish-docker-image
    uses: ./.github/workflows/publish_helm_chart.yml
    secrets: inherit
  wait-for-package-release-again:
    runs-on: ubuntu-latest
    needs: publish-helm-chart
    steps:
      - name: Sleep for 4 minutes
        run: sleep 240
        shell: bash
  publish-stack-templates:
    if: github.repository == 'zenml-io/zenml'
    needs: publish-python-package
    uses: ./.github/workflows/publish_stack_templates.yml
    secrets: inherit
  # create a tag on the ZenML cloud plugins repo
  create_tag_on_cloud_plugins_repo:
    runs-on: ubuntu-latest
    needs: wait-for-package-release-again
    steps:
      - name: Get the sha of the latest commit on plugins/main
        id: get_sha
        run: |
          echo "sha=$(curl -s -H "Authorization: token ${{ secrets.CLOUD_PLUGINS_REPO_PAT }}" https://api.github.com/repos/zenml-io/zenml-cloud-plugins/commits/main | jq -r '.sha')" >> "$GITHUB_OUTPUT"
      - name: Get the version from the github tag ref
        id: get_version
        run: echo "VERSION=${GITHUB_REF/refs\/tags\//}" >> "$GITHUB_OUTPUT"
      - name: Create a tag on ZenML Cloud plugins repo
        uses: actions/github-script@ed597411d8f924073f98dfc5c65a23a2325f34cd  # v8.0.0
        env:
          RELEASE_VERSION: ${{ steps.get_version.outputs.VERSION }}
          CLOUD_PLUGINS_SHA: ${{ steps.get_sha.outputs.sha }}
        with:
          github-token: ${{ secrets.CLOUD_PLUGINS_REPO_PAT }}
          script: |-
            await github.rest.git.createRef({
              owner: 'zenml-io',
              repo: 'zenml-cloud-plugins',
              ref: `refs/tags/${process.env.RELEASE_VERSION}`,
              sha: process.env.CLOUD_PLUGINS_SHA
            })

```

File: /Users/safoine/zenml-io/zenml/scripts/ci/run_mixed_environment_pytest.py
```py
"""Run offload pytest batches with per-test environment routing."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


def _extract_args(argv: list[str]) -> tuple[list[str], list[str], Path]:
    common_args: list[str] = []
    test_ids: list[str] = []
    junit_path: Path | None = None
    index = 0

    while index < len(argv):
        arg = argv[index]
        if arg.startswith("--junitxml="):
            junit_path = Path(arg.split("=", 1)[1])
        elif arg == "--junitxml":
            index += 1
            junit_path = Path(argv[index])
        elif arg == "--environment":
            index += 1
        elif arg.startswith("--environment="):
            pass
        elif arg.startswith("tests/"):
            test_ids.append(arg)
        else:
            common_args.append(arg)
        index += 1

    if junit_path is None:
        raise ValueError("Expected --junitxml in pytest arguments.")
    return common_args, test_ids, junit_path


def _run_pytest(
    *,
    common_args: list[str],
    test_ids: list[str],
    environment: str,
    junit_path: Path,
) -> int:
    if not test_ids:
        return 0

    command = [
        sys.executable,
        "-m",
        "pytest",
        *common_args,
        "--environment",
        environment,
        f"--junitxml={junit_path}",
        *test_ids,
    ]
    return subprocess.run(command).returncode


def _merge_junit(output_path: Path, input_paths: list[Path]) -> None:
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    total_time = 0.0
    merged = ET.Element("testsuite", {"name": "offload-batch"})

    for path in input_paths:
        if not path.exists():
            continue
        root = ET.parse(path).getroot()
        suites = (
            list(root.iter("testsuite")) if root.tag != "testsuite" else [root]
        )
        for suite in suites:
            for key in totals:
                totals[key] += int(suite.attrib.get(key, "0") or 0)
            total_time += float(suite.attrib.get("time", "0") or 0)
            for testcase in suite.findall("testcase"):
                merged.append(testcase)

    for key, value in totals.items():
        merged.set(key, str(value))
    merged.set("time", f"{total_time:.3f}")
    ET.ElementTree(merged).write(
        output_path,
        encoding="utf-8",
        xml_declaration=True,
    )


def main(argv: list[str] | None = None) -> int:
    """Route unit tests to default and integration tests to remote MySQL."""
    raw_args = argv or sys.argv[1:]
    if "--collect-only" in raw_args:
        return subprocess.run(
            [sys.executable, "-m", "pytest", *raw_args]
        ).returncode

    common_args, test_ids, junit_path = _extract_args(raw_args)
    unit_tests = [
        test_id for test_id in test_ids if test_id.startswith("tests/unit/")
    ]
    integration_tests = [
        test_id
        for test_id in test_ids
        if test_id.startswith("tests/integration/")
    ]
    other_tests = [
        test_id
        for test_id in test_ids
        if not test_id.startswith(("tests/unit/", "tests/integration/"))
    ]

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        unit_junit = temp_path / "unit.xml"
        integration_junit = temp_path / "integration.xml"
        other_junit = temp_path / "other.xml"

        exit_codes = [
            _run_pytest(
                common_args=common_args,
                test_ids=unit_tests,
                environment="default",
                junit_path=unit_junit,
            ),
            _run_pytest(
                common_args=common_args,
                test_ids=integration_tests,
                environment="remote-mysql-modal",
                junit_path=integration_junit,
            ),
            _run_pytest(
                common_args=common_args,
                test_ids=other_tests,
                environment="default",
                junit_path=other_junit,
            ),
        ]
        _merge_junit(junit_path, [unit_junit, integration_junit, other_junit])

    return 1 if any(exit_codes) else 0


if __name__ == "__main__":
    sys.exit(main())

```

File: /Users/safoine/zenml-io/zenml/.github/CLAUDE.md
```md
# ZenML GitHub Actions Guidelines

This document provides guidance for AI assistants working with ZenML's GitHub Actions workflows.

## Workflow Organization

### Categories

| Category | Workflows | Purpose |
|----------|-----------|---------|
| **CI/Testing** | ci-fast.yml, ci-slow.yml | Primary PR testing (two-tier approach) |
| **Reusable Tests** | unit-test.yml, linting.yml, integration-test-*.yml | Called by CI and release workflows |
| **Release** | release.yml, publish_*.yml | PyPI, Docker, Helm publishing |
| **Security** | codeql.yml, trivy-*.yml | Vulnerability scanning |
| **Maintenance** | stale-prs.yml, pr_labeler.yml, require-release-label.yml | Repo automation |
| **Special** | templates-test.yml, update-templates-to-examples.yml | Template syncing |

### Entry Points vs Reusable Workflows

**Entry points** (triggered externally): ci-fast.yml, ci-slow.yml, release.yml, nightly_build.yml

**Reusable workflows** (called via `workflow_call`): unit-test.yml, linting.yml, integration-test-*.yml, publish_*.yml

All reusable workflows use `secrets: inherit` for centralized secret management.

## Two-Tier CI Architecture

### ci-fast.yml (Every PR)

Runs automatically on all PRs and pushes to main:
- Spellcheck
- SQLite migration testing
- Linting (ubuntu, Python 3.11) — includes Ruff, pydoclint, yamlfix, zizmor, and mypy
- Unit tests (ubuntu, Python 3.11)
- Integration tests (2 environments, 6 shards each)
- API docs buildability test
- Template example updates (PRs only, same-repo only)

### ci-slow.yml (Full Matrix, Requires Label)

Gated by `run-slow-ci` label (checked dynamically):
- Multi-OS: Ubuntu, Windows, macOS
- Multi-Python: 3.10, 3.11, 3.12, 3.13
- Full database migration tests (MySQL, MariaDB, SQLite)
- VSCode tutorial pipeline tests
- Base package functionality tests

**Label mechanism**: Maintainers add `run-slow-ci` label and rerun workflow to trigger full CI without code changes.

## Release Process

Triggered by tag push. Sequence:

1. Unit tests (ubuntu, Python 3.11)
2. Database migration tests (MySQL, SQLite, MariaDB) - parallel
3. Publish to PyPI (trusted publishing with OIDC)
4. Wait 4 minutes (PyPI CDN propagation)
5. Publish Docker image (Google Cloud Build)
6. Publish Helm chart (AWS ECR Public)
7. Wait 4 minutes
8. Publish stack templates
9. Tag zenml-cloud-plugins repo

## Security Hardening with zizmor

[zizmor](https://woodruffw.github.io/zizmor/) is a GitHub Actions security linter. Configuration is in `.github/zizmor.yml`.

### Running zizmor locally

```bash
# Install (requires Python environment with dev deps)
uv pip install zizmor

# Run analysis
zizmor .github/workflows/

# Auto-fix SHA pinning (IMPORTANT: requires GH_TOKEN)
GH_TOKEN=$(gh auth token) zizmor --fix=all .github/workflows/
```

**Critical**: zizmor requires `GH_TOKEN` (not `GITHUB_TOKEN`) environment variable for SHA lookups when auto-fixing.

### Current Security Posture

**Enforced:**
- All actions SHA-pinned (prevents supply chain attacks)
- Malformed conditional detection
- Template injection detection (with documented exceptions)

**Disabled with TODOs:**
- `excessive-permissions`: Many workflows use default permissions. Audit incrementally.
- `artipacked`: Many workflows need `persist-credentials: true` for pushing commits.

### Documented Exceptions in zizmor.yml

- **Unpinned uses**: ZenML template repos intentionally stay on `@main` branch
- **Template injection**: Step outputs within same workflow are trusted
- **Cache poisoning**: Protected release branch workflows (docs only)
- **Secrets inherit**: First-party workflows calling other first-party workflows

## Common Patterns

### Environment Variables

Standard settings used across workflows:

```yaml
env:
  ZENML_DEBUG: true
  ZENML_ANALYTICS_OPT_IN: false
  PYTHONIOENCODING: utf-8
  UV_HTTP_TIMEOUT: 600
```

For testing stability:
```yaml
env:
  ZENML_LOGGING_VERBOSITY: INFO
  AUTO_OPEN_DASHBOARD: false
  ZENML_ENABLE_RICH_TRACEBACK: false
  TOKENIZERS_PARALLELISM: false
```

### Concurrency

All CI workflows use:
```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

This cancels previous runs when new commits are pushed to the same branch.

### Path Filtering

ci-fast and ci-slow ignore:
- `docs/**` - Documentation changes
- `*.md` - Markdown files
- `.claude/**` - Claude configuration
- `.github/workflows/claude.yml` - Claude workflow

But explicitly include `pyproject.toml` changes.

### Caching

uv cache key pattern:
```yaml
key: uv-${{ runner.os }}-${{ inputs.python-version }}-${{ hashFiles('src/zenml/integrations/*/__init__.py') }}
```

Cache invalidates when integrations change.

Offload CI uses separate cache families:
- `offload-uv-v1`: runner-side uv downloads/build artifacts for offload driver setup and pytest collection dependencies.
- `offload-image-v2`: Modal image metadata. This intentionally excludes runtime fields such as CPU, memory, `max_parallel`, commands used after sandbox creation, and test filters.
- `offload-junit-v2`: offload JUnit duration seeds keyed by lane and test-selection inputs.

Restored offload JUnit XML is only a duration seed. It must not be treated as current test output unless `.ci/offload/junit.xml` is newer than `.ci/offload/run-start.marker`. Stale restored XML should be quarantined as `junit.stale.xml`.

The `offload-cache-warm.yml` workflow refreshes offload image and JUnit duration caches weekly or manually. It is a maintenance workflow, not a branch-protection signal.

## Key Supporting Files

| File | Purpose |
|------|---------|
| `actions/setup_environment/action.yml` | Composite action for Python + ZenML dev setup |
| `zizmor.yml` | Security linter configuration |
| `codecov.yml` | Coverage reporting (lenient thresholds) |
| `dependabot.yml` | Weekly GitHub Actions updates (Tuesdays 07:00 CET) |
| `teams.yml` | Internal team members for privileged workflows |
| `branch-labels.yml` | Auto-labeling rules based on branch patterns |

## Template Workflows

### update-templates-to-examples.yml

Syncs external template repos to `examples/` folder:
- `zenml-io/template-e2e-batch` → `examples/e2e`
- `zenml-io/template-nlp` → `examples/e2e_nlp`
- `zenml-io/zenml-project-templates` → `examples/mlops_starter`
- `zenml-io/template-llm-finetuning` → `examples/llm_finetuning`

**Important**: These template repos use `@main` branch intentionally and are excluded from SHA pinning.

### templates-test.yml

Tests template compatibility by running test actions from template repos. Failure indicates breaking changes that need template updates.

## Special Workflows

### claude.yml

AI code review integration. Triggered by `@claude` mentions in issues/PRs. Gated to internal team members via `teams.yml`.

### snack-it.yml

Creates tracking issues from PRs when `snack-it` label is applied. Adds to GitHub Projects roadmap.

## Important Gotchas

1. **GH_TOKEN for zizmor**: Use `GH_TOKEN=$(gh auth token)` not `GITHUB_TOKEN` for SHA lookups

2. **Template repos stay unpinned**: The 4 template repositories in `update-templates-to-examples.yml` intentionally use `@main` - don't SHA-pin them

3. **zizmor strips subdirectory paths**: Actions with subdirectory paths like `github/codeql-action/init@SHA` or `zenml-io/template-e2e-batch/.github/actions/e2e_template_test@main` get incorrectly "fixed" by zizmor to just `github/codeql-action@SHA` (stripping `/init`). This breaks workflows. After running `zizmor --fix`, manually verify and restore any stripped subdirectory paths. Common affected actions:
   - `github/codeql-action/init` (Initialize CodeQL)
   - `github/codeql-action/analyze` (Perform CodeQL Analysis)
   - `github/codeql-action/upload-sarif` (Upload SARIF results)

4. **secrets: inherit is intentional**: Zizmor warns about this but it's the correct pattern for first-party reusable workflows

5. **Run format.sh before commits**: YAML files must pass yamlfix (`bash scripts/format.sh .github/`)

6. **Two-tier CI requires label**: Full CI only runs with `run-slow-ci` label - maintainers add this for thorough testing

7. **Release waits are intentional**: The 4-minute sleeps in release.yml allow PyPI CDN propagation

8. **Don't modify examples/ directly**: This folder is auto-updated by CI from template repos

## Formatting Workflows

Always run before committing workflow changes:

```bash
bash scripts/format.sh .github/
```

This runs yamlfix on YAML files to ensure consistent formatting.

## Adding New Workflows

1. Use SHA-pinned actions: `actions/checkout@<full-sha>  # v4.2.2`
2. Add appropriate concurrency settings
3. Include standard environment variables
4. Consider if it should be reusable (`workflow_call`)
5. Run zizmor to check for security issues
6. Update this document if adding new patterns

```

File: /Users/safoine/zenml-io/zenml/tests/integration/conftest.py
```py
#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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

"""Integration-test CI policy hooks."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Generator

import pytest

from zenml.client import Client
from zenml.constants import ENV_ZENML_ACTIVE_PROJECT_ID
from zenml.utils.string_utils import random_str


def _is_medium_tier() -> bool:
    """Return whether tests are running in the medium CI tier."""
    return os.environ.get("ZENML_CI_TIER") == "medium"


def _load_quarantined_tests() -> dict[str, str]:
    """Load tests quarantined for the current CI tier."""
    registry_path = Path(__file__).parents[2] / ".github/quarantined-tests.yml"
    if not registry_path.exists():
        return {}

    import yaml

    data: dict[str, Any] = (
        yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    )
    quarantined: dict[str, str] = {}
    for entry in data.get("quarantined", []):
        if "medium" not in entry.get("skip_in", []):
            continue
        quarantined[str(entry["test_id"])] = str(
            entry.get("reason", "quarantined")
        )
    return quarantined


def pytest_configure(config: pytest.Config) -> None:
    """Register CI markers."""
    config.addinivalue_line(
        "markers",
        "global_state: integration test intentionally mutates server-global state",
    )


@pytest.fixture
def zenml_workspace(
    monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> Generator[str, None, None]:
    """Create an isolated ZenML project for a workspace-safe test."""
    client = Client()
    original_project_id = client.active_project.id
    project_name = f"pytest_{random_str(8).lower()}"
    project = client.create_project(
        name=project_name,
        description=f"Isolated project for {request.node.nodeid}",
    )

    client.set_active_project(project.id)
    monkeypatch.setenv(ENV_ZENML_ACTIVE_PROJECT_ID, str(project.id))

    try:
        yield project_name
    finally:
        monkeypatch.setenv(
            ENV_ZENML_ACTIVE_PROJECT_ID, str(original_project_id)
        )
        client.set_active_project(original_project_id)
        client.delete_project(project_name)


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Skip medium-tier tests with active quarantines."""
    if not _is_medium_tier():
        return

    quarantined = _load_quarantined_tests()
    for item in items:
        if item.get_closest_marker("global_state"):
            item.add_marker(
                pytest.mark.skip(
                    reason="global-state test runs outside medium tier"
                )
            )
            continue

        reason = quarantined.get(item.nodeid)
        if reason:
            item.add_marker(pytest.mark.skip(reason=f"quarantined: {reason}"))

```

File: /Users/safoine/zenml-io/zenml/.github/workflows/integration-test-slow.yml
```yml
---
name: Integration Tests (Slow CI)
on:
  workflow_call:
    inputs:
      os:
        description: OS
        type: string
        required: true
      python-version:
        description: Python version
        type: string
        required: true
      test_environment:
        description: The test environment
        type: string
        required: true
      enable_tmate:
        description: Enable tmate session for debugging
        type: string
        required: false
        default: never
      tmate_timeout:
        description: Timeout for tmate session (minutes)
        type: number
        required: false
        default: 30
      reruns:
        description: Pytest rerun count (0 disables)
        type: number
        required: false
        default: 3
      git-ref:
        description: Git branch or ref
        type: string
        required: false
        default: ''
  workflow_dispatch:
    inputs:
      os:
        description: OS
        type: choice
        options: [ubuntu-latest, macos-13, windows-latest]
        required: false
        default: ubuntu-latest
      python-version:
        description: Python version
        type: choice
        options: ['3.10', '3.11', '3.12', '3.13']
        required: false
        default: '3.11'
      test_environment:
        description: The test environment
        type: choice
        options:
          # Default ZenML deployments
          - default
          - default-docker-orchestrator
          - default-airflow-orchestrator
          # Local ZenML server deployments
          - local-server
          - local-server-docker-orchestrator
          - local-server-airflow-orchestrator
          # Local ZenML docker-compose server deployments
          - docker-server-mysql
          - docker-server-mariadb
          - docker-server-docker-orchestrator-mysql
          - docker-server-docker-orchestrator-mariadb
          - docker-server-airflow-orchestrator-mysql
          - docker-server-airflow-orchestrator-mariadb
        required: false
        default: default
      enable_tmate:
        description: Enable tmate session for debugging
        type: choice
        options: [no, on-failure, always, before-tests]
        required: false
        default: 'no'
      tmate_timeout:
        description: Timeout for tmate session (minutes)
        type: number
        required: false
        default: 30
      reruns:
        description: Pytest rerun count (0 disables)
        type: number
        required: false
        default: 3
jobs:
  integration-tests-slow:
    name: integration-tests-slow
    runs-on: ${{ inputs.os }}
    strategy:
      fail-fast: false
    env:
      ZENML_DEBUG: 1
      ZENML_ANALYTICS_OPT_IN: false
      ZENML_ENABLE_RICH_TRACEBACK: false
      WHYLOGS_NO_ANALYTICS: 'True'
      PYTHONIOENCODING: utf-8
      UV_HTTP_TIMEOUT: 600
      # on MAC OS, we need to set this environment variable
      # to fix problems with the fork() calls (see this thread
      # for more information: http://sealiesoftware.com/blog/archive/2017/6/5/Objective-C_and_fork_in_macOS_1013.html)
      OBJC_DISABLE_INITIALIZE_FORK_SAFETY: 'YES'
      AWS_ACCESS_KEY_ID: ${{ secrets.AWS_US_EAST_1_ENV_ACCESS_KEY_ID }}
      AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_US_EAST_1_ENV_SECRET_ACCESS_KEY }}
      AWS_US_EAST_1_SERVER_URL: ${{ secrets.AWS_US_EAST_1_SERVER_URL }}
      AWS_US_EAST_1_SERVER_USERNAME: ${{ secrets.AWS_US_EAST_1_SERVER_USERNAME }}
      AWS_US_EAST_1_SERVER_PASSWORD: ${{ secrets.AWS_US_EAST_1_SERVER_PASSWORD }}
      GCP_US_EAST4_SERVER_URL: ${{ secrets.GCP_US_EAST4_SERVER_URL }}
      GCP_US_EAST4_SERVER_USERNAME: ${{ secrets.GCP_US_EAST4_SERVER_USERNAME }}
      GCP_US_EAST4_SERVER_PASSWORD: ${{ secrets.GCP_US_EAST4_SERVER_PASSWORD }}
      PYTEST_RERUNS: ${{ inputs.reruns }}
    # TODO: add Windows testing for Python 3.11 3.12 and 3.13 back in
    if: ${{ ! startsWith(github.event.head_commit.message, 'GitBook:') && ! (inputs.os == 'windows-latest' && inputs.python-version == '3.11') && ! (inputs.os == 'windows-latest' && inputs.python-version == '3.12') && ! (inputs.os == 'windows-latest' && inputs.python-version == '3.13') }}
    defaults:
      run:
        shell: bash
    steps:
      - name: Free disk space (Ubuntu)
        if: inputs.os == 'ubuntu-latest'
        run: |
          set -euxo pipefail
          echo "Before cleanup:"
          df -h
          sudo rm -rf /usr/share/dotnet || true
          sudo rm -rf /usr/local/lib/android || true
          sudo rm -rf /opt/ghc || true
          sudo rm -rf /opt/hostedtoolcache/CodeQL || true
          sudo docker image prune --all --force || true
          echo "After cleanup:"
          df -h
      - name: Set uv cache + temp dirs (/opt)
        if: inputs.os == 'ubuntu-latest'
        run: |
          sudo mkdir -p /opt/uv-cache /opt/tmp
          sudo chown -R "$(id -u)":"$(id -g)" /opt/uv-cache /opt/tmp
          echo "UV_CACHE_DIR=/opt/uv-cache" >> "$GITHUB_ENV"
          echo "TMPDIR=/opt/tmp" >> "$GITHUB_ENV"
          echo "TMP=/opt/tmp" >> "$GITHUB_ENV"
          echo "TEMP=/opt/tmp" >> "$GITHUB_ENV"
      - name: Move Docker data-root to /opt
        if: inputs.os == 'ubuntu-latest' && (contains(inputs.test_environment, 'docker')
          || contains(inputs.test_environment, 'kubeflow') || contains(inputs.test_environment,
          'airflow') || contains(inputs.test_environment, 'kubernetes'))
        run: |
          sudo mkdir -p /etc/docker
          sudo mkdir -p /opt/docker

          # Ensure Docker stores images/layers on the expanded /opt volume.
          if [ -f /etc/docker/daemon.json ]; then
            sudo python - <<'PY'
          import json
          from pathlib import Path
          path = Path("/etc/docker/daemon.json")
          data = json.loads(path.read_text())
          data["data-root"] = "/opt/docker"
          path.write_text(json.dumps(data))
          PY
          else
            echo '{"data-root":"/opt/docker"}' | sudo tee /etc/docker/daemon.json >/dev/null
          fi
      - name: Restart Docker (with /opt data-root)
        if: inputs.os == 'ubuntu-latest' && (contains(inputs.test_environment, 'docker')
          || contains(inputs.test_environment, 'kubeflow') || contains(inputs.test_environment,
          'airflow') || contains(inputs.test_environment, 'kubernetes'))
        run: |
          sudo systemctl stop docker || true
          # Free up space previously used by Docker's default root on the OS disk.
          sudo rm -rf /var/lib/docker/* || true
          sudo systemctl start docker
      - name: Login to Docker Hub
        uses: docker/login-action@4907a6ddec9925e35a0a9e82d7399ccc52663121  # v4.1.0
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}
        if: github.event.pull_request.head.repo.fork == false && (contains(inputs.test_environment,
          'docker') || contains(inputs.test_environment, 'kubeflow') || contains(inputs.test_environment,
          'airflow') || contains(inputs.test_environment, 'kubernetes'))
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
        with:
          ref: ${{ inputs.git-ref || github.event.pull_request.head.sha || github.sha }}
      - name: Restore uv cache
        uses: actions/cache@27d5ce7f107fe9357f9df03efb73ab90386fccae  # v5.0.5
        with:
          path: ${{ inputs.os == 'ubuntu-latest' && '/opt/uv-cache' || '~/.cache/uv' }}
          key: |
            uv-${{ runner.os }}-${{ inputs.python-version }}-${{ hashFiles('src/zenml/integrations/*/__init__.py') }}
          restore-keys: |
            uv-${{ runner.os }}-${{ inputs.python-version }}-${{ hashFiles('src/zenml/integrations/*/__init__.py') }}
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@ec61189d14ec14c8efccab744f656cffd0e33f37  # v6.1.0
        with:
          role-to-assume: ${{ secrets.AWS_US_EAST_1_ENV_ROLE_ARN }}
          aws-region: us-east-1
        if: contains(inputs.test_environment, 'aws')
      - name: Configure GCP credentials
        uses: google-github-actions/auth@7c6bc770dae815cd3e89ee6cdf493a5fab2cc093  # v3.0.0
        with:
          credentials_json: ${{ secrets.GCP_US_EAST4_ENV_CREDENTIALS }}
        if: contains(inputs.test_environment, 'gcp')
      - name: Set up gcloud SDK
        uses: google-github-actions/setup-gcloud@aa5489c8933f4cc7a4f7d45035b3b1440c9c10db  # v3.0.1
        with:
          install_components: gke-gcloud-auth-plugin
        if: contains(inputs.test_environment, 'gcp')
      - name: Setup environment
        uses: ./.github/actions/setup_environment
        with:
          python-version: ${{ inputs.python-version }}
          os: ${{ inputs.os }}
      - name: Install docker-compose for non-default environments
        if: inputs.test_environment != 'default'
        run: |
          pip install uv
          # see https://github.com/docker/docker-py/issues/3256 for why we need to pin requests
          # docker-compose is deprecated and doesn't work with newer versions of docker
          uv pip install --system "pyyaml==5.3.1" "requests<2.32.0" "docker==6.1.3" docker-compose
      - name: Install MacOS System Dependencies
        if: runner.os=='macOS'
        run: brew install libomp
      - name: Install kubectl on Linux
        run: |
          curl -LO "https://dl.k8s.io/release/v1.35.0/bin/linux/amd64/kubectl"
          sudo install -o root -g 0 -m 0755 kubectl /usr/local/bin/kubectl
        if: (inputs.os == 'ubuntu-latest' || inputs.os == 'arc-runner-set')
      - name: Install kubectl on MacOS
        run: |
          curl -LO "https://dl.k8s.io/release/v1.35.0/bin/darwin/amd64/kubectl"
          sudo install -o root -g 0 -m 0755 kubectl /usr/local/bin/kubectl
        if: runner.os=='macOS'
      - name: Install K3D
        run: |
          curl -s https://raw.githubusercontent.com/rancher/k3d/main/install.sh | bash
        if: runner.os!='Windows' && contains(inputs.test_environment, 'kubeflow')
      - name: Login to Amazon ECR
        id: login-ecr
        run: |
          aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 715803424590.dkr.ecr.us-east-1.amazonaws.com
        if: contains(inputs.test_environment, 'aws')
      - name: Login to Amazon EKS
        id: login-eks
        run: |
          aws eks --region us-east-1 update-kubeconfig --name zenml-ci-cluster --alias zenml-ci-aws-us-east-1
        if: contains(inputs.test_environment, 'aws')
      - name: Login to Google ECR
        run: |
          gcloud auth configure-docker --project zenml-ci
        if: contains(inputs.test_environment, 'gcp')
      - name: Login to Google GKE
        uses: google-github-actions/get-gke-credentials@3da1e46a907576cefaa90c484278bb5b259dd395  # v3.0.0
        with:
          cluster_name: zenml-ci-cluster
          location: us-east4
          project_id: zenml-ci
        if: contains(inputs.test_environment, 'gcp')
      - name: Setup tmate session before tests
        if: ${{ inputs.enable_tmate == 'before-tests' }}
        uses: mxschmitt/action-tmate@c0afd6f790e3a5564914980036ebf83216678101  # v3.23
        timeout-minutes: ${{ inputs.tmate_timeout }}
      - name: Integration Tests - Slow CI
        run: |
          bash scripts/test-coverage-xml.sh integration ${INPUTS_TEST_ENVIRONMENT}
        env:
          INPUTS_TEST_ENVIRONMENT: ${{ inputs.test_environment }}
      - name: Setup tmate session after tests
        if: ${{ inputs.enable_tmate == 'always' || (inputs.enable_tmate == 'on-failure' && failure()) }}
        uses: mxschmitt/action-tmate@c0afd6f790e3a5564914980036ebf83216678101  # v3.23
        timeout-minutes: ${{ inputs.tmate_timeout }}
      - name: Verify Python Env unaffected
        run: |-
          zenml integration list
          uv pip list
          uv pip check || true

```

File: /Users/safoine/zenml-io/zenml/.github/quarantined-tests.yml
```yml
---
schema_version: 1
quarantined: []

```

File: /Users/safoine/zenml-io/zenml/.github/workflows/integration-test-fast.yml
```yml
---
name: Integration Tests (Fast CI)
on:
  workflow_call:
    inputs:
      os:
        description: OS
        type: string
        required: true
      python-version:
        description: Python version
        type: string
        required: true
      test_environment:
        description: The test environment
        type: string
        required: true
      enable_tmate:
        description: Enable tmate session for debugging
        type: string
        required: false
        default: never
      tmate_timeout:
        description: Timeout for tmate session (minutes)
        type: number
        required: false
        default: 30
      reruns:
        description: Pytest rerun count (0 disables)
        type: number
        required: false
        default: 3
      ci_tier:
        description: CI tier name
        type: string
        required: false
        default: fast
      modal_ci_server_url:
        description: Per-run Modal ZenML server URL
        type: string
        required: false
        default: ''
      modal_ci_server_username:
        description: Per-run Modal ZenML server username
        type: string
        required: false
        default: ''
  workflow_dispatch:
    inputs:
      os:
        description: OS
        type: choice
        options: [ubuntu-latest, macos-13, windows-latest]
        required: false
        default: ubuntu-latest
      python-version:
        description: Python version
        type: choice
        options: ['3.10', '3.11', '3.12', '3.13']
        required: false
        default: '3.11'
      test_environment:
        description: The test environment
        type: choice
        options:
          # Default ZenML deployments
          - default
          - default-docker-orchestrator
          - default-airflow-orchestrator
          # Local ZenML server deployments
          - local-server
          - local-server-docker-orchestrator
          - local-server-airflow-orchestrator
          # Local ZenML docker-compose server deployments
          - docker-server-mysql
          - docker-server-mariadb
          - docker-server-docker-orchestrator-mysql
          - docker-server-docker-orchestrator-mariadb
          - docker-server-airflow-orchestrator-mysql
          - docker-server-airflow-orchestrator-mariadb
          - github-actions-server-docker-orchestrator
          - remote-mysql-modal
        required: false
        default: default
      enable_tmate:
        description: Enable tmate session for debugging
        type: choice
        options: [no, on-failure, always, before-tests]
        required: false
        default: 'no'
      tmate_timeout:
        description: Timeout for tmate session (minutes)
        type: number
        required: false
        default: 30
      reruns:
        description: Pytest rerun count (0 disables)
        type: number
        required: false
        default: 3
jobs:
  integration-tests-fast:
    name: integration-tests-fast
    runs-on: ${{ inputs.os }}
    strategy:
      fail-fast: false
      matrix:
        shard: [1, 2, 3, 4, 5, 6]
    env:
      ZENML_DEBUG: 1
      ZENML_ANALYTICS_OPT_IN: false
      ZENML_ENABLE_RICH_TRACEBACK: false
      WHYLOGS_NO_ANALYTICS: 'True'
      PYTHONIOENCODING: utf-8
      UV_HTTP_TIMEOUT: 600
      # on MAC OS, we need to set this environment variable
      # to fix problems with the fork() calls (see this thread
      # for more information: http://sealiesoftware.com/blog/archive/2017/6/5/Objective-C_and_fork_in_macOS_1013.html)
      OBJC_DISABLE_INITIALIZE_FORK_SAFETY: 'YES'
      AWS_ACCESS_KEY_ID: ${{ secrets.AWS_US_EAST_1_ENV_ACCESS_KEY_ID }}
      AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_US_EAST_1_ENV_SECRET_ACCESS_KEY }}
      AWS_US_EAST_1_SERVER_URL: ${{ secrets.AWS_US_EAST_1_SERVER_URL }}
      AWS_US_EAST_1_SERVER_USERNAME: ${{ secrets.AWS_US_EAST_1_SERVER_USERNAME }}
      AWS_US_EAST_1_SERVER_PASSWORD: ${{ secrets.AWS_US_EAST_1_SERVER_PASSWORD }}
      GCP_US_EAST4_SERVER_URL: ${{ secrets.GCP_US_EAST4_SERVER_URL }}
      GCP_US_EAST4_SERVER_USERNAME: ${{ secrets.GCP_US_EAST4_SERVER_USERNAME }}
      GCP_US_EAST4_SERVER_PASSWORD: ${{ secrets.GCP_US_EAST4_SERVER_PASSWORD }}
      MODAL_CI_SERVER_URL: ${{ inputs.modal_ci_server_url }}
      MODAL_CI_SERVER_USERNAME: ${{ inputs.modal_ci_server_username }}
      PYTEST_RERUNS: ${{ inputs.reruns }}
      ZENML_CI_TIER: ${{ inputs.ci_tier }}
    if: ${{ ! startsWith(github.event.head_commit.message, 'GitBook:') && (inputs.test_environment != 'remote-mysql-modal' || github.event_name != 'pull_request' || github.event.pull_request.head.repo.full_name == github.repository) }}
    defaults:
      run:
        shell: bash
    steps:
      - name: Free disk space (Ubuntu)
        if: inputs.os == 'ubuntu-latest'
        run: |
          set -euxo pipefail
          echo "Before cleanup:"
          df -h
          sudo rm -rf /usr/share/dotnet || true
          sudo rm -rf /usr/local/lib/android || true
          sudo rm -rf /opt/ghc || true
          sudo rm -rf /opt/hostedtoolcache/CodeQL || true
          sudo docker image prune --all --force || true
          echo "After cleanup:"
          df -h
      - name: Set uv cache + temp dirs (/opt)
        if: inputs.os == 'ubuntu-latest'
        run: |
          sudo mkdir -p /opt/uv-cache /opt/tmp
          sudo chown -R "$(id -u)":"$(id -g)" /opt/uv-cache /opt/tmp
          echo "UV_CACHE_DIR=/opt/uv-cache" >> "$GITHUB_ENV"
          echo "TMPDIR=/opt/tmp" >> "$GITHUB_ENV"
          echo "TMP=/opt/tmp" >> "$GITHUB_ENV"
          echo "TEMP=/opt/tmp" >> "$GITHUB_ENV"
      - name: Move Docker data-root to /opt
        if: inputs.os == 'ubuntu-latest' && (contains(inputs.test_environment, 'docker')
          || contains(inputs.test_environment, 'kubeflow') || contains(inputs.test_environment,
          'airflow') || contains(inputs.test_environment, 'kubernetes'))
        run: |
          sudo mkdir -p /etc/docker
          sudo mkdir -p /opt/docker

          # Ensure Docker stores images/layers on the expanded /opt volume.
          if [ -f /etc/docker/daemon.json ]; then
            sudo python - <<'PY'
          import json
          from pathlib import Path
          path = Path("/etc/docker/daemon.json")
          data = json.loads(path.read_text())
          data["data-root"] = "/opt/docker"
          path.write_text(json.dumps(data))
          PY
          else
            echo '{"data-root":"/opt/docker"}' | sudo tee /etc/docker/daemon.json >/dev/null
          fi
      - name: Restart Docker (with /opt data-root)
        if: inputs.os == 'ubuntu-latest' && (contains(inputs.test_environment, 'docker')
          || contains(inputs.test_environment, 'kubeflow') || contains(inputs.test_environment,
          'airflow') || contains(inputs.test_environment, 'kubernetes'))
        run: |
          sudo systemctl stop docker || true
          # Free up space previously used by Docker's default root on the OS disk.
          sudo rm -rf /var/lib/docker/* || true
          sudo systemctl start docker
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
      - name: Restore uv cache
        uses: actions/cache@27d5ce7f107fe9357f9df03efb73ab90386fccae  # v5.0.5
        with:
          path: ${{ inputs.os == 'ubuntu-latest' && '/opt/uv-cache' || '~/.cache/uv' }}
          key: |
            uv-${{ runner.os }}-${{ inputs.python-version }}-${{ hashFiles('src/zenml/integrations/*/__init__.py') }}
          restore-keys: |
            uv-${{ runner.os }}-${{ inputs.python-version }}-${{ hashFiles('src/zenml/integrations/*/__init__.py') }}
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@ec61189d14ec14c8efccab744f656cffd0e33f37  # v6.1.0
        with:
          role-to-assume: ${{ secrets.AWS_US_EAST_1_ENV_ROLE_ARN }}
          aws-region: us-east-1
        if: contains(inputs.test_environment, 'aws')
      - name: Configure GCP credentials
        uses: google-github-actions/auth@7c6bc770dae815cd3e89ee6cdf493a5fab2cc093  # v3.0.0
        with:
          credentials_json: ${{ secrets.GCP_US_EAST4_ENV_CREDENTIALS }}
        if: contains(inputs.test_environment, 'gcp')
      - name: Set up gcloud SDK
        uses: google-github-actions/setup-gcloud@aa5489c8933f4cc7a4f7d45035b3b1440c9c10db  # v3.0.1
        with:
          install_components: gke-gcloud-auth-plugin
        if: contains(inputs.test_environment, 'gcp')
      - name: Login to Docker Hub
        uses: docker/login-action@4907a6ddec9925e35a0a9e82d7399ccc52663121  # v4.1.0
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}
        if: github.event.pull_request.head.repo.fork == false && (contains(inputs.test_environment,
          'docker') || contains(inputs.test_environment, 'kubeflow') || contains(inputs.test_environment,
          'airflow') || contains(inputs.test_environment, 'kubernetes'))
      - name: Setup environment
        uses: ./.github/actions/setup_environment
        with:
          python-version: ${{ inputs.python-version }}
          os: ${{ inputs.os }}
      - name: Validate Modal connection details
        if: inputs.test_environment == 'remote-mysql-modal' && vars.ZENML_CI_MODAL_DISABLED
          != 'true'
        run: |
          test -n "$MODAL_CI_SERVER_URL"
          test -n "$MODAL_CI_SERVER_USERNAME"
      - name: Install docker-compose for local Docker environments
        if: inputs.test_environment != 'default' && inputs.test_environment != 'remote-mysql-modal'
        run: |
          pip install uv
          # see https://github.com/docker/docker-py/issues/3256 for why we need to pin requests
          # docker-compose is deprecated and doesn't work with newer versions of docker
          uv pip install --system "pyyaml==5.3.1" "requests<2.32.0" "docker==6.1.3" docker-compose
      - name: Install Linux System Dependencies
        if: (inputs.os == 'ubuntu-latest' || inputs.os == 'arc-runner-set')
        run: sudo apt install graphviz
      - name: Install MacOS System Dependencies
        if: runner.os=='macOS'
        run: brew install graphviz
      - name: Install Windows System Dependencies
        if: runner.os=='Windows'
        run: choco install graphviz
      - name: Unbreak python in github actions
        if: runner.os=='macOS'
        # github actions overwrites brew's python. Force it to reassert itself, by
        # running in a separate step.
        # Workaround GitHub Actions Python issues
        # see https://github.com/Homebrew/homebrew-core/issues/165793#issuecomment-1989441193
        run: |
          find /usr/local/bin -lname '*/Library/Frameworks/Python.framework/*' -delete
          sudo rm -rf /Library/Frameworks/Python.framework/
          brew install --force python3 && brew unlink python3 && brew unlink python3 && brew link --overwrite python3
      - name: Install Docker and Colima on MacOS
        if: runner.os=='macOS'
        run: |
          export HOMEBREW_NO_INSTALLED_DEPENDENTS_CHECK=1
          brew update
          brew install docker colima
          brew reinstall --force qemu

          # We need to mount the /private/tmp/zenml-test/ folder because
          # this folder is also mounted in the Docker containers that are
          # started by local ZenML orchestrators.
          colima start --mount /private/tmp/zenml-test/:w

          # This is required for the Docker Python SDK to work
          sudo ln -sf $HOME/.colima/default/docker.sock /var/run/docker.sock
      - name: Install kubectl on Linux
        run: |
          curl -L -o kubectl "https://dl.k8s.io/release/v1.35.0/bin/linux/amd64/kubectl"
          sudo install -o root -g 0 -m 0755 kubectl /usr/local/bin/kubectl
        if: (inputs.os == 'ubuntu-latest' || inputs.os == 'arc-runner-set') && (contains(inputs.test_environment,
          'kubeflow') || contains(inputs.test_environment, 'kubernetes') || contains(inputs.test_environment,
          'aws') || contains(inputs.test_environment, 'gcp'))
      - name: Install kubectl on MacOS
        run: |
          curl -LO "https://dl.k8s.io/release/v1.35.0/bin/darwin/amd64/kubectl"
          sudo install -o root -g 0 -m 0755 kubectl /usr/local/bin/kubectl
        if: runner.os=='macOS'
      - name: Install K3D
        run: |
          curl -s https://raw.githubusercontent.com/rancher/k3d/main/install.sh | bash
        if: runner.os!='Windows' && contains(inputs.test_environment, 'kubeflow')
      - name: Login to Amazon ECR
        id: login-ecr
        run: |
          aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 715803424590.dkr.ecr.us-east-1.amazonaws.com
        if: contains(inputs.test_environment, 'aws')
      - name: Login to Amazon EKS
        id: login-eks
        run: |
          aws eks --region us-east-1 update-kubeconfig --name zenml-ci-cluster --alias zenml-ci-aws-us-east-1
        if: contains(inputs.test_environment, 'aws')
      - name: Login to Google ECR
        run: |
          gcloud auth configure-docker --project zenml-ci
        if: contains(inputs.test_environment, 'gcp')
      - name: Login to Google GKE
        uses: google-github-actions/get-gke-credentials@3da1e46a907576cefaa90c484278bb5b259dd395  # v3.0.0
        with:
          cluster_name: zenml-ci-cluster
          location: us-east4
          project_id: zenml-ci
        if: contains(inputs.test_environment, 'gcp')
      - name: Setup tmate session before tests
        if: ${{ inputs.enable_tmate == 'before-tests' }}
        uses: mxschmitt/action-tmate@c0afd6f790e3a5564914980036ebf83216678101  # v3.23
        timeout-minutes: ${{ inputs.tmate_timeout }}
      - name: Sharded Integration Tests (Ubuntu) - Fast CI
        # Ubuntu integration tests run as 6 shards
        if: runner.os != 'macOS' && runner.os != 'Windows'
        run: |
          if [ "${INPUTS_TEST_ENVIRONMENT}" = "remote-mysql-modal" ]; then
            export MODAL_CI_SERVER_PASSWORD=$(python - <<'PY'
          from scripts.ci_modal_mysql_sandbox import derive_server_password
          print(derive_server_password())
          PY
          )
          fi
          bash scripts/test-coverage-xml.sh integration ${INPUTS_TEST_ENVIRONMENT} 6 ${{ matrix.shard }}
        env:
          INPUTS_TEST_ENVIRONMENT: ${{ inputs.test_environment == 'remote-mysql-modal' && vars.ZENML_CI_MODAL_DISABLED == 'true' && 'docker-server-mysql' || inputs.test_environment }}
          MODAL_TOKEN_SECRET: ${{ secrets.MODAL_TOKEN_SECRET }}
          ZENML_CI_CHECKOUT_REF: ${{ github.event.pull_request.head.sha || github.sha }}
      - name: Setup tmate session after tests
        if: ${{ inputs.enable_tmate == 'always' || (inputs.enable_tmate == 'on-failure' && failure()) }}
        uses: mxschmitt/action-tmate@c0afd6f790e3a5564914980036ebf83216678101  # v3.23
        timeout-minutes: ${{ inputs.tmate_timeout }}
      - name: Verify Python Env unaffected
        if: inputs.test_environment != 'remote-mysql-modal'
        run: |-
          zenml integration list
          uv pip list
          uv pip check || true

```

File: /Users/safoine/zenml-io/zenml/scripts/audit_integration_workspace_safety.py
```py
#!/usr/bin/env python3
"""Audit integration tests for workspace-safety classification."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path

INTEGRATION_ROOT = Path("tests/integration")
BASELINE_PATH = Path(".github/workspace-safety-baseline.txt")


def _is_global_state_marker(node: ast.AST) -> bool:
    """Return whether an AST node is a pytest global_state marker."""
    if isinstance(node, ast.Attribute):
        return node.attr == "global_state"
    if isinstance(node, ast.Call):
        return _is_global_state_marker(node.func)
    return False


def _decorators_include_global_state(
    node: ast.FunctionDef | ast.ClassDef,
) -> bool:
    """Return whether a function or class has the global_state marker."""
    return any(
        _is_global_state_marker(decorator) for decorator in node.decorator_list
    )


def _module_has_global_state_marker(tree: ast.Module) -> bool:
    """Return whether a module marks all tests as global-state tests."""
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "pytestmark":
                value = node.value
                values = value.elts if isinstance(value, ast.List) else [value]
                return any(_is_global_state_marker(item) for item in values)
    return False


def _test_uses_workspace_fixture(node: ast.FunctionDef) -> bool:
    """Return whether a test function requests the workspace fixture."""
    return any(arg.arg == "zenml_workspace" for arg in node.args.args)


def _iter_unclassified_tests(root: Path) -> list[str]:
    """List tests without a workspace fixture or global-state marker."""
    unclassified: list[str] = []
    for path in sorted(root.rglob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        module_is_global_state = _module_has_global_state_marker(tree)
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name.startswith(
                "test_"
            ):
                if module_is_global_state or _decorators_include_global_state(
                    node
                ):
                    continue
                if not _test_uses_workspace_fixture(node):
                    unclassified.append(f"{path}::{node.name}")
                continue

            if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                class_is_global_state = _decorators_include_global_state(node)
                for item in node.body:
                    if not isinstance(item, ast.FunctionDef):
                        continue
                    if not item.name.startswith("test_"):
                        continue
                    if (
                        module_is_global_state
                        or class_is_global_state
                        or _decorators_include_global_state(item)
                    ):
                        continue
                    if not _test_uses_workspace_fixture(item):
                        unclassified.append(
                            f"{path}::{node.name}::{item.name}"
                        )
    return unclassified


def _read_baseline(path: Path) -> set[str]:
    """Read a newline-delimited baseline file."""
    if not path.exists():
        return set()
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }


def main() -> None:
    """Run the CLI."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-baseline", action="store_true")
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args()

    unclassified = _iter_unclassified_tests(INTEGRATION_ROOT)
    if args.write_baseline:
        BASELINE_PATH.write_text(
            "# Integration tests grandfathered before workspace-safety audit.\n"
            + "\n".join(unclassified)
            + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {len(unclassified)} baseline entries to {BASELINE_PATH}")
        return

    baseline = _read_baseline(BASELINE_PATH)
    new_unclassified = [item for item in unclassified if item not in baseline]

    print(f"Unclassified integration tests: {len(unclassified)}")
    print(f"New unclassified integration tests: {len(new_unclassified)}")
    if args.enforce and new_unclassified:
        for item in new_unclassified:
            print(
                f"::error::{item} must use zenml_workspace or "
                "@pytest.mark.global_state"
            )
        raise SystemExit(1)


if __name__ == "__main__":
    main()

```

File: /Users/safoine/zenml-io/zenml/scripts/ci/classify_offload_result.py
```py
"""Classify offloaded CI results for workflow fallback decisions."""

from __future__ import annotations

import argparse
import os
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

try:
    from scripts.ci.print_junit_summary import (
        parse_junit_summary,
        print_parsed_summary,
    )
except ModuleNotFoundError:
    from print_junit_summary import parse_junit_summary, print_parsed_summary

INFRA_PATTERN = re.compile(
    r"(modal|sandbox|offload|rate.?limit|timeout|connection|network|"
    r"image build|no space left|permission denied|authentication|credentials)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Classification:
    """Normalized offload lane classification."""

    conclusion: str
    offload_infra_failed: bool
    tests_failed: bool
    message: str
    junit_current: bool
    junit_cacheable: bool


def _is_true(value: str | None) -> bool:
    return value is not None and value.lower() in {"1", "true", "yes", "on"}


def _has_junit_failures(junit_path: Path) -> bool:
    summary = parse_junit_summary(junit_path)
    print_parsed_summary(summary)
    return summary.failures > 0 or summary.errors > 0


def _infra_failure(
    message: str, *, junit_current: bool = False
) -> Classification:
    return Classification(
        conclusion="infra_failure",
        offload_infra_failed=True,
        tests_failed=False,
        message=message,
        junit_current=junit_current,
        junit_cacheable=False,
    )


def _read_log(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def classify_offload_result(
    *,
    exit_code: int,
    junit_path: Path,
    log_path: Path | None = None,
    setup_failed: bool = False,
    junit_min_mtime_ns: int | None = None,
) -> Classification:
    """Classify offload output as success, test failure, or infrastructure failure."""
    if setup_failed:
        return _infra_failure("Offload setup failed before tests ran.")

    junit_exists = junit_path.exists()
    if junit_exists and junit_min_mtime_ns is not None:
        if junit_path.stat().st_mtime_ns <= junit_min_mtime_ns:
            junit_exists = False
            stale_message = (
                "Offload did not produce current JUnit XML; existing JUnit "
                "file is a restored duration seed or stale artifact."
            )
            return _infra_failure(stale_message)

    if junit_exists:
        try:
            if _has_junit_failures(junit_path):
                return Classification(
                    conclusion="test_failure",
                    offload_infra_failed=False,
                    tests_failed=True,
                    message="Offloaded tests reported JUnit failures/errors.",
                    junit_current=True,
                    junit_cacheable=True,
                )
        except (ET.ParseError, ValueError) as exc:
            return _infra_failure(
                f"Offload produced invalid JUnit XML: {exc}",
                junit_current=True,
            )

        if exit_code in {0, 2}:
            message = "Offloaded tests passed."
            if exit_code == 2:
                message = "Offload reported flaky tests that passed on retry."
            return Classification(
                conclusion="success",
                offload_infra_failed=False,
                tests_failed=False,
                message=message,
                junit_current=True,
                junit_cacheable=True,
            )

        return _infra_failure(
            "Offload exited non-zero despite a passing JUnit report.",
            junit_current=True,
        )

    if exit_code == 0:
        return _infra_failure(
            "Offload exited successfully but did not produce JUnit XML."
        )

    log_text = _read_log(log_path)
    if INFRA_PATTERN.search(log_text):
        message = "Offload failed before producing JUnit XML; log matches infrastructure patterns."
    else:
        message = "Offload failed before producing JUnit XML."
    return _infra_failure(message)


def _write_github_outputs(classification: Classification) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as output_file:
        output_file.write(f"conclusion={classification.conclusion}\n")
        output_file.write(
            f"offload_infra_failed={str(classification.offload_infra_failed).lower()}\n"
        )
        output_file.write(
            f"tests_failed={str(classification.tests_failed).lower()}\n"
        )
        output_file.write(
            f"junit_current={str(classification.junit_current).lower()}\n"
        )
        output_file.write(
            f"junit_cacheable={str(classification.junit_cacheable).lower()}\n"
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exit-code", type=int, required=True)
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--log", type=Path)
    parser.add_argument("--setup-failed", default="false")
    parser.add_argument("--junit-min-mtime-ns", type=int)
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = _build_parser().parse_args(argv)
    classification = classify_offload_result(
        exit_code=args.exit_code,
        junit_path=args.junit,
        log_path=args.log,
        setup_failed=_is_true(args.setup_failed),
        junit_min_mtime_ns=args.junit_min_mtime_ns,
    )
    print(classification.message)
    _write_github_outputs(classification)
    return 0


if __name__ == "__main__":
    sys.exit(main())

```

File: /Users/safoine/zenml-io/zenml/pyproject.toml
```toml
[build-system]
requires = ["uv_build >= 0.8.17, <0.9.0"]
build-backend = "uv_build"

[tool.uv]
# Supply chain security: ignore Python packages published in the last 3 days.
# Most compromised packages get detected and yanked within hours; this rolling
# window blocks the majority of supply chain attacks automatically.
# Override for a single install: uv add <pkg> --exclude-newer "0 days"
# NOTE: when a version is filtered out, uv does NOT mention it — resolution
# just fails with "no compatible version found". Keep this in mind when debugging.
exclude-newer = "3 days"

[tool.uv.build-backend]
module-name = ["zenml", "zenml_cli"]

[project]
name = "zenml"
version = "0.94.3"
description = "ZenML: MLOps for Reliable AI: from Classical AI to Agents."
authors = [{name = "ZenML GmbH", email = "info@zenml.io"}]
readme = "README.md"
license = "Apache-2.0"
keywords = ["machine learning", "production", "pipeline", "mlops", "devops", "ai", "agents", "agentic workflows"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "Intended Audience :: Science/Research",
    "Intended Audience :: System Administrators",
    "License :: OSI Approved :: Apache Software License",
    "Programming Language :: Python :: 3 :: Only",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: System :: Distributed Computing",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Typing :: Typed",
]
requires-python = ">=3.10,<3.14"

dependencies = [
    "asgiref~=3.10.0",
    "click>=8.0.1,<=8.2.1",
    "cloudpickle>=2.0.0",
    "distro>=1.6.0,<2.0.0",
    "docker~=7.1.0",
    "gitpython>=3.1.18,<4.0.0",
    "jsonref",
    "opentelemetry-sdk==1.38.0",
    "packaging>=24.1",
    "psutil>=5.0.0",
    "pydantic>=2.0,<=2.12.5",
    "python-dateutil>=2.8.1,<3.0.0",
    "pyyaml>=6.0.1",
    "rich>=12.0.0", # Make sure to keep the version aligned with our `jupyter` extra
    "setuptools>=70.0.0",
]

[project.urls]
Homepage = "https://zenml.io"
Documentation = "https://docs.zenml.io"
Repository = "https://github.com/zenml-io/zenml"
Issues = "https://github.com/zenml-io/zenml/issues"

[project.scripts]
zenml = "zenml_cli:cli"

[project.optional-dependencies]
local = [
    "alembic>=1.8.1,<=1.15.2",
    "bcrypt==4.0.1",
    "passlib[bcrypt]~=1.7.4",
    "pymysql>=1.1.1,~=1.1.0",
    "sqlalchemy>=2.0.0,<3.0.0",
    "sqlalchemy_utils",
    "sqlmodel==0.0.18",
    "jsonschema>=4.0.0",
]
server = [
    "zenml[local,native-schedules]",  # Includes all the DB dependencies
    "fastapi>=0.100,<=0.115.8",
    "uvicorn[standard]>=0.17.5",
    "python-multipart~=0.0.9",
    "pyjwt[crypto]==2.7.*",
    "fastapi-utils",
    "orjson~=3.10.0",
    "Jinja2",
    "ipinfo>=4.4.3",
    "secure~=1.0.1",
    "tldextract~=5.1.0",
    "itsdangerous~=2.2.0",
    "croniter>=6.0.0",
    "cachetools>=5.3.0,<8.0.0",
]
jupyter = ["rich[jupyter]>=12.0.0"]
templates = ["copier>=8.1.0", "jinja2-time>=0.2.0,<0.3.0", "ruff>=0.1.7", "pyyaml-include<2.0"]
terraform = ["python-terraform"]
secrets-aws = ["boto3>=1.16.0"]
secrets-gcp = ["google-cloud-secret-manager>=2.12.5"]
secrets-azure = ["azure-identity>=1.4.0", "azure-keyvault-secrets>=4.0.0"]
secrets-hashicorp = ["hvac>=0.11.2"]
s3fs = ["s3fs>=2022.11.0,!=2025.3.1"]
gcsfs = ["gcsfs>=2022.11.0"]
adlfs = ["adlfs>=2021.10.0"]
connectors-kubernetes = ["kubernetes>=18.20.0"]
connectors-aws = ["boto3>=1.16.0", "kubernetes>=18.20.0", "aws-profile-manager>=0.5.0"]
connectors-gcp = [
    "google-cloud-container>=2.21.0",
    "google-cloud-storage>=2.9.0",
    "google-cloud-artifact-registry>=1.11.3",
    "kubernetes>=18.20.0",
]
connectors-azure = [
    "azure-identity>=1.4.0",
    "azure-mgmt-containerservice>=20.0.0",
    "azure-mgmt-containerregistry>=10.0.0",
    "azure-mgmt-storage>=20.0.0",
    "azure-storage-blob>=12.0.0",
    "azure-mgmt-resource>=21.0.0,<25.0.0",
    "kubernetes>=18.20.0",
    "requests>=2.27.11,<3.0.0",
    "marshmallow<4.0.0",
]
sagemaker = [
    "sagemaker>=2.237.3,<3.0.0",
]
vertex = [
    "google-cloud-aiplatform>=1.34.0",
    "kfp>=2.6.0",
    "urllib3<2.6.0",
    "google-cloud-pipeline-components>=2.19.0",
]
azureml = [
    "azure-ai-ml==1.23.1",
]
dev = [
    "bandit>=1.7.5,<2.0.0",
    "ruff>=0.1.7",
    "yamlfix>=1.16.0",
    "zizmor>=1.0.0",
    "coverage[toml]>=5.5,<6.0.0",
    "pytest>=7.4.0,<8.0.0",
    "mypy==1.18.1",
    "pre-commit",
    "pyment>=0.3.3,<0.4.0",
    "tox>=3.24.3",
    "hypothesis>=6.43.1",
    "typing-extensions>=3.7.4",
    "pydoclint>=0.8.3",
    "pytest-randomly>=3.10.1,<4.0.0",
    "pytest-mock>=3.6.1,<4.0.0",
    "pytest-clarity>=1.0.1,<2.0.0",
    "pytest-instafail>=0.5.0",
    "pytest-rerunfailures>=13.0,<14.0.0",
    "pytest-split>=0.10.0,<0.11.0",
    "mkdocs>=1.6.1,<2.0.0",
    "mkdocs-material==9.6.8",
    "mkdocs-awesome-pages-plugin>=2.10.1,<3.0.0",
    "mkdocstrings[python]>=0.28.1,<1.0.0",
    "mkdocstrings-python",
    "mkdocs-autorefs>=1.4.0,<2.0.0",
    "mike>=1.1.2,<2.0.0",
    "maison<2.0",
    "types-certifi>=2021.10.8.0",
    "types-croniter>=1.0.2",
    "types-futures>=3.3.1",
    "types-hvac>=2.3.0",
    "types-Markdown>=3.3.6",
    "types-paramiko>=3.4.0,<4.0.0",
    "types-Pillow>=9.2.1",
    "types-protobuf>=3.18.0",
    "types-PyMySQL>=1.0.4",
    "types-python-dateutil>=2.8.2",
    "types-python-slugify>=5.0.2",
    "types-PyYAML>=6.0.0",
    "types-redis>=4.1.19",
    "types-requests>=2.27.11",
    "types-setuptools>=57.4.2",
    "types-six>=1.16.2",
    "types-termcolor>=1.1.2",
    "types-psutil>=5.8.13",
    "types-passlib>=1.7.7",
    "types-jsonschema>=4.26.0",
    "types-cachetools>=5.3.0,<8.0.0"
]

[tool.pytest.ini_options]
filterwarnings = ["ignore::DeprecationWarning"]
log_cli = false
log_cli_level = "INFO"
testpaths = "tests"
xfail_strict = true
norecursedirs = [
    "tests/integration/examples/*", # ignore example folders
]

[tool.coverage.run]
parallel = true
source = ["src/zenml"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    'if __name__ == "__main__":',
    "if TYPE_CHECKING:",
]

[tool.ruff]
line-length = 79
# Exclude a variety of commonly ignored directories.
exclude = [
    ".bzr",
    ".direnv",
    ".eggs",
    ".git",
    ".hg",
    ".mypy_cache",
    ".nox",
    ".pants.d",
    ".ruff_cache",
    ".svn",
    ".tox",
    ".venv",
    "__pypackages__",
    "_build",
    "buck-out",
    ".test_durations",
    "build",
    "dist",
    "node_modules",
    "venv",
    '__init__.py',
    'src/zenml/cli/version.py',
    # LitGPT files from the LLM Finetuning example
    'examples/llm_finetuning/evaluate',
    'examples/llm_finetuning/finetune',
    'examples/llm_finetuning/generate',
    'examples/llm_finetuning/lit_gpt',
    'examples/llm_finetuning/scripts',
]

src = ["src", "test"]
# use Python 3.10 as the minimum version for autofixing
target-version = "py310"


[tool.ruff.format]
exclude = [
    "*.git",
    "*.hg",
    ".mypy_cache",
    ".tox",
    ".venv",
    "_build",
    "buck-out",
    "build]",
]

[tool.ruff.lint]
# Disable autofix for unused imports (`F401`).
unfixable = ["F401"]
per-file-ignores = { }
ignore = [
    "E501",
    "F401",
    "F403",
    "D301",
    "D401",
    "D403",
    "D407",
    "D213",
    "D203",
    "S101",
    "S104",
    "S105",
    "S106",
    "S107",
]
select = ["D", "E", "F", "I", "I001", "Q"]

[tool.ruff.lint.flake8-import-conventions.aliases]
altair = "alt"
"matplotlib.pyplot" = "plt"
numpy = "np"
pandas = "pd"
seaborn = "sns"

[tool.ruff.lint.mccabe]
max-complexity = 18

[tool.ruff.lint.pydocstyle]
# Use Google-style docstrings.
convention = "google"

[tool.pydoclint]
style = "google"
arg-type-hints-in-docstring = false
arg-type-hints-in-signature = true
check-return-types = false
check-yield-types = false
allow-init-docstring = true
check-class-attributes = false
check-arg-order = false
omit-stars-when-documenting-varargs = true
baseline = "pydoclint-baseline.txt"
auto-regenerate-baseline = true

[tool.bandit]
skips = ["B615"]

[tool.mypy]

plugins = ["pydantic.mypy"]

strict = true
namespace_packages = true
show_error_codes = true

# import all google, transformers and datasets files as `Any`
[[tool.mypy.overrides]]
module = [
    "google.*",
    "transformers.*", # https://github.com/huggingface/transformers/issues/13390
    "datasets.*",
    "langchain_community.*",
    "IPython.core.*",
]
follow_imports = "skip"

[[tool.mypy.overrides]]
module = [
    "airflow.*",
    "tensorflow.*",
    "apache_beam.*",
    "pandas.*",
    "distro.*",
    "analytics.*",
    "absl.*",
    "gcsfs.*",
    "s3fs.*",
    "adlfs.*",
    "fsspec.*",
    "torch.*",
    "pytorch_lightning.*",
    "sklearn.*",
    "numpy.*",
    "facets_overview.*",
    "IPython.core.*",
    "IPython.display.*",
    "plotly.*",
    "dash.*",
    "dash_bootstrap_components.*",
    "dash_cytoscape",
    "dash.dependencies",
    "docker.*",
    "flask.*",
    "kfp.*",
    "kubernetes.*",
    "urllib3.*",
    "kfp_server_api.*",
    "sagemaker.*",
    "azureml.*",
    "google.*",
    "google_cloud_pipeline_components.*",
    "neuralprophet.*",
    "lightgbm.*",
    "scipy.*",
    "seaborn.*",
    "deepchecks.*",
    "boto3.*",
    "botocore.*",
    "jupyter_dash.*",
    "slack_sdk.*",
    "azure-keyvault-keys.*",
    "azure-mgmt-resource.*",
    "azure.mgmt.resource.*",
    "model_archiver.*",
    "kfp_tekton.*",
    "mlflow.*",
    "python_terraform.*",
    "bentoml.*",
    "multipart.*",
    "jose.*",
    "sqlalchemy_utils.*",
    "sky.*",
    "copier.*",
    "datasets.*",
    "pyngrok.*",
    "cloudpickle.*",
    "matplotlib.*",
    "IPython.*",
    "huggingface_hub.*",
    "distutils.*",
    "accelerate.*",
    "label_studio_sdk.*",
    "argilla.*",
    "lightning_sdk.*",
    "peewee.*",
    "prodigy.*",
    "prodigy.components.*",
    "prodigy.components.db.*",
    "transformers.*",
    "vllm.*",
    "numba.*",
    "uvloop.*",
    "litellm",
    "mlx",
    "mlx.*",
    "runai",
    "runai.*",
    "jsonref",
]
ignore_missing_imports = true

[[tool.mypy.overrides]]
module = ["mlx.core.*"]  # workaround for failing mypy stub parsing (mlx==0.29.4 version)
follow_imports = 'skip'
follow_imports_for_stubs = true

```

File: /Users/safoine/zenml-io/zenml/src/zenml/cli/integration.py
```py
#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.

#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:

#       https://www.apache.org/licenses/LICENSE-2.0

#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Functionality to install or uninstall ZenML integrations via the CLI."""

import os
import subprocess
import sys
from typing import Optional, Tuple

import click
from rich.progress import track

from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import (
    confirmation,
    declare,
    error,
    exception,
    format_integration_list,
    install_packages,
    print_table,
    title,
    uninstall_package,
    warning,
)
from zenml.console import console
from zenml.enums import CliCategories
from zenml.logger import get_logger

_WHYLOGS_INTEGRATION_WARNING = (
    "WhyLabs was acquired by Apple and the hosted WhyLabs platform is being "
    "discontinued. The whylogs library remains open source and the WhyLabs "
    "platform is now available as OSS at "
    "https://github.com/whylabs/whylabs-oss, but hosted functionality may stop "
    "working. Plan accordingly before continuing with the whylogs integration."
)

logger = get_logger(__name__)


@cli.group(
    cls=TagGroup,
    tag=CliCategories.INTEGRATIONS,
)
def integration() -> None:
    """Interact with external integrations."""


@integration.command(name="list", help="List the available integrations.")
def list_integrations() -> None:
    """List all available integrations with their installation status."""
    from zenml.integrations.registry import integration_registry

    formatted_table = format_integration_list(
        sorted(list(integration_registry.integrations.items()))
    )
    print_table(formatted_table)
    warning(
        "\n" + "To install the dependencies of a specific integration, type: "
    )
    warning("zenml integration install INTEGRATION_NAME")


@integration.command(
    name="requirements", help="List all requirements for an integration."
)
@click.argument("integration_name", required=False, default=None)
def get_requirements(integration_name: Optional[str] = None) -> None:
    """List all requirements for the chosen integration.

    Args:
        integration_name: The name of the integration to list the requirements
            for.
    """
    from zenml.integrations.registry import integration_registry

    try:
        requirements = integration_registry.select_integration_requirements(
            integration_name
        )
    except KeyError as e:
        exception(e)
    else:
        if requirements:
            title(
                f"Requirements for {integration_name or 'all integrations'}:\n"
            )
            declare(f"{requirements}")
            warning(
                "\n" + "To install the dependencies of a "
                "specific integration, type: "
            )
            warning("zenml integration install INTEGRATION_NAME")


@integration.command(
    name="export-requirements", help="Export the integration requirements."
)
@click.argument("integrations", nargs=-1, required=False)
@click.option(
    "--ignore-integration",
    "-i",
    multiple=True,
    help="List of integrations to ignore explicitly.",
)
@click.option(
    "--output-file",
    "-o",
    "output_file",
    type=str,
    required=False,
    help="File to which to export the integration requirements. If not "
    "provided, the requirements will be printed to stdout instead.",
)
@click.option(
    "--overwrite",
    "-ov",
    "overwrite",
    type=bool,
    required=False,
    is_flag=True,
    help="Overwrite the output file if it already exists. This option is "
    "only valid if the output file is provided.",
)
@click.option(
    "--installed-only",
    "installed_only",
    is_flag=True,
    default=False,
    help="Only export requirements for integrations installed in your current "
    "environment. This can not be specified when also providing explicit "
    "integrations.",
)
@click.option(
    "--poetry",
    "poetry",
    is_flag=True,
    default=False,
    help="Add the exported requirements to your current Poetry project.",
)
def export_requirements(
    integrations: Tuple[str],
    ignore_integration: Tuple[str],
    output_file: Optional[str] = None,
    overwrite: bool = False,
    installed_only: bool = False,
    poetry: bool = False,
) -> None:
    """Exports integration requirements so they can be installed using pip.

    Args:
        integrations: The name of the integration to install the requirements
            for.
        ignore_integration: List of integrations to ignore explicitly.
        output_file: Optional path to the requirements output file.
        overwrite: Overwrite the output file if it already exists. This option
            is only valid if the output file is provided.
        installed_only: Only export requirements for integrations installed in
            your current environment. This can not be specified when also
            providing explicit integrations.
        poetry: Add the exported requirements to your current Poetry project.
    """
    from zenml.integrations.registry import integration_registry

    if installed_only and integrations:
        error(
            "You can either provide specific integrations or export only "
            "requirements for integrations installed in your local "
            "environment, not both."
        )

    if poetry and output_file:
        error(
            "You can either specify an output file or add the requirements to "
            "the Poetry project, not both."
        )

    all_integrations = set(integration_registry.integrations.keys())

    if integrations:
        integrations_to_export = set(integrations)
    elif installed_only:
        integrations_to_export = set(
            integration_registry.get_installed_integrations()
        )
    else:
        integrations_to_export = all_integrations

    for i in ignore_integration:
        try:
            integrations_to_export.remove(i)
        except KeyError:
            if i not in all_integrations:
                error(
                    f"Integration {i} does not exist. Available integrations: "
                    f"{all_integrations}"
                )

    if "whylogs" in integrations_to_export:
        warning(_WHYLOGS_INTEGRATION_WARNING)

    requirements = []
    for integration_name in integrations_to_export:
        try:
            requirements += (
                integration_registry.select_integration_requirements(
                    integration_name
                )
            )
        except KeyError:
            error(f"Unable to find integration '{integration_name}'.")

    if output_file:
        try:
            with open(output_file, "x") as f:
                f.write("\n".join(requirements))
        except FileExistsError:
            if overwrite or confirmation(
                "A file already exists at the specified path. "
                "Would you like to overwrite it?"
            ):
                with open(output_file, "w") as f:
                    f.write("\n".join(requirements))
        declare(f"Requirements exported to {output_file}.")
    if poetry:
        res = os.popen("poetry env list").read()
        envs = [
            env
            for env in res.split("\n")
            if env.lower().find("(activated)") > 0
        ]
        if len(envs) == 0:
            error(
                "No activated Poetry environment found. Please activate one "
                "and try again."
            )
        else:
            # Use subprocess.run with shell=False to avoid command injection
            args = ["poetry", "add"] + requirements
            subprocess.run(args, check=True)
            declare(
                f"Requirements added to `{envs[0]}` environment in Poetry."
            )
    else:
        click.echo(" ".join(requirements), nl=False)


@integration.command(
    help="Install the required packages for the integration of choice."
)
@click.argument("integrations", nargs=-1, required=False)
@click.option(
    "--ignore-integration",
    "-i",
    multiple=True,
    help="Integrations to ignore explicitly (passed in separately).",
)
@click.option(
    "--yes",
    "-y",
    "force",
    is_flag=True,
    help="Force the installation of the required packages. This will skip the "
    "confirmation step and reinstall existing packages as well",
)
@click.option(
    "--uv",
    "uv",
    is_flag=True,
    help="Experimental: Use uv for package installation.",
    default=False,
)
def install(
    integrations: Tuple[str],
    ignore_integration: Tuple[str],
    force: bool = False,
    uv: bool = False,
) -> None:
    """Installs the required packages for a given integration.

    If no integration is specified all required packages for all integrations
    are installed using pip or uv.

    Args:
        integrations: The name of the integration to install the requirements
            for.
        ignore_integration: Integrations to ignore explicitly (passed in
            separately).
        force: Force the installation of the required packages.
        uv: Use uv for package installation (experimental).
    """
    from zenml.cli.utils import is_pip_installed, is_uv_installed
    from zenml.integrations.registry import integration_registry

    if uv and not is_uv_installed():
        error(
            "UV is not installed but the uv flag was passed in. Please install "
            "uv or remove the uv flag."
        )

    if not uv and not is_pip_installed():
        error(
            "Pip is not installed. Please install pip or use the uv flag "
            "(--uv) for package installation."
        )

    if not integrations:
        # no integrations specified, use all registered integrations
        integration_set = set(integration_registry.integrations.keys())

        for i in ignore_integration:
            try:
                integration_set.remove(i)
            except KeyError:
                error(
                    f"Integration {i} does not exist. Available integrations: "
                    f"{list(integration_registry.integrations.keys())}"
                )
    else:
        integration_set = set(integrations)

    if "whylogs" in integration_set:
        warning(_WHYLOGS_INTEGRATION_WARNING)

    if sys.version_info.minor == 12 and "tensorflow" in integration_set:
        warning(
            "The TensorFlow integration is not yet compatible with Python "
            "3.12, thus its installation is skipped. Consider using a "
            "different version of Python and stay in touch for further updates."
        )
        integration_set.remove("tensorflow")

    if sys.version_info.minor == 12 and "deepchecks" in integration_set:
        warning(
            "The Deepchecks integration is not yet compatible with Python "
            "3.12, thus its installation is skipped. Consider using a "
            "different version of Python and stay in touch for further updates."
        )
        integration_set.remove("deepchecks")

    requirements = []
    integrations_to_install = []
    for integration_name in integration_set:
        try:
            if force or not integration_registry.is_installed(
                integration_name
            ):
                requirements += (
                    integration_registry.select_integration_requirements(
                        integration_name
                    )
                )
                integrations_to_install.append(integration_name)
            else:
                declare(
                    f"All required packages for integration "
                    f"'{integration_name}' are already installed."
                )
        except KeyError:
            error(f"Unable to find integration '{integration_name}'.")

    if requirements and (
        force
        or confirmation(
            "Are you sure you want to install the following "
            "packages to the current environment?\n"
            f"{requirements}"
        )
    ):
        with console.status("Installing integrations..."):
            install_packages(requirements, use_uv=uv)


@integration.command(
    help="Uninstall the required packages for the integration of choice."
)
@click.argument("integrations", nargs=-1, required=False)
@click.option(
    "--yes",
    "-y",
    "force",
    is_flag=True,
    help="Force the uninstallation of the required packages. This will skip "
    "the confirmation step",
)
@click.option(
    "--uv",
    "uv",
    is_flag=True,
    help="Experimental: Use uv for package uninstallation.",
    default=False,
)
def uninstall(
    integrations: Tuple[str], force: bool = False, uv: bool = False
) -> None:
    """Uninstalls the required packages for a given integration.

    If no integration is specified all required packages for all integrations
    are uninstalled using pip or uv.

    Args:
        integrations: The name of the integration to uninstall the requirements
            for.
        force: Force the uninstallation of the required packages.
        uv: Use uv for package uninstallation (experimental).
    """
    from zenml.cli.utils import is_pip_installed, is_uv_installed
    from zenml.integrations.registry import integration_registry

    if uv and not is_uv_installed():
        error("Package `uv` is not installed. Please install it and retry.")

    if not uv and not is_pip_installed():
        error(
            "Pip is not installed. Please install pip or use the uv flag "
            "(--uv) for package installation."
        )

    if not integrations:
        # no integrations specified, use all registered integrations
        integrations = tuple(integration_registry.integrations.keys())

    requirements = []
    for integration_name in integrations:
        try:
            if integration_registry.is_installed(integration_name):
                requirements += (
                    integration_registry.select_uninstall_requirements(
                        integration_name
                    )
                )
            else:
                warning(
                    f"Requirements for integration '{integration_name}' "
                    f"already not installed."
                )
        except KeyError:
            warning(f"Unable to find integration '{integration_name}'.")

    if requirements and (
        force
        or confirmation(
            "Are you sure you want to uninstall the following "
            "packages from the current environment?\n"
            f"{requirements}"
        )
    ):
        for n in track(
            range(len(requirements)),
            description="Uninstalling integrations...",
        ):
            uninstall_package(requirements[n], use_uv=uv)


@integration.command(
    help="Upgrade the required packages for the integration of choice."
)
@click.argument("integrations", nargs=-1, required=False)
@click.option(
    "--yes",
    "-y",
    "force",
    is_flag=True,
    help="Force the upgrade of the required packages. This will skip the "
    "confirmation step and re-upgrade existing packages as well",
)
@click.option(
    "--uv",
    "uv",
    is_flag=True,
    help="Experimental: Use uv for package upgrade.",
    default=False,
)
def upgrade(
    integrations: Tuple[str],
    force: bool = False,
    uv: bool = False,
) -> None:
    """Upgrade the required packages for a given integration.

    If no integration is specified all required packages for all integrations
    are installed using pip or uv.

    Args:
        integrations: The name of the integration to install the requirements
            for.
        force: Force the installation of the required packages.
        uv: Use uv for package installation (experimental).
    """
    from zenml.cli.utils import is_pip_installed, is_uv_installed
    from zenml.integrations.registry import integration_registry

    if uv and not is_uv_installed():
        error("Package `uv` is not installed. Please install it and retry.")

    if not uv and not is_pip_installed():
        error(
            "Pip is not installed. Please install pip or use the uv flag "
            "(--uv) for package installation."
        )

    if not integrations:
        # no integrations specified, use all registered integrations
        integrations = set(integration_registry.integrations.keys())

    requirements = []
    integrations_to_install = []
    for integration_name in integrations:
        try:
            if integration_registry.is_installed(integration_name):
                requirements += (
                    integration_registry.select_integration_requirements(
                        integration_name
                    )
                )
                integrations_to_install.append(integration_name)
            else:
                declare(
                    f"None of the required packages for integration "
                    f"'{integration_name}' are installed."
                )
        except KeyError:
            warning(f"Unable to find integration '{integration_name}'.")

    if requirements and (
        force
        or confirmation(
            f"Are you sure you want to upgrade the following "
            "packages to the current environment?\n"
            f"{requirements}"
        )
    ):
        with console.status("Upgrading integrations..."):
            install_packages(requirements, upgrade=True, use_uv=uv)

```

File: /Users/safoine/zenml-io/zenml/scripts/run-ci-checks.sh
```sh
#!/usr/bin/env bash
set -e
set -x

export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false

scripts/lint.sh
scripts/check-spelling.sh

```

File: /Users/safoine/zenml-io/zenml/.github/workflows/integration-test-slow-services.yml
```yml
---
name: Integration Tests (Slow CI)
on:
  workflow_call:
    inputs:
      os:
        description: OS
        type: string
        required: true
      python-version:
        description: Python version
        type: string
        required: true
      test_environment:
        description: The test environment
        type: string
        required: true
      enable_tmate:
        description: Enable tmate session for debugging
        type: string
        required: false
        default: never
      tmate_timeout:
        description: Timeout for tmate session (minutes)
        type: number
        required: false
        default: 30
      reruns:
        description: Pytest rerun count (0 disables)
        type: number
        required: false
        default: 3
  workflow_dispatch:
    inputs:
      os:
        description: OS
        type: choice
        options: [ubuntu-latest, macos-13, windows-latest]
        required: false
        default: ubuntu-latest
      python-version:
        description: Python version
        type: choice
        options: ['3.10', '3.11', '3.12', '3.13']
        required: false
        default: '3.11'
      test_environment:
        description: The test environment
        type: choice
        options:
          # Default ZenML deployments
          - default
          - default-docker-orchestrator
          - default-airflow-orchestrator
          # Local ZenML server deployments
          - local-server
          - local-server-docker-orchestrator
          - local-server-airflow-orchestrator
          # Local ZenML docker-compose server deployments
          - docker-server-mysql
          - docker-server-mariadb
          - docker-server-docker-orchestrator-mysql
          - docker-server-docker-orchestrator-mariadb
          - docker-server-airflow-orchestrator-mysql
          - docker-server-airflow-orchestrator-mariadb
        required: false
        default: default
      enable_tmate:
        description: Enable tmate session for debugging
        type: choice
        options: [no, on-failure, always, before-tests]
        required: false
        default: 'no'
      tmate_timeout:
        description: Timeout for tmate session (minutes)
        type: number
        required: false
        default: 30
      reruns:
        description: Pytest rerun count (0 disables)
        type: number
        required: false
        default: 3
jobs:
  integration-tests-slow:
    name: integration-tests-slow
    runs-on: ${{ inputs.os }}
    strategy:
      fail-fast: false
    env:
      ZENML_DEBUG: 1
      ZENML_ANALYTICS_OPT_IN: false
      ZENML_ENABLE_RICH_TRACEBACK: false
      WHYLOGS_NO_ANALYTICS: 'True'
      PYTHONIOENCODING: utf-8
      UV_HTTP_TIMEOUT: 600
      # on MAC OS, we need to set this environment variable
      # to fix problems with the fork() calls (see this thread
      # for more information: http://sealiesoftware.com/blog/archive/2017/6/5/Objective-C_and_fork_in_macOS_1013.html)
      OBJC_DISABLE_INITIALIZE_FORK_SAFETY: 'YES'
      AWS_ACCESS_KEY_ID: ${{ secrets.AWS_US_EAST_1_ENV_ACCESS_KEY_ID }}
      AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_US_EAST_1_ENV_SECRET_ACCESS_KEY }}
      AWS_US_EAST_1_SERVER_URL: ${{ secrets.AWS_US_EAST_1_SERVER_URL }}
      AWS_US_EAST_1_SERVER_USERNAME: ${{ secrets.AWS_US_EAST_1_SERVER_USERNAME }}
      AWS_US_EAST_1_SERVER_PASSWORD: ${{ secrets.AWS_US_EAST_1_SERVER_PASSWORD }}
      GCP_US_EAST4_SERVER_URL: ${{ secrets.GCP_US_EAST4_SERVER_URL }}
      GCP_US_EAST4_SERVER_USERNAME: ${{ secrets.GCP_US_EAST4_SERVER_USERNAME }}
      GCP_US_EAST4_SERVER_PASSWORD: ${{ secrets.GCP_US_EAST4_SERVER_PASSWORD }}
      PYTEST_RERUNS: ${{ inputs.reruns }}
    # TODO: add Windows testing for Python 3.11 and 3.12 back in
    # TODO: add macos testing back in
    if: ${{ ! startsWith(github.event.head_commit.message, 'GitBook:') && ! (inputs.os == 'windows-latest' && inputs.python-version == '3.11') && ! (inputs.os == 'windows-latest' && inputs.python-version == '3.12') && ! (inputs.os == 'macos-13' || inputs.os == 'macos-latest')  }}
    defaults:
      run:
        shell: bash
    steps:
      - name: Login to Docker Hub
        uses: docker/login-action@4907a6ddec9925e35a0a9e82d7399ccc52663121 # v4.1.0
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}
        if: github.event.pull_request.head.repo.fork == false && (contains(inputs.test_environment,
          'docker') || contains(inputs.test_environment, 'kubeflow') || contains(inputs.test_environment,
          'airflow') || contains(inputs.test_environment, 'kubernetes'))
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6.0.2
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@ec61189d14ec14c8efccab744f656cffd0e33f37 # v6.1.0
        with:
          role-to-assume: ${{ secrets.AWS_US_EAST_1_ENV_ROLE_ARN }}
          aws-region: us-east-1
        if: contains(inputs.test_environment, 'aws')
      - name: Configure GCP credentials
        uses: google-github-actions/auth@7c6bc770dae815cd3e89ee6cdf493a5fab2cc093 # v3.0.0
        with:
          credentials_json: ${{ secrets.GCP_US_EAST4_ENV_CREDENTIALS }}
        if: contains(inputs.test_environment, 'gcp')
      - name: Set up gcloud SDK
        uses: google-github-actions/setup-gcloud@aa5489c8933f4cc7a4f7d45035b3b1440c9c10db # v3.0.1
        with:
          install_components: gke-gcloud-auth-plugin
        if: contains(inputs.test_environment, 'gcp')
      - name: Setup environment
        uses: ./.github/actions/setup_environment
        with:
          python-version: ${{ inputs.python-version }}
          os: ${{ inputs.os }}
      - name: Install docker-compose for non-default environments
        if: inputs.test_environment != 'default'
        run: |
          pip install uv
          # see https://github.com/docker/docker-py/issues/3256 for why we need to pin requests
          # docker-compose is deprecated and doesn't work with newer versions of docker
          uv pip install --system "pyyaml==5.3.1" "requests<2.32.0" "docker==6.1.3" docker-compose
      - name: Install MacOS System Dependencies
        if: runner.os=='macOS'
        run: brew install libomp
      - name: Unbreak Python in GHA for 3.10
        if: runner.os=='macOS' && inputs.python-version != '3.11'
        # github actions overwrites brew's python. Force it to reassert itself, by
        # running in a separate step.
        # Workaround GitHub Actions Python issues
        # see https://github.com/Homebrew/homebrew-core/issues/165793#issuecomment-1989441193
        run: |
          find /usr/local/bin -lname '*/Library/Frameworks/Python.framework/*' -delete
          sudo rm -rf /Library/Frameworks/Python.framework/
          brew install --force python3 && brew unlink python3 && brew unlink python3 && brew link --overwrite python3
      - name: Unbreak Python in GHA for 3.11
        if: runner.os=='macOS' && inputs.python-version == '3.11'
        run: |
          # Unlink and re-link to prevent errors when github mac runner images
          # https://github.com/actions/setup-python/issues/577
          brew list -1 | grep python | while read formula; do brew unlink $formula; brew link --overwrite $formula; done
      - name: Install Docker and Colima on MacOS
        if: runner.os=='macOS'
        run: |
          export HOMEBREW_NO_INSTALLED_DEPENDENTS_CHECK=1
          brew update
          brew install docker colima
          brew reinstall --force qemu

          # We need to mount the /private/tmp/zenml-test/ folder because
          # this folder is also mounted in the Docker containers that are
          # started by local ZenML orchestrators.
          colima start --mount /private/tmp/zenml-test/:w

          # This is required for the Docker Python SDK to work
          sudo ln -sf $HOME/.colima/default/docker.sock /var/run/docker.sock
      - name: Install kubectl on Linux
        run: |
          curl -LO "https://dl.k8s.io/release/v1.35.0/bin/linux/amd64/kubectl"
          sudo install -o root -g 0 -m 0755 kubectl /usr/local/bin/kubectl
        if: (inputs.os == 'ubuntu-latest' || inputs.os == 'arc-runner-set')
      - name: Install kubectl on MacOS
        run: |
          curl -LO "https://dl.k8s.io/release/v1.35.0/bin/darwin/amd64/kubectl"
          sudo install -o root -g 0 -m 0755 kubectl /usr/local/bin/kubectl
        if: runner.os=='macOS'
      - name: Install K3D
        run: |
          curl -s https://raw.githubusercontent.com/rancher/k3d/main/install.sh | bash
        if: runner.os!='Windows' && contains(inputs.test_environment, 'kubeflow')
      - name: Login to Amazon ECR
        id: login-ecr
        run: |
          aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 715803424590.dkr.ecr.us-east-1.amazonaws.com
        if: contains(inputs.test_environment, 'aws')
      - name: Login to Amazon EKS
        id: login-eks
        run: |
          aws eks --region us-east-1 update-kubeconfig --name zenml-ci-cluster --alias zenml-ci-aws-us-east-1
        if: contains(inputs.test_environment, 'aws')
      - name: Login to Google ECR
        run: |
          gcloud auth configure-docker --project zenml-ci
        if: contains(inputs.test_environment, 'gcp')
      - name: Login to Google GKE
        uses: google-github-actions/get-gke-credentials@3da1e46a907576cefaa90c484278bb5b259dd395 # v3.0.0
        with:
          cluster_name: zenml-ci-cluster
          location: us-east4
          project_id: zenml-ci
        if: contains(inputs.test_environment, 'gcp')
      - name: Setup tmate session before tests
        if: ${{ inputs.enable_tmate == 'before-tests' }}
        uses: mxschmitt/action-tmate@c0afd6f790e3a5564914980036ebf83216678101 # v3.23
        timeout-minutes: ${{ inputs.tmate_timeout }}
      - name: Integration Tests - Slow CI
        run: |
          bash scripts/test-coverage-xml.sh integration ${INPUTS_TEST_ENVIRONMENT}
        env:
          INPUTS_TEST_ENVIRONMENT: ${{ inputs.test_environment }}
      - name: Setup tmate session after tests
        if: ${{ inputs.enable_tmate == 'always' || (inputs.enable_tmate == 'on-failure' && failure()) }}
        uses: mxschmitt/action-tmate@c0afd6f790e3a5564914980036ebf83216678101 # v3.23
        timeout-minutes: ${{ inputs.tmate_timeout }}
      - name: Verify Python Env unaffected
        run: |-
          zenml integration list
          uv pip list
          uv pip check || true
    services:
      mysql:
        image: mysql:5.7
        env:
          MYSQL_ROOT_PASSWORD: zenml
          MYSQL_DATABASE: zenml
        ports: 
          - 3306:3306
        options: >-
          --health-cmd="mysqladmin ping"
          --health-interval=10s
          --health-timeout=5s
          --health-retries=3
      zenml-server:
        image: ghcr.io/${{ github.repository_owner }}/zenml-server-github-actions:${{
          github.sha }}
        credentials:
          username: ${{ github.actor }}
          password: ${{ secrets.github_token }}
        env:
          ZENML_STORE_URL: mysql://root:zenml@mysql:3306/zenml
          ZENML_SERVER_DEPLOYMENT_TYPE: docker
          ZENML_SERVER_AUTO_ACTIVATE: 'True'
          ZENML_SERVER_AUTO_CREATE_DEFAULT_USER: 'True'
        ports:   
          - 8080:8080
        options: >-
          --health-cmd="curl -f http://127.0.0.1:8080/health"
          --health-interval=10s
          --health-timeout=5s
          --health-retries=3

```

File: /Users/safoine/zenml-io/zenml/scripts/install-zenml-dev.sh
```sh
#!/bin/sh -e

INTEGRATIONS=no
PIP_ARGS=
UPGRADE_ALL=no

show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Install ZenML in development mode with optional integrations.

OPTIONS:
    -i, --integrations yes|no    Install integrations (default: no)
    -s, --system                 Install packages system-wide instead of in virtual environment
    -u, --upgrade-all           Uninstall existing ZenML, clear caches, and install latest versions
    -h, --help                  Show this help message

EXAMPLES:
    # Basic installation
    $0
    
    # Install with integrations
    $0 --integrations yes
    
    # Force reinstall with latest versions of all dependencies
    $0 --upgrade-all --integrations yes
    
    # System-wide installation with latest versions
    $0 --system --upgrade-all

NOTES:
    - The --upgrade-all flag will uninstall existing ZenML installation and clear all caches
    - This ensures you get the latest compatible versions of all dependencies
    - Use this when you want to refresh your environment with the newest packages

EOF
}

parse_args () {
    while [ $# -gt 0 ]; do
        case $1 in
            -i|--integrations)
                INTEGRATIONS="$2"
                shift # past argument
                shift # past value
                ;;
            -s|--system)
                PIP_ARGS="--system"
                shift # past argument
                ;;
            -u|--upgrade-all)
                UPGRADE_ALL="yes"
                shift # past argument
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            -*|--*)
                echo "Unknown option $1"
                show_help
                exit 1
                ;;
            *)
                shift # past argument
                ;;
        esac
    done
}

clean_and_uninstall() {
    echo "🧹 Cleaning existing ZenML installation and clearing caches..."
    
    # Uninstall ZenML (if installed) and clear pip cache
    uv pip uninstall $PIP_ARGS zenml || true
    
    # Clear uv cache to ensure fresh downloads
    uv cache clean || true
    
    # Clear pip cache as well (in case pip was used previously)
    python -m pip cache purge 2>/dev/null || true
    
    echo "✅ Cleanup completed"
}

install_zenml() {
    echo "📦 Installing ZenML in editable mode..."
    
    # Build upgrade arguments based on UPGRADE_ALL flag
    upgrade_args=""
    if [ "$UPGRADE_ALL" = "yes" ]; then
        upgrade_args="--upgrade --force-reinstall"
        echo "🔄 Using --upgrade --force-reinstall to get latest versions"
    fi
    
    # install ZenML in editable mode
    uv pip install $PIP_ARGS $upgrade_args -e ".[server,templates,terraform,secrets-aws,secrets-gcp,secrets-azure,secrets-hashicorp,s3fs,gcsfs,adlfs,dev,connectors-aws,connectors-gcp,connectors-azure,azureml,sagemaker,vertex]"
    
    echo "✅ ZenML installation completed"
}

install_integrations() {
    echo "🔌 Installing ZenML integrations..."

    # figure out the python version
    python_version=$(python -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")

    ignore_integrations="feast label_studio bentoml seldon pycaret skypilot_aws skypilot_gcp skypilot_azure skypilot_kubernetes skypilot_lambda pigeon prodigy argilla vllm"

    # Ignore tensorflow and deepchecks only on Python 3.12 and 3.13
    if [ "$python_version" = "3.12" ] || [ "$python_version" = "3.13" ]; then
        ignore_integrations="$ignore_integrations tensorflow deepchecks"
    fi

    # TODO: Revisit once pytorch Windows support stabilizes.
    # torch DLL loading on Windows CI is unreliable (OSError / FileNotFoundError
    # at import time). Tracked in: https://github.com/zenml-io/zenml/issues/4471
    os_name=$(python -c "import platform; print(platform.system())")
    if [ "$os_name" = "Windows" ]; then
        ignore_integrations="$ignore_integrations pytorch neural_prophet pytorch_lightning"
    fi
    
    # turn the ignore integrations into a list of --ignore-integration args
    ignore_integrations_args=""
    for integration in $ignore_integrations; do
        ignore_integrations_args="$ignore_integrations_args --ignore-integration $integration"
    done

    # install basic ZenML integrations
    zenml integration export-requirements \
        --output-file integration-requirements.txt \
        $ignore_integrations_args

    # Handle package pins based on upgrade mode
    if [ "$UPGRADE_ALL" = "yes" ]; then
        echo "🔄 Using latest versions for integration dependencies"
        # When upgrading, use minimum versions to allow latest compatible
        echo "" >> integration-requirements.txt
        echo "pyyaml>=6.0.1" >> integration-requirements.txt
        echo "pyopenssl" >> integration-requirements.txt
        echo "typing-extensions" >> integration-requirements.txt
        echo "maison<2" >> integration-requirements.txt
    else
        # Original behavior with specific pins
        echo "" >> integration-requirements.txt
        echo "pyyaml>=6.0.1" >> integration-requirements.txt
        echo "pyopenssl" >> integration-requirements.txt
        echo "typing-extensions" >> integration-requirements.txt
        echo "maison<2" >> integration-requirements.txt
    fi
    
    echo "-e .[server,templates,terraform,secrets-aws,secrets-gcp,secrets-azure,secrets-hashicorp,s3fs,gcsfs,adlfs,dev,connectors-aws,connectors-gcp,connectors-azure,azureml,sagemaker,vertex]" >> integration-requirements.txt

    # Build upgrade arguments based on UPGRADE_ALL flag
    upgrade_args=""
    if [ "$UPGRADE_ALL" = "yes" ]; then
        upgrade_args="--upgrade --force-reinstall"
        echo "🔄 Using --upgrade --force-reinstall for integration dependencies"
    fi

    uv pip install $PIP_ARGS $upgrade_args -r integration-requirements.txt
    rm integration-requirements.txt
    
    echo "✅ Integration installation completed"

    # https://github.com/Kludex/python-multipart/pull/166
    # There is an install conflict between multipart and python_multipart
    # which causes our server to fail in case both are installed. We
    # need to uninstall this library for now until the changes make it into
    # fastapi and then need to bump the fastapi version to resolve this.
    uv pip uninstall $PIP_ARGS multipart

    # `docstring_parser_fork` (required by pydoclint) ships under the same
    # `docstring_parser/` namespace as the upstream `docstring-parser` package.
    # Some integration dependencies pull in upstream `docstring-parser`, which
    # then overwrites the fork's files on disk and breaks `pydoclint` with an
    # `ImportError: cannot import name 'DocstringYields'`. Force-reinstall the
    # fork last so its files win the namespace collision.
    uv pip install $PIP_ARGS --force-reinstall --no-deps "docstring_parser_fork"
}

set -x
set -e

export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false

parse_args "$@"

# Clean and upgrade tooling packages if upgrading all
if [ "$UPGRADE_ALL" = "yes" ]; then
    echo "🚀 Upgrading all dependencies to latest versions..."
    clean_and_uninstall
    python -m pip install --upgrade --force-reinstall wheel pip uv
else
    python -m pip install --upgrade wheel pip uv
fi

install_zenml

# install integrations, if requested
if [ "$INTEGRATIONS" = yes ]; then
    install_integrations
fi

```

File: /Users/safoine/zenml-io/zenml/.github/workflows/generate-test-duration.yml
```yml
---
name: Generate test duration file
on:
  workflow_call:
  schedule:
    - cron: 0 8 * * 1  # Run every Monday at 8 am
jobs:
  generate-test-duration-file:
    name: Generate test duration file
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
    env:
      ZENML_DEBUG: 1
      ZENML_ANALYTICS_OPT_IN: false
      PYTHONIOENCODING: utf-8
      UV_HTTP_TIMEOUT: 600
          # on MAC OS, we need to set this environment variable
          # to fix problems with the fork() calls (see this thread
          # for more information: http://sealiesoftware.com/blog/archive/2017/6/5/Objective-C_and_fork_in_macOS_1013.html)
      OBJC_DISABLE_INITIALIZE_FORK_SAFETY: 'YES'
    defaults:
      run:
        shell: bash
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
        with:
          ref: develop
      - name: Setup environment
        uses: ./.github/actions/setup_environment
        with:
          python-version: '3.10'
          os: ubuntu-latest
      - name: Generate test duration file
        continue-on-error: true
            # Ubuntu integration tests run as 6 shards
        run: |
          bash scripts/test-coverage-xml.sh "" default "" "" store-durations
      - name: Check difference in .test_durations
        run: |
          git diff --quiet || echo "Changes found"
          if [ -n "$(git status --porcelain)" ]; then
            # Commit changes directly to the specified branch
            git add .test_durations
            git commit -m "Update with new changes for test duration file at $(date +'%Y%m%d-%H%M%S')"
            git push origin develop
          else
            echo "No changes in .test_durations"
          fi
      - name: Verify Python Env unaffected
        run: |-
          zenml integration list
          uv pip list
          uv pip check || true

```

File: /Users/safoine/zenml-io/zenml/.github/workflows/integration-test-fast-services.yml
```yml
---
name: Integration Tests (Fast CI)
on:
  workflow_call:
    inputs:
      os:
        description: OS
        type: string
        required: true
      python-version:
        description: Python version
        type: string
        required: true
      test_environment:
        description: The test environment
        type: string
        required: true
      enable_tmate:
        description: Enable tmate session for debugging
        type: string
        required: false
        default: never
      tmate_timeout:
        description: Timeout for tmate session (minutes)
        type: number
        required: false
        default: 30
      reruns:
        description: Pytest rerun count (0 disables)
        type: number
        required: false
        default: 3
  workflow_dispatch:
    inputs:
      os:
        description: OS
        type: choice
        options: [ubuntu-latest, macos-13, windows-latest]
        required: false
        default: ubuntu-latest
      python-version:
        description: Python version
        type: choice
        options: ['3.10', '3.11', '3.12', '3.13']
        required: false
        default: '3.11'
      test_environment:
        description: The test environment
        type: choice
        options:
          # Default ZenML deployments
          - default
          - default-docker-orchestrator
          - default-airflow-orchestrator
          # Local ZenML server deployments
          - local-server
          - local-server-docker-orchestrator
          - local-server-airflow-orchestrator
          # Local ZenML docker-compose server deployments
          - docker-server-mysql
          - docker-server-mariadb
          - docker-server-docker-orchestrator-mysql
          - docker-server-docker-orchestrator-mariadb
          - docker-server-airflow-orchestrator-mysql
          - docker-server-airflow-orchestrator-mariadb
          - github-actions-server-docker-orchestrator
        required: false
        default: default
      enable_tmate:
        description: Enable tmate session for debugging
        type: choice
        options: [no, on-failure, always, before-tests]
        required: false
        default: 'no'
      tmate_timeout:
        description: Timeout for tmate session (minutes)
        type: number
        required: false
        default: 30
      reruns:
        description: Pytest rerun count (0 disables)
        type: number
        required: false
        default: 3
jobs:
  integration-tests-fast:
    name: integration-tests-fast
    runs-on: ${{ inputs.os }}
    strategy:
      fail-fast: false
      matrix:
        shard: [1, 2, 3, 4, 5, 6]
    env:
      ZENML_DEBUG: 1
      ZENML_ANALYTICS_OPT_IN: false
      ZENML_ENABLE_RICH_TRACEBACK: false
      WHYLOGS_NO_ANALYTICS: 'True'
      PYTHONIOENCODING: utf-8
      UV_HTTP_TIMEOUT: 600
      # on MAC OS, we need to set this environment variable
      # to fix problems with the fork() calls (see this thread
      # for more information: http://sealiesoftware.com/blog/archive/2017/6/5/Objective-C_and_fork_in_macOS_1013.html)
      OBJC_DISABLE_INITIALIZE_FORK_SAFETY: 'YES'
      AWS_ACCESS_KEY_ID: ${{ secrets.AWS_US_EAST_1_ENV_ACCESS_KEY_ID }}
      AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_US_EAST_1_ENV_SECRET_ACCESS_KEY }}
      AWS_US_EAST_1_SERVER_URL: ${{ secrets.AWS_US_EAST_1_SERVER_URL }}
      AWS_US_EAST_1_SERVER_USERNAME: ${{ secrets.AWS_US_EAST_1_SERVER_USERNAME }}
      AWS_US_EAST_1_SERVER_PASSWORD: ${{ secrets.AWS_US_EAST_1_SERVER_PASSWORD }}
      GCP_US_EAST4_SERVER_URL: ${{ secrets.GCP_US_EAST4_SERVER_URL }}
      GCP_US_EAST4_SERVER_USERNAME: ${{ secrets.GCP_US_EAST4_SERVER_USERNAME }}
      GCP_US_EAST4_SERVER_PASSWORD: ${{ secrets.GCP_US_EAST4_SERVER_PASSWORD }}
      PYTEST_RERUNS: ${{ inputs.reruns }}
    if: ${{ ! startsWith(github.event.head_commit.message, 'GitBook:') }}
    defaults:
      run:
        shell: bash
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6.0.2
      - name: Restore uv cache
        uses: actions/cache@27d5ce7f107fe9357f9df03efb73ab90386fccae # v5.0.5
        with:
          path: ~/.cache/uv
          key: |
            uv-${{ runner.os }}-${{ inputs.python-version }}-${{ hashFiles('src/zenml/integrations/*/__init__.py') }}
          restore-keys: |
            uv-${{ runner.os }}-${{ inputs.python-version }}-${{ hashFiles('src/zenml/integrations/*/__init__.py') }}
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@ec61189d14ec14c8efccab744f656cffd0e33f37 # v6.1.0
        with:
          role-to-assume: ${{ secrets.AWS_US_EAST_1_ENV_ROLE_ARN }}
          aws-region: us-east-1
        if: contains(inputs.test_environment, 'aws')
      - name: Configure GCP credentials
        uses: google-github-actions/auth@7c6bc770dae815cd3e89ee6cdf493a5fab2cc093 # v3.0.0
        with:
          credentials_json: ${{ secrets.GCP_US_EAST4_ENV_CREDENTIALS }}
        if: contains(inputs.test_environment, 'gcp')
      - name: Set up gcloud SDK
        uses: google-github-actions/setup-gcloud@aa5489c8933f4cc7a4f7d45035b3b1440c9c10db # v3.0.1
        with:
          install_components: gke-gcloud-auth-plugin
        if: contains(inputs.test_environment, 'gcp')
      - name: Login to Docker Hub
        uses: docker/login-action@4907a6ddec9925e35a0a9e82d7399ccc52663121 # v4.1.0
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}
        if: github.event.pull_request.head.repo.fork == false && (contains(inputs.test_environment,
          'docker') || contains(inputs.test_environment, 'kubeflow') || contains(inputs.test_environment,
          'airflow') || contains(inputs.test_environment, 'kubernetes'))
      - name: Setup environment
        uses: ./.github/actions/setup_environment
        with:
          python-version: ${{ inputs.python-version }}
          os: ${{ inputs.os }}
      - name: Install docker-compose for non-default environments
        if: inputs.test_environment != 'default'
        run: |
          pip install uv
          # see https://github.com/docker/docker-py/issues/3256 for why we need to pin requests
          # docker-compose is deprecated and doesn't work with newer versions of docker
          uv pip install --system "pyyaml==5.3.1" "requests<2.32.0" "docker==6.1.3" docker-compose
      - name: Install Linux System Dependencies
        if: (inputs.os == 'ubuntu-latest' || inputs.os == 'arc-runner-set')
        run: sudo apt install graphviz
      - name: Install MacOS System Dependencies
        if: runner.os=='macOS'
        run: brew install graphviz
      - name: Install Windows System Dependencies
        if: runner.os=='Windows'
        run: choco install graphviz
      - name: Unbreak python in github actions
        if: runner.os=='macOS'
        # github actions overwrites brew's python. Force it to reassert itself, by
        # running in a separate step.
        # Workaround GitHub Actions Python issues
        # see https://github.com/Homebrew/homebrew-core/issues/165793#issuecomment-1989441193
        run: |
          find /usr/local/bin -lname '*/Library/Frameworks/Python.framework/*' -delete
          sudo rm -rf /Library/Frameworks/Python.framework/
          brew install --force python3 && brew unlink python3 && brew unlink python3 && brew link --overwrite python3
      - name: Install Docker and Colima on MacOS
        if: runner.os=='macOS'
        run: |
          export HOMEBREW_NO_INSTALLED_DEPENDENTS_CHECK=1
          brew update
          brew install docker colima
          brew reinstall --force qemu

          # We need to mount the /private/tmp/zenml-test/ folder because
          # this folder is also mounted in the Docker containers that are
          # started by local ZenML orchestrators.
          colima start --mount /private/tmp/zenml-test/:w

          # This is required for the Docker Python SDK to work
          sudo ln -sf $HOME/.colima/default/docker.sock /var/run/docker.sock
      - name: Install kubectl on Linux
        run: |
          curl -LO "https://dl.k8s.io/release/v1.35.0/bin/linux/amd64/kubectl"
          sudo install -o root -g 0 -m 0755 kubectl /usr/local/bin/kubectl
        if: (inputs.os == 'ubuntu-latest' || inputs.os == 'arc-runner-set')
      - name: Install kubectl on MacOS
        run: |
          curl -LO "https://dl.k8s.io/release/v1.35.0/bin/darwin/amd64/kubectl"
          sudo install -o root -g 0 -m 0755 kubectl /usr/local/bin/kubectl
        if: runner.os=='macOS'
      - name: Install K3D
        run: |
          curl -s https://raw.githubusercontent.com/rancher/k3d/main/install.sh | bash
        if: runner.os!='Windows' && contains(inputs.test_environment, 'kubeflow')
      - name: Login to Amazon ECR
        id: login-ecr
        run: |
          aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 715803424590.dkr.ecr.us-east-1.amazonaws.com
        if: contains(inputs.test_environment, 'aws')
      - name: Login to Amazon EKS
        id: login-eks
        run: |
          aws eks --region us-east-1 update-kubeconfig --name zenml-ci-cluster --alias zenml-ci-aws-us-east-1
        if: contains(inputs.test_environment, 'aws')
      - name: Login to Google ECR
        run: |
          gcloud auth configure-docker --project zenml-ci
        if: contains(inputs.test_environment, 'gcp')
      - name: Login to Google GKE
        uses: google-github-actions/get-gke-credentials@3da1e46a907576cefaa90c484278bb5b259dd395 # v3.0.0
        with:
          cluster_name: zenml-ci-cluster
          location: us-east4
          project_id: zenml-ci
        if: contains(inputs.test_environment, 'gcp')
      - name: Setup tmate session before tests
        if: ${{ inputs.enable_tmate == 'before-tests' }}
        uses: mxschmitt/action-tmate@c0afd6f790e3a5564914980036ebf83216678101 # v3.23
        timeout-minutes: ${{ inputs.tmate_timeout }}
      - name: Sharded Integration Tests (Ubuntu) - Fast CI
        # Ubuntu integration tests run as 6 shards
        if: runner.os != 'macOS' && runner.os != 'Windows'
        run: |
          bash scripts/test-coverage-xml.sh integration ${INPUTS_TEST_ENVIRONMENT} 6 ${{ matrix.shard }}
        env:
          INPUTS_TEST_ENVIRONMENT: ${{ inputs.test_environment }}
      - name: Setup tmate session after tests
        if: ${{ inputs.enable_tmate == 'always' || (inputs.enable_tmate == 'on-failure' && failure()) }}
        uses: mxschmitt/action-tmate@c0afd6f790e3a5564914980036ebf83216678101 # v3.23
        timeout-minutes: ${{ inputs.tmate_timeout }}
      - name: Verify Python Env unaffected
        run: |-
          zenml integration list
          uv pip list
          uv pip check || true
    services:
      mysql:
        image: mysql:5.7
        env:
          MYSQL_ROOT_PASSWORD: zenml
          MYSQL_DATABASE: zenml
        ports:
          - 3306:3306
        options: >-
          --health-cmd="mysqladmin ping"
          --health-interval=10s
          --health-timeout=5s
          --health-retries=3
      zenml-server:
        image: ghcr.io/${{ github.repository_owner }}/zenml-server-github-actions:${{
          github.sha }}
        credentials:
          username: ${{ github.actor }}
          password: ${{ secrets.github_token }}
        env:
          ZENML_STORE_URL: mysql://root:zenml@mysql:3306/zenml
          ZENML_SERVER_DEPLOYMENT_TYPE: docker
          ZENML_SERVER_AUTO_ACTIVATE: 'True'
          ZENML_SERVER_AUTO_CREATE_DEFAULT_USER: 'True'
        ports:
          - 8080:8080
        options: >-
          --health-cmd="curl -f http://127.0.0.1:8080/health"
          --health-interval=10s
          --health-timeout=5s
          --health-retries=3

```

File: /Users/safoine/zenml-io/zenml/src/zenml/integrations/registry.py
```py
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
"""Implementation of a registry to track ZenML integrations."""

import importlib
import os
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type

from zenml.exceptions import IntegrationError
from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.integrations.integration import Integration

logger = get_logger(__name__)


class IntegrationRegistry(object):
    """Registry to keep track of ZenML Integrations."""

    def __init__(self) -> None:
        """Initializing the integration registry."""
        self._integrations: Dict[str, Type["Integration"]] = {}
        self._initialized = False

    @property
    def integrations(self) -> Dict[str, Type["Integration"]]:
        """Method to get integrations dictionary.

        Returns:
            A dict of integration key to type of `Integration`.
        """
        self._initialize()
        return self._integrations

    @integrations.setter
    def integrations(self, i: Any) -> None:
        """Setter method for the integrations property.

        Args:
            i: Value to set the integrations property to.

        Raises:
            IntegrationError: If you try to manually set the integrations property.
        """
        raise IntegrationError(
            "Please do not manually change the integrations within the "
            "registry. If you would like to register a new integration "
            "manually, please use "
            "`integration_registry.register_integration()`."
        )

    def register_integration(
        self, key: str, type_: Type["Integration"]
    ) -> None:
        """Method to register an integration with a given name.

        Args:
            key: Name of the integration.
            type_: Type of the integration.
        """
        self._integrations[key] = type_

    def _initialize(self) -> None:
        """Method to register all integrations."""
        if self._initialized:
            return
        self._initialized = True

        # Load all submodules in the integrations module
        integrations_dir = os.path.dirname(__file__)
        for file in os.listdir(integrations_dir):
            full_path = os.path.join(integrations_dir, file)
            # Skip anything that isn't a directory
            if not os.path.isdir(full_path):
                continue
            # Skip anything that doesn't have a __init__.py file
            if not os.path.exists(os.path.join(full_path, "__init__.py")):
                continue
            # Import the module
            module_path = f"zenml.integrations.{file}"
            try:
                importlib.import_module(module_path)
            except ImportError:
                logger.exception(f"Failed to import module `{module_path}`.")
                continue

    def activate_integrations(self) -> None:
        """Best-effort eager activation of installed integrations.

        Attempts to activate each integration that passes the
        metadata-based installation check. Activation imports the
        integration's runtime modules (materializers, service connectors,
        etc.) to trigger eager registration. If an individual activation
        fails due to a broken or incomplete install (ImportError) or
        native library load failure (OSError), the error is logged and
        remaining integrations continue.

        Note: activation failure only skips early registration side
        effects. Later on-demand imports (e.g. loading stored artifacts
        or stack components) may still attempt to import the same modules
        and could fail independently.
        """
        self._initialize()
        for name, integration in self._integrations.items():
            if integration.check_installation():
                logger.debug(f"Activating integration `{name}`...")
                try:
                    integration.activate()
                # ImportError: broken/incomplete install or undeclared
                # transitive dependency despite declared requirements
                # appearing installed.
                # OSError: native library or binary/DLL load failure
                # at import time.
                except (ImportError, OSError) as e:
                    logger.exception(
                        f"Failed to activate integration `{name}`: "
                        f"{type(e).__name__}: {e}. "
                        "Skipping activation-time registration (e.g. "
                        "materializers, service connectors). Some "
                        "features may be missing from auto-discovery, "
                        "and on-demand imports of this integration "
                        "may also fail."
                    )
                    continue
                logger.debug(f"Integration `{name}` is activated.")
            else:
                logger.debug(f"Integration `{name}` could not be activated.")

    @property
    def list_integration_names(self) -> List[str]:
        """Get a list of all possible integrations.

        Returns:
            A list of all possible integrations.
        """
        self._initialize()
        return [name for name in self._integrations]

    def select_integration_requirements(
        self,
        integration_name: Optional[str] = None,
        target_os: Optional[str] = None,
    ) -> List[str]:
        """Select the requirements for a given integration or all integrations.

        Args:
            integration_name: Name of the integration to check.
            target_os: Target OS for the requirements.

        Returns:
            List of requirements for the integration.

        Raises:
            KeyError: If the integration is not found.
        """
        self._initialize()
        if integration_name:
            if integration_name in self.list_integration_names:
                return self._integrations[integration_name].get_requirements(
                    target_os=target_os
                )
            else:
                raise KeyError(
                    f"Integration {integration_name} does not exist. "
                    f"Currently the following integrations are implemented. "
                    f"{self.list_integration_names}"
                )
        else:
            return [
                requirement
                for name in self.list_integration_names
                for requirement in self._integrations[name].get_requirements(
                    target_os=target_os
                )
            ]

    def select_uninstall_requirements(
        self,
        integration_name: Optional[str] = None,
        target_os: Optional[str] = None,
    ) -> List[str]:
        """Select the uninstall requirements for a given integration or all integrations.

        Args:
            integration_name: Name of the integration to check.
            target_os: Target OS for the requirements.

        Returns:
            List of requirements for the integration uninstall.

        Raises:
            KeyError: If the integration is not found.
        """
        self._initialize()
        if integration_name:
            if integration_name in self.list_integration_names:
                return self._integrations[
                    integration_name
                ].get_uninstall_requirements(target_os=target_os)
            else:
                raise KeyError(
                    f"Integration {integration_name} does not exist. "
                    f"Currently the following integrations are implemented. "
                    f"{self.list_integration_names}"
                )
        else:
            return [
                requirement
                for name in self.list_integration_names
                for requirement in self._integrations[
                    name
                ].get_uninstall_requirements(target_os=target_os)
            ]

    def is_installed(self, integration_name: Optional[str] = None) -> bool:
        """Checks if all requirements for an integration are installed.

        Args:
            integration_name: Name of the integration to check.

        Returns:
            True if all requirements are installed, False otherwise.

        Raises:
            KeyError: If the integration is not found.
        """
        self._initialize()
        if integration_name in self.list_integration_names:
            return self._integrations[integration_name].check_installation()
        elif not integration_name:
            all_installed = [
                self._integrations[item].check_installation()
                for item in self.list_integration_names
            ]
            return all(all_installed)
        else:
            raise KeyError(
                f"Integration '{integration_name}' not found. "
                f"Currently the following integrations are available: "
                f"{self.list_integration_names}"
            )

    def get_installed_integrations(self) -> List[str]:
        """Returns list of installed integrations.

        Returns:
            List of installed integrations.
        """
        self._initialize()
        return [
            name
            for name, integration in integration_registry.integrations.items()
            if integration.check_installation()
        ]


integration_registry = IntegrationRegistry()

```

File: /Users/safoine/zenml-io/zenml/.github/actions/setup_environment/action.yml
```yml
---
name: Install ZenML
description: Install ZenML, most integrations, loads/uploads cached venv and pip download
  cache if applicable
inputs:
  cache_version:
    description: Value gets appended to the cache key and will therefore invalidate
      the cache if it changes
    required: true
  python-version:
    description: Python version
    required: true
  os:
    description: OS
    required: true
  install_integrations:
    description: Install ZenML integrations
    required: false
    default: 'yes'
runs:
  using: composite
  steps:
    - name: Set up Python
      uses: actions/setup-python@v5.3.0
      with:
        python-version: ${{ inputs.python-version }}
    - name: Delete error-causing bash
      shell: bash
      if: ${{ inputs.os == 'windows-latest' }}
      run: rm.exe "C:/WINDOWS/system32/bash.EXE"
    - name: Set path to bash for example runner
      shell: bash
      if: ${{ inputs.os == 'windows-latest' }}
      run: |
        echo "SHELL_EXECUTABLE=C:\Program Files\Git\bin\bash.exe" >> $GITHUB_ENV
    - name: Configure git (non-Windows)
      if: ${{ inputs.os != 'windows-latest' }}
      shell: bash
      run: |
        git config --global user.email "info@zenml.io"
        git config --global user.name "ZenML GmbH"
    - name: Configure git (Windows)
      if: ${{ inputs.os == 'windows-latest' }}
      shell: bash
      run: |
        "C:\Program Files\Git\bin\git.exe" config --global user.email "info@zenml.io"
        "C:\Program Files\Git\bin\git.exe" config --global user.name "ZenML
        GmbH"
    - name: Install Terraform (Windows)
      if: ${{ inputs.os == 'windows-latest' }}
      shell: bash
      run: choco install terraform -y
    - name: Install Terraform (Mac)
      if: ${{ inputs.os == 'macos-13' || inputs.os == 'macos-latest' }}
      shell: bash
      run: |
        brew tap hashicorp/tap
        brew install hashicorp/tap/terraform
    - name: Install ZenML and dependencies
      shell: bash
      run: |
        scripts/install-zenml-dev.sh --system --integrations ${{ inputs.install_integrations }}
        uv pip install --system "setuptools<82"
    - name: Check Python environment
      shell: bash
      run: |-
        zenml integration list
        uv pip list
        uv pip check || true

```

File: /Users/safoine/zenml-io/zenml/scripts/test-coverage-xml.sh
```sh
#!/usr/bin/env bash

set -e
set -x

# If only unittests are needed call
# test-coverage-xml.sh unit
# For only integration tests call
# test-coverage-xml.sh integration
# To store durations, add a fifth argument 'store-durations'
TEST_SRC="tests/"${1:-""}
TEST_ENVIRONMENT=${2:-"default"}
TEST_SPLITS=${3:-"1"}
TEST_GROUP=${4:-"1"}
STORE_DURATIONS=${5:-""}

# Control flaky test retries via environment variables.
# - PYTEST_RERUNS: non-negative integer (0 disables reruns), defaults to 3 if unset or invalid.
# - PYTEST_RERUNS_DELAY: non-negative integer delay between reruns in seconds, defaults to 5 if unset or invalid.
# Validation guards against misconfiguration in CI while allowing explicit opt-out with 0.
RERUNS_DEFAULT=3
DELAY_DEFAULT=5

if [[ -n "${PYTEST_RERUNS+x}" ]]; then
    RERUNS="$PYTEST_RERUNS"
else
    RERUNS="$RERUNS_DEFAULT"
fi
if ! [[ "$RERUNS" =~ ^[0-9]+$ ]]; then
    echo "Warning: PYTEST_RERUNS='$RERUNS' is invalid. Falling back to ${RERUNS_DEFAULT}." >&2
    RERUNS="$RERUNS_DEFAULT"
fi

if [[ -n "${PYTEST_RERUNS_DELAY+x}" ]]; then
    RERUNS_DELAY="$PYTEST_RERUNS_DELAY"
else
    RERUNS_DELAY="$DELAY_DEFAULT"
fi
if ! [[ "$RERUNS_DELAY" =~ ^[0-9]+$ ]]; then
    echo "Warning: PYTEST_RERUNS_DELAY='$RERUNS_DELAY' is invalid. Falling back to ${DELAY_DEFAULT}." >&2
    RERUNS_DELAY="$DELAY_DEFAULT"
fi

PYTEST_RERUN_ARGS=(--reruns "$RERUNS" --reruns-delay "$RERUNS_DELAY")

export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false
export EVIDENTLY_DISABLE_TELEMETRY=1

./zen-test environment provision $TEST_ENVIRONMENT

# The '-vv' flag enables pytest-clarity output when tests fail.
# Shows errors instantly in logs when test fails.
if [ -n "$1" ]; then
    if [ "$STORE_DURATIONS" == "store-durations" ]; then
        coverage run -m pytest $TEST_SRC --color=yes -vv --environment $TEST_ENVIRONMENT --no-provision --cleanup-docker --store-durations --durations-path=.test_durations "${PYTEST_RERUN_ARGS[@]}" --instafail
    else
        coverage run -m pytest $TEST_SRC --color=yes -vv --durations-path=.test_durations --splits=$TEST_SPLITS --group=$TEST_GROUP --splitting-algorithm least_duration --environment $TEST_ENVIRONMENT --no-provision --cleanup-docker "${PYTEST_RERUN_ARGS[@]}" --instafail
    fi
else
    if [ "$STORE_DURATIONS" == "store-durations" ]; then
        coverage run -m pytest tests/unit --color=yes -vv --environment $TEST_ENVIRONMENT --no-provision --store-durations --durations-path=.test_durations "${PYTEST_RERUN_ARGS[@]}" --instafail
        coverage run -m pytest tests/integration --color=yes -vv --environment $TEST_ENVIRONMENT --no-provision --cleanup-docker --store-durations --durations-path=.test_durations "${PYTEST_RERUN_ARGS[@]}" --instafail
    else
        coverage run -m pytest tests/unit --color=yes -vv --durations-path=.test_durations --splits=$TEST_SPLITS --group=$TEST_GROUP --splitting-algorithm least_duration --environment $TEST_ENVIRONMENT --no-provision "${PYTEST_RERUN_ARGS[@]}" --instafail
        coverage run -m pytest tests/integration --color=yes -vv --durations-path=.test_durations --splits=$TEST_SPLITS --group=$TEST_GROUP --splitting-algorithm least_duration --environment $TEST_ENVIRONMENT --no-provision --cleanup-docker "${PYTEST_RERUN_ARGS[@]}" --instafail
    fi
fi

./zen-test environment cleanup $TEST_ENVIRONMENT

coverage combine
coverage report --show-missing
coverage xml

```

File: /Users/safoine/zenml-io/zenml/src/zenml/integrations/integration.py
```py
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
"""Base and meta classes for ZenML integrations."""

from typing import Any, Dict, List, Optional, Tuple, Type, cast

from packaging.requirements import Requirement

from zenml.integrations.registry import integration_registry
from zenml.logger import get_logger
from zenml.stack.flavor import Flavor
from zenml.utils.package_utils import get_dependencies, requirement_installed

logger = get_logger(__name__)


class IntegrationMeta(type):
    """Metaclass responsible for registering different Integration subclasses."""

    def __new__(
        mcs, name: str, bases: Tuple[Type[Any], ...], dct: Dict[str, Any]
    ) -> "IntegrationMeta":
        """Hook into creation of an Integration class.

        Args:
            name: The name of the class being created.
            bases: The base classes of the class being created.
            dct: The dictionary of attributes of the class being created.

        Returns:
            The newly created class.
        """
        cls = cast(Type["Integration"], super().__new__(mcs, name, bases, dct))
        if name != "Integration":
            integration_registry.register_integration(cls.NAME, cls)
        return cls


class Integration(metaclass=IntegrationMeta):
    """Base class for integration in ZenML."""

    NAME = "base_integration"

    REQUIREMENTS: List[str] = []
    APT_PACKAGES: List[str] = []
    REQUIREMENTS_IGNORED_ON_UNINSTALL: List[str] = []

    @classmethod
    def check_installation(cls) -> bool:
        """Method to check whether the required packages are installed.

        Returns:
            True if all required packages are installed, False otherwise.
        """
        for requirement in cls.get_requirements():
            parsed_requirement = Requirement(requirement)

            if not requirement_installed(parsed_requirement):
                logger.debug(
                    "Requirement '%s' for integration '%s' is not installed "
                    "or installed with the wrong version.",
                    requirement,
                    cls.NAME,
                )
                return False

            dependencies = get_dependencies(parsed_requirement)

            for dependency in dependencies:
                if not requirement_installed(dependency):
                    logger.debug(
                        "Requirement '%s' for integration '%s' is not "
                        "installed or installed with the wrong version.",
                        dependency,
                        cls.NAME,
                    )
                    return False

        logger.debug(
            f"Integration '{cls.NAME}' is installed correctly with "
            f"requirements {cls.get_requirements()}."
        )
        return True

    @classmethod
    def get_requirements(
        cls,
        target_os: Optional[str] = None,
        python_version: Optional[str] = None,
    ) -> List[str]:
        """Method to get the requirements for the integration.

        Args:
            target_os: The target operating system to get the requirements for.
            python_version: The Python version to use for the requirements.

        Returns:
            A list of requirements.
        """
        return cls.REQUIREMENTS

    @classmethod
    def get_uninstall_requirements(
        cls, target_os: Optional[str] = None
    ) -> List[str]:
        """Method to get the uninstall requirements for the integration.

        Args:
            target_os: The target operating system to get the requirements for.

        Returns:
            A list of requirements.
        """
        ret = []
        for each in cls.get_requirements(target_os=target_os):
            is_ignored = False
            for ignored in cls.REQUIREMENTS_IGNORED_ON_UNINSTALL:
                if each.startswith(ignored):
                    is_ignored = True
                    break
            if not is_ignored:
                ret.append(each)
        return ret

    @classmethod
    def activate(cls) -> None:
        """Abstract method to activate the integration."""

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Abstract method to declare new stack component flavors.

        Returns:
            A list of new stack component flavors.
        """
        return []

```
</file_contents>
<git_diff>
diff --git a/.github/CLAUDE.md b/.github/CLAUDE.md
index fe50c7c9b9..e68eb46387 100644
--- a/.github/CLAUDE.md
+++ b/.github/CLAUDE.md
@@ -151,6 +151,15 @@ key: uv-${{ runner.os }}-${{ inputs.python-version }}-${{ hashFiles('src/zenml/i
 
 Cache invalidates when integrations change.
 
+Offload CI uses separate cache families:
+- `offload-uv-v1`: runner-side uv downloads/build artifacts for offload driver setup and pytest collection dependencies.
+- `offload-image-v2`: Modal image metadata. This intentionally excludes runtime fields such as CPU, memory, `max_parallel`, commands used after sandbox creation, and test filters.
+- `offload-junit-v2`: offload JUnit duration seeds keyed by lane and test-selection inputs.
+
+Restored offload JUnit XML is only a duration seed. It must not be treated as current test output unless `.ci/offload/junit.xml` is newer than `.ci/offload/run-start.marker`. Stale restored XML should be quarantined as `junit.stale.xml`.
+
+The `offload-cache-warm.yml` workflow refreshes offload image and JUnit duration caches weekly or manually. It is a maintenance workflow, not a branch-protection signal.
+
 ## Key Supporting Files
 
 | File | Purpose |


diff --git a/tests/harness/cfg/deployments.yaml b/tests/harness/cfg/deployments.yaml
index db631674fa..3f04eb0c36 100644
--- a/tests/harness/cfg/deployments.yaml
+++ b/tests/harness/cfg/deployments.yaml
@@ -122,3 +122,14 @@ deployments:
       url: http://127.0.0.1:8080/
       username: default
       password: ''
+  - name: modal-mysql-server
+    description: >-
+      Modal-hosted ZenML server backed by MySQL for CI integration tests.
+    server: external
+    database: external
+    capabilities:
+      server: true
+    config:
+      url: '{{MODAL_CI_SERVER_URL}}'
+      username: '{{MODAL_CI_SERVER_USERNAME}}'
+      password: '{{MODAL_CI_SERVER_PASSWORD}}'


diff --git a/.github/workflows/unit-test.yml b/.github/workflows/unit-test.yml
index c06441125d..8f29b78a40 100644
--- a/.github/workflows/unit-test.yml
+++ b/.github/workflows/unit-test.yml
@@ -103,7 +103,7 @@ jobs:
         uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
         with:
           repository: ${{ github.repository }}
-          ref: ${{ github.event.pull_request.head.sha }}
+          ref: ${{ inputs.git-ref || github.event.pull_request.head.sha || github.sha }}
           fetch-depth: 0  # Fetch all history for all branches and tags
       - name: Restore uv cache
         uses: actions/cache@27d5ce7f107fe9357f9df03efb73ab90386fccae  # v5.0.5


diff --git a/.github/workflows/ci-fast.yml b/.github/workflows/ci-fast.yml
index 19d8669f26..1b8963e014 100644
--- a/.github/workflows/ci-fast.yml
+++ b/.github/workflows/ci-fast.yml
@@ -3,26 +3,13 @@ name: ci-fast
 on:
   workflow_dispatch:
   workflow_call:
+  merge_group:
   push:
-    branches: [main]
-    paths-ignore:
-      - docs/**
-      - '*'
-      - '!pyproject.toml'
-      - '**.md'
-      - .github/workflows/claude.yml
-      - .claude/**
+    branches: [develop]
   pull_request:
     types: [opened, synchronize, ready_for_review]
-    paths-ignore:
-      - docs/**
-      - '*'
-      - '!pyproject.toml'
-      - '**.md'
-      - .github/workflows/claude.yml
-      - .claude/**
 concurrency:
-  # New commit on branch cancels running workflows of the same branch
+  # New commit on branch cancels running workflows of the same branch.
   group: ${{ github.workflow }}-${{ github.ref }}
   cancel-in-progress: true
 jobs:
@@ -31,8 +18,8 @@ jobs:
     env:
       ZENML_ANALYTICS_OPT_IN: false
       ZENML_DEBUG: true
-    # if team member commented, not a draft, on a PR, using /fulltest
-    if: github.event.pull_request.draft == false || github.event_name == 'workflow_dispatch'
+    if: github.event_name != 'pull_request' || github.event.pull_request.draft ==
+      false
     steps:
       - name: Checkout code
         uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
@@ -45,7 +32,8 @@ jobs:
       - name: Test migrations across versions
         run: bash scripts/test-migrations.sh sqlite random
   spellcheck:
-    if: github.event.pull_request.draft == false
+    if: github.event_name != 'pull_request' || github.event.pull_request.draft ==
+      false
     runs-on: ubuntu-latest
     steps:
       - name: Checkout code
@@ -56,7 +44,8 @@ jobs:
           files: .
           config: ./.typos.toml
   api-docs-test:
-    if: github.event.pull_request.draft == false
+    if: github.event_name != 'pull_request' || github.event.pull_request.draft ==
+      false
     runs-on: ubuntu-latest
     steps:
       - name: Checkout code
@@ -68,17 +57,16 @@ jobs:
       - name: Test API docs buildable
         run: bash scripts/generate-docs.sh -v DUMMY -c
   update-templates-to-examples:
-    # this doesn't work on forked repositories (i.e. outside contributors)
-    # so we disable template updates for those PRs / branches
-    if: github.event.pull_request.head.repo.full_name == 'zenml-io/zenml' && github.event.pull_request.draft
-      == false
+    if: github.event_name == 'pull_request' && github.event.pull_request.head.repo.full_name
+      == 'zenml-io/zenml' && github.event.pull_request.draft == false
     uses: ./.github/workflows/update-templates-to-examples.yml
     with:
       python-version: '3.11'
       os: ubuntu-latest
     secrets: inherit
   linting:
-    if: github.event.pull_request.draft == false
+    if: github.event_name != 'pull_request' || github.event.pull_request.draft ==
+      false
     strategy:
       matrix:
         os: [ubuntu-latest]
@@ -89,39 +77,53 @@ jobs:
       python-version: ${{ matrix.python-version }}
       os: ${{ matrix.os }}
     secrets: inherit
-  ubuntu-setup-and-unit-test:
-    needs: linting
-    if: github.event.pull_request.draft == false
-    strategy:
-      matrix:
-        # IMPORTANT: Since we are using the combination of `arc-runner-set`
-        # and `3.10` in our `ci-fast` workflow, this combination has been
-        # excluded from the `ci-slow` workflow. If you change the configuration
-        # here, please adjust the configuration of `ci-slow` accordingly.
-        os: [ubuntu-latest]
-        python-version: ['3.11']
-      fail-fast: false
-    uses: ./.github/workflows/unit-test.yml
+  linux-fast-offload:
+    if: github.event_name != 'pull_request' || github.event.pull_request.draft ==
+      false
+    uses: ./.github/workflows/linux-fast-offload.yml
     with:
-      python-version: ${{ matrix.python-version }}
-      os: ${{ matrix.os }}
+      backend: modal
+      python-version: '3.13'
+      use-offload: true
     secrets: inherit
-  ubuntu-latest-integration-test:
-    needs: [linting]
-    if: github.event.pull_request.draft == false
-    strategy:
-      matrix:
-        # IMPORTANT: Since we are using the combination of `arc-runner-set`
-        # and `3.10` in our `ci-fast` workflow, this combination has been
-        # excluded from the `ci-slow` workflow. If you change the configuration
-        # here, please adjust the configuration of `ci-slow` accordingly.
-        os: [ubuntu-latest]
-        python-version: ['3.11']
-        test_environment: [default, docker-server-docker-orchestrator-mysql]
-      fail-fast: false
-    uses: ./.github/workflows/integration-test-fast.yml
+  linux-fast-offload-modal-mysql:
+    if: github.event_name != 'pull_request' || (github.event.pull_request.draft ==
+      false && github.event.pull_request.head.repo.full_name == github.repository)
+    uses: ./.github/workflows/linux-fast-offload.yml
     with:
-      os: ${{ matrix.os }}
-      python-version: ${{ matrix.python-version }}
-      test_environment: ${{ matrix.test_environment }}
+      backend: modal
+      python-version: '3.13'
+      use-offload: true
+      test_environment: modal-server-mysql
     secrets: inherit
+  ci-fast-required:
+    runs-on: ubuntu-latest
+    needs:
+      - sqlite-db-migration-testing-random
+      - spellcheck
+      - api-docs-test
+      - update-templates-to-examples
+      - linting
+      - linux-fast-offload
+      - linux-fast-offload-modal-mysql
+    if: always()
+    steps:
+      - name: Verify required fast CI jobs
+        env:
+          NEEDS_CONTEXT: ${{ toJSON(needs) }}
+        run: |-
+          python - <<'PY'
+          import json
+          import os
+          import sys
+          failed = []
+          for name, data in json.loads(os.environ["NEEDS_CONTEXT"]).items():
+              result = data["result"]
+              if result not in {"success", "skipped"}:
+                  failed.append(f"{name}: {result}")
+          if failed:
+              print("Fast CI dependencies failed:")
+              print("\n".join(failed))
+              sys.exit(1)
+          print("All fast CI dependencies passed or were skipped by design.")
+          PY


diff --git a/tests/harness/cfg/environments.yaml b/tests/harness/cfg/environments.yaml
index a323871587..8f2cfaab27 100644
--- a/tests/harness/cfg/environments.yaml
+++ b/tests/harness/cfg/environments.yaml
@@ -132,6 +132,18 @@ environments:
       - mlflow-local-deployer
     capabilities:
       synchronized: true
+  - name: remote-mysql-modal
+    description: >-
+      Modal-hosted ZenML server with local orchestrator and all local
+      components, using a MySQL database.
+    deployment: modal-mysql-server
+    requirements:
+      - data-validators
+      - mlflow-local-tracker
+      - mlflow-local-registry
+      - mlflow-local-deployer
+    capabilities:
+      synchronized: true
   - name: docker-server-docker-orchestrator-mysql
     description: >-
       Server docker-compose deployment with docker orchestrator and all local


diff --git a/tests/integration/functional/cli/test_model.py b/tests/integration/functional/cli/test_model.py
index 48c67b298a..0643cb271a 100644
--- a/tests/integration/functional/cli/test_model.py
+++ b/tests/integration/functional/cli/test_model.py
@@ -15,7 +15,6 @@
 
 from uuid import uuid4
 
-import pytest
 from click.testing import CliRunner
 
 from tests.integration.functional.cli.conftest import NAME, PREFIX
@@ -23,7 +22,7 @@ from zenml.cli.cli import cli
 from zenml.client import Client
 
 
-def test_model_list(clean_client_with_models: "Client"):
+def test_model_list(clean_client: "Client"):
     """Test that zenml model list does not fail."""
     runner = CliRunner(mix_stderr=False)
     list_command = cli.commands["model"].commands["list"]
@@ -31,7 +30,7 @@ def test_model_list(clean_client_with_models: "Client"):
     assert result.exit_code == 0, result.stderr
 
 
-def test_model_create_short_names(clean_client_with_models: "Client"):
+def test_model_create_short_names(clean_client: "Client"):
     """Test that zenml model create does not fail with short names."""
     runner = CliRunner(mix_stderr=False)
     create_command = cli.commands["model"].commands["register"]
@@ -67,7 +66,7 @@ def test_model_create_short_names(clean_client_with_models: "Client"):
     )
     assert result.exit_code == 0, result.stderr
 
-    model = clean_client_with_models.get_model(model_name)
+    model = clean_client.get_model(model_name)
     assert model.name == model_name
     assert model.license == "a"
     assert model.description == "b"
@@ -80,7 +79,7 @@ def test_model_create_short_names(clean_client_with_models: "Client"):
     assert {t.name for t in model.tags} == {"i", "j", "k"}
 
 
-def test_model_create_full_names(clean_client_with_models: "Client"):
+def test_model_create_full_names(clean_client: "Client"):
     """Test that zenml model create does not fail with full names."""
     runner = CliRunner(mix_stderr=False)
     create_command = cli.commands["model"].commands["register"]
@@ -116,7 +115,7 @@ def test_model_create_full_names(clean_client_with_models: "Client"):
     )
     assert result.exit_code == 0, result.stderr
 
-    model = clean_client_with_models.get_model(model_name)
+    model = clean_client.get_model(model_name)
     assert model.name == model_name
     assert model.license == "a"
     assert model.description == "b"
@@ -129,7 +128,7 @@ def test_model_create_full_names(clean_client_with_models: "Client"):
     assert {t.name for t in model.tags} == {"i", "j", "k"}
 
 
-def test_model_create_only_required(clean_client_with_models: "Client"):
+def test_model_create_only_required(clean_client: "Client"):
     """Test that zenml model create does not fail."""
     runner = CliRunner(mix_stderr=False)
     create_command = cli.commands["model"].commands["register"]
@@ -140,7 +139,7 @@ def test_model_create_only_required(clean_client_with_models: "Client"):
     )
     assert result.exit_code == 0, result.stderr
 
-    model = clean_client_with_models.get_model(model_name)
+    model = clean_client.get_model(model_name)
     assert model.name == model_name
     assert model.license is None
     assert model.description is None
@@ -153,8 +152,9 @@ def test_model_create_only_required(clean_client_with_models: "Client"):
     assert len(model.tags) == 0
 
 
-def test_model_update(clean_client_with_models: "Client"):
+def test_model_update(clean_client: "Client"):
     """Test that zenml model update does not fail."""
+    clean_client.create_model(name=NAME)
     runner = CliRunner(mix_stderr=False)
     update_command = cli.commands["model"].commands["update"]
     result = runner.invoke(
@@ -163,7 +163,7 @@ def test_model_update(clean_client_with_models: "Client"):
     )
     assert result.exit_code == 0, result.stderr
 
-    model = clean_client_with_models.get_model(NAME)
+    model = clean_client.get_model(NAME)
     assert model.trade_offs == "foo"
     assert {t.name for t in model.tags} == {"a"}
     assert model.description is None
@@ -174,16 +174,14 @@ def test_model_update(clean_client_with_models: "Client"):
     )
     assert result.exit_code == 0, result.stderr
 
-    model = clean_client_with_models.get_model(NAME)
+    model = clean_client.get_model(NAME)
     assert model.trade_offs == "foo"
     assert {t.name for t in model.tags} == {"b"}
     assert model.description == "bar"
     assert not model.save_models_to_registry
 
 
-def test_model_create_without_required_fails(
-    clean_client_with_models: "Client",
-):
+def test_model_create_without_required_fails(clean_client: "Client"):
     """Test that zenml model create fails."""
     runner = CliRunner(mix_stderr=False)
     create_command = cli.commands["model"].commands["register"]
@@ -193,7 +191,7 @@ def test_model_create_without_required_fails(
     assert result.exit_code != 0, result.stderr
 
 
-def test_model_delete_found(clean_client_with_models: "Client"):
+def test_model_delete_found(clean_client: "Client"):
     """Test that zenml model delete does not fail."""
     runner = CliRunner(mix_stderr=False)
     name = PREFIX + str(uuid4())
@@ -210,7 +208,7 @@ def test_model_delete_found(clean_client_with_models: "Client"):
     assert result.exit_code == 0, result.stderr
 
 
-def test_model_delete_not_found(clean_client_with_models: "Client"):
+def test_model_delete_not_found(clean_client: "Client"):
     """Test that zenml model delete fail."""
     runner = CliRunner(mix_stderr=False)
     name = PREFIX + str(uuid4())
@@ -222,23 +220,24 @@ def test_model_delete_not_found(clean_client_with_models: "Client"):
     assert result.exit_code != 0, result.stderr
 
 
-def test_model_version_list(clean_client_with_models: "Client"):
+def test_model_version_list(clean_client: "Client"):
     """Test that zenml model version list does not fail."""
+    clean_client.create_model(name=NAME)
     runner = CliRunner(mix_stderr=False)
     list_command = cli.commands["model"].commands["version"].commands["list"]
     result = runner.invoke(list_command, args=[f"--model={NAME}"])
     assert result.exit_code == 0, result.stderr
 
 
-def test_model_version_delete_found(clean_client_with_models: "Client"):
+def test_model_version_delete_found(clean_client: "Client"):
     """Test that zenml model version delete does not fail."""
     runner = CliRunner(mix_stderr=False)
     model_name = PREFIX + str(uuid4())
     model_version_name = PREFIX + str(uuid4())
-    model = clean_client_with_models.create_model(
+    model = clean_client.create_model(
         name=model_name,
     )
-    clean_client_with_models.create_model_version(
+    clean_client.create_model_version(
         name=model_version_name,
         model_name_or_id=model.id,
     )
@@ -252,12 +251,12 @@ def test_model_version_delete_found(clean_client_with_models: "Client"):
     assert result.exit_code == 0, result.stderr
 
 
-def test_model_version_delete_not_found(clean_client_with_models: "Client"):
+def test_model_version_delete_not_found(clean_client: "Client"):
     """Test that zenml model version delete fail."""
     runner = CliRunner(mix_stderr=False)
     model_name = PREFIX + str(uuid4())
     model_version_name = PREFIX + str(uuid4())
-    clean_client_with_models.create_model(
+    clean_client.create_model(
         name=model_name,
     )
     delete_command = (
@@ -270,25 +269,27 @@ def test_model_version_delete_not_found(clean_client_with_models: "Client"):
     assert result.exit_code != 0, result.stderr
 
 
-@pytest.mark.parametrize(
-    "command",
-    ("data_artifacts", "deployment_artifacts", "model_artifacts", "runs"),
-)
-def test_model_version_links_list(
-    command: str, clean_client_with_models: "Client"
-):
-    """Test that zenml model version artifacts list fails."""
+def test_model_version_links_list(clean_client_with_models: "Client"):
+    """Test that zenml model version link lists do not fail."""
     runner = CliRunner(mix_stderr=False)
-    list_command = cli.commands["model"].commands[command]
-    result = runner.invoke(
-        list_command,
-        args=[NAME],
-    )
-    assert result.exit_code == 0, result.stderr
-
-
-def test_model_version_update(clean_client_with_models: "Client"):
+    for command in (
+        "data_artifacts",
+        "deployment_artifacts",
+        "model_artifacts",
+        "runs",
+    ):
+        list_command = cli.commands["model"].commands[command]
+        result = runner.invoke(
+            list_command,
+            args=[NAME],
+        )
+        assert result.exit_code == 0, result.stderr
+
+
+def test_model_version_update(clean_client: "Client"):
     """Test that zenml model version stage update pass."""
+    clean_client.create_model(name=NAME)
+    clean_client.create_model_version(model_name_or_id=NAME)
     runner = CliRunner(mix_stderr=False)
     update_command = (
         cli.commands["model"].commands["version"].commands["update"]


diff --git a/.github/workflows/vscode-tutorial-pipelines-test.yml b/.github/workflows/vscode-tutorial-pipelines-test.yml
index 086358df67..9f4a0d8b74 100644
--- a/.github/workflows/vscode-tutorial-pipelines-test.yml
+++ b/.github/workflows/vscode-tutorial-pipelines-test.yml
@@ -5,6 +5,12 @@
 name: VSCode Tutorial Pipelines Test
 on:
   workflow_call:
+    inputs:
+      git-ref:
+        description: Git branch or ref
+        type: string
+        required: false
+        default: ''
   workflow_dispatch:
     inputs:
       python-version:
@@ -37,6 +43,7 @@ jobs:
       - name: Checkout ZenML code
         uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
         with:
+          ref: ${{ inputs.git-ref || github.event.pull_request.head.sha || github.sha }}
           fetch-depth: 0
       - name: Set up Python 3.12
         uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405  # v6.2.0


diff --git a/.github/workflows/linting.yml b/.github/workflows/linting.yml
index c29dc24897..b1d3995734 100644
--- a/.github/workflows/linting.yml
+++ b/.github/workflows/linting.yml
@@ -92,7 +92,7 @@ jobs:
         uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
         with:
           repository: ${{ github.repository }}
-          ref: ${{ github.event.pull_request.head.sha }}
+          ref: ${{ inputs.git-ref || github.event.pull_request.head.sha || github.sha }}
           fetch-depth: 0  # Fetch all history for all branches and tags
       - name: Restore uv cache
         uses: actions/cache@27d5ce7f107fe9357f9df03efb73ab90386fccae  # v5.0.5


diff --git a/.github/workflows/release.yml b/.github/workflows/release.yml
index 2146ef2f41..d18476a5ec 100644
--- a/.github/workflows/release.yml
+++ b/.github/workflows/release.yml
@@ -3,8 +3,23 @@ name: Release Package & Docker Image
 on:
   push:
     tags: ['*']
+permissions:
+  contents: read
+  checks: read
 jobs:
+  verify-known-good:
+    runs-on: ubuntu-latest
+    steps:
+      - name: Checkout code
+        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
+        with:
+          fetch-depth: 0
+      - name: Verify slow CI qualification (warn-only)
+        env:
+          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
+        run: python scripts/check_known_good.py --warn-only
   setup-and-test:
+    needs: verify-known-good
     uses: ./.github/workflows/unit-test.yml
     with:
       os: ubuntu-latest
@@ -13,6 +28,7 @@ jobs:
   # We only run the `latest` DB migration test here, as the other previous steps in the release flow already
   # test full migrations.
   mysql-db-migration-testing:
+    needs: verify-known-good
     runs-on: ubuntu-latest
     env:
       ZENML_ANALYTICS_OPT_IN: false
@@ -34,6 +50,7 @@ jobs:
       - name: Test migrations across versions
         run: bash scripts/test-migrations.sh mysql latest
   sqlite-db-migration-testing:
+    needs: verify-known-good
     runs-on: ubuntu-latest
     env:
       ZENML_ANALYTICS_OPT_IN: false
@@ -50,6 +67,7 @@ jobs:
       - name: Test migrations across versions
         run: bash scripts/test-migrations.sh sqlite latest
   mariadb-db-migration-testing:
+    needs: verify-known-good
     runs-on: ubuntu-latest
     env:
       ZENML_ANALYTICS_OPT_IN: false
@@ -160,12 +178,15 @@ jobs:
         run: echo "VERSION=${GITHUB_REF/refs\/tags\//}" >> "$GITHUB_OUTPUT"
       - name: Create a tag on ZenML Cloud plugins repo
         uses: actions/github-script@ed597411d8f924073f98dfc5c65a23a2325f34cd  # v8.0.0
+        env:
+          RELEASE_VERSION: ${{ steps.get_version.outputs.VERSION }}
+          CLOUD_PLUGINS_SHA: ${{ steps.get_sha.outputs.sha }}
         with:
           github-token: ${{ secrets.CLOUD_PLUGINS_REPO_PAT }}
           script: |-
             await github.rest.git.createRef({
               owner: 'zenml-io',
               repo: 'zenml-cloud-plugins',
-              ref: 'refs/tags/${{ steps.get_version.outputs.VERSION }}',
-              sha: '${{ steps.get_sha.outputs.sha }}'
+              ref: `refs/tags/${process.env.RELEASE_VERSION}`,
+              sha: process.env.CLOUD_PLUGINS_SHA
             })


diff --git a/tests/harness/deployment/base.py b/tests/harness/deployment/base.py
index 15aace081a..8172c22084 100644
--- a/tests/harness/deployment/base.py
+++ b/tests/harness/deployment/base.py
@@ -378,7 +378,7 @@ class BaseTestDeployment(ABC):
         store_config = self.get_store_config()
         if store_config is not None:
             store_type = BaseZenStore.get_store_type(store_config.url)
-            store_config_dict = store_config.model_dump()
+            store_config_dict = store_config.dict()
             if store_type == StoreType.REST:
                 if custom_username is not None:
                     store_config_dict["username"] = custom_username


diff --git a/CONTRIBUTING.md b/CONTRIBUTING.md
index 790a65b41a..bd3ca02b39 100644
--- a/CONTRIBUTING.md
+++ b/CONTRIBUTING.md
@@ -202,6 +202,10 @@ Please note that it is good practice to run the above commands before submitting
 any Pull Request: The CI GitHub Action
 will run it anyway, so you might as well catch the errors locally!
 
+The CI captain rotation lives in `.github/ci-captains.yml`. The weekly captain
+is the first responder for `develop-red` incidents opened by nightly slow CI and
+backs up the authors identified in the suspect commit range.
+
 ### 🚨 Reporting a Vulnerability
 
 Please refer to [our security / reporting instructions](./SECURITY.md) for


diff --git a/.github/workflows/integration-test-slow.yml b/.github/workflows/integration-test-slow.yml
index 791db19579..25e5ee2d79 100644
--- a/.github/workflows/integration-test-slow.yml
+++ b/.github/workflows/integration-test-slow.yml
@@ -30,6 +30,11 @@ on:
         type: number
         required: false
         default: 3
+      git-ref:
+        description: Git branch or ref
+        type: string
+        required: false
+        default: ''
   workflow_dispatch:
     inputs:
       os:
@@ -174,6 +179,8 @@ jobs:
           'docker') || contains(inputs.test_environment, 'kubeflow') || contains(inputs.test_environment,
           'airflow') || contains(inputs.test_environment, 'kubernetes'))
       - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
+        with:
+          ref: ${{ inputs.git-ref || github.event.pull_request.head.sha || github.sha }}
       - name: Restore uv cache
         uses: actions/cache@27d5ce7f107fe9357f9df03efb73ab90386fccae  # v5.0.5
         with:


diff --git a/.github/workflows/integration-test-fast.yml b/.github/workflows/integration-test-fast.yml
index c83a28f0bb..39db955f46 100644
--- a/.github/workflows/integration-test-fast.yml
+++ b/.github/workflows/integration-test-fast.yml
@@ -30,6 +30,21 @@ on:
         type: number
         required: false
         default: 3
+      ci_tier:
+        description: CI tier name
+        type: string
+        required: false
+        default: fast
+      modal_ci_server_url:
+        description: Per-run Modal ZenML server URL
+        type: string
+        required: false
+        default: ''
+      modal_ci_server_username:
+        description: Per-run Modal ZenML server username
+        type: string
+        required: false
+        default: ''
   workflow_dispatch:
     inputs:
       os:
@@ -64,6 +79,7 @@ on:
           - docker-server-airflow-orchestrator-mysql
           - docker-server-airflow-orchestrator-mariadb
           - github-actions-server-docker-orchestrator
+          - remote-mysql-modal
         required: false
         default: default
       enable_tmate:
@@ -109,8 +125,11 @@ jobs:
       GCP_US_EAST4_SERVER_URL: ${{ secrets.GCP_US_EAST4_SERVER_URL }}
       GCP_US_EAST4_SERVER_USERNAME: ${{ secrets.GCP_US_EAST4_SERVER_USERNAME }}
       GCP_US_EAST4_SERVER_PASSWORD: ${{ secrets.GCP_US_EAST4_SERVER_PASSWORD }}
+      MODAL_CI_SERVER_URL: ${{ inputs.modal_ci_server_url }}
+      MODAL_CI_SERVER_USERNAME: ${{ inputs.modal_ci_server_username }}
       PYTEST_RERUNS: ${{ inputs.reruns }}
-    if: ${{ ! startsWith(github.event.head_commit.message, 'GitBook:') }}
+      ZENML_CI_TIER: ${{ inputs.ci_tier }}
+    if: ${{ ! startsWith(github.event.head_commit.message, 'GitBook:') && (inputs.test_environment != 'remote-mysql-modal' || github.event_name != 'pull_request' || github.event.pull_request.head.repo.full_name == github.repository) }}
     defaults:
       run:
         shell: bash
@@ -205,8 +224,14 @@ jobs:
         with:
           python-version: ${{ inputs.python-version }}
           os: ${{ inputs.os }}
-      - name: Install docker-compose for non-default environments
-        if: inputs.test_environment != 'default'
+      - name: Validate Modal connection details
+        if: inputs.test_environment == 'remote-mysql-modal' && vars.ZENML_CI_MODAL_DISABLED
+          != 'true'
+        run: |
+          test -n "$MODAL_CI_SERVER_URL"
+          test -n "$MODAL_CI_SERVER_USERNAME"
+      - name: Install docker-compose for local Docker environments
+        if: inputs.test_environment != 'default' && inputs.test_environment != 'remote-mysql-modal'
         run: |
           pip install uv
           # see https://github.com/docker/docker-py/issues/3256 for why we need to pin requests
@@ -250,7 +275,9 @@ jobs:
         run: |
           curl -L -o kubectl "https://dl.k8s.io/release/v1.35.0/bin/linux/amd64/kubectl"
           sudo install -o root -g 0 -m 0755 kubectl /usr/local/bin/kubectl
-        if: (inputs.os == 'ubuntu-latest' || inputs.os == 'arc-runner-set')
+        if: (inputs.os == 'ubuntu-latest' || inputs.os == 'arc-runner-set') && (contains(inputs.test_environment,
+          'kubeflow') || contains(inputs.test_environment, 'kubernetes') || contains(inputs.test_environment,
+          'aws') || contains(inputs.test_environment, 'gcp'))
       - name: Install kubectl on MacOS
         run: |
           curl -LO "https://dl.k8s.io/release/v1.35.0/bin/darwin/amd64/kubectl"
@@ -289,14 +316,24 @@ jobs:
         # Ubuntu integration tests run as 6 shards
         if: runner.os != 'macOS' && runner.os != 'Windows'
         run: |
+          if [ "${INPUTS_TEST_ENVIRONMENT}" = "remote-mysql-modal" ]; then
+            export MODAL_CI_SERVER_PASSWORD=$(python - <<'PY'
+          from scripts.ci_modal_mysql_sandbox import derive_server_password
+          print(derive_server_password())
+          PY
+          )
+          fi
           bash scripts/test-coverage-xml.sh integration ${INPUTS_TEST_ENVIRONMENT} 6 ${{ matrix.shard }}
         env:
-          INPUTS_TEST_ENVIRONMENT: ${{ inputs.test_environment }}
+          INPUTS_TEST_ENVIRONMENT: ${{ inputs.test_environment == 'remote-mysql-modal' && vars.ZENML_CI_MODAL_DISABLED == 'true' && 'docker-server-mysql' || inputs.test_environment }}
+          MODAL_TOKEN_SECRET: ${{ secrets.MODAL_TOKEN_SECRET }}
+          ZENML_CI_CHECKOUT_REF: ${{ github.event.pull_request.head.sha || github.sha }}
       - name: Setup tmate session after tests
         if: ${{ inputs.enable_tmate == 'always' || (inputs.enable_tmate == 'on-failure' && failure()) }}
         uses: mxschmitt/action-tmate@c0afd6f790e3a5564914980036ebf83216678101  # v3.23
         timeout-minutes: ${{ inputs.tmate_timeout }}
       - name: Verify Python Env unaffected
+        if: inputs.test_environment != 'remote-mysql-modal'
         run: |-
           zenml integration list
           uv pip list


diff --git a/.github/workflows/ci-slow.yml b/.github/workflows/ci-slow.yml
index b4ba6feef7..ea2e5e8cdb 100644
--- a/.github/workflows/ci-slow.yml
+++ b/.github/workflows/ci-slow.yml
@@ -3,24 +3,6 @@ name: ci-slow
 on:
   workflow_dispatch:
   workflow_call:
-  push:
-    branches: [main]
-    paths-ignore:
-      - docs/**
-      - '*'
-      - '!pyproject.toml'
-      - '**.md'
-      - .github/workflows/claude.yml
-      - .claude/**
-  pull_request:
-    types: [opened, synchronize, ready_for_review]
-    paths-ignore:
-      - docs/**
-      - '*'
-      - '!pyproject.toml'
-      - '**.md'
-      - .github/workflows/claude.yml
-      - .claude/**
 concurrency:
   # New commit on branch cancels running workflows of the same branch
   group: ${{ github.workflow }}-${{ github.ref }}


diff --git a/.github/zizmor.yml b/.github/zizmor.yml
index 37f7b192fa..bd9ae79da9 100644
--- a/.github/zizmor.yml
+++ b/.github/zizmor.yml
@@ -52,8 +52,6 @@ rules:
   # (step outputs within same workflow are trusted)
   template-injection:
     ignore:
-      - release.yml:169  # VERSION from step output
-      - release.yml:170  # sha from step output
       - snack-it.yml:352  # issue_number from step output
       - snack-it.yml:353  # continuation of above
       - snack-it.yml:354  # project_added from step output
@@ -96,3 +94,7 @@ rules:
       - weekly-agent-pipelines-test.yml
       - nightly_build.yml
       - release.yml
+      - ci-medium.yml
+      - ci-slow-develop.yml
+      - slow-ci-on-pr.yml
+      - offload-cache-warm.yml


diff --git a/.github/workflows/base-package-functionality.yml b/.github/workflows/base-package-functionality.yml
index 8a70b46eef..8e80315d10 100644
--- a/.github/workflows/base-package-functionality.yml
+++ b/.github/workflows/base-package-functionality.yml
@@ -53,7 +53,7 @@ jobs:
         uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2
         with:
           repository: ${{ github.repository }}
-          ref: ${{ inputs.git-ref || github.event.pull_request.head.sha }}
+          ref: ${{ inputs.git-ref || github.event.pull_request.head.sha || github.sha }}
       - name: Set up Python
         uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405  # v6.2.0
         with:


diff --git a/scripts/test-migrations.sh b/scripts/test-migrations.sh
index 9a0bf2bbdb..38c7f6a0b1 100755
--- a/scripts/test-migrations.sh
+++ b/scripts/test-migrations.sh
@@ -2,6 +2,8 @@
 
 DB="sqlite"
 DB_STARTUP_DELAY=30 # Time in seconds to wait for the database container to start
+RANDOM_MIGRATION_COUNT="${RANDOM_MIGRATION_COUNT:-3}"
+RANDOM_MIGRATION_SEED="${RANDOM_MIGRATION_SEED:-${GITHUB_RUN_ID:-}}"
 
 export ZENML_ANALYTICS_OPT_IN=false
 export ZENML_DEBUG=true
@@ -325,6 +327,18 @@ echo "Testing database: $DB"
 echo "Testing versions: ${VERSIONS[@]}"
 echo "Migration type: $MIGRATION_TYPE"
 
+if [ "$MIGRATION_TYPE" == "random" ]; then
+    if ! [[ "$RANDOM_MIGRATION_COUNT" =~ ^[0-9]+$ ]] || [ "$RANDOM_MIGRATION_COUNT" -lt 1 ]; then
+        echo "RANDOM_MIGRATION_COUNT must be a positive integer" >&2
+        exit 1
+    fi
+    if [ -n "$RANDOM_MIGRATION_SEED" ]; then
+        RANDOM="$RANDOM_MIGRATION_SEED"
+        echo "Random migration seed: $RANDOM_MIGRATION_SEED"
+    fi
+    echo "Random migration count: $RANDOM_MIGRATION_COUNT"
+fi
+
 # Start completely fresh
 rm -rf "$ZENML_CONFIG_PATH"
 
@@ -366,7 +380,7 @@ else
 
         # Randomly select versions for random migrations
         MIGRATION_VERSIONS=()
-        while [ ${#MIGRATION_VERSIONS[@]} -lt 3 ]; do
+        while [ ${#MIGRATION_VERSIONS[@]} -lt "$RANDOM_MIGRATION_COUNT" ]; do
             VERSION=${VERSIONS[$RANDOM % ${#VERSIONS[@]}]}
             if [[ ! " ${MIGRATION_VERSIONS[@]} " =~ " $VERSION " ]]; then
                 MIGRATION_VERSIONS+=("$VERSION")


diff --git a/tests/integration/examples/utils.py b/tests/integration/examples/utils.py
index bb858dc73f..5adc68d2f1 100644
--- a/tests/integration/examples/utils.py
+++ b/tests/integration/examples/utils.py
@@ -1,3 +1,5 @@
+"""Utilities for running integration example tests."""
+
 #  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
 #
 #  Licensed under the Apache License, Version 2.0 (the "License");
@@ -106,6 +108,7 @@ class IntegrationTestExample:
 
 
 def copy_example_files(example_dir: str, dst_dir: str) -> None:
+    """Copy example files into a temporary test repository."""
     for item in os.listdir(example_dir):
         if item == ".zen":
             # don't copy any existing ZenML repository
@@ -221,7 +224,7 @@ def wait_and_validate_pipeline_run(
     older_than: Optional[datetime] = None,
     start_timeout: int = DEFAULT_PIPELINE_RUN_START_TIMEOUT,
     finish_timeout: int = DEFAULT_PIPELINE_RUN_FINISH_TIMEOUT,
-    poll_period: int = 10,
+    poll_period: int = 1,
 ) -> List[PipelineRunResponse]:
     """A basic example validation function.
 
@@ -240,7 +243,8 @@ def wait_and_validate_pipeline_run(
         finish_timeout: The timeout in seconds to wait for a single pipeline run
             to finish.
         poll_period: The period in seconds to wait between polling the pipeline
-            run status.
+            run status. Keep this low: local examples often finish between
+            polling intervals, so a long default adds pure idle time.
 
     Returns:
         A list of pipeline runs that were validated.

</git_diff>
<meta prompt 1 = "[Review]">
You are reviewing code changes with git diffs included in the prompt. The git diff shows what changed; the file contents show full context. Use both.

**Review Criteria:**

1. **Correctness & Safety**:
	- Do the changes achieve their intended purpose without regressions?
	- Are edge cases and error paths handled?
	- Any security vulnerabilities, race conditions, or resource leaks?
	- Any breaking changes to APIs or contracts?

2. **Design & Complexity**:
	- Do changes increase coupling or reduce separation of concerns?
	- Is new complexity justified, or can the same result be achieved more simply?
	- Are there DRY violations — duplicated logic that should be extracted?
	- Do abstractions sit at the right level (not too early, not too late)?

3. **Intentionality**:
	- Does every change have a clear purpose? Flag accidental modifications or dead code.
	- Are the changes minimal and focused, or is scope creeping in?

**Severity Levels — be disciplined about classification:**
- **P0 (Must fix)**: Bugs, data loss, security holes, crashes — things that break correctness.
- **P1 (Should fix)**: Design issues that will compound — poor separation of concerns, growing complexity, DRY violations, missing error handling for reachable paths.
- **P2 (Consider)**: Style, naming, minor refactoring opportunities, test coverage gaps.

Most findings should be P1 or P2. Reserve P0 for genuinely broken behavior.

**Output Format:**
1. One-paragraph summary of what the changes accomplish.
2. Findings grouped by severity (P0 → P1 → P2), each with: file reference, what's wrong, and a concrete suggestion. Omit empty severity groups.
3. If no issues found at a severity level, skip it — don't pad the review.
</meta prompt 1>
<user_instructions>
<taskname="CI Simplification Review"/>
<task>
Code review the current PR branch `feature/new-ci-architecture` against `develop`, with a narrow focus on simplifying and reducing the large CI/offload implementation while preserving intended behavior, outputs, the sub-10-minute fast-test goal, fallback semantics, and integrity of the new CI architecture. Prioritize concrete, actionable findings: redundant files/scripts, duplicated shell/Python logic, workflow overlap, helper abstractions that can be merged, tests that can be parameterized or reduced safely, and places where existing ZenML utilities should be reused. Treat this as a review: findings first, ordered by severity/impact, with file/line references where possible.
</task>

<architecture>
- Git diff snapshot: `_git_data/.../MAP.txt` records 64 changed files (+10,572/-130) against `develop`, with per-file patch artifacts selected for all modified files. Added files are selected as full source/config; `uv.lock` is intentionally not selected because it is ~188k tokens, but MAP records it as a large generated addition (+5,433 lines).
- Top-level CI orchestration lives in `.github/workflows/ci-fast.yml`, `ci-medium.yml`, `ci-slow-develop.yml`, `ci-slow.yml`, `slow-ci-on-pr.yml`, and related workflow-call files. New architecture separates fast/medium/slow lanes, adds develop health/qualification checks, and adds Modal/offload warming workflows.
- Offload lane implementation centers on `.github/workflows/linux-fast-offload.yml`, which performs eligibility checks, cache key computation, offload binary/cache setup, optional Modal MySQL sandbox provisioning, offload execution, result classification, artifact/timing emission, cache save, and fallback signaling.
- New Python helper scripts under `scripts/ci/` cover cache keys, JUnit parsing/normalization/summaries, offload result classification, timing manifests, integration requirement export, and mixed-environment pytest routing. Other new CI scripts under `scripts/` cover Modal sandbox lifecycle, health gates, qualification publishing, quarantine validation, workspace safety audit, matrix hashing, and known-good checks.
- Existing CI/test utilities selected for comparison include `.github/actions/setup_environment/action.yml`, `scripts/test-coverage-xml.sh`, `scripts/install-zenml-dev.sh`, `scripts/run-ci-checks.sh`, and related existing workflows such as `generate-test-duration.yml`, `integration-test-fast-services.yml`, and `integration-test-slow-services.yml`.
- Test harness changes add/adjust environments and deployments for Modal/remote MySQL, introduce `tests/integration/conftest.py`, and add unit tests for the new CI scripts under `tests/unit/scripts/ci/`.
- Integration requirement generation uses `src/zenml/cli/integration.py`, `src/zenml/integrations/registry.py`, and `src/zenml/integrations/integration.py`; those are selected to evaluate whether the new export helper duplicates existing CLI/API behavior.
</architecture>

<selected_context>
_git_data/repos/zenml-2aefb64b/2026-05-08/1045/MAP.txt: Full diff map, changed file tree, commit graph, per-file patch paths, and explicit note that `uv.lock` is a huge added generated file.
_git_data/.../diff/per-file/*.patch: Patches for modified files, including changed workflows, docs/config, test harness files, integration helpers, and changed tests. These show old-vs-new context for modifications.
.github/workflows/ci-fast.yml: Modified fast CI entrypoint; now delegates differently and is key to sub-10-minute target.
.github/workflows/ci-medium.yml: New medium CI workflow with lint/unit/integration/remote MySQL Modal jobs and rollup behavior.
.github/workflows/ci-slow-develop.yml: New develop slow qualification workflow, health/qualification publishing, and slow test orchestration.
.github/workflows/ci-slow.yml: Existing slow workflow after PR changes; compare with new `ci-slow-develop.yml` and `slow-ci-on-pr.yml` for overlap.
.github/workflows/linux-fast-offload.yml: New large offload workflow; primary simplification target, contains substantial inline shell and repeated setup/cache/classification logic.
.github/workflows/integration-test-fast.yml and integration-test-slow.yml: Existing workflow-call test lanes modified to support remote Modal MySQL and CI tiers.
.github/workflows/integration-test-fast-services.yml and integration-test-slow-services.yml: Existing service-based integration workflows for overlap/reuse comparison.
.github/workflows/base-package-functionality.yml, linting.yml, release.yml, unit-test.yml, vscode-tutorial-pipelines-test.yml: Existing workflows touched by the PR; patches selected for exact modifications.
.github/workflows/develop-health-gate.yml, modal-ci-image-warm.yml, offload-cache-warm.yml, slow-ci-on-pr.yml, validate-quarantine.yml, validate-workspace-safety.yml: New small workflow wrappers around new scripts/offload infrastructure.
.github/actions/setup_environment/action.yml: Existing composite environment setup reused by many workflows; compare against setup duplicated in offload workflow.
.github/ci-phase-c-rollout.md, ci-captains.yml, quarantined-tests.yml, workspace-safety-baseline.txt, zizmor.yml, CLAUDE.md: CI governance/config/doc additions; `workspace-safety-baseline.txt` is large and may be simplification target.
Dockerfile.ci, Dockerfile.ci.dockerignore, offload.toml, offload-modal-server-mysql.toml: New offload image/build/config inputs used by cache keys and workflow execution.
scripts/ci/classify_offload_result.py: Classifies offload results as success/test failure/infra failure; uses JUnit summary helper and emits GitHub outputs.
scripts/ci/compute_offload_cache_keys.py: Hashes pyproject/uv lock/offload configs/Dockerfile/integration files into uv/image/JUnit cache keys.
scripts/ci/emit_timing_manifest.py: Builds offload timing/artifact manifest from environment/workflow phase data.
scripts/ci/export_offload_integration_requirements.py: Exports integration requirements using integration registry, with ignore/supplement lists.
scripts/ci/normalize_offload_junit.py, print_junit_failures.py, print_junit_summary.py: JUnit manipulation/reporting helpers; review for consolidation.
scripts/ci/run_mixed_environment_pytest.py: Routes unit/integration/other test node IDs to different environments and merges JUnit reports.
scripts/ci_modal_mysql_sandbox.py: Modal sandbox lifecycle for remote MySQL server; used by medium workflow, fast integration workflow, and offload workflow.
scripts/audit_integration_workspace_safety.py, validate_quarantine.py, check_known_good.py, ci_matrix_hash.py, develop_health_gate.py, publish_ci_qualification.py: New supporting CI policy/health scripts.
scripts/test-coverage-xml.sh: Existing pytest coverage/splitting/duration runner; important for avoiding duplication in `run_mixed_environment_pytest.py` and workflow shell.
scripts/install-zenml-dev.sh: Existing dev/integration install logic; compare with Dockerfile/offload setup/export requirements.
pyproject.toml: Dependency groups, pytest config, lint config; selected instead of huge `uv.lock`.
src/zenml/cli/integration.py, src/zenml/integrations/registry.py, src/zenml/integrations/integration.py: Existing integration requirement export/list/install APIs used or duplicated by new offload requirement script.
tests/harness/cfg/deployments.yaml, environments.yaml, tests/harness/deployment/base.py: Harness deployment/environment definitions changed for Modal/remote MySQL.
tests/integration/conftest.py, tests/integration/examples/utils.py, tests/integration/functional/cli/test_model.py: Integration test fixture/behavior changes connected to remote Modal MySQL and global state handling.
tests/unit/scripts/ci/*: Unit tests for new CI helper scripts; review for duplicated fixtures/cases and adequate behavior coverage after any simplification recommendation.
CONTRIBUTING.md and scripts/test-migrations.sh: Smaller modified files included for completeness because patches touch CI/test behavior.
</selected_context>

<relationships>
- `ci-fast.yml` / `ci-medium.yml` / `slow-ci-on-pr.yml` / `ci-slow-develop.yml` -> workflow-call test lanes and offload workflows -> rollup/health gates.
- `linux-fast-offload.yml` -> `scripts/ci/compute_offload_cache_keys.py` -> `offload*.toml`, `Dockerfile.ci*`, `pyproject.toml`, `uv.lock` (omitted), integration registry files.
- `linux-fast-offload.yml` -> `scripts/ci_modal_mysql_sandbox.py` for `modal-server-mysql` lane -> derives password also used by `integration-test-fast.yml` and `run_mixed_environment_pytest.py` remote environment routing.
- `linux-fast-offload.yml` -> `scripts/ci/classify_offload_result.py` -> `scripts/ci/print_junit_summary.py` -> `scripts/ci/print_junit_failures.py`; same JUnit domain overlaps with `normalize_offload_junit.py` and `run_mixed_environment_pytest.py` merge logic.
- `scripts/ci/export_offload_integration_requirements.py` -> `integration_registry.select_integration_requirements()` and existing CLI `zenml integration export-requirements`; compare ignore/supplement behavior with `scripts/install-zenml-dev.sh`.
- Existing test execution path: workflows -> `.github/actions/setup_environment/action.yml` -> `scripts/test-coverage-xml.sh` -> `pytest` with `pytest-split`, `.test_durations`, `zen-test environment provision/cleanup`.
- New remote Modal MySQL path: `tests/harness/cfg/environments.yaml` + `deployments.yaml` + `scripts/ci_modal_mysql_sandbox.py` + selected integration workflow changes.
- Health gate path: `ci-slow-develop.yml` -> `scripts/publish_ci_qualification.py` and `scripts/ci_matrix_hash.py`; `develop-health-gate.yml` -> `scripts/develop_health_gate.py`; `check_known_good.py` also shares `ci_matrix_hash.py`.
</relationships>

<review_focus>
- Look for consolidation opportunities among small `scripts/ci` JUnit helpers and GitHub-output patterns.
- Look for shell/Python duplication between `linux-fast-offload.yml`, `integration-test-fast.yml`, `ci-medium.yml`, and existing setup/test scripts.
- Look for workflow overlap between `ci-slow.yml`, `ci-slow-develop.yml`, `slow-ci-on-pr.yml`, and existing integration service workflows.
- Look for whether `workspace-safety-baseline.txt`, quarantine/config files, or large generated artifacts can be generated/validated differently without losing behavior.
- Check whether new tests assert behavior at the right level or duplicate implementation details in a way that would block simplification.
- Preserve offload fallback semantics: infra failure should fall back appropriately; real test failures must remain failures; JUnit cache freshness/currentness must not become ambiguous.
</review_focus>

<ambiguities>
- `uv.lock` is not selected due the token budget; MAP shows it is an added 5,433-line generated file. Review dependency intent from `pyproject.toml` and treat the lockfile size as a noted PR-size contributor, but do not make line-specific claims about its contents.
- Added files are selected as full source/config rather than duplicate per-file patches; modified files have per-file patches selected so old-vs-new behavior is visible.
</ambiguities>
</user_instructions>
