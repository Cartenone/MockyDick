![mockyfast cover](./assets/cover.png)

# MockyFast

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**MockyFast** is a Python CLI tool for mocking HTTP APIs locally using YAML, JSON, and CSV-backed datasets.

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
- support CSV-backed data-driven mocks
- support response shaping for CSV data sources:
  - `wrap`
  - `not_found_status`
  - `not_found_body`
- support CSV type coercion and schema mapping
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
git clone https://github.com/Cartenone/mockyfast.git
cd mockyfast
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
mockyfast init
mockyfast validate mockyfast.yaml
mockyfast serve mockyfast.yaml --port 8000
```

### Short alias

```bash
mkf init
mkf validate mockyfast.yaml
mkf serve mockyfast.yaml --port 8000
```

---

## Quick start

Create a sample config:

```bash
mkf init
```

Validate it:

```bash
mkf validate mockyfast.yaml
```

Start the mock server:

```bash
mkf serve mockyfast.yaml --port 8000
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

### `mockyfast.yaml`

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

## CSV-backed data-driven mocks

MockyFast can build responses from local CSV files, making mocks more dynamic and reusable.

### `mocks/mockyfast.yaml`

```yaml
routes:
  - method: GET
    path: /users
    response:
      data_source:
        type: csv
        file: ./data/users.csv
        mode: all
        wrap: items

  - method: GET
    path: /users/{user_id}
    response:
      data_source:
        type: csv
        file: ./data/users.csv
        mode: first
        where:
          column: id
          equals_path_param: user_id
        not_found_status: 404
        not_found_body:
          error: user_not_found
```

### `mocks/data/users.csv`

```csv
id,name,active,balance
1,Mario,true,12.5
2,Luigi,false,7
```

### Example calls

```bash
curl http://127.0.0.1:8000/users
curl http://127.0.0.1:8000/users/1
curl http://127.0.0.1:8000/users/999
```

### Example response for `GET /users`

```json
{
  "items": [
    {
      "id": "1",
      "name": "Mario",
      "active": "true",
      "balance": "12.5"
    },
    {
      "id": "2",
      "name": "Luigi",
      "active": "false",
      "balance": "7"
    }
  ]
}
```

### Type coercion

You can automatically coerce CSV values into Python/JSON primitive types.

```yaml
routes:
  - method: GET
    path: /users/{user_id}
    response:
      data_source:
        type: csv
        file: ./data/users.csv
        mode: first
        where:
          column: id
          equals_path_param: user_id
        coerce_types: true
```

With `coerce_types: true`, values such as:

- `true` → `true`
- `false` → `false`
- `12` → `12`
- `12.5` → `12.5`

are returned as properly typed JSON values.

### Schema mapping

For more control, you can define an explicit schema:

```yaml
routes:
  - method: GET
    path: /users/{user_id}
    response:
      data_source:
        type: csv
        file: ./data/users.csv
        mode: first
        where:
          column: id
          equals_path_param: user_id
        schema:
          id: int
          active: bool
          balance: float
```

Supported schema types:

- `str`
- `int`
- `float`
- `bool`

When `schema` is present, it takes precedence over `coerce_types`.

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

`mockyfast` can return different responses for the same path depending on the request.

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

Instead of calling the real service during local development, you can point your app to `http://127.0.0.1:8000` and let `mockyfast` simulate the API.

That makes it easier to:

- develop locally
- reproduce edge cases
- test success and error responses
- work without depending on external environments

---

## Project structure example

```text
mocks/
├─ mockyfast.yaml
├─ data/
│  └─ users.csv
└─ responses/
   └─ users.json
```

Then run:

```bash
mkf serve ./mocks/mockyfast.yaml --port 8000
```

---

## Validation

Before starting the server, you can validate your configuration:

```bash
mkf validate mockyfast.yaml
```

This helps catch issues like:

- missing `routes`
- invalid route structure
- missing JSON files
- missing CSV files
- invalid `delay_ms`
- invalid request matching config
- invalid CSV schema configuration

---

## Tests

Run the test suite with:

```bash
pytest
```

---

## Roadmap

Planned improvements:

- better error messages and validation feedback
- JSON-backed data-driven mocks
- HTTP client / probe mode
- capture real API responses into reusable mock files
- more advanced matching rules
- stateful mock scenarios
- extended fault injection beyond `delay_ms`

Future exploration:

- OpenAPI-based mock generation
- record & replay mode
- GraphQL support
- WebSocket mocking
- gRPC support
- SOAP/XML support

---

## Author

Created by Cartenone.

---

## License

MIT