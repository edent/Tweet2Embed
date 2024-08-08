# Tweet2Img
Convert a public Tweet into an image &amp; alt text

Uses Selenium's Webdriver to launch a Chrome instance and takes a screenshot. Uses the Twitter embed API to get a copy of the text and any alt text.

Usage:

* `python tweet2img.py 123` will get the Tweet with ID 123, save a WebP screenshot, and print out the alt text.
* `python tweet2img.py 123 --thread` as above, but will include the parent Tweet if this is a reply.
* Screenshot and alt text are saved in the `output` directory.

Known bugs:

* Fractional Scaling may produce slightly fuzzy images (Wayland related?)
* Alt text contains t.co URls rather than the expanded ones (could use entities?)
* Many other thing (probably?)