from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel

from .config import load_mcp_config, load_runtime_config
from .digest import build_bundle_for_date, digest_path_for_date
from .normalise import iter_clean_records
from .status import get_pipeline_status


SUPPORTED_PROTOCOL_VERSIONS = ["2025-11-25", "2025-03-26"]
DEFAULT_PROTOCOL_VERSION = SUPPORTED_PROTOCOL_VERSIONS[0]
_clients: dict[str, asyncio.Queue[str]] = {}


class JsonRpcRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: int | str | None = None
    method: str
    params: dict[str, Any] = {}


class JsonRpcResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: int | str | None = None
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def _serialize_tool_result_text(result: Any) -> str:
    if isinstance(result, str):
        return result
    return f"{json.dumps(result, indent=2, sort_keys=True)}\n"


def _tool_list() -> list[dict[str, Any]]:
    return [
        {
            "name": "argus_pipeline_status",
            "description": "Get last run status and current-day artifact counts",
            "inputSchema": {
                "type": "object",
                "properties": {"date": {"type": "string"}},
                "additionalProperties": False,
            },
        },
        {
            "name": "argus_list_items",
            "description": "List normalized newsletter items for a date",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "source": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 200},
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "argus_get_digest",
            "description": "Get digest markdown for a date",
            "inputSchema": {
                "type": "object",
                "properties": {"date": {"type": "string"}},
                "additionalProperties": False,
            },
        },
        {
            "name": "argus_get_bundle",
            "description": "Get LLM-ready structured digest bundle for a date",
            "inputSchema": {
                "type": "object",
                "properties": {"date": {"type": "string"}},
                "additionalProperties": False,
            },
        },
    ]


def _run_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    runtime = load_runtime_config()
    date = arguments.get("date")

    if name == "argus_pipeline_status":
        status = get_pipeline_status(date=date, timezone=runtime.timezone)
        return {
            "date": status.date,
            "last_run": status.last_run,
            "raw_count": status.raw_count,
            "clean_count": status.clean_count,
            "digest_exists": status.digest_exists,
            "digest_path": status.digest_path,
        }

    if name == "argus_list_items":
        target_date = date or datetime.now(runtime.timezone).date().isoformat()
        source = str(arguments.get("source", "")).strip().lower()
        limit = int(arguments.get("limit", 50))
        rows = iter_clean_records(target_date)
        if source:
            rows = [row for row in rows if str(row.get("source", "")).lower() == source]
        return {"date": target_date, "count": len(rows[:limit]), "items": rows[:limit]}

    if name == "argus_get_digest":
        target_date = date or datetime.now(runtime.timezone).date().isoformat()
        path = digest_path_for_date(target_date)
        if not path.exists():
            return {"date": target_date, "exists": False, "digest": ""}
        return {"date": target_date, "exists": True, "digest": path.read_text(encoding="utf-8")}

    if name == "argus_get_bundle":
        target_date = date or datetime.now(runtime.timezone).date().isoformat()
        return build_bundle_for_date(target_date)

    raise ValueError(f"Unknown tool: {name}")


def _require_auth(authorization: str | None = Header(default=None)) -> None:
    cfg = load_mcp_config()
    expected = f"Bearer {cfg.auth_token}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


async def _event_stream(client_id: str) -> AsyncIterator[str]:
    queue = _clients[client_id]
    try:
        yield _sse("endpoint", {"message_url": f"/messages?client_id={client_id}"})
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=15)
                yield msg
            except TimeoutError:
                yield _sse("ping", {"at": datetime.utcnow().isoformat()})
    finally:
        _clients.pop(client_id, None)


def _open_sse_stream() -> StreamingResponse:
    client_id = str(uuid.uuid4())
    _clients[client_id] = asyncio.Queue()
    return StreamingResponse(_event_stream(client_id), media_type="text/event-stream")


async def _handle_rpc(request: JsonRpcRequest) -> JsonRpcResponse:
    if request.method == "initialize":
        requested = request.params.get("protocolVersion")
        protocol = requested if requested in SUPPORTED_PROTOCOL_VERSIONS else DEFAULT_PROTOCOL_VERSION
        return JsonRpcResponse(
            id=request.id,
            result={
                "protocolVersion": protocol,
                "serverInfo": {"name": "argus-mcp", "version": "0.1.0"},
                "capabilities": {"tools": {"listChanged": False}},
            },
        )

    if request.method == "tools/list":
        return JsonRpcResponse(id=request.id, result={"tools": _tool_list()})

    if request.method == "tools/call":
        name = str(request.params.get("name", ""))
        arguments = request.params.get("arguments", {})
        if not isinstance(arguments, dict):
            return JsonRpcResponse(id=request.id, error={"code": -32602, "message": "arguments must be an object"})
        try:
            result = _run_tool(name, arguments)
            return JsonRpcResponse(
                id=request.id,
                result={"content": [{"type": "text", "text": _serialize_tool_result_text(result)}]},
            )
        except Exception as exc:  # noqa: BLE001
            return JsonRpcResponse(id=request.id, error={"code": 500, "message": str(exc)})

    return JsonRpcResponse(id=request.id, error={"code": -32601, "message": "Method not found"})


def create_app() -> FastAPI:
    app = FastAPI(title="argus-mcp", version="0.1.0")

    @app.get("/health")
    def health(_: None = Depends(_require_auth)) -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/")
    async def root(request: JsonRpcRequest, _: None = Depends(_require_auth)) -> JSONResponse:
        response = await _handle_rpc(request)
        return JSONResponse(content=response.model_dump())

    @app.get("/sse")
    async def sse_endpoint(_: None = Depends(_require_auth)) -> StreamingResponse:
        return _open_sse_stream()

    @app.post("/sse", response_model=None)
    async def sse_post_compat(request: Request, _: None = Depends(_require_auth)) -> Response:
        body = await request.body()
        if not body:
            return _open_sse_stream()
        payload = json.loads(body.decode("utf-8"))
        rpc_request = JsonRpcRequest.model_validate(payload)
        response = await _handle_rpc(rpc_request)
        return JSONResponse(content=response.model_dump())

    @app.post("/messages")
    async def messages_endpoint(
        request: JsonRpcRequest,
        client_id: str = Query(...),
        _: None = Depends(_require_auth),
    ) -> JSONResponse:
        queue = _clients.get(client_id)
        if queue is None:
            return JSONResponse(status_code=404, content={"error": "unknown client_id"})
        response = await _handle_rpc(request)
        await queue.put(_sse("message", response.model_dump()))
        return JSONResponse(status_code=202, content={"queued": True})

    return app


app = create_app()
