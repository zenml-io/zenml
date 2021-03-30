#  Copyright (c) maiot GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

from training.trainer import UrduTrainer
from zenml.datasources import CSVDatasource
from zenml.exceptions import AlreadyExistsException
from zenml.pipelines import NLPPipeline
from zenml.repo import Repository
from zenml.steps.split import RandomSplit
from zenml.steps.tokenizer import HuggingFaceTokenizerStep

nlp_pipeline = NLPPipeline()

try:
    ds = CSVDatasource(name="My Urdu Text",
                       path="gs://zenml_quickstart/urdu_fake_news.csv")
except AlreadyExistsException:
    ds = Repository.get_instance().get_datasource_by_name(name="My Urdu Text")

nlp_pipeline.add_datasource(ds)

tokenizer_step = HuggingFaceTokenizerStep(
    text_feature="news",
    tokenizer="bert-wordpiece",
    vocab_size=3000)

nlp_pipeline.add_tokenizer(tokenizer_step=tokenizer_step)

nlp_pipeline.add_split(RandomSplit(
    split_map={'train': 0.7, 'eval': 0.2, 'test': 0.1}))

nlp_pipeline.add_trainer(
    UrduTrainer(
        model_name="distilbert-base-uncased",
        epochs=3,
        batch_size=64,
        learning_rate=5e-3)
)

nlp_pipeline.run()

# evaluate the model with the sentence "The earth is flat"
# which should (ideally) return FAKE_NEWS
nlp_pipeline.predict_sentence("دنیا سیدھی ہے")
