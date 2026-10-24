"""Safety checks for copying a remote database over the local one.

These tests never open a database connection. The copy itself is scripted.
"""

import os
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import BinaryIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from blockhaus101_app.management.commands.sync_remote_db import (
    DEFAULT_REMOTE_MEDIA,
    DatabaseTarget,
    ImageSyncFailed,
    ImageUpload,
    PgCommandFailed,
    SyncRefused,
    assert_sync_is_safe,
    download_images,
    load_remote_media_target,
    load_sync_targets,
    media_file_url,
    parse_database_url,
    pg_invocation,
    replace_database,
    require_pg_tools,
    require_upload_tools,
    run_pg_tool,
    upload_images,
)

LOCAL_URL = "postgres://postgres:secret@127.0.0.1:5433/blockhaus101_django"
REMOTE_URL = "postgres://postgres:secret@192.0.2.10:5432/blockhaus101_django"
LOCAL_NAME = "blockhaus101_django"


class RecordingRunner:
    def __init__(
        self,
        *,
        fail_sql: str | None = None,
        fail_tool: str | None = None,
        destination_exists: bool = True,
    ) -> None:
        self.calls: list[tuple[str, str, str, str]] = []
        self.dump_args: list[str] = []
        self.restored = b""
        self.fail_sql = fail_sql
        self.fail_tool = fail_tool
        self.destination_exists = destination_exists

    def __call__(
        self,
        tool: str,
        args: list[str],
        target: DatabaseTarget,
        *,
        stdin: BinaryIO | None = None,
        stdout: BinaryIO | None = None,
    ) -> str:
        sql = args[-1] if tool == "psql" else ""
        self.calls.append((tool, target.host, target.name, sql))
        if tool == "pg_dump":
            self.dump_args = args
        if sql == f"SELECT 1 FROM pg_database WHERE datname = '{LOCAL_NAME}'":
            return "1" if self.destination_exists else ""
        if self.fail_tool is not None and tool == self.fail_tool:
            raise PgCommandFailed(f"{tool} failed")
        if self.fail_sql is not None and sql == self.fail_sql:
            raise PgCommandFailed(f"failed: {sql}")
        if stdout is not None:
            stdout.write(b"PGDMP")
        if stdin is not None:
            self.restored = stdin.read()
        return ""


class TestParseDatabaseUrl(SimpleTestCase):
    def test_reads_a_postgres_url(self) -> None:
        target = parse_database_url(
            "postgresql://owner:p%40ss@DB.Example.com:5434/blockhaus101_django?sslmode=require"
        )

        self.assertEqual(target.user, "owner")
        self.assertEqual(target.password, "p@ss")
        self.assertEqual(target.host, "db.example.com")
        self.assertEqual(target.port, 5434)
        self.assertEqual(target.name, LOCAL_NAME)
        self.assertEqual(target.query, (("sslmode", "require"),))
        self.assertEqual(target.label(), f"owner@db.example.com:5434/{LOCAL_NAME}")

    def test_defaults_the_port_to_5432(self) -> None:
        target = parse_database_url("postgres://postgres:secret@127.0.0.1/blockhaus101_django")

        self.assertEqual(target.port, 5432)

    def test_rejects_a_non_postgres_url(self) -> None:
        with self.assertRaisesMessage(SyncRefused, "postgres://"):
            parse_database_url("mysql://postgres:secret@127.0.0.1/blockhaus101_django")

    def test_rejects_a_missing_database_name(self) -> None:
        with self.assertRaisesMessage(SyncRefused, "database name"):
            parse_database_url("postgres://postgres:secret@127.0.0.1")

    def test_rejects_an_unsafe_database_name(self) -> None:
        with self.assertRaisesMessage(SyncRefused, "identifier"):
            parse_database_url("postgres://postgres:secret@127.0.0.1:5432/blockhaus;drop")

    def test_rejects_an_invalid_port(self) -> None:
        with self.assertRaisesMessage(SyncRefused, "port"):
            parse_database_url("postgres://postgres:secret@127.0.0.1:99999/blockhaus101_django")

    def test_rejects_an_unknown_query_parameter(self) -> None:
        with self.assertRaisesMessage(SyncRefused, "sslrootcert"):
            parse_database_url(f"{LOCAL_URL}?sslrootcert=ca.pem")


class TestSyncSafety(SimpleTestCase):
    def test_copies_onto_the_database_url(self) -> None:
        source, destination = load_sync_targets(
            REMOTE_URL,
            "postgres://postgres:secret@db.example.com:5432/blockhaus101_django",
            "local",
        )

        self.assertEqual(source.host, "192.0.2.10")
        self.assertEqual(destination.host, "db.example.com")

    def test_allows_an_ssh_tunnel_on_another_local_port(self) -> None:
        source = parse_database_url("postgres://postgres:secret@127.0.0.1:5434/blockhaus101_django")
        destination = parse_database_url(LOCAL_URL)

        assert_sync_is_safe(source, destination, "local")

    def test_treats_localhost_and_loopback_as_the_same_database(self) -> None:
        source = parse_database_url("postgres://postgres:other@localhost:5433/blockhaus101_django")
        destination = parse_database_url(LOCAL_URL)

        with self.assertRaisesMessage(SyncRefused, "DATABASE_URL"):
            assert_sync_is_safe(source, destination, "local")

    def test_refuses_production_and_an_unset_environment(self) -> None:
        for environment in ("production", "staging", "unknown"):
            with self.assertRaisesMessage(SyncRefused, "ENVIRONMENT"):
                load_sync_targets(REMOTE_URL, LOCAL_URL, environment)

    def test_refuses_a_maintenance_database(self) -> None:
        destination = parse_database_url("postgres://postgres:secret@127.0.0.1:5432/postgres")

        with self.assertRaisesMessage(SyncRefused, "maintenance"):
            assert_sync_is_safe(parse_database_url(REMOTE_URL), destination, "local")

    def test_refuses_a_name_too_long_to_stage(self) -> None:
        name = "a" * 55
        destination = parse_database_url(f"postgres://postgres:secret@127.0.0.1:5432/{name}")

        with self.assertRaisesMessage(SyncRefused, "too long"):
            assert_sync_is_safe(parse_database_url(REMOTE_URL), destination, "local")

    def test_requires_the_remote_url(self) -> None:
        with self.assertRaisesMessage(SyncRefused, "REMOTE_DATABASE_URL"):
            load_sync_targets(None, LOCAL_URL, "local")


class TestReplaceLocalWithRemote(SimpleTestCase):
    def test_dumps_before_it_touches_the_local_database(self) -> None:
        source, destination = load_sync_targets(REMOTE_URL, LOCAL_URL, "local")
        runner = RecordingRunner()

        warning = replace_database(source, destination, runner, environment="local")

        self.assertIsNone(warning)
        self.assertEqual(runner.restored, b"PGDMP")
        tools = [call[0] for call in runner.calls]
        self.assertEqual(tools[0], "pg_dump")
        self.assertNotIn("-f", runner.dump_args)
        self.assertEqual(runner.calls[0][1:], ("192.0.2.10", LOCAL_NAME, ""))
        sqls = [call[3] for call in runner.calls if call[0] == "psql"]
        self.assertEqual(runner.calls[1][2], "postgres")
        self.assertIn('DROP DATABASE IF EXISTS "blockhaus101_django_incoming"', sqls[0])
        self.assertIn("CREATE DATABASE", sqls[1])
        self.assertEqual(tools[3], "pg_restore")
        self.assertEqual(runner.calls[3][1:], ("127.0.0.1", "blockhaus101_django_incoming", ""))
        self.assertIn(f"datname = '{LOCAL_NAME}'", sqls[2])
        self.assertIn("pg_terminate_backend", sqls[3])
        self.assertIn('RENAME TO "blockhaus101_django_previous"', sqls[5])
        self.assertIn(
            'ALTER DATABASE "blockhaus101_django_incoming" RENAME TO "blockhaus101_django"',
            sqls[6],
        )
        self.assertEqual(sqls[7], 'DROP DATABASE "blockhaus101_django_previous"')

    def test_a_failed_dump_does_not_touch_the_local_database(self) -> None:
        source, destination = load_sync_targets(REMOTE_URL, LOCAL_URL, "local")
        runner = RecordingRunner(fail_tool="pg_dump")

        with self.assertRaisesMessage(PgCommandFailed, "pg_dump failed"):
            replace_database(source, destination, runner, environment="local")

        self.assertEqual([call[0] for call in runner.calls], ["pg_dump"])

    def test_a_failed_restore_drops_the_temporary_database(self) -> None:
        source, destination = load_sync_targets(REMOTE_URL, LOCAL_URL, "local")
        runner = RecordingRunner(fail_tool="pg_restore")

        with self.assertRaisesMessage(PgCommandFailed, "was not changed"):
            replace_database(source, destination, runner, environment="local")

        sqls = [call[3] for call in runner.calls if call[0] == "psql"]
        self.assertTrue(all("RENAME TO" not in sql for sql in sqls))
        self.assertIn('DROP DATABASE IF EXISTS "blockhaus101_django_incoming"', sqls[-1])

    def test_a_failed_swap_renames_the_local_database_back(self) -> None:
        source, destination = load_sync_targets(REMOTE_URL, LOCAL_URL, "local")
        runner = RecordingRunner(
            fail_sql=(
                'ALTER DATABASE "blockhaus101_django_incoming" RENAME TO "blockhaus101_django"'
            )
        )

        with self.assertRaisesMessage(PgCommandFailed, "was not changed"):
            replace_database(source, destination, runner, environment="local")

        sqls = [call[3] for call in runner.calls if call[0] == "psql"]
        self.assertIn(
            'ALTER DATABASE "blockhaus101_django_previous" RENAME TO "blockhaus101_django"',
            sqls,
        )

    def test_stops_when_the_local_database_is_already_missing(self) -> None:
        source, destination = load_sync_targets(REMOTE_URL, LOCAL_URL, "local")
        runner = RecordingRunner(destination_exists=False)

        with self.assertRaisesMessage(PgCommandFailed, "already missing"):
            replace_database(source, destination, runner, environment="local")

        sqls = [call[3] for call in runner.calls if call[0] == "psql"]
        self.assertFalse(any("blockhaus101_django_previous" in sql for sql in sqls))

    def test_reports_when_the_rollback_itself_fails(self) -> None:
        source, destination = load_sync_targets(REMOTE_URL, LOCAL_URL, "local")
        incoming_rename = (
            'ALTER DATABASE "blockhaus101_django_incoming" RENAME TO "blockhaus101_django"'
        )
        rollback_rename = (
            'ALTER DATABASE "blockhaus101_django_previous" RENAME TO "blockhaus101_django"'
        )

        class BrokenRollback(RecordingRunner):
            def __call__(
                self,
                tool: str,
                args: list[str],
                target: DatabaseTarget,
                *,
                stdin: BinaryIO | None = None,
                stdout: BinaryIO | None = None,
            ) -> str:
                sql = args[-1] if tool == "psql" else ""
                if sql in {incoming_rename, rollback_rename}:
                    self.calls.append((tool, target.host, target.name, sql))
                    raise PgCommandFailed("rename failed")
                return super().__call__(tool, args, target, stdin=stdin, stdout=stdout)

        runner = BrokenRollback()
        with self.assertRaises(PgCommandFailed) as caught:
            replace_database(source, destination, runner, environment="local")

        self.assertFalse(caught.exception.local_unchanged)
        self.assertIn("Old data is in blockhaus101_django_previous", str(caught.exception))


class TestPgTools(SimpleTestCase):
    def test_refuses_when_a_client_tool_is_missing(self) -> None:
        with (
            patch(
                "blockhaus101_app.management.commands.sync_remote_db.shutil.which",
                return_value=None,
            ),
            self.assertRaisesMessage(SyncRefused, "pg_dump"),
        ):
            require_pg_tools()

    def test_command_keeps_the_password_out_of_the_argv(self) -> None:
        target = parse_database_url(LOCAL_URL)
        invocation = pg_invocation("psql", ["-c", "SELECT 1"], target)

        self.assertEqual(invocation.argv, ["psql", "--no-password", "-c", "SELECT 1"])
        self.assertEqual(invocation.env["PGHOST"], "127.0.0.1")
        self.assertEqual(invocation.env["PGPASSWORD"], "secret")
        self.assertNotIn("secret", " ".join(invocation.argv))

    def test_passes_sslmode_through(self) -> None:
        target = parse_database_url(f"{REMOTE_URL}?sslmode=require")
        invocation = pg_invocation("pg_dump", [], target)

        self.assertEqual(invocation.env["PGHOST"], "192.0.2.10")
        self.assertEqual(invocation.env["PGSSLMODE"], "require")

    def test_hides_the_password_when_a_tool_fails(self) -> None:
        target = parse_database_url(LOCAL_URL)
        completed = subprocess.CompletedProcess(
            args=[], returncode=1, stdout=b"", stderr=b"password secret was rejected"
        )
        with (
            patch(
                "blockhaus101_app.management.commands.sync_remote_db.subprocess.run",
                return_value=completed,
            ),
            self.assertRaises(PgCommandFailed) as caught,
        ):
            run_pg_tool("psql", ["-c", "SELECT 1"], target)

        self.assertNotIn("secret", str(caught.exception))
        self.assertIn("********", str(caught.exception))


class TestDownloadImages(SimpleTestCase):
    def test_saves_a_remote_image_under_the_media_folder(self) -> None:
        def fetch(url: str) -> bytes | None:
            self.assertEqual(
                url,
                "https://www.blockhaus101.com/media/exhibitions_imgs/one.jpg",
            )
            return b"image-bytes"

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = download_images(
                ["exhibitions_imgs/one.jpg"],
                base_url="https://www.blockhaus101.com",
                media_root=root,
                media_url="/media/",
                fetch=fetch,
            )
            saved = root / "exhibitions_imgs" / "one.jpg"
            self.assertEqual(saved.read_bytes(), b"image-bytes")

        self.assertEqual(result.downloaded, 1)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(result.failed, 0)

    def test_skips_an_image_that_is_already_present(self) -> None:
        def fetch(_url: str) -> bytes | None:
            raise AssertionError("existing image should not be downloaded")

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            existing = root / "exhibitions_imgs" / "one.jpg"
            existing.parent.mkdir()
            existing.write_bytes(b"already-there")
            result = download_images(
                ["exhibitions_imgs/one.jpg"],
                base_url="https://www.blockhaus101.com",
                media_root=root,
                media_url="/media/",
                fetch=fetch,
            )
            self.assertEqual(existing.read_bytes(), b"already-there")

        self.assertEqual(result.skipped, 1)

    def test_counts_a_failed_download(self) -> None:
        with TemporaryDirectory() as tmp:
            result = download_images(
                ["exhibitions_imgs/missing.jpg"],
                base_url="https://www.blockhaus101.com",
                media_root=Path(tmp),
                media_url="/media/",
                fetch=lambda _url: None,
            )

        self.assertEqual(result.failed, 1)
        self.assertEqual(result.downloaded, 0)

    def test_refuses_a_path_outside_the_media_folder(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = download_images(
                ["../outside.jpg"],
                base_url="https://www.blockhaus101.com",
                media_root=root,
                media_url="/media/",
                fetch=lambda _url: b"nope",
            )
            self.assertFalse((root.parent / "outside.jpg").exists())

        self.assertEqual(result.failed, 1)

    def test_builds_the_public_image_url(self) -> None:
        self.assertEqual(
            media_file_url(
                "https://www.blockhaus101.com",
                "/media/",
                "exhibitions_imgs/one.jpg",
            ),
            "https://www.blockhaus101.com/media/exhibitions_imgs/one.jpg",
        )


class RecordingTransfer:
    def __init__(self, sizes: str, *, fail: str | None = None) -> None:
        self.sizes = sizes
        self.fail = fail
        self.calls: list[tuple[list[str], bytes]] = []

    def __call__(self, argv: list[str], stdin: bytes | None = None) -> str:
        self.calls.append((argv, b"" if stdin is None else stdin))
        if self.fail is not None and argv[0] == self.fail:
            raise ImageSyncFailed(f"{argv[0]} failed")
        if argv[0] == "ssh":
            return self.sizes
        return ""


class TestRemoteMediaTarget(SimpleTestCase):
    def test_reads_the_ssh_target_and_defaults_the_folder(self) -> None:
        ssh_target, remote_media = load_remote_media_target("deploy@192.0.2.10", None)

        self.assertEqual(ssh_target, "deploy@192.0.2.10")
        self.assertEqual(remote_media, DEFAULT_REMOTE_MEDIA)

    def test_strips_a_trailing_slash_from_the_folder(self) -> None:
        _ssh_target, remote_media = load_remote_media_target(
            "deploy@192.0.2.10",
            "/home/www/blockhaus101/media/",
        )

        self.assertEqual(remote_media, "/home/www/blockhaus101/media")

    def test_refuses_a_missing_ssh_target(self) -> None:
        with self.assertRaisesMessage(SyncRefused, "REMOTE_SSH"):
            load_remote_media_target("  ", None)

    def test_refuses_an_ssh_target_that_is_not_user_at_host(self) -> None:
        with self.assertRaisesMessage(SyncRefused, "user@host"):
            load_remote_media_target("deploy@192.0.2.10;rm", None)

    def test_refuses_a_relative_media_folder(self) -> None:
        with self.assertRaisesMessage(SyncRefused, "absolute path"):
            load_remote_media_target("deploy@192.0.2.10", "media")

    def test_refuses_when_an_upload_tool_is_missing(self) -> None:
        with (
            patch(
                "blockhaus101_app.management.commands.sync_remote_db.shutil.which",
                return_value=None,
            ),
            self.assertRaisesMessage(SyncRefused, "rsync"),
        ):
            require_upload_tools()


class TestUploadImages(SimpleTestCase):
    def test_uploads_only_images_missing_on_the_server(self) -> None:
        transfer = RecordingTransfer("0\n12\n")
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(root, "exhibitions_imgs/new.jpeg")
            self._write(root, "exhibitions_imgs/old.jpeg")
            result = upload_images(
                ["exhibitions_imgs/new.jpeg", "exhibitions_imgs/old.jpeg"],
                media_root=root,
                ssh_target="deploy@192.0.2.10",
                remote_media=DEFAULT_REMOTE_MEDIA,
                run=transfer,
            )

        ssh_argv, ssh_stdin = transfer.calls[0]
        self.assertEqual(ssh_argv[0], "ssh")
        self.assertIn("BatchMode=yes", ssh_argv)
        self.assertEqual(ssh_argv[-2:], ["exhibitions_imgs/new.jpeg", "exhibitions_imgs/old.jpeg"])
        self.assertIn(b"mkdir -p", ssh_stdin)
        rsync_argv, rsync_stdin = transfer.calls[1]
        self.assertEqual(rsync_argv[0], "rsync")
        self.assertEqual(rsync_argv[-2], f"{root.resolve()}/")
        self.assertEqual(rsync_argv[-1], f"deploy@192.0.2.10:{DEFAULT_REMOTE_MEDIA}/")
        self.assertEqual(rsync_stdin, b"exhibitions_imgs/new.jpeg\n")
        self.assertEqual(result.uploaded, 1)
        self.assertEqual(result.skipped, 1)
        self.assertEqual(result.failed, 0)

    def test_skips_rsync_when_every_image_is_already_on_the_server(self) -> None:
        transfer = RecordingTransfer("8\n")
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(root, "exhibitions_imgs/old.jpeg")
            result = upload_images(
                ["exhibitions_imgs/old.jpeg"],
                media_root=root,
                ssh_target="deploy@192.0.2.10",
                remote_media=DEFAULT_REMOTE_MEDIA,
                run=transfer,
            )

        self.assertEqual([call[0][0] for call in transfer.calls], ["ssh"])
        self.assertEqual(result.skipped, 1)
        self.assertEqual(result.uploaded, 0)

    def test_counts_a_missing_local_image_and_still_uploads_the_others(self) -> None:
        transfer = RecordingTransfer("0\n")
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(root, "exhibitions_imgs/new.jpeg")
            result = upload_images(
                ["exhibitions_imgs/missing.jpeg", "exhibitions_imgs/new.jpeg"],
                media_root=root,
                ssh_target="deploy@192.0.2.10",
                remote_media=DEFAULT_REMOTE_MEDIA,
                run=transfer,
            )

        self.assertEqual(transfer.calls[1][1], b"exhibitions_imgs/new.jpeg\n")
        self.assertEqual(result.failed, 1)
        self.assertEqual(result.uploaded, 1)

    def test_refuses_a_path_outside_the_media_folder(self) -> None:
        transfer = RecordingTransfer("")
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = upload_images(
                ["../outside.jpeg"],
                media_root=root,
                ssh_target="deploy@192.0.2.10",
                remote_media=DEFAULT_REMOTE_MEDIA,
                run=transfer,
            )

        self.assertEqual(transfer.calls, [])
        self.assertFalse((root.parent / "outside.jpeg").exists())
        self.assertEqual(result.failed, 1)

    def test_stops_when_the_server_does_not_report_every_size(self) -> None:
        transfer = RecordingTransfer("0\n")
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(root, "exhibitions_imgs/one.jpeg")
            self._write(root, "exhibitions_imgs/two.jpeg")
            with self.assertRaisesMessage(ImageSyncFailed, "size"):
                upload_images(
                    ["exhibitions_imgs/one.jpeg", "exhibitions_imgs/two.jpeg"],
                    media_root=root,
                    ssh_target="deploy@192.0.2.10",
                    remote_media=DEFAULT_REMOTE_MEDIA,
                    run=transfer,
                )

    def test_stops_when_rsync_fails(self) -> None:
        transfer = RecordingTransfer("0\n", fail="rsync")
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(root, "exhibitions_imgs/one.jpeg")
            with self.assertRaisesMessage(ImageSyncFailed, "rsync failed"):
                upload_images(
                    ["exhibitions_imgs/one.jpeg"],
                    media_root=root,
                    ssh_target="deploy@192.0.2.10",
                    remote_media=DEFAULT_REMOTE_MEDIA,
                    run=transfer,
                )

    def _write(self, root: Path, name: str) -> None:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"image-bytes")


@override_settings(ENVIRONMENT="local")
class TestSyncRemoteDbCommand(SimpleTestCase):
    def test_yes_copies_the_remote_database_onto_the_local_one(self) -> None:
        replace = self._run("--yes")

        replace.assert_called_once()
        source, destination = replace.call_args.args[:2]
        self.assertEqual(source.host, "192.0.2.10")
        self.assertEqual(destination.host, "127.0.0.1")
        self.images.assert_called_once()
        self.upload.assert_not_called()

    def test_to_remote_copies_the_local_database_onto_the_remote_one(self) -> None:
        replace = self._run("--to-remote", "--yes")

        replace.assert_called_once()
        source, destination = replace.call_args.args[:2]
        self.assertEqual(source.host, "127.0.0.1")
        self.assertEqual(destination.host, "192.0.2.10")
        self.images.assert_not_called()
        self.upload.assert_called_once_with("deploy@192.0.2.10", DEFAULT_REMOTE_MEDIA)

    def test_confirmation_must_match_the_database_name(self) -> None:
        with self.assertRaisesMessage(CommandError, "not changed"):
            self._run(input_value="no")

    def test_matching_confirmation_copies(self) -> None:
        replace = self._run(input_value=LOCAL_NAME)

        replace.assert_called_once()

    def test_refuses_without_a_remote_url(self) -> None:
        with (
            patch.dict(os.environ, {"DATABASE_URL": LOCAL_URL}, clear=False),
            patch(
                "blockhaus101_app.management.commands.sync_remote_db.replace_database",
                return_value=None,
            ) as replace,
        ):
            os.environ.pop("REMOTE_DATABASE_URL", None)
            with self.assertRaisesMessage(CommandError, "REMOTE_DATABASE_URL"):
                call_command("sync_remote_db", "--yes")
        replace.assert_not_called()

    def test_to_remote_refuses_without_an_ssh_target(self) -> None:
        with (
            override_settings(ENVIRONMENT="local"),
            patch.dict(
                os.environ,
                {"DATABASE_URL": LOCAL_URL, "REMOTE_DATABASE_URL": REMOTE_URL, "REMOTE_SSH": ""},
            ),
            patch("blockhaus101_app.management.commands.sync_remote_db.require_pg_tools"),
            patch(
                "blockhaus101_app.management.commands.sync_remote_db.replace_database",
                return_value=None,
            ) as replace,
            patch(
                "blockhaus101_app.management.commands.sync_remote_db.Command._upload_images",
            ) as upload,
            self.assertRaisesMessage(CommandError, "REMOTE_SSH"),
        ):
            call_command("sync_remote_db", "--to-remote", "--yes")
        replace.assert_not_called()
        upload.assert_not_called()

    def test_to_remote_keeps_the_database_when_a_local_image_is_missing(self) -> None:
        with (
            override_settings(ENVIRONMENT="local"),
            patch.dict(
                os.environ,
                {
                    "DATABASE_URL": LOCAL_URL,
                    "REMOTE_DATABASE_URL": REMOTE_URL,
                    "REMOTE_SSH": "deploy@192.0.2.10",
                },
            ),
            patch("blockhaus101_app.management.commands.sync_remote_db.require_pg_tools"),
            patch("blockhaus101_app.management.commands.sync_remote_db.require_upload_tools"),
            patch(
                "blockhaus101_app.management.commands.sync_remote_db.replace_database",
                return_value=None,
            ) as replace,
            patch(
                "blockhaus101_app.management.commands.sync_remote_db.exhibition_image_names",
                return_value=["exhibitions_imgs/missing.jpeg"],
            ),
            patch(
                "blockhaus101_app.management.commands.sync_remote_db.upload_images",
                return_value=ImageUpload(uploaded=0, skipped=0, failed=1),
            ),
            self.assertRaisesMessage(CommandError, "not changed"),
        ):
            call_command("sync_remote_db", "--to-remote", "--yes")
        replace.assert_not_called()

    @override_settings(ENVIRONMENT="production")
    def test_refuses_when_the_environment_is_production(self) -> None:
        with self.assertRaisesMessage(CommandError, "production"):
            self._run("--yes", environment="production")

    def _run(
        self,
        *args: str,
        input_value: str | None = None,
        environment: str = "local",
    ) -> MagicMock:
        with (
            override_settings(ENVIRONMENT=environment),
            patch.dict(
                os.environ,
                {
                    "DATABASE_URL": LOCAL_URL,
                    "REMOTE_DATABASE_URL": REMOTE_URL,
                    "REMOTE_SSH": "deploy@192.0.2.10",
                },
            ),
            patch("blockhaus101_app.management.commands.sync_remote_db.require_pg_tools"),
            patch("blockhaus101_app.management.commands.sync_remote_db.require_upload_tools"),
            patch(
                "blockhaus101_app.management.commands.sync_remote_db.replace_database",
                return_value=None,
            ) as replace,
            patch(
                "blockhaus101_app.management.commands.sync_remote_db.Command._download_images",
            ) as images,
            patch(
                "blockhaus101_app.management.commands.sync_remote_db.Command._upload_images",
            ) as upload,
            patch("builtins.input", return_value="" if input_value is None else input_value),
        ):
            self.images = images
            self.upload = upload
            call_command("sync_remote_db", *args)
        return replace
