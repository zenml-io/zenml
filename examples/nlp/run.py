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

from zenml.core.pipelines.nlp_pipeline import NLPPipeline
from zenml.core.steps.trainer.nlp_tokenizers.hf_tokenizer import \
    TokenizerStep
from zenml.core.steps.split.random_split import RandomSplit
from zenml.core.datasources.csv_datasource import CSVDatasource
from zenml.core.repo.repo import Repository
from zenml.utils.exceptions import AlreadyExistsException
from examples.nlp.training.trainer import UrduTrainer


base_path = "/Users/nicholasjunge/workspaces/ml/data/urdu_fake_news/" \
            "urdu_fake_news_small.csv"

try:
    nlp_pipeline = NLPPipeline(name="nlp_test")
except AlreadyExistsException:
    nlp_pipeline = Repository.get_instance().get_pipeline_by_name("nlp_test")

try:
    ds = CSVDatasource(name="my_text", path=base_path)
except AlreadyExistsException:
    ds = Repository.get_instance().get_datasource_by_name(name="my_text")

nlp_pipeline.add_datasource(ds)

tokenizer_step = TokenizerStep(text_feature="news",
                               vocab_size=3000,
                               min_frequency=2,
                               # special_tokens=[
                               #     "<s>",
                               #     "<pad>",
                               #     "</s>",
                               #     "<unk>",
                               #     "<mask>",
                               # ]
                               )

nlp_pipeline.add_tokenizer(tokenizer_step=tokenizer_step)

nlp_pipeline.add_split(RandomSplit(split_map={"train": 0.9,
                                              "eval": 0.1}))

nlp_pipeline.add_trainer(UrduTrainer(epochs=1, batch_size=16))

nlp_pipeline.run()

nlp_pipeline("دنیا سیدھی ہے")
