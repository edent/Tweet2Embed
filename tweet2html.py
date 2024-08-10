#   For command line
import argparse

#   File and Bits
import io
import os
import tempfile

#   Image Manipulation
from PIL import Image

#   Etc
import requests
import pyperclip
import base64
import html

#	Date manipulation
from datetime import datetime
from dateutil import parser

#   Command line options
arguments = argparse.ArgumentParser(
	prog='tweet2html',
	description='Convert a Tweet ID to semantic HTML')
arguments.add_argument('id',       type=int,            help='ID of the Tweet (integer)')
arguments.add_argument('--thread', action='store_true', help='Show the thread (default false)', required=False)
arguments.add_argument('--css',    action='store_true', help='Copy the CSS (default false)',    required=False)

args = arguments.parse_args()
tweet_id = args.id
thread = args.thread
css = args.css

if ( True == thread ):
	hide_thread = "false"
else :
	hide_thread = "true"

if ( True == css ):
	css_show = True
else :
	css_show = False

def tweet_entities_to_html(text, entities):
	# Initialize a list to hold parts of the HTML output
	html_parts = []

	# Current position in the text we are processing
	last_index = 0

	# Combine all entities into one list and sort by the start index
	all_entities = []
	if 'urls' in entities:
		all_entities.extend(
			[
				(
					url['url'], 
					f"<a href='{url['expanded_url']}'>{url['display_url']}</a>", 
					url['indices'][0], 
					url['indices'][1]
				) for url in entities['urls']
			]
		)
	if 'hashtags' in entities:
		all_entities.extend(
			[
				(
					f"#{hashtag['text']}", 
					f"<a href='https://twitter.com/hashtag/{hashtag['text']}'>#{hashtag['text']}</a>",
					hashtag['indices'][0], 
					hashtag['indices'][1]
				) for hashtag in entities['hashtags']
			]
		)
	if 'user_mentions' in entities:
		all_entities.extend(
			[
				(
					f"@{mention['screen_name']}", 
					f"<a href='https://twitter.com/{mention['screen_name']}'>@{mention['screen_name']}</a>", 
					mention['indices'][0], 
					mention['indices'][1]
				) for mention in entities['user_mentions']
			]
		)

	if 'media' in entities:
		all_entities.extend(
			[
				(
					f"{media['url']}", 
					f"<a href='{media['expanded_url']}'>{media['display_url']}</a>", 
					media['indices'][0], 
					media['indices'][1]
				) for media in entities['media']
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
	return ''.join(html_parts)

def get_media( mediaDetails) :
	media_html = ""
	for media in mediaDetails :
		#   Convert small version of media to embedded WebP
		media_url  = media["media_url_https"] + ":small"
		media_img  = requests.get(media_url)
		media_img  = Image.open(io.BytesIO(media_img.content))
		output_img = os.path.join( tempfile.gettempdir() , f"temp.webp" )
		media_img.save( output_img, 'webp', optimize=True, quality=60 )
		#   Convert image to base64 data URl
		binary_img      = open(output_img, 'rb').read()
		base64_utf8_str = base64.b64encode(binary_img).decode('utf-8')
		media_img = f'data:image/webp;base64,{base64_utf8_str}'
		media_alt = ""
		if "ext_alt_text" in media :
			media_alt = media["ext_alt_text"]
		#	Is this a video or an image?
		if "video_info" in media :
			#	TODO! Find a better way to get the best video
			media_html += f'''
			<video class='tweet-embed-video' controls src="{media["video_info"]["variants"][-1]["url"]}" poster="{media_img}" width="550"></video>
			'''
		else:
			media_html += f"<a href='{media['media_url_https']}'><img class='tweet-embed-media' alt='{media_alt}' src='{media_img}'></a>"
	return media_html

#   Save directory
output_directory = "output"
os.makedirs(output_directory, exist_ok = True)

#   Get the data
json_url =  f"https://cdn.syndication.twimg.com/tweet-result?id={tweet_id}&lang=en&token=1"
response = requests.get(json_url)
data = response.json()

#   Text of Tweet
tweet_id       = data["id_str"]
tweet_name     = data["user"]["name"]
tweet_user     = data["user"]["screen_name"]
tweet_avatar   = data["user"]["profile_image_url_https"]
tweet_text     = data["text"]
tweet_date     = data["created_at"] 
tweet_likes    = data["favorite_count"]
tweet_replies  = data["conversation_count"]
tweet_entities = data["entities"] 
tweet_url      = f"https://twitter.com/{tweet_user}/status/{tweet_id}"

tweet_time = parser.parse( tweet_date )
tweet_time = tweet_time.strftime('%H:%M - %a %d %B %Y')

#   Embed entities
tweet_text = tweet_entities_to_html( tweet_text, tweet_entities )
print(tweet_text)

#	Add media
tweet_media = ""
if ( "mediaDetails" in data ) :
	tweet_media = get_media( data["mediaDetails"])

#   Newlines to BR
tweet_text = tweet_text.replace("\n","<br>")

#   Convert avatar to embedded WebP
tweet_avatar = requests.get(tweet_avatar)
tweet_avatar = Image.open(io.BytesIO(tweet_avatar.content))
output_img = os.path.join( tempfile.gettempdir() , f"{tweet_id}.webp")
tweet_avatar.save( output_img, 'webp', optimize=True, quality=60 )
#   Convert image to base64 data URl
binary_img      = open(output_img, 'rb').read()
base64_utf8_str = base64.b64encode(binary_img).decode('utf-8')
tweet_avatar = f'data:image/webp;base64,{base64_utf8_str}'


#   Generate HTML to be pasted
tweet_css = '''
<style>
.tweet-embed {
	all: unset;
	display: block;
}
.tweet-embed * {
	all: unset;
	display: revert;
}
.tweet-embed::after {
	all: unset;
}
.tweet-embed::before {
	all: unset;
}
blockquote:not(*) {
	all: unset;
}
.tweet-embed a {
	cursor: pointer;
}
blockquote.tweet-embed {
	box-sizing: border-box;
	border: .5px solid;
	width: 550px;
	max-width: 100%;
	font-family: sans-serif;
	margin: 0;
	margin-bottom: .5em;
	padding: 1em;
	border-radius: 1em;
	background-color: white;
	color: black;
	display: block;
}
.tweet-embed-header {
	display: flex;
	justify-content: space-between;
}
.tweet-embed-user {
	display: flex;
	position: relative;
	align-items: center;
	text-decoration: none;
	color: inherit;
}
.tweet-embed-avatar {
	width: 3em;
	height: 3em;
	border-radius: 100%;
	margin-right: .5em;
}
.tweet-embed-user-names-name {
	display: flex;
	align-items: center;
	font-weight: bold;
	margin: 0;
}
.tweet-embed-text {
	margin-top: .5em;
}
.tweet-embed-footer {
	display: flex;
	align-items: center;
	justify-content: space-between;
}
.tweet-embed-logo {
	width: 3em;
}
.tweet-embed-hr {
	border: .1px solid;
	margin: .5em 0 .5em 0;
}
.tweet-embed-likes {
	margin: 0;
}
.tweet-embed-reply {
	display: block;
}
.tweet-embed-text a, .tweet-embed-footer time {
	color: blue;
	text-decoration: underline;
}
.tweet-embed-media, .tweet-embed-video {
	border-radius:1em;
	max-width:100%;
}
</style>
'''
#   HTML to be pasted
tweet_html = f'''
<blockquote class="tweet-embed">
	<header class="tweet-embed-header">
		<a href="https://twitter.com/{tweet_user}" class="tweet-embed-user">
			<img class="tweet-embed-avatar"
				src="{tweet_avatar}" alt="">
			<div class="tweet-embed-user-names">
				<p class="tweet-embed-user-names-name">{tweet_name}</p>@{tweet_user}
			</div>
		</a>
		<img class="tweet-embed-logo"
			src='data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciCmFyaWEtbGFiZWw9IlR3aXR0ZXIiIHJvbGU9ImltZyIKdmlld0JveD0iMCAwIDUxMiA1MTIiPjxwYXRoCmQ9Im0wIDBINTEyVjUxMkgwIgpmaWxsPSIjZmZmIi8+PHBhdGggZmlsbD0iIzFkOWJmMCIgZD0ibTQ1OCAxNDBxLTIzIDEwLTQ1IDEyIDI1LTE1IDM0LTQzLTI0IDE0LTUwIDE5YTc5IDc5IDAgMDAtMTM1IDcycS0xMDEtNy0xNjMtODNhODAgODAgMCAwMDI0IDEwNnEtMTcgMC0zNi0xMHMtMyA2MiA2NCA3OXEtMTkgNS0zNiAxczE1IDUzIDc0IDU1cS01MCA0MC0xMTcgMzNhMjI0IDIyNCAwIDAwMzQ2LTIwMHEyMy0xNiA0MC00MSIvPjwvc3ZnPg==' >
	</header>
	<section class="tweet-embed-text">{tweet_text}{tweet_media}</section>
	<hr class="tweet-embed-hr">
	<footer class="tweet-embed-footer">
		<a href="{tweet_url}" aria-label="{tweet_likes} likes" class="tweet-embed-likes">❤️ {tweet_likes}</a>
		<a href="{tweet_url}" aria-label="{tweet_replies} replies" class="tweet-embed-likes">💬 {tweet_replies}</a>
		<a href="{tweet_url}"><time datetime="{tweet_date}">{tweet_time}</time></a>
	</footer>
</blockquote>
'''

if css_show :
	tweet_html = tweet_css + tweet_html

#   Compact the html
tweet_html = tweet_html.replace("\n", "")
tweet_html = tweet_html.replace("\t", "")

#   Copy to clipboard
pyperclip.copy( tweet_html )

#   Print to say we've finished
print( f"Copied {tweet_url}" )