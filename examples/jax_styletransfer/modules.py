from typing import Optional

import haiku as hk
import jax
import jax.numpy as jnp

# ImageNet statistics
imagenet_mean = jnp.array([0.485, 0.456, 0.406])
imagenet_std = jnp.array([0.229, 0.224, 0.225])


def gram_matrix(x: jnp.ndarray):
    """Computes the Gram Matrix of an input tensor x."""
    n, c, h, w = x.shape

    assert n == 1, "style transfer mini-batch has to be singular"

    features = jnp.reshape(x, (n * c, h * w))

    return jnp.dot(features, features.T) / (n * c * h * w)


class StyleLoss(hk.Module):
    """Identity layer capturing the style loss between input and target."""

    def __init__(self, target: jnp.ndarray, name: Optional[str] = None):
        super(StyleLoss, self).__init__(name=name)
        self.target_g = jax.lax.stop_gradient(gram_matrix(target))

    def __call__(self, x: jnp.ndarray):
        g = gram_matrix(x)

        style_loss = jnp.mean(jnp.square(g - self.target_g))
        hk.set_state("style_loss", style_loss)

        return x


class ContentLoss(hk.Module):
    """Identity layer capturing the content loss between input and target."""

    def __init__(self, target: jnp.ndarray, name: Optional[str] = None):
        super(ContentLoss, self).__init__(name=name)
        self.target = jax.lax.stop_gradient(target)

    def __call__(self, x: jnp.ndarray):
        content_loss = jnp.mean(jnp.square(x - self.target))
        hk.set_state("content_loss", content_loss)

        return x


class Normalization(hk.Module):
    # A module normalizing an input image to ImageNet statistics.

    def __init__(self,
                 image: jnp.ndarray,
                 mean: jnp.ndarray = imagenet_mean,
                 std: jnp.ndarray = imagenet_std,
                 name: Optional[str] = None):
        super(Normalization, self).__init__(name=name)

        # bind image to class to make it a trainable parameter
        self.image = image

        # expand mean and std to shape [C x 1 x 1] so they can
        # be broadcast onto images of shape [N x C x H x W].
        self.mean = jnp.expand_dims(mean, (1, 2))
        self.std = jnp.expand_dims(std, (1, 2))

    def __call__(self, x: jnp.ndarray, is_training: bool = False):
        # Throw away the input and use the tracked parameter instead.
        # This assures that the image is actually styled
        img = hk.get_parameter("image",
                               shape=self.image.shape,
                               dtype=self.image.dtype,
                               init=hk.initializers.Constant(self.image))

        if is_training:
            out = img
        else:
            out = x

        return (out - self.mean) / self.std
