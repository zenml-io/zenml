# :running: MLOps 101 with ZenML

Build your first MLOps pipelines with ZenML.

## :earth_americas: Overview

This repository is a minimalistic MLOps project intended as a starting point to learn how to put ML workflows into 
production. At ZenML we believe that you should have the power to write your pipeline and then run it wherever you want. 
For experimentation the local (notebook) environment gives you the highest flexibility and development speed. But at 
some point you will need to deploy this very same code to a remote execution environment. There can be many reasons for 
this. You might want to leverage powerful cloud accelerators, you might want to automate your pipelines within your
CI/CD flow and/or you might want to simply move long-running training jobs out of your machine. Whatever your reason is, 
when you hit that point, ZenML ensures that the very same code you ran locally, can be ported to the environment of your
choice.

Here is a representation of how it will all come together: 

<img src=".assets/Overview.png" width="70%" alt="Pipelines Overview">

1) We have done some of the experimenting for you already and created a simple finetuning pipeline for a text-to-text task.
2) We will run this pipeline on your machine and a verify that everything works as expected.
3) Now we'll connect ZenMl to your infrastructure and configure everything.
4) Finally, we are ready to run our code remotely.

## 🏃 Run on Colab

You can use Google Colab to see ZenML in action, no signup / installation required!

<a href="https://colab.research.google.com/github/zenml-io/zenml/blob/main/examples/quickstart/quickstart.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>

## :computer: Run Locally

To run locally, install ZenML and pull this quickstart (if you haven't already done so):

```shell
# Install ZenML
pip install "zenml[server]"

# clone the ZenML repository
git clone https://github.com/zenml-io/zenml.git
cd zenml/examples/quickstart
```

Now we're ready to start. You have two options for running the quickstart locally:

#### Option 1 - Interactively explore the quickstart using Jupyter Notebook:
```bash
pip install notebook
jupyter notebook
# open notebooks/quickstart.ipynb
```

#### Option 2 - Execute the whole training pipeline from a Python script:

To run this quickstart you need to connect to a ZenML Server. You can deploy it 
[yourself on your own infrastructure](https://docs.zenml.io/getting-started/deploying-zenml) or try it
out for free, no credit-card required in our [ZenML Pro managed service](https://zenml.io/pro). In the following 
commands we install our requirements, initialize our zenml environment and connect to the deployed ZenML Server.

```bash
# Install required zenml integrations
pip install -r requirements.txt

# Initialize ZenML
zenml init

# Start the ZenServer to enable dashboard access
zenml connect --url="INSERT_YOUR_SERVER_URL_HERE"
```

As described above we have done the first step already and created an experimental pipeline. Feel free to check out 
the individual steps in the [`steps`](steps) directory. The pipeline that connects these steps can be found in 
the [`pipeline`](pipelines) directory. 

And here is how to run it. When you run the pipeline with the following command you will be using the configuration
[here](configs/training_local.yaml)

```bash
# Run the pipeline locally
python run.py --model_type=t5-small --orchestration_environment local
```

<img src=".assets/DAG.png" width="50%" alt="Dashboard view">

Above you can see the dashboard view of the pipeline we just ran in the ZenML Dashboard.
You can find the URL for this within the logs produced by the command above. 

As you can see the pipeline has run successfully. It also printed out some examples - however it seems the model is not 
yet able to solve the task well. What we did so far was validate that the pipeline and its individual steps work
well together.


### 🌵 Running Remotely

Our last section confirmed to us, that the pipeline works. Let's now run the pipeline in the environment of your choice.

For you to be able to try this next section, you will need to have access to a cloud environment (AWS, GCP, AZURE). 
ZenML wraps around all the major cloud providers and orchestration tools and lets you easily deploy your code onto them.

To do this lets head over to the `Stack` section of your ZenML Dashboard. Here you'll be able to either connect to an
existing or deploy a new environment. Choose on of the options presented to you there and come back when you have a 
stack ready to go. Then proceed to the appropriate section below. **Do not** run all three. Also be sure that you 
are running with a remote ZenML server (see Step 1 above).

<img src=".assets/StackCreate.png" width="20%" alt="Stack creation in the ZenML Dashboard">

#### AWS

For AWS you will need to install some aws requirements in your local environment. You will also 
need an AWS stack registered in ZenML. 

```bash
!zenml integration install aws s3 -y

zenml stack set <INSERT_YOUR_STACK_NAME_HERE>
python run.py --model_type=t5-small --orchestration_environment aws
```

You can edit `configs/training_aws.yaml` to adjust the settings for running your pipeline in aws.

#### GCP

For GCP you will need to install some aws requirements in your local environment. You will also 
need an AWS stack registered in ZenML. 
```bash
!zenml integration install gcp

zenml stack set <INSERT_YOUR_STACK_NAME_HERE>
python run.py --model_type=t5-small --orchestration_environment gcp
```

You can edit `configs/training_gcp.yaml` to adjust the settings.

#### Azure
```bash
!zenml integration install azure skypilot

zenml stack set <INSERT_YOUR_STACK_NAME_HERE>
python run.py --model_type=t5-small --orchestration_environment azure
```

You can edit `configs/training_azure.yaml` to adjust the settings.

## Further exploration

This was just the tip of the iceberg of what ZenML can do; check out the [**docs**](https://docs.zenml.io/) to learn more
about the capabilities of ZenML. For example, you might want to:

- [Deploy ZenML](https://docs.zenml.io/user-guide/production-guide/connect-deployed-zenml) to collaborate with your colleagues.
- Run the same pipeline on a [cloud MLOps stack in production](https://docs.zenml.io/user-guide/production-guide/cloud-stack).
- Track your metrics in an experiment tracker like [MLflow](https://docs.zenml.io/stacks-and-components/component-guide/experiment-trackers/mlflow).

## What next?

* If you have questions or feedback... join our [**Slack Community**](https://zenml.io/slack) and become part of the ZenML family!
* If you want to quickly get started with ZenML, check out [ZenML Pro](https://zenml.io/pro).