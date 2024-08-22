#   File and Bits
import io

#   Sleeping
import time

#   Etc
import requests

#   Image Manipulation
from PIL import Image

#   Selenium
from selenium import webdriver

#   If using Chrome
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By

#   Firefox specific
from selenium.webdriver.firefox.options import Options as FirefoxOptions

from tweet2embed.settings import AVAILABLE_BROWSERS, DEFAULT_BROWSER


def get_driver(browser=DEFAULT_BROWSER):
    if browser not in AVAILABLE_BROWSERS:
        raise ValueError("Invalid browser")

    if browser == "firefox":
        #   Firefox's Headless Options
        firefox_options = FirefoxOptions()
        firefox_options.add_argument("--headless")
        return webdriver.Firefox(options=firefox_options)
    elif browser == "chrome":
        #   Chrome's Headless Options
        chrome_options = ChromeOptions()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--window-size=1920,2160")

        #   Turn off everything
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-logging")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--force-device-scale-factor=1")
        chrome_options.add_argument("--high-dpi-support=1")

        #   Wayland to stop fuzzyness on fractional scaling
        chrome_options.add_argument("--enable-features=UseOzonePlatform")
        chrome_options.add_argument("--ozone-platform=wayland")
        return webdriver.Chrome(options=chrome_options)
    else:
        raise ValueError("Invalid browser")


def get_image(tweet_id, driver=None, browser="chrome", show_thread=True):
    if show_thread:
        hide_thread = "false"
    else:
        hide_thread = "true"

    #   Get the driver
    if driver is None:
        driver = get_driver(browser)

    #   Open the Tweet on the embed platform
    driver.get(
        f"https://platform.twitter.com/embed/Tweet.html?hideCard=false&hideThread={hide_thread}&lang=en&theme=light&width=550px&id={tweet_id}"
    )

    #   Wait for page to fully render
    time.sleep(3)

    #   Get the Tweet
    tweet = driver.find_element(By.TAG_NAME, "article")
    #   Use the parent element for more padding
    tweet = driver.execute_script("return arguments[0].parentNode;", tweet)

    #   Get Screenshot
    image_binary = tweet.screenshot_as_png
    img = Image.open(io.BytesIO(image_binary))
    width = img.width
    height = img.height

    #   Resize to a maximum width (useful if on HiDPI screen)
    max_width = 550
    resize_factor = width // max_width
    (width, height) = (
        int(img.width // resize_factor),
        int(img.height // resize_factor),
    )
    img = img.resize((width, height), Image.Resampling.LANCZOS)

    #   Kill the driver
    driver.quit()

    return img


def get_alt_text(data, session=None, show_thread=True):
    if session is None:
        session = requests.Session()

    #   Generate Alt Text
    tweet_alt = ""
    ptweet_alt = ""
    qtweet_alt = ""

    #   Is this a thread?
    if "parent" in data and show_thread:
        ptweet_text = data["parent"]["text"]
        ptweet_name = (
            data["parent"]["user"]["name"]
            + " (@"
            + data["parent"]["user"]["screen_name"]
            + ")"
        )
        ptweet_date = data["parent"]["created_at"]
        if "mediaDetails" in data["parent"]:
            for media in data["parent"]["mediaDetails"]:
                if "ext_alt_text" in media:
                    ptweet_text += " . Image: " + media["ext_alt_text"]
        ptweet_alt += f"{ptweet_date}. {ptweet_name}. {ptweet_text}. Reply "

    #   Text of Tweet
    tweet_text = data["text"]
    tweet_name = data["user"]["name"] + " (@" + data["user"]["screen_name"] + ")"
    tweet_date = data["created_at"]
    if "mediaDetails" in data:
        for media in data["mediaDetails"]:
            if "ext_alt_text" in media:
                tweet_text += " . Image: " + media["ext_alt_text"]
    tweet_alt += f"{tweet_date}. {tweet_name}. {tweet_text}."

    #   Is this a quote Tweet?
    if "quoted_tweet" in data and show_thread:
        qtweet_text = data["quoted_tweet"]["text"]
        qtweet_name = (
            data["quoted_tweet"]["user"]["name"]
            + " (@"
            + data["quoted_tweet"]["user"]["screen_name"]
            + ")"
        )
        qtweet_date = data["quoted_tweet"]["created_at"]
        if "mediaDetails" in data["quoted_tweet"]:
            for media in data["quoted_tweet"]["mediaDetails"]:
                if "ext_alt_text" in media:
                    qtweet_text += " . Image: " + media["ext_alt_text"]
        qtweet_alt += f" Quoting: {qtweet_date}. {qtweet_name}. {qtweet_text}."

    #   Stick it all together
    tweet_alt = f"Screenshot from Twitter. {ptweet_alt}{tweet_alt}{qtweet_alt}".replace(
        "\n", " "
    )
    return tweet_alt
