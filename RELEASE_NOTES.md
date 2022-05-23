# 0.8.0

## 🧘‍♀️ Extensibility is our middle name

* The ability to register custom stack component flavors (and renaming types to
  flavor (Registering custom stack component flavors by @bcdurak in
  https://github.com/zenml-io/zenml/pull/541)
* The ability to easily extend orchestrators
* Documentation for stacks, stack components and flavors by @bcdurak in
  https://github.com/zenml-io/zenml/pull/607
* Allow configuration of s3fs by @schustmi in
  https://github.com/zenml-io/zenml/pull/532
* Ability to use SSL to connect to MySQL clients (That allows for connecting to
  Cloud based MYSQL deployments)
* New MySQL metadata stores by @bcdurak in
  https://github.com/zenml-io/zenml/pull/580!
* Docs and messaging change
* Make Orchestrators more extensible and simplify the interface by @AlexejPenner
  in https://github.com/zenml-io/zenml/pull/581
* S3 Compatible Artifact Store and materializers file handling by @safoinme in
  https://github.com/zenml-io/zenml/pull/598

## Manage your stacks

* Update stack and stack components via the CLI by @strickvl in
  https://github.com/zenml-io/zenml/pull/497
* Add `stack delete` confirmation prompt by @strickvl in
  https://github.com/zenml-io/zenml/pull/548
* Add `zenml stack export` and `zenml stack import` commands by @fa9r in
  https://github.com/zenml-io/zenml/pull/560

## Collaboration

* User management by @schustmi in https://github.com/zenml-io/zenml/pull/500

## CLI improvements

* CLI speed improvement by @bcdurak in
  https://github.com/zenml-io/zenml/pull/567
* Ensure `rich` CLI displays full text and wraps table text by @strickvl in
  https://github.com/zenml-io/zenml/pull/577
* Add CLI command to remove stack component attribute by @strickvl in
  https://github.com/zenml-io/zenml/pull/590
* Beautify CLI by grouping commands list into tags by @safoinme in
  https://github.com/zenml-io/zenml/pull/546

## New integrations:

* Add PyTorch example by @htahir1 in https://github.com/zenml-io/zenml/pull/559
* Added GCP as secret manager by @AlexejPenner in
  https://github.com/zenml-io/zenml/pull/556

## Documentation / ZenBytes etc

* ZenBytes update (and ZenFiles)
* Beautification of Examples by @AlexejPenner in
  https://github.com/zenml-io/zenml/pull/491
* Document global configuration and repository by @stefannica in
  https://github.com/zenml-io/zenml/pull/579
* ZenML Collaboration docs by @stefannica in
  https://github.com/zenml-io/zenml/pull/597

## ➕ Other Updates, Additions and Fixes

* Experiment tracker stack components by @htahir1 in
  https://github.com/zenml-io/zenml/pull/530
* Secret Manager improvements and Seldon Core secret passing by @stefannica in
  https://github.com/zenml-io/zenml/pull/529
* Pipeline run tracking by @schustmi in
  https://github.com/zenml-io/zenml/pull/601
* Stream model deployer logs through CLI by @stefannica in
  https://github.com/zenml-io/zenml/pull/557
* Fix various usability bugs by @stefannica in
  https://github.com/zenml-io/zenml/pull/561
* Replace `-f` and `--force` with `-y` and `--yes` by @strickvl in
  https://github.com/zenml-io/zenml/pull/566
* Make it easier to submit issues by @htahir1 in
  https://github.com/zenml-io/zenml/pull/571
* Sync the repository and local store with the disk configuration files and
  other fixes by @stefannica in https://github.com/zenml-io/zenml/pull/588
* Add ability to give in-line pip requirements for pipeline by @strickvl in
  https://github.com/zenml-io/zenml/pull/583
* Fix evidently visualizer on Colab by @fa9r in
  https://github.com/zenml-io/zenml/pull/592

## 🙌 Community Contributions

* @Ankur3107 made their first contribution in
  https://github.com/zenml-io/zenml/pull/467
* @MateusGheorghe made their first contribution in
  https://github.com/zenml-io/zenml/pull/523
* Added support for scipy sparse matrices by @avramdj in
  https://github.com/zenml-io/zenml/pull/534

# 0.7.3

## 📊 Experiment Tracking Components

[PR #530](https://github.com/zenml-io/zenml/pull/530) adds a new stack component to ZenMLs ever-growing list:  `experiment_trackers` allows users to configure your experiment tracking tools with ZenML. Examples of experiment tracking tools are [Weights&Biases](https://wandb.ai), [mlflow](https://mlflow.org), [Neptune](https://neptune.ai), amongst others.

Existing users might be confused, as ZenML has had MLflow and wandb support for a while now without such a component. However, this component allows uses more control over the configuration of MLflow and wandb with the new `MLFlowExperimentTracker` and 
 `WandbExperimentTracker` components. This allows these tools to work in more scenarios than the currently limiting local use-cases.

## 🔎 XGBoost and LightGBM support

[XGBoost](https://xgboost.readthedocs.io/en/stable/) and [LightGBM](https://lightgbm.readthedocs.io/) are one of the most widely used boosting algorithm libraries out there. This release adds materializers for native objects for each library.

Check out [both examples here](https://github.com/zenml-io/zenml/tree/main/examples) and PR's [#544](https://github.com/zenml-io/zenml/pull/544) and [#538](https://github.com/zenml-io/zenml/pull/538) for more details.

## 📂 Parameterized S3FS support to enable non-AWS S3 storage (minio, ceph)

A big complaint of the [S3 Artifact Store](https://github.com/zenml-io/zenml/blob/main/src/zenml/integrations/s3/artifact_stores/s3_artifact_store.py) integration was that it was hard to parameterize it in a way that it supports non-AWS S3 storage like [minio](https://min.io/) and [ceph](https://docs.ceph.com/en/latest/radosgw/s3/). The latest release 
 made this super simple! When you want to register an S3ArtifactStore from the CLI, you can now pass in  `client_kwargs`, `config_kwargs` or `s3_additional_kwargs` as a JSON string. For example:

```shell
zenml artifact-store register my_s3_store --type=s3 --path=s3://my_bucket \
    --client_kwargs='{"endpoint_url": "http://my-s3-endpoint"}'
```

See PR [#532](https://github.com/zenml-io/zenml/pull/532) for more details.

## 🧱 New CLI commands to update stack components

We added functionality to allow users to update stacks that already exist. This shows the basic workflow:

```shell
zenml orchestrator register local_orchestrator2 -t local
zenml stack update default -o local_orchestrator2
zenml stack describe default
zenml container-registry register local_registry --type=default --uri=localhost:5000
zenml container-registry update local --uri='somethingelse.com'
zenml container-registry rename local local2
zenml container-registry describe local2
zenml stack rename default new_default
zenml stack update new_default -c local2
zenml stack describe new_default
zenml stack remove-component -c
```
More details are in the [CLI docs](https://apidocs.zenml.io/0.7.3/cli/). 
Users can add new stack components to a pre-existing stack, or they can modify 
already-present stack components. They can also rename their stack and individual stack components.

## 🐛 Seldon Core authentication through ZenML secrets

The Seldon Core Model Deployer stack component was updated in this release to allow the configuration of ZenML secrets with credentials that authenticate Seldon to access the Artifact Store. The Seldon Core integration provides 3 different secret schemas for the 3 flavors of Artifact Store: AWS, GCP, and Azure, but custom secrets can be used as well. For more information on how to use this feature please refer to our [Seldon Core deployment example](https://github.com/zenml-io/zenml/tree/main/examples/seldon_deployment).

Lastly, we had numerous other changes such as ensuring the PyTorch materializer works across all artifact stores 
and the Kubeflow Metadata Store can be easily queried locally.

## Detailed Changelog
* Fix caching & `mypy` errors by @strickvl in https://github.com/zenml-io/zenml/pull/524
* Switch unit test from local_daemon to multiprocessing by @jwwwb in https://github.com/zenml-io/zenml/pull/508
* Change Pytorch materializer to support remote storage by @safoinme in https://github.com/zenml-io/zenml/pull/525
* Remove TODO from Feature Store `init` docstring by @strickvl in https://github.com/zenml-io/zenml/pull/527
* Fixed typo predicter -> predictor by @MateusGheorghe in https://github.com/zenml-io/zenml/pull/523
* Fix mypy errors by @strickvl in https://github.com/zenml-io/zenml/pull/528
* Replaced old local_* logic by @htahir1 in https://github.com/zenml-io/zenml/pull/531
* capitalize aws username in ECR docs by @wjayesh in https://github.com/zenml-io/zenml/pull/533
* Build docker base images quicker after release by @schustmi in https://github.com/zenml-io/zenml/pull/537
* Allow configuration of s3fs by @schustmi in https://github.com/zenml-io/zenml/pull/532
* Update contributing and fix ci badge to main by @htahir1 in https://github.com/zenml-io/zenml/pull/536
* Added XGboost integration by @htahir1 in https://github.com/zenml-io/zenml/pull/538
* Added fa9r to .github/teams.yml. by @fa9r in https://github.com/zenml-io/zenml/pull/539
* Secret Manager improvements and Seldon Core secret passing by @stefannica in https://github.com/zenml-io/zenml/pull/529
* User management by @schustmi in https://github.com/zenml-io/zenml/pull/500
* Update stack and stack components via the CLI by @strickvl in https://github.com/zenml-io/zenml/pull/497
* Added lightgbm integration by @htahir1 in https://github.com/zenml-io/zenml/pull/544
* Fix the Kubeflow metadata store and other stack management improvements by @stefannica in https://github.com/zenml-io/zenml/pull/542
* Experiment tracker stack components by @htahir1 in https://github.com/zenml-io/zenml/pull/530

## New Contributors
* @MateusGheorghe made their first contribution in https://github.com/zenml-io/zenml/pull/523
* @fa9r made their first contribution in https://github.com/zenml-io/zenml/pull/539

**Full Changelog**: https://github.com/zenml-io/zenml/compare/0.7.2...0.7.3
**Blog Post**: https://blog.zenml.io/zero-seven-two-three-release/

# 0.7.2

0.7.2 is a minor release which quickly patches some bugs found in the last
release to do with Seldon and Mlflow deployment.

This release also features initial versions of two amazing new integrations:
[HuggingFace](https://huggingface.co/) and [Weights&Biases](https://wandb.ai/site)!

- HuggingFace models are now supported to be passed through ZenML pipelines!
- You can now track your pipeline runs with Weights&Biases with the new
`enable_wandb` decorator!

Continuous model deployment with MLflow has been improved with ZenML 0.7.2. A new
MLflow Model Deployer Stack component is now available and needs to be part of
your stack to be able to deploy models:

```bash
zenml integration install mlflow
zenml model-deployer register mlflow --type=mlflow
zenml stack register local_with_mlflow -m default -a default -o default -d mlflow
zenml stack set local_with_mlflow
```

The MLflow Model Deployer is yet another addition to the list of Model Deployers
available in ZenML. You can read more on deploying models to production with MLflow
in our [Continuous Training and Deployment documentation section](https://docs.zenml.io/features/continuous-training-and-deployment) and our [MLflow deployment example](https://github.com/zenml-io/zenml/tree/main/examples/mlflow_deployment).

## What's Changed
* Fix the seldon deployment example by @htahir1 in https://github.com/zenml-io/zenml/pull/511
* Create base deployer and refactor MLflow deployer implementation by @wjayesh in https://github.com/zenml-io/zenml/pull/489
* Add nlp example by @Ankur3107 in https://github.com/zenml-io/zenml/pull/467
* Fix typos by @strickvl in https://github.com/zenml-io/zenml/pull/515
* Bugfix/hypothesis given does not work with fixture by @jwwwb in https://github.com/zenml-io/zenml/pull/513
* Bug: fix long Kubernetes labels in Seldon deployments by @stefannica in https://github.com/zenml-io/zenml/pull/514
* Change prediction_uri to prediction_url in MLflow deployer by @stefannica in https://github.com/zenml-io/zenml/pull/516
* Simplify HuggingFace Integration by @AlexejPenner in https://github.com/zenml-io/zenml/pull/517
* Weights & Biases Basic Integration by @htahir1 in https://github.com/zenml-io/zenml/pull/518

## New Contributors
* @Ankur3107 made their first contribution in https://github.com/zenml-io/zenml/pull/467

**Full Changelog**: https://github.com/zenml-io/zenml/compare/0.7.1...0.7.2

# 0.7.1

The release introduces the [Seldon Core](https://github.com/SeldonIO/seldon-core) ZenML integration, featuring the
*Seldon Core Model Deployer* and a *Seldon Core standard model deployer step*.
The [*Model Deployer*](https://docs.zenml.io/core-concepts#model-deployer)
is a new type of stack component that enables you to develop continuous
model deployment pipelines that train models and continuously deploy them to an
external model serving tool, service or platform. You can read more on deploying models
to production with Seldon Core in our
[Continuous Training and Deployment documentation section](https://docs.zenml.io/features/continuous-training-and-deployment) and our [Seldon Core deployment example](https://github.com/zenml-io/zenml/tree/main/examples/seldon_deployment).

We also see two new integrations with [Feast](https://feast.dev) as ZenML's first feature store integration. Feature stores allow data teams to serve data via an offline store and an online low-latency store where data is kept in sync between the two. It also offers a centralized registry where features (and feature schemas) are stored for use within a team or wider organization. ZenML now supports connecting to a Redis-backed Feast feature store as a stack component integration. Check out the [full example](https://github.com/zenml-io/zenml/tree/release/0.7.1/examples/feature_store) to see it in action! 

0.7.1 also brings  an addition to ZenML training library integrations with [NeuralProphet](https://neuralprophet.com/html/index.html). Check out the new [example](https://github.com/zenml-io/zenml/tree/main/examples) for more details, and the [docs](https://docs.zenml.io) for more further detail on all new features!

## What's Changed
* Add linting of examples to `pre-commit` by @strickvl in https://github.com/zenml-io/zenml/pull/490
* Remove dev-specific entries in `.gitignore` by @strickvl in https://github.com/zenml-io/zenml/pull/488
* Produce periodic mocked data for Segment/Mixpanel by @AlexejPenner in https://github.com/zenml-io/zenml/pull/487
* Abstractions for artifact stores by @bcdurak in https://github.com/zenml-io/zenml/pull/474
* enable and disable cache from runtime config by @AlexejPenner in https://github.com/zenml-io/zenml/pull/492
* Basic Seldon Core Deployment Service by @stefannica in https://github.com/zenml-io/zenml/pull/495
* Parallelise our test suite and make errors more readable by @alex-zenml in https://github.com/zenml-io/zenml/pull/378
* Provision local zenml service by @jwwwb in https://github.com/zenml-io/zenml/pull/496
* bugfix/optional-secrets-manager by @safoinme in https://github.com/zenml-io/zenml/pull/493
* Quick fix for copying folders by @bcdurak in https://github.com/zenml-io/zenml/pull/501
* Pin exact ml-pipelines-sdk version by @schustmi in https://github.com/zenml-io/zenml/pull/506
* Seldon Core model deployer stack component and standard step by @stefannica in https://github.com/zenml-io/zenml/pull/499
* Fix datetime test / bug by @strickvl in https://github.com/zenml-io/zenml/pull/507
* Added NeuralProphet integration by @htahir1 in https://github.com/zenml-io/zenml/pull/504
* Feature Store (Feast with Redis) by @strickvl in https://github.com/zenml-io/zenml/pull/498


# 0.7.0

With ZenML 0.7.0, a lot has been revamped under the hood about how things are stored. Importantly what this means is that ZenML now has [system-wide profiles](https://docs.zenml.io/features/profiles) that let you register stacks to share across several of your projects! If you still want to manage your stacks for each project folder individually, profiles still let you do that as well.

Most projects of any complexity will require passwords or tokens to access data and infrastructure, and for this purpose ZenML 0.7.0 introduces [the Secrets Manager](https://docs.zenml.io/features/secrets) stack component to seamlessly pass around these values to your steps. Our AWS integration also allows you to use AWS Secrets Manager as a backend to handle all your secret persistence needs.

Finally, in addition to the new AzureML and Sagemaker Step Operators that version 0.6.3 brought, this release also adds the ability to [run individual steps on GCP's Vertex AI](https://docs.zenml.io/v/docs/features/step-operators).

Beyond this, some smaller bugfixes and documentation changes combine to make ZenML 0.7.0 a more pleasant user experience.

## What's Changed
* Added quick mention of how to use dockerignore by @AlexejPenner in https://github.com/zenml-io/zenml/pull/468
* Made rich traceback optional with ENV variable by @htahir1 in https://github.com/zenml-io/zenml/pull/472
* Separate stack persistence from repo implementation by @jwwwb in https://github.com/zenml-io/zenml/pull/462
* Adding safoine username to github team by @safoinme in https://github.com/zenml-io/zenml/pull/475
* Fix `zenml stack describe` bug by @strickvl in https://github.com/zenml-io/zenml/pull/476
* ZenProfiles and centralized ZenML repositories by @stefannica in https://github.com/zenml-io/zenml/pull/471
* Add `examples` folder to linting script by @strickvl in https://github.com/zenml-io/zenml/pull/482
* Vertex AI integration and numerous other changes by @htahir1 in https://github.com/zenml-io/zenml/pull/477
* Fix profile handing in the Azure ML step operator by @stefannica in https://github.com/zenml-io/zenml/pull/483
* Copy the entire stack configuration into containers by @stefannica in https://github.com/zenml-io/zenml/pull/480
* Improve some things with the Profiles CLI output by @stefannica in https://github.com/zenml-io/zenml/pull/484
* Secrets manager stack component and interface by @AlexejPenner in https://github.com/zenml-io/zenml/pull/470
* Update schedule.py (#485) by @avramdj in https://github.com/zenml-io/zenml/pull/485 

## New Contributors
* @avramdj in https://github.com/zenml-io/zenml/pull/485 

**Full Changelog**: https://github.com/zenml-io/zenml/compare/0.6.3...0.7.0rc


# 0.6.3

With ZenML 0.6.3, you can now run your ZenML steps on Sagemaker and AzureML! It's normal to have certain steps that require specific hardware on which to run model training, for example, and this latest release gives you the power to switch out hardware for individual steps to support this.

We added a new Tensorboard visualization that you can make use of when using our Kubeflow Pipelines integration. We handle the background processes needed to spin up this interactive web interface that you can use to visualize your model's performance over time.

Behind the scenes we gave our integration testing suite a massive upgrade, fixed a number of smaller bugs and made documentation updates. For a detailed look at what's changed, give [our full release notes](https://github.com/zenml-io/zenml/releases/tag/0.6.3) a glance.

## What's Changed
* Fix typo by @wjayesh in https://github.com/zenml-io/zenml/pull/432
* Remove tabulate dependency (replaced by rich) by @jwwwb in https://github.com/zenml-io/zenml/pull/436
* Fix potential issue with local integration tests by @schustmi in https://github.com/zenml-io/zenml/pull/428
* Remove support for python 3.6 by @schustmi in https://github.com/zenml-io/zenml/pull/437
* Create clean test repos in separate folders by @michael-zenml in https://github.com/zenml-io/zenml/pull/430
* Copy explicit materializers before modifying, log correct class by @schustmi in https://github.com/zenml-io/zenml/pull/434
* Fix typo in mysql password parameter by @pafpixel in https://github.com/zenml-io/zenml/pull/438
* Pytest-fixture for separate virtual environments for each integration test by @AlexejPenner in https://github.com/zenml-io/zenml/pull/405
* Bugfix/fix failing tests due to comments step by @AlexejPenner in https://github.com/zenml-io/zenml/pull/444
* Added --use-virtualenvs option to allow choosing envs to run by @AlexejPenner in https://github.com/zenml-io/zenml/pull/445
* Log whether a step was cached by @strickvl in https://github.com/zenml-io/zenml/pull/435
* Added basic integration tests for remaining examples by @strickvl in https://github.com/zenml-io/zenml/pull/439
* Improve error message when provisioning local kubeflow resources with a non-local container registry. by @schustmi in https://github.com/zenml-io/zenml/pull/442
* Enable generic step inputs and outputs by @schustmi in https://github.com/zenml-io/zenml/pull/440
* Removed old reference to a step that no longer exists by @AlexejPenner in https://github.com/zenml-io/zenml/pull/452
* Correctly use custom kubernetes context if specified by @schustmi in https://github.com/zenml-io/zenml/pull/451
* Fix CLI stack component describe/list commands by @schustmi in https://github.com/zenml-io/zenml/pull/450
* Ignore type of any tfx proto file by @schustmi in https://github.com/zenml-io/zenml/pull/453
* Another boyscout pr on the gh actions by @AlexejPenner in https://github.com/zenml-io/zenml/pull/455
* Upgrade TFX to 1.6.1 by @jwwwb in https://github.com/zenml-io/zenml/pull/441
* Added ZenFiles to README by @htahir1 in https://github.com/zenml-io/zenml/pull/457
* Upgrade `rich` from 11.0 to 12.0 by @strickvl in https://github.com/zenml-io/zenml/pull/458
* Add Kubeflow tensorboard viz and fix tensorflow file IO for cloud back-ends by @stefannica in https://github.com/zenml-io/zenml/pull/447
* Implementing the `explain` subcommand by @bcdurak in https://github.com/zenml-io/zenml/pull/460
* Implement AzureML and Sagemaker step operators by @schustmi in https://github.com/zenml-io/zenml/pull/456

## New Contributors
* @pafpixel made their first contribution in https://github.com/zenml-io/zenml/pull/438

# 0.6.2

ZenML 0.6.2 brings you the ability to serve models using MLflow deployments as well as an updated CLI interface! For a real continuous deployment cycle, we know that ZenML pipelines should be able to handle everything — from pre-processing to training to serving to monitoring and then potentially re-training and re-serving. The interfaces we created in this release are the foundation on which all of this will build.

We also improved how you interact with ZenML through the CLI. Everything looks so much smarter and readable now with the popular `rich` library integrated into our dependencies.

Smaller changes that you'll notice include updates to our cloud integrations and bug fixes for Windows users. For a detailed look at what's changed, see below.

## What's Changed

* Updated notebook for quickstart by @htahir1 in https://github.com/zenml-io/zenml/pull/398
* Update tensorflow base image by @schustmi in https://github.com/zenml-io/zenml/pull/396
* Add cloud specific deployment guide + refactoring by @wjayesh in https://github.com/zenml-io/zenml/pull/400
* add cloud sub page to toc.md by @wjayesh in https://github.com/zenml-io/zenml/pull/401
* fix tab indent by @wjayesh in https://github.com/zenml-io/zenml/pull/402
* Bugfix for workflows failing due to modules not being found by @bcdurak in https://github.com/zenml-io/zenml/pull/390
* Improve github workflows by @schustmi in https://github.com/zenml-io/zenml/pull/406
* Add plausible script to docs.zenml.io pages by @alex-zenml in https://github.com/zenml-io/zenml/pull/414
* Add orchestrator and ECR docs by @wjayesh in https://github.com/zenml-io/zenml/pull/413
* Richify the CLI by @alex-zenml in https://github.com/zenml-io/zenml/pull/392
* Allow specification of required integrations for a pipeline by @schustmi in https://github.com/zenml-io/zenml/pull/408
* Update quickstart in docs to conform to examples by @htahir1 in https://github.com/zenml-io/zenml/pull/410
* Updated PR template with some more details by @htahir1 in https://github.com/zenml-io/zenml/pull/411
* Bugfix on the CLI to work without a git installation by @bcdurak in https://github.com/zenml-io/zenml/pull/412
* Added Ayush's Handle by @ayush714 in https://github.com/zenml-io/zenml/pull/417
* Adding an info message on Windows if there is no application associated to .sh files by @bcdurak in https://github.com/zenml-io/zenml/pull/419
* Catch `matplotlib` crash when running IPython in terminal by @strickvl in https://github.com/zenml-io/zenml/pull/416
* Automatically activate integrations when unable to find stack component by @schustmi in https://github.com/zenml-io/zenml/pull/420
* Fix some code inspections by @halvgaard in https://github.com/zenml-io/zenml/pull/422
* Prepare integration tests on kubeflow by @schustmi in https://github.com/zenml-io/zenml/pull/423
* Add concepts back into glossary by @strickvl in https://github.com/zenml-io/zenml/pull/425
* Make guide easier to follow by @wjayesh in https://github.com/zenml-io/zenml/pull/427
* Fix httplib to 0.19 and pyparsing to 2.4 by @jwwwb in https://github.com/zenml-io/zenml/pull/426
* Wrap context serialization in try blocks by @jwwwb in https://github.com/zenml-io/zenml/pull/397
* Track stack configuration when registering and running a pipeline by @schustmi in https://github.com/zenml-io/zenml/pull/429
* MLflow deployment integration by @stefannica in https://github.com/zenml-io/zenml/pull/415

# 0.6.1

ZenML 0.6.1 is out and it's all about the cloud ☁️! We have improved AWS integration and a brand-new [Azure](https://github.com/zenml-io/zenml/tree/0.6.1/src/zenml/integrations/azure) integration! Run your pipelines on AWS and Azure now and let us know how it went on our [Slack](https://zenml.io/slack-invite).

Smaller changes that you'll notice include much-awaited updates and fixes, including the first iterations of scheduling pipelines and tracking more reproducibility-relevant data in the metadata store.

For a detailed look at what's changed, see below.

## What's changed

* Add MVP for scheduling by @htahir1 in https://github.com/zenml-io/zenml/pull/354
* Add S3 artifact store and filesystem by @schustmi in https://github.com/zenml-io/zenml/pull/359
* Update 0.6.0 release notes by @alex-zenml in https://github.com/zenml-io/zenml/pull/362
* Fix cuda-dev base container image by @stefannica in https://github.com/zenml-io/zenml/pull/361
* Mark ZenML as typed package by @schustmi in https://github.com/zenml-io/zenml/pull/360
* Improve error message if ZenML repo is missing inside kubeflow container entrypoint by @schustmi in https://github.com/zenml-io/zenml/pull/363
* Spell whylogs and WhyLabs correctly in our docs by @stefannica in https://github.com/zenml-io/zenml/pull/369
* Feature/add readme for mkdocs by @AlexejPenner in https://github.com/zenml-io/zenml/pull/372
* Cleaning up the assets pushed by gitbook automatically by @bcdurak in https://github.com/zenml-io/zenml/pull/371
* Turn codecov off for patch updates by @htahir1 in https://github.com/zenml-io/zenml/pull/376
* Minor changes and fixes by @schustmi in https://github.com/zenml-io/zenml/pull/365
* Only include python files when building local docs by @schustmi in https://github.com/zenml-io/zenml/pull/377
* Prevent access to repo during step execution by @schustmi in https://github.com/zenml-io/zenml/pull/370
* Removed duplicated Section within docs by @AlexejPenner in https://github.com/zenml-io/zenml/pull/379
* Fixing the materializer registry to spot sub-classes of defined types by @bcdurak in https://github.com/zenml-io/zenml/pull/368
* Computing hash of step and materializer works in notebooks by @htahir1 in https://github.com/zenml-io/zenml/pull/375
* Sort requirements to improve docker build caching by @schustmi in https://github.com/zenml-io/zenml/pull/383
* Make sure the s3 artifact store is registered when the integration is activated by @schustmi in https://github.com/zenml-io/zenml/pull/382
* Make MLflow integration work with kubeflow and scheduled pipelines by @stefannica in https://github.com/zenml-io/zenml/pull/374
* Reset _has_been_called to False ahead of pipeline.connect by @AlexejPenner in https://github.com/zenml-io/zenml/pull/385
* Fix local airflow example by @schustmi in https://github.com/zenml-io/zenml/pull/366
* Improve and extend base materializer error messages by @schustmi in https://github.com/zenml-io/zenml/pull/380
* Windows CI issue by @schustmi in https://github.com/zenml-io/zenml/pull/389
* Add the ability to attach custom properties to the Metadata Store by @bcdurak in https://github.com/zenml-io/zenml/pull/355
* Handle case when return values do not match output by @AlexejPenner in https://github.com/zenml-io/zenml/pull/386
* Quickstart code in docs fixed by @AlexejPenner in https://github.com/zenml-io/zenml/pull/387
* Fix mlflow tracking example by @stefannica in https://github.com/zenml-io/zenml/pull/393
* Implement azure artifact store and fileio plugin by @schustmi in https://github.com/zenml-io/zenml/pull/388
* Create todo issues with separate issue type by @schustmi in https://github.com/zenml-io/zenml/pull/394
* Log that steps are cached while running pipeline by @alex-zenml in https://github.com/zenml-io/zenml/pull/381
* Schedule added to context for all orchestrators by @AlexejPenner in https://github.com/zenml-io/zenml/pull/391

# 0.6.0

ZenML 0.6.0 is out now. We've made some big changes under the hood, but our biggest public-facing addition is our new integration to support all your data logging needs: [`whylogs`](https://github.com/whylabs/whylogs). Our core architecture was [thoroughly reworked](https://github.com/zenml-io/zenml/pull/305) and is now in a much better place to support our ongoing development needs.


Smaller changes that you'll notice include extensive documentation additions, updates and fixes. For a detailed look at what's changed, see below.

## 📊 Whylogs logging

[Whylogs](https://github.com/whylabs/whylogs) is an open source library that analyzes your data and creates statistical summaries called whylogs profiles. Whylogs profiles can be visualized locally or uploaded to the WhyLabs platform where more comprehensive analysis can be carried out.

ZenML integrates seamlessly with Whylogs and [WhyLabs](https://whylabs.ai/). This example shows how easy it is to enhance steps in an existing ML pipeline with Whylogs profiling features. Changes to the user code are minimal while ZenML takes care of all aspects related to Whylogs session initialization, profile serialization, versioning and persistence and even uploading generated profiles to [Whylabs](https://whylabs.ai/).

![Example of the visualizations you can make from Whylogs profiles](https://blog.zenml.io/assets/posts/release_0_6_0/whylogs-visualizer.png)

With our `WhylogsVisualizer`, as described in [the associated example notes](https://github.com/zenml-io/zenml/tree/0.6.0/examples/whylogs), you can visualize Whylogs profiles generated as part of a pipeline.

## ⛩ New Core Architecture

We implemented [some fundamental changes](https://github.com/zenml-io/zenml/pull/305) to the core architecture to solve some of the issues we previously had and provide a more extensible design to support quicker implementations of different stack components and integrations. The main change was to refactor the `Repository`, `Stack` and `StackComponent` architectures. These changes had a pretty wide impact so involved changes in many files throughout the codebase, especially in the CLI which makes calls to all these pieces.

We've already seen how it helps us move faster in building integrations and we hope it helps making contributions as pain-free as possible!

## 🗒 Documentation and Example Updates

As the codebase and functionality of ZenML grows, we always want to make sure our documentation is clear, up-to-date and easy to use. We made a number of changes in this release that will improve your experience in this regard:

- added a number of new explainers on key ZenML concepts and how to use them in your code, notably on [how to create a custom materializer](https://docs.zenml.io/v/0.6.0/guides/index/custom-materializer) and [how to fetch historic pipeline runs](https://docs.zenml.io/v/0.6.0/guides/index/historic-runs) using the `StepContext`
- fixed a number of typos and broken links
- [added versioning](https://github.com/zenml-io/zenml/pull/336) to our API documentation so you can choose to view the reference appropriate to the version that you're using. We now use `mkdocs` for this so you'll notice a slight visual refresh as well.
- added new examples highlighting specific use cases and integrations:
	- how to create a custom materializer ([example](https://github.com/zenml-io/zenml/tree/0.6.0/examples/custom_materializer))
	- how to fetch historical pipeline runs ([example](https://github.com/zenml-io/zenml/tree/0.6.0/examples/fetch_historical_runs))
	- how to use standard interfaces for common ML patterns ([example](https://github.com/zenml-io/zenml/tree/0.6.0/examples/standard_interfaces))
	- `whylogs` logging ([example](https://github.com/zenml-io/zenml/tree/0.6.0/examples/whylogs))

## ➕ Other updates, additions and fixes

As with most releases, we made a number of small but significant fixes and additions. The most import of these were that you can now [access the metadata store](https://github.com/zenml-io/zenml/pull/338) via the step context. This enables a number of new possible workflows and pipeline patterns and we're really excited to have this in the release.

We [added in](https://github.com/zenml-io/zenml/pull/315) a markdown parser for the `zenml example info …` command, so now when you want to use our CLI to learn more about specific examples you will see beautifully parsed text and not markdown markup.

We improved a few of our error messages, too, like for when the return type of a step function [doesn’t match the expected type](https://github.com/zenml-io/zenml/pull/322), or if [step is called twice](https://github.com/zenml-io/zenml/pull/353). We hope this makes ZenML just that little bit easier to use.

# 0.5.7

ZenML 0.5.7 is here  :100:  and it brings not one, but :fire:TWO:fire: brand new integrations :rocket:! ZenML now support [MLFlow](https://www.mlflow.org/docs/latest/tracking.html) for tracking pipelines as experiments and [Evidently](https://github.com/evidentlyai/evidently) for detecting drift in your ML pipelines in production!

## New Features
* Introducing the [MLFLow Tracking](https://www.mlflow.org/docs/latest/tracking.html) Integration, a first step towards 
our complete MLFlow Integration as described in the [#115 poll](https://github.com/zenml-io/zenml/discussions/115). 
Full example found [here](https://github.com/zenml-io/zenml/tree/0.5.7/examples/mlflow).
* Introducing the [Evidently](https://github.com/evidentlyai/evidently) integration. Use the standard 
[Evidently drift detection step](https://github.com/zenml-io/zenml/blob/0.5.7/src/zenml/integrations/evidently/steps/evidently_profile.py) 
to calculate drift automatically in your pipeline. Full example found [here](https://github.com/zenml-io/zenml/tree/0.5.7/examples/drift_detection).

## Bugfixes
* Prevent KFP install timeouts during `stack up` by @stefannica in https://github.com/zenml-io/zenml/pull/299
* Prevent naming parameters same name as inputs/outputs to prevent kwargs-errors by @bcdurak in https://github.com/zenml-io/zenml/pull/300


## What's Changed
* Force pull overwrites local examples without user confirmation by @AlexejPenner in https://github.com/zenml-io/zenml/pull/278
* Updated README with latest features by @htahir1 in https://github.com/zenml-io/zenml/pull/280
* Integration test the examples within ci pipeline by @AlexejPenner in https://github.com/zenml-io/zenml/pull/282
* Add exception for missing system requirements by @kamalesh0406 in https://github.com/zenml-io/zenml/pull/281
* Examples are automatically pulled if not present before any example command is run by @AlexejPenner in https://github.com/zenml-io/zenml/pull/279
* Add pipeline error for passing the same step object twice by @kamalesh0406 in https://github.com/zenml-io/zenml/pull/283
* Create pytest fixture to use a temporary zenml repo in tests by @htahir1 in https://github.com/zenml-io/zenml/pull/287
* Additional example run implementations for standard interfaces, functional and class based api by @AlexejPenner in https://github.com/zenml-io/zenml/pull/286
* Make pull_request.yaml actually use os.runner instead of ubuntu by @htahir1 in https://github.com/zenml-io/zenml/pull/288
* In pytest return to previous workdir before tearing down tmp_dir fixture by @AlexejPenner in https://github.com/zenml-io/zenml/pull/289
* Don't raise an exception during integration installation if system requirement is not installed by @schustmi in https://github.com/zenml-io/zenml/pull/291
* Update starting page for the API docs by @alex-zenml in https://github.com/zenml-io/zenml/pull/294
* Add `stack up` failure prompts by @alex-zenml in https://github.com/zenml-io/zenml/pull/290
* Spelling fixes by @alex-zenml in https://github.com/zenml-io/zenml/pull/295
* Remove instructions to git init from docs by @bcdurak in https://github.com/zenml-io/zenml/pull/293
* Fix the `stack up` and `orchestrator up` failure prompts by @stefannica in https://github.com/zenml-io/zenml/pull/297
* Prevent KFP install timeouts during `stack up` by @stefannica in https://github.com/zenml-io/zenml/pull/299
* Add stefannica to list of internal github users by @stefannica in https://github.com/zenml-io/zenml/pull/303
* Improve KFP UI daemon error messages by @schustmi in https://github.com/zenml-io/zenml/pull/292
* Replaced old diagrams with new ones in the docs by @AlexejPenner in https://github.com/zenml-io/zenml/pull/306
* Fix broken links & text formatting in docs by @alex-zenml in https://github.com/zenml-io/zenml/pull/302
* Run KFP container as local user/group if local by @stefannica in https://github.com/zenml-io/zenml/pull/304
* Add james to github team by @jwwwb in https://github.com/zenml-io/zenml/pull/308
* Implement integration of mlflow tracking by @AlexejPenner in https://github.com/zenml-io/zenml/pull/301
* Bugfix integration tests on windows by @jwwwb in https://github.com/zenml-io/zenml/pull/296
* Prevent naming parameters same name as inputs/outputs to prevent kwargs-errors by @bcdurak in https://github.com/zenml-io/zenml/pull/300
* Add tests for `fileio` by @alex-zenml in https://github.com/zenml-io/zenml/pull/298
* Evidently integration (standard steps and example) by @alex-zenml in https://github.com/zenml-io/zenml/pull/307
* Implemented evidently integration by @stefannica in https://github.com/zenml-io/zenml/pull/310
* Make mlflow example faster by @AlexejPenner in https://github.com/zenml-io/zenml/pull/312

## New Contributors
* @kamalesh0406 made their first contribution in https://github.com/zenml-io/zenml/pull/281
* @stefannica made their first contribution in https://github.com/zenml-io/zenml/pull/297
* @jwwwb made their first contribution in https://github.com/zenml-io/zenml/pull/308


**Full Changelog**: https://github.com/zenml-io/zenml/compare/0.5.6...0.5.7
# 0.5.6

        )                    *      (     
     ( /(                  (  `     )\ )  
     )\())    (            )\))(   (()/(  
    ((_)\    ))\    (     ((_)()\   /(_)) 
     _((_)  /((_)   )\ )  (_()((_) (_))   
    |_  /  (_))    _(_/(  |  \/  | | |    
     / /   / -_)  | ' \)) | |\/| | | |__  
    /___|  \___|  |_||_|  |_|  |_| |____| 

This release fixes some known bugs from previous releases and especially 0.5.5. Therefore, upgrading to 0.5.6 is a **breaking change**. You must do the following in order to proceed with this version:

```
cd zenml_enabled_repo
rm -rf .zen/
```

And then start again with ZenML init:

```
pip install --upgrade zenml
zenml init
```

## New Features
* Added `zenml example run [EXAMPLE_RUN_NAME]` feature: The ability to run an example with one command. In order to run this, do `zenml example pull` first and see all examples available by running `zenml example list`.
* Added ability to specify a `.dockerignore` file before running pipelines on Kubeflow.
* Kubeflow Orchestrator is now leaner and faster. 
* Added the `describe` command group to the CLI for groups `stack`, `orchestrator`, `artifact-store`, and `metadata-store`. E.g. `zenml stack describe`

## Bug fixes and minor improvements
* Adding `StepContext` to a branch now invalidates caching by default. Disable explicitly with `enable_cache=True`.
* Docs updated to reflect minor changes in CLI commands.
* CLI `list` commands now mentions active component. Try `zenml stack list` to check this out.
* `zenml version` now has cooler art.

## What's Changed
* Delete blog reference from release notes by @alex-zenml in https://github.com/zenml-io/zenml/pull/228
* Docs updates by @alex-zenml in https://github.com/zenml-io/zenml/pull/229
* Update kubeflow guide by @schustmi in https://github.com/zenml-io/zenml/pull/230
* Updated quickstart to reflect newest zenml version by @alexej-zenml in https://github.com/zenml-io/zenml/pull/231
* Add KFP GCP example readme by @schustmi in https://github.com/zenml-io/zenml/pull/233
* Baris/update docs with class api by @bcdurak in https://github.com/zenml-io/zenml/pull/232
* fixing a small typo [ci skip] by @bcdurak in https://github.com/zenml-io/zenml/pull/236
* Hamza/docs last min updates by @htahir1 in https://github.com/zenml-io/zenml/pull/234
* fix broken links by @alex-zenml in https://github.com/zenml-io/zenml/pull/237
* added one more page for standardized artifacts [ci skip] by @bcdurak in https://github.com/zenml-io/zenml/pull/238
* Unified use of cli_utils.print_table for all table format cli printouts by @AlexejPenner in https://github.com/zenml-io/zenml/pull/240
* Remove unused tfx kubeflow code by @schustmi in https://github.com/zenml-io/zenml/pull/239
* Relaxed typing requirements for cli_utils.print_table by @AlexejPenner in https://github.com/zenml-io/zenml/pull/241
* Pass input artifact types to kubeflow container entrypoint by @schustmi in https://github.com/zenml-io/zenml/pull/242
* Catch duplicate run name error and throw custom exception by @schustmi in https://github.com/zenml-io/zenml/pull/243
* Improved logs by @htahir1 in https://github.com/zenml-io/zenml/pull/244
* CLI active component highlighting by @alex-zenml in https://github.com/zenml-io/zenml/pull/245
* Baris/eng 244 clean up by @bcdurak in https://github.com/zenml-io/zenml/pull/246
* CLI describe command by @alex-zenml in https://github.com/zenml-io/zenml/pull/248
* Alexej/eng 35 run examples from cli by @AlexejPenner in https://github.com/zenml-io/zenml/pull/253
* CLI argument and option flag consistency improvements by @alex-zenml in https://github.com/zenml-io/zenml/pull/250
* Invalidate caching when a step requires a step context by @schustmi in https://github.com/zenml-io/zenml/pull/252
* Implement better error messages for custom step output artifact types by @schustmi in https://github.com/zenml-io/zenml/pull/254
* Small improvements by @schustmi in https://github.com/zenml-io/zenml/pull/251
* Kubeflow dockerignore by @schustmi in https://github.com/zenml-io/zenml/pull/249
* Rename container registry folder to be consistent with the other stack components by @schustmi in https://github.com/zenml-io/zenml/pull/257
* Update todo script by @schustmi in https://github.com/zenml-io/zenml/pull/256
* Update docs following CLI change by @alex-zenml in https://github.com/zenml-io/zenml/pull/255
* Bump mypy version by @schustmi in https://github.com/zenml-io/zenml/pull/258
* Kubeflow Windows daemon alternative by @schustmi in https://github.com/zenml-io/zenml/pull/259
* Run pre commit in local environment by @schustmi in https://github.com/zenml-io/zenml/pull/260
* Hamza/eng 269 move beam out by @htahir1 in https://github.com/zenml-io/zenml/pull/262
* Update docs by @alex-zenml in https://github.com/zenml-io/zenml/pull/261
* Hamza/update readme with contribitions by @htahir1 in https://github.com/zenml-io/zenml/pull/271
* Hamza/eng 256 backoff analytics by @htahir1 in https://github.com/zenml-io/zenml/pull/270
* Add spellcheck by @alex-zenml in https://github.com/zenml-io/zenml/pull/264
* Using the pipeline run name to explicitly access when explaining the … by @AlexejPenner in https://github.com/zenml-io/zenml/pull/263
* Import user main module in kubeflow entrypoint to make sure all components are registered by @schustmi in https://github.com/zenml-io/zenml/pull/273
* Fix cli version command by @schustmi in https://github.com/zenml-io/zenml/pull/272
* User is informed of version mismatch and example pull defaults to cod… by @AlexejPenner in https://github.com/zenml-io/zenml/pull/274
* Hamza/eng 274 telemetry by @htahir1 in https://github.com/zenml-io/zenml/pull/275
* Update docs with right commands and events by @htahir1 in https://github.com/zenml-io/zenml/pull/276
* Fixed type annotation for some python versions by @AlexejPenner in https://github.com/zenml-io/zenml/pull/277

**Full Changelog**: https://github.com/zenml-io/zenml/compare/0.5.5...0.5.6

# 0.5.5

ZenML 0.5.5 is jam-packed with new features to take your ML pipelines to the next level. Our three biggest new features: Kubeflow Pipelines, CLI support for our integrations and Standard Interfaces. That’s right, Standard Interfaces are back!

## What's Changed
* Implement base component tests by @schustmi in https://github.com/zenml-io/zenml/pull/211
* Add chapter names by @alex-zenml in https://github.com/zenml-io/zenml/pull/212
* Fix docstring error by @alex-zenml in https://github.com/zenml-io/zenml/pull/213
* Hamza/add caching example by @htahir1 in https://github.com/zenml-io/zenml/pull/214
* Update readme by @alex-zenml in https://github.com/zenml-io/zenml/pull/216
* Hamza/add small utils by @htahir1 in https://github.com/zenml-io/zenml/pull/219
* Update docs by @alex-zenml in https://github.com/zenml-io/zenml/pull/220
* Docs fixes by @alex-zenml in https://github.com/zenml-io/zenml/pull/222
* Baris/eng 182 standard interfaces by @bcdurak in https://github.com/zenml-io/zenml/pull/209
* Fix naming error by @alex-zenml in https://github.com/zenml-io/zenml/pull/221
* Remove framework design by @alex-zenml in https://github.com/zenml-io/zenml/pull/224
* Alexej/eng 234 zenml integration install by @alexej-zenml in https://github.com/zenml-io/zenml/pull/223
* Fix deployment section order by @alex-zenml in https://github.com/zenml-io/zenml/pull/225
* the readme of the example by @bcdurak in https://github.com/zenml-io/zenml/pull/227
* Kubeflow integration by @schustmi in https://github.com/zenml-io/zenml/pull/226

## New Contributors
* @alexej-zenml made their first contribution in https://github.com/zenml-io/zenml/pull/223

**Full Changelog**: https://github.com/zenml-io/zenml/compare/0.5.4...0.5.5

# 0.5.4

0.5.4 adds a [lineage tracking](https://github.com/zenml-io/zenml/tree/main/examples/lineage) integration to visualize lineage of pipeline runs! It also includes numerous bug fixes and optimizations.

## What's Changed
* Fix typos by @alex-zenml in https://github.com/zenml-io/zenml/pull/192
* Fix Apache Beam bug by @alex-zenml in https://github.com/zenml-io/zenml/pull/194
* Fix apache beam logging bug by @alex-zenml in https://github.com/zenml-io/zenml/pull/195
* Add step context by @schustmi in https://github.com/zenml-io/zenml/pull/196
* Init docstrings by @alex-zenml in https://github.com/zenml-io/zenml/pull/197
* Hamza/small fixes by @htahir1 in https://github.com/zenml-io/zenml/pull/199
* Fix writing to metadata store with airflow orchestrator by @schustmi in https://github.com/zenml-io/zenml/pull/198
* Use pipeline parameter name as step name in post execution by @schustmi in https://github.com/zenml-io/zenml/pull/200
* Add error message when step name is not in metadata store by @schustmi in https://github.com/zenml-io/zenml/pull/201
* Add option to set repo location using an environment variable by @schustmi in https://github.com/zenml-io/zenml/pull/202
* Run cloudbuild after pypi publish by @schustmi in https://github.com/zenml-io/zenml/pull/203
* Refactor component generation by @schustmi in https://github.com/zenml-io/zenml/pull/204
* Removed unnecessary panel dependency by @htahir1 in https://github.com/zenml-io/zenml/pull/206
* Updated README to successively install requirements by @AlexejPenner in https://github.com/zenml-io/zenml/pull/205
* Store active stack in local config by @schustmi in https://github.com/zenml-io/zenml/pull/208
* Hamza/eng 125 lineage tracking vis by @htahir1 in https://github.com/zenml-io/zenml/pull/207

## New Contributors
* @AlexejPenner made their first contribution in https://github.com/zenml-io/zenml/pull/205

**Full Changelog**: https://github.com/zenml-io/zenml/compare/0.5.3...0.5.4

# 0.5.3

Version 0.5.3 adds [statistics visualizations](https://github.com/zenml-io/zenml/blob/main/examples/visualizers/statistics/README.md), greatly improved speed for CLI commands as well as lots of small improvements to the pipeline and step interface. 

## What's Changed
* Make tests run in a random order by @alex-zenml in https://github.com/zenml-io/zenml/pull/160
* Connect steps using *args by @schustmi in https://github.com/zenml-io/zenml/pull/162
* Move location of repobeats image by @alex-zenml in https://github.com/zenml-io/zenml/pull/163
* Hamza/add sam by @htahir1 in https://github.com/zenml-io/zenml/pull/165
* Pipeline initialization with *args by @schustmi in https://github.com/zenml-io/zenml/pull/164
* Improve detection of third party modules during class resolving by @schustmi in https://github.com/zenml-io/zenml/pull/167
* Merge path_utils into fileio & refactor what was left by @alex-zenml in https://github.com/zenml-io/zenml/pull/168
* Update docker files by @schustmi in https://github.com/zenml-io/zenml/pull/169
* Hamza/deploy api reference by @htahir1 in https://github.com/zenml-io/zenml/pull/171
* API Reference by @schustmi in https://github.com/zenml-io/zenml/pull/172
* Add color back into our github actions by @alex-zenml in https://github.com/zenml-io/zenml/pull/176
* Refactor tests not raising by @alex-zenml in https://github.com/zenml-io/zenml/pull/177
* Improve step and pipeline interface by @schustmi in https://github.com/zenml-io/zenml/pull/175
* Alex/eng 27 windows bug again by @htahir1 in https://github.com/zenml-io/zenml/pull/178
* Automated todo tracking by @schustmi in https://github.com/zenml-io/zenml/pull/173
* Fix mypy issues related to windows by @schustmi in https://github.com/zenml-io/zenml/pull/179
* Include Github URL to TODO comment in issue by @schustmi in https://github.com/zenml-io/zenml/pull/181
* Create Visualizers logic by @htahir1 in https://github.com/zenml-io/zenml/pull/182
* Add README for visualizers examples by @alex-zenml in https://github.com/zenml-io/zenml/pull/184
* Allow None as default value for BaseStep configs by @schustmi in https://github.com/zenml-io/zenml/pull/185
* Baris/eng 37 standard import check by @bcdurak in https://github.com/zenml-io/zenml/pull/183
* Replace duplicated code by call to source_utils.resolve_class by @schustmi in https://github.com/zenml-io/zenml/pull/186
* Remove unused base enum cases by @schustmi in https://github.com/zenml-io/zenml/pull/187
* Testing mocks for CLI `examples` command by @alex-zenml in https://github.com/zenml-io/zenml/pull/180
* Set the correct module for steps created using our decorator by @schustmi in https://github.com/zenml-io/zenml/pull/188
* Fix some cli commands by @schustmi in https://github.com/zenml-io/zenml/pull/189
* Tag jira issues for which the todo was deleted by @schustmi in https://github.com/zenml-io/zenml/pull/190
* Remove deadlinks by @alex-zenml in https://github.com/zenml-io/zenml/pull/191


**Full Changelog**: https://github.com/zenml-io/zenml/compare/0.5.2...0.5.3

# 0.5.2

0.5.2 brings an improved post-execution workflow and lots of minor changes and upgrades for the developer experience when 
creating pipelines. It also improves the Airflow orchestrator logic to accommodate for more real world scenarios. Check out the 
[low level API guide for more details!](https://docs.zenml.io/guides/low-level-api)

## What's Changed
* Fix autocomplete for step and pipeline decorated functions by @schustmi in https://github.com/zenml-io/zenml/pull/144
* Add reference docs for CLI example functionality by @alex-zenml in https://github.com/zenml-io/zenml/pull/145
* Fix mypy integration by @schustmi in https://github.com/zenml-io/zenml/pull/147
* Improve Post-Execution Workflow by @schustmi in https://github.com/zenml-io/zenml/pull/146
* Fix CLI examples bug by @alex-zenml in https://github.com/zenml-io/zenml/pull/148
* Update quickstart example notebook by @alex-zenml in https://github.com/zenml-io/zenml/pull/150
* Add documentation images by @alex-zenml in https://github.com/zenml-io/zenml/pull/151
* Add prettierignore to gitignore by @alex-zenml in https://github.com/zenml-io/zenml/pull/154
* Airflow orchestrator improvements by @schustmi in https://github.com/zenml-io/zenml/pull/153
* Google colab added by @htahir1 in https://github.com/zenml-io/zenml/pull/155
* Tests for `core` and `cli` modules by @alex-zenml in https://github.com/zenml-io/zenml/pull/149
* Add Paperspace environment check by @alex-zenml in https://github.com/zenml-io/zenml/pull/156
* Step caching by @schustmi in https://github.com/zenml-io/zenml/pull/157
* Add documentation for pipeline step parameter and run name configuration by @schustmi in https://github.com/zenml-io/zenml/pull/158
* Automatically disable caching if the step function code has changed by @schustmi in https://github.com/zenml-io/zenml/pull/159


**Full Changelog**: https://github.com/zenml-io/zenml/compare/0.5.1...0.5.2

# 0.5.1
0.5.1 builds on top of Slack of the 0.5.0 release with quick bug updates.


## Overview

* Pipeline can now be run via a YAML file. #132
* CLI now let's you pull directly from GitHub examples folder. :fire: Amazing @alex-zenml with #141!
* ZenML now has full [mypy](http://mypy-lang.org/) compliance. :tada: Thanks @schustmi for #140!
* Numerous bugs and performance improvements. #136, @bcdurak great job with #142
* Added new docs with a low level API guide. #143

[Our roadmap](https://docs.zenml.io/support/roadmap) goes into further detail on the timeline. Vote on the [next features now](https://github.com/zenml-io/zenml/discussions).

We encourage every user (old or new) to start afresh with this release. Please go over our latest [docs](https://docs.zenml.io) and [examples](examples) to get a hang of the new system.


# 0.5.0
This long-awaited ZenML release marks a seminal moment in the project's history. We present to you a complete 
revamp of the internals of ZenML, with a fresh new design and API. While these changes are significant, and have been months 
in the making, the original vision of ZenML has not wavered. We hope that the ZenML community finds the new 
design choices easier to grasp and use, and we welcome feedback on the [issues board](https://github.com/zenml-io/zenml/issues).

## Warning
0.5.0 is a complete API change from the previous versions of ZenML, and is a *breaking* upgrade. Fundamental 
concepts have been changed, and therefore backwards compatibility is not maintained. Please use only this version 
with fresh projects.

With such significant changes, we expect this release to also be breaking. Please report any bugs in the issue board, and 
they should be addressed in upcoming releases.

## Overview

* Introducing a new functional API for creating pipelines and steps. This is now the default mechanism for building ZenML pipelines. [read more](https://docs.zenml.io/quickstart-guide)
* Steps now use Materializers to handle artifact serialization/deserialization between steps. This is a powerful change, and will be expanded upon in the future. [read more](https://docs.zenml.io/core/materializers)
* Introducing the new `Stack` paradigm: Easily transition from one MLOps stack to the next with a few CLI commands [read more](https://docs.zenml.io/core/stacks)
* Introducing a new `Artifact`, `Typing`, and `Annotation` system, with `pydantic` (and `dataclasses`) support [read more](https://docs.zenml.io/core/artifacts)
* Deprecating the `pipelines_dir`: Now individual pipelines will be stored in their metadata stores, making the metadata store a single source of truth. [read more](https://docs.zenml.io/core/stacks)
* Deprecating the YAML config file: ZenML no longer natively compiles to an intermediate YAML-based representation. Instead, it compiles and deploys directly into the selected orchestrator's 
representation. While we do plan to support running pipelines directly through YAML in the future, it will no longer be
the default route through which pipelines are run. [read more about orchestrators here](https://docs.zenml.io/core/stacks)

## Technical Improvements
* A completely new system design, please refer to the [docs](https://docs.zenml.io/core/core-concepts).
* Better type hints and docstrings.
* Auto-completion support.
* Numerous performance improvements and bug fixes, including a smaller dependency footprint.

## What to expect in the next weeks and the new ZenML
Currently, this release is bare bones. We are missing some basic features which used to be part of ZenML 0.3.8 (the previous release):

* Standard interfaces for `TrainingPipeline`.
* Individual step interfaces like `PreprocessorStep`, `TrainerStep`, `DeployerStep` etc. need to be rewritten from within the new paradigm. They should
be included in the non-RC version of this release.
* A proper production setup with an orchestrator like Airflow.
* A post-execution workflow to analyze and inspect pipeline runs.
* The concept of `Backends` will evolve into a simple mechanism of transitioning individual steps into different runners.
* Support for `KubernetesOrchestrator`, `KubeflowOrchestrator`, `GCPOrchestrator` and `AWSOrchestrator` are also planned.
* Dependency management including Docker support is planned.

[Our roadmap](https://docs.zenml.io/support/roadmap) goes into further detail on the timeline.

We encourage every user (old or new) to start afresh with this release. Please go over our latest [docs](https://docs.zenml.io) 
and [examples](examples) to get a hang of the new system.

Onwards and upwards to 1.0.0!

# 0.5.0rc2
This long-awaited ZenML release marks a seminal moment in the project's history. We present to you a complete 
revamp of the internals of ZenML, with a fresh new design and API. While these changes are significant, and have been months 
in the making, the original vision of ZenML has not wavered. We hope that the ZenML community finds the new 
design choices easier to grasp and use, and we welcome feedback on the [issues board](https://github.com/zenml-io/zenml/issues).

## Warning
0.5.0rc0 is a complete API change from the previous versions of ZenML, and is a *breaking* upgrade. Fundamental 
concepts have been changed, and therefore backwards compatibility is not maintained. Please use only this version 
with fresh projects.

With such significant changes, we expect this release to also be breaking. Please report any bugs in the issue board, and 
they should be addressed in upcoming releases.

## Overview

* Introducing a new functional API for creating pipelines and steps. This is now the default mechanism for building ZenML pipelines. [read more](https://docs.zenml.io/quickstart-guide)
* Introducing the new `Stack` paradigm: Easily transition from one MLOps stack to the next with a few CLI commands [read more](https://docs.zenml.io/core/stacks)
* Introducing a new `Artifact`, `Typing`, and `Annotation` system, with `pydantic` (and `dataclasses`) support [read more](https://docs.zenml.io/core/artifacts)
* Deprecating the `pipelines_dir`: Now individual pipelines will be stored in their metadata stores, making the metadata store a single source of truth. [read more](https://docs.zenml.io/core/stacks)
* Deprecating the YAML config file: ZenML no longer natively compiles to an intermediate YAML-based representation. Instead, it compiles and deploys directly into the selected orchestrator's 
representation. While we do plan to support running pipelines directly through YAML in the future, it will no longer be
the default route through which pipelines are run. [read more about orchestrators here](https://docs.zenml.io/core/stacks)

## Technical Improvements
* A completely new system design, please refer to the [docs](https://docs.zenml.io/core/core-concepts).
* Better type hints and docstrings.
* Auto-completion support.
* Numerous performance improvements and bug fixes, including a smaller dependency footprint.

## What to expect in the next weeks and the new ZenML
Currently, this release is bare bones. We are missing some basic features which used to be part of ZenML 0.3.8 (the previous release):

* Standard interfaces for `TrainingPipeline`.
* Individual step interfaces like `PreprocessorStep`, `TrainerStep`, `DeployerStep` etc. need to be rewritten from within the new paradigm. They should
be included in the non-RC version of this release.
* A proper production setup with an orchestrator like Airflow.
* A post-execution workflow to analyze and inspect pipeline runs.
* The concept of `Backends` will evolve into a simple mechanism of transitioning individual steps into different runners.
* Support for `KubernetesOrchestrator`, `KubeflowOrchestrator`, `GCPOrchestrator` and `AWSOrchestrator` are also planned.
* Dependency management including Docker support is planned.

[Our roadmap](https://docs.zenml.io/support/roadmap) goes into further detail on the timeline.

We encourage every user (old or new) to start afresh with this release. Please go over our latest [docs](https://docs.zenml.io) 
and [examples](examples) to get a hang of the new system.

Onwards and upwards to 1.0.0!

# 0.3.7.1
This release fixes some known bugs from previous releases and especially 0.3.7. Same procedure as always, please delete existing pipelines, metadata, and artifact stores.

```
cd zenml_enabled_repo
rm -rf pipelines/
rm -rf .zenml/
```

And then another ZenML init:

```
pip install --upgrade zenml
cd zenml_enabled_repo
zenml init
```

## New Features
* Introduced new `zenml example` CLI sub-group: Easily pull examples via zenml to check it out.

```bash
zenml example pull # pulls all examples in `zenml_examples` directory
zenml example pull EXAMPLE_NAME  # pulls specific example
zenml example info EXAMPLE_NAME  # gives quick info regarding example
```  
Thanks Michael Xu for the suggestion!

* Updated examples with new `zenml examples` paradigm for examples.

## Bug Fixes + Refactor

* ZenML now works on Windows -> Thank you @Franky007Bond for the heads up.
* Updated numerous bugs in examples directory. Also updated README's.
* Fixed remote orchestration logic -> Now remote orchestration works.
* Changed datasource `to_config` to include reference to backend, metadata, and artifact store.


# 0.3.7
0.3.7 is a much-needed, long-awaited, big refactor of the Datasources paradigm of ZenML. There are also bug fixes, improvements, and more!

For those upgrading from an older version of ZenML, we ask to please delete their old `pipelines` dir and `.zenml` folders and start afresh with a `zenml init`.

If only working locally, this is as simple as:

```
cd zenml_enabled_repo
rm -rf pipelines/
rm -rf .zenml/
```

And then another ZenML init:

```
pip install --upgrade zenml
cd zenml_enabled_repo
zenml init
```

## New Features
* The inner-workings of the `BaseDatasource` have been modified along with the concrete implementations. Now, there is no relation between a `DataStep` and a `Datasource`: A `Datasource` holds all the logic to version and track itself via the new `commit` paradigm.

* Introduced a new interface for datasources, the `process` method which is responsible for ingesting data and writing to TFRecords to be consumed by later steps.

* Datasource versions (snapshots) can be accessed directly via the `commits` paradigm: Every commit is a new version of data.

* Added `JSONDatasource` and `TFRecordsDatasource`.

## Bug Fixes + Refactor
A big thanks to our new contributor @aak7912 for the help in this release with issue #71 and PR #75.

* Added an example for [regression](https://github.com/zenml-io/zenml/tree/main/examples/regression).
* `compare_training_runs()` now takes an optional `datasource` parameter to filter by datasource.
* `Trainer` interface refined to focus on `run_fn` rather than other helper functions.
* New docs released with a streamlined vision and coherent storyline: https://docs.zenml.io
* Got rid of unnecessary Torch dependency with base ZenML version.


# 0.3.6
0.3.6 is a more inwards-facing release as part of a bigger effort to create a more flexible ZenML. As a first step, ZenML now supports arbitrary splits for all components natively, freeing us from the `train/eval` split paradigm. Here is an overview of changes:

## New Features
* The inner-workings of the `BaseTrainerStep`, `BaseEvaluatorStep` and the `BasePreprocessorStep` have been modified along with their respective components to work with the new split_mapping. Now, users can define arbitrary splits (not just train/eval). E.g. Doing a `train/eval/test` split is possible.

* Within the instance of a `TrainerStep`, the user has access to `input_patterns` and `output_patterns` which provide the required uris with respect to their splits for the input and output(test_results) examples.

* The built-in trainers are modified to work with the new changes.

## Bug Fixes + Refactor
A big thanks to our new super supporter @zyfzjsc988 for most of the feedback that led to bug fixes and enhancements for this release: 

* #63: Now one can specify which ports ZenML opens its add-on applications.
* #64 Now there is a way to list integrations with the following code:
```
from zenml.utils.requirements_utils import list_integrations.
list_integrations()
```
* Fixed #61: `view_anomalies()` breaking in the quickstart.
* Analytics is now `opt-in` by default, to get rid of the unnecessary prompt at `zenml init`. Users can still freely `opt-out` by using the CLI:

```
zenml config analytics opt-out
```

Again, the telemetry data is fully anonymized and just used to improve the product. Read more [here](https://docs.zenml.io/misc/usage-analytics.html)

# 0.3.5

## New Features
* Added a new interface into the trainer step called [`test_fn`]() which is utilized to produce model predictions and save them as test results

* Implemented a new evaluator step called [`AgnosticEvaluator`]() which is designed to work regardless of the model type as long as you run the `test_fn` in your trainer step

* The first two changes allow torch trainer steps to be followed by an agnostic evaluator step, see the example [here]().

* Proposed a new naming scheme, which is now integrated into the built-in steps, in order to make it easier to handle feature/label names

* Implemented a new adapted version of 2 TFX components, namely the [`Trainer`]() and the [`Evaluator`]() to allow the aforementioned changes to take place

* Modified the [`TorchFeedForwardTrainer`]() to showcase how to use TensorBoard in conjunction with PyTorch


## Bug Fixes + Refactor
* Refactored how ZenML treats relative imports for custom steps. Now:
```python

```

* Updated the [Scikit Example](https://github.com/zenml-io/zenml/tree/main/examples/scikit), [PyTorch Lightning Example](https://github.com/zenml-io/zenml/tree/main/examples/pytorch_lightning), [GAN Example](https://github.com/zenml-io/zenml/tree/main/examples/gan) accordingly. Now they should work according to their README's.

Big shout out to @SarahKing92 in issue #34 for raising the above issues!


# 0.3.4
This release is a big design change and refactor. It involves a significant change in the Configuration file structure, meaning this is a **breaking upgrade**. 
For those upgrading from an older version of ZenML, we ask to please delete their old `pipelines` dir and `.zenml` folders and start afresh with a `zenml init`.

If only working locally, this is as simple as:

```
cd zenml_enabled_repo
rm -rf pipelines/
rm -rf .zenml/
```

And then another ZenML init:

```
pip install --upgrade zenml
cd zenml_enabled_repo
zenml init
```

## New Features
* Introduced another higher-level pipeline: The [NLPPipeline](https://github.com/zenml-io/zenml/blob/main/zenml/pipelines/nlp_pipeline.py). This is a generic 
  NLP pipeline for a text-datasource based training task. Full example of how to use the NLPPipeline can be found [here](https://github.com/zenml-io/zenml/tree/main/examples/nlp)
* Introduced a [BaseTokenizerStep](https://github.com/zenml-io/zenml/blob/main/zenml/steps/tokenizer/base_tokenizer.py) as a simple mechanism to define how to train and encode using any generic 
tokenizer (again for NLP-based tasks).

## Bug Fixes + Refactor
* Significant change to imports: Now imports are way simpler and user-friendly. E.g. Instead of:
```python
from zenml.core.pipelines.training_pipeline import TrainingPipeline
```

A user can simple do:

```python
from zenml.pipelines import TrainingPipeline
```

The caveat is of course that this might involve a re-write of older ZenML code imports.

Note: Future releases are also expected to be breaking. Until announced, please expect that upgrading ZenML versions may cause older-ZenML 
generated pipelines to behave unexpectedly. 
