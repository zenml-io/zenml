from typing import List
from urllib.request import urlretrieve

import h5py
import haiku as hk
import jax
import jax.numpy as jnp

from modules import StyleLoss, ContentLoss, Normalization

__all__ = ["augmented_vgg19"]

MODEL = "https://github.com/fchollet/deep-learning-models/releases/download/v0.1/vgg19_weights_tf_dim_ordering_tf_kernels_notop.h5"


def augmented_vgg19(content_image: jnp.ndarray,
                    style_image: jnp.ndarray,
                    content_layers: List[str] = None,
                    style_layers: List[str] = None,
                    pooling: str = "max") -> hk.Sequential:
    """Build a VGG19 network augmented by content and style loss layers."""
    pooling = pooling.lower()
    poolings = {"avg": hk.AvgPool, "max": hk.MaxPool}

    if pooling not in poolings:
        raise ValueError("Pooling method not recognized. Options are: "
                         f"{', '.join(repr(p) for p in poolings)}.")

    tmp_path, _ = urlretrieve(MODEL, None)

    vgg19_weights = h5py.File(tmp_path, 'r')

    params = dict()
    # layers (weights + biases) are arranged in h5.Groups
    for name, group in vgg19_weights.items():
        weights = dict()
        for k, v in group.items():
            v = jnp.array(v)
            if len(v.shape) == 1:
                v = jnp.expand_dims(v, (1, 2))

            weights[k] = v

        params[name] = weights

    # prepend a normalization layer
    layers = [Normalization(content_image, name="norm")]

    # index of last content/style loss layer
    last_layer = 0

    # desired depth layers to compute style/content losses
    content_layers = content_layers or []
    style_layers = style_layers or []

    model = hk.Sequential(layers=layers)

    for name, p_dict in params.items():
        if "pool" in name:
            layers.append(poolings.get(pooling)(window_shape=2,
                                         strides=2,
                                         padding="VALID",
                                         channel_axis=1,
                                         name=f"{name}_{pooling}_pool"))
        elif "conv" in name:
            w_init, b_init = None, None
            for k, v in p_dict.items():
                # p_dict contains exactly two arrays, W and b
                if "W" in k:
                    w_init = hk.initializers.Constant(v)
                elif "b" in k:
                    b_init = hk.initializers.Constant(v)

            assert w_init is not None, f"missing weights for convolution {name!r}"
            h, w, input_channels, output_channels = w_init.constant.shape

            layers.append(hk.Conv2D(
                output_channels=output_channels,
                kernel_shape=(h, w),
                stride=1,
                padding="SAME",
                data_format="NCHW",
                w_init=w_init,
                b_init=b_init,
                name=name)
            )

            if name in style_layers:
                last_layer = len(layers) + 1
                model.layers = tuple(layers)
                style_target = model(style_image, is_training=False)
                layers.append(StyleLoss(target=style_target,
                                        name=f"{name}_style_loss"))

            if name in content_layers:
                last_layer = len(layers) + 1
                model.layers = tuple(layers)
                content_target = model(content_image, is_training=False)
                layers.append(ContentLoss(target=content_target,
                                          name=f"{name}_content_loss"))

            layers.append(jax.nn.relu)

    model.layers = tuple(layers[:last_layer])

    return model
