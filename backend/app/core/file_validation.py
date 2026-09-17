"""Upload content validation — magic-byte sniffing for image uploads.

Never trust the client-supplied Content-Type: it is trivially spoofable and
the stored bytes are later served back to browsers. Validate the actual
file signature and serve with X-Content-Type-Options: nosniff so browsers
cannot MIME-sniff HTML/JS out of an "image"."""
from __future__ import annotations

from typing import Any

_MAGIC: list[tuple[bytes, str]] = [
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"\x00\x00\x01\x00", "image/x-icon"),  # ICO
]


def sniff_image_mime(content: bytes) -> str | None:
    """Return the image MIME type implied by magic bytes, or None."""
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    for magic, mime in _MAGIC:
        if content.startswith(magic):
            return mime
    return None


# Response headers for serving stored upload bytes safely.
NOSNIFF_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    # SVG mitigation: belt-and-suspenders in case a legacy SVG is stored —
    # scripts inside the response cannot execute.
    "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'",
}


# Upload size ceilings (bytes). mzXML/mzML files are legitimately large;
# everything else should be small.
MAX_MZXML_BYTES = 200 * 1024 * 1024      # 200 MB per mzXML/mzML file
MAX_CSV_BYTES = 50 * 1024 * 1024         # 50 MB for CSV/training data
MAX_METH_BYTES = 5 * 1024 * 1024         # 5 MB for .meth instrument files
MAX_CHROMATOGRAM_BYTES = 10 * 1024 * 1024  # 10 MB for chromatogram CSV/TXT


async def read_upload_limited(file: Any, max_bytes: int) -> bytes:
    """Read an UploadFile with a hard size cap.

    Reads at most ``max_bytes + 1`` bytes so oversized bodies are rejected
    (HTTP 413) without buffering the entire payload into memory.
    """
    from fastapi import HTTPException, status

    contents = await file.read(max_bytes + 1)
    if len(contents) > max_bytes:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            f"File too large (max {max_bytes // (1024 * 1024)} MB)",
        )
    return contents
