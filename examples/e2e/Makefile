stack_name ?= e2e_template_stack
setup:
	pip install -r requirements.txt
	zenml integration install aws sklearn mlflow slack evidently kubeflow kubernetes -y

install-stack-local:
	@echo "Specify stack name [$(stack_name)]: " && read input && [ -n "$$input" ] && stack_name="$$input" || stack_name="$(stack_name)" && \
	zenml experiment-tracker register -f mlflow mlflow_local_$${stack_name} && \
	zenml model-registry register -f mlflow mlflow_local_$${stack_name} && \
	zenml model-deployer register -f mlflow mlflow_local_$${stack_name} && \
	zenml data-validator register -f evidently evidently_$${stack_name} && \
	zenml stack register -a default -o default -r mlflow_local_$${stack_name} \
	-d mlflow_local_$${stack_name} -e mlflow_local_$${stack_name} -dv \
	evidently_$${stack_name} $${stack_name} && \
	zenml stack set $${stack_name}
