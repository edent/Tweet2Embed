# Tweet2Embed

Convert a public Tweet into either:

* Image &amp; alt text
* Semantic HTML and CSS

Uses Selenium's Webdriver to launch a Firefox or Chrome instance and takes a screenshot. Uses the Twitter embed API to get a copy of the text and any alt text. An HTML representation is copied to the clipboard.

Usage:

## tweet2img
* `python tweet2img.py 123` will get the Tweet with ID 123, save a WebP screenshot, and print out the alt text.
* `python tweet2img.py 123 --thread` as above, but will include the parent Tweet if this is a reply.
* Screenshot and alt text are saved in the `output` directory.
* Clipboard receives a copy of the HTML - including data-encoded image - ready to paste in.
    * `<a href="https://twitter.com/edent/status/123"><img src="data:image/webp;base64,Ukl..." width="550" height="439" alt="Screenshot from Twitter. 2022-08-19T13:36:44.000Z. Description."/></a>`


## tweet2html
* `python tweet2html.py 123` will get the Tweet with ID 123, create an embedded HTML and CSS representation, and copy it to the clipboard. An HTML file is also saved.
* `--thread` to get a parent or quote tweet
* `--css` if you want the CSS as well
* `--prett` for pretty-printed HTML

##  Examples
* `1432768058028875791` Video
* `1095659600420966400` Reply - parent has image
* `909106648928718848` Multiple images
* `1560621791470448642` Quote Tweet
* `670060095972245504` Poll

## Known bugs:

* Fractional Scaling may produce slightly fuzzy images (Wayland related?)
* On tweet2img, the alt text contains t.co URls rather than the expanded ones (could use entities?)
* Number of retweets not shown (is there a non-API way to get it?)
* No Twitter Cards in the HTML (for now?)
* Many other things (probably?)