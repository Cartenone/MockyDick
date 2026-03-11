import pytest

from mockydick.config import load_config, load_json_file


def test_load_config_reads_valid_yaml(tmp_path):
    config_file = tmp_path / "test.yaml"
    config_file.write_text(
        """
routes:
  - method: GET
    path: /health
    response:
      status_code: 200
      body:
        ok: true
""",
        encoding="utf-8",
    )

    config = load_config(str(config_file))

    assert "routes" in config
    assert isinstance(config["routes"], list)
    assert config["routes"][0]["method"] == "GET"
    assert config["routes"][0]["path"] == "/health"


def test_load_config_raises_if_file_does_not_exist():
    with pytest.raises(FileNotFoundError):
        load_config("missing.yaml")


def test_load_config_raises_if_root_is_not_a_dict(tmp_path):
    config_file = tmp_path / "invalid.yaml"
    config_file.write_text(
        """
- method: GET
  path: /health
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="root object"):
        load_config(str(config_file))


def test_load_config_raises_if_routes_is_missing(tmp_path):
    config_file = tmp_path / "missing_routes.yaml"
    config_file.write_text(
        """
name: example
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Missing 'routes' key"):
        load_config(str(config_file))


def test_load_config_raises_if_routes_is_not_a_list(tmp_path):
    config_file = tmp_path / "invalid_routes.yaml"
    config_file.write_text(
        """
routes:
  method: GET
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="'routes' must be a list"):
        load_config(str(config_file))


def test_load_json_file_reads_json_relative_to_config(tmp_path):
    config_file = tmp_path / "mockydick.yaml"
    config_file.write_text("routes: []", encoding="utf-8")

    responses_dir = tmp_path / "responses"
    responses_dir.mkdir()

    json_file = responses_dir / "users.json"
    json_file.write_text(
        """
{
  "users": [
    { "id": 1, "name": "Mario" }
  ]
}
""",
        encoding="utf-8",
    )

    data = load_json_file(str(config_file), "./responses/users.json")

    assert data == {
        "users": [
            {"id": 1, "name": "Mario"}
        ]
    }


def test_load_json_file_raises_if_json_file_does_not_exist(tmp_path):
    config_file = tmp_path / "mockydick.yaml"
    config_file.write_text("routes: []", encoding="utf-8")

    with pytest.raises(FileNotFoundError):
        load_json_file(str(config_file), "./responses/missing.json")


def test_load_config_raises_if_route_has_no_method(tmp_path):
    config_file = tmp_path / "invalid.yaml"
    config_file.write_text(
        """
routes:
  - path: /health
    response:
      status_code: 200
      body:
        ok: true
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="is missing 'method'"):
        load_config(str(config_file))


def test_load_config_raises_if_route_has_no_path(tmp_path):
    config_file = tmp_path / "invalid.yaml"
    config_file.write_text(
        """
routes:
  - method: GET
    response:
      status_code: 200
      body:
        ok: true
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="is missing 'path'"):
        load_config(str(config_file))


def test_load_config_raises_if_route_has_no_response(tmp_path):
    config_file = tmp_path / "invalid.yaml"
    config_file.write_text(
        """
routes:
  - method: GET
    path: /health
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="is missing 'response'"):
        load_config(str(config_file))


def test_load_config_raises_if_body_and_body_from_are_both_present(tmp_path):
    responses_dir = tmp_path / "responses"
    responses_dir.mkdir()

    json_file = responses_dir / "health.json"
    json_file.write_text('{"ok": true}', encoding="utf-8")

    config_file = tmp_path / "invalid.yaml"
    config_file.write_text(
        """
routes:
  - method: GET
    path: /health
    response:
      body:
        ok: true
      body_from: ./responses/health.json
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="cannot have both 'body' and 'body_from'"):
        load_config(str(config_file))


def test_load_config_raises_if_request_query_is_not_an_object(tmp_path):
    config_file = tmp_path / "invalid.yaml"
    config_file.write_text(
        """
routes:
  - method: GET
    path: /orders
    request:
      query: shipped
    response:
      status_code: 200
      body:
        items: []
""",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="'request.query' in route #1 must be an object",
    ):
        load_config(str(config_file))


def test_load_config_raises_if_request_headers_is_not_an_object(tmp_path):
    config_file = tmp_path / "invalid.yaml"
    config_file.write_text(
        """
routes:
  - method: GET
    path: /profile
    request:
      headers: Bearer secret-token
    response:
      status_code: 200
      body:
        user: mario
""",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="'request.headers' in route #1 must be an object",
    ):
        load_config(str(config_file))


def test_load_config_raises_if_request_json_is_not_object_or_list(tmp_path):
    config_file = tmp_path / "invalid.yaml"
    config_file.write_text(
        """
routes:
  - method: POST
    path: /login
    request:
      json: hello
    response:
      status_code: 200
      body:
        token: fake-jwt-token
""",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="'request.json' in route #1 must be an object or a list",
    ):
        load_config(str(config_file))


def test_load_config_raises_if_response_delay_ms_is_not_an_int(tmp_path):
    config_file = tmp_path / "invalid.yaml"
    config_file.write_text(
        """
routes:
  - method: GET
    path: /slow
    response:
      status_code: 200
      delay_ms: hello
      body:
        ok: true
""",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="'response.delay_ms' in route #1 must be an integer",
    ):
        load_config(str(config_file))


def test_load_config_raises_if_response_delay_ms_is_negative(tmp_path):
    config_file = tmp_path / "invalid.yaml"
    config_file.write_text(
        """
routes:
  - method: GET
    path: /slow
    response:
      status_code: 200
      delay_ms: -100
      body:
        ok: true
""",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="'response.delay_ms' in route #1 cannot be negative",
    ):
        load_config(str(config_file))