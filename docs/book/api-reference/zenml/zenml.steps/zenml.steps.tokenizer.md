# Tokenizer

&lt;!DOCTYPE html&gt;

zenml.steps.tokenizer package — ZenML documentation  [ZenML](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/modules.html)
*  [Page](zenml.steps.tokenizer.md)
  * * [zenml.steps.tokenizer package](zenml.steps.tokenizer.md)
      * [Submodules](zenml.steps.tokenizer.md#submodules)
      * [zenml.steps.tokenizer.base\_tokenizer module](zenml.steps.tokenizer.md#module-zenml.steps.tokenizer.base_tokenizer)
      * [zenml.steps.tokenizer.hf\_tokenizer module](zenml.steps.tokenizer.md#module-zenml.steps.tokenizer.hf_tokenizer)
      * [zenml.steps.tokenizer.utils module](zenml.steps.tokenizer.md#module-zenml.steps.tokenizer.utils)
      * [Module contents](zenml.steps.tokenizer.md#module-zenml.steps.tokenizer)
* [ « zenml.steps.s...](zenml.steps.split.md)
* [ zenml.steps.t... »](zenml.steps.trainer/)
*  [Source](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/_sources/zenml.steps.tokenizer.rst.txt)

## zenml.steps.tokenizer package[¶](zenml.steps.tokenizer.md#zenml-steps-tokenizer-package)

### Submodules[¶](zenml.steps.tokenizer.md#submodules)

### zenml.steps.tokenizer.base\_tokenizer module[¶](zenml.steps.tokenizer.md#module-zenml.steps.tokenizer.base_tokenizer)

 _class_ `zenml.steps.tokenizer.base_tokenizer.BaseTokenizer`\(_text\_feature: str_, _skip\_training: bool = False_, _\*\*kwargs_\)[¶](zenml.steps.tokenizer.md#zenml.steps.tokenizer.base_tokenizer.BaseTokenizer)

Bases: [`zenml.steps.base_step.BaseStep`](./#zenml.steps.base_step.BaseStep)

Base step class for all tokenizers. `encode`\(_sequence: str_, _output\_format: str_\)[¶](zenml.steps.tokenizer.md#zenml.steps.tokenizer.base_tokenizer.BaseTokenizer.encode) `load_vocab`\(_path\_to\_vocab: str_\)[¶](zenml.steps.tokenizer.md#zenml.steps.tokenizer.base_tokenizer.BaseTokenizer.load_vocab) `save`\(_output\_dir: str_\)[¶](zenml.steps.tokenizer.md#zenml.steps.tokenizer.base_tokenizer.BaseTokenizer.save) `train`\(_files: List\[str\]_\)[¶](zenml.steps.tokenizer.md#zenml.steps.tokenizer.base_tokenizer.BaseTokenizer.train)

### zenml.steps.tokenizer.hf\_tokenizer module[¶](zenml.steps.tokenizer.md#module-zenml.steps.tokenizer.hf_tokenizer)

 _class_ `zenml.steps.tokenizer.hf_tokenizer.HuggingFaceTokenizerStep`\(_text\_feature: str_, _tokenizer: str_, _tokenizer\_params: Dict\[str, Any\] = None_, _skip\_training: bool = False_, _vocab\_size: int = 30000_, _min\_frequency: int = 2_, _sentence\_length: int = 128_, _special\_tokens: List\[str\] = None_, _batch\_size: int = 64_, _\*\*kwargs_\)[¶](zenml.steps.tokenizer.md#zenml.steps.tokenizer.hf_tokenizer.HuggingFaceTokenizerStep)

Bases: [`zenml.steps.tokenizer.base_tokenizer.BaseTokenizer`](zenml.steps.tokenizer.md#zenml.steps.tokenizer.base_tokenizer.BaseTokenizer)

Base step for Tokenizer usage in NLP pipelines.

This step can be used in Natural Language Processing \(NLP\) pipelines, where tokenization is a special form of preprocessing for text data in sequence form.

This step was primarily designed to integrate the Huggingface ecosystem \(transformers, tokenizers, datasets\) into ZenML. Other tokenization libraries can work with this step, but are not guaranteed to work. `encode`\(_sequence: str_, _output\_format: str = 'tf\_example'_\)[¶](zenml.steps.tokenizer.md#zenml.steps.tokenizer.hf_tokenizer.HuggingFaceTokenizerStep.encode)

Encode a sentence with the tokenizer in this class and output it into the specified output format. Supported return types are “tf\_tensors”, returning a dictionary of tensorflow tensor objects, “dict”, returning a dictionary of lists, and “tf\_example”, returning a tf.train.Example proto file.Parameters

* **sequence** – String, sentence to encode with the trained tokenizer.
* **output\_format** – String specifying output format. Can be either tf\_tensors, dict or tf\_example.

Returns

A representation of the sentence in IDs based on the vocabulary

of the tokenizer.

 `load_vocab`\(_path\_to\_vocab: str_\)[¶](zenml.steps.tokenizer.md#zenml.steps.tokenizer.hf_tokenizer.HuggingFaceTokenizerStep.load_vocab)

Re-instantiate the class tokenizer with output vocabulary / merges.Parameters

**path\_to\_vocab** – Path to vocab / merges files from a training run. `save`\(_output\_dir: str_\)[¶](zenml.steps.tokenizer.md#zenml.steps.tokenizer.hf_tokenizer.HuggingFaceTokenizerStep.save)

Save a trained tokenizer model to disk.Parameters

**output\_dir** – Path to which to save the trained tokenizer. `train`\(_files: List\[str\]_\)[¶](zenml.steps.tokenizer.md#zenml.steps.tokenizer.hf_tokenizer.HuggingFaceTokenizerStep.train)

Method for training a tokenizer on a data iterator. The iterator is constructed inside the function in a closure from a TFRecord dataset.Parameters

**files** – List of TFRecord files in GZIP format to ingest.

### zenml.steps.tokenizer.utils module[¶](zenml.steps.tokenizer.md#module-zenml.steps.tokenizer.utils)

### Module contents[¶](zenml.steps.tokenizer.md#module-zenml.steps.tokenizer)

 [Back to top](zenml.steps.tokenizer.md)

 © Copyright 2021, maiot GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 3.3.1.  


