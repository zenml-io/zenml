#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""ZenML Server Implementation.

The ZenML Server is a centralized service meant for use in a collaborative
setting in which stacks, stack components, flavors, pipeline and pipeline runs
can be shared over the network with other users.

You can use the `zenml server up` command to spin up ZenML server instances
that are either running locally as daemon processes or docker containers, or
to deploy a ZenML server remotely on a managed cloud platform. The other CLI
commands in the same `zenml server` group can be used to manage the server
instances deployed from your local machine.

To connect the local ZenML client to one of the managed ZenML servers, call
`zenml server connect` with the name of the server you want to connect to.
"""
