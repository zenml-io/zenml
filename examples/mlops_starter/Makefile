# MLOps Starter Makefile
# Convenient commands for the complete MLOps workflow

.PHONY: help install setup train promote serve test clean

help: ## Show this help message
	@echo "MLOps Starter - Complete Workflow Commands"
	@echo "=========================================="
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make <target>\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  %-15s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

install: ## Install dependencies
	pip install -r requirements.txt
	zenml integration install sklearn pandas -y

setup: ## Initialize ZenML and start local server
	zenml init
	zenml login --local

data: ## Run feature engineering pipeline
	python run.py --feature-pipeline

train: ## Run training pipeline (both SGD and RF models)
	python run.py --training-pipeline

promote: ## Promote Random Forest model to production
	zenml model version update breast_cancer_classifier rf --stage production

inference: ## Run batch inference pipeline
	python run.py --inference-pipeline

serve: ## Deploy serving endpoint
	zenml pipeline deploy pipelines.inference --config configs/inference.yaml

test-endpoint: ## Test the deployed endpoint
	python test_serving.py

example-client: ## Run example client
	python example_client.py

# Complete workflows
full-batch: data train promote inference ## Complete batch ML workflow

full-serving: data train promote serve ## Complete workflow including serving deployment

# Pipeline status and monitoring
status: ## Show model and deployment status
	@echo "📋 Current Models:"
	zenml model list
	@echo "\n🚀 Current Deployments:"
	zenml pipeline deployment list

logs: ## Show recent pipeline logs
	zenml pipeline runs list --size 10

clean: ## Clean up temporary files
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete
	find . -name ".pytest_cache" -delete

# Development helpers
format: ## Format code
	black . --exclude venv
	isort . --skip venv

lint: ## Lint code
	flake8 . --exclude venv
	mypy . --exclude venv

# Help text
info:
	@echo "🚀 MLOps Starter - Complete Workflow"
	@echo "===================================="
	@echo ""
	@echo "Quick Start:"
	@echo "  make install setup data train promote serve"
	@echo ""
	@echo "Then test your endpoint:"
	@echo "  make test-endpoint"
	@echo ""
	@echo "Monitor your deployments:"
	@echo "  make status"