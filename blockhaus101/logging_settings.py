from .settings import LOGGING_LEVEL

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