# 🗂 Get your data from a Feature Store

<!-- basic introduction paragraph

- what is a feature store
- what problem does it solve
- what specific combo have we integrated with? -->

## 🗺 Overview: Features Stores & ZenML

<!-- - how to think about a feature store
- what is it used for?
- components / architecture of a feature store
  - offline / batch serving
  - online serving
- The main abstractions you need to think of / how do we help you?:
  - getting offline features
  - getting online features
- caveats about our integration
  - this example runs locally
  - we assume you have a feature store already if you want to use it in
    production (ZenML doesn't currently help you set that all up)
  - online serving doesn't work in tandem with deployed models currently
- This example, and what features of features it showcases / what you can do
  with the ZenML feature store integration -->

## 🧰 How the example is implemented

<!-- Showcase the code and explain how it works
Maybe a visual diagram showing the various parts of it? -->

# 🖥 Run it locally

## ⏩ SuperQuick `feature-store` run

If you're really in a hurry, and you want just to see this example pipeline run,
without wanting to fiddle around with all the individual installation and
configuration steps, just run the following:

```shell
zenml example run feature_store
```

## 👣 Step-by-Step

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

If you ran the Redis server as a daemon process, you'll want to find the process
ID (using `ps aux | grep redis-server`) and you can `kill` the process from the
terminal.

# 📜 Learn more

Our docs regarding the Feast feature store integration can be found
[here](https://docs.zenml.io/features/feature-store).
