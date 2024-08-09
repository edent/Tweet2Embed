#   For command line
import argparse

#   Sleeping
import time

#   File and Bits
import io
import os
import tempfile

#   Image Manipulation
from PIL import Image

#   Selenium
from selenium import webdriver 
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

#   Firefox specific
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager

#   Etc
import requests
import pyperclip
import base64
import html

#   If using Chrome
# from selenium.webdriver.chrome.options import Options

#   Command line options
parser = argparse.ArgumentParser(
    prog='tweet2img',
    description='Convert a Tweet ID to an image and alt text')
parser.add_argument('id',       type=int,            help='ID of the Tweet (integer)')
parser.add_argument('--thread', action='store_true', help='Show the thread (default false)', required=False)

args = parser.parse_args()
tweet_id = args.id
thread = args.thread

if ( True == thread ):
    hide_thread = "false"
else :
    hide_thread = "true"

# #   Chrome's Headless Options
# chrome_options = Options()
# chrome_options.add_argument('--headless=new')
# chrome_options.add_argument('--window-size=1920,2160')

# #   Turn off everything
# chrome_options.add_argument("--no-sandbox")
# chrome_options.add_argument("--disable-dev-shm-usage")
# chrome_options.add_argument("--disable-extensions")
# chrome_options.add_argument("--disable-infobars")
# chrome_options.add_argument("--disable-logging")
# chrome_options.add_argument("--log-level=3")
# chrome_options.add_argument('--force-device-scale-factor=1')
# chrome_options.add_argument('--high-dpi-support=1')

# #   Wayland to stop fuzzyness on fractional scaling
# chrome_options.add_argument("--enable-features=UseOzonePlatform")
# chrome_options.add_argument("--ozone-platform=wayland")

# #   Start Chrome
# driver = webdriver.Chrome(options=chrome_options)

#   Firefox's Headless Options
firefox_options = Options()
firefox_options.add_argument("--headless")
#   Start Firefox
driver = webdriver.Firefox( options=firefox_options )

#   Open the Tweet on the embed platform
driver.get(f"https://platform.twitter.com/embed/Tweet.html?hideCard=false&hideThread={hide_thread}&lang=en&theme=light&width=550px&id={tweet_id}")

#   Wait for page to fully render
time.sleep(3)

#   Get the Tweet
tweet = driver.find_element(By.TAG_NAME, "article")
#   Use the parent element for more padding
tweet = driver.execute_script("return arguments[0].parentNode;", tweet)

#   Get Screenshot
image_binary = tweet.screenshot_as_png
img = Image.open(io.BytesIO(image_binary))
width  = img.width
height = img.height

#   Resize to a maximum width (useful if on HiDPI screen)
max_width = 550
resize_factor = width // max_width
(width, height) = ( int(img.width // resize_factor), int(img.height // resize_factor))
img = img.resize( (width, height), Image.Resampling.LANCZOS )

#   Save directory
output_directory = "output"
os.makedirs(output_directory, exist_ok = True)

#   Optimal(ish) quality
output_img = os.path.join(output_directory, f"{tweet_id}.webp")
img.save( output_img, 'webp', optimize=True, quality=60 )

#   Kill the driver
driver.quit()

#   Generate Alt Text
tweet_alt = ""

#   Get the data
json_url =  f"https://cdn.syndication.twimg.com/tweet-result?id={tweet_id}&lang=en&token=1"
response = requests.get(json_url)
data = response.json()

#   Is this a thread?
if ( "parent" in data and hide_thread == "false" ) :
    tweet_text = data["parent"]["text"]
    tweet_name = data["parent"]["user"]["name"] + " (@" + data["parent"]["user"]["screen_name"] + ")"
    tweet_date = data["parent"]["created_at"]
    if "mediaDetails" in data["parent"]:
        for media in data["parent"]["mediaDetails"] :
            if "ext_alt_text" in media :
                tweet_text += " . Image: " + media["ext_alt_text"]
    tweet_alt += f"{tweet_date}. {tweet_name}. {tweet_text}. Reply "

#   Text of Tweet
tweet_text = data["text"]
tweet_name = data["user"]["name"] + " (@" + data["user"]["screen_name"] + ")"
tweet_date = data["created_at"] 
if "mediaDetails" in data:
    for media in data["mediaDetails"] :
        if "ext_alt_text" in media :
            tweet_text += " . Image: " + media["ext_alt_text"]

#   Stick it all together
tweet_alt += f"{tweet_date}. {tweet_name}. {tweet_text}"
tweet_alt = f"Screenshot from Twitter. {tweet_alt}".replace("\n", " ")

#   Save as a text file
with open(  os.path.join( output_directory, f"{tweet_id}.txt" ) , 'w', encoding="utf-8" ) as text_file:
    text_file.write( tweet_alt )

#   Generate HTML to be pasted

#   Link
tweet_url = "https://twitter.com/" + data["user"]["screen_name"] + "/status/" + data["id_str"]

#   Convert image to base64 data URl
binary_img      = open(output_img, 'rb').read()
base64_utf8_str = base64.b64encode(binary_img).decode('utf-8')
data_url = f'data:image/webp;base64,{base64_utf8_str}'

#   Ensure alt is sanitised
tweet_alt = html.escape(tweet_alt)

#   HTML to be pasted
tweet_html = f"<a href=\"{tweet_url}\"><img src=\"{data_url}\" width=\"{width}\" height=\"{height}\" alt=\"{tweet_alt}\"/></a>"

#   Copy to clipboard
pyperclip.copy( tweet_html )

#   Print to say we've finished
print( f"Copied {tweet_url}" )