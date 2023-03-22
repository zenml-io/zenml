import base64

IMG_PATH = "docs/mkdocs/_assets/favicon.png"

with open(IMG_PATH, "rb") as image2string:
    converted_string = base64.b64encode(image2string.read())
print(type(converted_string))

with open("img.png", "wb") as file:
    file.write(base64.b64decode((converted_string)))
