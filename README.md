
# ZenML: Bring Zen to your ML with reproducible pipelines

We are coming soon! We're working hard to make our first public commit of ZenML (formerly [Core Engine](https://docs.maiot.io)). We hope to be live by mid December 2020. In the meanwhile, this README serves as a teaser of what to expect.

ZenML will be fully open-source. Do show us some love by giving us a star - It keeps us motivated and commiting!

## TMLS Annual Conference & Expo 2020
For folks who have landed here from Ben's talk at TMLS 2020, welcome! We'd be happy if you could give us a star and watch for new changes. You'd be the first one we reach out to personally when we're live!

## Why use ZenML?
Most of the people reading this would want to know why they would want to use yet another supposed MLOps tool that solves all production problems. The simple answer to this question there is still no one solution out there that really solves the ML in production headache: Most of them either solve for really Ops-y problems (CI/CD, deployments, feature stores) or for really Data Scienc-y (remote kernels, metadata tracking, hyper-parameter tuning) problems. The tools that are really state-of-the-art and come close are not approachable (financially + technologically) for hobbyists or smaller teams that just want to get models in production. The result is that 87% of ML models never make it into production, and those that do make it tend be looked after by enormous engineering teams with big budgets.

​The team behind ZenML has been through the ringer with putting models in production, and has built ZenML from the perspective of both ML and Ops people. Our goal with ZenML is to provide a neat interface for data scientists to write production-ready code from training day 0, and to provide a configurable, extensible and managed backend for Ops people to keep things chugging along. 

Last but not least, our hope is that ZenML provides the hobbyist/smaller companies with a golden path to put models in production. With our free plan, you can start writing production-ready ML pipelines immediately.

## Overview
If you are used to writing Jupyter notebooks, scripts and glue-code to get your ML experiments or pipelines going, you should give ZenML a try. ZenML will provide you with an easy way to run your code in a distributed, transparent and tracked environment. You can leverage all the perks of running in a production-ready environment, but without the overhead of setting up the Ops, the datasources, organizing all this and writing the code that brings it all together into one coherent environment for your organization.

ZenML takes care of much of the hassle of ML development, so you can focus on writing your app without needing to reinvent the wheel. By providing an easy-to-use and powerful computing platform, we expedite the transition of ML models to production services.

#### For Data Science people..
For the people who actually create models and do experiments, you get exposed a simple interface to plug and play your models and data with. You can run experiments remotely as easily as possible, and use  the automatic evaluation mechanisms that are built-in to analyze what happened. The goal is for you to follow as closely as possible the pandas/numpy/scikit paradigm you are familiar with, but to end-up with production-ready, scale-able and deploy-able models at the end. Every parameter is tracked and all artifacts are reproducible.

#### For Ops people..
For the people who are responsible for managing the infrastructure and tasked with negotiating the ever changing ML eco-system, ZenML should be seen as a platform that provides high-level integrations to various backends that are tedious to build and maintain. If you want to swap out some components of ZenML with others, then you are free to do so! For example, if you want to deploy on different cloud providers (AWS, GCP, Azure), or a different data processing backend (Spark, Dataflow etc), then ZenML provides this ability natively.

## The team behind it all
Visit [our company page](https://maiot.io/team/) to see the faces behind this project!