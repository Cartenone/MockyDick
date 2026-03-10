from pathlib import Path
import json

import yaml


def load_config(path: str) -> dict:
    config_path = Path(path)

    if not config_path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with config_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}

    if not isinstance(data, dict):
        raise ValueError("The YAML file must contain a root object.")

    routes = data.get("routes")
    if routes is None:
        raise ValueError("Missing 'routes' key in YAML file.")

    if not isinstance(routes, list):
        raise ValueError("'routes' must be a list.")

    validate_routes(data, path)

    return data


def validate_routes(config: dict, config_path: str) -> None:
    routes = config.get("routes", [])

    for index, route in enumerate(routes, start=1):
        if not isinstance(route, dict):
            raise ValueError(f"Route #{index} must be an object.")

        if "method" not in route:
            raise ValueError(f"Route #{index} is missing 'method'.")

        if "path" not in route:
            raise ValueError(f"Route #{index} is missing 'path'.")

        if "response" not in route:
            raise ValueError(f"Route #{index} is missing 'response'.")

        request = route.get("request")
        if request is not None and not isinstance(request, dict):
            raise ValueError(f"'request' in route #{index} must be an object.")

        if request is not None:
            query = request.get("query")
            if query is not None and not isinstance(query, dict):
                raise ValueError(
                    f"'request.query' in route #{index} must be an object."
                )

            headers = request.get("headers")
            if headers is not None and not isinstance(headers, dict):
                raise ValueError(
                    f"'request.headers' in route #{index} must be an object."
                )

            expected_json = request.get("json")
            if expected_json is not None and not isinstance(expected_json, (dict, list)):
                raise ValueError(
                    f"'request.json' in route #{index} must be an object or a list."
                )

        response = route["response"]

        if not isinstance(response, dict):
            raise ValueError(f"'response' in route #{index} must be an object.")

        has_body = "body" in response
        has_body_from = "body_from" in response

        if has_body and has_body_from:
            raise ValueError(
                f"Route #{index} cannot have both 'body' and 'body_from'."
            )

        if has_body_from:
            load_json_file(config_path, response["body_from"])

        delay_ms = response.get("delay_ms")
        if delay_ms is not None:
            if not isinstance(delay_ms, int):
                raise ValueError(
                    f"'response.delay_ms' in route #{index} must be an integer."
                )

            if delay_ms < 0:
                raise ValueError(
                    f"'response.delay_ms' in route #{index} cannot be negative."
                )


def load_json_file(config_path: str, relative_json_path: str):
    base_path = Path(config_path).parent
    json_path = (base_path / relative_json_path).resolve()

    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found: {relative_json_path}")

    with json_path.open("r", encoding="utf-8") as file:
        return json.load(file)