## Setup k8s Orchestrator on EKS
- AWS_REGION = "us-east-1"
- AWS_EKS_CLUSTER = "native-kubernetes-orchestrator"
- KUBE_CONTEXT = "zenml-kubernetes" 
- `aws eks --region {AWS_REGION} update-kubeconfig --name {AWS_EKS_CLUSTER} --alias {KUBE_CONTEXT}`
- (kubectl config current-context)
- zenml orchestrator register k8s_orchestrator --flavor=kubernetes --kubernetes_context={KUBE_CONTEXT} --synchronous=True

## Setup Metadata Store
- `kubectl apply -k src/zenml/integrations/kubernetes/orchestrators/yaml`
- `zenml metadata-store register kubernetes_store -f mysql --host=mysql --port=3306 --database=mysql --username=root --password=''`

## Setup ECR
- AWS_REGION = "us-east-1"
- ECR_REGISTRY_NAME = "715803424590.dkr.ecr.us-east-1.amazonaws.com"
- `aws ecr get-login-password --region {AWS_REGION} | docker login --username AWS --password-stdin {ECR_REGISTRY_NAME}`
- `zenml container-registry register ecr_registry --flavor=default --uri={ECR_REGISTRY_NAME}`

## Setup Artifact Store
- S3_BUCKET_NAME = "s3://zenbytes-bucket"
- `zenml artifact-store register s3_store --flavor=s3 --path={S3_BUCKET_NAME}`

## Register Stack
- zenml stack register aws_kubernetes_stack -m kubernetes_store -a s3_store -o k8s_orchestrator -c ecr_registry

## Run pipeline

- `python run.py`
- `kubectl get pods` -> find "evaluator" pod
- `kubectl logs {EVALUATOR_POD}`  -> you should see "Test accuracy: ..." in outputs
