# Get up and running quickly
Our goal here is to help you to get the first practical experience with our tool and give you a brief overview on some basic functionalities of ZenML.

The quickest way to get started is to create a simple pipeline. We'll be using the [MNIST](http://yann.lecun.com/exdb/mnist/) dataset (originally developed by Yann LeCun and others) digits, and then later the [Fashion MNIST](https://github.com/zalandoresearch/fashion-mnist) dataset developed by Zalando.

If you want to run this notebook in an interactive environment, feel free to run it in a [Google Colab version](https://colab.research.google.com/drive/1evoEqzKPLQwCss4LtDVKoIda8fJb3B1O?usp=sharing).

### Pre-requisites
In order to run this example, you need to install and initialize ZenML:

```bash
# install CLI
pip install zenml
pip install tensorflow

# initialize CLI
cd ~
mkdir zenml_examples
git clone https://github.com/zenml-io/zenml.git
cp -r zenml/examples/quickstart zenml_examples
cd zenml_examples/quickstart
git init
zenml init
```

### Run the project
Now we're ready. Execute:

```bash
python quickstart.py
```

Or just a jupyter notebook
```bash
jupyter notebook  # jupyter must be installed
```

Or check out a [Google Colab version](https://colab.research.google.com/drive/1evoEqzKPLQwCss4LtDVKoIda8fJb3B1O?usp=sharing) to test it out immediately.

### Clean up
In order to clean up, in the root of your repo, delete the remaining zenml references.

```python
rm -rf ~/zenml_examples
rm -rf ~/zenml
```
