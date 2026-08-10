# SPDX-License-Identifier: AGPL-3.0-only
"""CLI + MCP transports: --version/--describe/health; stdio default; --sse optional."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import signal
import sys

from .describe import describe
from .health import health
from .version import __version__

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s: %(message)s",
    stream=sys.stderr,
    force=True,
)
logger = logging.getLogger(__name__)


def _env_port(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, str(default)))
    except ValueError:
        return default


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Athena Diary MCP (SanctumOS)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Transport:
  Default `serve`          STDIO for Letta/Cursor local process configs.
  serve --sse              SSE over HTTP for remote or shared Sanctum boxes.
        """,
    )
    parser.add_argument("--version", action="store_true", help="Print version")
    parser.add_argument("--describe", action="store_true", help="SMCP describe JSON")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("health", help="Print health JSON")
    serve_p = sub.add_parser("serve", help="Run MCP server (stdio or --sse)")
    serve_p.add_argument(
        "--sse",
        action="store_true",
        help="Use SSE transport (HTTP). Default is STDIO.",
    )
    serve_p.add_argument(
        "--port",
        type=int,
        default=_env_port("MCP_PORT", 8000),
        help="Port for SSE",
    )
    serve_p.add_argument(
        "--host",
        type=str,
        default=os.environ.get("MCP_HOST", "127.0.0.1"),
        help="Host for SSE",
    )
    serve_p.add_argument(
        "--allow-external",
        action="store_true",
        help="Bind SSE to 0.0.0.0",
    )
    return parser


async def _run_stdio() -> None:  # pragma: no cover - needs live mcp stdio
    from mcp.server.stdio import stdio_server

    from .server import create_server, register_tools

    server = create_server()
    register_tools(server)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


async def _run_sse(args: argparse.Namespace) -> None:  # pragma: no cover - needs mcp+uvicorn
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.requests import Request
    from starlette.responses import Response
    from starlette.routing import Mount, Route

    from .server import create_server, register_tools

    host = "0.0.0.0" if args.allow_external else args.host
    if args.allow_external:
        logger.warning("External connections allowed (--allow-external).")

    server = create_server()
    register_tools(server)
    sse_transport = SseServerTransport("/messages/")

    async def sse_endpoint(request: Request):
        async with sse_transport.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await server.run(
                streams[0],
                streams[1],
                server.create_initialization_options(),
            )
        return Response()

    async def sse_post_endpoint(request: Request):
        return Response(
            "POST to /sse not supported. Use GET /sse.",
            status_code=400,
            media_type="text/plain",
        )

    app = Starlette(
        routes=[
            Route("/sse", sse_endpoint, methods=["GET"]),
            Route("/sse", sse_post_endpoint, methods=["POST"]),
            Mount("/messages/", app=sse_transport.handle_post_message),
        ]
    )

    import uvicorn

    config = uvicorn.Config(app, host=host, port=args.port, log_level="info")
    server_instance = uvicorn.Server(config)

    def on_signal(signum: int, frame: object) -> None:
        logger.info("Shutting down SSE server.")
        server_instance.should_exit = True
        prev = _prev_handlers.get(signum)
        if callable(prev):
            prev(signum, frame)

    _prev_handlers: dict[int, object] = {}
    _prev_handlers[signal.SIGINT] = signal.signal(signal.SIGINT, on_signal)
    _prev_handlers[signal.SIGTERM] = signal.signal(signal.SIGTERM, on_signal)

    logger.info("Starting athena-diary MCP SSE on %s:%s", host, args.port)
    await server_instance.serve()


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(__version__)
        return 0

    if args.describe:
        print(json.dumps(describe(), indent=2))
        return 0

    if args.command == "health":
        print(json.dumps(health(), indent=2))
        return 0

    if args.command == "serve":
        try:
            if getattr(args, "sse", False):
                asyncio.run(_run_sse(args))
            else:
                asyncio.run(_run_stdio())
        except ImportError as e:
            print(f"MCP deps missing: {e}", file=sys.stderr)
            return 2
        except KeyboardInterrupt:
            return 0
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
