# :dango: Pipeline Orchestration on Kubernetes

This example will demonstrate how to orchestrate pipelines using the ZenML Kubernetes-native orchestrator. We will build a simple pipeline consisting of four steps and orchestrate it in an Amazon EKS Kubernetes cluster.

## :heavy_check_mark: Requirements

In order to follow this tutorial you need to first spin up an Amazon EKS cluster, an ECR container registry, as well as a S3 bucket 
for artifact storage. 

Furthermore, you need to have kubectl and Docker installed locally.

### Setup and Register Kubernetes Orchestrator on EKS
After spinning up your EKS cluster, run the following command to grant access to your local kubectl.

```bash
AWS_REGION = "eu-central-1"
AWS_EKS_CLUSTER = "native-kubernetes-orchestrator"
KUBE_CONTEXT = "zenml-kubernetes" 
aws eks --region {AWS_REGION} update-kubeconfig --name {AWS_EKS_CLUSTER} --alias {KUBE_CONTEXT}
```

Next, run the following command to register your Kubernetes orchestrator:

```bash
zenml orchestrator register k8s_orchestrator 
    --flavor=kubernetes 
    --kubernetes_context={KUBE_CONTEXT} 
    --synchronous=True
```

### Setup and Register Metadata Store


For metadata storage, we will use a MySQL database that we deploy within the EKS cluster. Run the following command to spin up the MySQL pod in your EKS cluster:

```bash
kubectl apply -k src/zenml/integrations/kubernetes/orchestrators/yaml
```

Now we can register the database as a metadata store as follows:
```bash
zenml metadata-store register kubernetes_store 
    --flavor=mysql
    --host=mysql 
    --port=3306 
    --database=mysql 
    --username=root 
    --password=''
```

### Register ECR Container Registry
Next, you need to login to your ECR via Docker so you can push images to your container registry:

```bash
AWS_REGION = "us-east-1"
ECR_REGISTRY_NAME = "715803424590.dkr.ecr.us-east-1.amazonaws.com"
aws ecr get-login-password --region {AWS_REGION} | docker login --username AWS --password-stdin {ECR_REGISTRY_NAME}
```

Now you can register your ECR in ZenML like this:
```bash
zenml container-registry register ecr_registry 
    --flavor=default 
    --uri={ECR_REGISTRY_NAME}
```

### Setup Artifact Store
Lastly, we also need to register our S3 bucket as artifact store:

```bash
S3_BUCKET_NAME = "s3://zenbytes-bucket"
zenml artifact-store register s3_store 
    --flavor=s3 
    --path={S3_BUCKET_NAME}
```

### Register Stack

Finally, let us bring everything together and register our stack:
```bash
zenml stack register aws_kubernetes_stack 
    -m kubernetes_store 
    -a s3_store 
    -o k8s_orchestrator 
    -c ecr_registry
```

## :computer: Run Pipeline Locally
Now that our stack is set up, all of our ML code will automatically be executed on the EKS cluster. Let's run the example pipeline:

```bash
python run.py
```

You should now see the following output (which are the logs of the kubernetes orchestrator pod):

```
INFO:root:Starting orchestration...
INFO:root:Running step importer...
INFO:root:Waiting for step importer...
INFO:root:Step importer finished.
INFO:root:Running step skew_comparison...
INFO:root:Running step svc_trainer...
INFO:root:Waiting for step skew_comparison...
INFO:root:Waiting for step svc_trainer...
INFO:root:Step svc_trainer finished.
INFO:root:Running step evaluator...
INFO:root:Waiting for step evaluator...
INFO:root:Step skew_comparison finished.
INFO:root:Step evaluator finished.
INFO:root:Orchestration complete.
```

Note that the `skew_comparison` and `svc_trainer` steps were run in parallel, as they both only depend on the `importer` step.

### Check Result

After orchestration is complete, run the following command to list all Kubernetes pods that were created to run this example:

```
kubectl get pods -l pipeline=parallelizable_pipeline
```

You should see that all your steps have status `Completed`. If not, wait for the remaining jobs to finish. Once every step is completed, find the pod corresponding to the `evaluator` step and print it's logs:

```bash
kubectl get pods -l step=evaluator
EVALUATOR_POD = ...
kubectl logs {EVALUATOR_POD}
```

If everything went well, you should be able to see the test accuracy printed in the logs.

## :sponge: Clean Up

Run the following commands to delete all pods and other Kubernetes units we created during this example:

### Delete Run Pods
```bash
kubectl delete -k src/zenml/integrations/kubernetes/orchestrators/yaml
```

### Delete MySQL Metadata Store
```bash
kubectl delete pod -l pipeline=parallelizable_pipeline
```
