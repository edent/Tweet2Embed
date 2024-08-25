#   For command line
import argparse

#   File and Bits
import os
import json

#   Etc
import requests
import random
from urllib.parse import urlparse

def is_valid_url(url):
	try:
		result = urlparse(url)
		return all([result.scheme, result.netloc, result.path])
	except ValueError:
		return False

#   Command line options
arguments = argparse.ArgumentParser(
	prog='tweet2json',
	description='Download the JSON representation of any public Tweet')
arguments.add_argument("id", type=str,                        help="ID of the Tweet (integer)")
arguments.add_argument("-p", "--pretty", action="store_true", help="Pretty Print the output (default false)",    required=False)

args = arguments.parse_args()

if (is_valid_url(args.id)):
	url_parts = result = urlparse(args.id)
	tweet_id = url_parts.path.split("/")[-1]
else :
	tweet_id = args.id

if (tweet_id.isdecimal() is False) :
	print( "No valid Tweet ID found." )
	raise SystemExit

pretty_print = True if args.pretty else False

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

if (pretty_print) :
	twitter_json = json.dumps(data, indent=3)
else :
	twitter_json = json.dumps(data)

#   Save directory
output_directory = "output"
os.makedirs(output_directory, exist_ok = True)
save_location = os.path.join( output_directory, f"{tweet_id}.json" ) 

#   Save as JSON
with open( save_location, 'w', encoding="utf-8" ) as json_file:
	json_file.write( twitter_json )
print( f"Saved to {save_location}" )