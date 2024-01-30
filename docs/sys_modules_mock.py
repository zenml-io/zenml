import sys
from unittest.mock import MagicMock

mockers = [
    "python_terraform",
    "aws_profile_manager",
    "azure.core.credentials",
    "azure.core.exceptions",
    "azure.identity",
    "azure.mgmt.containerregistry",
    "azure.mgmt.containerservice",
    "azure.mgmt.resource",
    "azure.mgmt.storage",
    "azure.storage.blob",
    "google",
    "google.api_core.exceptions",
    "google.auth",
    "google.auth.exceptions",
    "google.auth.transport.requests",
    "google.cloud",
    "google.oauth2",
    "google.cloud.secretmanager",
    "sagemaker",
    "sagemaker.network",
    "sagemaker.processing",
    "sagemaker.workflow.execution_variables",
    "sagemaker.workflow.pipeline",
    "sagemaker.workflow.steps",
    "azure.storage.blob",
    "azure.storage.blob._models",
    "azure.storage.blob._shared.base_client",
    "azure.storage.blob.aio",
    "azure.storage.blob.aio._list_blobs_helper",
    "sky",
    "gitlab",
    "langchain",
    "xgboost",
    "google.cloud.scheduler_v1",
    "neptune",
    "label_studio_sdk",
    "kfp",
    "catboost",
    "azureml",
    "discord",
    "google.cloud.aiplatform_v1",
    "kserve",
    "redis",
    "mlflow",
    "google.cloud.devtools",
    "facets_overview",
    "google.cloud.functions_v2",
    "langchain.vectorstores",
    "facets_overview.generic_feature_statistics_generator",
    "feast",
    "azureml.core",
    "lightgbm",
    "gitlab.v4",
    "gitlab.v4.objects",
    "langchain.vectorstores.base",
    "azureml.core.authentication",
    "pycaret",
    "feast.infra",
    "pycaret.classification",
    "feast.infra.registry",
    "feast.infra.registry.base_registry",
    "sklearn",
    "sklearn.discriminant_analysis",
    "sklearn.ensemble",
    "sklearn.gaussian_process",
    "sklearn.kernel_ridge",
    "sklearn.linear_model",
    "sklearn.naive_bayes",
    "sklearn.neighbors",
    "sklearn.neural_network",
    "sklearn.svm",
    "sklearn.tree",
    "deepchecks",
    "azureml.core.conda_dependencies",
    "tensorboard",
    "pyspark",
    "wandb",
    "github",
    "mlflow.entities",
    "slack_sdk",
    "neuralprophet",
    "mlflow.pyfunc",
    "tensorflow",
    "datasets",
    "polars",
    "bentoml",
    "PIL",
    "great_expectations",
    "kfp.compiler",
    "openai",
    "google.cloud.aiplatform_v1.types",
    "kubernetes",
    "google.cloud.scheduler_v1.types",
    "scipy",
    "kfp_tekton",
    "evidently",
    "whylogs",
    "google.cloud.functions_v2.types",
    "kfp.v2",
    "mlflow.tracking",
    "sklearn.base",
    "torch",
    "great_expectations.data_context",
    "pyarrow",
    "mlflow.pyfunc.backend",
    "kfp.v2.compiler",
    "deepchecks.tabular",
    "tensorboard.manager",
    "whylogs.api",
    "scipy.sparse",
    "pyspark.conf",
    "kubernetes.client",
    "model_archiver",
    "whylogs.core",
    "slack_sdk.errors",
    "torch.utils",
    "evidently.test_preset",
    "great_expectations.checkpoint",
    "google.cloud.aiplatform_v1.types.job_state",
    "github.Repository",
    "tensorflow.python",
    "great_expectations.core",
    "evidently.pipeline",
    "bentoml._internal",
    "mlflow.entities.model_registry",
    "evidently.metric_preset",
    "deepchecks.core",
    "tensorboard.uploader",
    "datasets.dataset_dict",
    "kfp_tekton.compiler",
    "kfp_server_api",
    "mlflow.store",
    "bentoml.client",
    "torch.nn",
    "pyspark.sql",
    "evidently.metric_preset.metric_preset",
    "slack_sdk.rtm",
    "mlflow.exceptions",
    "kfp_server_api.exceptions",
    "pyarrow.parquet",
    "kubernetes.client.rest",
    "model_archiver.model_packaging",
    "kfp_tekton.compiler.pipeline_utils",
    "mlflow.store.db",
    "tensorflow.python.keras",
    "torch.utils.data",
    "great_expectations.checkpoint.types",
    "bentoml._internal.bento",
    "deepchecks.tabular.checks",
    "evidently.test_preset.test_preset",
    "whylogs.viz",
    "great_expectations.data_context.store",
    "great_expectations.checkpoint.types.checkpoint_result",
    "model_archiver.model_packaging_utils",
    "tensorflow.python.keras.utils",
    "evidently.tests",
    "evidently.metrics",
    "great_expectations.data_context.store.tuple_store_backend",
    "mlflow.store.db.db_types",
    "torch.utils.data.dataloader",
    "deepchecks.vision",
    "bentoml.exceptions",
    "great_expectations.exceptions",
    "deepchecks.vision.checks",
    "evidently.metrics.base_metric",
    "great_expectations.core.expectation_validation_result",
    "evidently.tests.base_test",
    "tensorflow.python.keras.utils.layer_utils",
    "evidently.utils",
    "great_expectations.data_context.types",
    "deepchecks.core.checks",
    "evidently.utils.generators",
    "great_expectations.data_context.types.base",
    "deepchecks.tabular.checks.data_integrity",
    "great_expectations.data_context.types.resource_identifiers",
    "great_expectations.types",
    "great_expectations.data_context.data_context",
    "langchain.docstore",
    "transformers",
    "deepchecks.core.suite",
    "whylogs.api.writer",
    "pyspark.ml",
    "great_expectations.core.batch",
    "evidently.pipeline.column_mapping",
    "mlflow.version",
    "deepchecks.core.check_result",
    "deepchecks.tabular.suites",
    "whylogs.api.writer.whylabs",
    "great_expectations.profile",
    "langchain.docstore.document",
    "evidently.report",
    "transformers.tokenization_utils_base",
    "langchain.embeddings",
    "great_expectations.profile.user_configurable_profiler",
    "evidently.test_suite",
    "deepchecks.vision.suites",
    "google.auth.compute_engine",
    "google.api_core",
    "google.auth.credentials",
    "google.oauth2.credentials",
    "s3fs",
    "gcsfs",
    "boto3",
    "adlfs",
    "azure.keyvault",
    "hvac",
    "botocore",
    "azure.keyvault.secrets",
    "hvac.exceptions",
    "botocore.exceptions",
    "botocore.client",
    "botocore.signers",
]


class DocsMocker(MagicMock):
    _DOCS_BUILDING_MODE: bool = True

    def __init__(self, *args, **kwargs):
        super(DocsMocker, self).__init__(*args, **kwargs)
        self.__getitem__ = DocsMocker._getitem
        self._full_name: str = self._extract_mock_name()
        self.__name__ = self._full_name.split(".")[-1]
        self.__module__ = ".".join(self._full_name.split(".")[:-1])
        self.__version__ = "1.0.0"
        self.__mro_entries__ = lambda _: (self._factory(),)

    def _factory(self, name: str = None):
        if name:
            class _(self.__class__):
                __module__ = ".".join(name.split(".")[:-1])
                __qualname__ = name.split(".")[-1]
            return _(name=name)
        else:
            class _(self.__class__):
                __module__ = self.__module__
                __qualname__ = self.__name__

            return _

    @staticmethod
    def _getitem(self: "DocsMocker", item):
        return self._factory()(name=f"{self._full_name}[{item}]")

    def __repr__(self) -> str:
        return self._full_name


for mocker in mockers:
    sys.modules[mocker] = DocsMocker(name=mocker)

from zenml.materializers.base_materializer import BaseMaterializer

BaseMaterializer._DOCS_BUILDING_MODE = True

if __name__ == "__main__":
    import os
    import importlib
    from zenml.logger import get_logger

    logger = get_logger(__name__)

    modules_to_add = []
    empty_dirs = []
    meaningful_files = [".py", ".tf", ".yaml", ".yml"]
    for root, subdirs, files in os.walk("src/zenml"):
        if not root.endswith("__pycache__"):
            root = root[len("src/") :]

            no_meaningful_files = len(subdirs) == 0
            for file in files:
                for mf in meaningful_files:
                    if file.endswith(mf):
                        no_meaningful_files = False
                        break
                if file.endswith(".py") and not file == "__init__.py":
                    module_name = root.replace("/", ".") + "." + file[:-3]
                    try:
                        importlib.import_module(module_name)
                    except ModuleNotFoundError as e:
                        msg: str = e.args[0]
                        module = msg[msg.find("'") + 1 :]
                        module = module[: module.find("'")]
                        modules_to_add.append(module)
                        logger.warning(msg)
                    except Exception as e:
                        logger.info("failed importing", module_name)
                        logger.error(e.args[0])
            if no_meaningful_files:
                empty_dirs.append(root)
    if modules_to_add:
        modules_to_add = set(modules_to_add)
        logger.error("Consider mocking :", modules_to_add.difference(set(mockers)))
    if empty_dirs:
        logger.warning(
            f"Directories without any 'meaningful_files' {meaningful_files} files detected. This might affect docs building process:",
            empty_dirs,
        )
    if modules_to_add:
        logger.error(
            "Returning non-zero status code to indicate that docs building failed. Please fix the above errors and try again."
        )
        exit(1)
