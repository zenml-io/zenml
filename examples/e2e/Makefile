remote-login:
	zenml connect --url ${ZENML_SERVER_URL} --username ${ZENML_SERVER_USER}

setup: remote-login
	zenml integration install sklearn mlflow s3 kubernetes kubeflow slack evidently -y
	zenml integration export-requirements >> .zenml_integration_requirements
	zenml stack set ${ZENML_SERVER_STACK}
	zenml stack up
