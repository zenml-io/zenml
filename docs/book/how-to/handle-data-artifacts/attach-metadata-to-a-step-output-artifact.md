# Attach metadata to a step output/ artifact

<pre class="language-python"><code class="lang-python">from sklearn.base import RegressorMixin

<strong>from zenml import log_artifact_metadata, step
</strong>
@step
def model_evaluation() -> Tuple[
    Annotated[RegressorMixin, "model"], Annotated[float, "r2_score"]
]:
    """Evaluates the Model attaches the metrics to the model."""
    
    classifier = ...
    r2_score, mse, rmse = ...

    log_artifact_metadata(
        metadata={
            "metrics": {
                "r2_score": float(r2_score),
                "mse": float(mse),
                "rmse": float(rmse),
            }
        }
        artifact_name="model",  # Reflects the name in the output annotation (see above)

    ) # Attaches this metadata to the model
    
    return classifier, r2_score
</code></pre>
