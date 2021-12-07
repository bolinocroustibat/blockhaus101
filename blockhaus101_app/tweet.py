from random import choice
import re

import tweepy

from blockhaus101.settings import (
    logger,
    TWITTER_CONSUMER_KEY,
    TWITTER_CONSUMER_SECRET,
    TWITTER_ACCESS_TOKEN,
    TWITTER_ACCESS_TOKEN_SECRET,
)
from blockhaus101.settings import logger, correct_sentence
from blockhaus101_app.models import Artist, Exhibition, Data
from blockhaus101 import settings


def generate_tweet(artist: Artist, exhibition: Exhibition, tweet_type: str) -> str:
    if tweet_type == "tweet1":
        logger.info("Generate tweet of type 1")
        tweet_structures = Data.objects.filter(type__name="tweets1")
    elif tweet_type == "tweet2":
        logger.info("Generate tweet of type 2")
        tweet_structures = Data.objects.filter(type__name="tweets1")
    else:
        logger.error("Unknown tweet type")
        raise ValueError("Invalid tweet type")
    tweet = choice(tweet_structures).text
    tweet = tweet.replace("[SELF]", artist.name)
    tweet = tweet.replace("[SELFDISCIPLINE]", artist.discipline)
    tweet = tweet.replace("[EXPO]", exhibition.title)
    if "[EXPOSTARTDATE]" in tweet:
        expo_startdate: str = "{:%d %B}".format(exhibition.startdate)
        if expo_startdate[0] == "0":
            expo_startdate = expo_startdate[1:]
        tweet = tweet.replace("[EXPOSTARTDATE]", expo_startdate)
    if "[EXPOENDDATE]" in tweet:
        expo_enddate = "{:%d %B}".format(exhibition.enddate)
        if expo_enddate[0] == "0":
            expo_enddate = expo_enddate[1:]
        tweet = tweet.replace("[EXPOENDDATE]", expo_enddate)
    keywords: list = re.findall(r"\[[^][]*]", tweet)
    used_words = dict()
    for k in keywords:
        word_type = k.replace("[", "").replace("]", "")
        chosen_data = Data.choose_random(word_type=word_type, used_words=used_words)
        if chosen_data:
            chosen_word = chosen_data[0]
            used_words = chosen_data[1]
            # only replace one occurence, we want the same keyword to be able to be replaced by another word
            tweet = tweet.replace(f"[{word_type}]", chosen_word, 1)
    return correct_sentence(tweet)


def send_tweet(tweet: str) -> None:
    try:
        auth = tweepy.OAuthHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)
        auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET)
        api = tweepy.API(auth)
        # If the authentication was successful, you should see the name of the account print out
        twitter_account_name = api.me().name
        try:
            # If the application settings are set for "Read and Write" then this line should tweet out the message to your account's timeline. The "Read and Write" setting is on https://dev.twitter.com/apps
            api.update_status(status=tweet)
            logger.info(f'sent to Twitter account "{twitter_account_name}"')
        except Exception as e:
            logger.error(
                f'Error while trying to send tweet to "{twitter_account_name}" account: {e}'
            )
    except Exception as e:
        logger.error(f"Error while connecting to Twitter account: {e}")
