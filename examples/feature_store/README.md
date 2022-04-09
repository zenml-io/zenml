# 🗂 Get your data from a Feature Store

Feature stores allow data teams to serve data via an offline store and an online low-latency store where data is kept in sync between the two. It also offers a centralized registry where features (and feature schemas) are stored for use within a team or wider organization.

As a data scientist working on training your model, your requirements for how you access your batch / 'offline' data will almost certainly be different from how you access that data as part of a real-time or online inference setting. Feast solves the problem of developing [train-serve skew](https://ploomber.io/blog/train-serve-skew/) where those two sources of data diverge from each other.

Feature stores are a relatively recent addition to commonly-used machine learning stacks. [Feast](https://feast.dev/) is a leading open-source feature store, first developed by [Gojek](https://www.gojek.com/en-id/) in collaboration with Google.

This example runs locally, using a (local) [Redis](https://redis.com/) server to simulate the online part of the store.

## 🗺 Features Stores & ZenML

There are two core functions that feature stores enable: access to data from an offline / batch store for training and access to online data at inference time. The ZenML Feast integration enables both of these behaviors.

This example showcases a local implementation where the whole setup runs on a single machine, but we assume that users of the ZenML Feast integration will have set up their own feature store already. We encourage users to check out [Feast's documentation](https://docs.feast.dev/) and [guides](https://docs.feast.dev/how-to-guides/) on how to setup your offline and online data sources via the configuration `yaml` file.

This example currently shows the offline data retrieval part of what Feast enables. (Online data retrieval is currently possible in a local / simple setting, but we don't currently support using the online data serving in the context of a deployed model or as part of model deployment.)

## 🧰 How the example is implemented

This example has two simple steps, showing how you can access historical (batch / offline) data from a local file source.

# 🖥 Run it locally

## 👣 Step-by-Step `feature-store` run

### 📄 Prerequisites

In order to run this example, you need to install and initialize ZenML:

```shell
# install CLI
pip install zenml

# install ZenML integration
zenml integration install feast
```

Since this example is built around a [Redis](https://redis.com/) use case, a
Python package to interact with Redis will get installed alongside Feast, but
you will still first need to install Redis yourself. See
[this page](https://redis.com/blog/feast-with-redis-tutorial-for-machine-learning/)
for some instructions on how to do that on your operating system.

You will then need to run a Redis server in the background in order for this
example to work. You can either use the `redis-server` command in your terminal
(which will run a continuous process until you CTRL-C out of it), or you can run
the daemonized version:

```shell
redis-server --daemonize yes

# verify it is running (Unix machines)
ps aux | grep redis-server
```

Once Redis is up and running, you can access the example code and setup in the
following way:

```shell
# pull example
zenml example pull feature_store
cd zenml_examples/feature_store

# Initialize ZenML repo
zenml init
```

You then should setup the Feast feature store stack component and activate it as
part of your current working stack:

```shell
# register the feature store stack component
zenml feature-store register feast_store -t feast --feast_repo="./feast_feature_repo"

# register the sagemaker stack
zenml stack register fs_stack -m default -o default -a default -f feast_store

# activate the stack
zenml stack set fs_stack

# view the current active stack
zenml stack describe
```

The final step is to apply the configuration of your feature store (listed in
the `feast_feature_repo/feature_store.yaml` file) by entering the following
commands:

```shell
cd feast_feature_repo
feast apply
```

You should see some acknowledgment that an entity and a feature view has been
registered and that infrastructure has been deployed.

### ▶️ Run the Code

Now we're ready. Execute:

```bash
cd ..
python run.py
```

### 🧽 Clean up

In order to clean up, delete the remaining ZenML references.

```shell
rm -rf zenml_examples
```

If you ran the Redis server as a daemon process, you'll want to find the process ID (using `ps aux | grep redis-server`) and you can `kill` the process from the terminal.

# 📜 Learn more

Our docs regarding the Feast feature store integration can be found [here](https://docs.zenml.io/features/feature-store).