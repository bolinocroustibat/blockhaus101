"""Copy one PostgreSQL database over the other.

The source database is dumped first and restored into a temporary database.
The destination database is renamed aside only after that restore succeeds,
then replaced. A failed dump or restore leaves the destination database in place.
"""

import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, BinaryIO, Protocol
from urllib.parse import parse_qsl, unquote, urlparse

import niquests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import connections

from blockhaus101.settings import logger
from blockhaus101_app.models import Exhibition

REMOTE_SITE_URL = "https://www.blockhaus101.com"

_DB_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")
_RESERVED_DATABASES = frozenset({"postgres", "template0", "template1"})
_SUPPORTED_QUERY = frozenset({"sslmode"})
_PG_TOOLS = ("pg_dump", "pg_restore", "psql")


class SyncRefused(Exception):
    """Raised when a remote-to-local copy must not run."""


class PgCommandFailed(Exception):
    """Raised when pg_dump, pg_restore, or psql fails."""

    def __init__(self, message: str, *, local_unchanged: bool = True) -> None:
        super().__init__(message)
        self.local_unchanged = local_unchanged


@dataclass(frozen=True)
class DatabaseTarget:
    user: str
    password: str
    host: str
    port: int
    name: str
    query: tuple[tuple[str, str], ...] = ()

    def label(self) -> str:
        return f"{self.user}@{self.host}:{self.port}/{self.name}"

    def same_database_as(self, other: "DatabaseTarget") -> bool:
        return (
            _canonical_host(self.host) == _canonical_host(other.host)
            and self.port == other.port
            and self.name == other.name
        )


class PgRunner(Protocol):
    def __call__(
        self,
        tool: str,
        args: list[str],
        target: DatabaseTarget,
        *,
        stdin: BinaryIO | None = None,
        stdout: BinaryIO | None = None,
    ) -> str: ...


@dataclass(frozen=True)
class PgInvocation:
    argv: list[str]
    env: dict[str, str]


def parse_database_url(url: str) -> DatabaseTarget:
    """Parse a postgres URL. The password is kept for the client tools and never logged."""
    parsed = urlparse(url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise SyncRefused("Database URL must start with postgres:// or postgresql://.")
    if not parsed.hostname:
        raise SyncRefused("Database URL must include a host.")
    name = unquote(parsed.path.lstrip("/").rstrip("/"))
    if not name:
        raise SyncRefused("Database URL must include a database name.")
    if _DB_NAME.fullmatch(name) is None:
        raise SyncRefused(f"Database name {name!r} must be a plain PostgreSQL identifier.")
    user = unquote(parsed.username or "")
    if not user or any(character.isspace() for character in user):
        raise SyncRefused("Database URL must include a user.")
    password = unquote(parsed.password or "")
    if any(character in password for character in "\r\n\x00"):
        raise SyncRefused("Database password contains a character that cannot be passed safely.")
    try:
        port = parsed.port or 5432
    except ValueError as exc:
        raise SyncRefused("Database URL has an invalid port.") from exc
    if not 1 <= port <= 65535:
        raise SyncRefused("Database URL has an invalid port.")

    query: list[tuple[str, str]] = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if key not in _SUPPORTED_QUERY:
            raise SyncRefused(
                f"Database URL query parameter {key!r} is not supported. Only sslmode is kept."
            )
        query.append((key, value))

    return DatabaseTarget(
        user=user,
        password=password,
        host=parsed.hostname,
        port=port,
        name=name,
        query=tuple(query),
    )


def assert_sync_is_safe(
    source: DatabaseTarget, destination: DatabaseTarget, environment: str
) -> None:
    """Refuse to run outside the local environment or to copy a database onto itself."""
    if environment != "local":
        raise SyncRefused(
            "Refusing to replace a database when ENVIRONMENT is "
            f"{environment!r}. Set ENVIRONMENT=local to run this on your machine."
        )
    if destination.name in _RESERVED_DATABASES:
        raise SyncRefused("Refusing to replace a PostgreSQL maintenance database.")
    if source.same_database_as(destination):
        raise SyncRefused("REMOTE_DATABASE_URL and DATABASE_URL point at the same database.")
    _temporary_names(destination.name)


def load_sync_targets(
    source_url: str | None,
    destination_url: str | None,
    environment: str,
) -> tuple[DatabaseTarget, DatabaseTarget]:
    if not source_url:
        raise SyncRefused("Set REMOTE_DATABASE_URL in .env to the database to copy from.")
    if not destination_url:
        raise SyncRefused("Set DATABASE_URL in .env to the local database to replace.")
    source = parse_database_url(source_url)
    destination = parse_database_url(destination_url)
    assert_sync_is_safe(source, destination, environment)
    return source, destination


def require_pg_tools() -> None:
    missing = [tool for tool in _PG_TOOLS if shutil.which(tool) is None]
    if missing:
        raise SyncRefused(f"PostgreSQL client tools were not found: {', '.join(missing)}.")


def pg_invocation(tool: str, args: list[str], target: DatabaseTarget) -> PgInvocation:
    """Build a client-tool command. The password stays out of the argv."""
    env = os.environ.copy()
    env.update(_connection_env(target))
    return PgInvocation([tool, "--no-password", *args], env)


def run_pg_tool(
    tool: str,
    args: list[str],
    target: DatabaseTarget,
    *,
    stdin: BinaryIO | None = None,
    stdout: BinaryIO | None = None,
) -> str:
    invocation = pg_invocation(tool, args, target)
    result = subprocess.run(
        invocation.argv,
        env=invocation.env,
        stdin=stdin if stdin is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE if stdout is None else stdout,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        detail = _scrub(result.stderr, target.password).strip() or "no error output"
        raise PgCommandFailed(f"{tool} failed: {detail}")
    if stdout is not None:
        return ""
    return _scrub(result.stdout, target.password)


def replace_database(
    source: DatabaseTarget,
    destination: DatabaseTarget,
    run: PgRunner,
    *,
    environment: str,
    progress: Callable[[str], None] | None = None,
) -> str | None:
    """Dump the source database and swap it over the destination.

    Returns a warning when the old destination database could not be dropped
    after a successful swap. Raises PgCommandFailed without changing the
    destination database when the dump or restore fails.
    """
    assert_sync_is_safe(source, destination, environment)
    admin = _maintenance_target(destination)
    incoming_name, _previous_name = _temporary_names(destination.name)
    incoming = replace(destination, name=incoming_name)

    def say(message: str) -> None:
        if progress is not None:
            progress(message)

    say(f"Dumping {source.label()}.")
    with tempfile.TemporaryDirectory() as tmp:
        dump_path = Path(tmp) / "remote.dump"
        with dump_path.open("wb") as dump_file:
            # Omit --file. pg_dump treats "-f -" as a file named "-", not stdout.
            run(
                "pg_dump",
                ["--format=custom", "--no-owner", "--no-privileges"],
                source,
                stdout=dump_file,
            )
        say(f"Restoring into temporary database {incoming_name}.")
        try:
            _psql(admin, f"DROP DATABASE IF EXISTS {_sql_ident(incoming_name)}", run)
            _psql(
                admin,
                f"CREATE DATABASE {_sql_ident(incoming_name)} TEMPLATE template0 ENCODING 'UTF8'",
                run,
            )
            with dump_path.open("rb") as dump_file:
                run(
                    "pg_restore",
                    ["--no-owner", "--no-privileges", "--exit-on-error", "-d", incoming_name],
                    incoming,
                    stdin=dump_file,
                )
            say(f"Replacing {destination.label()}.")
            return _swap(destination, incoming_name, run)
        except PgCommandFailed as exc:
            if not exc.local_unchanged:
                raise
            try:
                _psql(admin, f"DROP DATABASE IF EXISTS {_sql_ident(incoming_name)}", run)
            except PgCommandFailed as drop_exc:
                raise PgCommandFailed(
                    f"{exc} The temporary database {incoming_name} is still present: {drop_exc}",
                    local_unchanged=False,
                ) from exc
            raise PgCommandFailed(f"{exc} The database was not changed.") from exc


def _swap(destination: DatabaseTarget, incoming_name: str, run: PgRunner) -> str | None:
    admin = _maintenance_target(destination)
    _incoming_name, previous_name = _temporary_names(destination.name)
    destination_ident = _sql_ident(destination.name)
    incoming_ident = _sql_ident(incoming_name)
    previous_ident = _sql_ident(previous_name)

    # A previous run can leave the old database under the previous name and the
    # live name missing. Do not drop that copy while trying again.
    if not _database_exists(admin, destination.name, run):
        raise PgCommandFailed(
            f"Database {destination.name} is already missing. "
            f"If the previous copy is still in {previous_name}, rename it back manually "
            "before running this again.",
            local_unchanged=True,
        )

    _psql(admin, _terminate_sql(destination.name), run)
    _psql(admin, f"DROP DATABASE IF EXISTS {previous_ident}", run)
    _psql(admin, f"ALTER DATABASE {destination_ident} RENAME TO {previous_ident}", run)
    try:
        _psql(admin, f"ALTER DATABASE {incoming_ident} RENAME TO {destination_ident}", run)
    except PgCommandFailed as exc:
        try:
            _psql(admin, _terminate_sql(previous_name), run)
            _psql(admin, f"ALTER DATABASE {previous_ident} RENAME TO {destination_ident}", run)
        except PgCommandFailed as rollback_exc:
            raise PgCommandFailed(
                "The database was renamed and could not be restored. "
                f"Old data is in {previous_name}. The new copy is in {incoming_name}. "
                f"{rollback_exc}",
                local_unchanged=False,
            ) from exc
        raise PgCommandFailed(str(exc), local_unchanged=True) from exc
    try:
        _psql(admin, f"DROP DATABASE {previous_ident}", run)
    except PgCommandFailed as exc:
        return (
            f"The database was replaced, but the previous copy {previous_name} "
            f"is still there. {exc}"
        )
    return None


def _psql(admin: DatabaseTarget, sql: str, run: PgRunner) -> str:
    return run("psql", ["-X", "-v", "ON_ERROR_STOP=1", "-q", "-tA", "-c", sql], admin)


def _database_exists(admin: DatabaseTarget, database_name: str, run: PgRunner) -> bool:
    sql = f"SELECT 1 FROM pg_database WHERE datname = {_sql_literal(database_name)}"
    return _psql(admin, sql, run).strip() == "1"


def _temporary_names(database_name: str) -> tuple[str, str]:
    incoming = f"{database_name}_incoming"
    previous = f"{database_name}_previous"
    for name in (database_name, incoming, previous):
        if _DB_NAME.fullmatch(name) is None:
            raise SyncRefused(
                f"Database name {database_name!r} is too long to stage a replacement."
            )
    return incoming, previous


def _maintenance_target(destination: DatabaseTarget) -> DatabaseTarget:
    return replace(destination, name="postgres")


def _terminate_sql(database_name: str) -> str:
    return (
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
        f"WHERE datname = {_sql_literal(database_name)} AND pid <> pg_backend_pid()"
    )


def _sql_ident(name: str) -> str:
    if _DB_NAME.fullmatch(name) is None:
        raise SyncRefused(f"Unsafe database name {name!r}.")
    return f'"{name}"'


def _sql_literal(value: str) -> str:
    if _DB_NAME.fullmatch(value) is None:
        raise SyncRefused(f"Unsafe database name {value!r}.")
    return f"'{value}'"


def _canonical_host(host: str) -> str:
    lowered = host.lower()
    # localhost and loopback are the same machine, whichever form the URL uses.
    if lowered in {"localhost", "127.0.0.1", "::1"}:
        return "localhost"
    return lowered


def _connection_env(target: DatabaseTarget) -> dict[str, str]:
    env = {
        "PGHOST": target.host,
        "PGPORT": str(target.port),
        "PGUSER": target.user,
        "PGPASSWORD": target.password,
        "PGDATABASE": target.name,
        "PGCONNECT_TIMEOUT": "30",
    }
    for key, value in target.query:
        if key == "sslmode":
            env["PGSSLMODE"] = value
    return env


@dataclass(frozen=True)
class ImageDownload:
    downloaded: int
    skipped: int
    failed: int


def exhibition_image_names() -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    exhibitions = Exhibition.objects.all().only("image1", "image2")
    for exhibition in exhibitions:
        for field_name in ("image1", "image2"):
            image = getattr(exhibition, field_name)
            if not image or not image.name or image.name in seen:
                continue
            seen.add(image.name)
            names.append(image.name)
    return names


def media_file_url(base_url: str, media_url: str, name: str) -> str:
    prefix = media_url if media_url.endswith("/") else f"{media_url}/"
    if not prefix.startswith("/"):
        prefix = f"/{prefix}"
    return f"{base_url.rstrip('/')}{prefix}{name.lstrip('/')}"


def fetch_url(url: str) -> bytes | None:
    try:
        response = niquests.get(url, timeout=60)
        response.raise_for_status()
    except niquests.RequestException as exc:
        logger.error("Could not download %s: %s", url, exc)
        return None
    content = response.content
    if not content:
        logger.error("Could not download %s: empty response", url)
        return None
    return content


def download_images(
    names: list[str],
    *,
    base_url: str,
    media_root: Path,
    media_url: str,
    fetch: Callable[[str], bytes | None],
) -> ImageDownload:
    """Save exhibition image files under the local media folder."""
    root = media_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    downloaded = 0
    skipped = 0
    failed = 0
    for name in names:
        destination = (root / name).resolve()
        if not destination.is_relative_to(root):
            logger.error("Refusing to save an image outside the media folder: %s", name)
            failed += 1
            continue
        if destination.is_file() and destination.stat().st_size > 0:
            skipped += 1
            continue
        content = fetch(media_file_url(base_url, media_url, name))
        if not content:
            failed += 1
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        downloaded += 1
    return ImageDownload(downloaded=downloaded, skipped=skipped, failed=failed)


def _scrub(data: bytes | str | None, secret: str) -> str:
    if data is None:
        text = ""
    elif isinstance(data, bytes):
        text = data.decode(errors="replace")
    else:
        text = data
    if secret:
        return text.replace(secret, "********")
    return text


class Command(BaseCommand):
    help = (
        "Replace one database with a copy of the other. "
        "By default, delete the DATABASE_URL database and copy REMOTE_DATABASE_URL onto it. "
        "Use --to-remote to delete the remote database instead. "
        "Runs only when ENVIRONMENT=local."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--to-remote",
            action="store_true",
            help="Delete the remote database and replace it with a copy of DATABASE_URL.",
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Skip typing the name of the database that will be deleted. Safety checks still apply.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        to_remote = bool(options["to_remote"])
        try:
            remote_url = os.getenv("REMOTE_DATABASE_URL")
            local_url = os.getenv("DATABASE_URL")
            if not remote_url:
                raise SyncRefused("Set REMOTE_DATABASE_URL in .env to the remote database.")
            if not local_url:
                raise SyncRefused("Set DATABASE_URL in .env to the local database.")
            if to_remote:
                source_url, destination_url = local_url, remote_url
            else:
                source_url, destination_url = remote_url, local_url
            source, destination = load_sync_targets(
                source_url,
                destination_url,
                settings.ENVIRONMENT,
            )
            require_pg_tools()
        except SyncRefused as exc:
            raise CommandError(str(exc)) from exc

        if to_remote:
            summary = (
                "This deletes the remote database and replaces it with a copy of the local one."
            )
            images_note = "Exhibition images are not copied to the remote server."
            deleted = "remote"
        else:
            summary = (
                "This deletes the local database and replaces it with a copy of the remote one."
            )
            images_note = f"Exhibition images will be downloaded from {REMOTE_SITE_URL}."
            deleted = "local"
        self.stdout.write(
            self.style.WARNING(
                f"\n{summary}\n"
                f"  From: {source.label()}\n"
                f"  Onto: {destination.label()}\n"
                f"{images_note}\n"
            )
        )
        if not options["yes"]:
            self._confirm(destination, deleted)

        logger.info("Replacing database %s with %s", destination.label(), source.label())
        connections.close_all()

        def run(
            tool: str,
            args: list[str],
            target: DatabaseTarget,
            *,
            stdin: BinaryIO | None = None,
            stdout: BinaryIO | None = None,
        ) -> str:
            return run_pg_tool(tool, args, target, stdin=stdin, stdout=stdout)

        def progress(message: str) -> None:
            self.stdout.write(message)

        try:
            warning = replace_database(
                source,
                destination,
                run,
                environment=settings.ENVIRONMENT,
                progress=progress,
            )
        except (SyncRefused, PgCommandFailed) as exc:
            logger.error("Could not copy the database: %s", exc)
            raise CommandError(str(exc)) from exc

        if warning:
            self.stdout.write(self.style.WARNING(warning))
        self.stdout.write(
            self.style.SUCCESS(f"{destination.label()} now matches {source.label()}.")
        )
        if to_remote:
            return
        self._download_images()

    def _download_images(self) -> None:
        self.stdout.write(f"Downloading exhibition images from {REMOTE_SITE_URL}.")
        try:
            result = download_images(
                exhibition_image_names(),
                base_url=REMOTE_SITE_URL,
                media_root=Path(settings.MEDIA_ROOT),
                media_url=settings.MEDIA_URL,
                fetch=fetch_url,
            )
        except OSError as exc:
            logger.error("Could not save exhibition images: %s", exc)
            self.stdout.write(
                self.style.WARNING(
                    f"The database was replaced, but exhibition images could not be saved: {exc}"
                )
            )
            return
        self.stdout.write(
            "Exhibition images: "
            f"{result.downloaded} downloaded, "
            f"{result.skipped} already present, "
            f"{result.failed} failed."
        )

    def _confirm(self, destination: DatabaseTarget, deleted: str) -> None:
        prompt = f'Type "{destination.name}" to replace the {deleted} database: '
        try:
            typed = input(prompt)
        except EOFError as exc:
            raise CommandError(
                "Refusing to replace the database without a confirmation. Pass --yes to proceed."
            ) from exc
        if typed != destination.name:
            raise CommandError("Confirmation did not match. The database was not changed.")
