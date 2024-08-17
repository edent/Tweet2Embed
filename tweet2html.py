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

#   Command line options
arguments = argparse.ArgumentParser(
	prog='tweet2html',
	description='Convert a Tweet ID to semantic HTML')
arguments.add_argument("id", type=int,                        help="ID of the Tweet (integer)")
arguments.add_argument("-t", "--thread", action="store_true", help="Show the thread (default false)", required=False)
arguments.add_argument("-c", "--css",    action="store_true", help="Copy the CSS (default false)",    required=False)
arguments.add_argument("-p", "--pretty", action="store_true", help="Pretty Print the output (default false)",    required=False)
arguments.add_argument("-s", "--save",   action="store_true", help="Save the output to a file (default false)",    required=False)
arguments.add_argument("-m", "--schema", action='store_true', help="Add Schema.org metadata (default false)",    required=False)

args = arguments.parse_args()
tweet_id = args.id

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
	media_html = '<div class="tweet-embed-media-grid">'
	#	Iterate through the attached media
	for media in mediaDetails :
		#	Convert small version of media to embedded WebP
		print( "Embedding media…" )
		media_img = image_to_inline( media["media_url_https"] + ":small" )
		
		#	Find alt text
		media_alt = ""
		if "ext_alt_text" in media :
			media_alt = html.escape( media["ext_alt_text"] )
	
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
			<a href="{media['media_url_https']}" class="tweet-embed-media-link"><img class="tweet-embed-media" alt="{media_alt}" src="{media_img}"></a>
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

def tweet_to_html( tweet_data ) :
	#	Show the thread / quote?
	tweet_parent = ""
	tweet_quote  = ""
	if thread_show :
		if "parent" in tweet_data :
			print( "Parent detected…" )
			tweet_parent = tweet_to_html( tweet_data["parent"] )
		if "quoted_tweet" in tweet_data :
			print( "Quote detected…" )
			tweet_quote = tweet_to_html( tweet_data["quoted_tweet"] )

	#	Take the data from the API of a single Tweet (which might also be a quote or reply).
	#	Create a semantic HTML representation
	#   Tweet Information
	tweet_id       = tweet_data["id_str"]
	tweet_name     = tweet_data["user"]["name"]
	tweet_user     = tweet_data["user"]["screen_name"]
	tweet_avatar   = tweet_data["user"]["profile_image_url_https"]
	tweet_shape    = tweet_data["user"].get("profile_image_shape", "Square")#	Some users don't have this
	tweet_text     = tweet_data["text"]
	tweet_date     = tweet_data["created_at"] 
	tweet_lang     = tweet_data["lang"]
	print( f"Detected language - {tweet_lang}" )

	tweet_likes    = (int)(tweet_data.get("favorite_count",     0))#	Might not exist
	tweet_replies  = (int)(tweet_data.get("conversation_count", 0))#	Might not exist
	tweet_retweets = (int)(tweet_data.get("retweet_count",      0))#	Might not exist
	tweet_entities = tweet_data["entities"]
	global tweet_url
	tweet_url      = f"https://twitter.com/{tweet_user}/status/{tweet_id}"

	#	User labels
	if "highlighted_label" in tweet_data["user"] :
		tweet_label     = html.escape( tweet_data["user"]["highlighted_label"]["description"] )
		tweet_badge_img = image_to_inline( tweet_data["user"]["highlighted_label"]["badge"]["url"] )
		print( f"Badge found '{tweet_label}'…")
		tweet_badge  = f'<br><img src="{tweet_badge_img}" alt="" class="tweet-embed-badge"> {tweet_label}'
	else :
		tweet_badge = ""

	#	Get the datetime
	tweet_time = parser.parse( tweet_date )
	tweet_time = tweet_time.strftime('%H:%M - %a %d %B %Y')

	#	Is this a reply?
	if "in_reply_to_screen_name" in tweet_data :
		tweet_reply_to   = tweet_data["in_reply_to_screen_name"]
		tweet_reply_id = tweet_data.get("in_reply_to_status_id_str","")	#	Doesn't exist on older tweets
		if "" == tweet_reply_id :
			tweet_reply_link = f'https://twitter.com/{tweet_reply_to}'
		else :
			tweet_reply_link = f'https://twitter.com/{tweet_reply_to}/status/{tweet_reply_id}'
		tweet_reply = f'''
			<small class="tweet-embed-reply"><a href="{tweet_reply_link}">Replying to @{tweet_reply_to}</a></small>
		'''
	else :
		tweet_reply = ""

	#   Embed entities
	tweet_text = tweet_entities_to_html( tweet_text, tweet_entities )

	#	Add media
	tweet_media = ""
	if ( "mediaDetails" in tweet_data ) :
		tweet_media = get_media( tweet_data["mediaDetails"] )

	#	Add card
	tweet_card = ""
	if "card" in tweet_data :
		tweet_card = get_card_html( tweet_data["card"] )

	#   Newlines to BR
	tweet_text = tweet_text.replace("\n","<br>")

	#   Convert avatar to embedded WebP
	print( "Storing avatar…")
	tweet_avatar = image_to_inline( tweet_avatar )

	#	Avatar shape
	if tweet_shape == "Circle" :
		avatar_shape = "tweet-embed-avatar-circle"
	elif tweet_shape == "Square" :
		avatar_shape = "tweet-embed-avatar-square"
	else :
		avatar_shape = "tweet-embed-avatar-circle"

	#	Schema.org metadata
	schema_post   = ' itemscope itemtype="https://schema.org/SocialMediaPosting"'       if schema_org else ""
	schema_body   = ' itemprop="articleBody"'   if schema_org else ""
	schema_time   = ' itemprop="datePublished"' if schema_org else ""
	schema_author = ' itemprop="author" itemscope itemtype="https://schema.org/Person"' if schema_org else ""
	schema_url    = ' itemprop="url"'   if schema_org else ""
	schema_image  = ' itemprop="image"' if schema_org else ""
	schema_name   = ' itemprop="name"'  if schema_org else ""

	#   HTML
	tweet_html = f'''
	<blockquote class="tweet-embed" id="tweet-embed-{tweet_id}" lang="{tweet_lang}"{schema_post}>
		{tweet_parent}
		<header class="tweet-embed-header"{schema_author}>
			<a href="https://twitter.com/{tweet_user}" class="tweet-embed-user"{schema_url}>
				<img class="tweet-embed-avatar {avatar_shape}" src="{tweet_avatar}" alt=""{schema_image}>
				<div class="tweet-embed-user-names">
					<p class="tweet-embed-user-names-name"{schema_name}>{tweet_name}</p>@{tweet_user}{tweet_badge}
				</div>
			</a>
			<img class="tweet-embed-logo" alt="" src='data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciCmFyaWEtbGFiZWw9IlR3aXR0ZXIiIHJvbGU9ImltZyIKdmlld0JveD0iMCAwIDUxMiA1MTIiPjxwYXRoCmQ9Im0wIDBINTEyVjUxMkgwIgpmaWxsPSIjZmZmIi8+PHBhdGggZmlsbD0iIzFkOWJmMCIgZD0ibTQ1OCAxNDBxLTIzIDEwLTQ1IDEyIDI1LTE1IDM0LTQzLTI0IDE0LTUwIDE5YTc5IDc5IDAgMDAtMTM1IDcycS0xMDEtNy0xNjMtODNhODAgODAgMCAwMDI0IDEwNnEtMTcgMC0zNi0xMHMtMyA2MiA2NCA3OXEtMTkgNS0zNiAxczE1IDUzIDc0IDU1cS01MCA0MC0xMTcgMzNhMjI0IDIyNCAwIDAwMzQ2LTIwMHEyMy0xNiA0MC00MSIvPjwvc3ZnPg=='>
		</header>
		<section class="tweet-embed-text"{schema_body}>
			{tweet_reply}
			{tweet_text}
			{tweet_media}
			{tweet_card}
			{tweet_quote}
		</section>
		<hr class="tweet-embed-hr">
		<footer class="tweet-embed-footer">
			<a href="{tweet_url}" aria-label="{tweet_likes} likes" class="tweet-embed-meta">❤️ {tweet_likes:n}</a>
			<a href="{tweet_url}" aria-label="{tweet_replies} replies" class="tweet-embed-meta">💬 {tweet_replies:n}</a>
			<a href="{tweet_url}" aria-label="{tweet_retweets} retweets" class="tweet-embed-meta">♻️ {tweet_retweets:n}</a>			
			<a href="{tweet_url}"><time datetime="{tweet_date}"{schema_time}>{tweet_time}</time></a>
		</footer>
	</blockquote>
	'''
	return tweet_html

#   Get the data from the Twitter embed API
for _ in range(5):
	#	Lazy retry strategy
	try :
		print( "Downloading data…" )
		token = random.randint(1,10000)
		json_url =  f"https://cdn.syndication.twimg.com/tweet-result?id={tweet_id}&lang=en&token={token}"
		response = requests.get(json_url)
		data = response.json()
		break
	except :
		print( "Retrying…" )
		continue

#	If Tweet was deleted, exit.
if "TweetTombstone" == data["__typename"] :
	print( "This Post was deleted by the Post author." )
	raise SystemExit

#	Turn the Tweet into HTML
tweet_html = tweet_to_html(data)

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
.tweet-embed-footer{
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
	tweet_html = tweet_css + tweet_html

#   Compact the output if necessary
if not pretty_print :
	print( "Compacting…")
	tweet_html = tweet_html.replace("\n", "")
	tweet_html = tweet_html.replace("\t", "")

#   Copy to clipboard
pyperclip.copy( tweet_html )
#   Print to say we've finished
print( f"Copied {tweet_id}" )

if save_file :
	#	Save HTML
	#   Save directory
	output_directory = "output"
	os.makedirs(output_directory, exist_ok = True)
	save_location = os.path.join( output_directory, f"{tweet_id}.html" ) 
	#   Save as HTML file
	with open( save_location, 'w', encoding="utf-8" ) as html_file:
		html_file.write( tweet_html )
	print( f"Saved to {save_location}" )

#	Submit the Tweet to Archive.org
print( f"Archiving… {tweet_url}" )
requests.post( "https://web.archive.org/save/", data={"url": tweet_url, "capture_all":"on"}, timeout=5 )
