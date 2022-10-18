import os

import sentry_sdk
import toml
from sentry_sdk.integrations.django import DjangoIntegration

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
    "fr": "Erreur lors de l'envoi du message. Veuillez nous contacter ultérieurement."
}
MAIL_INVALID_MESSAGE = {
    "en": "Your message is invalid. Please check that all the fields are correctly filled.",
    "fr": "Votre demande n'a pas été envoyée, vérifiez que tous les champs ont été correctement remplis."
}
MAIL_SUCCESS_MESSAGE = {
    "en": "Your message has been sent. Thank you!",
    "fr": "Votre demande a bien été envoyée. Nous vous tiendrons au courant dans les plus brefs délais."
}

# Local settings
try:
    from .local_settings import *
except Exception as e:
    print(e)
    print("Note: local_settings.py not present or non valid. Using default settings.")
    ENVIRONMENT = "unknown"
    LOGGING_LEVEL = "DEBUG"

# # Logging
# LOGGING = {
#     "version": 1,
#     "disable_existing_loggers": False,
#     "formatters": {
#         "colored": {
#             "()": "coloredlogs.ColoredFormatter",
#             "format": "%(name)s %(levelname)s %(message)s",
#         },
#     },
#     "handlers": {
#         "console": {"class": "logging.StreamHandler", "formatter": "colored",},
#     },
#     "loggers": {
#         "django": {"handlers": ["console"], "level": "INFO", "propogate": False,},
#         "admin-auth-logger": {
#             "handlers": ["console"],
#             "level": "DEBUG",
#             "propogate": False,
#         },
#         "{}-auth".format(__name__): {
#             "handlers": ["console"],
#             "level": "DEBUG",
#             "propogate": False,
#         },
#         "blockhaus101": {
#             "handlers": ["console"],
#             "level": LOGGING_LEVEL,
#             "propogate": False,
#         },
#     },
# }
import logging

logger = logging.getLogger("blockhaus101")

pyproject: dict = toml.load("pyproject.toml")
APP_NAME: str = pyproject["tool"]["poetry"]["name"]
VERSION: str = pyproject["tool"]["poetry"]["version"]
if ENVIRONMENT in ["staging", "production"]:
    sentry_sdk.init(
        dsn="https://38a42a04381f4e0dbb2c1f4f2229bb69@o352691.ingest.sentry.io/4503999464865792",
        integrations=[
            DjangoIntegration(),
        ],
        release=f"{APP_NAME}@{VERSION}",
        environment=ENVIRONMENT,

        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # We recommend adjusting this value in production.
        traces_sample_rate=1.0,

        # If you wish to associate users to errors (assuming you are using
        # django.contrib.auth) you may enable sending PII data.
        send_default_pii=True
    )
