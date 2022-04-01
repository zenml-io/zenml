# Materializers in ZenML
The precise way that data passes between the steps is dictated by `materializers`. The data that flows through steps 
are stored as artifacts and artifacts are stored in artifact stores. The logic that governs the reading and writing of 
data to and from the artifact stores lives in the materializers. In order to control more precisely how data 
flows between steps, one can simply create a custom materializer by sub-classing the `BaseMaterializer` class.

## 🗺 Overview

Within this tutorial you'll get a quick overview of materializers in ZenML. 

## ⚡ Get started immediately - [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/zenml-io/zenml/blob/feature/ENG-634-beautify-examples/examples/Zenml_Basics/custom_materializer/materializers_in_zenml.ipynb)

We've written a notebook on caching that you can get started on immediately on [Google Colab](https://colab.research.google.com/github/zenml-io/zenml/blob/feature/ENG-634-beautify-examples/examples/Zenml_Basics/custom_materializer/materializers_in_zenml.ipynb).

## 💻 Run it locally
### 📃 Pre-requisites

```shell
# install CLI
pip install zenml 

# pull example if you don't have it locally already
zenml example pull custom_materializer
cd zenml_examples/zenml_basics/custom_materializer
```

### ▶ Run the code

We offer two ways for you to try this out locally:

1. Start the notebook server of your choice and dive right into the [code](materializers_in_zenml.ipynb)

2. Have a look at our [materializers_in_zenml.py](materializers_in_zenml.py) script and feel free to run it 
using:

```bash
python materializers_in_zenml.py
```

Feel free to comment out or change the code of the `MyMaterializer` to see how it affects the pipeline run.

### 👓 Learn more

Check out our [Docs](tbd) to  find more about caching and ZenML
