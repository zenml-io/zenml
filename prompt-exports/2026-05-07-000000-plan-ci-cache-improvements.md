<file_map>
/Users/safoine/zenml-io/zenml
├── .github
│   ├── actions
│   │   └── setup_environment
│   │       └── action.yml *
│   ├── workflows
│   │   ├── ci-fast.yml *
│   │   ├── ci-medium.yml *
│   │   ├── generate-test-duration.yml *
│   │   ├── integration-test-fast-services.yml *
│   │   ├── integration-test-fast.yml *
│   │   ├── linux-fast-offload.yml *
│   │   ├── modal-ci-image-warm.yml *
│   │   └── unit-test.yml *
│   ├── ISSUE_TEMPLATE
│   ├── blocks
│   ├── CLAUDE.md *
│   └── ci-phase-c-rollout.md *
├── scripts
│   ├── ci
│   │   ├── classify_offload_result.py * +
│   │   ├── emit_timing_manifest.py * +
│   │   ├── modal_sandbox_requirements.txt *
│   │   ├── print_junit_failures.py * +
│   │   └── print_junit_summary.py * +
│   ├── ci_modal_mysql_sandbox.py * +
│   ├── install-zenml-dev.sh *
│   └── test-coverage-xml.sh *
├── tests
│   ├── unit
│   │   ├── scripts
│   │   │   └── ci
│   │   │       ├── test_classify_offload_result.py * +
│   │   │       ├── test_emit_timing_manifest.py * +
│   │   │       ├── test_offload_config.py * +
│   │   │       └── test_print_junit_summary.py * +
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
│   ├── harness
│   │   ├── cfg
│   │   ├── cli
│   │   ├── deployment
│   │   └── model
│   ├── integration
│   │   ├── examples
│   │   │   ├── bentoml
│   │   │   │   ├── inference_samples
│   │   │   │   ├── pipelines
│   │   │   │   └── steps
│   │   │   ├── deepchecks
│   │   │   │   ├── pipelines
│   │   │   │   └── steps
│   │   │   ├── discord
│   │   │   │   ├── pipelines
│   │   │   │   └── steps
│   │   │   ├── evidently
│   │   │   │   ├── pipelines
│   │   │   │   │   └── text_report_test_pipeline
│   │   │   │   └── steps
│   │   │   │       ├── data_loader
│   │   │   │       ├── data_splitter
│   │   │   │       ├── text_data_analyzer
│   │   │   │       ├── text_data_report
│   │   │   │       └── text_data_test
│   │   │   ├── facets
│   │   │   │   ├── pipelines
│   │   │   │   │   └── facets_pipeline
│   │   │   │   └── steps
│   │   │   │       └── importer
│   │   │   ├── great_expectations
│   │   │   │   ├── pipelines
│   │   │   │   └── steps
│   │   │   ├── huggingface
│   │   │   │   ├── pipelines
│   │   │   │   │   ├── deployment_pipelines
│   │   │   │   │   ├── sequence_classifier_pipeline
│   │   │   │   │   └── token_classifier_pipeline
│   │   │   │   └── steps
│   │   │   │       ├── data_importer
│   │   │   │       ├── evaluation
│   │   │   │       ├── load_tokenizer
│   │   │   │       ├── prediction_service_loader
│   │   │   │       ├── predictor
│   │   │   │       ├── tokenization
│   │   │   │       └── training
│   │   │   ├── lightgbm
│   │   │   │   ├── pipelines
│   │   │   │   │   └── lgbm_pipeline
│   │   │   │   └── steps
│   │   │   │       ├── data_loader
│   │   │   │       ├── predictor
│   │   │   │       └── trainer
│   │   │   ├── mlflow
│   │   │   │   ├── pipelines
│   │   │   │   │   ├── deployment_pipelines
│   │   │   │   │   ├── registry_pipelines
│   │   │   │   │   └── tracking_pipeline
│   │   │   │   └── steps
│   │   │   ├── neural_prophet
│   │   │   │   ├── data
│   │   │   │   ├── pipelines
│   │   │   │   │   └── neural_prophet_pipeline
│   │   │   │   └── steps
│   │   │   │       ├── data_loader
│   │   │   │       ├── predictor
│   │   │   │       └── trainer
│   │   │   ├── pytorch
│   │   │   │   ├── pipelines
│   │   │   │   └── steps
│   │   │   ├── scipy
│   │   │   │   ├── pipelines
│   │   │   │   │   └── training_pipeline
│   │   │   │   └── steps
│   │   │   │       ├── loader
│   │   │   │       ├── predictor
│   │   │   │       ├── trainer
│   │   │   │       └── vectorizer
│   │   │   ├── seldon
│   │   │   │   ├── custom_predict
│   │   │   │   ├── pipelines
│   │   │   │   └── steps
│   │   │   │       ├── common
│   │   │   │       ├── pytorch
│   │   │   │       ├── sklearn
│   │   │   │       └── tensorflow
│   │   │   ├── sklearn
│   │   │   │   ├── pipelines
│   │   │   │   └── steps
│   │   │   ├── slack
│   │   │   │   ├── pipelines
│   │   │   │   └── steps
│   │   │   ├── tensorflow
│   │   │   │   ├── pipelines
│   │   │   │   └── steps
│   │   │   ├── whylogs
│   │   │   │   ├── pipelines
│   │   │   │   │   └── profiling_pipeline
│   │   │   │   └── steps
│   │   │   │       ├── loader
│   │   │   │       ├── profiler
│   │   │   │       └── splitter
│   │   │   └── xgboost
│   │   │       ├── pipelines
│   │   │       │   └── training_pipeline
│   │   │       └── steps
│   │   │           ├── loader
│   │   │           ├── predictor
│   │   │           └── trainer
│   │   ├── functional
│   │   │   ├── artifacts
│   │   │   ├── cli
│   │   │   ├── deployers
│   │   │   │   └── server
│   │   │   ├── materializers
│   │   │   ├── model
│   │   │   ├── models
│   │   │   ├── pipelines
│   │   │   ├── steps
│   │   │   ├── triggers
│   │   │   ├── utils
│   │   │   ├── zen_server
│   │   │   │   ├── api
│   │   │   │   └── pipeline_execution
│   │   │   └── zen_stores
│   │   └── integrations
│   │       ├── airflow
│   │       │   └── orchestrators
│   │       ├── aws
│   │       │   ├── deployers
│   │       │   └── orchestrators
│   │       ├── azure
│   │       │   └── artifact_stores
│   │       ├── deepchecks
│   │       │   ├── data_validators
│   │       │   └── materializers
│   │       ├── evidently
│   │       │   └── data_validators
│   │       ├── facets
│   │       │   └── materializers
│   │       ├── gcp
│   │       │   ├── artifact_stores
│   │       │   ├── experiment_trackers
│   │       │   ├── image_builders
│   │       │   └── orchestrators
│   │       ├── gitlab
│   │       │   └── code_repositories
│   │       ├── great_expectations
│   │       │   └── materializers
│   │       ├── huggingface
│   │       │   ├── materializers
│   │       │   └── steps
│   │       │       ├── eval_dataset
│   │       │       └── trn_dataset
│   │       ├── hyperai
│   │       │   └── orchestrators
│   │       ├── kaniko
│   │       │   └── image_builders
│   │       ├── kubeflow
│   │       │   └── orchestrators
│   │       ├── kubernetes
│   │       │   ├── orchestrators
│   │       │   └── step_operators
│   │       ├── label_studio
│   │       │   └── label_config_generators
│   │       ├── langchain
│   │       │   └── materializers
│   │       ├── lightgbm
│   │       │   └── materializers
│   │       ├── llama_index
│   │       │   └── materializers
│   │       ├── mlflow
│   │       │   └── experiment_trackers
│   │       ├── mlx
│   │       ├── modal
│   │       │   └── step_operators
│   │       ├── neptune
│   │       │   └── experiment_tracker
│   │       ├── neural_prophet
│   │       │   └── materializers
│   │       ├── numpy
│   │       ├── pandas
│   │       ├── pillow
│   │       │   └── materializers
│   │       ├── polars
│   │       │   └── materializers
│   │       ├── pytorch
│   │       │   └── materializers
│   │       ├── runai
│   │       ├── s3
│   │       │   └── artifact_stores
│   │       ├── scipy
│   │       │   └── materializers
│   │       ├── sklearn
│   │       │   └── materializers
│   │       ├── skypilot
│   │       ├── tensorflow
│   │       │   └── materializers
│   │       ├── whylogs
│   │       │   └── materializers
│   │       └── xgboost
│   │           └── materializers
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
│   │   │   │   └── assets
│   │   │   ├── oss-api
│   │   │   │   └── oss-api
│   │   │   ├── oss-api-docs
│   │   │   │   └── v1
│   │   │   │       ├── artifact-versions
│   │   │   │       ├── model-versions
│   │   │   │       ├── models
│   │   │   │       ├── pipelines
│   │   │   │       ├── run-templates
│   │   │   │       ├── runs
│   │   │   │       ├── service-accounts
│   │   │   │       │   └── api-keys
│   │   │   │       ├── service-connectors
│   │   │   │       ├── steps
│   │   │   │       └── users
│   │   │   ├── pro-api
│   │   │   │   └── pro-api
│   │   │   └── pro-api-docs
│   │   │       └── api-reference
│   │   │           ├── auth
│   │   │           ├── devices
│   │   │           ├── organizations
│   │   │           │   └── validation
│   │   │           ├── rbac
│   │   │           ├── roles
│   │   │           ├── server
│   │   │           ├── teams
│   │   │           ├── tenants
│   │   │           └── users
│   │   ├── component-guide
│   │   │   ├── .gitbook
│   │   │   │   └── assets
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
│   │   │   │   └── connector-types
│   │   │   └── step-operators
│   │   ├── getting-started
│   │   │   ├── deploying-zenml
│   │   │   └── zenml-pro
│   │   │       ├── .gitbook
│   │   │       │   └── assets
│   │   │       └── scripts
│   │   ├── how-to
│   │   │   ├── artifacts
│   │   │   ├── code-repositories
│   │   │   ├── containerization
│   │   │   ├── contribute-to-zenml
│   │   │   ├── dashboard
│   │   │   ├── deployment
│   │   │   ├── environment-variables
│   │   │   ├── infrastructure-deployment
│   │   │   │   ├── infrastructure-as-code
│   │   │   │   └── stack-deployment
│   │   │   ├── manage-zenml-server
│   │   │   │   ├── connecting-to-zenml
│   │   │   │   └── migration-guide
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
│   │   │       └── assets
│   │   └── user-guide
│   │       ├── .gitbook
│   │       │   └── assets
│   │       ├── best-practices
│   │       ├── llmops-guide
│   │       │   ├── evaluation
│   │       │   ├── finetuning-embeddings
│   │       │   ├── finetuning-llms
│   │       │   ├── rag-with-zenml
│   │       │   └── reranking
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
├── src
│   ├── zenml
│   │   ├── alerter
│   │   ├── analytics
│   │   ├── annotators
│   │   ├── artifact_stores
│   │   ├── artifacts
│   │   ├── cli
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
│   │   │       ├── dashboard
│   │   │       │   └── assets
│   │   │       └── fastapi
│   │   ├── dispatcher
│   │   ├── entrypoints
│   │   ├── execution
│   │   │   ├── pipeline
│   │   │   │   └── dynamic
│   │   │   └── step
│   │   ├── experiment_trackers
│   │   ├── feature_stores
│   │   ├── hooks
│   │   ├── image_builders
│   │   ├── integrations
│   │   │   ├── airflow
│   │   │   │   ├── flavors
│   │   │   │   └── orchestrators
│   │   │   ├── argilla
│   │   │   │   ├── annotators
│   │   │   │   └── flavors
│   │   │   ├── aws
│   │   │   │   ├── container_registries
│   │   │   │   ├── deployers
│   │   │   │   ├── flavors
│   │   │   │   ├── image_builders
│   │   │   │   ├── orchestrators
│   │   │   │   ├── service_connectors
│   │   │   │   └── step_operators
│   │   │   ├── azure
│   │   │   │   ├── artifact_stores
│   │   │   │   ├── flavors
│   │   │   │   ├── orchestrators
│   │   │   │   ├── service_connectors
│   │   │   │   └── step_operators
│   │   │   ├── bentoml
│   │   │   │   ├── flavors
│   │   │   │   ├── materializers
│   │   │   │   ├── model_deployers
│   │   │   │   ├── services
│   │   │   │   └── steps
│   │   │   ├── comet
│   │   │   │   ├── experiment_trackers
│   │   │   │   └── flavors
│   │   │   ├── databricks
│   │   │   │   ├── flavors
│   │   │   │   ├── model_deployers
│   │   │   │   ├── orchestrators
│   │   │   │   ├── services
│   │   │   │   └── utils
│   │   │   ├── deepchecks
│   │   │   │   ├── data_validators
│   │   │   │   ├── flavors
│   │   │   │   ├── materializers
│   │   │   │   └── steps
│   │   │   ├── discord
│   │   │   │   ├── alerters
│   │   │   │   ├── flavors
│   │   │   │   └── steps
│   │   │   ├── evidently
│   │   │   │   ├── data_validators
│   │   │   │   ├── flavors
│   │   │   │   └── steps
│   │   │   ├── facets
│   │   │   │   ├── materializers
│   │   │   │   └── steps
│   │   │   ├── feast
│   │   │   │   ├── feature_stores
│   │   │   │   └── flavors
│   │   │   ├── gcp
│   │   │   │   ├── artifact_stores
│   │   │   │   ├── deployers
│   │   │   │   ├── experiment_trackers
│   │   │   │   ├── flavors
│   │   │   │   ├── image_builders
│   │   │   │   ├── orchestrators
│   │   │   │   ├── service_connectors
│   │   │   │   └── step_operators
│   │   │   ├── github
│   │   │   │   └── code_repositories
│   │   │   ├── gitlab
│   │   │   │   └── code_repositories
│   │   │   ├── great_expectations
│   │   │   │   ├── data_validators
│   │   │   │   ├── flavors
│   │   │   │   ├── materializers
│   │   │   │   └── steps
│   │   │   ├── huggingface
│   │   │   │   ├── deployers
│   │   │   │   ├── flavors
│   │   │   │   ├── materializers
│   │   │   │   ├── model_deployers
│   │   │   │   ├── services
│   │   │   │   └── steps
│   │   │   ├── hyperai
│   │   │   │   ├── flavors
│   │   │   │   ├── orchestrators
│   │   │   │   └── service_connectors
│   │   │   ├── jax
│   │   │   ├── kaniko
│   │   │   │   ├── flavors
│   │   │   │   └── image_builders
│   │   │   ├── kubeflow
│   │   │   │   ├── flavors
│   │   │   │   └── orchestrators
│   │   │   ├── kubernetes
│   │   │   │   ├── deployers
│   │   │   │   ├── flavors
│   │   │   │   ├── orchestrators
│   │   │   │   ├── service_connectors
│   │   │   │   ├── step_operators
│   │   │   │   └── templates
│   │   │   │       └── kubernetes
│   │   │   ├── label_studio
│   │   │   │   ├── annotators
│   │   │   │   ├── flavors
│   │   │   │   ├── label_config_generators
│   │   │   │   └── steps
│   │   │   ├── langchain
│   │   │   │   └── materializers
│   │   │   ├── lightgbm
│   │   │   │   └── materializers
│   │   │   ├── lightning
│   │   │   │   ├── flavors
│   │   │   │   └── orchestrators
│   │   │   ├── llama_index
│   │   │   │   └── materializers
│   │   │   ├── mlflow
│   │   │   │   ├── experiment_trackers
│   │   │   │   ├── flavors
│   │   │   │   ├── model_deployers
│   │   │   │   ├── model_registries
│   │   │   │   ├── services
│   │   │   │   └── steps
│   │   │   ├── mlx
│   │   │   ├── modal
│   │   │   │   ├── flavors
│   │   │   │   └── step_operators
│   │   │   ├── neptune
│   │   │   │   ├── experiment_trackers
│   │   │   │   └── flavors
│   │   │   ├── neural_prophet
│   │   │   │   └── materializers
│   │   │   ├── numpy
│   │   │   │   └── materializers
│   │   │   ├── openai
│   │   │   │   └── hooks
│   │   │   ├── pandas
│   │   │   │   └── materializers
│   │   │   ├── pigeon
│   │   │   │   ├── annotators
│   │   │   │   └── flavors
│   │   │   ├── pillow
│   │   │   │   └── materializers
│   │   │   ├── polars
│   │   │   │   └── materializers
│   │   │   ├── prodigy
│   │   │   │   ├── annotators
│   │   │   │   └── flavors
│   │   │   ├── pycaret
│   │   │   │   └── materializers
│   │   │   ├── pytorch
│   │   │   │   └── materializers
│   │   │   ├── pytorch_lightning
│   │   │   │   └── materializers
│   │   │   ├── runai
│   │   │   │   ├── client
│   │   │   │   ├── flavors
│   │   │   │   └── step_operators
│   │   │   ├── s3
│   │   │   │   ├── artifact_stores
│   │   │   │   └── flavors
│   │   │   ├── scipy
│   │   │   │   └── materializers
│   │   │   ├── seldon
│   │   │   │   ├── custom_deployer
│   │   │   │   ├── flavors
│   │   │   │   ├── model_deployers
│   │   │   │   ├── secret_schemas
│   │   │   │   ├── services
│   │   │   │   └── steps
│   │   │   ├── sklearn
│   │   │   │   └── materializers
│   │   │   ├── skypilot
│   │   │   │   ├── flavors
│   │   │   │   └── orchestrators
│   │   │   ├── skypilot_aws
│   │   │   │   ├── flavors
│   │   │   │   └── orchestrators
│   │   │   ├── skypilot_azure
│   │   │   │   ├── flavors
│   │   │   │   └── orchestrators
│   │   │   ├── skypilot_gcp
│   │   │   │   ├── flavors
│   │   │   │   └── orchestrators
│   │   │   ├── skypilot_kubernetes
│   │   │   │   ├── flavors
│   │   │   │   └── orchestrators
│   │   │   ├── skypilot_lambda
│   │   │   │   ├── flavors
│   │   │   │   └── orchestrators
│   │   │   ├── slack
│   │   │   │   ├── alerters
│   │   │   │   ├── flavors
│   │   │   │   └── steps
│   │   │   ├── spark
│   │   │   │   ├── flavors
│   │   │   │   ├── materializers
│   │   │   │   └── step_operators
│   │   │   ├── tekton
│   │   │   │   ├── flavors
│   │   │   │   └── orchestrators
│   │   │   ├── tensorboard
│   │   │   │   ├── services
│   │   │   │   └── visualizers
│   │   │   ├── tensorflow
│   │   │   │   └── materializers
│   │   │   ├── vllm
│   │   │   │   ├── flavors
│   │   │   │   ├── model_deployers
│   │   │   │   └── services
│   │   │   ├── whylogs
│   │   │   │   ├── data_validators
│   │   │   │   ├── flavors
│   │   │   │   ├── materializers
│   │   │   │   ├── secret_schemas
│   │   │   │   └── steps
│   │   │   └── xgboost
│   │   │       └── materializers
│   │   ├── io
│   │   ├── log_stores
│   │   │   ├── artifact
│   │   │   ├── datadog
│   │   │   └── otel
│   │   ├── login
│   │   │   └── pro
│   │   │       ├── organization
│   │   │       └── workspace
│   │   ├── materializers
│   │   ├── metadata
│   │   ├── model
│   │   ├── model_deployers
│   │   ├── model_registries
│   │   ├── models
│   │   │   └── v2
│   │   │       ├── base
│   │   │       ├── core
│   │   │       └── misc
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
│   │   │   │   ├── daemon
│   │   │   │   └── docker
│   │   │   ├── feature_gate
│   │   │   ├── pipeline_execution
│   │   │   ├── rbac
│   │   │   └── routers
│   │   └── zen_stores
│   │       ├── migrations
│   │       │   ├── backup
│   │       │   └── versions
│   │       ├── resource_pools
│   │       ├── schemas
│   │       └── secrets_stores
│   └── zenml_cli
├── Dockerfile.ci *
├── Dockerfile.ci.dockerignore *
├── offload-modal-server-mysql.toml *
├── offload.toml *
└── pyproject.toml *


(* denotes selected files)
(+ denotes code-map available)
Config: directory-only view; selected files shown.
</file_map>
<file_contents>
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

File: /Users/safoine/zenml-io/zenml/tests/unit/scripts/ci/test_classify_offload_result.py
```py
"""Tests for offload result classification."""

from __future__ import annotations

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


def test_classifies_junit_failures_as_test_failures(tmp_path: Path) -> None:
    """Failing JUnit reports are treated as test failures."""
    junit = tmp_path / "junit.xml"
    junit.write_text(FAILING_JUNIT)

    result = classify_offload_result(exit_code=1, junit_path=junit)

    assert result.conclusion == "test_failure"
    assert result.offload_infra_failed is False
    assert result.tests_failed is True


def test_exit_code_two_with_passing_junit_is_success(tmp_path: Path) -> None:
    """Offload exit code 2 means flakes passed on retry."""
    junit = tmp_path / "junit.xml"
    junit.write_text(PASSING_JUNIT)

    result = classify_offload_result(exit_code=2, junit_path=junit)

    assert result.conclusion == "success"
    assert result.offload_infra_failed is False
    assert result.tests_failed is False


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


def test_setup_failure_is_infrastructure_failure(tmp_path: Path) -> None:
    """Driver setup failures trigger fallback instead of test failure."""
    result = classify_offload_result(
        exit_code=1,
        junit_path=tmp_path / "missing.xml",
        setup_failed=True,
    )

    assert result.conclusion == "infra_failure"
    assert result.offload_infra_failed is True
    assert result.tests_failed is False

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

File: /Users/safoine/zenml-io/zenml/Dockerfile.ci
```ci
ARG PYTHON_VERSION=3.13
ARG UV_VERSION=0.8.22

FROM python:${PYTHON_VERSION}-slim-bookworm AS builder
ARG UV_VERSION

RUN set -ex \
  && apt-get update \
  && apt-get install -y --no-install-recommends git graphviz build-essential \
  && apt-get clean -y \
  && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade wheel pip "uv==${UV_VERSION}"

WORKDIR /app
COPY . .

RUN scripts/install-zenml-dev.sh --integrations yes --system \
  && uv pip install --system 'setuptools<82' \
  && { pip cache purge 2>/dev/null || true; }

FROM python:${PYTHON_VERSION}-slim-bookworm

RUN set -ex \
  && apt-get update \
  && apt-get install -y --no-install-recommends git graphviz \
  && apt-get clean -y \
  && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local /usr/local

WORKDIR /app

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
    assert config["provider"]["type"] == "default"
    assert config["report"]["output_dir"] == ".ci/offload"
    assert set(config["groups"]) == {"unit", "integration"}
    assert config["framework"]["run_args"].startswith(
        "--no-provision --environment default"
    )


def test_modal_mysql_offload_config_is_valid() -> None:
    """Modal/MySQL offload config targets the remote server environment."""
    config = tomllib.loads(Path("offload-modal-server-mysql.toml").read_text())

    assert config["offload"]["max_parallel"] == 20
    assert config["provider"]["type"] == "default"
    assert config["report"]["output_dir"] == ".ci/offload"
    assert set(config["groups"]) == {"unit", "integration"}
    assert "remote-mysql-modal" in config["framework"]["run_args"]
    assert "MODAL_CI_SERVER_URL" in config["provider"]["create_command"]

```

File: /Users/safoine/zenml-io/zenml/offload.toml
```toml
[offload]
max_parallel = 20
test_timeout_secs = 960
max_batch_duration_secs = 180
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

File: /Users/safoine/zenml-io/zenml/scripts/ci/modal_sandbox_requirements.txt
```txt
modal==1.4.1
click>=8.0
dockerfile-parse>=2.0.0

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

File: /Users/safoine/zenml-io/zenml/Dockerfile.ci.dockerignore
```dockerignore
*
!.dockerignore
!Dockerfile.ci
!Dockerfile.ci.dockerignore
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


def _is_true(value: str | None) -> bool:
    return value is not None and value.lower() in {"1", "true", "yes", "on"}


def _has_junit_failures(junit_path: Path) -> bool:
    summary = parse_junit_summary(junit_path)
    print_parsed_summary(summary)
    return summary.failures > 0 or summary.errors > 0


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
) -> Classification:
    """Classify offload output as success, test failure, or infrastructure failure."""
    if setup_failed:
        return Classification(
            conclusion="infra_failure",
            offload_infra_failed=True,
            tests_failed=False,
            message="Offload setup failed before tests ran.",
        )

    if junit_path.exists():
        try:
            if _has_junit_failures(junit_path):
                return Classification(
                    conclusion="test_failure",
                    offload_infra_failed=False,
                    tests_failed=True,
                    message="Offloaded tests reported JUnit failures/errors.",
                )
        except (ET.ParseError, ValueError) as exc:
            return Classification(
                conclusion="infra_failure",
                offload_infra_failed=True,
                tests_failed=False,
                message=f"Offload produced invalid JUnit XML: {exc}",
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
            )

        return Classification(
            conclusion="infra_failure",
            offload_infra_failed=True,
            tests_failed=False,
            message="Offload exited non-zero despite a passing JUnit report.",
        )

    if exit_code == 0:
        return Classification(
            conclusion="infra_failure",
            offload_infra_failed=True,
            tests_failed=False,
            message="Offload exited successfully but did not produce JUnit XML.",
        )

    log_text = _read_log(log_path)
    if INFRA_PATTERN.search(log_text):
        message = "Offload failed before producing JUnit XML; log matches infrastructure patterns."
    else:
        message = "Offload failed before producing JUnit XML."
    return Classification(
        conclusion="infra_failure",
        offload_infra_failed=True,
        tests_failed=False,
        message=message,
    )


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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exit-code", type=int, required=True)
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--log", type=Path)
    parser.add_argument("--setup-failed", default="false")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = _build_parser().parse_args(argv)
    classification = classify_offload_result(
        exit_code=args.exit_code,
        junit_path=args.junit,
        log_path=args.log,
        setup_failed=_is_true(args.setup_failed),
    )
    print(classification.message)
    _write_github_outputs(classification)
    return 0


if __name__ == "__main__":
    sys.exit(main())

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

File: /Users/safoine/zenml-io/zenml/offload-modal-server-mysql.toml
```toml
[offload]
max_parallel = 20
test_timeout_secs = 960
max_batch_duration_secs = 180
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
command = "python -m pytest -p no:pytest_postgresql"
run_args = "--no-provision --environment remote-mysql-modal -p no:randomly -p no:rerunfailures"

[groups.unit]
retry_count = 0
filters = "tests/unit"

[groups.integration]
retry_count = 0
filters = "tests/integration --ignore=tests/integration/examples -m 'not slow'"

[report]
output_dir = ".ci/offload"

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
          python3 -m pip install --user "uv==0.8.22" -r scripts/ci/modal_sandbox_requirements.txt
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
      - name: Restore offload image cache
        id: restore-image-cache
        if: steps.eligibility.outputs.eligible == 'true' && steps.setup.outcome ==
          'success'
        uses: actions/cache/restore@27d5ce7f107fe9357f9df03efb73ab90386fccae  # v5.0.5
        with:
          path: .offload-image-cache
          key: offload-image-v1-${{ runner.os }}-${{ inputs.python-version }}-${{
            hashFiles('Dockerfile.ci', 'Dockerfile.ci.dockerignore', 'pyproject.toml',
            'scripts/install-zenml-dev.sh', 'offload.toml', 'offload-modal-server-mysql.toml')
            }}
          restore-keys: |
            offload-image-v1-${{ runner.os }}-${{ inputs.python-version }}-
      - name: Restore JUnit duration cache
        id: restore-junit-cache
        if: steps.eligibility.outputs.eligible == 'true' && steps.setup.outcome ==
          'success'
        uses: actions/cache/restore@27d5ce7f107fe9357f9df03efb73ab90386fccae  # v5.0.5
        with:
          path: .ci/offload/junit.xml
          key: offload-junit-${{ inputs.test_environment }}-${{ runner.os }}-${{ inputs.python-version
            }}
          restore-keys: |
            offload-junit-${{ inputs.test_environment }}-${{ runner.os }}-
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
        run: |
          echo "started_at=$(date +%s)" >> "$GITHUB_OUTPUT"
          trap 'echo "completed_at=$(date +%s)" >> "$GITHUB_OUTPUT"' EXIT
          python3 scripts/ci/classify_offload_result.py \
            --exit-code "$OFFLOAD_EXIT_CODE" \
            --junit .ci/offload/junit.xml \
            --log .ci/offload/offload.log \
            --setup-failed "$SETUP_FAILED"
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
        uses: actions/cache/save@27d5ce7f107fe9357f9df03efb73ab90386fccae  # v5.0.5
        with:
          path: .offload-image-cache
          key: offload-image-v1-${{ runner.os }}-${{ inputs.python-version }}-${{
            hashFiles('Dockerfile.ci', 'Dockerfile.ci.dockerignore', 'pyproject.toml',
            'scripts/install-zenml-dev.sh', 'offload.toml', 'offload-modal-server-mysql.toml')
            }}
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
        if: always() && steps.junit-cache-path.outputs.exists == 'true'
        uses: actions/cache/save@27d5ce7f107fe9357f9df03efb73ab90386fccae  # v5.0.5
        with:
          path: .ci/offload/junit.xml
          key: offload-junit-${{ inputs.test_environment }}-${{ runner.os }}-${{ inputs.python-version
            }}-${{ github.run_id }}
      - name: Upload offload artifacts
        if: always()
        uses: actions/upload-artifact@2848b2cda0e5190984587ec6bb1f36730ca78d50  # v4.6.2
        with:
          name: linux-fast-offload-artifacts
          path: .ci/offload
          if-no-files-found: warn
      - name: Fail on unsuccessful offload
        if: steps.classify.outputs.conclusion != 'success'
        run: exit 1

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
    assert manifest["artifacts"]["offload_log"]["exists"] is False

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
            "coverage_xml": _file_metadata(output_dir / "coverage.xml"),
            "offload_log": _file_metadata(output_dir / "offload.log"),
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
</file_contents>
<meta prompt 1 = "[Architect]">
You are producing an implementation-ready technical plan. The implementer will work from your plan without asking clarifying questions, so every design decision must be resolved, every touched component must be identified, and every behavioral change must be specified precisely.

Your job:
1. Analyze the requested change against the provided code — identify the relevant architecture, constraints, data flow, and extension points.
2. Decide whether this is best solved by a targeted change or a broader refactor, and justify that decision.
3. Produce a plan detailed enough that an engineer can implement it file-by-file without making design decisions of their own.

Hard constraints:
- Do not write production code, patches, diffs, or copy-paste-ready implementations.
- Stay in analysis and architecture mode only.
- Use illustrative snippets, interface shapes, sample signatures, state/data shapes, or pseudocode when they communicate the design more precisely than prose. Keep them partial — enough to remove ambiguity, not enough to copy-paste.
- Scale your response to the complexity of the request. Small, localized changes need short plans; only expand sections for changes that genuinely require the detail.

─── ANALYSIS ───

Current-state analysis (always include):
- Map the existing responsibilities, type relationships, ownership, data flow, and mutation points relevant to the request.
- Identify existing code that should be reused or extended — never duplicate what already exists without justification.
- Note hard constraints: API contracts, protocol conformances, state ownership rules, thread/actor isolation, persistence schemas, UI update mechanisms.
- When multiple subsystems interact, trace the call chain end-to-end and identify each transformation boundary.

─── DESIGN ───

Design standards — address only the standards relevant to the change; skip sections that don't apply:

1. New and modified components/types: For each, specify:
   - The name, kind (for example: class, interface, enum, record, service, module, controller), and why that kind fits the codebase and language.
   - The fields/properties/state it owns, including data shape, mutability, and ownership/lifecycle semantics.
   - Key callable interfaces or signatures, including inputs, outputs, and whether execution is synchronous/asynchronous or can fail.
   - Contracts it implements, extends, composes with, or depends on.
   - For closed sets of variants (for example enums, tagged unions, discriminated unions): all cases/variants and any attached data.
   - Where the component lives (file path) and who creates/owns its instances.

2. State and data flow: For each state change the plan introduces or modifies:
   - What triggers the change (user action, callback, notification, timer, stream event).
   - The exact path the data travels: source → transformations → destination.
   - Thread/actor/queue context at each step.
   - How downstream consumers observe the change (published property, delegate, notification, binding, callback).
   - What happens if the change arrives out of order, is duplicated, or is dropped.

3. API and interface changes: For each modified public/internal interface:
   - The before and after signatures (or new signature if additive).
   - Every call site that must be updated, grouped by file.
   - Backward-compatibility strategy if the interface is used by external consumers or persisted data.

4. Persistence and serialization: When the plan touches stored data:
   - Schema changes with exact field names, types, and defaults.
   - Migration strategy: how existing data is read, transformed, and re-persisted.
   - What happens when new code reads old data and when old code reads new data (if rollback is possible).

5. Concurrency and lifecycle:
   - Specify the execution model and safety boundaries for each new/modified component: thread affinity, event-loop/runtime constraints, isolation boundaries, queue/worker discipline, or thread-safety expectations as applicable.
   - Identify potential races, leaked references/resources, or lifecycle mismatches introduced by the change.
   - When operations are asynchronous, specify cancellation/abort behavior and what state remains after interruption.

6. Error handling and edge cases:
   - For each operation that can fail, specify what failures are possible and how they propagate.
   - Describe degraded-mode behavior: what the user sees, what state is preserved, what recovery is available.
   - Identify boundary conditions: empty collections, missing/null/optional values, first-run states, interrupted operations.

7. Algorithmic and logic-heavy work (include whenever the change involves non-trivial control flow, state machines, data transformations, or performance-sensitive paths):
   - Describe the algorithm step-by-step: inputs, outputs, invariants, and data structures.
   - Cover edge cases, failure modes, and performance characteristics (time/space complexity if relevant).
   - Explain why this approach over the most plausible alternatives.

8. Avoid unnecessary complexity:
   - Do not add layers, abstractions, or indirection without a concrete benefit identified in the plan.
   - Do not create parallel code paths — unify where possible.
   - Reuse existing patterns unless those patterns are themselves the problem.

─── OUTPUT ───

Structure your response as:

1. **Summary** — One paragraph: what changes, why, and the high-level approach.

2. **Current-state analysis** — How the relevant code works today. Trace the data/control flow end-to-end. Identify what is reusable and what is blocking.

3. **Design** — The core of the plan. Apply every applicable standard from above. Organize by logical component or subsystem, not by standard number. Each component section should cover types, state flow, interfaces, persistence, concurrency, and error handling as relevant to that component.

4. **File-by-file impact** — For every file that changes, list:
   - What changes (added/modified/removed types, methods, properties).
   - Why (which design decision drives this change).
   - Dependencies on other changes in this plan (ordering constraints).

5. **Risks and migration** — Include only when the change introduces breaking changes, data migration, or rollback concerns. Omit for additive or non-breaking work.

6. **Implementation order** — A numbered sequence of steps. Each step should be independently compilable and testable where possible. Call out steps that must be atomic (landed together).

Response discipline:
- Be specific to the provided code — reference actual type names, file paths, method names, and property names.
- Make every assumption explicit.
- Flag unknowns that must be validated during implementation, with a suggested validation approach.
- When a design decision has a non-obvious rationale, explain it in one sentence.
- Do not pad with generic advice. Every sentence should convey information the implementer needs.

Please proceed with your analysis based on the following <user instructions>
</meta prompt 1>
<user_instructions>
<taskname="CI Cache Planning"/>
<task>
Plan improvements to ZenML's CI caching around uv dependency setup for pytest collection, offload/image build cache behavior, and LPT/JUnit duration cache scheduling. The user explicitly does not want the current default and MySQL test lanes changed right now; preserve that both offload lanes continue to run both unit and integration tests.
</task>

<architecture>
- `.github/workflows/ci-fast.yml` is the fast CI entry point. It calls `linux-fast-offload.yml` twice: once with `test_environment: default` omitted, and once with `test_environment: modal-server-mysql`.
- `.github/workflows/linux-fast-offload.yml` is the reusable offload lane. It installs uv/offload driver deps on the GitHub runner, restores `.offload-image-cache`, restores `.ci/offload/junit.xml`, optionally starts a Modal MySQL sandbox, runs `offload -v run --parallel 20`, classifies JUnit/log output, saves image and JUnit caches, uploads `.ci/offload`, and fails unless classification is success.
- `offload.toml` and `offload-modal-server-mysql.toml` define the offload provider and pytest groups. Both currently include `[groups.unit] filters = "tests/unit"` and `[groups.integration] ...`, so both default and MySQL offload lanes run unit + integration tests. Do not remove either group or split lanes unless the user later asks.
- `Dockerfile.ci` builds a Python slim image and runs `scripts/install-zenml-dev.sh --integrations yes --system`, then copies `/usr/local` into the runtime image. `Dockerfile.ci.dockerignore` includes source, tests, examples, scripts, `pyproject.toml`, `uv.lock`, and offload configs in the image build context.
- `scripts/install-zenml-dev.sh` installs uv, ZenML editable extras, and optionally generated integration requirements. It is used by normal test workflows via `.github/actions/setup_environment/action.yml` and by `Dockerfile.ci`.
- `.github/workflows/unit-test.yml`, `.github/workflows/integration-test-fast.yml`, and `.github/workflows/integration-test-fast-services.yml` show the existing non-offload dependency setup and uv cache pattern. They are context for cache consistency, not an invitation to alter lane composition.
- `.github/workflows/ci-medium.yml` uses `unit-test.yml` plus `integration-test-fast.yml` with `remote-mysql-modal`; it is included because Modal/MySQL behavior appears in both current and newer CI architecture paths.
- `scripts/test-coverage-xml.sh` is the normal pytest/coverage runner. It uses `.test_durations`, `pytest-split --splitting-algorithm least_duration`, and `--store-durations` mode.
- `.github/workflows/generate-test-duration.yml` is the scheduled job that updates `.test_durations` on `develop`; `linux-fast-offload.yml` instead restores/saves JUnit XML under `.ci/offload/junit.xml` for offload duration scheduling.
- `scripts/ci_modal_mysql_sandbox.py` manages the separate Modal MySQL server sandbox and warm-image workflow; `modal-ci-image-warm.yml` schedules `warm-image` for that sandbox image, not necessarily the offload test image built from `Dockerfile.ci`.
- `scripts/ci/classify_offload_result.py`, `print_junit_summary.py`, `print_junit_failures.py`, and `emit_timing_manifest.py` consume `.ci/offload/junit.xml` and `.ci/offload/offload.log` for classification and diagnostics.
</architecture>

<selected_context>
.github/workflows/linux-fast-offload.yml: Core target. Contains runner setup, full dev dependency install for offload driver/collection, cargo/offload binary cache, `.offload-image-cache` restore/save, JUnit duration cache restore/save, Modal MySQL branch, offload command, artifact upload, and final failure gate.
.github/workflows/ci-fast.yml: Shows current fast entry point and the two offload jobs that must keep running unit + integration tests unchanged.
.github/workflows/ci-medium.yml: Shows newer medium CI flow with separate Modal MySQL sandbox and remote-mysql-modal integration test path.
.github/workflows/unit-test.yml: Current unit reusable workflow with uv cache restore and shared setup action.
.github/workflows/integration-test-fast.yml: Current fast integration reusable workflow, uv cache setup, remote-mysql-modal handling, and six-shard LPT usage through `test-coverage-xml.sh`.
.github/workflows/integration-test-fast-services.yml: Services-backed integration workflow using MySQL/zenml-server services and the same setup/test pattern.
.github/workflows/generate-test-duration.yml: Scheduled `.test_durations` generator for pytest-split LPT scheduling.
.github/workflows/modal-ci-image-warm.yml: Modal server sandbox image warmer, useful contrast with offload image cache behavior.
.github/actions/setup_environment/action.yml: Shared Python/ZenML install action used by test workflows.
.github/CLAUDE.md: Local workflow guidelines, cache pattern documentation, and formatting/security expectations.
.github/ci-phase-c-rollout.md: CI rollout notes, including Modal smoke-test commands and branch-protection constraints.
scripts/install-zenml-dev.sh: Heavy dependency install path for normal workflows and Dockerfile image build.
scripts/test-coverage-xml.sh: Normal pytest runner and `.test_durations`/least_duration logic.
scripts/ci_modal_mysql_sandbox.py: Modal MySQL sandbox image/build/start/stop implementation and `warm_image()`.
scripts/ci/modal_sandbox_requirements.txt: Modal/offload driver dependencies installed in `linux-fast-offload.yml`.
scripts/ci/classify_offload_result.py: Offload result classification based on JUnit/log presence and failures.
scripts/ci/emit_timing_manifest.py: Emits `.ci/offload/timing-manifest.json` with phase timings and artifact metadata.
scripts/ci/print_junit_summary.py and scripts/ci/print_junit_failures.py: JUnit parsing/printing helpers used by classification.
Dockerfile.ci: Offload image build definition, currently installs all dev/integration deps during image build.
Dockerfile.ci.dockerignore: Offload image build context include/exclude list.
offload.toml: Default offload config, unit + integration groups, Dockerfile prepare command with `--cached` and `.offload-image-cache` implications.
offload-modal-server-mysql.toml: MySQL offload config, same unit + integration groups and remote-mysql-modal environment.
pyproject.toml: Dependency/extras definitions, pytest dev dependencies (`pytest-split`, `pytest-rerunfailures`, coverage), uv config, and pytest settings.
tests/unit/scripts/ci/test_offload_config.py: Tests offload config shape and currently asserts `max_parallel == 20`.
tests/unit/scripts/ci/test_classify_offload_result.py: Tests offload classification behavior.
tests/unit/scripts/ci/test_emit_timing_manifest.py: Tests timing manifest artifact metadata.
tests/unit/scripts/ci/test_print_junit_summary.py: Tests JUnit summary parsing.
</selected_context>

<relationships>
- `ci-fast.yml` -> `linux-fast-offload.yml` default lane -> `offload.toml` -> `Dockerfile.ci` -> `install-zenml-dev.sh` -> offload runs `tests/unit` + `tests/integration -m 'not slow'`.
- `ci-fast.yml` -> `linux-fast-offload.yml` modal-server-mysql lane -> starts `scripts/ci_modal_mysql_sandbox.py start` -> swaps `offload-modal-server-mysql.toml` over `offload.toml` during run -> offload runs `tests/unit` + `tests/integration --ignore=tests/integration/examples -m 'not slow'` with remote MySQL env vars.
- `linux-fast-offload.yml` restores `.offload-image-cache` before `offload run`; `offload.toml` provider `prepare_command` uses `uv run @modal_sandbox.py prepare Dockerfile.ci --cached --include-cwd ...`; save is skipped when restore reports exact cache hit.
- `linux-fast-offload.yml` restores `.ci/offload/junit.xml` before offload and saves a new cache key ending in `${{ github.run_id }}` whenever a non-empty JUnit file exists, even on failure.
- Normal workflows (`unit-test.yml`, `integration-test-fast*.yml`, `linting.yml`) restore uv cache with key `uv-${{ runner.os }}-${{ inputs.python-version }}-${{ hashFiles('src/zenml/integrations/*/__init__.py') }}` and run `.github/actions/setup_environment/action.yml` -> `scripts/install-zenml-dev.sh`.
- `scripts/test-coverage-xml.sh` uses `.test_durations` with pytest-split LPT for normal lanes; offload lane appears to rely on JUnit restore/save for duration scheduling rather than the scheduled `.test_durations` file.
- `classify_offload_result.py` treats missing/invalid JUnit as infrastructure failure and existing failing JUnit as test failure; this affects whether failed runs still produce duration artifacts useful for future scheduling.
</relationships>

<current_worktree_state>
Uncommitted changes already exist and should be preserved unless the user explicitly asks otherwise:
- `offload.toml`: `max_parallel` changed from 32 to 20; sandbox resources changed from `--cpu 2 --memory-gb 4` to `--cpu 4 --memory-gb 8`.
- `offload-modal-server-mysql.toml`: same `max_parallel` and resource changes.
- `.github/workflows/linux-fast-offload.yml`: default `OFFLOAD_COMMAND` changed from `offload -v run --parallel 32` to `offload -v run --parallel 20`.
- `tests/unit/scripts/ci/test_offload_config.py`: expected `max_parallel` changed from 32 to 20.
</current_worktree_state>

<ambiguities>
- The offload tool implementation for `@modal_sandbox.py` is not in this repository; only its invocation in `offload*.toml` is visible. Treat behavior of `.offload-image-cache` as inferred from config/workflow names unless confirmed elsewhere.
- `linux-fast-offload.yml` already saves JUnit cache with `if: always()` when `.ci/offload/junit.xml` exists; if the user still sees missed scheduling after failures, investigate whether JUnit is absent/invalid, restored over, overwritten, or not used by offload as expected.
- `modal-ci-image-warm.yml` warms the Modal MySQL server sandbox image from `scripts/ci_modal_mysql_sandbox.py`; it does not directly warm the offload test image built from `Dockerfile.ci`.
- The user asked for planning improvements and explicitly excluded test lane changes. Keep proposed changes scoped to caching/setup/image/JUnit scheduling unless they approve broader CI topology changes.
</ambiguities>
</user_instructions>
