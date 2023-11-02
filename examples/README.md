# ZenML Use Cases

This folder contains examples of ZenML pipelines. These are more involved use
cases with production-ready pipelines, with the exception of
some that will be indicated in the table below.

These core demonstrations of ZenML showcase the power of the framework in real
scenarios that use cloud infrastructure or other cloud components.
Explanations for how to use and run the use cases can be found in the README
associated with each sub-folder.

{% hint style="info" %}
This directory previously contained examples of ZenML integrations and how to
use them. These have been ingested into the core library as integration tests.
It is therefore still possible to view the code at
[`/tests/integration/examples`](https://github.com/zenml-io/zenml/tree/main/tests/integration/examples)
but for explanations on how to use them, please refer to our dedicated [Component
guide](https://docs.zenml.io/stacks-and-components/component-guide) in our
documentation which has been updated with all the latest information.
{% endhint %}

Note that our full use cases are all implemented as templates so you can start
with our code and then adapt the specifics to your individual needs. To learn
more about how to do this, please [visit our dedicated documentation
page](https://docs.zenml.io/user-guide/starter-guide/using-project-templates) on
this.

| Name | Description | Integrations | Core Project |
| ---- | ----------- | ------------ | ------------ |
| quickstart | This is our quickstart example showcasing basic functionality and a workflow to get you started with the ZenML framework | mlflow | ✅ |
| e2e | Trains one or more scikit-learn classification models to make predictions on tabular classification datasets | scikit-learn | ✅ |
| generative_chat | LEGACY: constructs a vector store to be used by a LLM-based chatbot based on documentation and data from a variety of sources | langchain, llama-index, slack |   |
| label_studio_annotation | LEGACY: shows how to use the Label Studio integration for annotation in a computer-vision use case and series of pipelines | label_studio, pillow |   |
| label_studio_text_annotation | LEGACY: shows how to use the Label Studio integration in a NLP / text-based use case and series of pipelines | label_studio |   |

## ❓ Questions / Further Assistance

If you have any questions about how to get going with these use cases, or if
you're wondering how you can adapt them to your particular needs, please do
[reach out to us on Slack](https://zenml.io/slack-invite/)!
