#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

from torch.utils.data import DataLoader
from torch import nn
import torch
from typing import List, Dict

import numpy as np
import matplotlib
from foxai.context_manager import FoXaiExplainer, ExplainerWithParams, CVClassificationExplainers
from foxai.visualizer import mean_channels_visualization

from zenml import step
from zenml.steps import Output


@step
def explain(model: nn.Module, test_dataloader: DataLoader) -> Output(
        explanation=List,
        figure_list=List,
):
    """Explain predictions of the model."""
    explainer_list = [
        ExplainerWithParams(explainer_name=CVClassificationExplainers.CV_GRADIENT_SHAP_EXPLAINER),
    ]
    device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
    model.to(device)

    figure_list: List[Dict[str, np.ndarray]] = []
    attributes_list: List[matplotlib.figure.Figure] = []
    counter: int = 0
    max_samples_to_explain: int = 20

    for sample_batch in test_dataloader:
        if counter > max_samples_to_explain:
            break

        sample_list, label_list = sample_batch
        # iterate over all samples in batch
        for sample, label in zip(sample_list, label_list):
            # add batch size dimension to the data sample
            input_data = sample.reshape(
                1,
                sample.shape[0],
                sample.shape[1],
                sample.shape[2],
            ).to(device) # move it to specified device

            with FoXaiExplainer(
                model=model,
                explainers=explainer_list,
                target=label,
            ) as xai_model:
                # calculate attributes for every explainer
                _, attributes_dict = xai_model(input_data)

            for key, value in attributes_dict.items():
                # create figure from attributes and original image          
                figure = mean_channels_visualization(
                    attributions=value[0],
                    transformed_img=sample,
                    title= f"Mean of channels ({key})",
                )
                figure_list.append(figure)

            for k, v in attributes_dict.items():
                attributes_dict[k] = v.detach().cpu().numpy()

            attributes_list.append(attributes_dict)

        counter += 1
    return attributes_list, figure_list
