from pathlib import Path
import json
from mockydick.datasources.csv_source import SUPPORTED_SCHEMA_TYPES
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
        has_data_source = "data_source" in response

        selected_response_sources = sum([has_body, has_body_from, has_data_source])

        if selected_response_sources > 1:
            raise ValueError(
                f"Route #{index} can only define one of 'body', 'body_from', or 'data_source'."
            )

        if has_body_from:
            load_json_file(config_path, response["body_from"])

        if has_data_source:
            validate_data_source(response["data_source"], config_path, index)

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


def validate_data_source(data_source: dict, config_path: str, index: int) -> None:
    if not isinstance(data_source, dict):
        raise ValueError(f"'response.data_source' in route #{index} must be an object.")

    source_type = data_source.get("type")
    if source_type != "csv":
        raise ValueError(
            f"'response.data_source.type' in route #{index} must be 'csv'."
        )

    file_path = data_source.get("file")
    if not isinstance(file_path, str):
        raise ValueError(
            f"'response.data_source.file' in route #{index} must be a string."
        )

    load_csv_file_reference(config_path, file_path)

    mode = data_source.get("mode")
    if mode not in {"first", "all"}:
        raise ValueError(
            f"'response.data_source.mode' in route #{index} must be 'first' or 'all'."
        )

    where = data_source.get("where")
    if where is not None:
        if not isinstance(where, dict):
            raise ValueError(
                f"'response.data_source.where' in route #{index} must be an object."
            )

        if "column" not in where:
            raise ValueError(
                f"'response.data_source.where.column' in route #{index} is required."
            )

        has_path_param = "equals_path_param" in where
        has_query_param = "equals_query_param" in where

        if has_path_param == has_query_param:
            raise ValueError(
                f"'response.data_source.where' in route #{index} must define exactly one of "
                f"'equals_path_param' or 'equals_query_param'."
            )

    wrap = data_source.get("wrap")
    if wrap is not None and not isinstance(wrap, str):
        raise ValueError(
            f"'response.data_source.wrap' in route #{index} must be a string."
        )

    not_found_status = data_source.get("not_found_status")
    if not_found_status is not None:
        if not isinstance(not_found_status, int):
            raise ValueError(
                f"'response.data_source.not_found_status' in route #{index} must be an integer."
            )

        if not_found_status < 100 or not_found_status > 599:
            raise ValueError(
                f"'response.data_source.not_found_status' in route #{index} must be a valid HTTP status code."
            )

    not_found_body = data_source.get("not_found_body")
    if not_found_body is not None and not isinstance(
        not_found_body, (dict, list, str, int, float, bool)
    ):
        raise ValueError(
            f"'response.data_source.not_found_body' in route #{index} must be a valid JSON-compatible value."
        )

    coerce_types = data_source.get("coerce_types")
    if coerce_types is not None and not isinstance(coerce_types, bool):
        raise ValueError(
            f"'response.data_source.coerce_types' in route #{index} must be a boolean."
        )

    schema = data_source.get("schema")
    if schema is not None:
        if not isinstance(schema, dict):
            raise ValueError(
                f"'response.data_source.schema' in route #{index} must be an object."
            )

        for field_name, field_type in schema.items():
            if not isinstance(field_name, str):
                raise ValueError(
                    f"'response.data_source.schema' in route #{index} must use string field names."
                )

            if field_type not in SUPPORTED_SCHEMA_TYPES:
                allowed = ", ".join(sorted(SUPPORTED_SCHEMA_TYPES))
                raise ValueError(
                    f"'response.data_source.schema.{field_name}' in route #{index} "
                    f"must be one of: {allowed}."
                )

def load_json_file(config_path: str, relative_json_path: str):
    base_path = Path(config_path).parent
    json_path = (base_path / relative_json_path).resolve()

    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found: {relative_json_path}")

    with json_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_csv_file_reference(config_path: str, relative_csv_path: str) -> None:
    base_path = Path(config_path).parent
    csv_path = (base_path / relative_csv_path).resolve()

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {relative_csv_path}")
    
