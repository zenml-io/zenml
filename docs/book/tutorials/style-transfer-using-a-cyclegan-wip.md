---
description: We make a Neural Network paint like Monet!
---

# Style Transfer using a CycleGAN \[WIP\]

Generative Neural Networks are a very different story compared to "normal" Neural Networks. Since they are trained to learn the probability distribution from data rather than the marginal distribution of a target feature, you can sample them just like any other probability distribution and "create" your own data. A very well-known example of this is the **Generative Adversarial Network** \(GAN\), in which two rival networks are trained to generate realistic data based on a training input. 

A visually appealing example of this type of architecture is the **CycleGAN.** Conceptually, it is an adversarial network designed to learn a mapping between two different datasets, in order to be able to create data from one or the other. A lot of additional information, as well as some examples for this concept, can be found on the original paper author's page [here](https://junyanz.github.io/CycleGAN/).

Now we want to take real photographs and use a CycleGAN network to turn it into something that looks just like a Monet painting. This concept is commonly called Style Transfer - with it, you could for example take any painter's style and apply it to your heart's content on any image, creating a perfectly realistic rendition of that image in that painter's style, provided you have enough real sample paintings to sufficiently train such a network.

![Monet&apos;s lost work?!?](../assets/monet.png)

