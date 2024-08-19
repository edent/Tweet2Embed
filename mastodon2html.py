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
import random

#	Date manipulation
from datetime import datetime
from dateutil import parser

#	Formatting
import locale
locale.setlocale(locale.LC_ALL, '')

#	URl manipulation
import urllib
from urllib.parse import urlparse

#   Command line options
arguments = argparse.ArgumentParser(
	prog="mastodon2html",
	description="Convert a Tweet ID to semantic HTML")
arguments.add_argument("id", type=str,                        help="URl of the Mastodon post")
arguments.add_argument("-t", "--thread", action="store_true", help="Show the thread (default false)", required=False)
arguments.add_argument("-c", "--css",    action="store_true", help="Copy the CSS (default false)",    required=False)
arguments.add_argument("-p", "--pretty", action="store_true", help="Pretty Print the output (default false)",    required=False)
arguments.add_argument("-s", "--save",   action="store_true", help="Save the output to a file (default false)",    required=False)
arguments.add_argument("-m", "--schema", action='store_true', help="Add Schema.org metadata (default false)",    required=False)

args = arguments.parse_args()

#	Get Mastodon information
mastodon_url   = args.id
mastodon_parts = urlparse( mastodon_url )
mastodon_host  = mastodon_parts.netloc
mastodon_path  = mastodon_parts.path
mastodon_id    = mastodon_path.split("/")[-1] #	Last element of /@example/123456
mastodon_api   = f"https://{mastodon_host}/api/v1/statuses/{mastodon_id}"

#	Get settings from arguments
thread_show  = True if args.thread else False
css_show     = True if args.css    else False
pretty_print = True if args.pretty else False
save_file    = True if args.save   else False
schema_org   = True if args.schema else False

def image_to_inline( url ) : 
	#	Download the image
	image_file = requests.get( url )
	#	Convert to bytes
	image_file = Image.open( io.BytesIO( image_file.content ) )
	#	Temp file name with only alphanumeric characters
	temp_file_name = "".join(x for x in url if x.isalnum())
	#	Full path of the image
	output_img = os.path.join( tempfile.gettempdir() , f"{temp_file_name}.webp" )
	#	Save as a low quality WebP
	image_file.save( output_img, 'webp', optimize=True, quality=60 )
	#   Convert image to base64 data URl
	#	Read the image from disk
	binary_img      = open( output_img, 'rb' ).read()
	#	Encode to Base64
	base64_utf8_str = base64.b64encode( binary_img ).decode('utf-8')
	#	Delete the temporary file
	os.remove( output_img )
	#	Return as data encoded suitable for an <img src="...">
	return f'data:image/webp;base64,{base64_utf8_str}'

def mastodon_emojis( mastodon_text, emojis ) :
	for emoji in emojis:
		shortcode = emoji["shortcode"]
		url	      = emoji["url"]
		emoji_img = image_to_inline( url )
		emoji_img_html = f'<img src="{emoji_img}" alt=":{shortcode}:" class="mastodon-embed-emoji">'
		mastodon_text = mastodon_text.replace( f":{shortcode}:", emoji_img_html )
	return mastodon_text


def get_media( media_attachments) :
	media_html = '<div class="mastodon-embed-media-grid">'
	#	Iterate through the attached media
	for media in media_attachments :
		media_type = media["type"]

		#	Convert small version of media to embedded WebP
		print( "Embedding media…" )
		media_img = image_to_inline( media["preview_url"] )
		
		#	Find alt text
		media_alt = ""
		if "description" in media :
			if media["description"] is not None:
				media_alt = html.escape( media["description"] )
	
		#	Is this a video or an image?
		if "video" == media_type :
			print( "Video poster…" )
			#	Embed the poster in the <video>, link to last video which should be highest quality
			#	TODO! Find a better way to get the best video
			media_html += f'''
			<video class='mastodon-embed-video' controls src="{media["url"]}" poster="{media_img}" width="550"></video>
			'''
		if "image" == media_type :
			#	Embed the image
			media_html += f'''
			<a href="{media['url']}" class="mastodon-embed-media-link"><img class="mastodon-embed-media" alt="{media_alt}" src="{media_img}"></a>
			'''
	return media_html + "</div>"

def get_poll_html( poll_data ) :
	print( "Poll…")
	poll_html = "<hr class=\"mastodon-embed-hr\">"

	votes_count = poll_data["votes_count"]

	option_counter = 0

	for option in poll_data["options"] :
		option_title = option["title"]
		#	Calculate the percentages. Round to 1 decimal place.
		option_votes = option["votes_count"]
		if votes_count > 0 :
			option_percent = '{0:.1f}'.format( (option_votes / votes_count) * 100 )
		else :
			option_percent = "0"

		#	Generate semantic HTML
		poll_html += f'''
			<label for="poll_{option_counter}">{option_title}: ({option_votes:n})</label><br>
			<meter class="mastodon-embed-meter" id="poll_{option_counter}" min="0" max="100" low="33" high="66" value="{option_percent}">{option_votes}</meter><br>
		'''

		option_counter += 1
	
	return poll_html

def get_card_html( card_data ) :
	card_type = card_data["type"] 
	print( "Card of type " + card_type )

	#	Photo Card
	if "photo" == card_type or "link" == card_type :
		card_title            = ""
		card_title_html       = ""
		card_description      = ""
		card_description_html = ""
		card_thumbnail        = ""
		card_thumbnail_html   = ""
		card_thumbnail_alt    = ""
		card_url              = ""
		card_html             = ""
		
		if "provider_name" in card_data:
			card_provider = card_data["provider_name"]
			card_provider_html = f"{card_provider}<br>"

		if "title" in card_data:
			card_title = card_data["title"]
			card_title_html = f"{card_title}<br>"
		
		if "description" in card_data :
			card_description = card_data["description"]
			card_description_html = f"{card_description}<br>"
		
		if "image_description" in card_data :
			card_thumbnail_alt = html.escape( card_data["image_description"] )
		
		if "image" in card_data :
			print( "Converting card's thumbnail_image…" )
			card_thumbnail = card_data["image"]
			#   Convert  media to embedded WebP
			card_thumbnail = image_to_inline( card_thumbnail )
			card_thumbnail_html = f'''
				<div class="mastodon-embed-media-grid">
					<img src="{card_thumbnail}" alt="{card_thumbnail_alt}" class="mastodon-embed-media">
				</div>
				'''
		
		if "url" in card_data :
			card_url = card_data["url"]

		card_html += f'''
			<a href="{card_url}" class="mastodon-embed-card">
				{card_thumbnail_html}
				{card_provider_html}
				{card_title_html}
				{card_description_html}
			</a>
		'''
		return card_html

def mastodon_to_html( mastodon_data ) :
	#	Show the thread / quote?
	# tweet_parent = ""
	# tweet_quote  = ""
	# if thread_show :
	# 	if "parent" in tweet_data :
	# 		print( "Parent detected…" )
	# 		tweet_parent = tweet_to_html( tweet_data["parent"] )
	# 	if "quoted_tweet" in tweet_data :
	# 		print( "Quote detected…" )
	# 		tweet_quote = tweet_to_html( tweet_data["quoted_tweet"] )

	#	Take the data from the API of a single Tweet (which might also be a quote or reply).
	#	Create a semantic HTML representation
	#   Post Information
	mastodon_id       = mastodon_data["id"]
	mastodon_url      = mastodon_data["url"]
	mastodon_text     = mastodon_data["content"]
	mastodon_date     = mastodon_data["created_at"] 
	mastodon_language = mastodon_data["language"]
	print( f"Detected language - {mastodon_language}" )

	mastodon_likes    = (int)(mastodon_data.get("favourites_count", 0))#	Might not exist
	mastodon_replies  = (int)(mastodon_data.get("replies_count",    0))#	Might not exist
	mastodon_retweets = (int)(mastodon_data.get("reblogs_count",    0))#	Might not exist

	#	User information
	user_name         = mastodon_data["account"]["username"]
	user_display      = mastodon_data["account"]["display_name"]
	user_avatar       = mastodon_data["account"]["avatar"]
	user_url          = mastodon_data["account"]["url"]
	user_bot          = (bool)(mastodon_data["account"].get("bot",  False))

	#	User labels
	if user_bot :
		user_label     = "Automated"
		user_badge_img = "🤖"
		print( f"Bot found …")
		user_badge  = f'<br>{user_badge_img} {user_label}'
	else :
		user_badge = ""

	#	Get the datetime
	mastodon_time = parser.parse( mastodon_date )
	mastodon_time = mastodon_time.strftime('%H:%M - %a %d %B %Y')

	#	Is this a reply?
	# if "in_reply_to_screen_name" in tweet_data :
	# 	tweet_reply_to   = tweet_data["in_reply_to_screen_name"]
	# 	tweet_reply_id = tweet_data.get("in_reply_to_status_id_str","")	#	Doesn't exist on older tweets
	# 	if "" == tweet_reply_id :
	# 		tweet_reply_link = f'https://twitter.com/{tweet_reply_to}'
	# 	else :
	# 		tweet_reply_link = f'https://twitter.com/{tweet_reply_to}/status/{tweet_reply_id}'
	# 	tweet_reply = f'''
	# 		<small class="mastodon-embed-reply"><a href="{tweet_reply_link}">Replying to @{tweet_reply_to}</a></small>
	# 	'''
	# else :
	# 	tweet_reply = ""

	# #   Embed entities
	# tweet_text = tweet_entities_to_html( tweet_text, tweet_entities )

	#	Add shortcode emoji to text
	if "emojis" in mastodon_data :
		if mastodon_data["emojis"] is not None :
			mastodon_text = mastodon_emojis( mastodon_text, mastodon_data["emojis"] )

	#	Add media
	mastodon_media = ""
	if ( "media_attachments" in mastodon_data ) :
		if mastodon_data["media_attachments"] is not None :
			mastodon_media = get_media( mastodon_data["media_attachments"] )

	#	Add card
	mastodon_card = ""
	if "card" in mastodon_data :
		if mastodon_data["card"] is not None :
			mastodon_card = get_card_html( mastodon_data["card"] )
	
	#	Add poll
	mastodon_poll = ""
	if "poll" in mastodon_data :
		if mastodon_data["poll"] is not None :
			mastodon_poll = get_poll_html( mastodon_data["poll"] )

	#   Convert avatar to embedded WebP
	print( "Storing avatar…")
	mastodon_avatar = image_to_inline( user_avatar )

	#	Schema.org metadata
	schema_post   = ' itemscope itemtype="https://schema.org/SocialMediaPosting"'       if schema_org else ""
	schema_body   = ' itemprop="articleBody"'   if schema_org else ""
	schema_time   = ' itemprop="datePublished"' if schema_org else ""
	schema_author = ' itemprop="author" itemscope itemtype="https://schema.org/Person"' if schema_org else ""
	schema_url    = ' itemprop="url"'   if schema_org else ""
	schema_image  = ' itemprop="image"' if schema_org else ""
	schema_name   = ' itemprop="name"'  if schema_org else ""

	#   HTML
	mastodon_html = f'''
	<blockquote class="mastodon-embed" id="mastodon-embed-{mastodon_id}" lang="{mastodon_language}"{schema_post}>
		<header class="mastodon-embed-header"{schema_author}>
			<a href="{user_url}" class="mastodon-embed-user"{schema_url}>
				<img class="mastodon-embed-avatar" src="{user_avatar}" alt=""{schema_image}>
				<div class="mastodon-embed-user-names">
					<p class="mastodon-embed-user-names-name"{schema_name}>{user_name}</p>@{user_display}{user_badge}
				</div>
			</a>
			<img class="mastodon-embed-logo" alt="Mastodon" src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' aria-label='Mastodon' role='img' viewBox='0 0 512 512' fill='%23fff'%3E%3Cpath d='m0 0H512V512H0'/%3E%3ClinearGradient id='a' y2='1'%3E%3Cstop offset='0' stop-color='%236364ff'/%3E%3Cstop offset='1' stop-color='%23563acc'/%3E%3C/linearGradient%3E%3Cpath fill='url(%23a)' d='M317 381q-124 28-123-39 69 15 149 2 67-13 72-80 3-101-3-116-19-49-72-58-98-10-162 0-56 10-75 58-12 31-3 147 3 32 9 53 13 46 70 69 83 23 138-9'/%3E%3Cpath d='M360 293h-36v-93q-1-26-29-23-20 3-20 34v47h-36v-47q0-31-20-34-30-3-30 28v88h-36v-91q1-51 44-60 33-5 51 21l9 15 9-15q16-26 51-21 43 9 43 60'/%3E%3C/svg%3E" >
		</header>
		<section class="mastodon-embed-text"{schema_body}>
			{mastodon_text}
			{mastodon_media}
			{mastodon_poll}
			{mastodon_card}
		</section>
		<hr class="mastodon-embed-hr">
		<footer class="mastodon-embed-footer">
			<a href="{mastodon_url}">
				<span aria-label="{mastodon_likes} likes" class="mastodon-embed-meta">❤️ {mastodon_likes:n}</span>
				<span aria-label="{mastodon_replies} replies" class="mastodon-embed-meta">💬 {mastodon_replies:n}</span>
				<span aria-label="{mastodon_retweets} reposts" class="mastodon-embed-meta">🔁 {mastodon_retweets:n}</span>
				<time datetime="{mastodon_date}"{schema_time}>{mastodon_time}</time>
			</a>
		</footer>
	</blockquote>
	'''
	return mastodon_html

#   Get the data from the Mastodon API
for _ in range(5):
	#	Lazy retry strategy
	try :
		print( f"Downloading {mastodon_api}" )
		response = requests.get( mastodon_api )
		data = response.json()
		break
	except :
		print( "Retrying…" )
		continue

#	If Post was deleted, exit.
if "error" in data :
	print( "This post doesn't exist." )
	raise SystemExit

#	Turn the Tweet into HTML
mastodon_html = mastodon_to_html( data )

#   Generate Content to be pasted

#	CSS
mastodon_css = '''
<style>
.mastodon-embed{
	all:unset;
	display:block;
}
.mastodon-embed * {
	all:unset;
	display:revert;
}
.mastodon-embed::after{
	all:unset;
}
.mastodon-embed::before{
	all:unset;
}
blockquote:not(*){
	all:unset;
}
.mastodon-embed a{
	cursor:pointer;
}
blockquote.mastodon-embed{
	box-sizing:border-box;
	border:.5px solid;
	width:550px;
	max-width:100%;
	font-family:sans-serif;
	margin:auto;
	margin-bottom:.5em;
	padding:1em;
	border-radius:.5em;
	background-color:#FFF;
	color:#000;
	display:block;
}
.mastodon-embed-header{
	display:flex;
	justify-content:space-between;
}
.mastodon-embed-user{
	display:flex;
	position:relative;
	align-items:center;
	text-decoration:none;
	color:inherit;
}
.mastodon-embed-avatar{
	width:3em;
	height:3em;
	margin-right:.5em;
}
.mastodon-embed-avatar-circle{
	border-radius:50%;
}
.mastodon-embed-avatar-square{
	border-radius:5%;
}
.mastodon-embed-user-names-name{
	display:flex;
	align-items:center;
	font-weight:bold;
	margin:0;
}
.mastodon-embed-text{
	margin-top:.5em;
}
.mastodon-embed-footer a{
	display:flex;
	align-items:center;
	justify-content:space-between;
}
.mastodon-embed-logo{
	width:3em;
}
.mastodon-embed-hr{
	border:.1px solid;
	margin:.5em 0 .5em 0;
}
.mastodon-embed-meta{
	text-decoration:none !important;
	color:unset !important;
}
.mastodon-embed-reply{
	display:block;
}
.mastodon-embed-text a, .mastodon-embed-footer time{
	color:blue;
	text-decoration:underline;
}
.mastodon-embed-media-grid {
	display: flex;
	flex-wrap: wrap;
}
.mastodon-embed-media-link {
	flex-grow: 1;
	width: 50%;
}
.mastodon-embed-media, .mastodon-embed-video {
	padding: .1em;
	width: 100%;
	border-radius:.5em;
	max-width:100%;
	object-fit: cover;
	height: 100%;
}
.mastodon-embed-reply{
	font-size:.75em;
	display:block;
}
.mastodon-embed-meter{
	width:100%;
	background:#0005;
}
.mastodon-embed-card{
	text-decoration:none !important;
	color:unset !important;
	border:.5px solid;
	display:block;
	font-size:.85em;
	padding:.5em;
	border-radius:.5em;
}
.mastodon-embed-badge{
	height:1em;
	vertical-align: text-top;
}
.mastodon-embed-text p {
	margin-bottom:1em;
}
.mastodon-embed-emoji{
	display:inline;
	width:1em;
}
</style>
'''

#   Compact the output if necessary
if not pretty_print :
	print( "Compacting…")
	mastodon_html = mastodon_html.replace("\n", "").replace("\t", "")
	mastodon_css  = mastodon_css.replace("\n", "").replace("\t", "")
	#	Inline CSS
	mastodon_css = '<link rel="stylesheet" type="text/css" href="data:text/css,' + urllib.parse.quote(mastodon_css) + '">'

#	Add the CSS to the output if requsted
if css_show :
	mastodon_html = mastodon_css + mastodon_html

#   Copy to clipboard
pyperclip.copy( mastodon_html )

#   Print to say we've finished
print( f"Copied {mastodon_url}" )

if save_file :
	#	Save HTML
	#   Save directory
	output_directory = "output"
	os.makedirs(output_directory, exist_ok = True)
	#	Make URl filename safe
	mastodon_file_name = "".join(x for x in mastodon_url if x.isalnum())
	save_location = os.path.join( output_directory, f"{mastodon_file_name}.html" ) 
	#   Save as HTML file
	with open( save_location, 'w', encoding="utf-8" ) as html_file:
		html_file.write( mastodon_html )
	print( f"Saved to {save_location}" )

#	Submit the Tweet to Archive.org
print( f"Archiving… {mastodon_url}" )
requests.post( "https://web.archive.org/save/", data={"url": mastodon_url, "capture_all":"on"}, timeout=5 )
