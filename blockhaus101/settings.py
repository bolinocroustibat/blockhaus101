import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # BASE_DIR is where your manage.py lies
SITE_ROOT = os.path.abspath(os.path.dirname(__file__)) # SITE_ROOT is BASE_DIR + your_project_name (where this settings.py is)

# Blockhaus specific - path to json cache
JSON_PATH = os.path.join(os.path.abspath(os.path.join(BASE_DIR, 'blockhaus101_app', 'json_data/')), '')

# where the static files will go when doing a collectstatic if debug=false
STATIC_ROOT = os.path.join(SITE_ROOT, 'static')

# TWEEPY
# The consumer keys can be found on your application's Details
# page located at https://dev.twitter.com/apps (under "OAuth settings")
TWITTER_CONSUMER_KEY="NY2nHNNVMEMYarF3dnnVHmHnK"
TWITTER_CONSUMER_SECRET="ID89Z7VOYc0SpSnRLc24iWCffbrrkU6yCdzSgCQfzhDVEuO4de"
# The access tokens can be found on your applications's Details
# page located at https://dev.twitter.com/apps (located
# under "Your access token")
TWITTER_ACCESS_TOKEN="845743348908478466-7QcSj9koknxYAaOrGk03N9ix8xcmJs1"
TWITTER_ACCESS_TOKEN_SECRET="6XdmNzhpJH5BzDQpknhC0romDuoFKyAqORT7mwJN8CpWd"

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '+%umqk%=)x=%_l3+++*a28wjom@99zeykg$1*z+1&u$v1=_pys'

# Django debug toolbar authorized IPs
INTERNAL_IPS = ('127.0.0.1',)

# Application definition

INSTALLED_APPS = [
	'django.contrib.admin',
	'django.contrib.auth',
	'django.contrib.contenttypes',
	'django.contrib.sessions',
	'django.contrib.messages',
	'django.contrib.staticfiles',
	'solo',
	'debug_toolbar',
	'blockhaus101_app',
]

MIDDLEWARE = [
	'django.middleware.security.SecurityMiddleware',
	'django.contrib.sessions.middleware.SessionMiddleware',
	'django.middleware.common.CommonMiddleware',
	'django.middleware.csrf.CsrfViewMiddleware',
	'django.contrib.auth.middleware.AuthenticationMiddleware',
	'django.contrib.messages.middleware.MessageMiddleware',
	'django.middleware.clickjacking.XFrameOptionsMiddleware',
	'debug_toolbar.middleware.DebugToolbarMiddleware',
]

ROOT_URLCONF = 'blockhaus101.urls'

TEMPLATES = [
	{
		'BACKEND': 'django.template.backends.django.DjangoTemplates',
		'DIRS': [],
		'APP_DIRS': True,
		'OPTIONS': {
			'context_processors': [
				'django.template.context_processors.debug',
				'django.template.context_processors.request',
				'django.contrib.auth.context_processors.auth',
				'django.contrib.messages.context_processors.messages',
			],
		},
	},
]

WSGI_APPLICATION = 'blockhaus101.wsgi.application'


# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
	{
		'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
	},
	{
		'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
	},
	{
		'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
	},
	{
		'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
	},
]


# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = 'fr-FR'

TIME_ZONE = 'Europe/Paris'

USE_I18N = True

USE_L10N = True

USE_TZ = False

# Local settings
try:
	from .local_settings import *
except Exception:
	print('Note: local_settings.py not present. Using default settings.')
	LOGGING_LEVEL = 'DEBUG'

# Logging
LOGGING = {
	'version': 1,
	'disable_existing_loggers': False,
	'formatters': {
		'colored': {
			'()': 'coloredlogs.ColoredFormatter',
			'format': '%(name)s %(levelname)s %(message)s',
		},
	},
	'handlers': {
		'console': {
			'class': 'logging.StreamHandler',
			'formatter': 'colored',
		},
	},
	'loggers': {
		'django': {
			'handlers': ['console'],
			'level': 'INFO',
			'propogate': False,
		},
		'admin-auth-logger': {
			'handlers': ['console'],
			'level': 'DEBUG',
			'propogate': False,
		},
		'{}-auth'.format(__name__): {
			'handlers': ['console'],
			'level': 'DEBUG',
			'propogate': False,
		},
		'blockhaus101': {
			'handlers': ['console'],
			'level': LOGGING_LEVEL,
			'propogate': False
		}
	}
}
