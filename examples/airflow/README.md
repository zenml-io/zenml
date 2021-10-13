# Get in production with Airflow
Set up Airflow

### Pre-requisites
In order to run this example, you need to install and initialize ZenML:

```bash
# install CLI
pip install zenml
pip install apache-airflow

# initialize CLI
cd ~
mkdir zenml_examples
git clone https://github.com/zenml-io/zenml.git
cp -r zenml/examples/airflow zenml_examples
cd zenml_examples/airflow
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
rm -rf ~/zenml_examples
rm -rf ~/zenml
```
