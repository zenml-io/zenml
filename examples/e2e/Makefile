MLFLOW_EXPERIMENT_TRACKER_NAME := mlflow_aws

remote-login:
	zenml connect --url ${ZENML_SERVER_URL} --username zenml

setup: remote-login
	zenml integration install sklearn mlflow s3 kubernetes kubeflow slack evidently -y
	zenml integration export-requirements >> .zenml_integration_requirements

register-components:
	zenml experiment-tracker describe ${MLFLOW_EXPERIMENT_TRACKER_NAME} && \
	echo "Updating experiment tracker" && \
	
	zenml experiment-tracker update ${MLFLOW_EXPERIMENT_TRACKER_NAME} \
			--tracking_username={{mlflow_aws.tracking_user}} \
			--tracking_password={{mlflow_aws.tracking_password}} \
			--tracking_uri=${MLFLOW_EXPERIMENT_TRACKER_URI} \
	|| \
	echo "Registering experiment tracker" && \
	zenml experiment-tracker register ${MLFLOW_EXPERIMENT_TRACKER_NAME} \
			--flavor=mlflow \
			--tracking_username={{mlflow_aws.tracking_user}} \
			--tracking_password={{mlflow_aws.tracking_password}} \
			--tracking_uri=${MLFLOW_EXPERIMENT_TRACKER_URI}

create-stack-aws:
	zenml stack register e2e_example_aws \
    	-a s3_implicit\
		-o k8s_orchestrator\
		-d mlflow_deployer\
		-e mlflow_aws\
		-r mlflow_registry\
		-c aws_registry\
		-al slack_alerter\
		-dv evidently
	zenml stack set e2e_example_aws
	zenml stack up

