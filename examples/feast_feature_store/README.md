# Instructions for use

```bash
# install zenml
zenml integration install gcp feast -y --uv
zenml stack set feast

cd examples/feast_feature_store
zenml init

# setup feast
cd feast_feature_repo
feast apply


