from zenml.pipelines import pipeline


@pipeline
def inference_pipeline(
    inference_data_loader,
    prediction_service_loader,
    predictor,
    training_data_loader,
    skew_comparison,
    drift_detector,
):
    """Inference pipeline with skew and drift detection."""
    inference_data = inference_data_loader()
    model_deployment_service = prediction_service_loader()
    predictor(model_deployment_service, inference_data)
    training_data, _, _, _ = training_data_loader()
    reference, comparison = skew_comparison(training_data, inference_data)
    drift_detector(reference, comparison)
