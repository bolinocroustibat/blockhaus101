# Galerie Søren Bollinger

## 🖥️ Run locally

### ⚙️ Set up the Python environment

```bash
uv sync
```

### 🧹 Lint, format, type check

```bash
uv run ruff check --fix . && uv run ruff format .
uv run ty check
```

CI runs the same checks without rewriting files (`ruff check .`, `ruff format --check .`, `ty check`) on pushes to `main`, and again before a tag deploy.

### ✅ Tests

```bash
uv run python manage.py test
```

CI runs the test suite on those same pushes.

### 🔑 Set the env vars in a .env file

Copy the example file and fill in your own values:

```bash
cp .env.example .env
```

The site reads **`DATABASE_URL`**. **`POSTGRES_PORT`** is the host port Docker publishes for Postgres. Compose uses `5432` when `POSTGRES_PORT` is unset. `.env.example` sets `POSTGRES_PORT=5433` and a `DATABASE_URL` on that same port, so a copied `.env` stays clear of a Postgres already bound to `5432`. Keep the port in `DATABASE_URL` aligned with `POSTGRES_PORT`. For a remote database, point `DATABASE_URL` at that host (often via an SSH tunnel to `127.0.0.1` on your laptop).

When the app runs on the host, set **`MEDIA_ROOT`** to a writable folder. Uncomment `MEDIA_ROOT=media` in `.env`. In Docker the container keeps `/app/media`, so leave `MEDIA_ROOT` unset there.

You can get these values from:
- OpenAI API key: https://platform.openai.com/api-keys
- GetImgAI API key: https://getimg.ai/
- Twitter API keys: https://developer.twitter.com/en/portal/dashboard
- Sentry DSN: Your Sentry project settings

### Copy one database onto the other

`DATABASE_URL` is the local database. `REMOTE_DATABASE_URL` is the other one.

```bash
uv run python manage.py sync_remote_db
uv run python manage.py sync_remote_db --apply
uv run python manage.py sync_remote_db --to-remote
uv run python manage.py sync_remote_db --to-remote --apply
```

Without `--apply`, the command only prints the image copies and the exhibition image links that would change. `--apply` deletes the local database and replaces it with the remote one, then downloads exhibition images from the public site into the local media folder. `--to-remote --apply` uploads local exhibition images to the server, then deletes the remote database and replaces it with the local one. The database is left unchanged if the upload fails. Set `REMOTE_SSH` to `user@host` (your SSH keys are used) and `REMOTE_MEDIA_PATH` to the media folder on that server. It runs only when `ENVIRONMENT=local`. You will be asked to type the name of the database that will be deleted.

### ▶️ Run

Start Postgres, apply migrations, then start the site:

```bash
docker compose up -d db
uv run python manage.py migrate
uv run python manage.py runserver
```

## 🐳 Run with Docker

Use the same `.env` as for a local run (`cp .env.example .env`). Compose reads it and passes the variables into the app and cron containers. Leave `MEDIA_ROOT` unset.

Start the app, the database, and cron with:

```bash
docker compose up -d
```

Static files and exhibition images are mounted from `/home/www/blockhaus101/static` and `/home/www/blockhaus101/media`. Those paths are on the server. Inside Compose, the app and cron use `postgres://postgres:postgres@db:5432/blockhaus101_django`.

A git tag push deploys this stack. GitHub Actions builds the image, pushes it to `ghcr.io/bolinocroustibat/blockhaus101`, then on the server runs `docker compose pull`, `docker compose down`, and `docker compose up -d` in `/home/www/blockhaus101`. The app container migrates, collects static files, and serves with Gunicorn and one Uvicorn worker on port 8000. Cron posts the scheduled tweets.

## 📦 Archive: previous production setup

The notes below describe the earlier bare-metal setup (systemd, Gunicorn, Nginx). They are kept for reference.

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
