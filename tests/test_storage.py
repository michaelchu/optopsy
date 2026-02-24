"""Tests for optopsy.ui.storage — LocalStorageClient."""

import asyncio

import pytest

pytest.importorskip("chainlit", reason="chainlit not installed")

from optopsy.ui.storage import LocalStorageClient


@pytest.fixture
def storage(tmp_path):
    return LocalStorageClient(storage_dir=tmp_path)


class TestUploadFile:
    def test_upload_bytes(self, storage, tmp_path):
        async def _run():
            result = await storage.upload_file(
                "a/b/file.json", b'{"x":1}', mime="application/json"
            )
            assert result["object_key"] == "a/b/file.json"
            assert "/optopsy-storage/" in result["url"]
            assert (tmp_path / "a" / "b" / "file.json").read_bytes() == b'{"x":1}'

        asyncio.run(_run())

    def test_upload_string(self, storage, tmp_path):
        async def _run():
            await storage.upload_file("chart.json", '{"data":[]}')
            assert (tmp_path / "chart.json").read_text() == '{"data":[]}'

        asyncio.run(_run())

    def test_overwrite_false_raises(self, storage):
        async def _run():
            await storage.upload_file("f.txt", b"first")
            with pytest.raises(FileExistsError):
                await storage.upload_file("f.txt", b"second", overwrite=False)

        asyncio.run(_run())

    def test_overwrite_true_replaces(self, storage, tmp_path):
        async def _run():
            await storage.upload_file("f.txt", b"first")
            await storage.upload_file("f.txt", b"second", overwrite=True)
            assert (tmp_path / "f.txt").read_bytes() == b"second"

        asyncio.run(_run())


class TestDeleteFile:
    def test_delete_existing(self, storage, tmp_path):
        async def _run():
            await storage.upload_file("del.txt", b"x")
            result = await storage.delete_file("del.txt")
            assert result is True
            assert not (tmp_path / "del.txt").exists()

        asyncio.run(_run())

    def test_delete_nonexistent(self, storage):
        async def _run():
            result = await storage.delete_file("nope.txt")
            assert result is False

        asyncio.run(_run())


class TestGetReadUrl:
    def test_url_format(self, storage):
        async def _run():
            url = await storage.get_read_url("user/elem/chart")
            assert url == "/optopsy-storage/user/elem/chart"

        asyncio.run(_run())

    def test_traversal_rejected(self, storage):
        async def _run():
            with pytest.raises(ValueError, match="traversal"):
                await storage.get_read_url("../../etc/passwd")

        asyncio.run(_run())


class TestPathTraversal:
    def test_upload_traversal(self, storage):
        async def _run():
            with pytest.raises(ValueError, match="traversal"):
                await storage.upload_file("../../etc/passwd", b"bad")

        asyncio.run(_run())

    def test_delete_traversal(self, storage):
        async def _run():
            with pytest.raises(ValueError, match="traversal"):
                await storage.delete_file("../../../etc/shadow")

        asyncio.run(_run())
