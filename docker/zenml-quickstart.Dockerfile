ARG PYTHON_VERSION=3.11
ARG ZENML_VERSION=latest
ARG CLOUD_PROVIDER

FROM zenmldocker/zenml:${ZENML_VERSION}-py${PYTHON_VERSION} as base

# Install the Python requirements
RUN pip install uv

RUN uv pip install zenml${ZENML_VERSION:+==$ZENML_VERSION} notebook pyarrow datasets transformers transformers[torch] torch sentencepiece

RUN uv pip install sagemaker>=2.117.0 kubernetes aws-profile-manager s3fs>2022.3.0 boto3 adlfs>=2021.10.0 azure-keyvault-keys azure-keyvault-secrets azure-identity azureml-core==1.56.0 azure-mgmt-containerservice>=20.0.0 azure-storage-blob==12.17.0 azure-ai-ml==1.18.0 kfp>=2.6.0 gcsfs google-cloud-secret-manager google-cloud-container>=2.21.0 google-cloud-artifact-registry>=1.11.3 google-cloud-storage>=2.9.0 google-cloud-aiplatform>=1.34.0 google-cloud-build>=3.11.0
