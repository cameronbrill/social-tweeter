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

def processTweet(tweet):
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
    return tweet

def get_score(tweet):
    url = os.getenv("AZURE_URL")
    querystring = {"subscription-key":os.getenv("SUBSCRIPTION_KEY"),"verbose":"true","show-all-intents":"true","log":"true","query":tweet.full_text}
    payload = ""
    headers = {
        'cache-control': "no-cache",
        'Postman-Token': os.getenv("POSTMAN_TOKEN")
        }
    response = requests.request("GET", url, data=payload, headers=headers, params=querystring)
    return response

def strip_tweet_info(tweet, sentiment):
    return {
        "name": tweet.user.name,
        "user_id": tweet.user.id,
        "id":tweet.id,
        "text": tweet.full_text,
        "created_at": tweet.created_at,
        "in_reply_to_status_id": tweet.in_reply_to_status_id,
        "location": tweet.user.location,
        "suicidal-score": sentiment["prediction"]["intents"]["suicidal"]["score"],
        "top-intent": sentiment["prediction"]["topIntent"],
        "sentiment-score": sentiment["prediction"]["sentiment"]["score"],
        "twitter_url": "https://twitter.com/"+tweet.user.screen_name,
        "profile_pic": tweet.user.profile_image_url_https
        }

def get_all_tweets(uid):
    tweets = twitterAPI.user_timeline(user_id=uid, tweet_mode="extended", count=20)
    uid = str(uid)
    for tweet in tweets:
        tweet = processTweet(tweet) 
        response = get_score(tweet)
        sentiment = json.loads(response.text)
        tweet = strip_tweet_info(tweet, sentiment)
        firebase.post('/testing/no/user/'+uid+"/tweets", tweet)
    user_score = 1
    temp = firebase.get('/testing/no/user/'+uid+'/tweets', None)
    temp = temp[list(temp.keys())[0]]
    worst_tweet = (temp["text"], temp["suicidal-score"])
    num_tweets = 1
    for tweet in firebase.get('/testing/no/user/'+uid+'/tweets', None):
        tweet = firebase.get('/testing/no/user/'+uid+'/tweets/'+tweet, None)
        print(tweet)
        num_tweets+=1
        user_score+=tweet["suicidal-score"]
        worst_tweet = (tweet["text"], tweet["suicidal-score"]) if tweet["suicidal-score"]>worst_tweet[1] else worst_tweet
    user_score /= num_tweets
    user = {
        "name": temp['name'],
        "score": user_score,
        "worst_tweet": worst_tweet,
        "twitter_url": temp["twitter_url"],
        "profile_pic": temp["profile_pic"],
        "user_id": temp["user_id"],
        "color": "rgb("+str(user_score*255)+","+str((1-user_score)*255)+",0)"
    }
    firebase.post('/testing/user/', user)
    pass

def getThread(status_id: int) -> None:
    tweet = twitterAPI.get_status(id=status_id, tweet_mode="extended")
    #Strip out the urls.
    tweet = processTweet(tweet)

    response = get_score(tweet)

    sentiment = json.loads(response.text)

    tweet = strip_tweet_info(tweet, sentiment)

    if not firebase.get("/testing/user/", None) or not str(tweet["user_id"]) in list(firebase.get("/testing/no/user/", None).keys()):
        get_all_tweets(tweet["user_id"])
    if tweet["in_reply_to_status_id"]:
        getThread(tweet["in_reply_to_status_id"])

class CustomStreamListener(StreamListener):

    def on_data(self, data) -> bool:
        tweet = json.loads(data)
        if tweet["in_reply_to_status_id"]:
            getThread(tweet["in_reply_to_status_id"])
        return(True)
    
    def on_error(self, status):
        print(status)


# Set up twitter api objects
twitterStream = Stream(auth=auth, listener=CustomStreamListener())
twitterAPI = API(auth)

twitterStream.filter(track=["ShellHacksHelp"])
