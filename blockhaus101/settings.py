import logging
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
TWITTER_CONSUMER_KEY = "NY2nHNNVMEMYarF3dnnVHmHnK"
TWITTER_CONSUMER_SECRET = "ID89Z7VOYc0SpSnRLc24iWCffbrrkU6yCdzSgCQfzhDVEuO4de"
# The access tokens can be found on your applications's Details
# page located at https://dev.twitter.com/apps (located
# under "Your access token")
TWITTER_ACCESS_TOKEN = "845743348908478466-7QcSj9koknxYAaOrGk03N9ix8xcmJs1"
TWITTER_ACCESS_TOKEN_SECRET = "6XdmNzhpJH5BzDQpknhC0romDuoFKyAqORT7mwJN8CpWd"

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "+%umqk%=)x=%_l3+++*a28wjom@99zeykg$1*z+1&u$v1=_pys"

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
    "django_htmx",
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
    "django_htmx.middleware.HtmxMiddleware",
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
OPENAI_MODEL = {
    "id": "gpt-4o-mini",
    "pricing": {
        "input_per_1M": 0.15,  # $0.15 per 1M input tokens
        "output_per_1M": 0.60,  # $0.60 per 1M output tokens
    },
}

# Img prompts to map disciplines to their specific display formats
GETIMGAPI_PROMPTS = {
    "photography": "Generate a photorealistic image of a photography exhibition space. Show large format photographs mounted on walls and freestanding displays. The theme of the photographs is {exhibition_title}, but don't use it if it is too abstract.",
    "plastic arts": "Generate a photorealistic image of a plastic arts exhibition space. Show sculptural objects and three-dimensional artworks. The theme of the artworks is {exhibition_title}, but don't use it if it is too abstract.",
    "artistic installation": "Generate a photorealistic image of an art installation exhibition space, with a spatial arrangement of a site-specific installation with mixed media elements. The theme of the installation is {exhibition_title}, but don't use it if it is too abstract.",
    "artistic performances": "Generate a photorealistic image of a a single {artist_gender} human (the performer) in a weird relaxing position surrounded by weird everyday objects, in a dedicated room with no other artworks, nothing on the walls. The theme of the performance is {exhibition_title}, but don't use it if it is too abstract.",
    "abstract art": "Generate a photorealistic image of an art exhibition space, with non-representational painting artworks spread on the walls. The theme of the artworks is {exhibition_title}, but don't use it if it is too abstract.",
    "algorithms": "Generate a photorealistic image of an art exhibition space with artworks of computer-generated visualizations. The theme of the artworks is {exhibition_title}, but don't use it if it is too abstract.",
    "video": "Generate a photorealistic image of a dedicated dark room with a single projection of an abstract or figurative video.",
    "visual arts": "Generate a photorealistic image of an art exhibition space with mixed media works combining different visual elements on diplay. The theme of the artworks is {exhibition_title}, but don't use it if it is too abstract.",
    "sculpture": "Generate a photorealistic image of a sculpture exhibition space with only three-dimensional sculptures and spatial arrangements. The theme of the artworks is {exhibition_title}, but don't use it if it is too abstract.",
    "collages": "Generate a photorealistic image of an art sculpture exhibition space with mixed-media collage works mounted on walls and in vitrines.",
    "gif-art": "Generate a photorealistic image of a exhibition space with digital screens displaying animated GIFs.",
    "iconographic sampling": "Generate a photorealistic image of an art exhibition space with remixed visual elements displayed through various media.",
    "social network art": "Generate a photorealistic image of an art exhibition space with artworks made with famous memes and typical social networks contents.",
    "immersive experiences": "Generate a photorealistic image of an art exhibition space with room-scale installations with interactive elements",
    "painting": "Generate a photorealistic image of an art exhibition space with paintings mounted on gallery walls.",
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
        dsn="https://38a42a04381f4e0dbb2c1f4f2229bb69@o352691.ingest.sentry.io/4503999464865792",
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
