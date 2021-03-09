import tensorflow as tf
import os
import json
import argparse
from shutil import copyfile

parser = argparse.ArgumentParser(
    description="Process images and create metadata JSON file.")

parser.add_argument("input_dir", type=str,
                    default="gs://zenml_quickstart/cycle_gan_mini",
                    help="directory containing the images.")

parser.add_argument("output_dir", type=str, default=".",
                    help="output_directory for the processed images.")

parser.add_argument("--max_imgs", type=int, default=1 << 30,
                    help="Maximum number of images to process.")

monet_dir = "monet_jpg"  # change this to your monet directory
real_dir = "photo_jpg"  # change this to your photo directory
image_ext = ".jpg"


def prepare_gan_image_dir(input_dir, output_dir, max_imgs):

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    monet_imgs = tf.io.gfile.glob(
        os.path.join(input_dir, monet_dir, "*" + image_ext))

    real_imgs = tf.io.gfile.glob(
        os.path.join(input_dir, real_dir, "*" + image_ext))

    label_dict = {}

    for img_set in [monet_imgs, real_imgs]:
        for i, img in enumerate(img_set):
            if i == max_imgs:
                break
            with open(img, "rb") as img_file:
                monet_img_raw = img_file.read()
            monet_img = tf.io.decode_image(monet_img_raw).numpy()
            metadata = dict(zip(["height", "width", "num_channels"],
                                monet_img.shape))
            file_name = os.path.basename(img)
            copyfile(img, os.path.join(output_dir, file_name))

            label = "monet" if monet_dir in img else "real"
            label_dict[file_name] = {"label": label, "metadata": metadata}

    json_outpath = os.path.join(output_dir, "labels.json")
    with open(json_outpath, "w") as fp:
        json.dump(label_dict, fp)


if __name__ == "__main__":
    args = parser.parse_args()

    prepare_gan_image_dir(input_dir=args.input_dir,
                          output_dir=args.output_dir,
                          max_imgs=args.max_imgs)
