# # Auth logging for fail2ban
# authlogger = logging.getLogger('auth-logger')
# authlogger.setLevel(logging.WARN)
# handler = logging.handlers.RotatingFileHandler(
# 	'auth.log',
# 	maxBytes=500000,
# 	backupCount=5
# )
# authlogger.addHandler(handler)


def get_client_ip(request) -> str:
    """
    Given a Django request, send back the client IP as a string.
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip: str = x_forwarded_for.split(",")[-1].strip()
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip
