---
id: intro
title: Introduction to the Core Engine
sidebar_label: Introduction
---
## Welcome

Whether you're a new or an experienced user, there is plenty to discover about the Core Engine. We've collected 
(and continue to expand) this information and present it in a digestible way so you can start and build.

If you are already familiar with the basics, the [core concepts](developer_guide/core_concepts.md) will provide a 
better reference guide for the available features and internals.
<hr />

## What is the Core Engine
The Core Engine is an end-to-end MLOps platform that serves multiple roles in your machine learning workflow. It is:

* A **workload processing engine** - it processes and executes your code (in a distributed environment)
* An **orchestrator** - it automates configuration, management, and coordination of your ML workloads.
* A **ML framework** - it provides built-in plug-ins for normal tasks (like evaluation and serving).
* A **standardized interface** - to quickly configure and run pipelines from data ingestion, to training, evaluation, and finally serving. 

If you are coming from the land of writing jupyter notebooks, scripts and glue-code to get your ML experiments or 
pipelines going, you should give the Core Engine a try. The Core Engine will provide you with an easy way to 
run your code in a distributed, transparent and tracked environment. You can leverage all the perks of running in a 
production-ready environment, but without the overhead of setting up the Ops, the datasources, organizing all this and 
writing the code that brings it all together into one coherent environment for your organization.

The Core Engine takes care of much of the hassle of ML development, so you can focus on writing your app without 
needing to reinvent the wheel. By providing an **easy-to-use** and **powerful** computing platform, we expedite 
the transition of ML models to production services.
<hr />

## Basics
All experiments and model trainings are run in individual [pipelines](developer_guide/pipelines_config_yaml.md) 
and organized into [workspaces](developer_guide/workspaces.md). Similar experiments, i.e. ones using the same 
datasource, should be grouped in the same [workspace](developer_guide/workspaces.md), as subsequent pipeline runs 
enable the Core Engine to skip certain processing steps. This native [caching](developer_guide/caching.md) is 
built-in and supported across all plans and for all types of datasets.

[Configuration files](developer_guide/pipelines_config_yaml.md) are at the heart of each pipeline. They define 
your **_features_** and **_labels_**, how your data is **_split_** and which kind of **_preprocessing_** should be 
used. They configure your model and training (**_trainer_**), define the **_evaluator_** and contain 
optionally additional configuration for **_timeseries_** datasets. The configuration files are important because they separate
 the configuration of your pipeline from the actual implementation. This makes it easy to collaborate, 
 increases traceability, and standardizes your ML workflow. 

[Datasources](developer_guide/datasources.md) are the heart and soul you bring to the party. They contain and 
define your data. Feel free to reach out at [support@maiot.io](mailto:support@maiot.io) and tell us 
which datasource you'd like to see supported for your use-case.<hr />

## Key Features

### Declarative Configurations
Declarative Configurations for pipelines, models and datasources guarantee repeatable, reliable and comparable 
experiments.

### Native Caching
Machine Learning development involves repetitive experimentation. Thanks to [native caching](developer_guide/caching.md) 
of all computations you'll never have to repeat the same thing twice - saving time and money for all subsequent 
experiments.

### All the right tools
The Core Engine supports a wide variety of plugins and tools, including your favorite ones such as 
[TensorBoard](https://www.tensorflow.org/tensorboard) and the [What-If tool](https://pair-code.github.io/what-if-tool/) 
(WIP). They all come pre-configured and out-of-the-box as a result of every pipeline run.

### Native distributed computation
With big enough data, it can take hours to crunch through data in one single machine. The Core Engine uses distributed data processing technologies ([Apache Beam](https://beam.apache.org/)) for efficient execution, reducing hours of computation to just minutes.
<hr />

## Helpful Guides
<div class="container">
    <div class="row pt-4">
        <div class="col-md-6 col-sm-12">
            <div class="pb-5">
                <a href="installation"><h2 class="text-purple pb-3">&raquo; Install the Core Engine CLI</h2></a>
                <p>The most convenient way (in our opinion at least) to interact with the Core Engine is through the CLI. Installing is easy:</p>
                <code>pip install cengine</code>
                <p class="pt-3">Once the installation is completed, you can check whether the installation was successful through:</p>
                <code>cengine --version</code>
                <p class="text-right pt-2"><a href="installation">More about installation...</a></p>
                <hr />
            </div>
            <div class="pb-5">
                <a href="developer_guide/core_concepts"><h2 class="text-purple">&raquo; Core Concepts</h2></a>
                <p>The Core Engine is an end-to-end platform to run ML experiments.</p>
                <p>Experiments are conceptualized as <b>pipelines</b>, which are bundled into <b>workspaces</b>. There is <b>caching</b>, <b>config files</b>, <b>evaluation</b>, <b> model architectures</b> and so much more.</p>
                <p class="text-right pt-2"><a href="developer_guide/core_concepts">More about the Core Concepts...</a></p>
                <hr />
            </div>
        </div>
        <div class="col-md-6 col-sm-12">
            <div class="pb-5">
                <a href="quickstart"><h2 class="text-purple pb-3">&raquo; A quick start to the Core Engine</h2></a>
                <p>Once you've successfully created your account and completed the <a href="installation">installation</a> you're ready to go. Jump right into the quick start if you're new to the Core Engine to run your first pipeline within minutes!</p>
                <p class="text-right pt-2"><a href="quickstart">More about the Quick Start...</a></p>
                <hr />
            </div>
            <div class="pb-5">
                <a href="workspaces"><h2 class="text-purple pb-3">&raquo; A primer on workspaces</h2></a>
                <p>The concept of <a href="workspaces">workspaces</a> is created to maintain an organized and efficient structure within the ML workflow of your organization.</p>
                <p>Through a workspace, developers can:</p>
                <ul>
                    <li>Gather all their solutions about a problem under one roof</li>
                    <li>Collaborate on the same problem by sharing their experiments and solutions</li>
                </ul>
                <p class="text-right pt-2"><a href="developer_guide/workspaces">More about Workspacest...</a></p>
                <hr />
            </div>
        </div>
    </div>
</div>