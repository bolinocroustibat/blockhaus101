# Blockhaus 101 – Agent instructions

When editing this repo, suggesting code, or proposing commits, follow the conventions below.

## Project overview

Blockhaus 101 is an **AI-powered contemporary art exhibition generator**. It automatically creates and publishes weekly/monthly exhibitions of marginal contemporary art: AI generates exhibition content, artist biographies, promotional images, and social media content.

- **Stack**: Python 3.14 preferred, 3.12+ minimum (uv), Django 5.1+, PostgreSQL, Docker, HTMX. OpenAI for text, GetImgAI for images, Twitter API for posting, Sentry for monitoring.
- **Apps**: `blockhaus101_app` (exhibitions, artists, public views), `base_data_app` (translations, AI config), `blockhaus101` (settings).
- **Key config**: **`.env`** is the most important (all env vars: DB, API keys, etc.). It is gitignored so the LLM cannot read it. To know which env vars exist, read **`.env.example`**. Other config: `pyproject.toml`, `blockhaus101/settings.py`, `docker-compose.yml`.
- **Tests**: Unit tests in `blockhaus101_app/tests/`. Run after each modification with `uv run python manage.py test`. CI integration is planned (TODO).

## Conventions

- **Language**: Use **English** for all comments, docstrings, names (variables, functions, classes), and user-facing strings.
- **Python & packages**: Use **uv** only. Run: `uv run python ...`, `uv run python manage.py ...`. Add deps: `uv add <package>` or `uv add --dev <package>` — do **not** use `pip install` or `uv pip install`.
- **Commits**: Use **English** and **Conventional Commits** (e.g. `feat: add X`, `fix: Y`, `docs: Z`).
- **Type hints**: Use **systematic type hinting**. Use modern Python 3.10+ native types: `dict`, `list`, `tuple`, `str | None` — **not** `Dict`, `List`, `Tuple`, `Optional` from `typing`.
- **Lint & format**: After each code change, run:
  ```bash
  uv run ruff check --fix . && uv run ruff format .
  ```

## Code architecture

### Module organization

Models, views, and helpers are **split into one file per entity** inside subdirectories, re-exported via `__init__.py` (with `# ruff: noqa: F401`). When adding a new model/view/helper, **always add the import in the corresponding `__init__.py`**.

- Models: `blockhaus101_app/models/<model>.py` → `models/__init__.py`
- Views: `blockhaus101_app/views/<view>.py` → `views/__init__.py`
- Helpers: `blockhaus101_app/helpers/<helper>.py` → `helpers/__init__.py`
- Exception: tweet logic lives at `blockhaus101_app/tweet.py` (app root, not in helpers).

### Views

All views are **function-based** (no CBV). No authentication on public views. Admin at `/admin101/`.

### Language / i18n

Language is **NOT** handled via Django's i18n framework. Instead:
- Language code (`fr`|`en`) is a **URL parameter**: `/fr/`, `/en/`.
- Templates live in **language-specific directories**: `{lang}/base.html`, `{lang}/index.html`.
- Template paths built dynamically: `f"{lang}/template_name.html"`.
- Dates formatted with `babel.dates.format_date(date, locale=lang)`.

### HTMX pattern

- `request.htmx` (from `django_htmx` middleware) detects HTMX requests.
- Full page → `{lang}/page.html`; HTMX partial → `{lang}/partials/fragment.html`.

### Async/sync bridge

API clients (`AsyncOpenAI`, `httpx.AsyncClient`) are **async**, but all callers (views, models, commands) are **sync**. Always wrap with `asyncio.run()`:
```python
result = asyncio.run(api.some_async_method(...))
```
Never `await` directly in views, models, or management commands.

### Logging

Use the **singleton logger from settings** everywhere — not `logging.getLogger(__name__)`:
```python
from blockhaus101.settings import logger
```

### Settings subtleties

- **`USE_TZ = False`**: Naive datetimes; use `datetime.now()`, never `timezone.now()`.
- **`DEFAULT_AUTO_FIELD = "django.db.models.AutoField"`**: Integer PKs (not BigAutoField).
- **`OPENAI_MODEL`**: A dict with `id` and `pricing` keys, not a plain string.
- **`db_table`**: All models set explicit `db_table` prefixed `blockhaus101_`.
- **`on_delete`**: `CASCADE` for owned content, `PROTECT` for reference data (Language, Data), `SET_NULL` for optional links.

### Error handling

- `OpenAiAPI` methods return **tuples**: `(result_text, price, error_msg)` — all nullable.
- `GetImgAiAPI` methods return `dict | None` (`None` on failure).
- Errors are **logged but not raised** (resilient/silent approach). Sentry captures unhandled exceptions automatically via `DjangoIntegration`.
- No retry logic or rate limiting is currently implemented.

## Content generation pipeline

### How content is generated

1. **French-first**: All content (titles, bios, exhibition texts) is generated in French, then translated to other languages via OpenAI or `Data.translation` lookups.
2. **Template system**: `Data` entries contain `[KEYWORD]` placeholders (e.g. `[SELF]`, `[SELFDISCIPLINE]`, `[EXPO]`, `[SELFEXPO]`, `[EXPOSTARTDATE]`, `[EXPOENDDATE]`) replaced at generation time with random data from the DB.
3. **Position-based sentences**: Texts are assembled sentence by sentence. Each sentence is randomly drawn from `Data` entries filtered by `position` (1–6). Some positions are randomly included/excluded.
4. **Weighted random selection**: `Data.weight` (default 10) controls selection probability via `Data.choose_random()`.
5. **French grammar post-processing**: `correct_text()` handles elisions (`de le` → `du`), vowel contractions (`de a...` → `d'a...`), and gender agreement (`il` → `elle`, `né` → `née`).

### Model `generate()` / `save()` pattern

- **`model.generate()`** populates fields but does **NOT** save. The caller must call `save()` explicitly.
- **`Exhibition.save()`** auto-calculates `startdate`/`enddate` if not set (chains from last exhibition or falls back to `datetime.now()`).
- **`ExhibitionText.save()`** auto-generates a unique slug. **Silently skips saving** if too many collisions (max 10).
- No Django signals are used — all logic lives in model methods.

### Translation in `Data` model

`Data.translation` is a **self-referential FK** linking the same content across languages. To find a translation: look up `Data.objects.get(language__code=lang, translation=original_data)`.

### API wrappers

- **OpenAI**: `OpenAiAPI` class in `blockhaus101_app/helpers/api_openai.py`. Methods: `translate()`, `reformulate()`, `get_models_ids()`. All async.
- **GetImgAI**: `GetImgAiAPI` class in `blockhaus101_app/helpers/api_getimgai.py`. Main method: `stable_diffusion_xl()`. All async, 30s timeout.
- **Twitter**: `generate_tweet()` and `send_tweet()` in `blockhaus101_app/tweet.py`. Sync (tweepy).
- **Image generation**: `Exhibition.generate_image()` looks up discipline prompt from `GETIMGAPI_PROMPTS` dict, calls GetImgAI, decodes base64, saves as `ContentFile`.

### Management commands

Run with: `uv run python manage.py <command_name>`.

- `generate_exhibition` – full AI exhibition pipeline (artist + titles + bios + image + texts). Flags: `--img`, `--save`.
- `generate_expo_img` – generate image for a specific exhibition (`--id`).
- `generate_expo_imgs` – batch generate images for all exhibitions missing images.
- `generate_tweet` – generate/post social content (`--lang`, `--type tweets1|tweets2`).
- `reformulate_expo_text` – refine exhibition text via OpenAI (`--id`, `--save`).
- `get_openai_models` – list OpenAI models.
- `delete_exhibitions` – delete exhibitions after a given date (uses `transaction.atomic()`).
- `check_missing_images` – verify image files exist on disk.
- `import` – import base data from Google Sheets CSV.
- `generate_translations` (base_data_app) – translate Data entries via Google Translate.

### Practices

- Validate and sanitize generated content before saving.
- Use fallbacks for API failures (e.g. French text if translation fails).
- Prefer efficient prompts and caching to limit API cost.

## Deployment

- **ASGI**: Gunicorn + Uvicorn workers (not WSGI).
- **Docker**: `app` (Django), `db` (PostgreSQL), `cron` (scheduled tasks — same image, separate container).
- **Cron** (not Celery): Tweet generation scheduled via system cron in `cron/entrypoint.sh`.
- **CI/CD**: GitHub Actions on tag push → version bump → Docker build/push to GHCR → deploy via SSH → Sentry release.
