# ☮️ Fine-tuning open source LLMs using MLOps pipelines

Welcome to your newly generated "ZenML LLM Finetuning project" project! This is
a great way to get hands-on with ZenML using production-like template. 
The project contains a collection of ZenML steps, pipelines and other artifacts
and useful resources that can serve as a solid starting point for finetuning open-source LLMs using ZenML.

Using these pipelines, we can run the data-preparation and model finetuning with a single command while using YAML files for [configuration](https://docs.zenml.io/user-guide/production-guide/configure-pipeline) and letting ZenML take care of tracking our metadata and [containerizing our pipelines](https://docs.zenml.io/user-guide/advanced-guide/infrastructure-management/containerize-your-pipeline).

<div align="center">
  <br/>
    <a href="https://cloud.zenml.io">
      <img alt="Model version metadata" src=".assets/model.png">
    </a>
  <br/>
</div>

## :earth_americas: Inspiration and Credit

This project heavily relies on the [Lit-GPT project](https://github.com/Lightning-AI/litgpt) of the amazing people at Lightning AI. We used [this blogpost](https://lightning.ai/pages/community/lora-insights/#toc14) to get started with LoRA and QLoRA and modified the commands they recommend to make them work using ZenML.

## 🏃 How to run

In this project we provide a few predefined configuration files for finetuning models on the [Alpaca](https://huggingface.co/datasets/tatsu-lab/alpaca) dataset. Before we're able to run any pipeline, we need to set up our environment as follows:

```bash
# Set up a Python virtual environment, if you haven't already
python3 -m venv .venv
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### Combined feature engineering and finetuning pipeline

The easiest way to get started with just a single command is to run the finetuning pipeline with the `finetune-alpaca.yaml` configuration file, which will do both feature engineering and finetuning:

```shell
python run.py --finetuning-pipeline --config finetune-alpaca.yaml
```

When running the pipeline like this, the trained adapter will be stored in the ZenML artifact store. You can optionally upload the adapter, the merged model or both by specifying the `adapter_output_repo` and `merged_output_repo` parameters in the configuration file.


### Evaluation pipeline

Before running this pipeline, you will need to fill in the `adapter_repo` in the `eval.yaml` configuration file. This should point to a huggingface repository that contains the finetuned adapter you got by running the finetuning pipeline.

```shell
python run.py --eval-pipeline --config eval.yaml
```

### Merging pipeline

In case you have trained an adapter using the finetuning pipeline, you can merge it with the base model by filling in the `adapter_repo` and `output_repo` parameters in the `merge.yaml` file, and then running:

```shell
python run.py --merge-pipeline --config merge.yaml
```

### Feature Engineering followed by Finetuning

If you want to finetune your model on a different dataset, you can do so by running the feature engineering pipeline followed by the finetuning pipeline. To define your dataset, take a look at the `scripts/prepare_*` scripts and set the dataset name in the `feature-alpaca.yaml` config file.

```shell
python run.py --feature-pipeline --config feature-alpaca.yaml
python run.py --finetuning-pipeline --config finetune-from-dataset.yaml
```

## ☁️ Running with a remote stack

To finetune an LLM on remote infrastructure, you can either use a remote orchestrator or a remote step operator. Follow these steps to set up a complete remote stack:
- Register the [orchestrator](https://docs.zenml.io/stacks-and-components/component-guide/orchestrators) (or [step operator](https://docs.zenml.io/stacks-and-components/component-guide/step-operators)) and make sure to configure it in a way so that the finetuning step has access to a GPU with at least 24GB of VRAM. Check out our docs for more [details](https://docs.zenml.io/stacks-and-components/component-guide).
    - To access GPUs with this amount of VRAM, you might need to increase your GPU quota ([AWS](https://docs.aws.amazon.com/servicequotas/latest/userguide/request-quota-increase.html), [GCP](https://console.cloud.google.com/iam-admin/quotas), [Azure](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-manage-quotas?view=azureml-api-2#request-quota-and-limit-increases)).
    - The GPU instance that your finetuning will be running on will have CUDA drivers of a specific version installed. If that CUDA version is not compatible with the one provided by the default Docker image of the finetuning pipeline, you will need to modify it in the configuration file. See [here](https://hub.docker.com/r/pytorch/pytorch/tags) for a list of available PyTorch images.
    - If you're running out of memory, you can experiment with quantized LoRA (QLoRA) by setting a different value for the `quantize` parameter in the configuration, or reduce the `global_batch_size`/`micro_batch_size`.
- Register a remote [artifact store](https://docs.zenml.io/stacks-and-components/component-guide/artifact-stores) and [container registry](https://docs.zenml.io/stacks-and-components/component-guide/container-registries).
- Register a stack with all these components
    ```shell
    zenml stack register llm-finetuning-stack -o <ORCHESTRATOR_NAME> \
        -a <ARTIFACT_STORE_NAME> \
        -c <CONTAINER_REGISTRY_NAME> \
        [-s <STEP_OPERATOR_NAME>]
    ```

## 💾 Running with custom data

To finetune a model with your custom data, you will need to convert it to a CSV file with the columns described
[here](https://github.com/Lightning-AI/litgpt/blob/main/tutorials/prepare_dataset.md#preparing-custom-datasets-from-a-csv-file).

Next, update the `configs/feature-custom.yaml` file and set the value of the `csv_path` parameter to that CSV file.
With all that in place, you can now run the feature engineering pipeline to convert your CSV into the correct format for training and then run the finetuning pipeline as follows:
```shell
python run.py --feature-pipeline --config feature-custom.yaml
python run.py --finetuning-pipeline --config finetune-from-dataset.yaml
```

## 📜 Project Structure

The project loosely follows [the recommended ZenML project structure](https://docs.zenml.io/user-guide/starter-guide/follow-best-practices):

```
.
├── configs                         # pipeline configuration files
│   ├── eval.yaml                   # configuration for the evaluation pipeline
│   ├── feature-alpaca.yaml         # configuration for the feature engineering pipeline
│   ├── feature-custom.yaml         # configuration for the feature engineering pipeline
│   ├── finetune-alpaca.yaml        # configuration for the finetuning pipeline
│   ├── finetune-from-dataset.yaml  # configuration for the finetuning pipeline
│   └── merge.yaml                  # configuration for the merging pipeline
├── pipelines                       # `zenml.pipeline` implementations
│   ├── evaluate.py                 # Evaluation pipeline
│   ├── feature_engineering.py      # Feature engineering pipeline
│   ├── finetuning.py               # Finetuning pipeline
│   └── merge.py                    # Merging pipeline
├── steps                           # logically grouped `zenml.steps` implementations
│   ├── evaluate.py                 # evaluate model performance
│   ├── feature_engineering.py      # preprocess data
│   ├── finetune.py                 # finetune a model
│   ├── merge.py                    # merge model and adapter
│   ├── params.py                   # shared parameters for steps
│   └── utils.py                    # utility functions
├── .dockerignore
├── README.md                       # this file
├── requirements.txt                # extra Python dependencies 
└── run.py                          # CLI tool to run pipelines on ZenML Stack
```
