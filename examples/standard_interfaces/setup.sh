#!/usr/bin/env bash

set -Eeo pipefail

download_data () {
  wget -O diabetes.csv https://gist.githubusercontent.com/AlexejPenner/0564d4cea7b7685f9ef119b56ff05475/raw/2c1fbd64b6624e251b53d9ba6d93b176a5bef050/diabetes.csv
  export data='diabetes.csv'
}

pre_run () {
  zenml integration install sklearn
  zenml integration install tensorflow
}

pre_run_forced () {
  zenml integration install sklearn -f
  zenml integration install tensorflow -f
}