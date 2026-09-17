"""Path-traversal regression tests for the model artifact registry."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.config import settings
from app.core.ml.registry import _artifact_path


class TestArtifactPathConfinement:
    def test_normal_inputs_confined(self):
        p = _artifact_path("C18", "sig_abc123", 1)
        assert p.parent == Path(settings.model_storage_path).resolve()
        assert p.name == "C18_sig_abc123_v1.pkl"

    @pytest.mark.parametrize("bad", [
        "../escape",
        "../../etc/passwd",
        "..\\..\\windows",
        "a/b/c",
        "/absolute/path",
        "..",
        "....//....",
        "C:\\Windows\\System32",
        "sub/dir",
        "a\x00b",  # null byte
    ])
    def test_traversal_inputs_cannot_escape(self, bad):
        p = _artifact_path(bad, "sig", 1)
        # Either it resolves inside the storage dir, or it raises — either
        # is a safe outcome; it must never point outside the root.
        assert Path(settings.model_storage_path).resolve() in p.parents \
            or p.parent == Path(settings.model_storage_path).resolve()
        assert "/" not in p.name and "\\" not in p.name

    @pytest.mark.parametrize("bad", ["../x", "a\\b", "x/y", ".."])
    def test_traversal_signatures_cannot_escape(self, bad):
        p = _artifact_path("C18", bad, 1)
        storage = Path(settings.model_storage_path).resolve()
        assert p.parent == storage

    def test_long_inputs_truncated(self):
        p = _artifact_path("X" * 500, "Y" * 500, 1)
        storage = Path(settings.model_storage_path).resolve()
        assert p.parent == storage
        assert len(p.name) < 200
