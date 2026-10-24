"""Copy one PostgreSQL database over the other.

The source database is dumped first and restored into a temporary database.
The destination database is renamed aside only after that restore succeeds,
then replaced. A failed dump or restore leaves the destination database in place.
"""

import csv
import io
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
_SSH_TARGET = re.compile(r"^[A-Za-z0-9._-]+@[A-Za-z0-9._-]+$")
_REMOTE_PATH = re.compile(r"^/[A-Za-z0-9._/-]+$")
_RESERVED_DATABASES = frozenset({"postgres", "template0", "template1"})
_SUPPORTED_QUERY = frozenset({"sslmode"})
_PG_TOOLS = ("pg_dump", "pg_restore", "psql")
_UPLOAD_TOOLS = ("ssh", "rsync")
_SSH_OPTIONS = ("-o", "BatchMode=yes", "-o", "ConnectTimeout=30")
_RSYNC_RSH = "ssh -o BatchMode=yes -o ConnectTimeout=30"
_REMOTE_SIZE_SCRIPT = """\
root=$1
shift
if [ ! -d "$root" ] || [ ! -r "$root" ] || [ ! -w "$root" ] || [ ! -x "$root" ]; then
  printf 'The media folder is not readable and writable: %s\\n' "$root" >&2
  exit 1
fi
for name in "$@"; do
  path="$root/$name"
  if [ -f "$path" ]; then
    if size=$(stat -c %s -- "$path" 2>/dev/null); then
      printf '%s\\n' "$size"
    else
      printf 'Could not read the size of %s\\n' "$path" >&2
      exit 1
    fi
  else
    printf '0\\n'
  fi
done
"""


class SyncRefused(Exception):
    """Raised when a remote-to-local copy must not run."""


class ImageSyncFailed(Exception):
    """Raised when exhibition images cannot be copied to the remote server."""


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


class TransferRunner(Protocol):
    def __call__(self, argv: list[str], stdin: bytes | None = None) -> str: ...


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


def exhibition_image_rows() -> list[tuple[int, str, str]]:
    """Return each exhibition id with its two image paths. Blank images are empty strings."""
    rows: list[tuple[int, str, str]] = []
    exhibitions = Exhibition.objects.all().only("id", "image1", "image2").order_by("id")
    for exhibition in exhibitions:
        exhibition_id = exhibition.pk
        if not isinstance(exhibition_id, int):
            continue
        image1 = exhibition.image1.name if exhibition.image1 else ""
        image2 = exhibition.image2.name if exhibition.image2 else ""
        rows.append((exhibition_id, image1 or "", image2 or ""))
    return rows


def image_names_from_rows(rows: list[tuple[int, str, str]]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for _exhibition_id, image1, image2 in rows:
        for name in (image1, image2):
            if not name or name in seen:
                continue
            seen.add(name)
            names.append(name)
    return names


def exhibition_image_names() -> list[str]:
    return image_names_from_rows(exhibition_image_rows())


_EXHIBITION_IMAGE_COPY = (
    "COPY (SELECT id, COALESCE(image1, ''), COALESCE(image2, '') "
    "FROM blockhaus101_exhibitions ORDER BY id) TO STDOUT WITH (FORMAT csv)"
)


def fetch_exhibition_images(target: DatabaseTarget, run: PgRunner) -> list[tuple[int, str, str]]:
    """Read exhibition image paths from a database without changing it."""
    output = run(
        "psql",
        ["-X", "-v", "ON_ERROR_STOP=1", "-q", "-c", _EXHIBITION_IMAGE_COPY],
        target,
    )
    return parse_exhibition_image_csv(output)


def parse_exhibition_image_csv(text: str) -> list[tuple[int, str, str]]:
    rows: list[tuple[int, str, str]] = []
    for record in csv.reader(io.StringIO(text)):
        if not record:
            continue
        if len(record) != 3 or not record[0].isdigit():
            raise PgCommandFailed("Could not read exhibition image links from the database.")
        rows.append((int(record[0]), record[1], record[2]))
    return rows


@dataclass(frozen=True)
class ImageLinkChange:
    exhibition_id: int
    field: str
    before: str
    after: str


@dataclass(frozen=True)
class ExhibitionImageDiff:
    changes: tuple[ImageLinkChange, ...]
    added: tuple[tuple[int, str, str], ...]
    removed: tuple[tuple[int, str, str], ...]


def diff_exhibition_images(
    incoming_rows: list[tuple[int, str, str]],
    current_rows: list[tuple[int, str, str]],
) -> ExhibitionImageDiff:
    """Compare image paths. Incoming rows are what the destination database would become."""
    incoming = {row[0]: row for row in incoming_rows}
    current = {row[0]: row for row in current_rows}
    changes: list[ImageLinkChange] = []
    for exhibition_id in sorted(set(incoming) & set(current)):
        _exhibition_id, incoming_1, incoming_2 = incoming[exhibition_id]
        _exhibition_id, current_1, current_2 = current[exhibition_id]
        if incoming_1 != current_1:
            changes.append(ImageLinkChange(exhibition_id, "image1", current_1, incoming_1))
        if incoming_2 != current_2:
            changes.append(ImageLinkChange(exhibition_id, "image2", current_2, incoming_2))
    added = tuple(incoming[exhibition_id] for exhibition_id in sorted(set(incoming) - set(current)))
    removed = tuple(
        current[exhibition_id] for exhibition_id in sorted(set(current) - set(incoming))
    )
    return ExhibitionImageDiff(tuple(changes), added, removed)


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


@dataclass(frozen=True)
class ImageUpload:
    uploaded: int
    skipped: int
    failed: int


@dataclass(frozen=True)
class ImageUploadPlan:
    to_upload: tuple[str, ...]
    already_remote: tuple[str, ...]
    missing_local: tuple[str, ...]
    refused: tuple[str, ...]


@dataclass(frozen=True)
class ImageDownloadPlan:
    to_download: tuple[str, ...]
    already_local: tuple[str, ...]
    refused: tuple[str, ...]


def load_remote_ssh_target(ssh_target: str | None) -> str:
    """Read the server that stores exhibition images."""
    target = (ssh_target or "").strip()
    if not target:
        raise SyncRefused(
            "Set REMOTE_SSH in .env to user@host for the server that stores exhibition images."
        )
    if _SSH_TARGET.fullmatch(target) is None:
        raise SyncRefused("REMOTE_SSH must look like user@host.")
    return target


def load_remote_media_path(remote_media: str | None) -> str:
    """Read the folder on the server that stores exhibition images."""
    folder = (remote_media or "").strip().rstrip("/")
    if not folder:
        raise SyncRefused(
            "Set REMOTE_MEDIA_PATH in .env to the absolute folder on the server "
            "that stores exhibition images."
        )
    if not _is_safe_remote_path(folder):
        raise SyncRefused("REMOTE_MEDIA_PATH must be an absolute path on the server.")
    return folder


def require_upload_tools() -> None:
    missing = [tool for tool in _UPLOAD_TOOLS if shutil.which(tool) is None]
    if missing:
        raise SyncRefused(
            "Tools required to upload exhibition images were not found: " + ", ".join(missing) + "."
        )


def plan_image_upload(
    names: list[str],
    *,
    media_root: Path,
    ssh_target: str,
    remote_media: str,
    run: TransferRunner,
) -> ImageUploadPlan:
    """Decide which exhibition images would be copied. This only reads remote file sizes."""
    root = media_root.resolve()
    missing_local: list[str] = []
    refused: list[str] = []
    present: list[str] = []
    for name in names:
        path = _local_image_path(root, name)
        if path is None:
            logger.error("Refusing to upload an image outside the media folder: %s", name)
            refused.append(name)
            continue
        if not path.is_file() or path.stat().st_size <= 0:
            logger.error("Exhibition image is missing locally: %s", name)
            missing_local.append(name)
            continue
        present.append(name)
    if not present:
        return ImageUploadPlan((), (), tuple(missing_local), tuple(refused))

    sizes = _remote_image_sizes(ssh_target, remote_media, present, run)
    to_upload: list[str] = []
    already_remote: list[str] = []
    for name, size in zip(present, sizes, strict=True):
        if size <= 0:
            to_upload.append(name)
        else:
            already_remote.append(name)
    return ImageUploadPlan(
        tuple(to_upload),
        tuple(already_remote),
        tuple(missing_local),
        tuple(refused),
    )


def upload_images(
    names: list[str],
    *,
    media_root: Path,
    ssh_target: str,
    remote_media: str,
    run: TransferRunner,
) -> ImageUpload:
    """Copy exhibition image files to the remote media folder.

    A file already stored on the server is left in place. The caller decides
    whether a missing local file should stop the database copy.
    """
    plan = plan_image_upload(
        names,
        media_root=media_root,
        ssh_target=ssh_target,
        remote_media=remote_media,
        run=run,
    )
    if plan.to_upload:
        run(
            _rsync_argv(media_root.resolve(), ssh_target, remote_media),
            stdin=("\n".join(plan.to_upload) + "\n").encode(),
        )
    return ImageUpload(
        uploaded=len(plan.to_upload),
        skipped=len(plan.already_remote),
        failed=len(plan.missing_local) + len(plan.refused),
    )


def plan_image_download(names: list[str], *, media_root: Path) -> ImageDownloadPlan:
    """Decide which exhibition images would be fetched. This does not download them."""
    root = media_root.resolve()
    to_download: list[str] = []
    already_local: list[str] = []
    refused: list[str] = []
    for name in names:
        path = _local_image_path(root, name)
        if path is None:
            logger.error("Refusing to save an image outside the media folder: %s", name)
            refused.append(name)
            continue
        if path.is_file() and path.stat().st_size > 0:
            already_local.append(name)
            continue
        to_download.append(name)
    return ImageDownloadPlan(tuple(to_download), tuple(already_local), tuple(refused))


def run_transfer(argv: list[str], stdin: bytes | None = None) -> str:
    result = subprocess.run(
        argv,
        input=stdin,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.decode(errors="replace").strip() or "no error output"
        raise ImageSyncFailed(f"{argv[0]} failed: {detail}")
    return result.stdout.decode(errors="replace")


def _is_safe_remote_path(path: str) -> bool:
    if path == "/" or _REMOTE_PATH.fullmatch(path) is None:
        return False
    return all(part not in {"", ".", ".."} for part in path.split("/")[1:])


def _is_safe_image_name(name: str) -> bool:
    """Allow generated filenames, including accented letters, and reject path tricks."""
    if not name or "\\" in name:
        return False
    if any(character.isspace() or ord(character) < 32 or character == "\x7f" for character in name):
        return False
    parts = name.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        return False
    return all(character.isalnum() or character in "._-" for character in name.replace("/", ""))


def _local_image_path(root: Path, name: str) -> Path | None:
    if not _is_safe_image_name(name):
        return None
    path = (root / name).resolve()
    if not path.is_relative_to(root):
        return None
    return path


def _remote_image_sizes(
    ssh_target: str,
    remote_media: str,
    names: list[str],
    run: TransferRunner,
) -> list[int]:
    stdout = run(
        ["ssh", *_SSH_OPTIONS, ssh_target, "bash", "-s", "--", remote_media, *names],
        stdin=_REMOTE_SIZE_SCRIPT.encode(),
    )
    lines = stdout.splitlines()
    if len(lines) != len(names) or any(not line.isdigit() for line in lines):
        raise ImageSyncFailed("Could not read the size of the exhibition images on the server.")
    return [int(line) for line in lines]


def _rsync_argv(media_root: Path, ssh_target: str, remote_media: str) -> list[str]:
    return [
        "rsync",
        "-rl",
        "--chmod=D755,F644",
        "--files-from=-",
        "-e",
        _RSYNC_RSH,
        f"{media_root}/",
        f"{ssh_target}:{remote_media}/",
    ]


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
        "By default, only print the image copies and image-link changes. "
        "Pass --apply to upload or download exhibition images and replace the database. "
        "Use --to-remote to copy the local database onto the remote one. "
        "Runs only when ENVIRONMENT=local."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--to-remote",
            action="store_true",
            help="Copy DATABASE_URL onto the remote database, instead of the other way around.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help=(
                "Replace the database and copy exhibition images. "
                "Without this flag, nothing is uploaded or deleted."
            ),
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
                ssh_target = load_remote_ssh_target(os.getenv("REMOTE_SSH"))
                remote_media = load_remote_media_path(os.getenv("REMOTE_MEDIA_PATH"))
                require_upload_tools()
            else:
                source_url, destination_url = remote_url, local_url
                ssh_target, remote_media = "", ""
            source, destination = load_sync_targets(
                source_url,
                destination_url,
                settings.ENVIRONMENT,
            )
            require_pg_tools()
        except SyncRefused as exc:
            raise CommandError(str(exc)) from exc

        dry_run = not bool(options["apply"])
        if to_remote:
            summary = (
                "This would delete the remote database and replace it with a copy of the local one."
                if dry_run
                else "This deletes the remote database and replaces it with a copy of the local one."
            )
            images_note = (
                "Exhibition images would be uploaded first to "
                f"{ssh_target}:{remote_media}. "
                "The remote database would be replaced only after that upload succeeded."
                if dry_run
                else "Exhibition images will be uploaded first to "
                f"{ssh_target}:{remote_media}. "
                "The remote database is replaced only after that upload succeeds."
            )
            deleted = "remote"
        else:
            summary = (
                "This would delete the local database and replace it with a copy of the remote one."
                if dry_run
                else "This deletes the local database and replaces it with a copy of the remote one."
            )
            images_note = (
                f"Exhibition images would be downloaded from {REMOTE_SITE_URL}."
                if dry_run
                else f"Exhibition images will be downloaded from {REMOTE_SITE_URL}."
            )
            deleted = "local"
        self.stdout.write(
            self.style.WARNING(
                f"\n{summary}\n"
                f"  From: {source.label()}\n"
                f"  Onto: {destination.label()}\n"
                f"{images_note}\n"
            )
        )
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "Dry run. Nothing will be uploaded or deleted. Pass --apply to do it."
                )
            )
        elif not options["yes"]:
            self._confirm(destination, deleted)

        def run(
            tool: str,
            args: list[str],
            target: DatabaseTarget,
            *,
            stdin: BinaryIO | None = None,
            stdout: BinaryIO | None = None,
        ) -> str:
            return run_pg_tool(tool, args, target, stdin=stdin, stdout=stdout)

        if dry_run:
            try:
                self._report_image_plan(
                    to_remote=to_remote,
                    source=source,
                    destination=destination,
                    ssh_target=ssh_target,
                    remote_media=remote_media,
                    run=run,
                )
            except PgCommandFailed as exc:
                logger.error("Could not read exhibition image links: %s", exc)
                raise CommandError(str(exc)) from exc
            return

        connections.close_all()

        def progress(message: str) -> None:
            self.stdout.write(message)

        if to_remote:
            self._upload_images(ssh_target, remote_media)

        logger.info("Replacing database %s with %s", destination.label(), source.label())
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

    def _report_image_plan(
        self,
        *,
        to_remote: bool,
        source: DatabaseTarget,
        destination: DatabaseTarget,
        ssh_target: str,
        remote_media: str,
        run: PgRunner,
    ) -> None:
        upload_blocked = False
        if to_remote:
            self.stdout.write("Reading local exhibition image links.")
            incoming_rows = exhibition_image_rows()
            self.stdout.write("Checking which exhibition images are already on the server.")
            try:
                upload_plan = plan_image_upload(
                    image_names_from_rows(incoming_rows),
                    media_root=Path(settings.MEDIA_ROOT),
                    ssh_target=ssh_target,
                    remote_media=remote_media,
                    run=run_transfer,
                )
            except (OSError, ImageSyncFailed) as exc:
                logger.error("Could not check exhibition images on the server: %s", exc)
                raise CommandError(
                    f"Could not check exhibition images on the server: {exc}"
                ) from exc
            upload_blocked = bool(upload_plan.missing_local or upload_plan.refused)
            self._write_upload_plan(upload_plan)
            self.stdout.write("Reading remote exhibition image links.")
            current_rows = fetch_exhibition_images(destination, run)
        else:
            self.stdout.write("Reading remote exhibition image links.")
            incoming_rows = fetch_exhibition_images(source, run)
            self.stdout.write("Reading local exhibition image links.")
            current_rows = exhibition_image_rows()
            download_plan = plan_image_download(
                image_names_from_rows(incoming_rows),
                media_root=Path(settings.MEDIA_ROOT),
            )
            self._write_download_plan(download_plan)

        diff = diff_exhibition_images(incoming_rows, current_rows)
        self._write_image_link_diff(diff)
        if upload_blocked:
            self.stdout.write(
                self.style.WARNING(
                    "The real run would stop before replacing the remote database, "
                    "because an exhibition image is missing locally or has an unsafe path."
                )
            )
            return
        if to_remote:
            self.stdout.write(
                "The real run would upload those files, then replace the whole remote database. "
                "Every table would be replaced, including these image links."
            )
            return
        self.stdout.write(
            "The real run would replace the whole local database, then download those files "
            f"from {REMOTE_SITE_URL}."
        )

    def _write_upload_plan(self, plan: ImageUploadPlan) -> None:
        blocked = len(plan.missing_local) + len(plan.refused)
        self.stdout.write(
            "Exhibition images: "
            f"{len(plan.to_upload)} would be uploaded, "
            f"{len(plan.already_remote)} already on the server, "
            f"{blocked} missing or refused locally."
        )
        self._write_names("Would upload", plan.to_upload)
        self._write_names("Missing locally", plan.missing_local)
        self._write_names("Refused", plan.refused)

    def _write_download_plan(self, plan: ImageDownloadPlan) -> None:
        self.stdout.write(
            "Exhibition images: "
            f"{len(plan.to_download)} would be downloaded, "
            f"{len(plan.already_local)} already present, "
            f"{len(plan.refused)} refused."
        )
        self._write_names("Would download", plan.to_download)
        self._write_names("Refused", plan.refused)

    def _write_image_link_diff(self, diff: ExhibitionImageDiff) -> None:
        self.stdout.write(
            "Exhibition image links: "
            f"{len(diff.changes)} would change, "
            f"{len(diff.added)} exhibitions would be added, "
            f"{len(diff.removed)} exhibitions would be removed."
        )
        for change in diff.changes:
            before = change.before or "(none)"
            after = change.after or "(none)"
            self.stdout.write(f"  {change.exhibition_id} {change.field}: {before} -> {after}")
        for exhibition_id, image1, image2 in diff.added:
            self.stdout.write(
                f"  add {exhibition_id}: image1={image1 or '(none)'} image2={image2 or '(none)'}"
            )
        for exhibition_id, image1, image2 in diff.removed:
            self.stdout.write(
                f"  remove {exhibition_id}: image1={image1 or '(none)'} image2={image2 or '(none)'}"
            )

    def _write_names(self, label: str, names: tuple[str, ...]) -> None:
        if not names:
            return
        self.stdout.write(f"{label}:")
        for name in names:
            self.stdout.write(f"  {name}")

    def _upload_images(self, ssh_target: str, remote_media: str) -> None:
        self.stdout.write(f"Uploading exhibition images to {ssh_target}:{remote_media}.")
        try:
            result = upload_images(
                exhibition_image_names(),
                media_root=Path(settings.MEDIA_ROOT),
                ssh_target=ssh_target,
                remote_media=remote_media,
                run=run_transfer,
            )
        except (OSError, ImageSyncFailed) as exc:
            logger.error("Could not upload exhibition images: %s", exc)
            raise CommandError(
                f"Exhibition images were not uploaded. The remote database was not changed: {exc}"
            ) from exc
        if result.failed:
            logger.error(
                "Exhibition image upload left %s file(s) missing locally",
                result.failed,
            )
            missing = (
                "1 exhibition image is missing locally"
                if result.failed == 1
                else f"{result.failed} exhibition images are missing locally"
            )
            raise CommandError(
                "The remote database was not changed: "
                f"{missing} "
                f"({result.uploaded} uploaded, {result.skipped} already on the server)."
            )
        self.stdout.write(
            "Exhibition images: "
            f"{result.uploaded} uploaded, "
            f"{result.skipped} already on the server."
        )

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
