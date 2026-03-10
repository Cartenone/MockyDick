from pathlib import Path

from typer.testing import CliRunner

from getmocked.cli import app

runner = CliRunner()


def test_init_creates_config_file():
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        assert "Sample file created" in result.stdout
        assert Path("getmocked.yaml").exists()


def test_init_fails_if_file_already_exists():
    with runner.isolated_filesystem():
        Path("getmocked.yaml").write_text("already exists", encoding="utf-8")

        result = runner.invoke(app, ["init"])

        assert result.exit_code == 1
        assert "already exists" in result.stdout


def test_validate_succeeds_for_valid_config():
    with runner.isolated_filesystem():
        Path("getmocked.yaml").write_text(
            """routes:
  - method: GET
    path: /health
    response:
      status_code: 200
      body:
        ok: true
""",
            encoding="utf-8",
        )

        result = runner.invoke(app, ["validate", "getmocked.yaml"])

        assert result.exit_code == 0
        assert "Configuration is valid." in result.stdout


def test_validate_fails_for_invalid_config():
    with runner.isolated_filesystem():
        Path("invalid.yaml").write_text(
            """name: example
""",
            encoding="utf-8",
        )

        result = runner.invoke(app, ["validate", "invalid.yaml"])

        assert result.exit_code == 1
        assert "Invalid configuration" in result.stdout