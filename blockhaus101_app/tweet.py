import re

from babel.dates import format_date
import tweepy

from base_data_app.models import Data
from blockhaus101_app.helpers import correct_sentence
from blockhaus101_app.models import Artist, Exhibition
from blockhaus101.settings import (
    TWITTER_ACCESS_TOKEN,
    TWITTER_ACCESS_TOKEN_SECRET,
    TWITTER_CONSUMER_KEY,
    TWITTER_CONSUMER_SECRET,
    logger,
)


def generate_tweet(
    lang: str, artist: Artist, exhibition: Exhibition, tweet_type: str
) -> str:
    if tweet_type == "tweets1":
        logger.info("Generate tweet of type 1")
    elif tweet_type == "tweets2":
        logger.info("Generate tweet of type 2")
    else:
        logger.error("Unknown tweet type")
        raise ValueError("Invalid tweet type")
    tweet_structure = Data.choose_random(type=tweet_type, lang=lang)
    tweet = tweet_structure.text
    tweet = tweet.replace("[SELF]", artist.name)
    tweet = tweet.replace("[SELFDISCIPLINE]", artist.discipline.text)
    tweet = tweet.replace("[EXPO]", exhibition.title)
    if "[EXPOSTARTDATE]" in tweet:
        expo_startdate: str = format_date(
            exhibition.startdate, format="medium", locale=lang
        )
        tweet = tweet.replace("[EXPOSTARTDATE]", expo_startdate)
    if "[EXPOENDDATE]" in tweet:
        expo_enddate: str = format_date(
            exhibition.enddate, format="medium", locale=lang
        )
        tweet = tweet.replace("[EXPOENDDATE]", expo_enddate)
    keywords: list = re.findall(r"\[[^][]*]", tweet)
    used_words = dict()
    for k in keywords:
        word_type = k.replace("[", "").replace("]", "")
        chosen_data = Data.choose_random_excluding(type=word_type, lang=lang, excluding=used_words)
        if chosen_data:
            chosen_word = chosen_data[0]
            used_words = chosen_data[1]
            # only replace one occurence, we want the same keyword to be able to be replaced by another word
            tweet = tweet.replace(f"[{word_type}]", chosen_word, 1)
    return correct_sentence(lang=lang, sentence=tweet)


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
