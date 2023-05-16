#!/usr/bin/env bash

pre_run () {
  zenml integration install sklearn
}

pre_run_forced () {
  zenml integration install sklearn -y
}
