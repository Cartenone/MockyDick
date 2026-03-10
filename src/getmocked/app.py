from collections import defaultdict
import asyncio

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from getmocked.config import load_config, load_json_file


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
    normalized_actual_headers = {key.lower(): value for key, value in actual_headers.items()}

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


def build_response_body(route: dict, config_path: str, path_params: dict):
    response_config = route.get("response", {})

    if "body_from" in response_config:
        body = load_json_file(config_path, response_config["body_from"])
    else:
        body = response_config.get("body", {})

    return render_template(body, path_params)


def get_response_delay_ms(route: dict) -> int:
    response_config = route.get("response", {})
    return int(response_config.get("delay_ms", 0))


def create_app(config_path: str) -> FastAPI:
    config = load_config(config_path)
    app = FastAPI(title="getMocked")

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
                    body = build_response_body(route, _config_path, request.path_params)
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