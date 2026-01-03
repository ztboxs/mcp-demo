from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, validator

from .compress import (
    DEFAULT_INPUT_DIR,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_TARGET_BYTES,
    SUPPORTED_INPUT_EXTS,
    compress_batch_tool,
    compress_image_tool,
    list_images_resource,
)


class CompressImageRequest(BaseModel):
    path: str
    target_bytes: int = Field(DEFAULT_TARGET_BYTES, gt=0)
    output_format: str = Field("jpeg", description="jpeg|png")

    input_allowlist: Optional[List[str]] = None
    output_allowlist: Optional[List[str]] = None

    @validator("output_format")
    def validate_format(cls, v: str) -> str:
        if v.lower() not in {"jpeg", "jpg", "png"}:
            raise ValueError("output_format must be jpeg or png")
        return v


class CompressBatchRequest(BaseModel):
    paths: List[str]
    target_bytes: int = Field(DEFAULT_TARGET_BYTES, gt=0)
    output_format: str = Field("jpeg", description="jpeg|png")

    input_allowlist: Optional[List[str]] = None
    output_allowlist: Optional[List[str]] = None

    @validator("paths")
    def validate_paths(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("paths cannot be empty")
        return v

    @validator("output_format")
    def validate_format(cls, v: str) -> str:
        if v.lower() not in {"jpeg", "jpg", "png"}:
            raise ValueError("output_format must be jpeg or png")
        return v


class ListImagesResponse(BaseModel):
    images: List[str]


app = FastAPI(title="MCP Image Compression Demo", version="0.1.0")


def _to_paths(values: Optional[List[str]], default: Path) -> List[Path]:
    return [Path(p).expanduser() for p in (values or [str(default)])]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/resources/images", response_model=ListImagesResponse)
def list_images(
    input_allowlist: Optional[List[str]] = None,
):
    allow = _to_paths(input_allowlist, DEFAULT_INPUT_DIR)
    images = list_images_resource(allow)
    return {"images": images}


@app.post("/tools/compress_image")
def compress_image(req: CompressImageRequest):
    result = compress_image_tool(
        path=req.path,
        target_bytes=req.target_bytes,
        output_format=req.output_format,
        input_allowlist=_to_paths(req.input_allowlist, DEFAULT_INPUT_DIR),
        output_allowlist=_to_paths(req.output_allowlist, DEFAULT_OUTPUT_DIR),
    )
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result)
    return result


@app.post("/tools/compress_batch")
def compress_batch(req: CompressBatchRequest):
    results = compress_batch_tool(
        paths=req.paths,
        target_bytes=req.target_bytes,
        output_format=req.output_format,
        input_allowlist=_to_paths(req.input_allowlist, DEFAULT_INPUT_DIR),
        output_allowlist=_to_paths(req.output_allowlist, DEFAULT_OUTPUT_DIR),
    )
    return {"results": results}


# Quick guidance for running:
#   uvicorn src.server:app --reload --port 8000
# Example requests (HTTP):
#   GET  http://127.0.0.1:8000/resources/images
#   POST http://127.0.0.1:8000/tools/compress_image
#        { "path": "/Users/you/Pictures/in/a.jpg", "target_bytes": 10000, "output_format": "jpeg" }

