import tweepy
from babel.dates import format_date

from base_data_app.models.data import Data
from base_data_app.models.language import Language
from blockhaus101.settings import (
    TWITTER_ACCESS_TOKEN,
    TWITTER_ACCESS_TOKEN_SECRET,
    TWITTER_CONSUMER_KEY,
    TWITTER_CONSUMER_SECRET,
    logger,
)
from blockhaus101_app.helpers import correct_text, replace_text
from blockhaus101_app.models import Artist, Exhibition, ExhibitionTitle


def generate_tweet(lang: str, artist: Artist, exhibition: Exhibition, tweet_type: str) -> str:
    if tweet_type == "tweets1":
        logger.info("Generate tweet of type 1")
    elif tweet_type == "tweets2":
        logger.info("Generate tweet of type 2")
    else:
        logger.error("Unknown tweet type")
        raise ValueError("Invalid tweet type")
    language = Language.objects.get(code=lang)
    tweet_structure = Data.choose_random(data_type=tweet_type, lang=lang)
    if not tweet_structure:
        raise ValueError(
            f"Could not find a random tweet structure for type '{tweet_type}' in language '{lang}'"
        )
    tweet = tweet_structure.text
    tweet = tweet.replace("[SELF]", artist.name)
    tweet = tweet.replace("[SELFDISCIPLINE]", artist.get_discipline(lang=lang))
    tweet = tweet.replace(
        "[EXPO]", ExhibitionTitle.objects.get(language=language, exhibition=exhibition).text
    )
    if "[EXPOSTARTDATE]" in tweet and exhibition.startdate:
        expo_startdate: str = format_date(exhibition.startdate.date(), format="medium", locale=lang)
        tweet = tweet.replace("[EXPOSTARTDATE]", expo_startdate)
    if "[EXPOENDDATE]" in tweet and exhibition.enddate:
        expo_enddate: str = format_date(exhibition.enddate.date(), format="medium", locale=lang)
        tweet = tweet.replace("[EXPOENDDATE]", expo_enddate)
    tweet, _used_words = replace_text(tweet, lang)
    return correct_text(text=tweet, lang=lang)


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
        except tweepy.TweepyException as e:
            logger.error(
                f'Error while trying to send tweet to "{twitter_account_name}" account: {e}'
            )
    except tweepy.TweepyException as e:
        logger.error(f"Error while connecting to Twitter account: {e}")
