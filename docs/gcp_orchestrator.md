* Put a file called Dockerfile in the root of your repository
* The Dockerfile should begin with:
```dockerfile
FROM eu.gcr.io/core-engine/zenml/base:0.0.1
```
docker tag zenml:0.0.1 eu.gcr.io/core-engine/zenml/base:0.0.1


# ZenML config
# Set your GOOGLE_APPLICATION_CREDENTIALS beforehand. These should hav ethe following permissions:
* Service Account User permission
* Compute Engine Admin

```bash
zenml config artifacts set gs://path/to/artifact/store
```

```
# start a proxy
./cloud_sql_proxy -instances=core-engine:europe-west1:mlmetadata=tcp:3306 -credential_file=$GOOGLE_APPLICATION_CREDENTIALS
```

```
# change metadata store
zenml config metadata set mysql --port="3306" --host="127.0.0.1" --password="JjIwd3u7JbtveBgu" --username="mlmetadata" --database="zenml_pgo_test"
```