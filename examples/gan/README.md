This folder contains an example ZenML pipeline for a Style Transfer workflow using the CycleGAN architecture.

Most of the code for the actual Tensorflow implementation of the CycleGAN model was taken from
the [CycleGAN tutorial](https://www.tensorflow.org/tutorials/generative/cyclegan) in the Tensorflow documentation.

The data for this tutorial has been sourced from and is licensed according
to [the original CycleGAN repository](https://github.com/junyanz/CycleGAN).

The code for the tutorial is structured according to our recommendation on repository structure. The `preprocessing`
folder contains the preprocessing code and ZenML step. The `trainer` folder contains the CycleGAN model implementation
as well as the TrainerStep that handles data sourcing and preparation.

The `gan_run.py` script can be used to run the CycleGAN pipeline locally using a persisted local download of the 
Monet image dataset. The only thing that has to be adjusted is the base folder for the images.

The `prepare_gan_images.py` script can be used to generate a labels.json file for use in the ZenML image pipeline.
Simply set the (hardcoded) paths inside the file to the image folder locations on your machine.

The `cycle_gan.ipynb` notebook is the main Jupyter Notebook object of this tutorial. Executing it runs a ZenML pipeline
on an example image dataset persisted in a public Google Cloud Storage bucket .

The `cycle_gan_serving.ipynb` notebook is a demo on how to query a model deployed on Google Cloud AI Platform (GCAIP)
for predictions. Please refer to the ZenML documentation on how to train and deploy models on AI Platform.