---
description: Build production ML pipelines from the simple step interface.
---

# Class-based API

The class-based ZenML API is defined by the base classes `BaseStep` and `BasePipeline`. These interfaces allow our 
users to maintain a higher level of control while they are creating a step definition and using it within the context 
of a pipeline.

A user may also mix-and-match the Functional API with the Class Based API: All standard data types and steps that 
are applicable in both of these approaches.

In order to illustrate how the Class-based API functions, we'll do a simple exercise to build our standard 
built-in training pipeline piece-by-piece.

