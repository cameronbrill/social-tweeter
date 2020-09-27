from tweepy import Stream
from tweepy import OAuthHandler 
from tweepy.streaming import StreamListener
from tweepy import API
import requests
import pprint
from dotenv import load_dotenv
from firebase import firebase
import json
import os
load_dotenv()

#consumer key, consumer secret, access token, access secret.
ckey = os.getenv('API_KEY')
csecret=os.getenv('API_SECRET_KEY')
atoken=os.getenv('ACCESS_TOKEN')
asecret=os.getenv('TOKEN_SECRET')

# firebase database object
firebase = firebase.FirebaseApplication(os.getenv('FIREBASE_URL'), None)

# Twitter auth
auth = OAuthHandler(ckey, csecret)
auth.set_access_token(atoken, asecret)

# created_at : The time the status was posted.
# id : The ID of the status.
# id_str : The ID of the status as a string.
# text : The text of the status.
# entities : The parsed entities of the status such as hashtags, URLs etc.
# source : The source of the status.
# source_url : The URL of the source of the status.
# in_reply_to_status_id : The ID of the status being replied to.
# in_reply_to_status_id_str : The ID of the status being replied to in as a string.
# in_reply_to_user_id : The ID of the user being replied to.
# in_reply_to_user_id_str : The ID of the user being replied to as a string.
# in_reply_to_screen_name : The screen name of the user being replied to
# user : The User object of the poster of the status.
# geo : The geo object of the status.
# coordinates : The coordinates of the status.
# place : The place of the status.
# contributors : The contributors of the status.
# is_quote_status : Indicates whether the status is a quoted status or not.
# retweet_count : The number of retweets of the status.
# favorite_count : The number of likes of the status.
# favorited : Indicates whether the status has been favourited by the authenticated user or not.
# retweeted : Indicates whether the status has been retweeted by the authenticated user or not.
# possibly_sensitive : Indicates whether the status is sensitive or not.
# lang : The language of the status.


def getThread(status_id: int) -> None:
    tweet = twitterAPI.get_status(id=status_id, tweet_mode="extended")
    #Strip out the urls.

    if 'urls' in tweet.entities:
        for url in tweet.entities['urls']:
            if url["url"] in tweet.full_text:
                tweet.full_text=tweet.full_text.replace(url["url"], '')
    #Strip out the hashtags.
    if 'hashtags' in tweet.entities:
        for tag in tweet.entities['hashtags']:
            if "#"+tag["text"] in tweet.full_text:
                tweet.full_text=tweet.full_text.replace("#"+tag["text"], '')
    #Strip out the user mentions.
    if 'user_mentions' in tweet.entities:
        for men in tweet.entities['user_mentions']:
            if "@"+men["screen_name"] in tweet.full_text:
                tweet.full_text=tweet.full_text.replace("@"+men["screen_name"], '')
    #Strip out the media.
    if 'media' in tweet.entities:
        for med in tweet.entities['media']:
            if med["url"] in tweet.full_text:
                tweet.full_text=tweet.full_text.replace(med["url"], '')
    #Strip out the symbols.
    if 'symbols' in tweet.entities:
        for sym in tweet.entities['symbols']:
            if "$"+sym["text"] in tweet.full_text:
                tweet.full_text=tweet.full_text.replace("$"+sym["text"], '')

    url = os.getenv("AZURE_URL")
    querystring = {"subscription-key":os.getenv("SUBSCRIPTION_KEY"),"verbose":"true","show-all-intents":"true","log":"true","query":tweet.full_text}
    payload = ""
    headers = {
        'cache-control': "no-cache",
        'Postman-Token': os.getenv("POSTMAN_TOKEN")
        }
    response = requests.request("GET", url, data=payload, headers=headers, params=querystring)
    sentiment = json.loads(response.text)

    tweet = {
        "name": tweet.user.name,
        "user_id": tweet.user.id,
        "id":tweet.id,
        "text": tweet.full_text,
        "created_at": tweet.created_at,
        "in_reply_to_status_id": tweet.in_reply_to_status_id,
        "location": tweet.user.location,
        "suicidal-score": sentiment["prediction"]["intents"]["suicidal"]["score"],
        "top-intent": sentiment["prediction"]["topIntent"],
        "sentiment-score": sentiment["prediction"]["sentiment"]["score"]
        }
    firebase.post('/testing/tweets', tweet)
    firebase.post('/testing/user/'+str(tweet['user_id'])+'/tweets', tweet)
    if tweet["in_reply_to_status_id"]:
        getThread(tweet["in_reply_to_status_id"])

class CustomStreamListener(StreamListener):

    def on_data(self, data) -> bool:
        tweet = json.loads(data)
        #tweet = {
        #    "name": tweet["user"]["name"],
        #    "id":tweet["id"],
        #    "text": tweet["text"],
        #    "created_at": tweet["created_at"],
        #    "in_reply_to_status_id": tweet["in_reply_to_status_id"],
        #    "location": tweet["user"]["location"],
        #    "score": 0
        #    }
        #firebase.post('/testing/tweets', tweet)
        if tweet["in_reply_to_status_id"]:
            getThread(tweet["in_reply_to_status_id"])
        return(True)
    
    def on_error(self, status):
        print(status)

# Set up twitter api objects
twitterStream = Stream(auth=auth, listener=CustomStreamListener())
twitterAPI = API(auth)

twitterStream.filter(track=["ShellHacksHelp"])
