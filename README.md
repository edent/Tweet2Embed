# Tweet2Embed

Convert a public Tweet into either:

* Image &amp; alt text
* Semantic HTML and CSS

Uses Selenium's Webdriver to launch a Firefox or Chrome instance and takes a screenshot. Uses the Twitter embed API to get a copy of the text and any alt text. An HTML representation is copied to the clipboard.

## Features

* 🗣 Avatars inlined as WebP
* 📸 All attached photos inlined
* 🎥 Video poster inline, <video> to original mp4
* 🔗 Hyperlinks don't use t.co
* #️⃣ Hashtags & @ mentions linked
* 🔄 Includes reply threads & quote Tweets
* 🕰 Semantic time
* 🔍 Schema.org metadata
* 🖼 Cards
* 📊 Polls
* ♥ , 🔁 & 🗨 counts
* 📖 Autosubmit the Tweet to Archive.org

## Usage

### tweet2html
* `python tweet2html.py 123` will get the Tweet with ID 123, create an embedded HTML, and copy it to the clipboard.
* `--thread` to get a parent or quote tweet
* `--css` if you want the CSS as well
* `--pretty` for pretty-printed HTML
* `--save` save the HTML to a file
* `--schema` adds Schema.org metadata

#### Typical Output

Run `python tweet2html.py -mtp 671919410630819840` and receive:

```html
<blockquote class="tweet-embed" id="tweet-embed-671919410630819840" lang="en" itemscope itemtype="https://schema.org/SocialMediaPosting">
    <header class="tweet-embed-header" itemprop="author" itemscope itemtype="https://schema.org/Person">
        <a href="https://twitter.com/polls" class="tweet-embed-user" itemprop="url">
            <img class="tweet-embed-avatar tweet-embed-avatar-circle" src="data:image/webp;base64,UklGRuwAAABXRUJQVlA4IOAAAABQBgCdASowADAAPrVWpEunJSOhqrqpWOAWiWUAxQaACJBCAEB6EJ7HdwZ7m9AsQTxW+yk80gC5I/REUAD+5Ij/FsUhuZ/jfEF7U+ofYABMBkF4Sc8d827tC2qwG95CN3fVuuFS/uqP/Fwucurp8KcurrXcBQpkUCdvp40Y29kx8lP8Y45C3t4IcJPYcIDFVl5+L1M3426aJn0CIdA27KAZjABt0TDw3lgHKggxpvOpEjEgBMnQHzq9rFumwbXgCzvqgOwsseDr6msoySerlXwDZWfNYqz4k58dV2tZoAAAAA==" alt="" itemprop="image">
            <div class="tweet-embed-user-names">
                <p class="tweet-embed-user-names-name" itemprop="name">polls</p>@polls
            </div>
        </a>
        <img class="tweet-embed-logo" alt="" src='data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciCmFyaWEtbGFiZWw9IlR3aXR0ZXIiIHJvbGU9ImltZyIKdmlld0JveD0iMCAwIDUxMiA1MTIiPjxwYXRoCmQ9Im0wIDBINTEyVjUxMkgwIgpmaWxsPSIjZmZmIi8+PHBhdGggZmlsbD0iIzFkOWJmMCIgZD0ibTQ1OCAxNDBxLTIzIDEwLTQ1IDEyIDI1LTE1IDM0LTQzLTI0IDE0LTUwIDE5YTc5IDc5IDAgMDAtMTM1IDcycS0xMDEtNy0xNjMtODNhODAgODAgMCAwMDI0IDEwNnEtMTcgMC0zNi0xMHMtMyA2MiA2NCA3OXEtMTkgNS0zNiAxczE1IDUzIDc0IDU1cS01MCA0MC0xMTcgMzNhMjI0IDIyNCAwIDAwMzQ2LTIwMHEyMy0xNiA0MC00MSIvPjwvc3ZnPg=='>
    </header>
    <section class="tweet-embed-text" itemprop="articleBody">
        The Beatles or The Rolling Stones?
        <hr class="tweet-embed-hr">
        <label for="poll_1_count">The Beatles: (28,857)</label><br>
        <meter class="tweet-embed-meter" id="poll_1_count" min="0" max="100" low="33" high="66" value="76.1">28857</meter><br>
        <label for="poll_2_count">The Rolling Stones: (9,074)</label><br>
        <meter class="tweet-embed-meter" id="poll_2_count" min="0" max="100" low="33" high="66" value="23.9">9074</meter><br>
    </section>
    <hr class="tweet-embed-hr">
    <footer class="tweet-embed-footer">
        <a href="https://twitter.com/polls/status/671919410630819840" aria-label="113 likes" class="tweet-embed-meta">❤️ 113</a>
        <a href="https://twitter.com/polls/status/671919410630819840" aria-label="38 replies" class="tweet-embed-meta">💬 38</a>
        <a href="https://twitter.com/polls/status/671919410630819840" aria-label="0 retweets" class="tweet-embed-meta">🔁 0</a>			
        <a href="https://twitter.com/polls/status/671919410630819840"><time datetime="2015-12-02T05:10:45.000Z" itemprop="datePublished">05:10 - Wed 02 December 2015</time></a>
    </footer>
</blockquote>
```

## tweet2img
* `python tweet2img.py 123` will get the Tweet with ID 123, save a WebP screenshot, and print out the alt text.
* `python tweet2img.py 123 --thread` as above, but will include the parent Tweet if this is a reply.
* Screenshot and alt text are saved in the `output` directory.
* Clipboard receives a copy of the HTML - including data-encoded image - ready to paste in.
    * `<a href="https://twitter.com/edent/status/123"><img src="data:image/webp;base64,Ukl..." width="550" height="439" alt="Screenshot from Twitter. 2022-08-19T13:36:44.000Z. Description."/></a>`


##  Useful Examples
* `1432768058028875791` Video
* `1095659600420966400` Reply - parent has image
* `909106648928718848` Multiple images
* `1560621791470448642` Quote Tweet
* `670060095972245504` Poll
* `83659275024601088` Deleted Tweet
* `1131218926493413377` Summary Card
* `1485588404037648389` Reply to a quoted Tweet

## Known bugs:

* Fractional Scaling may produce slightly fuzzy images (Wayland related?)
* On tweet2img, the alt text contains t.co URls rather than the expanded ones (could use entities?)
* Only some Twitter Cards are rendered in HTML (are there more?)
* No Dark Mode (overkill?)
* Many other things (probably?)
