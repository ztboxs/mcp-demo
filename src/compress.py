from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Iterable, Literal, Optional

from PIL import Image


DEFAULT_TARGET_BYTES = 10_000
QUALITY_START = 85
QUALITY_MIN = 30
QUALITY_STEP = 5
SCALE_FACTOR = 0.9
MIN_EDGE = 64

DEFAULT_INPUT_DIR = Path("~/Pictures/in").expanduser()
DEFAULT_OUTPUT_DIR = Path("~/Pictures/out").expanduser()

SUPPORTED_INPUT_EXTS = {".jpg", ".jpeg", ".png"}


SupportedFormat = Literal["JPEG", "PNG"]
Status = Literal["ok", "partial"]


@dataclass
class CompressResult:
    status: Status
    input_size: int
    output_size: int
    ratio: float
    output_path: Path
    target_bytes: int
    message: Optional[str] = None


def _normalize_format(fmt: str) -> SupportedFormat:
    norm = fmt.lower()
    if norm in {"jpg", "jpeg"}:
        return "JPEG"
    if norm == "png":
        return "PNG"
    raise ValueError(f"unsupported output format: {fmt}")


def _save_to_bytes(img: Image.Image, fmt: SupportedFormat, quality: Optional[int]) -> bytes:
    """Save image to bytes with given format and quality (quality ignored for PNG)."""
    buffer = BytesIO()
    save_kwargs = {"format": fmt}
    if fmt == "JPEG":
        # Remove metadata implicitly; do not carry EXIF/info
        save_kwargs.update({"quality": quality, "optimize": True, "progressive": False})
    elif fmt == "PNG":
        # PNG quality parameter is not used; optimize to reduce size
        save_kwargs.update({"optimize": True, "compress_level": 9})
    img.save(buffer, **save_kwargs)
    return buffer.getvalue()


def _resize_proportional(img: Image.Image, factor: float) -> Image.Image:
    w, h = img.size
    new_w = max(int(w * factor), 1)
    new_h = max(int(h * factor), 1)
    return img.resize((new_w, new_h), Image.LANCZOS)


def compress_image_file(
    input_path: Path,
    output_path: Path,
    target_bytes: int = DEFAULT_TARGET_BYTES,
    output_format: str = "jpeg",
) -> CompressResult:
    """Best-effort compress an image to target size while keeping aspect ratio."""
    if target_bytes <= 0:
        raise ValueError("target_bytes must be positive")

    fmt = _normalize_format(output_format)
    if not input_path.exists():
        raise FileNotFoundError(f"input not found: {input_path}")

    input_size = input_path.stat().st_size

    with Image.open(input_path) as img:
        # Convert to RGB to ensure consistent save and strip metadata
        base_img = img.convert("RGB")

    quality_steps = list(range(QUALITY_START, QUALITY_MIN - 1, -QUALITY_STEP))

    best_bytes: Optional[bytes] = None
    best_size = float("inf")
    best_img: Optional[Image.Image] = None

    current_img = base_img
    attempt_status: Status = "partial"
    message: Optional[str] = None

    while True:
        for q in quality_steps:
            data = _save_to_bytes(current_img, fmt, q)
            size = len(data)
            if size < best_size:
                best_size = size
                best_bytes = data
                best_img = current_img
            if size <= target_bytes:
                attempt_status = "ok"
                message = None
                break
        if attempt_status == "ok":
            break

        # Scale down proportionally
        w, h = current_img.size
        if max(w, h) <= MIN_EDGE:
            message = "reached minimum edge, best-effort partial result"
            break
        scaled = _resize_proportional(current_img, SCALE_FACTOR)
        if scaled.size == current_img.size:
            message = "cannot scale further, best-effort partial result"
            break
        current_img = scaled

    if best_bytes is None or best_img is None:
        raise RuntimeError("compression failed unexpectedly")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(best_bytes)

    ratio = best_size / input_size if input_size > 0 else 0.0
    return CompressResult(
        status=attempt_status,
        input_size=input_size,
        output_size=int(best_size),
        ratio=ratio,
        output_path=output_path,
        target_bytes=target_bytes,
        message=message,
    )


# --------- Tool-friendly wrappers with path/format checks ----------

def _is_within_allowlist(path: Path, allowlist: Iterable[Path]) -> bool:
    resolved = path.resolve()
    for base in allowlist:
        base_resolved = Path(base).expanduser().resolve()
        if resolved == base_resolved or base_resolved in resolved.parents:
            return True
    return False


def compress_image_tool(
    path: str,
    target_bytes: int = DEFAULT_TARGET_BYTES,
    output_format: str = "jpeg",
    input_allowlist: Optional[Iterable[Path]] = None,
    output_allowlist: Optional[Iterable[Path]] = None,
) -> dict:
    """
    Validate and compress a single image.
    Returns a dict suitable for MCP tool response.
    """
    input_allowlist = list(input_allowlist or [DEFAULT_INPUT_DIR])
    output_allowlist = list(output_allowlist or [DEFAULT_OUTPUT_DIR])

    in_path = Path(path)
    if not _is_within_allowlist(in_path, input_allowlist):
        return {
            "status": "error",
            "message": "input path not in allowlist",
            "input_path": str(in_path),
        }

    if in_path.suffix.lower() not in SUPPORTED_INPUT_EXTS:
        return {
            "status": "error",
            "message": "unsupported input format; only jpeg/png accepted",
            "input_path": str(in_path),
        }

    fmt_norm = output_format.lower()
    if fmt_norm not in {"jpeg", "jpg", "png"}:
        return {
            "status": "error",
            "message": "unsupported output format; use jpeg or png",
            "input_path": str(in_path),
        }

    out_dir = output_allowlist[0]
    out_dir = out_dir.expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_name = in_path.stem + (".png" if fmt_norm == "png" else ".jpg")
    out_path = out_dir / out_name

    if not _is_within_allowlist(out_path, output_allowlist):
        return {
            "status": "error",
            "message": "output path not in allowlist",
            "output_path": str(out_path),
            "input_path": str(in_path),
        }

    try:
        result = compress_image_file(
            input_path=in_path,
            output_path=out_path,
            target_bytes=target_bytes,
            output_format=fmt_norm,
        )
    except FileNotFoundError:
        return {
            "status": "error",
            "message": "input file not found",
            "input_path": str(in_path),
        }
    except ValueError as exc:
        return {
            "status": "error",
            "message": str(exc),
            "input_path": str(in_path),
        }
    except Exception as exc:  # pragma: no cover - unexpected
        return {
            "status": "error",
            "message": f"unexpected error: {exc}",
            "input_path": str(in_path),
        }

    return {
        "status": result.status,
        "input_path": str(in_path),
        "output_path": str(result.output_path),
        "input_size": result.input_size,
        "output_size": result.output_size,
        "ratio": result.ratio,
        "target_bytes": result.target_bytes,
        "message": result.message,
    }


def compress_batch_tool(
    paths: Iterable[str],
    target_bytes: int = DEFAULT_TARGET_BYTES,
    output_format: str = "jpeg",
    input_allowlist: Optional[Iterable[Path]] = None,
    output_allowlist: Optional[Iterable[Path]] = None,
) -> list[dict]:
    """Compress multiple images independently; errors for one do not stop others."""
    results: list[dict] = []
    for p in paths:
        results.append(
            compress_image_tool(
                path=p,
                target_bytes=target_bytes,
                output_format=output_format,
                input_allowlist=input_allowlist,
                output_allowlist=output_allowlist,
            )
        )
    return results


def list_images_resource(
    input_allowlist: Optional[Iterable[Path]] = None,
) -> list[str]:
    """List allowed image files (jpeg/png) under the first allowed input dir."""
    input_allowlist = list(input_allowlist or [DEFAULT_INPUT_DIR])
    root = input_allowlist[0].expanduser()
    if not root.exists():
        return []
    found: list[str] = []
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_INPUT_EXTS:
            if _is_within_allowlist(path, input_allowlist):
                found.append(str(path))
    return found

