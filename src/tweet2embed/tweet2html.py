#   For command line
import html

# Formatting
import locale
import random

import requests

#   Etc
from dateutil import parser

from tweet2embed.utils import TweetFetchingError, image_to_inline, jinja_env

locale.setlocale(locale.LC_ALL, "")


def tweet_entities_to_html(text, entities):
    # Initialize a list to hold parts of the HTML output
    html_parts = []

    # Current position in the text we are processing
    last_index = 0

    # Combine all entities into one list and sort by the start index
    all_entities = []

    # Process URls - show the display URl and link to the expanded URl, bypassing t.co
    if "urls" in entities:
        all_entities.extend(
            [
                (
                    url["url"],
                    f"<a href='{url['expanded_url']}'>{url['display_url']}</a>",
                    url["indices"][0],
                    url["indices"][1],
                )
                for url in entities["urls"]
            ]
        )

    # Link hashtags to Twitter
    if "hashtags" in entities:
        all_entities.extend(
            [
                (
                    f"#{hashtag['text']}",
                    f"<a href='https://twitter.com/hashtag/{hashtag['text']}'>#{hashtag['text']}</a>",
                    hashtag["indices"][0],
                    hashtag["indices"][1],
                )
                for hashtag in entities["hashtags"]
            ]
        )

    # Link user mentions to Twitter
    if "user_mentions" in entities:
        all_entities.extend(
            [
                (
                    f"@{mention['screen_name']}",
                    f"<a href='https://twitter.com/{mention['screen_name']}'>@{mention['screen_name']}</a>",
                    mention["indices"][0],
                    mention["indices"][1],
                )
                for mention in entities["user_mentions"]
            ]
        )

    # Link media to Twitter (will also embed later on)
    if "media" in entities:
        all_entities.extend(
            [
                (
                    f"{media['url']}",
                    f"<a href='{media['expanded_url']}'>{media['display_url']}</a>",
                    media["indices"][0],
                    media["indices"][1],
                )
                for media in entities["media"]
            ]
        )

    # Sort entities by start index
    all_entities.sort(key=lambda e: e[2])

    # Iterate over entities to build HTML
    for entity_text, replacement, start_index, end_index in all_entities:
        # Add text between the last processed entity and the current one
        html_parts.append(text[last_index:start_index])
        # Add the HTML replacement for the current entity
        html_parts.append(replacement)
        # Update the last index to the end of the current entity
        last_index = end_index

    # Add the remaining text after the last entity
    html_parts.append(text[last_index:])

    # Join all parts into a single HTML string
    return "".join(html_parts)


def get_media(mediaDetails, session=None):
    if session is None:
        session = requests.Session()

    media_html = '<div class="social-embed-media-grid">'
    # Iterate through the attached media
    for media in mediaDetails:
        # Convert small version of media to embedded WebP
        print("Embedding media…")
        media_img = image_to_inline(media["media_url_https"] + ":small", session)

        # Find alt text
        media_alt = ""
        if "ext_alt_text" in media:
            media_alt = html.escape(media["ext_alt_text"])

        # Is this a video or an image?
        if "video_info" in media:
            print("Video poster…")
            # Embed the poster in the <video>, link to last video which should be highest quality
            # TODO! Find a better way to get the best video
            media_html += f"""
            <video class='social-embed-video' controls src="{media["video_info"]["variants"][-1]["url"]}" poster="{media_img}" width="550"></video>
            """
        else:
            # Embed the image
            media_html += f"""
            <a href="{media['media_url_https']}" class="social-embed-media-link"><img class="social-embed-media" alt="{media_alt}" src="{media_img}"></a>
            """
    return media_html + "</div>"


def get_card_html(card_data, session=None):
    if session is None:
        session = requests.Session()

    poll_html = ""
    # As per https://github.com/igorbrigadir/twitter-advanced-search
    card_name = card_data["name"]
    print("Card of type " + card_name)

    # Poll
    if (
        card_name == "poll2choice_text_only"
        or card_name == "poll3choice_text_only"
        or card_name == "poll4choice_text_only"
    ):
        # Default values
        poll_1_label = ""
        poll_2_label = ""
        poll_3_label = ""
        poll_4_label = ""
        poll_1_count = 0
        poll_2_count = 0
        poll_3_count = 0
        poll_4_count = 0

        # Get labels and counts
        if "choice1_label" in card_data["binding_values"]:
            poll_1_label = card_data["binding_values"]["choice1_label"]["string_value"]
            poll_1_count = (int)(
                card_data["binding_values"]["choice1_count"]["string_value"]
            )
        if "choice2_label" in card_data["binding_values"]:
            poll_2_label = card_data["binding_values"]["choice2_label"]["string_value"]
            poll_2_count = (int)(
                card_data["binding_values"]["choice2_count"]["string_value"]
            )
        if "choice3_label" in card_data["binding_values"]:
            poll_3_label = card_data["binding_values"]["choice3_label"]["string_value"]
            poll_3_count = (int)(
                card_data["binding_values"]["choice3_count"]["string_value"]
            )
        if "choice4_label" in card_data["binding_values"]:
            poll_4_label = card_data["binding_values"]["choice4_label"]["string_value"]
            poll_4_count = (int)(
                card_data["binding_values"]["choice4_count"]["string_value"]
            )

        # Calculate the percentages. Round to 1 decimal place.
        poll_total = poll_1_count + poll_2_count + poll_3_count + poll_4_count
        poll_1_percent = "{0:.1f}".format((poll_1_count / poll_total) * 100)
        poll_2_percent = "{0:.1f}".format((poll_2_count / poll_total) * 100)
        poll_3_percent = "{0:.1f}".format((poll_3_count / poll_total) * 100)
        poll_4_percent = "{0:.1f}".format((poll_4_count / poll_total) * 100)

        # Generate semantic HTML
        if poll_1_label != "":
            poll_html += f"""
                <hr class="social-embed-hr">
                <label for="poll_1_count">{poll_1_label}: ({poll_1_count:n})</label><br>
                <meter class="social-embed-meter" id="poll_1_count" min="0" max="100" low="33" high="66" value="{poll_1_percent}">{poll_1_count}</meter><br>
            """
        if poll_2_label != "":
            poll_html += f"""
                <label for="poll_2_count">{poll_2_label}: ({poll_2_count:n})</label><br>
                <meter class="social-embed-meter" id="poll_2_count" min="0" max="100" low="33" high="66" value="{poll_2_percent}">{poll_2_count}</meter><br>
            """
        if poll_3_label != "":
            poll_html += f"""
                <label for="poll_3_count">{poll_3_label}: ({poll_3_count:n})</label><br>
                <meter class="social-embed-meter" id="poll_3_count" min="0" max="100" low="33" high="66" value="{poll_3_percent}">{poll_3_count}</meter><br>
            """
        if poll_4_label != "":
            poll_html += f"""
                <label for="poll_4_count">{poll_4_label}: ({poll_4_count:n})</label><br>
                <meter class="social-embed-meter" id="poll_4_count" min="0" max="100" low="33" high="66" value="{poll_4_percent}">{poll_4_count}</meter>
            """
        return poll_html

    # Photo Card
    if "summary_large_image" == card_name:
        card_vanity = ""
        card_vanity_html = ""
        card_title = ""
        card_title_html = ""
        card_description = ""
        card_description_html = ""
        card_thumbnail = ""
        card_thumbnail_html = ""
        card_thumbnail_alt = ""
        card_url = ""
        card_html = ""

        if "vanity_url" in card_data["binding_values"]:
            card_vanity = card_data["binding_values"]["vanity_url"]["string_value"]
            card_vanity_html = f"{card_vanity}<br>"

        if "title" in card_data["binding_values"]:
            card_title = card_data["binding_values"]["title"]["string_value"]
            card_title_html = f"{card_title}<br>"

        if "description" in card_data["binding_values"]:
            card_description = card_data["binding_values"]["description"][
                "string_value"
            ]
            card_description_html = f"{card_description}<br>"

        if "summary_photo_image_alt_text" in card_data["binding_values"]:
            card_thumbnail_alt = html.escape(
                card_data["binding_values"]["summary_photo_image_alt_text"][
                    "string_value"
                ]
            )

        if "thumbnail_image" in card_data["binding_values"]:
            print("Converting card's thumbnail_image…")
            card_thumbnail = card_data["binding_values"]["thumbnail_image"][
                "image_value"
            ]["url"]
            #   Convert  media to embedded WebP
            card_thumbnail = image_to_inline(card_thumbnail, session)
            card_thumbnail_html = f"""
                <img src="{card_thumbnail}" alt="{card_thumbnail_alt}" class="social-embed-media">
                """

        if "url" in card_data:
            card_url = card_data["url"]

        card_html += f"""
            <a href="{card_url}" class="social-embed-card">
                {card_thumbnail_html}
                {card_vanity_html}
                {card_title_html}
                {card_description_html}
            </a>
        """
        return card_html


def tweet_to_html(
    tweet_data, session=None, thread_show=False, schema_org=False, css_show=False
):
    if session is None:
        session = requests.Session()

    # Show the thread / quote?
    tweet_parent = ""
    tweet_quote = ""
    if thread_show:
        if "parent" in tweet_data:
            print("Parent detected…")
            tweet_parent = tweet_to_html(tweet_data["parent"])
        if "quoted_tweet" in tweet_data:
            print("Quote detected…")
            tweet_quote = tweet_to_html(tweet_data["quoted_tweet"])

    # Take the data from the API of a single Tweet (which might also be a quote or reply).
    # Create a semantic HTML representation
    #   Tweet Information
    tweet_id = tweet_data["id_str"]
    tweet_name = tweet_data["user"]["name"]
    tweet_user = tweet_data["user"]["screen_name"]
    tweet_avatar = tweet_data["user"]["profile_image_url_https"]
    tweet_shape = tweet_data["user"].get(
        "profile_image_shape", "Square"
    )  # Some users don't have this
    tweet_text = tweet_data["text"]
    tweet_date = tweet_data["created_at"]
    tweet_lang = tweet_data["lang"]
    print(f"Detected language - {tweet_lang}")

    tweet_likes = (int)(tweet_data.get("favorite_count", 0))  # Might not exist
    tweet_replies = (int)(tweet_data.get("conversation_count", 0))  # Might not exist
    tweet_retweets = (int)(tweet_data.get("retweet_count", 0))  # Might not exist
    tweet_entities = tweet_data["entities"]
    tweet_url = f"https://twitter.com/{tweet_user}/status/{tweet_id}"

    # User labels
    if "highlighted_label" in tweet_data["user"]:
        tweet_label = html.escape(
            tweet_data["user"]["highlighted_label"]["description"]
        )
        tweet_badge_img = image_to_inline(
            tweet_data["user"]["highlighted_label"]["badge"]["url"], session
        )
        print(f"Badge found '{tweet_label}'…")
        tweet_badge = f'<br><img src="{tweet_badge_img}" alt="" class="social-embed-badge"> {tweet_label}'
    else:
        tweet_badge = ""

    # Get the datetime
    tweet_time = parser.parse(tweet_date)
    tweet_time = tweet_time.strftime("%H:%M - %a %d %B %Y")

    # Is this a reply?
    if "in_reply_to_screen_name" in tweet_data:
        tweet_reply_to = tweet_data["in_reply_to_screen_name"]
        tweet_reply_id = tweet_data.get(
            "in_reply_to_status_id_str", ""
        )  # Doesn't exist on older tweets
        if "" == tweet_reply_id:
            tweet_reply_link = f"https://twitter.com/{tweet_reply_to}"
        else:
            tweet_reply_link = (
                f"https://twitter.com/{tweet_reply_to}/status/{tweet_reply_id}"
            )
        tweet_reply = f"""
            <small class="social-embed-reply"><a href="{tweet_reply_link}">Replying to @{tweet_reply_to}</a></small>
        """
    else:
        tweet_reply = ""

    #   Embed entities
    tweet_text = tweet_entities_to_html(tweet_text, tweet_entities)

    # Add media
    tweet_media = ""
    if "mediaDetails" in tweet_data:
        tweet_media = get_media(tweet_data["mediaDetails"], session)

    # Add card
    tweet_card = ""
    if "card" in tweet_data:
        tweet_card = get_card_html(tweet_data["card"], session)

    #   Newlines to BR
    tweet_text = tweet_text.replace("\n", "<br>")

    #   Convert avatar to embedded WebP
    print("Storing avatar…")
    tweet_avatar = image_to_inline(tweet_avatar, session)

    #   HTML
    template = jinja_env.get_template("tweet.html.j2")
    tweet_html = template.render(
        schema_org=schema_org,
        css_show=css_show,
        tweet_id=tweet_id,
        tweet_name=tweet_name,
        tweet_user=tweet_user,
        tweet_avatar=tweet_avatar,
        tweet_shape=tweet_shape,
        tweet_time=tweet_time,
        tweet_text=tweet_text,
        tweet_media=tweet_media,
        tweet_card=tweet_card,
        tweet_likes=tweet_likes,
        tweet_replies=tweet_replies,
        tweet_retweets=tweet_retweets,
        tweet_badge=tweet_badge,
        tweet_reply=tweet_reply,
        tweet_parent=tweet_parent,
        tweet_quote=tweet_quote,
    )
    return tweet_url, tweet_html


def get_tweet_data(tweet_id, session=None):
    if session is None:
        session = requests.Session()

    data = None

    # Get the data from the Twitter embed API
    for _ in range(5):
        # Lazy retry strategy
        try:
            print("Downloading data…")
            token = random.randint(1, 10000)
            json_url = f"https://cdn.syndication.twimg.com/tweet-result?id={tweet_id}&lang=en&token={token}"
            response = session.get(json_url)
            response.raise_for_status()
            data = response.json()
            break
        except requests.HTTPError:
            print("Retrying…")
            continue

    if not data:
        msg = "No data received from Twitter."
        raise TweetFetchingError(msg)

    # If Tweet was deleted, exit.
    if "TweetTombstone" == data["__typename"]:
        msg = "This Tweet was deleted by the Tweet author."
        raise TweetFetchingError(msg)

    return data
