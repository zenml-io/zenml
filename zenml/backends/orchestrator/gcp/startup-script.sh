#!/usr/bin/env bash

# get image name and container parameters from the metadata
IMAGE_NAME=$(curl http://metadata.google.internal/computeMetadata/v1/instance/attributes/image_name -H "Metadata-Flavor: Google")

CONTAINER_PARAMS=$(curl http://metadata.google.internal/computeMetadata/v1/instance/attributes/container_params -H "Metadata-Flavor: Google")

MLMD_TARGET=$(curl http://metadata.google.internal/computeMetadata/v1/instance/attributes/mlmd_target -H "Metadata-Flavor: Google")

sudo HOME=/home/root docker run -d --net=host -p 127.0.0.1:3306:3306 --rm gcr.io/cloudsql-docker/gce-proxy:1.16 /cloud_sql_proxy -instances=${MLMD_TARGET}=tcp:0.0.0.0:3306

# Run! The logs will go to stack driver
sudo HOME=/home/root  docker run --log-driver=gcplogs --net=host ${IMAGE_NAME} ${CONTAINER_PARAMS}

# Get the zone
zoneMetadata=$(curl "http://metadata.google.internal/computeMetadata/v1/instance/zone" -H "Metadata-Flavor:Google")
# Split on / and get the 4th element to get the actual zone name
IFS=$'/'
zoneMetadataSplit=($zoneMetadata)
ZONE="${zoneMetadataSplit[3]}"

# Run compute delete on the current instance. Need to run in a container
# because COS machines don't come with gcloud installed
docker run --entrypoint "gcloud" google/cloud-sdk:alpine compute instances delete ${HOSTNAME}  --delete-disks=all --zone=${ZONE}