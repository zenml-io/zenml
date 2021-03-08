# Natural Language Processing with ZenML

This example introduces a standard Natural Language Processing (NLP) workflow in ZenML.

The NLP ecosystem of choice for this example is [HuggingFace](https://github.com/huggingface). They provide many
convenience utilities such as tokenizers, models and datasets for use in pipelines. We want to showcase here how easy it
is to integrate these tools into a production ML setting with ZenML.

## Pre-requisites

In order to run this example, you need to clone the zenml repo.

```bash
git clone https://github.com/maiot-io/zenml.git
```

Before continuing, either [install the zenml pip package](https://docs.zenml.io/getting-started/installation.html) or
install it [from the cloned repo](../../zenml/README.md).

```
cd zenml
zenml init
cd examples/nlp
```

Also, you have to install some HuggingFace libraries to be able to proceed. To do that, in your ZenML virtual
environment run

```
pip install zenml[huggingface]
```

which installs the `transformers` and `tokenizers` libraries. Then, you can easily start up your first NLP pipeline by
navigating this example and executing the `run.py` script inside this folder.

```
zenml init
cd zenml/examples/nlp
python run.py
```

This will train a DistilBERT model on a corpus of fake news in Urdu. The data can be sourced as `urdu_fake_news` from
the HuggingFace `datasets` repository.

### Data citation

```
@article{MaazUrdufake2020,
    author = {Amjad, Maaz and Sidorov, Grigori and Zhila, Alisa and  G’{o}mez-Adorno, Helena and Voronkov, Ilia  and Gelbukh, Alexander},
    title = {Bend the Truth: A Benchmark Dataset for Fake News Detection in Urdu and Its Evaluation},
    journal={Journal of Intelligent & Fuzzy Systems},
    volume={39},
    number={2},
    pages={2457-2469},
    doi = {10.3233/JIFS-179905},
    year={2020},
    publisher={IOS Press}
}
```

## Caveats
As is shown in the `run.py` file, you can directly query a pipeline that was run locally with an example sentence. 
In order to do this, you have to define a `load_model` method in your `Trainer` step, as was done in the example.

## Next steps

If you are happy with your model performance, you can run some inference in the script by calling the pipeline object on
a sentence. This is designed with the similar mechanic from HuggingFace pipelines in mind. Otherwise, you can add
evaluation mechanics, although this is something that has not yet been tested, so stay tuned for that.

We hope you enjoyed this small tutorial, and catch you again for the next one!