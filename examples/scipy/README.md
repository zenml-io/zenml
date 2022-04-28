# [SciPy](https://scipy.org/) sparse matrices in ZenML

An elementary data structure widely used in `sklearn` to store sparse arrays.

# 🖥 Run it locally

## ⏩ SuperQuick `scipy` run

If you're really in a hurry, and you want just to see this example pipeline run,
without wanting to fiddle around with all the individual installation and
configuration steps, just run the following:

```shell
zenml example run scipy
```

### 📄 Prerequisites

In order to run this example, you need to install and initialize ZenML:

```shell
# install CLI
pip install zenml

# install ZenML integrations
zenml integration install scipy

# pull example
zenml example pull scipy
cd zenml_examples/scipy

# Initialize ZenML repo
zenml init
```

### ▶️ Run the Code

Now we're ready. Execute:

```bash
python run.py
```

### 🧽 Clean up

In order to clean up, delete the remaining ZenML references.

```shell
rm -rf zenml_examples
```
