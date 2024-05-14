# Attach metrics to a step output/ artifact

<pre class="language-python"><code class="lang-python">from sklearn.base import RegressorMixin

<strong>from zenml import log_artifact_metadata, step
</strong>
@step()
def model_evaluation() -> Annotated[RegressorMixin, "model"]:
    """Evaluates the Model attaches the metrics to the model."""

    r2_score, mse, rmse = ...

    log_artifact_metadata(
        metadata={
            "metrics": {
                "r2_score": float(r2_score),
                "mse": float(mse),
                "rmse": float(rmse),
            }
        }
    ) # Attaches this metadata to the model
    return model
</code></pre>
