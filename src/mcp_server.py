"""
MCP Server for image compression.

Run with:
    python -m src.mcp_server

Or in Cursor/Claude Desktop config:
    "command": "python",
    "args": ["-m", "src.mcp_server"]
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    Resource,
    ResourceContents,
    TextResourceContents,
)

from src.compress import (
    compress_image_tool,
    compress_batch_tool,
    list_images_resource,
    DEFAULT_INPUT_DIR,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_TARGET_BYTES,
)

server = Server("mcp-img-compress")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Expose available tools to MCP clients."""
    return [
        Tool(
            name="compress_image",
            description="压缩单张图片到目标大小（默认10KB），保持宽高比，输出JPEG（非webp），去除EXIF。",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "图片路径（必须在允许目录内）",
                    },
                    "target_bytes": {
                        "type": "integer",
                        "description": "目标大小（字节），默认10000",
                        "default": DEFAULT_TARGET_BYTES,
                    },
                    "output_format": {
                        "type": "string",
                        "enum": ["jpeg", "png"],
                        "description": "输出格式，默认jpeg",
                        "default": "jpeg",
                    },
                    "input_dir": {
                        "type": "string",
                        "description": "输入目录（覆盖默认 ~/Pictures/in）",
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "输出目录（覆盖默认 ~/Pictures/out）",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="compress_batch",
            description="批量压缩多张图片，逐个处理，单个失败不影响其他。",
            inputSchema={
                "type": "object",
                "properties": {
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "图片路径列表",
                    },
                    "target_bytes": {
                        "type": "integer",
                        "description": "目标大小（字节），默认10000",
                        "default": DEFAULT_TARGET_BYTES,
                    },
                    "output_format": {
                        "type": "string",
                        "enum": ["jpeg", "png"],
                        "description": "输出格式，默认jpeg",
                        "default": "jpeg",
                    },
                    "input_dir": {
                        "type": "string",
                        "description": "输入目录（覆盖默认）",
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "输出目录（覆盖默认）",
                    },
                },
                "required": ["paths"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool invocations."""
    input_dir = Path(arguments.get("input_dir", str(DEFAULT_INPUT_DIR))).expanduser()
    output_dir = Path(arguments.get("output_dir", str(DEFAULT_OUTPUT_DIR))).expanduser()
    target_bytes = arguments.get("target_bytes", DEFAULT_TARGET_BYTES)
    output_format = arguments.get("output_format", "jpeg")

    if name == "compress_image":
        path = arguments.get("path", "")
        result = compress_image_tool(
            path=path,
            target_bytes=target_bytes,
            output_format=output_format,
            input_allowlist=[input_dir],
            output_allowlist=[output_dir],
        )
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "compress_batch":
        paths = arguments.get("paths", [])
        results = compress_batch_tool(
            paths=paths,
            target_bytes=target_bytes,
            output_format=output_format,
            input_allowlist=[input_dir],
            output_allowlist=[output_dir],
        )
        return [TextContent(type="text", text=json.dumps(results, ensure_ascii=False, indent=2))]

    else:
        return [TextContent(type="text", text=json.dumps({"error": f"unknown tool: {name}"}))]


@server.list_resources()
async def list_resources() -> list[Resource]:
    """Expose resources (image list)."""
    return [
        Resource(
            uri="images://list",
            name="可压缩图片列表",
            description="列出允许目录下的 JPEG/PNG 图片",
            mimeType="application/json",
        ),
    ]


@server.read_resource()
async def read_resource(uri: str) -> ResourceContents:
    """Return resource contents."""
    if uri == "images://list":
        images = list_images_resource()
        return TextResourceContents(
            uri=uri,
            mimeType="application/json",
            text=json.dumps(images, ensure_ascii=False, indent=2),
        )
    raise ValueError(f"unknown resource: {uri}")


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())

