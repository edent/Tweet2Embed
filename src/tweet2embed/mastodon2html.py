#   For command line
import html

# Formatting
import locale
from urllib.parse import urlparse

import requests

#   Etc
from dateutil import parser

from tweet2embed.utils import TweetFetchingError, image_to_inline, jinja_env

locale.setlocale(locale.LC_ALL, "")


def mastodon_emojis(mastodon_text, emojis, session=None):
    if session is None:
        session = requests.Session()

    for emoji in emojis:
        shortcode = emoji["shortcode"]
        url = emoji["url"]
        emoji_img = image_to_inline(url, session)
        emoji_img_html = (
            f'<img src="{emoji_img}" alt=":{shortcode}:" class="social-embed-emoji">'
        )
        mastodon_text = mastodon_text.replace(f":{shortcode}:", emoji_img_html)
    return mastodon_text


def get_media(media_attachments, session=None):
    if session is None:
        session = requests.Session()

    media_html = '<div class="social-embed-media-grid">'
    # Iterate through the attached media
    for media in media_attachments:
        media_type = media["type"]

        # Convert small version of media to embedded WebP
        print("Embedding media…")
        media_img = image_to_inline(media["preview_url"], session)

        # Find alt text
        media_alt = ""
        if "description" in media:
            if media["description"] is not None:
                media_alt = html.escape(media["description"])

        # Is this a video or an image?
        if "video" == media_type:
            print("Video poster…")
            # Embed the poster in the <video>, link to last video which should be highest quality
            # TODO! Find a better way to get the best video
            media_html += f"""
			<video class='social-embed-video' controls src="{media["url"]}" poster="{media_img}" width="550"></video>
			"""
        if "image" == media_type:
            # Embed the image
            media_html += f"""
			<a href="{media['url']}" class="social-embed-media-link"><img class="social-embed-media" alt="{media_alt}" src="{media_img}"></a>
			"""
    return media_html + "</div>"


def get_poll_html(poll_data):
    print("Poll…")
    poll_html = '<hr class="social-embed-hr">'

    votes_count = poll_data["votes_count"]

    option_counter = 0

    for option in poll_data["options"]:
        option_title = option["title"]
        # Calculate the percentages. Round to 1 decimal place.
        option_votes = option["votes_count"]
        if votes_count > 0:
            option_percent = "{0:.1f}".format((option_votes / votes_count) * 100)
        else:
            option_percent = "0"

        # Generate semantic HTML
        poll_html += f"""
			<label for="poll_{option_counter}">{option_title}: ({option_votes:n})</label><br>
			<meter class="social-embed-meter" id="poll_{option_counter}" min="0" max="100" low="33" high="66" value="{option_percent}">{option_votes}</meter><br>
		"""

        option_counter += 1

    return poll_html


def get_card_html(card_data, session=None):
    if session is None:
        session = requests.Session()

    card_type = card_data["type"]
    print("Card of type " + card_type)

    # Photo Card
    if "photo" == card_type or "link" == card_type:
        card_title = ""
        card_title_html = ""
        card_description = ""
        card_description_html = ""
        card_thumbnail = ""
        card_thumbnail_html = ""
        card_thumbnail_alt = ""
        card_url = ""
        card_html = ""

        if "provider_name" in card_data:
            card_provider = card_data["provider_name"]
            card_provider_html = f"{card_provider}<br>"

        if "title" in card_data:
            card_title = card_data["title"]
            card_title_html = f"{card_title}<br>"

        if "description" in card_data:
            card_description = card_data["description"]
            card_description_html = f"{card_description}<br>"

        if "image_description" in card_data:
            card_thumbnail_alt = html.escape(card_data["image_description"])

        if "image" in card_data:
            print("Converting card's thumbnail_image…")
            card_thumbnail = card_data["image"]
            #   Convert  media to embedded WebP
            card_thumbnail = image_to_inline(card_thumbnail, session)
            card_thumbnail_html = f"""
				<div class="social-embed-media-grid">
					<img src="{card_thumbnail}" alt="{card_thumbnail_alt}" class="social-embed-media">
				</div>
				"""

        if "url" in card_data:
            card_url = card_data["url"]

        card_html += f"""
			<a href="{card_url}" class="social-embed-card">
				{card_thumbnail_html}
				{card_provider_html}
				{card_title_html}
				{card_description_html}
			</a>
		"""
        return card_html


def mastodon_to_html(
    mastodon_data, session=None, thread_show=False, schema_org=False, css_show=False
):
    if session is None:
        session = requests.Session()

    # Show the thread / quote?
    # tweet_parent = ""
    # tweet_quote  = ""
    # if thread_show :
    # 	if "parent" in tweet_data :
    # 		print( "Parent detected…" )
    # 		tweet_parent = tweet_to_html( tweet_data["parent"] )
    # 	if "quoted_tweet" in tweet_data :
    # 		print( "Quote detected…" )
    # 		tweet_quote = tweet_to_html( tweet_data["quoted_tweet"] )

    # Take the data from the API of a single Tweet (which might also be a quote or reply).
    # Create a semantic HTML representation
    #   Post Information
    mastodon_id = mastodon_data["id"]
    mastodon_url = mastodon_data["url"]
    mastodon_text = mastodon_data["content"]
    mastodon_date = mastodon_data["created_at"]
    mastodon_language = mastodon_data["language"]
    print(f"Detected language - {mastodon_language}")

    mastodon_likes = (int)(mastodon_data.get("favourites_count", 0))  # Might not exist
    mastodon_replies = (int)(mastodon_data.get("replies_count", 0))  # Might not exist
    mastodon_retweets = (int)(mastodon_data.get("reblogs_count", 0))  # Might not exist

    # User information
    user_name = mastodon_data["account"]["username"]
    user_display = mastodon_data["account"]["display_name"]
    user_avatar = mastodon_data["account"]["avatar"]
    user_url = mastodon_data["account"]["url"]
    user_bot = (bool)(mastodon_data["account"].get("bot", False))

    # User labels
    if user_bot:
        user_label = "Automated"
        user_badge_img = "🤖"
        print("Bot found …")
        user_badge = f"<br>{user_badge_img} {user_label}"
    else:
        user_badge = ""

    # Get the datetime
    mastodon_time = parser.parse(mastodon_date)
    mastodon_time = mastodon_time.strftime("%H:%M - %a %d %B %Y")

    # Is this a reply?
    # if "in_reply_to_screen_name" in tweet_data :
    # 	tweet_reply_to   = tweet_data["in_reply_to_screen_name"]
    # 	tweet_reply_id = tweet_data.get("in_reply_to_status_id_str","")	#	Doesn't exist on older tweets
    # 	if "" == tweet_reply_id :
    # 		tweet_reply_link = f'https://twitter.com/{tweet_reply_to}'
    # 	else :
    # 		tweet_reply_link = f'https://twitter.com/{tweet_reply_to}/status/{tweet_reply_id}'
    # 	tweet_reply = f'''
    # 		<small class="social-embed-reply"><a href="{tweet_reply_link}">Replying to @{tweet_reply_to}</a></small>
    # 	'''
    # else :
    # 	tweet_reply = ""

    # #   Embed entities
    # tweet_text = tweet_entities_to_html( tweet_text, tweet_entities )

    # Add shortcode emoji to text
    if "emojis" in mastodon_data:
        if mastodon_data["emojis"] is not None:
            mastodon_text = mastodon_emojis(
                mastodon_text, mastodon_data["emojis"], session
            )

    # Add media
    mastodon_media = ""
    if "media_attachments" in mastodon_data:
        if mastodon_data["media_attachments"] is not None:
            mastodon_media = get_media(mastodon_data["media_attachments"], session)

    # Add card
    mastodon_card = ""
    if "card" in mastodon_data:
        if mastodon_data["card"] is not None:
            mastodon_card = get_card_html(mastodon_data["card"], session)

    # Add poll
    mastodon_poll = ""
    if "poll" in mastodon_data:
        if mastodon_data["poll"] is not None:
            mastodon_poll = get_poll_html(mastodon_data["poll"])

    #   Convert avatar to embedded WebP
    print("Storing avatar…")
    mastodon_avatar = image_to_inline(user_avatar, session)

    #   HTML
    template = jinja_env.get_template("mastodon.html.j2")
    mastodon_html = template.render(
        schema_org=schema_org,
        css_show=css_show,
        mastodon_id=mastodon_id,
        mastodon_url=mastodon_url,
        mastodon_text=mastodon_text,
        mastodon_time=mastodon_time,
        mastodon_likes=mastodon_likes,
        mastodon_replies=mastodon_replies,
        mastodon_retweets=mastodon_retweets,
        mastodon_media=mastodon_media,
        mastodon_card=mastodon_card,
        mastodon_poll=mastodon_poll,
        user_name=user_name,
        user_display=user_display,
        user_url=user_url,
        mastodon_avatar=mastodon_avatar,
        user_badge=user_badge,
    )
    return mastodon_url, mastodon_html


def get_mastodon_data(mastodon_url, session=None):
    if session is None:
        session = requests.Session()

    data = None

    # Get Mastodon information
    mastodon_parts = urlparse(mastodon_url)
    mastodon_host = mastodon_parts.netloc
    mastodon_path = mastodon_parts.path
    mastodon_id = mastodon_path.split("/")[-1]  # Last element of /@example/123456
    mastodon_api = f"https://{mastodon_host}/api/v1/statuses/{mastodon_id}"

    #   Get the data from the Mastodon API
    for _ in range(5):
        # Lazy retry strategy
        try:
            print(f"Downloading {mastodon_api}")
            response = session.get(mastodon_api)
            response.raise_for_status()
            data = response.json()
            break
        except requests.HTTPError:
            print("Retrying…")
            continue

    if not data:
        msg = "No data received from Mastodon API."
        raise TweetFetchingError(msg)

    # If Post was deleted, exit.
    if "error" in data:
        msg = "This Post doesn't exist."
        raise TweetFetchingError(msg)

    return data
