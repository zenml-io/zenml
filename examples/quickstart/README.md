```shell
# Register the MLflow experiment tracker
zenml experiment-tracker register mlflow --flavor=mlflow
zenml model-registry register mlflow --flavor=mlflow
zenml model-deployer register mlflow --flavor=mlflow


zenml stack register quickstart -a default -o default -e mlflow -r mlflow -d mlflow --set


```
