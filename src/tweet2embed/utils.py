#   For command line
import base64

#   File and Bits
import io

# Formatting
import os
import tempfile

#   Etc
import requests
from jinja2 import Environment, PackageLoader, select_autoescape

#   Image Manipulation
from PIL import Image

jinja_env = Environment(
    loader=PackageLoader("tweet2embed"), autoescape=select_autoescape()
)


class TweetFetchingError(Exception):
    pass


def image_to_inline(url, session=None):
    if session is None:
        session = requests.Session()

    # Download the image
    image_file = session.get(url)
    # Convert to bytes
    image_file = Image.open(io.BytesIO(image_file.content))
    # Temp file name with only alphanumeric characters
    temp_file_name = "".join(x for x in url if x.isalnum())
    # Full path of the image
    output_img = os.path.join(tempfile.gettempdir(), f"{temp_file_name}.webp")
    # Save as a low quality WebP
    image_file.save(output_img, "webp", optimize=True, quality=60)
    #   Convert image to base64 data URl
    # Read the image from disk
    binary_img = open(output_img, "rb").read()
    # Encode to Base64
    base64_utf8_str = base64.b64encode(binary_img).decode("utf-8")
    # Delete the temporary file
    os.remove(output_img)
    # Return as data encoded suitable for an <img src="...">
    return f"data:image/webp;base64,{base64_utf8_str}"


def archive_url(url, session=None):
    if session is None:
        session = requests.Session()

    # Submit the URL to Archive.org
    session.post(
        "https://web.archive.org/save/",
        data={"url": url, "capture_all": "on"},
        timeout=5,
    )
    print(f"Archiving… {url}")
