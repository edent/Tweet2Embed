import argparse
import time

import io
import os
from PIL import Image

import tempfile

from selenium import webdriver 
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

import requests

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

#   Chrome's headless options
chrome_options = Options()
chrome_options.add_argument('--headless=new')
chrome_options.add_argument('--window-size=1920,2160')

#   Turn off everything
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--disable-infobars")
chrome_options.add_argument("--disable-logging")
chrome_options.add_argument("--log-level=3")

#   Wayland to stop fuzzyness on fractional scaling
chrome_options.add_argument("--enable-features=UseOzonePlatform")
chrome_options.add_argument("--ozone-platform=wayland")

#   Start Chrome
driver = webdriver.Chrome(options=chrome_options)

#   Open the Tweet on the embed platform
driver.get(f"https://platform.twitter.com/embed/Tweet.html?hideCard=false&hideThread={hide_thread}&lang=en&theme=light&width=550px&id={tweet_id}")

#   Zoom in to prevent fuzziness
zoom_factor = 1.25
zoom = str(zoom_factor * 100) +"%"
driver.execute_script(f"document.body.style.zoom='{zoom}'")

#   Wait for page to fully render
time.sleep(5)

#   Get the Tweet
tweet = driver.find_element(By.TAG_NAME, "article")
#   Use the parent element for more padding
tweet = driver.execute_script("return arguments[0].parentNode;", tweet)

# #   Save as a blurry image
# image_binary = tweet.screenshot_as_png
# img = Image.open(io.BytesIO(image_binary))
# #   Use WebP format
# img.save(f"{tweet_id}.webp")

#   Get the location & size of the element on the page
location = tweet.location
size = tweet.size
#   Save a screenshot of the whole page
tmp_png = os.path.join(tempfile.gettempdir(), "tmp.png")
driver.save_screenshot(tmp_png)

#   Crop the screenshot to the specific element
x = location['x']
y = location['y']
width  = location['x'] + size['width']  * zoom_factor
height = location['y'] + size['height'] * zoom_factor

img = Image.open(tmp_png)
img = img.crop((int(x), int(y), int(width), int(height)))

#   Resize if you want to
# (width, height) = ( int(img.width // zoom_factor), int(img.height // zoom_factor))
# img = img.resize((width, height), Image.Resampling.LANCZOS)
output_directory = "output"
os.makedirs(output_directory, exist_ok = True)
img.save( os.path.join(output_directory, f"{tweet_id}.webp") )

#   Generate Alt Text

#   Get the data
json_url =  f"https://cdn.syndication.twimg.com/tweet-result?id={tweet_id}&lang=en&token=1"
response = requests.get(json_url)
data = response.json()

tweet_alt = ""

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

tweet_alt += f"{tweet_date}. {tweet_name}. {tweet_text}"

tweet_alt = f"Screenshot from Twitter. {tweet_alt}".replace("\n", " ")

with open(  os.path.join( output_directory, f"{tweet_id}.txt" ) , 'w', encoding="utf-8" ) as text_file:
    text_file.write( tweet_alt )

print( tweet_alt )
