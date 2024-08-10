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
from datetime import datetime
from dateutil import parser

#   Command line options
arguments = argparse.ArgumentParser(
	prog='tweet2html',
	description='Convert a Tweet ID to semantic HTML')
arguments.add_argument('id',       type=int,            help='ID of the Tweet (integer)')
arguments.add_argument('--thread', action='store_true', help='Show the thread (default false)', required=False)
args = arguments.parse_args()
tweet_id = args.id
thread = args.thread

#   Save directory
output_directory = "output"
os.makedirs(output_directory, exist_ok = True)

#   Get the data
json_url =  f"https://cdn.syndication.twimg.com/tweet-result?id={tweet_id}&lang=en&token=1"
response = requests.get(json_url)
data = response.json()

#   Text of Tweet
tweet_id      = data["id_str"]
tweet_name    = data["user"]["name"]
tweet_user    = data["user"]["screen_name"]
tweet_avatar  = data["user"]["profile_image_url_https"]
tweet_text    = data["text"]
tweet_date    = data["created_at"] 
tweet_likes   = data["favorite_count"]
tweet_replies = data["conversation_count"]
tweet_url     = f"https://twitter.com/{tweet_user}/status/{tweet_id}"

tweet_time = parser.parse( tweet_date )
tweet_time = tweet_time.strftime('%H:%M - %a %d %B %Y')

#   Embed entities
#   TODO!

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


# if "mediaDetails" in data:
#     for media in data["mediaDetails"] :
#         if "ext_alt_text" in media :
#             tweet_text += " . Image: " + media["ext_alt_text"]
# tweet_alt += f"{tweet_date}. {tweet_name}. {tweet_text}."


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
	<section class="tweet-embed-text">{tweet_text}</section>
	<hr class="tweet-embed-hr">
	<footer class="tweet-embed-footer">
		<a href="{tweet_url}" aria-label="{tweet_likes} likes" class="tweet-embed-likes">❤️ {tweet_likes}</a>
		<a href="{tweet_url}" aria-label="{tweet_replies} replies" class="tweet-embed-likes">💬 {tweet_replies}</a>
		<a href="{tweet_url}"><time datetime="{tweet_date}">{tweet_time}</time></a>
	</footer>
</blockquote>
'''

tweet_output = tweet_css + tweet_html

#   Compact the html
tweet_output = tweet_output.replace("\n", "")
tweet_output = tweet_output.replace("\t", "")

#   Copy to clipboard
pyperclip.copy( tweet_output )

#   Print to say we've finished
print( f"Copied {tweet_url}" )