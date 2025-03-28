---
description: Troubleshooting tips for your ZenML deployment
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Troubleshoot the deployed server

In this document, we will go over some common issues that you might face when deploying ZenML and how to solve them.

## Viewing logs

Analyzing logs is a great way to debug issues. Depending on whether you have a Kubernetes (using Helm or `zenml deploy`)
or a Docker deployment, you can view the logs in different ways.

{% tabs %}
{% tab title="Kubernetes" %}
If you are using Kubernetes, you can view the logs of the ZenML server using the following method:

* Check all pods that are running your ZenML deployment.

```bash
kubectl -n <KUBERNETES_NAMESPACE> get pods
```

* If you see that the pods aren't running, you can use the command below to get the logs for all pods at once.

```bash
kubectl -n <KUBERNETES_NAMESPACE> logs -l app.kubernetes.io/name=zenml
```

Note that the error can either be from the `zenml-db-init` container that connects to the MySQL database or from
the `zenml` container that runs the server code. If the get pods command shows that the pod is failing in the `Init`
state then use `zenml-db-init` as the container name, otherwise use `zenml`.

```bash
kubectl -n <KUBERNETES_NAMESPACE> logs -l app.kubernetes.io/name=zenml -c <CONTAINER_NAME>
```

{% hint style="info" %}
You can also use the `--tail` flag to limit the number of lines to show or the `--follow` flag to follow the logs in
real-time.
{% endhint %}
{% endtab %}

{% tab title="Docker" %}
If you are using Docker, you can view the logs of the ZenML server using the following method:

* If you used the `zenml login --local --docker` CLI command to deploy the Docker ZenML server, you can check the logs with the
  command:

  ```shell
  zenml logs -f
  ```
* If you used the `docker run` command to manually deploy the Docker ZenML server, you can check the logs with the
  command:

  ```shell
  docker logs zenml -f
  ```
* If you used the `docker compose` command to manually deploy the Docker ZenML server, you can check the logs with the
  command:

  ```shell
  docker compose -p zenml logs -f
  ```

{% endtab %}
{% endtabs %}

## Fixing database connection problems

If you are using a MySQL database, you might face issues connecting to it. The logs from the `zenml-db-init` container
should give you a good idea of what the problem is. Here are some common issues and how to fix them:

* If you see an error like `ERROR 1045 (28000): Access denied for user <USER> using password YES`, it means that the
  username or password is incorrect. Make sure that the username and password are correctly set for whatever deployment
  method you are using.
* If you see an error like `ERROR 2003 (HY000): Can't connect to MySQL server on <HOST> (<IP>)`, it means that the host
  is incorrect. Make sure that the host is correctly set for whatever deployment method you are using.

You can test the connection and the credentials by running the following command from your machine:

```bash
mysql -h <HOST> -u <USER> -p
```

{% hint style="info" %}
If you are using a Kubernetes deployment, you can use the `kubectl port-forward` command to forward the MySQL port to
your local machine. This will allow you to connect to the database from your machine.
{% endhint %}

## Fixing database initialization problems

If you’ve migrated from a newer ZenML version to an older version and see errors like `Revision not found` in
your `zenml-db-init` logs, one way out is to drop the database and create a new one with the same name.

* Log in to your MySQL instance.

  ```bash
  mysql -h <HOST> -u <NAME> -p
  ```
* Drop the database for the server.

  ```sql
  drop database <NAME>;
  ```
* Create the database with the same name.

  ```sql
  create database <NAME>;
  ```
* Restart the Kubernetes pods or the docker container running your server to trigger the database initialization again.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
