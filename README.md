# Blockhaus 101

## 🖥️ How to run locally

### ⚙️ Set up the Python environment

```bash
uv sync
```

### 🧹 Lint and format the code

```bash
uv run ruff check --fix . && uv run ruff format .
```

### 🔑 Set the env vars in a .env file

Create a `.env` file in the root directory with the following variables:

```bash
# App settings
ENVIRONMENT=local
APP_PORT=8000
POSTGRES_PORT=5433

# Django core settings
DEBUG=False
DJANGO_SECRET_KEY="your-secret-key-here"
ALLOWED_HOSTS=*

# Database settings
POSTGRES_DB=blockhaus101_django
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Email settings
EMAIL_HOST=your-smtp-host
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your-email-password

# External services
## OpenAI
OPENAI_API_KEY=your-openai-api-key

## GetImgAI
GETIMGAI_API_KEY=your-getimgai-api-key

## Twitter API
TWITTER_CONSUMER_KEY=your-twitter-consumer-key
TWITTER_CONSUMER_SECRET=your-twitter-consumer-secret
TWITTER_ACCESS_TOKEN=your-twitter-access-token
TWITTER_ACCESS_TOKEN_SECRET=your-twitter-access-token-secret

## Sentry
SENTRY_DSN=your-sentry-dsn
```

You can get these values from:
- OpenAI API key: https://platform.openai.com/api-keys
- GetImgAI API key: https://getimg.ai/
- Twitter API keys: https://developer.twitter.com/en/portal/dashboard
- Sentry DSN: Your Sentry project settings

### ▶️ Run

```bash
uv run python manage.py runserver
```

## 🐳 How to run with Docker

```bash
docker compose up -d
```

## 🚀 How to deploy on a server

### 🌐 Deploy on production as ASGI with Uvicorn

See `https://www.valentinog.com/blog/uvicorn-django/` for more info.


#### To run as async with ASGI with Uvicorn

```sh
gunicorn blockhaus101.asgi:application -k uvicorn.workers.UvicornWorker
```

For production, the number of workers `-w` should be adjusted based on the number of CPU cores.
For example, here with 20 cores, and adding a log file:
```sh
gunicorn blockhaus101.asgi:application -w 40 -k uvicorn.workers.UvicornWorker --log-file -
```


#### Systemd service to make Uvicorn peristent on production environment

File `/etc/systemd/system/blockhaus101.service`:
```
[Unit]
Description=blockhaus101 uvicorn daemon
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/home/www/blockhaus101-django
ExecStart=/home/blockhaus101/venv/bin/gunicorn blockhaus101.asgi:application -w 20 -k uvicorn.workers.UvicornWorker --log-file -

[Install]
WantedBy=multi-user.target
```
If the service file is changed, run `systemctl daemon-reload` to reload the changes.

To restart the service after any change in the service and/or project:
`systemctl restart blockhaus101`
...and reload Nginx with:
`systemctl reload nginx`


#### Nginx vhost content with proxy pass to Uvicorn

File `/etc/nginx/sites-available/blockhaus101.com`:

```
server {
	server_name blockhaus101.com;
	return 301 $scheme://www.blockhaus101.com$request_uri;

	listen 443 ssl http2; # managed by Certbot
	ssl_certificate /etc/letsencrypt/live/blockhaus101.com/fullchain.pem; # managed by Certbot
	ssl_certificate_key /etc/letsencrypt/live/blockhaus101.com/privkey.pem; # managed by Certbot
	include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
	ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot

}

upstream uvicorn {
	# Uvicorn/Gunicorn web server
	server 127.0.0.1:8000;
}

server {
	server_name www.blockhaus101.com;

	location /static/ {
		alias /home/www/blockhaus101-django/blockhaus101/static/;
	}

	location / {
		# Pass to Uvicorn/Gunicorn web server service
		proxy_pass http://uvicorn;
		proxy_set_header Host $host;
		proxy_set_header X-Real-IP $remote_addr;
		proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
		proxy_set_header X-Forwarded-Proto $scheme;
	}

	# HTTPS - auto added by Certbot
	listen 443 ssl http2; # managed by Certbot
	ssl_certificate /etc/letsencrypt/live/blockhaus101.com/fullchain.pem; # managed by Certbot
	ssl_certificate_key /etc/letsencrypt/live/blockhaus101.com/privkey.pem; # managed by Certbot
	include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
	ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot

}

server {
	if ($host = blockhaus101.com) {
		return 301 https://$host$request_uri;
	} # managed by Certbot

	server_name blockhaus101.com;
	listen 80;
	return 404; # managed by Certbot
}

server {
	if ($host = www.blockhaus101.com) {
		return 301 https://$host$request_uri;
	} # managed by Certbot

	server_name www.blockhaus101.com;
	listen 80;
	return 404; # managed by Certbot
}
```
