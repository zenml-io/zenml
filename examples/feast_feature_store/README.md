# Instructions for use

```bash
# install zenml
zenml integration install feast -y --uv
zenml feature-store update ...
zenml stack set feast

cd examples/feast_feature_store
zenml init

# setup feast
cd feast_feature_repo
feast apply

# inspect the data we just loaded into the feature store
feast ui

# run the pipeline
cd ..
python run.py

# check out the code + dashboard
