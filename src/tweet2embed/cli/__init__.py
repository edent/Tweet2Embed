import base64
import html
import os
from urllib.parse import urlparse

import click
import pyperclip
import requests

from tweet2embed.mastodon2html import get_mastodon_data, mastodon_to_html
from tweet2embed.settings import AVAILABLE_BROWSERS, DEFAULT_BROWSER
from tweet2embed.tweet2html import get_tweet_data, tweet_to_html
from tweet2embed.tweet2img import get_alt_text, get_driver, get_image
from tweet2embed.utils import TweetFetchingError, archive_url


@click.command(help="Convert a tweet or mastodon post to an embeddable format")
@click.argument("post_url", type=str, nargs=-1)
@click.option(
    "-o",
    "--output",
    type=click.Choice(["html", "img"]),
    help="Format to output",
    default=["html"],
    multiple=True,
)
@click.option(
    "-r",
    "--browser",
    type=click.Choice(AVAILABLE_BROWSERS),
    help="Browser to use for screenshots (img only)",
    default=DEFAULT_BROWSER,
    multiple=False,
)
@click.option(
    "-s",
    "--save",
    "save_file",
    type=click.Path(file_okay=False, dir_okay=True),
    help="Directory to save the output to",
    default=None,
)
@click.option(
    "-b", "--clipboard/--no-clipboard", help="Copy to clipboard", default=True
)
@click.option(
    "-t",
    "--thread/--no-thread",
    "thread_show",
    help="Show the thread (default false)",
    default=False,
)
@click.option(
    "-c",
    "--css/--no-css",
    "css_show",
    help="Copy the CSS (default false - only for HTML output)",
    default=False,
)
@click.option(
    "-p",
    "--pretty/--no-pretty",
    "pretty_print",
    help="Pretty Print the output (default false - only for HTML output)",
    default=False,
)
@click.option(
    "-m",
    "--schema/--no-schema",
    "schema_org",
    help="Add Schema.org metadata (default false - only for HTML output)",
    default=False,
)
@click.option(
    "-a",
    "--archive/--no-archive",
    help="Submit the URL to Archive.org",
    default=True,
)
def tweet2embed_cli(
    post_url,
    output=["html"],
    **kwargs,
):
    if not kwargs.get("save_file") and not kwargs.get("clipboard"):
        msg = "You must either save the output to a file or copy it to the clipboard"
        raise click.UsageError(msg)

    warned_about_mastodon_images = False
    session = requests.Session()

    for post_url_item in post_url:
        tweet_id = None
        if post_url_item.isdigit():
            tweet_id = post_url_item
        else:
            url_parts = urlparse(post_url_item)
            if url_parts.netloc in (
                "twitter.com",
                "www.twitter.com",
                "x.com",
                "www.x.com",
            ):
                tweet_id = url_parts.path.split("/")[-1]

        try:
            if tweet_id:
                if "html" in output:
                    tweet2html(
                        tweet_id,
                        session=session,
                        **kwargs,
                    )
                if "img" in output:
                    tweet2img(
                        tweet_id,
                        session=session,
                        **kwargs,
                    )
            else:
                if "img" in output:
                    if not warned_about_mastodon_images:
                        msg = "Mastodon posts can only be converted to HTML"
                        click.echo(msg)
                        warned_about_mastodon_images = True
                if "html" in output:
                    mastodon2html(
                        post_url_item,
                        session=session,
                        **kwargs,
                    )
        except TweetFetchingError as e:
            click.echo(f"Error fetching Tweet: {e}")


def mastodon2html(
    mastodon_url,
    session=None,
    thread_show=False,
    css_show=False,
    pretty_print=False,
    copy_text=False,
    save_file=False,
    schema_org=False,
    archive=True,
    **kwargs,
):
    if session is None:
        session = requests.Session()

    data = get_mastodon_data(mastodon_url, session=session)

    # Turn the Tweet into HTML
    mastodon_url, mastodon_html = mastodon_to_html(
        data,
        session=session,
        thread_show=thread_show,
        schema_org=schema_org,
        css_show=css_show,
    )

    #   Compact the output if necessary
    if not pretty_print:
        print("Compacting…")
        mastodon_html = mastodon_html.replace("\n", "").replace("\t", "").strip()

    #   Copy to clipboard
    pyperclip.copy(mastodon_html)
    print(f"Copied {mastodon_url}")

    if save_file:
        # Save HTML
        #   Save directory
        os.makedirs(save_file, exist_ok=True)
        # Make URl filename safe
        mastodon_file_name = "".join(x for x in mastodon_url if x.isalnum())
        save_location = os.path.join(save_file, f"{mastodon_file_name}.html")
        #   Save as HTML file
        with open(save_location, "w", encoding="utf-8") as html_file:
            html_file.write(mastodon_html)
        print(f"Saved to {save_location}")

    if archive:
        # Submit the Tweet to Archive.org
        archive_url(mastodon_url, session=session)


def tweet2html(
    tweet_id,
    session=None,
    thread_show=False,
    css_show=False,
    pretty_print=False,
    copy_text=False,
    save_file=False,
    schema_org=False,
    archive=True,
    **kwargs,
):
    if session is None:
        session = requests.Session()
    data = get_tweet_data(tweet_id, session)

    # Turn the Tweet into HTML
    tweet_url, tweet_html = tweet_to_html(
        data,
        session=session,
        thread_show=thread_show,
        schema_org=schema_org,
        css_show=css_show,
    )

    #   Compact the output if necessary
    if not pretty_print:
        print("Compacting…")
        tweet_html = tweet_html.replace("\n", "").replace("\t", "").strip()

    if copy_text:
        #   Copy to clipboard
        pyperclip.copy(tweet_html)
        #   Print to say we've finished
        print(f"Copied {tweet_id}")

    if save_file:
        # Save HTML
        #   Save directory
        os.makedirs(save_file, exist_ok=True)
        save_location = os.path.join(save_file, f"{tweet_id}.html")
        #   Save as HTML file
        with open(save_location, "w", encoding="utf-8") as html_file:
            html_file.write(tweet_html)
        print(f"Saved to {save_location}")

    if archive:
        # Submit the Tweet to Archive.org
        archive_url(tweet_url, session=session)


def tweet2img(
    tweet_id,
    session=None,
    driver=None,
    browser=DEFAULT_BROWSER,
    thread_show=False,
    save_file=False,
    copy_text=False,
    archive=True,
    **kwargs,
):
    if session is None:
        session = requests.Session()

    if driver is None:
        driver = get_driver(browser)

    #   Get the data
    data = get_tweet_data(tweet_id, session=session)
    img = get_image(tweet_id, driver=driver, show_thread=thread_show)
    tweet_alt = get_alt_text(data, session=session, show_thread=thread_show)
    #   Link
    tweet_url = (
        "https://twitter.com/"
        + data["user"]["screen_name"]
        + "/status/"
        + data["id_str"]
    )

    if save_file:
        #   Save directory
        os.makedirs(save_file, exist_ok=True)

        #   Optimal(ish) quality
        output_img = os.path.join(save_file, f"{tweet_id}.webp")
        img.save(output_img, "webp", optimize=True, quality=60)

        #   Save as a text file
        with open(
            os.path.join(save_file, f"{tweet_id}.txt"), "w", encoding="utf-8"
        ) as text_file:
            text_file.write(tweet_alt)

    if copy_text:
        #   Convert image to base64 data URl
        binary_img = open(output_img, "rb").read()
        base64_utf8_str = base64.b64encode(binary_img).decode("utf-8")
        data_url = f"data:image/webp;base64,{base64_utf8_str}"

        #   Ensure alt is sanitised
        tweet_alt = html.escape(tweet_alt)

        #   HTML to be pasted
        tweet_html = f'<a href="{tweet_url}"><img src="{data_url}" width="{img.width}" height="{img.height}" alt="{tweet_alt}"/></a>'

        #   Copy to clipboard
        pyperclip.copy(tweet_html)
        print(f"Copied {tweet_url}")
