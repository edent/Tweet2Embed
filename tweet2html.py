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
arguments.add_argument('--pretty', action='store_true', help='Pretty Print the output (default false)',    required=False)

args = arguments.parse_args()
tweet_id = args.id
thread = args.thread
css = args.css
pretty = args.pretty

if ( True == thread ):
	thread_show = True
else :
	thread_show = False

if ( True == css ):
	css_show = True
else :
	css_show = False

if ( True == pretty ):
	pretty_print = True
else :
	pretty_print = False

def tweet_entities_to_html(text, entities):
	#	Initialize a list to hold parts of the HTML output
	html_parts = []

	#	Current position in the text we are processing
	last_index = 0

	#	Combine all entities into one list and sort by the start index
	all_entities = []

	#	Process URls - show the display URl and link to the expanded URl, bypassing t.co
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
	
	#	Link hashtags to Twitter
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
	
	#	Link user mentions to Twitter
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

	#	Link media to Twitter (will also embed later on)
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

	#	Sort entities by start index
	all_entities.sort(key=lambda e: e[2])

	#	Iterate over entities to build HTML
	for entity_text, replacement, start_index, end_index in all_entities:
		#	Add text between the last processed entity and the current one
		html_parts.append(text[last_index:start_index])
		#	Add the HTML replacement for the current entity
		html_parts.append(replacement)
		#	Update the last index to the end of the current entity
		last_index = end_index

	#	Add the remaining text after the last entity
	html_parts.append(text[last_index:])

	#	Join all parts into a single HTML string
	return ''.join(html_parts)

def get_media( mediaDetails) :
	media_html = ""
	#	Iterate through the attached media
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
		
		#	Find alt text
		media_alt = ""
		if "ext_alt_text" in media :
			media_alt = html.escape( media["ext_alt_text"] )
	
		#	Is this a video or an image?
		if "video_info" in media :
			#	Embed the poster in the <video>, link to last video which should be highest quality
			#	TODO! Find a better way to get the best video
			media_html += f'''
			<video class='tweet-embed-video' controls src="{media["video_info"]["variants"][-1]["url"]}" poster="{media_img}" width="550"></video>
			'''
		else:
			#	Embed the image
			media_html += f"<a href='{media['media_url_https']}'><img class='tweet-embed-media' alt='{media_alt}' src='{media_img}'></a>"
	return media_html

def tweet_to_html( tweet_data ) :

	#	Show the thread / quote?
	tweet_parent = ""
	tweet_quote  = ""
	if thread_show :
		if "parent" in tweet_data :
			tweet_parent = tweet_to_html( tweet_data["parent"] )


	#	Take the data from the API of a single Tweet (which might also be a quote or reply).
	#	Create a semantic HTML representation
	#   Tweet Information
	tweet_id       = tweet_data["id_str"]
	tweet_name     = tweet_data["user"]["name"]
	tweet_user     = tweet_data["user"]["screen_name"]
	tweet_avatar   = tweet_data["user"]["profile_image_url_https"]
	tweet_text     = tweet_data["text"]
	tweet_date     = tweet_data["created_at"] 
	tweet_likes    = tweet_data.get("favorite_count", "")	#	Might not exist
	tweet_replies  = tweet_data.get("conversation_count", "")#	Might not exist
	tweet_entities = tweet_data["entities"] 
	tweet_url      = f"https://twitter.com/{tweet_user}/status/{tweet_id}"

	#	Get the datetime
	tweet_time = parser.parse( tweet_date )
	tweet_time = tweet_time.strftime('%H:%M - %a %d %B %Y')

	#	Is this a reply?
	if "in_reply_to_screen_name" in tweet_data :
		tweet_reply_to   = tweet_data["in_reply_to_screen_name"]
		tweet_reply_link = tweet_data["in_reply_to_status_id_str"]
		tweet_reply = f'''
	<small class="tweet-embed-reply"><a href="https://twitter.com/{tweet_reply_to}/status/{tweet_reply_link}">Replying to @{tweet_reply_to}</a></small>
	'''
	else :
		tweet_reply = ""

	#   Embed entities
	tweet_text = tweet_entities_to_html( tweet_text, tweet_entities )

	#	Add media
	tweet_media = ""
	if ( "mediaDetails" in tweet_data ) :
		tweet_media = get_media( tweet_data["mediaDetails"] )

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

	#   HTML
	tweet_html = f'''
	<blockquote class="tweet-embed">
		{tweet_parent}
		<header class="tweet-embed-header">
			<a href="https://twitter.com/{tweet_user}" class="tweet-embed-user">
				<img class="tweet-embed-avatar"	src="{tweet_avatar}" alt="">
				<div class="tweet-embed-user-names">
					<p class="tweet-embed-user-names-name">{tweet_name}</p>@{tweet_user}
				</div>
			</a>
			<img class="tweet-embed-logo" src='data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciCmFyaWEtbGFiZWw9IlR3aXR0ZXIiIHJvbGU9ImltZyIKdmlld0JveD0iMCAwIDUxMiA1MTIiPjxwYXRoCmQ9Im0wIDBINTEyVjUxMkgwIgpmaWxsPSIjZmZmIi8+PHBhdGggZmlsbD0iIzFkOWJmMCIgZD0ibTQ1OCAxNDBxLTIzIDEwLTQ1IDEyIDI1LTE1IDM0LTQzLTI0IDE0LTUwIDE5YTc5IDc5IDAgMDAtMTM1IDcycS0xMDEtNy0xNjMtODNhODAgODAgMCAwMDI0IDEwNnEtMTcgMC0zNi0xMHMtMyA2MiA2NCA3OXEtMTkgNS0zNiAxczE1IDUzIDc0IDU1cS01MCA0MC0xMTcgMzNhMjI0IDIyNCAwIDAwMzQ2LTIwMHEyMy0xNiA0MC00MSIvPjwvc3ZnPg=='>
		</header>
		<section class="tweet-embed-text">{tweet_reply}{tweet_text}{tweet_media}</section>
		<hr class="tweet-embed-hr">
		<footer class="tweet-embed-footer">
			<a href="{tweet_url}" aria-label="{tweet_likes} likes" class="tweet-embed-likes">❤️ {tweet_likes}</a>
			<a href="{tweet_url}" aria-label="{tweet_replies} replies" class="tweet-embed-likes">💬 {tweet_replies}</a>
			<a href="{tweet_url}"><time datetime="{tweet_date}">{tweet_time}</time></a>
		</footer>
	</blockquote>
	'''
	return tweet_html

#   Get the data from the Twitter embed API
json_url =  f"https://cdn.syndication.twimg.com/tweet-result?id={tweet_id}&lang=en&token=1"
response = requests.get(json_url)
data = response.json()

tweet_html = tweet_to_html(data)

#   Generate HTML to be pasted

#	CSS
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
.tweet-embed-reply{
	font-size:.75em;
	display:block;
}
</style>
'''

#	Add the CSS to the output if requsted
if css_show :
	tweet_html = tweet_css + tweet_html

#   Compact the HTML if necessary
if not pretty_print :
	tweet_html = tweet_html.replace("\n", "")
	tweet_html = tweet_html.replace("\t", "")

#   Copy to clipboard
pyperclip.copy( tweet_html )

#   Print to say we've finished
print( f"Copied {tweet_id}" )

#	Save HTML
#   Save directory
output_directory = "output"
os.makedirs(output_directory, exist_ok = True)
#   Save as HTML file
with open(  os.path.join( output_directory, f"{tweet_id}.html" ) , 'w', encoding="utf-8" ) as html_file:
    html_file.write( tweet_html )