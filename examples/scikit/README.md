# Get up and running quickly
This is the quickstart example that runs a `TrainingPipeline` to train a Scikit-based classifier on the 
[Pime Indian Diabetes dataset](https://www.kaggle.com/uciml/pima-indians-diabetes-database).

### Pre-requisites
In order to run this example, you need to install and initialize ZenML:

```bash
pip install "zenml"
zenml example pull scikit
cd zenml_examples/scikit
git init
zenml init
```

### Run the project
Now we're ready. Execute:

```bash
python run.py
```


### Clean up
In order to clean up, in the root of your repo, delete the remaining zenml references.

```python
rm -r .zenml
rm -r pipelines
```

## Caveats
Full scikit support is still in development. For now, please use `StandardPreprocesser` based 
preprocessing and no evaluator or deploy steps with Scikit trainers.

## Next Steps
Try [creating your own custom pytorch trainer](https://docs.zenml.io/getting-started/creating-custom-logic.html)!