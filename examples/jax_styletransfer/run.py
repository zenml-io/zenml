#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
import copy
from functools import partial

from PIL import Image
from urllib.request import urlopen
import time

import haiku as hk
import jax
import jax.numpy as jnp
from jax import tree_util
import optax
from zenml.logger import get_logger
from zenml.steps import step, Output
from zenml.steps.base_step_config import BaseStepConfig

from models import augmented_vgg19

logger = get_logger(__name__)

CONTENT_IMAGE = "https://pytorch.org/tutorials/_static/img/neural-style/dancing.jpg"
STYLE_IMAGE = "https://pytorch.org/tutorials/_static/img/neural-style/picasso.jpg"

tree_sum = partial(tree_util.tree_reduce, lambda x, y: x + y)


class JAXStyleTransferConfig(BaseStepConfig):
    image_size: int = 128
    content_weight: float = 1.
    style_weight: float = 1e4
    pooling: str = "max"
    num_steps: int = 100
    learning_rate: float = 0.001
    log_every: int = 50


def preprocess(input_image: Image, image_size: int = 512, dtype=None):
    """Load image into jax.numpy array, rescale values to 0-1, add batch axis."""
    input_image = input_image.resize((image_size, image_size))
    image = jnp.array(input_image, dtype=dtype)
    image = image / 255.  # normalize
    image = jnp.moveaxis(image, -1, 0)  # move channel axis to the front
    image = jnp.expand_dims(image, 0)  # add batch axis
    return image


@step
def image_loader() -> Output(content_image=jnp.ndarray, style_image=jnp.ndarray):
    """
    Load the content and style images from the Pytorch tutorial on neural style transfer.
    """
    content_image = preprocess(Image.open(urlopen(CONTENT_IMAGE)))
    style_image = preprocess(Image.open(urlopen(STYLE_IMAGE)))

    return content_image, style_image

@step
def trainer(
    config: JAXStyleTransferConfig, content_image: jnp.ndarray, style_image: jnp.ndarray
):

    weights = {"content_loss": config.content_weight,
               "style_loss": config.style_weight}

    def net_fn(image: jnp.ndarray, is_training: bool = False):
        vgg = augmented_vgg19(content_image=content_image,
                              style_image=style_image,
                              pooling=config.pooling)
        return vgg(image, is_training)

    def loss(trainable_params: hk.Params,
             non_trainable_params: hk.Params,
             current_state: hk.State,
             image: jnp.ndarray):

        merged_params = hk.data_structures.merge(trainable_params,
                                                 non_trainable_params)

        # stateful apply call, state contains the losses
        _, new_state = net.apply(merged_params, current_state,
                                 None, image, is_training=True)

        weighted_loss = hk.data_structures.map(
            # m: module name, n: parameter name, v: parameter value
            lambda m, n, v: weights[n] * v,
            new_state,
        )

        loss_val = tree_sum(weighted_loss)

        return loss_val, new_state

    @jax.jit
    def update(trainable_params: hk.Params,
               non_trainable_params: hk.Params,
               c_opt_state: optax.OptState,
               c_state: hk.State,
               image: jnp.ndarray):
        """Learning rule (stochastic gradient descent)."""
        (_, new_state), trainable_grads = (
            jax.value_and_grad(loss, has_aux=True)(
                trainable_params,
                non_trainable_params,
                c_state,
                image,
            )
        )

        # update trainable params
        updates, new_opt_state = opt.update(trainable_grads,
                                            c_opt_state,
                                            trainable_params)

        new_params = optax.apply_updates(trainable_params, updates)

        return new_params, new_opt_state, new_state

    net = hk.transform_with_state(net_fn)
    opt = optax.adam(learning_rate=config.learning_rate)

    input_image = copy.deepcopy(content_image)

    # Initialize network and optimiser, supply an input to get shapes.
    full_params, state = net.init(None, input_image, False)

    # split params into trainable and non-trainable
    t_params, nt_params = hk.data_structures.partition(
        lambda m, n, v: m == "norm",
        full_params,
    )

    opt_state = opt.init(t_params)

    num_params = hk.data_structures.tree_size(full_params)
    num_t_params = hk.data_structures.tree_size(t_params)
    mem = hk.data_structures.tree_bytes(full_params)

    logger.info(f"Total number of parameters: {num_params}")
    logger.info(f"Number of trainable parameters: {num_t_params}")
    logger.info(f"Number of non-trainable parameters: {num_params - num_t_params}")
    logger.info(f"Memory footprint of network parameters: {mem / 1e6:.2f} MB")
    logger.info("Starting style transfer optimization loop.")

    start = time.time()

    for i in range(config.num_steps):
        # state holds content and style loss values
        t_params, opt_state, state = update(
            t_params,
            nt_params,
            opt_state,
            state,
            input_image,
        )

        if (i + 1) % config.log_every == 0:
            c_loss_tree, s_loss_tree = hk.data_structures.partition(
                lambda m, n, v: n == "content_loss",
                state,
            )
            content_loss, style_loss = tree_sum(c_loss_tree), tree_sum(s_loss_tree)

            logger.debug(
                f"Iteration: {step} Content loss: {content_loss:.4f} Style loss: {style_loss:.4f}"
            )

    logger.info(f"Style transfer finished. Took {(time.time() - start):.2f} secs.")


if __name__ == '__main__':
    pass
