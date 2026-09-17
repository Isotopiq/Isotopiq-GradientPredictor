"""Unit tests for upload content validation (magic bytes, size caps)."""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.core.file_validation import (
    read_upload_limited,
    sniff_image_mime,
)

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32
GIF87 = b"GIF87a" + b"\x00" * 32
GIF89 = b"GIF89a" + b"\x00" * 32
WEBP = b"RIFF" + b"\x24\x00\x00\x00" + b"WEBP" + b"\x00" * 32
ICO = b"\x00\x00\x01\x00" + b"\x00" * 32
SVG = b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'


class TestSniffImageMime:
    @pytest.mark.parametrize(
        "content,expected",
        [
            (PNG, "image/png"),
            (JPEG, "image/jpeg"),
            (GIF87, "image/gif"),
            (GIF89, "image/gif"),
            (WEBP, "image/webp"),
            (ICO, "image/x-icon"),
        ],
    )
    def test_valid_magic_bytes(self, content, expected):
        assert sniff_image_mime(content) == expected

    def test_svg_rejected(self):
        # SVG is scriptable — must never pass image validation
        assert sniff_image_mime(SVG) is None

    def test_html_rejected(self):
        assert sniff_image_mime(b"<html><body>not an image</body></html>") is None

    def test_garbage_rejected(self):
        assert sniff_image_mime(b"\x00" * 64) is None
        assert sniff_image_mime(b"") is None
        assert sniff_image_mime(b"PNG") is None  # truncated magic


class _FakeUpload:
    """Minimal UploadFile stand-in honouring the size argument."""

    def __init__(self, content: bytes):
        self._buf = content

    async def read(self, size: int = -1) -> bytes:
        return self._buf if size < 0 else self._buf[:size]


class TestReadUploadLimited:
    @pytest.mark.asyncio
    async def test_under_limit(self):
        data = b"x" * 1024
        assert await read_upload_limited(_FakeUpload(data), 2048) == data

    @pytest.mark.asyncio
    async def test_exactly_at_limit(self):
        data = b"x" * 2048
        assert await read_upload_limited(_FakeUpload(data), 2048) == data

    @pytest.mark.asyncio
    async def test_over_limit_raises_413(self):
        data = b"x" * 4096
        with pytest.raises(HTTPException) as exc_info:
            await read_upload_limited(_FakeUpload(data), 2048)
        assert exc_info.value.status_code == 413

    @pytest.mark.asyncio
    async def test_huge_body_not_fully_buffered(self):
        # A 300 MB body must be rejected after reading only cap+1 bytes.
        read_sizes: list[int] = []

        class TrackingUpload(_FakeUpload):
            async def read(self, size: int = -1) -> bytes:
                read_sizes.append(size)
                return await super().read(size)

        with pytest.raises(HTTPException):
            await read_upload_limited(TrackingUpload(b"y" * 300_000_000), 1024)
        assert read_sizes == [1025]  # capped read, never a full .read()
