import logging
import os
import tomllib
from pathlib import Path

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

from blockhaus101.captcha import custom_captcha_challenge

# Define BASE_DIR as the directory containing the settings.py file
BASE_DIR = Path(__file__).resolve().parent.parent

# Define SITE_ROOT as the root directory of your project
SITE_ROOT = BASE_DIR.parent

# where the static files will go when doing a collectstatic if debug=false
STATIC_ROOT = BASE_DIR / "static"
STATIC_URL = "/static/"
# where the media (and notably the Blockhaus101 generated images) will go
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"

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
LANGUAGE_CODE = "fr-FR"
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

PERIOD = 7  # in days
LOCATIONS = [
    ("paris", "Paris"),
    ("copenhagen", "København"),
    ("austin", "Austin"),
    ("beijing", "Beijing"),
]

# A helpful rule of thumb is that one token generally corresponds to ~4 characters of text for common English text.  # noqa 501
# This translates to roughly ¾ of a word (so 100 tokens ~= 75 words).
# https://openai.com/pricing/
OPENAI_MODEL_ID = "gpt-4o-mini"

# Main prompt - focuses on what we want
GETIMGAPI_PROMPT = """Generate a photorealistic image of a contemporary art exhibition space. For {discipline}, show {specific_format} prominently displayed in the gallery. The exhibition name is "{exhibition_title}", so if possible the works can be vaguely related to that theme. Don't show any people, focus on the artwork(s) only."""

# Dictionary to map disciplines to their specific display formats
GETIMGAPI_FORMATS = {
    "photography": "large format photographs mounted on walls and freestanding displays",
    "plastic arts": "sculptural objects and three-dimensional artworks",
    "artistic installation": "site-specific installations with mixed media elements",
    "artistic performance": "performance art documentation through video screens and spatial arrangements",
    "abstract art": "non-representational artworks in various media",
    "algorithms": "digital displays and computer-generated visualizations",
    "video": "multiple video projections and screens of different sizes",
    "visual arts": "mixed media works combining different visual elements",
    "sculpture": "three-dimensional sculptures and spatial arrangements",
    "collages": "mixed-media collage works mounted on walls and in vitrines",
    "gif-art": "digital screens displaying animated artworks",
    "iconographic sampling": "remixed visual elements displayed through various media",
    "social network art": "digital displays showing social media-based artworks",
    "immersive experiences": "room-scale installations with interactive elements",
    "painting": "paintings mounted on gallery walls",
}

GETIMGAPI_NEGATIVE_PROMPT = """cartoon, anime, illustration, painting style, drawing, sketch, doodle, watercolor, oil painting effect, artificial looking, fake, low quality, blurry, noisy, oversaturated, overexposed, bad composition, distorted perspective, unrealistic shadows, text, watermarks, signatures, frames, borders, collage style, instagram filters, bad lighting, grainy"""

# Local settings
try:
    from .local_settings import *  # noqa
except Exception as e:
    print(e)
    print("Note: local_settings.py not present or non valid. Using default settings.")
    ENVIRONMENT = "unknown"
    LOGGING_LEVEL = "DEBUG"

logger = logging.getLogger("blockhaus101")

with open("pyproject.toml", "rb") as f:
    pyproject: dict = tomllib.load(f)
APP_NAME: str = pyproject["project"]["name"]
VERSION: str = pyproject["project"]["version"]
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
