# Styling images using a Generative Adversarial Network

This folder contains an example ZenML pipeline for a Style Transfer workflow using the CycleGAN architecture.

Most of the code for the actual Tensorflow implementation of the CycleGAN model was taken from
the [CycleGAN tutorial](https://www.tensorflow.org/tutorials/generative/cyclegan) in the Tensorflow documentation.

The data for this tutorial has been sourced from and is licensed according
to [the original CycleGAN repository](https://github.com/junyanz/CycleGAN).

## Citation
```
Unpaired Image-to-Image Translation using Cycle-Consistent Adversarial Networks.

Jun-Yan Zhu*, Taesung Park*, Phillip Isola, Alexei A. Efros

Berkeley AI Research Lab, UC Berkeley

IEEE International Conference on Computer Vision (ICCV) 2017. (* equal contributions)
```
## Code explanation

The code for the tutorial is structured according to our recommendation on repository structure. The `preprocessing`
folder contains the preprocessing code and ZenML step. The `trainer` folder contains the CycleGAN model implementation
as well as the TrainerStep that handles data sourcing and preparation.

The `prepare_gan_images.py` script can be used to generate a labels.json file for use in the ZenML image pipeline.
Simply set the (hardcoded) paths inside the file to the image folder locations on your machine. The script assumes a 
certain folder structure:
```
base_dir -> monet_jpg
         -> real_jpg
```
where `monet_jpg` and `real_jpg` need to be subdirectories of your base directory which contain the Monet paintings and
the real images, respectively.

The `cycle_gan.ipynb` notebook is the main Jupyter Notebook object of this tutorial. Executing it runs a ZenML pipeline
on an example image dataset persisted in a public Google Cloud Storage bucket. In addition, it contains an optional 
tutorial on running the same workload with a deployment step on Google Cloud AI Platform, and shows how to obtain 
styled images by sending prediction requests to the deployed model over a Google API client.

## Pre-requisites
In order to run this example, you need to clone the zenml repo.

```bash
git clone https://github.com/maiot-io/zenml.git
```

Before continuing, either [install the zenml pip package](https://docs.zenml.io/getting-started/installation.html) or install it [from the cloned repo](../../zenml/README.md). 
In both cases, make sure to also install the gcp extension (e.g. with pip: `pip install zenml[gcp]`)

```
cd zenml
zenml init
cd examples/gan
```

In addition, you will have to install `tensorflow_addons` by typing
```
pip install tensorflow_addons
```
in your virtual environment.

## Run the project
Now we're ready. Execute:

```bash
python run.py
```

This will train a CycleGAN model on the image data. Since the network has a large amount of down- and upsampling layers,
this may take a while.


## Caveats 

This example uses ZenML's image datasource to ingest images from a filesystem. In order to include features and
metadata, you have to supply a `labels.json` file that contains all of this information for each image. To generate 
such a label file, you can use the supplied `prepare_gan_images.py` script.

## Next steps

If you are not satisfied with the generated images, you can try adjusting the hyperparameters and see how they impact 
the output images. Also, you can deploy your model to Google Cloud AI Platform by executing the second part of the 
[Jupyter Notebook](./cycle_gan.ipynb), and then use it to generate images via REST requests.