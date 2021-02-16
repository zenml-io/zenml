#
# Copyright (c) maiot GmbH 2021. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied. See the License for the specific language governing
# permissions and limitations under the License.
#
#! /usr/bin/env bash

# bash way of splitting of the current directory name
CWD=${PWD##*/}
ZENML_DIR=".zenml"
GIT=".git"
PIPELINES="pipelines"

if [ -d "$ZENML_DIR" ] || [ -d "$PIPELINES" ] || [ -d "$GIT" ]; then
  # Take action if $DIR exists. #
  echo "Either the .zenml, .git or pipelines directory exists already. Make sure to run tests in a clean directory."
  exit 1
fi

# make sure that the current directory is tests, otherwise complain
if [ "$CWD" != "tests" ]; then
  echo "Make sure to run ZenML tests directly from the tests directory."
  exit 1
fi

git init
git add .
git commit -m 'test commit'

python generate_test_pipelines.py

pytest ../zenml

PYTEST_EXIT=$?

rm -rf $GIT
rm -rf $ZENML_DIR
rm -rf $PIPELINES
rm .gitignore

exit $PYTEST_EXIT