# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

# For a sqlite database
#DATABASES = {
#	'default': {
#		'ENGINE': 'django.db.backends.sqlite3',
#		'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
#	}
#}

import pymysql
pymysql.install_as_MySQLdb()

DEBUG = True

DATABASES = {
	'default': {
		'ENGINE': 'django.db.backends.mysql', 
		'NAME': 'blockhaus101_django',
		'USER': 'root',
		'PASSWORD': 'root',
		'HOST': 'localhost',   # Or an IP Address that your DB is hosted on
		'PORT': '8889',
	}
}