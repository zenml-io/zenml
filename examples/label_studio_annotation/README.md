# 🏷 Continuous Annotation with Label Studio

Data annotation / labeling is a core part of MLOps that is frequently left out
of the conversation. ZenML offers a way to build continuous annotation
(combining training and annotation into a loop) with Label Studio. This uses a
combination of user-defined steps as well as some built-in steps that ZenML
provides.

## 🗺 Overview

NOTE: This example currently only runs with a cloud artifact store. [This guide
by Label Studio](https://labelstud.io/guide/storage.html) contains more details
if you have trouble understanding the instructions below.

For a full video walkthrough on how to run this example, please check out [our
community hour demo](https://www.youtube.com/watch?v=bLFGnoApWeU) in which we
show how to run the various pipelines, in what order, all using an AWS stack.

# 🖥 Run the example

You will need to obtain your Label Studio API key. This will give you access to
the web annotation interface.

```shell
# start a temporary / one-off label-studio instance to get your API key
label-studio start -p 8094
```

First order of business is to sign up if you haven't done so already, using an
email and a password. Then visit http://localhost:8094/ to log in, and then
visit http://localhost:8094/user/account and get your Label Studio API key (from
the upper right hand corner). You will need it for later. Ctrl-c out of the
Label Studio server that is running on the terminal.

In order to run this example, you need to install and initialize ZenML and Label
Studio.

```shell
pip install zenml

# pull example
zenml example pull label_studio_annotation
cd zenml_examples/label_studio_annotation

# Initialize ZenML repo
zenml init
```

## 👣 Step-by-Step Infrastructure Setup

Pick your preferred infrastructure provider from Azure, GCP and AWS. Then follow
the relevant guide below for how to set up the infrastructure required by this
example.

### 🥞 Set up your stack for Microsoft Azure

You should install the relevant integrations:

```shell
zenml integration install label_studio pytorch azure
```

Some setup for your stack is required. This assumes you have a cloud secrets
manager setup and installed. (See
[here](https://docs.zenml.io/mlops-stacks/secrets-managers) for more on how to
do that.)

```shell
zenml stack copy default <ANNOTATION_STACK_NAME>

zenml stack set <ANNOTATION_STACK_NAME>

zenml secrets-manager register <YOUR_SECRETS_MANAGER> --key_vault_name=<YOUR_KEY_VAULT_NAME> -f azure_key_vault

zenml stack update <ANNOTATION_STACK_NAME> -x <YOUR_SECRETS_MANAGER>

zenml secret register <YOUR_AZURE_AUTH_SECRET_NAME> --schema=azure --account_name="<YOUR_AZURE_ACCOUNT_NAME>" --account_key="<YOUR_AZURE_ACCOUNT_KEY>"

zenml artifact-store register azure_artifact_store -f=azure --path="az://<NAME_OF_ARTIFACT_STORE_OR_BLOB_IN_AZURE>" --authentication_secret="<YOUR_AZURE_AUTH_SECRET_NAME>"

zenml stack update <ANNOTATION_STACK_NAME> -a <YOUR_CLOUD_ARTIFACT_STORE>

zenml secret register <LABEL_STUDIO_SECRET_NAME> --api_key="<YOUR_API_KEY>"

zenml annotator register <YOUR_LABEL_STUDIO_ANNOTATOR> --flavor label_studio --authentication_secret="<LABEL_STUDIO_SECRET_NAME>"

zenml stack update <ANNOTATION_STACK_NAME> -an <YOUR_LABEL_STUDIO_ANNOTATOR>

zenml stack up
```

This will initialize the daemon server which Label Studio requires, albeit
running on a default port of 8093.

### 🥞 Set up your stack for GCP

You should install the relevant integrations:

```shell
zenml integration install label_studio pytorch gcp
```

This setup guide assumes that you have installed and are able to use the
`gcloud` CLI to run commands.

Create your artifact store and set up the necessary permissions and service
accounts:

```shell
gsutil mb -p <YOUR_GCP_PROJECT_NAME> -l <YOUR_GCP_REGION_NAME> -c standard "gs://<YOUR_BUCKET_NAME>"

gcloud iam service-accounts create <YOUR_SERVICE_ACCOUNT_NAME>

gcloud projects add-iam-policy-binding <YOUR_GCP_PROJECT_NAME> --member="serviceAccount:<YOUR_SERVICE_ACCOUNT_NAME>@<YOUR_GCP_PROJECT_NAME>.iam.gserviceaccount.com" --role="roles/storage.admin"

gcloud projects add-iam-policy-binding <YOUR_GCP_PROJECT_NAME> --member="serviceAccount:<YOUR_SERVICE_ACCOUNT_NAME>@<YOUR_GCP_PROJECT_NAME>.iam.gserviceaccount.com" --role="roles/iam.serviceAccountTokenCreator"

gcloud iam service-accounts keys create ls-annotation-credentials.json --iam-account=<YOUR_SERVICE_ACCOUNT_NAME>@<YOUR_GCP_PROJECT_NAME>.iam.gserviceaccount.com
```

Now you have a credentials `json` file that you can use to authenticate with
Label Studio. Make sure to note down the path where this was created.

Now you can set up the rest of your stack:

```shell
zenml stack copy default <YOUR_ANNOTATION_STACK_NAME>

zenml stack set <YOUR_ANNOTATION_STACK_NAME>

zenml secrets-manager register <YOUR_SECRETS_MANAGER> -f gcp_secrets_manager --project_id="<YOUR_GCP_PROJECT_NAME>"

zenml stack update <YOUR_ANNOTATION_STACK_NAME> -x <YOUR_SECRETS_MANAGER>

zenml secret register <YOUR_GCP_AUTH_SECRETS_NAME> --schema=gcp --token="@PATH/TO/JSON/FILE/CREATED/ABOVE"

zenml artifact-store register gcp_artifact_store -f=gcp --path="gs://<YOUR_BUCKET_NAME>" --authentication_secret="<YOUR_GCP_AUTH_SECRETS_NAME>"

zenml stack update <YOUR_ANNOTATION_STACK_NAME> -a <YOUR_CLOUD_ARTIFACT_STORE>

zenml secret register <LABEL_STUDIO_SECRET_NAME> --api_key="<YOUR_API_KEY>"

zenml annotator register <YOUR_LABEL_STUDIO_ANNOTATOR> --flavor label_studio --authentication_secret="<LABEL_STUDIO_SECRET_NAME>"

zenml stack update <YOUR_ANNOTATION_STACK_NAME> -an <YOUR_LABEL_STUDIO_ANNOTATOR>

zenml stack up
```

This will initialize the daemon server which Label Studio requires, albeit
running on a default port of 8093.

### 🥞 Set up your stack for AWS

You should install the relevant integrations:

```shell
zenml integration install label_studio pytorch s3
```

Create your basic S3 bucket via CLI command:

```shell
REGION=<YOUR_DESIRED_AWS_REGION>
S3_BUCKET_NAME=<YOUR_DESIRED_S3_BUCKET_NAME>

aws s3api create-bucket --bucket=$S3_BUCKET_NAME --region=$REGION --create-bucket-configuration=LocationConstraint=$REGION
```

Create a `.json` file on your local hard drive containing the following data,
making sure to replace `<YOUR_BUCKET_NAME>` with the actual value you used
above:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor1",
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket",
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject"
            ],
            "Resource": [
                "arn:aws:s3:::<YOUR_BUCKET_NAME>",
                "arn:aws:s3:::<YOUR_BUCKET_NAME>/*"
            ]
        }
    ]
}
```

Create a policy using [the `create-policy` CLI
command](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_create-cli.html)
for IAM to manage the Label Studio access to the S3 bucket. This assumes you are
running the command from the same directory in which you saved the policy file.

```shell
# this token duration is the maximum possible, but you will have to check if your bucket allows this
aws iam create-policy --policy-name <YOUR_POLICY_NAME> --policy-document file://<YOUR_POLICY_FILE_NAME> --duration_seconds=43200
```

Set up cross-origin resource sharing (CORS) access to your bucket, using a
policy that allows `GET` access from the same host name as your Label Studio
deployment. You can use the CORS file we have pre-populated for you inside the
examples repo as follows:

```shell
cd cloud_config/aws

aws s3api put-bucket-cors --bucket $S3_BUCKET_NAME --cors-configuration file://cors.json

cd ../..
```

Now you can get to the fun part of setting up Label Studio and working with
ZenML:

```shell
zenml stack copy default <YOUR_AWS_ZENML_STACK_NAME>

zenml stack set <YOUR_AWS_ZENML_STACK_NAME>

zenml secrets-manager register <YOUR_SECRETS_MANAGER> --flavor=aws --region_name=<AWS_REGION_NAME>

zenml stack update <YOUR_AWS_ZENML_STACK_NAME> -x <YOUR_SECRETS_MANAGER>

# copy down the credentials output from this command
aws sts get-session-token --profile=<YOUR_AWS_CONFIG_PROFILE_NAME>
```

Use the credentials output from the command to get your
`<LABEL_STUDIO_ACCESS_KEY_ID>`, `<LABEL_STUDIO_SECRET_ACCESS_KEY>`, and
`<LABEL_STUDIO_AWS_SESSION_TOKEN>` which we will use to register a secret.

```shell
# this secret must be named 'aws_label_studio'
zenml secret register aws_label_studio --schema=aws_label_studio --aws_access_key_id="<LABEL_STUDIO_ACCESS_KEY_ID>" --aws_secret_access_key="<LABEL_STUDIO_SECRET_ACCESS_KEY>" --aws_session_token="<LABEL_STUDIO_AWS_SESSION_TOKEN>"

# use your standard access key id and secret access key from ~/.aws/credentials here
zenml secret register <YOUR_AWS_SECRET_NAME> --schema=aws_label_studio--aws_access_key_id="<YOUR_ACCESS_KEY_ID>" --aws_secret_access_key="<YOUR_SECRET_ACCESS_KEY>"

zenml artifact-store register <YOUR_CLOUD_ARTIFACT_STORE> --flavor=s3 --path=s3://<YOUR_S3_BUCKET_NAME> --authentication_secret="<YOUR_AWS_SECRET_NAME>"

zenml stack update <YOUR_AWS_ZENML_STACK_NAME> -a <YOUR_CLOUD_ARTIFACT_STORE>

zenml secret register <LABEL_STUDIO_SECRET_NAME> --api_key="<YOUR_API_KEY>"

zenml annotator register <YOUR_LABEL_STUDIO_ANNOTATOR> --flavor label_studio --authentication_secret="<LABEL_STUDIO_SECRET_NAME>"

zenml stack update <YOUR_AWS_ZENML_STACK_NAME> -an <YOUR_LABEL_STUDIO_ANNOTATOR>

zenml stack up
```

This will initialize the daemon server which Label Studio requires, albeit
running on a default port of 8093.


### ▶️ Run the Code

There are several parts to running the pipeline. Start with:

```shell
python run.py aws --train
```

On the first time you run this, this will fetch a pretrained model and amend the
head so that it is able to perform binary image classification. It does not get
finetuned at this point, however.

You can use the CLI command to view our newly created dataset:

```
zenml annotator dataset list
```

It will show that we now have an `aria_detector` dataset.

Then you can use this model to perform inference on some images (located in
`data/batch_1`). These 'pre-annotations' will then be synchronized with Label
Studio.

```shell
python run.py aws --inference
```

At this point you should do some annotation using the Label Studio web
interface, making sure to annotate all the ten images. You can launch the
annotation interface with the CLI:

```shell
zenml annotator dataset launch aria_detector
```

When you're done, you can get the stats on the annotation work you did by using
the ZenML CLI:

```shell
zenml annotator dataset stats aria_detector
```

This will tell you how many labeled and unlabeled tasks you have for your Label
Studio dataset.

With the annotations complete, you should rerun the training step. This time
instead of just pulling a pretrained model, the step will finetune our
previously-downloaded pretrained model using the ten annotations we just made.
This will improve our model's performance (a bit).

```shell
python run.py aws --train --rerun
```

Now we can rerun the inference step, though using a different set of data
(`data/batch_2`).

```shell
python run.py aws --inference --rerun
```

Once we've rerun this step, we can inspect the predictions our newly finetuned
model made within Label Studio.

## CLI Commands for the Label Studio Integration

Once you've run the pipeline for the first time, you'll be able to use some of
the ZenML CLI commands to interact with your Label Studio annotations and the
dataset:

```shell
# the obvious ones to try
zenml annotator describe
zenml annotator dataset list
zenml annotator dataset <YOUR_DATASET_NAME> stats
```

### 🧽 Clean up

In order to clean up, delete any relevant cloud infrastructure that was created
above (the cloud storage bucket is the main one, along with any permissions and
whatever secrets or secrets vaults you created) and the remaining ZenML
references. If you created assets under a GCP project, or an Azure resource
group, then the newly created assets should be easy to find. With Amazon,
deleting the IAM rules, the secrets manager vault and the S3 bucket are what you
need to delete.

```shell
rm -rf zenml_examples
```

# 📜 Learn more

If you want to learn more about annotation in general or about how to use your
own annotation tool in ZenML check out our
[docs](https://docs.zenml.io/mlops-stacks/annotators).

To explore other available CLI commands related to the annotator stack
components, check out the [CLI docs annotator
section](https://apidocs.zenml.io/latest/api_docs/repository/#zenml.repository.Repository).
