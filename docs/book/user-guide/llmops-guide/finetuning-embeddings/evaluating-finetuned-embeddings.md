---
description: Evaluate finetuned embeddings and compare to original base embeddings.
---

Now that we've finetuned our embeddings, we can evaluate them and compare to the
base embeddings. We have all the data saved and versioned already, and we will
reuse the same MatryoshkaLoss function for evaluation.

In code, our evaluation steps are easy to comprehend. Here, for example, is the
base model evaluation step:

```python
from zenml import log_model_metadata, step

def evaluate_model(
    dataset: DatasetDict, model: SentenceTransformer
) -> Dict[str, float]:
    """Evaluate the given model on the dataset."""
    evaluator = get_evaluator(
        dataset=dataset,
        model=model,
    )
    return evaluator(model)

@step
def evaluate_base_model(
    dataset: DatasetDict,
) -> Annotated[Dict[str, float], "base_model_evaluation_results"]:
    """Evaluate the base model on the given dataset."""
    model = SentenceTransformer(
        EMBEDDINGS_MODEL_ID_BASELINE,
        device="cuda" if torch.cuda.is_available() else "cpu",
    )

    results = evaluate_model(
        dataset=dataset,
        model=model,
    )

    # Convert numpy.float64 values to regular Python floats
    # (needed for serialization)
    base_model_eval = {
        f"dim_{dim}_cosine_ndcg@10": float(
            results[f"dim_{dim}_cosine_ndcg@10"]
        )
        for dim in EMBEDDINGS_MODEL_MATRYOSHKA_DIMS
    }

    log_model_metadata(
        metadata={"base_model_eval": base_model_eval},
    )

    return results
```

We log the results for our core Matryoshka dimensions as model metadata to ZenML
within our evaluation step. This will allow us to inspect these results from
within [the Model Control Plane](https://docs.zenml.io/how-to/use-the-model-control-plane) (see
below for more details). Our results come in the form of a dictionary of string
keys and float values which will, like all step inputs and outputs, be
versioned, tracked and saved in your artifact store.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>


