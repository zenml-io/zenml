# MLflow Terraform Module 

## Input Variables

Input | Description
--- | ---
htpasswd | The username-password combination in the form of an `htpasswd` string to be used to setup the tracking server. You can use any online generator like https://www.web2generators.com/apache-tools/htpasswd-generator 
artifact_S3 | true if the artifact store is S3.
artifact_S3_Bucket | The name of the S3 bucket.
artifact_S3_Access_Key | The access key for the S3 bucket.
artifact_S3_Secret_Key | The secret key for the S3 bucket.

## Outputs

Output | Description
--- | ---
ingress-controller-name | Used for getting the ingress URL for the MLflow tracking server|
ingress-controller-namespace | Used for getting the ingress URL for the MLflow tracking server|

The tracking URI is obtained by querying the relevant Kubernetes service that exposes the tracking server. This is done automatically when you execute any recipe. You can use the `mlflow-tracking-URL` output to get this value.

However, you can also manually query the URL by using the folowing command.

```
kubectl get service <ingress-controller-name>-ingress-nginx-controller -n <ingress-controller-namespace>
```

In the output of this command, the EXTERNAL_IP field is the IP of the ingress controller and the path "/" is configured already to direct to the MLflow tracking server.
