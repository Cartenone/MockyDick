from collections import defaultdict
import asyncio
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from mockyfast.config import load_config, load_json_file
from mockyfast.state_store import InMemoryResourceStore
from mockyfast.datasources.csv_source import load_csv_rows, query_csv_data
from mockyfast.datasources.json_source import load_json_rows, query_json_data


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


def get_resource_name(route: dict) -> str:
    response_config = route.get("response", {})
    data_source = response_config["data_source"]

    if "resource_name" in data_source:
        return data_source["resource_name"]

    return route["path"]


def seed_mutable_store_for_route(
    route: dict,
    config_path: str,
    store: InMemoryResourceStore,
) -> None:
    response_config = route.get("response", {})
    data_source = response_config.get("data_source")

    if not data_source or not data_source.get("mutable", False):
        return

    resource_name = get_resource_name(route)

    if data_source["type"] == "csv":
        rows = load_csv_rows(config_path, data_source["file"])
    elif data_source["type"] == "json":
        rows = load_json_rows(config_path, data_source["file"])
    else:
        raise ValueError(f"Unsupported data source type: {data_source['type']}")

    store.seed(resource_name, rows)


def resolve_where_expected_value(
    where: dict[str, Any],
    path_params: dict[str, Any],
    query_params: dict[str, Any],
) -> Any:
    if "equals_path_param" in where:
        return path_params.get(where["equals_path_param"])

    if "equals_query_param" in where:
        return query_params.get(where["equals_query_param"])

    return None


def query_mutable_data_source(
    route: dict,
    store: InMemoryResourceStore,
    path_params: dict[str, Any],
    query_params: dict[str, Any],
) -> Any:
    response_config = route.get("response", {})
    data_source = response_config["data_source"]

    resource_name = get_resource_name(route)
    mode = data_source["mode"]
    where = data_source.get("where")

    rows = store.list(resource_name)

    if where is None:
        filtered_rows = rows
    else:
        compare_key = where.get("column") or where.get("field")
        expected_value = resolve_where_expected_value(where, path_params, query_params)

        if expected_value is None:
            filtered_rows = []
        else:
            filtered_rows = [
                row for row in rows if str(row.get(compare_key)) == str(expected_value)
            ]

    if mode == "all":
        return filtered_rows

    if mode == "first":
        return filtered_rows[0] if filtered_rows else None

    raise ValueError(f"Unsupported mutable data source mode: {mode}")


def build_data_source_response(
    route: dict,
    config_path: str,
    path_params: dict[str, Any],
    query_params: dict[str, Any],
    store: InMemoryResourceStore,
) -> tuple[bool, Any, int | None, Any]:
    response_config = route.get("response", {})
    data_source = response_config["data_source"]

    if data_source.get("mutable", False):
        result = query_mutable_data_source(
            route=route,
            store=store,
            path_params=path_params,
            query_params=query_params,
        )
    elif data_source["type"] == "csv":
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
    elif data_source["type"] == "json":
        result = query_json_data(
            config_path=config_path,
            relative_json_path=data_source["file"],
            mode=data_source["mode"],
            where=data_source.get("where"),
            path_params=path_params,
            query_params=query_params,
        )
    else:
        raise ValueError(f"Unsupported data source type: {data_source['type']}")

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
    store: InMemoryResourceStore,
) -> tuple[bool, Any, int | None, Any]:
    response_config = route.get("response", {})

    if "data_source" in response_config:
        return build_data_source_response(
            route=route,
            config_path=config_path,
            path_params=path_params,
            query_params=query_params,
            store=store,
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
    app.state.store = InMemoryResourceStore()

    routes = config.get("routes", [])
    grouped_routes = defaultdict(list)

    for route in routes:
        seed_mutable_store_for_route(route, config_path, app.state.store)

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
                    store = request.app.state.store
                    response_config = route.get("response", {})
                    status_code = response_config.get("status_code", 200)

                    data_source = response_config.get("data_source")
                    if data_source and data_source.get("mutable", False):
                        resource_name = get_resource_name(route)
                        key_field = data_source["key_field"]

                        if request.method == "GET":
                            where = data_source.get("where")
                            mode = data_source["mode"]

                            if mode == "all":
                                result = store.list(resource_name)

                                if where is not None:
                                    compare_key = where.get("column") or where.get("field")
                                    expected_value = resolve_where_expected_value(
                                        where,
                                        request.path_params,
                                        dict(request.query_params),
                                    )

                                    if expected_value is None:
                                        result = []
                                    else:
                                        result = [
                                            row
                                            for row in result
                                            if str(row.get(compare_key)) == str(expected_value)
                                        ]

                            elif mode == "first":
                                where = data_source.get("where", {})
                                compare_key = where.get("column") or where.get("field")
                                expected_value = resolve_where_expected_value(
                                    where,
                                    request.path_params,
                                    dict(request.query_params),
                                )

                                rows = store.list(resource_name)

                                if expected_value is None:
                                    result = None
                                else:
                                    result = next(
                                        (
                                            row
                                            for row in rows
                                            if str(row.get(compare_key)) == str(expected_value)
                                        ),
                                        None,
                                    )
                            else:
                                raise ValueError(f"Unsupported mutable mode: {mode}")

                            if data_source["mode"] == "first" and result is None:
                                not_found_status = data_source.get("not_found_status", 404)
                                not_found_body = data_source.get(
                                    "not_found_body", {"detail": "Resource not found"}
                                )
                                return JSONResponse(
                                    content=not_found_body,
                                    status_code=not_found_status,
                                )

                            wrap = data_source.get("wrap")
                            if wrap is not None:
                                result = {wrap: result}

                            return JSONResponse(content=result, status_code=status_code)

                        if request.method == "POST":
                            payload = await request.json()
                            created = store.create(resource_name, payload)
                            return JSONResponse(content=created, status_code=status_code)

                        if request.method == "PUT":
                            payload = await request.json()

                            where = data_source.get("where", {})
                            key_value = resolve_where_expected_value(
                                where,
                                request.path_params,
                                dict(request.query_params),
                            )

                            updated = store.update(
                                resource_name=resource_name,
                                key_field=key_field,
                                key_value=key_value,
                                payload=payload,
                            )

                            if updated is None:
                                return JSONResponse(
                                    content={"detail": "Resource not found"},
                                    status_code=404,
                                )

                            return JSONResponse(content=updated, status_code=status_code)

                        if request.method == "DELETE":
                            where = data_source.get("where", {})
                            key_value = resolve_where_expected_value(
                                where,
                                request.path_params,
                                dict(request.query_params),
                            )

                            deleted = store.delete(
                                resource_name=resource_name,
                                key_field=key_field,
                                key_value=key_value,
                            )

                            if not deleted:
                                return JSONResponse(
                                    content={"detail": "Resource not found"},
                                    status_code=404,
                                )

                            return JSONResponse(
                                content={"deleted": True},
                                status_code=status_code,
                            )

                    found, body, not_found_status, not_found_body = build_response_body(
                        route=route,
                        config_path=_config_path,
                        path_params=request.path_params,
                        query_params=dict(request.query_params),
                        store=store,
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