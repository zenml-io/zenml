import tensorflow as tf
import os
import json
from shutil import copyfile


# change this to your base directory
image_base_dir = "/Users/nicholasjunge/workspaces/maiot/ce_project"
monet_dir = "monet_jpg"  # change this to your monet directory
real_dir = "photo_jpg"  # change this to your photo directory
image_ext = ".jpg"

# change this to your desired output directory
out_dir = "/Users/nicholasjunge/workspaces/maiot/ce_project/images_mini"

# change this number to adjust the dataset size.
NUM_IMGS = 2


def prepare_gan_image_dir(num=100):

    if not os.path.exists(out_dir):
        os.mkdir(out_dir)

    monet_imgs = tf.io.gfile.glob(
        os.path.join(image_base_dir, monet_dir, "*" + image_ext))

    real_imgs = tf.io.gfile.glob(
        os.path.join(image_base_dir, real_dir, "*" + image_ext))

    label_dict = {}

    for img_set in [monet_imgs, real_imgs]:
        for i, img in enumerate(img_set):
            if i == num:
                break
            with open(img, "rb") as img_file:
                monet_img_raw = img_file.read()
            monet_img = tf.io.decode_image(monet_img_raw).numpy()
            metadata = dict(zip(["height", "width", "num_channels"],
                                monet_img.shape))
            file_name = os.path.basename(img)
            copyfile(img, os.path.join(out_dir, file_name))

            label = "monet" if monet_dir in img else "real"
            label_dict[file_name] = {"label": label, "metadata": metadata}

    json_outpath = os.path.join(out_dir, "labels.json")
    with open(json_outpath, "w") as fp:
        json.dump(label_dict, fp)


if __name__ == "__main__":
    prepare_gan_image_dir(num=NUM_IMGS)
