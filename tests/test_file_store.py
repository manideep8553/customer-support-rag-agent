import pytest

from backend.enterprise.file_store.service import FileStore


@pytest.mark.asyncio
async def test_file_store_upload_local():
    store = FileStore()
    content = b"hello world, this is a test file"
    stored = await store.upload(
        content=content,
        original_filename="test.txt",
        content_type="text/plain",
        uploaded_by="test-user",
    )
    assert stored.original_filename == "test.txt"
    assert stored.size_bytes == len(content)
    assert stored.backend.value == "local"
    assert stored.stored_path is not None

    # Clean up
    import os
    if os.path.exists(stored.stored_path):
        os.remove(stored.stored_path)


@pytest.mark.asyncio
async def test_file_store_upload_empty():
    store = FileStore()
    stored = await store.upload(
        content=b"",
        original_filename="empty.txt",
    )
    assert stored.size_bytes == 0
    assert stored.original_filename is not None

    import os
    if os.path.exists(stored.stored_path):
        os.remove(stored.stored_path)


@pytest.mark.asyncio
async def test_file_store_delete():
    store = FileStore()
    stored = await store.upload(
        content=b"delete me",
        original_filename="delete.txt",
    )
    result = await store.delete(stored.stored_path)
    assert result is True


@pytest.mark.asyncio
async def test_file_store_get_url():
    store = FileStore()
    stored = await store.upload(
        content=b"url test",
        original_filename="url_test.txt",
    )
    url = await store.get_url(stored.stored_path)
    assert url.startswith("/api/v1/files/") or url.startswith("http")

    import os
    if os.path.exists(stored.stored_path):
        os.remove(stored.stored_path)
