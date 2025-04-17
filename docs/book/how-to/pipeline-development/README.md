---
icon: paintbrush-pencil
---

# Pipeline Development

This section covers all aspects of pipeline development in ZenML.

## Simulating Pipeline Runs

ZenML does not support a direct 'dry run' feature. However, you can simulate a pipeline run using mock data. Here are the steps to simulate a pipeline run:

1. **Use Mock Data**: Create mock data that mimics the structure of your real data. This allows you to test the pipeline logic without processing real data.

2. **Integrate Mock Data**: Replace the real data inputs in your pipeline with the mock data. This can be done by modifying the data loading steps in your pipeline to load mock data instead.

3. **Set Up a Test Environment**: Configure a test environment specifically for pipeline testing. This includes setting up isolated resources and configurations that do not affect your production environment.

4. **Test Scenarios**: Simulate common scenarios where testing the pipeline logic or configuration is beneficial. This includes verifying the pipeline's structure, flow, and error handling without executing real data processing.

By following these steps, you can effectively test and validate your pipeline configurations without the need for executing real data processing.