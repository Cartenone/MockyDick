![mockydick cover](./assets/cover.png)

# MockyDick

**MockyDick** is a Python CLI tool for mocking HTTP APIs locally using YAML and JSON files.

It helps you simulate external services during local development without relying on hosted mock platforms or remote dashboards.

## Why?

Because sometimes you just need a fast, local, and controllable way to simulate APIs while developing.

No external mock platforms, no unnecessary setup — just local files, a local server, and a workflow you control.

---

## Features

- initialize a sample config file
- validate mock configuration before running
- serve mock HTTP endpoints locally
- support inline JSON responses
- support external JSON response files
- support path parameters
- support request matching by:
  - query params
  - headers
  - JSON body
- support delayed responses with `delay_ms`
- automated tests with `pytest`

---

## Installation

### From source

```bash
git clone https://github.com/Cartenone/mockydick.git
cd mockydick
pip install .
```

### Development install

```bash
pip install -e ".[dev]"
```

---

## Commands

### Main command

```bash
mockydick init
mockydick validate mockydick.yaml
mockydick serve mockydick.yaml --port 8000
```

### Short alias

```bash
mdk init
mdk validate mockydick.yaml
mdk serve mockydick.yaml --port 8000
```

---

## Quick start

Create a sample config:

```bash
mdk init
```

Validate it:

```bash
mdk validate mockydick.yaml
```

Start the mock server:

```bash
mdk serve mockydick.yaml --port 8000
```

Then call it:

```bash
curl http://127.0.0.1:8000/health
```

---

## Example configuration

### Basic route

```yaml
routes:
  - method: GET
    path: /health
    response:
      status_code: 200
      body:
        ok: true
```

---

## Using external JSON files

### `mockydick.yaml`

```yaml
routes:
  - method: GET
    path: /users
    response:
      status_code: 200
      body_from: ./responses/users.json
```

### `responses/users.json`

```json
{
  "users": [
    { "id": 1, "name": "Mario" },
    { "id": 2, "name": "Luigi" }
  ]
}
```

---

## Path params

You can use path parameters in the route path and reference them in the response body.

```yaml
routes:
  - method: GET
    path: /users/{user_id}
    response:
      status_code: 200
      body:
        id: "{user_id}"
        name: "User {user_id}"
```

Example:

```bash
curl http://127.0.0.1:8000/users/123
```

Response:

```json
{
  "id": "123",
  "name": "User 123"
}
```

---

## Request matching

`mockydick` can return different responses for the same path depending on the request.

### Match by query params

```yaml
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
```

### Match by headers

```yaml
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
```

### Match by JSON body

```yaml
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
```

---

## Delayed responses

You can simulate slow APIs using `delay_ms`.

```yaml
routes:
  - method: GET
    path: /slow
    response:
      status_code: 200
      delay_ms: 3000
      body:
        ok: true
```

This is useful when you want to simulate:

- slow services
- network latency
- client-side timeouts

---

## Example use case

Imagine your application depends on an external service.

Instead of calling the real service during local development, you can point your app to `http://127.0.0.1:8000` and let `mockydick` simulate the API.

That makes it easier to:

- develop locally
- reproduce edge cases
- test success and error responses
- work without depending on external environments

---

## Project structure example

```text
mocks/
├─ mockydick.yaml
└─ responses/
   └─ users.json
```

Then run:

```bash
mdk serve ./mocks/mockydick.yaml --port 8000
```

---

## Validation

Before starting the server, you can validate your configuration:

```bash
mdk validate mockydick.yaml
```

This helps catch issues like:

- missing `routes`
- invalid route structure
- missing JSON files
- invalid `delay_ms`
- invalid request matching config

---

## Tests

Run the test suite with:

```bash
pytest
```

---

## Roadmap

Planned improvements:

- better error messages
- reusable datasets / data-driven mocks
- HTTP client mode
- capture real responses into mock files
- more advanced matching rules

---

## Author

Created by Cartenone.

---

## License

MIT