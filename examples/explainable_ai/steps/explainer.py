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

import shap
from shap.plots import image
from foxai.context_manager import FoXaiExplainer, ExplainerWithParams, CVClassificationExplainers
from foxai.visualizer import mean_channels_visualization

from zenml import step
from zenml.steps import Output
from zenml.types import HTMLString

import mpld3
import numpy as np

import matplotlib.pyplot as plt
from enum import Enum


class ExplainerType(Enum):
    FOXAI = "foxai"
    SHAP = "shap"


def create_figure_list_html(figure_list: List[matplotlib.figure.Figure]) -> str:
    # convert matplotlib.figure.Figure to HTML string
    figure_html_list = [mpld3.fig_to_html(figure) for figure in figure_list]

    # construct HTML list of Figures to display
    figure_string = "<ul>"
    for fig in figure_html_list:
        figure_string = f"{figure_string}<li>{fig}</li>"
    figure_string = f"{figure_string}</ul>"
    return figure_string


@step(enable_cache=False)
def explain_foxai(
    model: nn.Module,
    test_dataloader: DataLoader,
    classes: List[str],
) -> Output(
        figure_list=HTMLString,
        explanation=Dict,
):
    """Explain predictions of the model."""
    explainer_list = [
        ExplainerWithParams(explainer_name=CVClassificationExplainers.CV_LAYER_GRADCAM_EXPLAINER),
        ExplainerWithParams(explainer_name=CVClassificationExplainers.CV_DECONVOLUTION_EXPLAINER),
    ]
    device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
    model.to(device)

    idx2label = {index: label for index, label in enumerate(classes)}

    attributes_list: List[Dict[str, np.ndarray]] = []
    figure_list: List[matplotlib.figure.Figure] = []
    counter: int = 0
    max_samples_to_explain: int = 10

    for sample_batch in test_dataloader:
        if counter > max_samples_to_explain:
            break

        sample_list, targets_list = sample_batch
        # iterate over all samples in batch
        for sample, class_no in zip(sample_list, targets_list):
            # add batch size dimension to the data sample
            if counter > max_samples_to_explain:
                break
            input_data = sample.reshape(
                1,
                sample.shape[0],
                sample.shape[1],
                sample.shape[2],
            ).to(device) # move it to specified device

            label = idx2label[class_no.item()]
            with FoXaiExplainer(
                model=model,
                explainers=explainer_list,
                target=class_no,
            ) as xai_model:
                # calculate attributes for every explainer
                _, attributes_dict = xai_model(input_data)

            org_figure = mean_channels_visualization(
                attributions=sample,
                title=f"Original image. Class: {label}",
                transformed_img=sample,
                alpha=0.0,
            )
            figure_list.append(org_figure)

            for key, value in attributes_dict.items():
                # create figure from attributes and original image          
                figure = mean_channels_visualization(
                    attributions=value[0],
                    transformed_img=sample,
                    title= f"Mean of channels ({key}). Class: {label}",
                )
                figure_list.append(figure)

            for k, v in attributes_dict.items():
                print(k, type(v), v.shape)
                attributes_dict[k] = v.detach().cpu().numpy()

            attributes_list.append(attributes_dict)

            counter += 1

    figure_string = create_figure_list_html(figure_list=figure_list)

    return HTMLString(figure_string), attributes_dict

@step(enable_cache=False)
def explain_shap(
    model: nn.Module,
    test_dataloader: DataLoader,
    classes: List[str], # mypy: disable = unused-argument
) -> Output(
        figure_list=HTMLString,
        explanation=List,
):
    """Explain predictions of the model."""
    device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
    model.to(device)

    attributes_list: List[Dict[str, np.ndarray]] = []
    counter: int = 0
    max_samples_to_explain: int = 100

    selected_sample_list = []
    for sample_batch in test_dataloader:
        if counter > max_samples_to_explain:
            break

        sample_list, targets_list = sample_batch
        # iterate over all samples in batch
        for sample, _ in zip(sample_list, targets_list):
            if counter > max_samples_to_explain:
                break

            selected_sample_list.append(sample)

    selected_sample_list = torch.stack(selected_sample_list).to(device)

    background = selected_sample_list[0:100]
    test_images = selected_sample_list[25:30]
    explainer = shap.DeepExplainer(model, background)
    shap_values = explainer.shap_values(test_images)
    attributes_list.append({"shap": shap_values})

    shap_numpy = [np.swapaxes(np.swapaxes(s, 1, -1), 1, 2) for s in shap_values]
    test_numpy = np.swapaxes(np.swapaxes(test_images.cpu().detach().numpy(), 1, -1), 1, 2)

    image(shap_numpy, -test_numpy, show=True)
    # get current figure
    figure = plt.gcf()

    figure_string = create_figure_list_html(figure_list=[figure])

    return HTMLString(figure_string), attributes_list
