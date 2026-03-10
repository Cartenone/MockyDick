from fastapi.testclient import TestClient
import time
from getmocked.app import create_app


def test_create_app_serves_configured_route(tmp_path):
    config_file = tmp_path / "getmocked.yaml"
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

    app = create_app(str(config_file))
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_create_app_returns_custom_status_code(tmp_path):
    config_file = tmp_path / "getmocked.yaml"
    config_file.write_text(
        """
routes:
  - method: GET
    path: /not-found
    response:
      status_code: 404
      body:
        error: not_found
""",
        encoding="utf-8",
    )

    app = create_app(str(config_file))
    client = TestClient(app)

    response = client.get("/not-found")

    assert response.status_code == 404
    assert response.json() == {"error": "not_found"}


def test_create_app_loads_body_from_json_file(tmp_path):
    responses_dir = tmp_path / "responses"
    responses_dir.mkdir()

    json_file = responses_dir / "users.json"
    json_file.write_text(
        """
{
  "users": [
    { "id": 1, "name": "Mario" },
    { "id": 2, "name": "Luigi" }
  ]
}
""",
        encoding="utf-8",
    )

    config_file = tmp_path / "getmocked.yaml"
    config_file.write_text(
        """
routes:
  - method: GET
    path: /users
    response:
      status_code: 200
      body_from: ./responses/users.json
""",
        encoding="utf-8",
    )

    app = create_app(str(config_file))
    client = TestClient(app)

    response = client.get("/users")

    assert response.status_code == 200
    assert response.json() == {
        "users": [
            {"id": 1, "name": "Mario"},
            {"id": 2, "name": "Luigi"},
        ]
    }

def test_create_app_supports_path_params_in_body(tmp_path):
    config_file = tmp_path / "getmocked.yaml"
    config_file.write_text(
        """
routes:
  - method: GET
    path: /users/{user_id}
    response:
      status_code: 200
      body:
        id: "{user_id}"
        name: "User {user_id}"
""",
        encoding="utf-8",
    )

    app = create_app(str(config_file))
    client = TestClient(app)

    response = client.get("/users/123")

    assert response.status_code == 200
    assert response.json() == {
        "id": "123",
        "name": "User 123",
    }


def test_create_app_supports_path_params_in_body_from_json(tmp_path):
    responses_dir = tmp_path / "responses"
    responses_dir.mkdir()

    json_file = responses_dir / "user.json"
    json_file.write_text(
        """
{
  "id": "{user_id}",
  "message": "User {user_id} loaded"
}
""",
        encoding="utf-8",
    )

    config_file = tmp_path / "getmocked.yaml"
    config_file.write_text(
        """
routes:
  - method: GET
    path: /users/{user_id}
    response:
      status_code: 200
      body_from: ./responses/user.json
""",
        encoding="utf-8",
    )

    app = create_app(str(config_file))
    client = TestClient(app)

    response = client.get("/users/42")

    assert response.status_code == 200
    assert response.json() == {
        "id": "42",
        "message": "User 42 loaded",
    }
def test_create_app_matches_route_by_query_params(tmp_path):
    config_file = tmp_path / "getmocked.yaml"
    config_file.write_text(
        """
routes:
  - method: GET
    path: /orders
    request:
      query:
        status: shipped
    response:
      status_code: 200
      body:
        items:
          - id: 1
            status: shipped

  - method: GET
    path: /orders
    response:
      status_code: 200
      body:
        items: []
""",
        encoding="utf-8",
    )

    app = create_app(str(config_file))
    client = TestClient(app)

    response = client.get("/orders?status=shipped")

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {"id": 1, "status": "shipped"},
        ]
    }


def test_create_app_uses_fallback_route_when_query_does_not_match(tmp_path):
    config_file = tmp_path / "getmocked.yaml"
    config_file.write_text(
        """
routes:
  - method: GET
    path: /orders
    request:
      query:
        status: shipped
    response:
      status_code: 200
      body:
        items:
          - id: 1
            status: shipped

  - method: GET
    path: /orders
    response:
      status_code: 200
      body:
        items: []
""",
        encoding="utf-8",
    )

    app = create_app(str(config_file))
    client = TestClient(app)

    response = client.get("/orders")

    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_create_app_returns_404_when_no_route_matches(tmp_path):
    config_file = tmp_path / "getmocked.yaml"
    config_file.write_text(
        """
routes:
  - method: GET
    path: /orders
    request:
      query:
        status: shipped
    response:
      status_code: 200
      body:
        items:
          - id: 1
            status: shipped
""",
        encoding="utf-8",
    )

    app = create_app(str(config_file))
    client = TestClient(app)

    response = client.get("/orders")

    assert response.status_code == 404
    assert response.json() == {"detail": "No matching mock route found"}

def test_create_app_matches_route_by_headers(tmp_path):
    config_file = tmp_path / "getmocked.yaml"
    config_file.write_text(
        """
routes:
  - method: GET
    path: /profile
    request:
      headers:
        Authorization: Bearer secret-token
    response:
      status_code: 200
      body:
        user: mario

  - method: GET
    path: /profile
    response:
      status_code: 401
      body:
        error: unauthorized
""",
        encoding="utf-8",
    )

    app = create_app(str(config_file))
    client = TestClient(app)

    response = client.get("/profile", headers={"Authorization": "Bearer secret-token"})

    assert response.status_code == 200
    assert response.json() == {"user": "mario"}


def test_create_app_uses_fallback_route_when_headers_do_not_match(tmp_path):
    config_file = tmp_path / "getmocked.yaml"
    config_file.write_text(
        """
routes:
  - method: GET
    path: /profile
    request:
      headers:
        Authorization: Bearer secret-token
    response:
      status_code: 200
      body:
        user: mario

  - method: GET
    path: /profile
    response:
      status_code: 401
      body:
        error: unauthorized
""",
        encoding="utf-8",
    )

    app = create_app(str(config_file))
    client = TestClient(app)

    response = client.get("/profile")

    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}


def test_create_app_matches_headers_case_insensitively(tmp_path):
    config_file = tmp_path / "getmocked.yaml"
    config_file.write_text(
        """
routes:
  - method: GET
    path: /profile
    request:
      headers:
        authorization: Bearer secret-token
    response:
      status_code: 200
      body:
        user: mario
""",
        encoding="utf-8",
    )

    app = create_app(str(config_file))
    client = TestClient(app)

    response = client.get("/profile", headers={"Authorization": "Bearer secret-token"})

    assert response.status_code == 200
    assert response.json() == {"user": "mario"}
def test_create_app_matches_route_by_json_body(tmp_path):
    config_file = tmp_path / "getmocked.yaml"
    config_file.write_text(
        """
routes:
  - method: POST
    path: /login
    request:
      json:
        username: admin
        password: secret
    response:
      status_code: 200
      body:
        token: fake-jwt-token

  - method: POST
    path: /login
    response:
      status_code: 401
      body:
        error: invalid_credentials
""",
        encoding="utf-8",
    )

    app = create_app(str(config_file))
    client = TestClient(app)

    response = client.post(
        "/login",
        json={
            "username": "admin",
            "password": "secret",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"token": "fake-jwt-token"}


def test_create_app_uses_fallback_route_when_json_body_does_not_match(tmp_path):
    config_file = tmp_path / "getmocked.yaml"
    config_file.write_text(
        """
routes:
  - method: POST
    path: /login
    request:
      json:
        username: admin
        password: secret
    response:
      status_code: 200
      body:
        token: fake-jwt-token

  - method: POST
    path: /login
    response:
      status_code: 401
      body:
        error: invalid_credentials
""",
        encoding="utf-8",
    )

    app = create_app(str(config_file))
    client = TestClient(app)

    response = client.post(
        "/login",
        json={
            "username": "admin",
            "password": "wrong",
        },
    )

    assert response.status_code == 401
    assert response.json() == {"error": "invalid_credentials"}


def test_create_app_returns_404_when_json_is_required_but_request_has_no_json(tmp_path):
    config_file = tmp_path / "getmocked.yaml"
    config_file.write_text(
        """
routes:
  - method: POST
    path: /login
    request:
      json:
        username: admin
    response:
      status_code: 200
      body:
        token: fake-jwt-token
""",
        encoding="utf-8",
    )

    app = create_app(str(config_file))
    client = TestClient(app)

    response = client.post("/login", content="not-json")

    assert response.status_code == 404
    assert response.json() == {"detail": "No matching mock route found"}


def test_create_app_json_match_is_partial_for_dicts(tmp_path):
    config_file = tmp_path / "getmocked.yaml"
    config_file.write_text(
        """
routes:
  - method: POST
    path: /login
    request:
      json:
        username: admin
    response:
      status_code: 200
      body:
        token: fake-jwt-token
""",
        encoding="utf-8",
    )

    app = create_app(str(config_file))
    client = TestClient(app)

    response = client.post(
        "/login",
        json={
            "username": "admin",
            "password": "secret",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"token": "fake-jwt-token"}

def test_create_app_applies_response_delay(tmp_path):
    config_file = tmp_path / "getmocked.yaml"
    config_file.write_text(
        """
routes:
  - method: GET
    path: /slow
    response:
      status_code: 200
      delay_ms: 100
      body:
        ok: true
""",
        encoding="utf-8",
    )

    app = create_app(str(config_file))
    client = TestClient(app)

    start = time.perf_counter()
    response = client.get("/slow")
    elapsed = time.perf_counter() - start

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert elapsed >= 0.09