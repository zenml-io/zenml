# Customer Churn Prediction: Training and Deployment

This example demonstrates the complete lifecycle of a machine learning model with ZenML, from training a churn prediction model to deploying it as a real-time inference service.

## 🎯 What You'll Learn

- **Training ML Models**: Build and train a customer churn prediction model using synthetic data
- **Model Deployment**: Deploy your trained model as a real-time HTTP service
- **Pipeline Deployments**: Convert batch pipelines into production-ready APIs
- **Model Versioning**: Manage model artifacts with automatic versioning and tagging
- **Real-time Inference**: Serve predictions with millisecond latency

## 🏗️ Example Structure

```
deploying_ml_model/
├── pipelines/
│   ├── training_pipeline.py     # Model training pipeline
│   └── inference_pipeline.py    # Real-time inference pipeline
├── steps/
│   ├── data.py                  # Synthetic data generation
│   ├── train.py                 # Model training step
│   └── inference.py             # Prediction step
├── run.py                       # Main CLI interface
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## 📊 The Use Case

**Customer Churn Prediction**: Predict whether a customer will cancel their subscription based on their usage patterns and account details.

**Features Used**:
- Account length (months)
- Customer service calls
- Monthly charges
- Total charges
- Internet service status
- Phone service status
- Contract length
- Payment method

## 🚀 Quick Start

### 1. Train the Model

```bash
# Generate synthetic data and train a Random Forest classifier
python run.py --train

# Train with more samples for better accuracy
python run.py --train --samples 5000
```

This will:
- Generate 1000 synthetic customer records
- Train a Random Forest classifier with feature scaling
- Evaluate model performance on held-out test data
- Tag the model as "production" for deployment
- Log training metrics and model metadata

### 2. Test Local Inference

```bash
# Test with sample customer data
python run.py --predict

# Test with custom customer features
python run.py --predict --features '{
  "account_length": 24,
  "customer_service_calls": 2,
  "monthly_charges": 45.0,
  "total_charges": 1080.0,
  "has_internet_service": 1,
  "has_phone_service": 1,
  "contract_length": 12,
  "payment_method_electronic": 0
}'
```

### 3. Deploy as Real-time Service

Deploy the inference pipeline as a containerized HTTP service:

```bash
# Deploy locally (for testing)
zenml pipeline deploy pipelines.churn_inference_pipeline.churn_inference_pipeline \
  --name churn-service

# Deploy to cloud (requires cloud deployer setup)
zenml pipeline deploy pipelines.churn_inference_pipeline.churn_inference_pipeline \
  --name churn-service-prod
```

### 4. Test the Deployed Service

Once deployed, you can make predictions via HTTP:

```bash
# Get deployment URL
zenml deployment list

# Make prediction via curl
curl -X POST <deployment-url>/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "parameters": {
      "customer_features": {
        "account_length": 24,
        "customer_service_calls": 2,
        "monthly_charges": 45.0,
        "total_charges": 1080.0,
        "has_internet_service": 1,
        "has_phone_service": 1,
        "contract_length": 12,
        "payment_method_electronic": 0
      }
    }
  }'
```

## 🔧 Advanced Usage

### Model Retraining

Retrain with different parameters:

```bash
# Train with more data
python run.py --train --samples 10000

# The new model will automatically be tagged as "production"
# and the inference service will use the latest version
```

### Deployment Configuration

Configure deployment settings for different environments:

```python
# In inference_pipeline.py, modify settings for your needs
settings={
    "deployer.gcp": {
        "memory": "2Gi",
        "cpu": 2,
        "min_replicas": 1,
        "max_replicas": 10,
        "location": "us-central1"
    },
    "deployer.aws": {
        "cpu": 1024,
        "memory": 2048,
        "min_replicas": 1,
        "max_replicas": 5
    }
}
```

### Monitoring and Observability

Every prediction request creates a ZenML run with full lineage:

```bash
# View recent predictions
zenml pipeline runs list --pipeline churn_inference_pipeline

# Inspect a specific prediction
zenml pipeline runs describe <run-id>

# View model performance over time
zenml artifact versions list --name churn-model
```

## 📈 Model Performance

The example uses a Random Forest classifier with the following typical performance:

- **Accuracy**: ~85-90% on synthetic data
- **Features**: 8 customer attributes
- **Training Time**: ~2-5 seconds on 1000 samples
- **Inference Time**: ~50-100ms per prediction
- **Model Size**: ~200KB serialized

## 🔄 Production Workflow

1. **Development**: Train and test models locally
2. **Staging**: Deploy to staging environment for validation
3. **Production**: Deploy to production with monitoring
4. **Monitoring**: Track prediction performance and model drift
5. **Retraining**: Update model with new data as needed

## 🛠️ Deployment Options

This example supports multiple deployment targets:

| Target | Use Case | Setup |
|--------|----------|-------|
| **Local** | Development/testing | Built-in, no setup required |
| **Docker** | Local containerized testing | `zenml deployer register docker -f docker` |
| **GCP Cloud Run** | Serverless production | Requires GCP project and authentication |
| **AWS App Runner** | Serverless production | Requires AWS account and IAM setup |

## 📝 Key Concepts Demonstrated

### 1. **Pipeline Separation**
- **Training Pipeline**: Batch job for model development
- **Inference Pipeline**: Real-time service for production

### 2. **Artifact Management**
- Models are automatically versioned and tagged
- Production models are clearly identified
- Full lineage from training data to predictions

### 3. **Deployment Patterns**
- Convert any pipeline into a deployable service
- Configure resources and scaling per environment
- Built-in health checks and monitoring

### 4. **Model Serving**
- Load production models automatically
- Handle errors gracefully
- Return structured prediction results

## 🤝 Next Steps

- **Extend the Model**: Add more features or try different algorithms
- **Add Monitoring**: Implement model drift detection
- **Scale Up**: Deploy to production cloud environments
- **Integrate**: Connect to your existing data sources and applications

For more advanced examples, check out:
- [Weather Agent](../weather_agent/) - For LLM-powered agent deployments
- [Quickstart](../quickstart/) - For hybrid AI/ML workflows

---

**Questions?** Check the [ZenML Documentation](https://docs.zenml.io) or join our [Slack Community](https://zenml.io/slack).