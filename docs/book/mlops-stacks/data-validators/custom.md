---
description: How to develop a custom Data Validator
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


{% hint style="warning" %}
**Base abstraction in progress!**

We are actively working on the base abstraction for the Data Validators, which 
will be available soon. As a result, their extension is not recommended at the 
moment. When you are selecting a data validator for your stack, you can use 
one of [the existing flavors](./data-validators.md#data-validator-flavors).

If you need to implement your own Data Validator flavor, you can still do so,
but keep in mind that you may have to refactor it when the base abstraction
is updated. 
{% endhint %}

ZenML comes equipped with [Data Validator implementations](./data-validators.md#data-validator-flavors)
that integrate a variety of data logging and validation libraries, frameworks
and platforms. However, if you need to use a different library or service as a
backend for your ZenML Data Validator, you can extend ZenML to provide your own
custom Data Validator implementation.

## Build your own custom data validator

If you want to implement your own custom Data Validator, you can follow the
following steps:

1. Create a class which inherits from [the `BaseDataValidator` class](https://apidocs.zenml.io/latest/api_docs/data_validators/#zenml.data_validators.base_data_validator.BaseDataValidator).
2. Define the `FLAVOR` class variable.
3. Override one or more of the `BaseDataValidator` methods, depending on the
capabilities of the underlying library/service that you want to integrate.
4. (Optional) You should also provide some standard steps that others can easily
insert into their pipelines for instant access to data validation features.

Once you are done with the implementation, you can register it through the CLI 
as:

```shell
zenml data-validator flavor register <THE-SOURCE-PATH-OF-YOUR-DATA-VALIDATOR>
```

ZenML includes a range of Data Validator implementations provided by specific
integration modules. You can use them as examples of how you can extend the [base Data Validator class](https://apidocs.zenml.io/latest/api_docs/data_validators/#zenml.data_validators.base_data_validator.BaseDataValidator)
to implement your own custom Data Validator:

|  Data Validator  | Implementation  |
|------------------|-----------------|
| [Deepchecks](./deepchecks.md) | [DeepchecksDataValidator](https://github.com/zenml-io/zenml/blob/main/src/zenml/integrations/deepchecks/data_validators/deepchecks_data_validator.py) |
| [Evidently](./evidently.md) | [EvidentlyDataValidator](https://github.com/zenml-io/zenml/blob/main/src/zenml/integrations/evidently/data_validators/evidently_data_validator.py) |
| [Great Expectations](./great-expectations.md) | [GreatExpectationsDataValidator](https://github.com/zenml-io/zenml/blob/main/src/zenml/integrations/great_expectations/data_validators/ge_data_validator.py) |
| [Whylogs/WhyLabs](./whylogs.md) | [WhylogsDataValidator](https://github.com/zenml-io/zenml/blob/main/src/zenml/integrations/whylogs/data_validators/whylogs_data_validator.py) |
