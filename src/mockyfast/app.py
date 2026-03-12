from collections import defaultdict
import asyncio
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from mockyfast.config import load_config, load_json_file
from mockyfast.datasources.csv_source import query_csv_data


def render_template(value, path_params: dict):
    if isinstance(value, str):
        try:
            return value.format(**path_params)
        except Exception:
            return value

    if isinstance(value, dict):
        return {key: render_template(val, path_params) for key, val in value.items()}

    if isinstance(value, list):
        return [render_template(item, path_params) for item in value]

    return value


def query_matches(expected_query: dict, actual_query: dict) -> bool:
    for key, expected_value in expected_query.items():
        actual_value = actual_query.get(key)
        if actual_value != str(expected_value):
            return False
    return True


def headers_matches(expected_headers: dict, actual_headers: dict) -> bool:
    normalized_actual_headers = {
        key.lower(): value for key, value in actual_headers.items()
    }

    for key, expected_value in expected_headers.items():
        actual_value = normalized_actual_headers.get(key.lower())
        if actual_value != str(expected_value):
            return False
    return True


def json_matches(expected, actual) -> bool:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return False

        for key, expected_value in expected.items():
            if key not in actual:
                return False
            if not json_matches(expected_value, actual[key]):
                return False

        return True

    if isinstance(expected, list):
        if not isinstance(actual, list):
            return False

        if len(expected) != len(actual):
            return False

        for expected_item, actual_item in zip(expected, actual):
            if not json_matches(expected_item, actual_item):
                return False

        return True

    return expected == actual


async def route_matches(route: dict, request: Request) -> bool:
    request_config = route.get("request", {})

    expected_query = request_config.get("query")
    if expected_query:
        actual_query = dict(request.query_params)
        if not query_matches(expected_query, actual_query):
            return False

    expected_headers = request_config.get("headers")
    if expected_headers:
        actual_headers = dict(request.headers)
        if not headers_matches(expected_headers, actual_headers):
            return False

    expected_json = request_config.get("json")
    if expected_json is not None:
        try:
            actual_json = await request.json()
        except Exception:
            return False

        if not json_matches(expected_json, actual_json):
            return False

    return True


def build_data_source_response(
    route: dict,
    config_path: str,
    path_params: dict[str, Any],
    query_params: dict[str, Any],
) -> tuple[bool, Any, int | None, Any]:
    response_config = route.get("response", {})
    data_source = response_config["data_source"]

    result = query_csv_data(
        config_path=config_path,
        relative_csv_path=data_source["file"],
        mode=data_source["mode"],
        where=data_source.get("where"),
        path_params=path_params,
        query_params=query_params,
        schema=data_source.get("schema"),
        coerce_types=data_source.get("coerce_types", False),
    )

    if data_source["mode"] == "first" and result is None:
        not_found_status = data_source.get("not_found_status", 404)
        not_found_body = data_source.get(
            "not_found_body", {"detail": "Resource not found"}
        )
        return False, None, not_found_status, not_found_body

    wrap = data_source.get("wrap")
    if wrap is not None:
        result = {wrap: result}

    return True, result, None, None


def build_response_body(
    route: dict,
    config_path: str,
    path_params: dict[str, Any],
    query_params: dict[str, Any],
) -> tuple[bool, Any, int | None, Any]:
    response_config = route.get("response", {})

    if "data_source" in response_config:
        return build_data_source_response(
            route=route,
            config_path=config_path,
            path_params=path_params,
            query_params=query_params,
        )

    if "body_from" in response_config:
        body = load_json_file(config_path, response_config["body_from"])
    else:
        body = response_config.get("body", {})

    return True, render_template(body, path_params), None, None


def get_response_delay_ms(route: dict) -> int:
    response_config = route.get("response", {})
    return int(response_config.get("delay_ms", 0))


def create_app(config_path: str) -> FastAPI:
    config = load_config(config_path)
    app = FastAPI(title="MockyFast")

    routes = config.get("routes", [])
    grouped_routes = defaultdict(list)

    for route in routes:
        method = route["method"].upper()
        path = route["path"]
        grouped_routes[(method, path)].append(route)

    for (method, path), route_group in grouped_routes.items():

        async def handler(
            request: Request,
            _route_group=route_group,
            _config_path=config_path,
        ):
            for route in _route_group:
                if await route_matches(route, request):
                    response_config = route.get("response", {})
                    status_code = response_config.get("status_code", 200)

                    found, body, not_found_status, not_found_body = build_response_body(
                        route=route,
                        config_path=_config_path,
                        path_params=request.path_params,
                        query_params=dict(request.query_params),
                    )

                    if not found:
                        return JSONResponse(
                            content=not_found_body,
                            status_code=not_found_status,
                        )

                    delay_ms = get_response_delay_ms(route)

                    if delay_ms > 0:
                        await asyncio.sleep(delay_ms / 1000)

                    return JSONResponse(
                        content=body,
                        status_code=status_code,
                    )

            return JSONResponse(
                content={"detail": "No matching mock route found"},
                status_code=404,
            )

        app.add_api_route(path, handler, methods=[method])

    return app