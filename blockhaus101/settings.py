import importlib.metadata
import logging
import os

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

from blockhaus101.captcha import custom_captcha_challenge

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)  # BASE_DIR is where your manage.py lies
SITE_ROOT = os.path.abspath(
    os.path.dirname(__file__)
)  # SITE_ROOT is BASE_DIR + your_project_name (where this settings.py is)

# Blockhaus specific - path to json cache
JSON_PATH = os.path.join(
    os.path.abspath(os.path.join(BASE_DIR, "blockhaus101_app", "json_data/")), ""
)

# where the static files will go when doing a collectstatic if debug=false
STATIC_ROOT = os.path.join(BASE_DIR, "static")
STATIC_URL = "/static/"

# TWEEPY
# The consumer keys can be found on your application's Details
# page located at https://dev.twitter.com/apps (under "OAuth settings")
TWITTER_CONSUMER_KEY = os.getenv("TWITTER_CONSUMER_KEY", "")
TWITTER_CONSUMER_SECRET = os.getenv("TWITTER_CONSUMER_SECRET", "")
# The access tokens can be found on your applications's Details
# page located at https://dev.twitter.com/apps (located
# under "Your access token")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN", "")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET", "")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")

# Django debug toolbar authorized IPs
INTERNAL_IPS = ("127.0.0.1",)

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "debug_toolbar",
    "base_data_app",
    "blockhaus101_app",
    "captcha",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

ROOT_URLCONF = "blockhaus101.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/
LANGUAGE_CODE = "en-EN"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_L10N = True
USE_TZ = False

MAIL_ERROR_MESSAGE = {
    "en": "An error occured while sending your message. Please try again later.",
    "fr": "Erreur lors de l'envoi du message. Veuillez nous contacter ultérieurement.",
}
MAIL_INVALID_MESSAGE = {
    "en": "Your message is invalid. Please check that all the fields are correctly filled.",
    "fr": "Votre demande n'a pas été envoyée, vérifiez que tous les champs ont été correctement remplis.",
}
MAIL_SUCCESS_MESSAGE = {
    "en": "Your message has been sent. Thank you!",
    "fr": "Votre demande a bien été envoyée. Nous vous tiendrons au courant dans les plus brefs délais.",
}

GENDER_CHOICES = (("f", "female"), ("m", "male"))

# Captcha
CAPTCHA_LETTER_ROTATION = 0
CAPTCHA_NOISE_FUNCTIONS: list = []
# CAPTCHA_CHALLENGE_FUNCT = "captcha.helpers.random_char_challenge"
CAPTCHA_CHALLENGE_FUNCT = custom_captcha_challenge

# A helpful rule of thumb is that one token generally corresponds to ~4 characters of text for common English text.  # noqa 501
# This translates to roughly ¾ of a word (so 100 tokens ~= 75 words).
# https://openai.com/pricing/
OPENAI_MODELS = [
    {
        "friendly-name": "GPT-4 Turbo 2024-04-09 (optimized for vision)",
        "model-name": "gpt-4-turbo-2024-04-09",
        "max-input-tokens": 128000,
        "max-output-tokens": 4096,
        "price_input_per_1M": 10,
        "price_output_per_1M": 30,
    },
    {
        "friendly-name": "GPT-4 Turbo 0125 preview",
        "model-name": "gpt-4-0125-preview",
        "max-input-tokens": 128000,
        "max-output-tokens": 4096,
        "price_input_per_1M": 10,
        "price_output_per_1M": 30,
    },
    {
        "friendly-name": "GPT-4 Turbo 1106 preview",
        "model-name": "gpt-4-1106-preview",
        "max-input-tokens": 128000,
        "max-output-tokens": 4096,
        "price_input_per_1M": 10,
        "price_output_per_1M": 30,
    },
    {
        "friendly-name": "GPT-4 0613",
        "model-name": "gpt-4",
        "max-input-tokens": 8192,
        "max-output-tokens": 8192,
        "price_input_per_1M": 30,
        "price_output_per_1M": 60,
    },  # https://community.openai.com/t/gpt-4-32k-vs-gpt-4-turbo-api-legal-advice-on-using/659991/7
    {
        "friendly-name": "GPT-4 32k",
        "model-name": "gpt-4-32k",
        "max-input-tokens": 32768,
        "max-output-tokens": 32768,
        "price_input_per_1M": 60,
        "price_output_per_1M": 120,
    },  # https://community.openai.com/t/gpt-4-32k-vs-gpt-4-turbo-api-legal-advice-on-using/659991/7
    {
        "friendly-name": "GPT-3.5 Turbo 0125",
        "model-name": "gpt-3.5-turbo-0125",
        "max-input-tokens": 16385,
        "max-output-tokens": 4096,
        "price_input_per_1M": 0.5,
        "price_output_per_1M": 1.5,
    },
    {
        "friendly-name": "GPT-3.5 Turbo Instruct",
        "model-name": "gpt-3.5-turbo-instruct",
        "max-input-tokens": 4096,
        "max-output-tokens": 4096,
        "price_input_per_1M": 1.5,
        "price_output_per_1M": 2,
    },
]
OPENAI_MODEL = "gpt-3.5-turbo-0125"
OPENAI_SYSTEM_PROMPT = "Bonjour, vous parlez français et vous pouvez reformuler un texte français en gradant son style et son sens, mais en l'étoffant légèrement."
OPENAI_USER_PROMPT = "Je souhaite que vous reformuliez ce texte en français en gardant son sens, ses informations exactes principales. Son style doit converser le style original, c'est à dire celui d'un texte artistique un peu prétentieux, mais il doit être légèrement étoffé et allonge, si possible autour de 50% plus long. Ne pas inclure dans votre réponse autre chose que le texte en lui-même. Voici le texte HTML à reformuler: « {html_text} »"


# Local settings
try:
    from .local_settings import *  # noqa
except Exception as e:
    print(e)
    print("Note: local_settings.py not present or non valid. Using default settings.")
    ENVIRONMENT = "unknown"
    LOGGING_LEVEL = "DEBUG"

logger = logging.getLogger("blockhaus101")


APP_NAME: str = importlib.metadata.metadata("blockhaus101")["name"]
VERSION: str = importlib.metadata.version(APP_NAME)


if ENVIRONMENT in ["staging", "production"]:
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN", ""),
        integrations=[DjangoIntegration()],
        release=f"{APP_NAME}@{VERSION}",
        environment=ENVIRONMENT,
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # We recommend adjusting this value in production.
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
        # If you wish to associate users to errors (assuming you are using
        # django.contrib.auth) you may enable sending PII data.
        send_default_pii=True,
    )
