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

def get_media( media_attachments) :
	media_html = '<div class="tweet-embed-media-grid">'
	#	Iterate through the attached media
	for media in media_attachments :
		#	Convert small version of media to embedded WebP
		print( "Embedding media…" )
		media_img = image_to_inline( media["preview_url"] )
		
		#	Find alt text
		media_alt = ""
		if "description" in media :
			media_alt = html.escape( media["description"] )
	
		#	Is this a video or an image?
		if "video_info" in media :
			print( "Video poster…" )
			#	Embed the poster in the <video>, link to last video which should be highest quality
			#	TODO! Find a better way to get the best video
			media_html += f'''
			<video class='tweet-embed-video' controls src="{media["video_info"]["variants"][-1]["url"]}" poster="{media_img}" width="550"></video>
			'''
		else:
			#	Embed the image
			media_html += f'''
			<a href="{media['url']}" class="tweet-embed-media-link"><img class="tweet-embed-media" alt="{media_alt}" src="{media_img}"></a>
			'''
	return media_html + "</div>"

def get_card_html( card_data ) :
	poll_html = ""
	#	As per https://github.com/igorbrigadir/twitter-advanced-search
	card_name = card_data["name"] 
	print( "Card of type " + card_name )

	#	Poll
	if card_name == "poll2choice_text_only" or card_name == "poll3choice_text_only" or card_name == "poll4choice_text_only" :
		#	Default values
		poll_1_label = ""
		poll_2_label = ""
		poll_3_label = ""
		poll_4_label = ""
		poll_1_count = 0
		poll_2_count = 0
		poll_3_count = 0
		poll_4_count = 0

		#	Get labels and counts
		if "choice1_label" in card_data["binding_values"] :
			poll_1_label =        card_data["binding_values"]["choice1_label"]["string_value"]
			poll_1_count = (int) (card_data["binding_values"]["choice1_count"]["string_value"])
		if "choice2_label" in card_data["binding_values"] :
			poll_2_label =        card_data["binding_values"]["choice2_label"]["string_value"]
			poll_2_count = (int) (card_data["binding_values"]["choice2_count"]["string_value"])
		if "choice3_label" in card_data["binding_values"] :
			poll_3_label =        card_data["binding_values"]["choice3_label"]["string_value"]
			poll_3_count = (int) (card_data["binding_values"]["choice3_count"]["string_value"])
		if "choice4_label" in card_data["binding_values"] :
			poll_4_label =        card_data["binding_values"]["choice4_label"]["string_value"]
			poll_4_count = (int) (card_data["binding_values"]["choice4_count"]["string_value"])

		#	Calculate the percentages. Round to 1 decimal place.
		poll_total = poll_1_count + poll_2_count + poll_3_count + poll_4_count
		poll_1_percent = '{0:.1f}'.format( (poll_1_count / poll_total) * 100 )
		poll_2_percent = '{0:.1f}'.format( (poll_2_count / poll_total) * 100 )
		poll_3_percent = '{0:.1f}'.format( (poll_3_count / poll_total) * 100 )
		poll_4_percent = '{0:.1f}'.format( (poll_4_count / poll_total) * 100 )

		#	Generate semantic HTML
		if poll_1_label != "" :
			poll_html += f'''
				<hr class="tweet-embed-hr">
				<label for="poll_1_count">{poll_1_label}: ({poll_1_count:n})</label><br>
				<meter class="tweet-embed-meter" id="poll_1_count" min="0" max="100" low="33" high="66" value="{poll_1_percent}">{poll_1_count}</meter><br>
			'''
		if poll_2_label != "" :
			poll_html += f'''
				<label for="poll_2_count">{poll_2_label}: ({poll_2_count:n})</label><br>
				<meter class="tweet-embed-meter" id="poll_2_count" min="0" max="100" low="33" high="66" value="{poll_2_percent}">{poll_2_count}</meter><br>
			'''
		if poll_3_label != "" :
			poll_html += f'''
				<label for="poll_3_count">{poll_3_label}: ({poll_3_count:n})</label><br>
				<meter class="tweet-embed-meter" id="poll_3_count" min="0" max="100" low="33" high="66" value="{poll_3_percent}">{poll_3_count}</meter><br>
			'''
		if poll_4_label != "" :
			poll_html += f'''
				<label for="poll_4_count">{poll_4_label}: ({poll_4_count:n})</label><br>
				<meter class="tweet-embed-meter" id="poll_4_count" min="0" max="100" low="33" high="66" value="{poll_4_percent}">{poll_4_count}</meter>
			'''
		return poll_html

	#	Photo Card
	if "summary_large_image" == card_name :
		card_vanity           = ""
		card_vanity_html      = ""
		card_title            = ""
		card_title_html       = ""
		card_description      = ""
		card_description_html = ""
		card_thumbnail        = ""
		card_thumbnail_html   = ""
		card_thumbnail_alt    = ""
		card_url              = ""
		card_html             = ""

		if "vanity_url" in card_data["binding_values"] :
			card_vanity = card_data["binding_values"]["vanity_url"]["string_value"]
			card_vanity_html = f"{card_vanity}<br>"
		
		if "title" in card_data["binding_values"] :
			card_title = card_data["binding_values"]["title"]["string_value"]
			card_title_html = f"{card_title}<br>"
		
		if "description" in card_data["binding_values"] :
			card_description = card_data["binding_values"]["description"]["string_value"]
			card_description_html = f"{card_description}<br>"
		
		if "summary_photo_image_alt_text" in card_data["binding_values"] :
			card_thumbnail_alt = html.escape( card_data["binding_values"]["summary_photo_image_alt_text"]["string_value"] )
		
		if "thumbnail_image" in card_data["binding_values"] :
			print( "Converting card's thumbnail_image…" )
			card_thumbnail = card_data["binding_values"]["thumbnail_image"]["image_value"]["url"]
			#   Convert  media to embedded WebP
			card_thumbnail = image_to_inline( card_thumbnail )
			card_thumbnail_html = f'''
				<img src="{card_thumbnail}" alt="{card_thumbnail_alt}" class="tweet-embed-media">
				'''
		
		if "url" in card_data :
			card_url = card_data["url"]

		card_html += f'''
			<a href="{card_url}" class="tweet-embed-card">
				{card_thumbnail_html}
				{card_vanity_html}
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


	# tweet_entities = tweet_data["entities"]

	# #	User labels
	# if "highlighted_label" in tweet_data["user"] :
	# 	tweet_label     = html.escape( tweet_data["user"]["highlighted_label"]["description"] )
	# 	tweet_badge_img = image_to_inline( tweet_data["user"]["highlighted_label"]["badge"]["url"] )
	# 	print( f"Badge found '{tweet_label}'…")
	# 	tweet_badge  = f'<br><img src="{tweet_badge_img}" alt="" class="tweet-embed-badge"> {tweet_label}'
	# else :
	# 	tweet_badge = ""

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
	# 		<small class="tweet-embed-reply"><a href="{tweet_reply_link}">Replying to @{tweet_reply_to}</a></small>
	# 	'''
	# else :
	# 	tweet_reply = ""

	# #   Embed entities
	# tweet_text = tweet_entities_to_html( tweet_text, tweet_entities )

	#	Add media
	mastodon_media = ""
	if ( "media_attachments" in mastodon_data ) :
		mastodon_media = get_media( mastodon_data["media_attachments"] )

	# #	Add card
	# tweet_card = ""
	# if "card" in tweet_data :
	# 	tweet_card = get_card_html( tweet_data["card"] )

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
	<blockquote class="tweet-embed" id="tweet-embed-{mastodon_id}" lang="{mastodon_language}"{schema_post}>
		<header class="tweet-embed-header"{schema_author}>
			<a href="{user_url}" class="tweet-embed-user"{schema_url}>
				<img class="tweet-embed-avatar" src="{user_avatar}" alt=""{schema_image}>
				<div class="tweet-embed-user-names">
					<p class="tweet-embed-user-names-name"{schema_name}>{user_name}</p>@{user_display}
				</div>
			</a>
			<img class="tweet-embed-logo" alt="Mastodon" src='data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciCmFyaWEtbGFiZWw9Ik1hc3RvZG9uIiByb2xlPSJpbWciCnZpZXdCb3g9IjAgMCA1MTIgNTEyIgpmaWxsPSIjZmZmIj48cGF0aApkPSJtMCAwSDUxMlY1MTJIMCIvPjxsaW5lYXJHcmFkaWVudCBpZD0iYSIgeTI9IjEiPjxzdG9wIG9mZnNldD0iMCIgc3RvcC1jb2xvcj0iIzYzNjRmZiIvPjxzdG9wIG9mZnNldD0iMSIgc3RvcC1jb2xvcj0iIzU2M2FjYyIvPjwvbGluZWFyR3JhZGllbnQ+PHBhdGggZmlsbD0idXJsKCNhKSIgZD0iTTMxNyAzODFxLTEyNCAyOC0xMjMtMzkgNjkgMTUgMTQ5IDIgNjctMTMgNzItODAgMy0xMDEtMy0xMTYtMTktNDktNzItNTgtOTgtMTAtMTYyIDAtNTYgMTAtNzUgNTgtMTIgMzEtMyAxNDcgMyAzMiA5IDUzIDEzIDQ2IDcwIDY5IDgzIDIzIDEzOC05Ii8+PHBhdGggZD0iTTM2MCAyOTNoLTM2di05M3EtMS0yNi0yOS0yMy0yMCAzLTIwIDM0djQ3aC0zNnYtNDdxMC0zMS0yMC0zNC0zMC0zLTMwIDI4djg4aC0zNnYtOTFxMS01MSA0NC02MCAzMy01IDUxIDIxbDkgMTUgOS0xNXExNi0yNiA1MS0yMSA0MyA5IDQzIDYwIi8+PC9zdmc+'>
		</header>
		<section class="tweet-embed-text"{schema_body}>
			{mastodon_text}
			{mastodon_media}
		</section>
		<hr class="tweet-embed-hr">
		<footer class="tweet-embed-footer">
			<a href="{mastodon_url}">
				<span aria-label="{mastodon_likes} likes" class="tweet-embed-meta">❤️ {mastodon_likes:n}</span>
				<span aria-label="{mastodon_replies} replies" class="tweet-embed-meta">💬 {mastodon_replies:n}</span>
				<span aria-label="{mastodon_retweets} reposts" class="tweet-embed-meta">♻️ {mastodon_retweets:n}</span>
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

# #	If Tweet was deleted, exit.
# if "TweetTombstone" == data["__typename"] :
# 	print( "This Post was deleted by the Post author." )
# 	raise SystemExit

#	Turn the Tweet into HTML
mastodon_html = mastodon_to_html( data )

#   Generate Content to be pasted

#	CSS
tweet_css = '''
<style>
.tweet-embed{
	all:unset;
	display:block;
}
.tweet-embed * {
	all:unset;
	display:revert;
}
.tweet-embed::after{
	all:unset;
}
.tweet-embed::before{
	all:unset;
}
blockquote:not(*){
	all:unset;
}
.tweet-embed a{
	cursor:pointer;
}
blockquote.tweet-embed{
	box-sizing:border-box;
	border:.5px solid;
	width:550px;
	max-width:100%;
	font-family:sans-serif;
	margin:auto;
	margin-bottom:.5em;
	padding:1em;
	border-radius:1em;
	background-color:#FFF;
	color:#000;
	display:block;
}
.tweet-embed-header{
	display:flex;
	justify-content:space-between;
}
.tweet-embed-user{
	display:flex;
	position:relative;
	align-items:center;
	text-decoration:none;
	color:inherit;
}
.tweet-embed-avatar{
	width:3em;
	height:3em;
	margin-right:.5em;
}
.tweet-embed-avatar-circle{
	border-radius:50%;
}
.tweet-embed-avatar-square{
	border-radius:5%;
}
.tweet-embed-user-names-name{
	display:flex;
	align-items:center;
	font-weight:bold;
	margin:0;
}
.tweet-embed-text{
	margin-top:.5em;
}
.tweet-embed-footer a{
	display:flex;
	align-items:center;
	justify-content:space-between;
}
.tweet-embed-logo{
	width:3em;
}
.tweet-embed-hr{
	border:.1px solid;
	margin:.5em 0 .5em 0;
}
.tweet-embed-meta{
	text-decoration:none !important;
	color:unset !important;
}
.tweet-embed-reply{
	display:block;
}
.tweet-embed-text a, .tweet-embed-footer time{
	color:blue;
	text-decoration:underline;
}
.tweet-embed-media-grid {
	display: flex;
	flex-wrap: wrap;
}
.tweet-embed-media-link {
	flex-grow: 1;
	width: 50%;
}
.tweet-embed-media, .tweet-embed-video {
	padding: .1em;
	width: 100%;
	border-radius:1em;
	max-width:100%;
	object-fit: cover;
	height: 100%;
}
.tweet-embed-reply{
	font-size:.75em;
	display:block;
}
.tweet-embed-meter{
	width:100%;
	background:#0005;
}
.tweet-embed-card{
	text-decoration:none !important;
	color:unset !important;
	border:.5px solid;
	display:block;
	font-size:.85em;
	padding:.5em;
	border-radius:1em;
}
.tweet-embed-badge{
	height:1em;
	vertical-align: text-top;
}
</style>
'''

#	Add the CSS to the output if requsted
if css_show :
	mastodon_html = tweet_css + mastodon_html

#   Compact the output if necessary
if not pretty_print :
	print( "Compacting…")
	mastodon_html = mastodon_html.replace("\n", "")
	mastodon_html = mastodon_html.replace("\t", "")

#   Copy to clipboard
pyperclip.copy( mastodon_html )
#   Print to say we've finished
print( f"Copied {mastodon_url}" )

if save_file :
	#	Save HTML
	#   Save directory
	output_directory = "output"
	os.makedirs(output_directory, exist_ok = True)
	mastodon_file_name = "".join(x for x in mastodon_url if x.isalnum())

	save_location = os.path.join( output_directory, f"{mastodon_file_name}.html" ) 
	#   Save as HTML file
	with open( save_location, 'w', encoding="utf-8" ) as html_file:
		html_file.write( mastodon_html )
	print( f"Saved to {save_location}" )

#	Submit the Tweet to Archive.org
print( f"Archiving… {mastodon_url}" )
requests.post( "https://web.archive.org/save/", data={"url": mastodon_url, "capture_all":"on"}, timeout=5 )