"""
Smoke tests for image compression tools.

Usage:
    python tests/smoke.py
"""

from pathlib import Path
import tempfile

from PIL import Image

from src.compress import (
    DEFAULT_TARGET_BYTES,
    compress_batch_tool,
    compress_image_file,
)


def _make_sample(path: Path, size=(800, 600), color=(120, 180, 200)):
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", size, color)
    img.save(path, format="JPEG", quality=95)
    return path


def test_single(tmpdir: Path):
    input_path = tmpdir / "input.jpg"
    output_path = tmpdir / "out.jpg"
    _make_sample(input_path)

    result = compress_image_file(
        input_path=input_path,
        output_path=output_path,
        target_bytes=DEFAULT_TARGET_BYTES,
        output_format="jpeg",
    )
    assert output_path.exists(), "output not created"
    assert result.output_size > 0, "output size invalid"
    assert result.status in {"ok", "partial"}


def test_batch(tmpdir: Path):
    img1 = tmpdir / "a.jpg"
    img2 = tmpdir / "b.png"
    _make_sample(img1)
    _make_sample(img2)

    results = compress_batch_tool(
        paths=[str(img1), str(img2)],
        target_bytes=DEFAULT_TARGET_BYTES,
        output_format="jpeg",
        input_allowlist=[tmpdir],
        output_allowlist=[tmpdir],
    )
    assert len(results) == 2
    for res in results:
        assert res["status"] in {"ok", "partial"}, res
        assert Path(res["output_path"]).exists(), res


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        test_single(tmpdir)
        test_batch(tmpdir)
        print("smoke tests passed")

