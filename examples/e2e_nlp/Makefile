stack_name ?= nlp_template_stack
setup:
	pip install -r requirements.txt
	zenml integration install pytorch mlflow aws s3 slack huggingface -y
	zenml init

install-local-stack:
	@echo "Specify stack name [$(stack_name)]: " && read input && [ -n "$$input" ] && stack_name="$$input" || stack_name="$(stack_name)" && \
	zenml experiment-tracker register -f mlflow mlflow_local_$${stack_name} && \
	zenml model-registry register -f mlflow mlflow_local_$${stack_name} && \
	zenml stack register -a default -o default -r mlflow_local_$${stack_name} \
    -e mlflow_local_$${stack_name} $${stack_name} && \
	zenml stack set $${stack_name} && \
	zenml login --local
