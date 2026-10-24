"""Safety checks for copying a remote database over the local one.

These tests never open a database connection. The copy itself is scripted.
"""

import os
import subprocess
from typing import BinaryIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from blockhaus101_app.management.commands.sync_remote_db import (
    DatabaseTarget,
    PgCommandFailed,
    SyncRefused,
    assert_sync_is_safe,
    load_sync_targets,
    parse_database_url,
    pg_invocation,
    replace_database,
    require_pg_tools,
    run_pg_tool,
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


@override_settings(ENVIRONMENT="local")
class TestSyncRemoteDbCommand(SimpleTestCase):
    def test_yes_copies_the_remote_database_onto_the_local_one(self) -> None:
        replace = self._run("--yes")

        replace.assert_called_once()
        source, destination = replace.call_args.args[:2]
        self.assertEqual(source.host, "192.0.2.10")
        self.assertEqual(destination.host, "127.0.0.1")

    def test_to_remote_copies_the_local_database_onto_the_remote_one(self) -> None:
        replace = self._run("--to-remote", "--yes")

        replace.assert_called_once()
        source, destination = replace.call_args.args[:2]
        self.assertEqual(source.host, "127.0.0.1")
        self.assertEqual(destination.host, "192.0.2.10")

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
                {"DATABASE_URL": LOCAL_URL, "REMOTE_DATABASE_URL": REMOTE_URL},
            ),
            patch("blockhaus101_app.management.commands.sync_remote_db.require_pg_tools"),
            patch(
                "blockhaus101_app.management.commands.sync_remote_db.replace_database",
                return_value=None,
            ) as replace,
            patch("builtins.input", return_value="" if input_value is None else input_value),
        ):
            call_command("sync_remote_db", *args)
        return replace
