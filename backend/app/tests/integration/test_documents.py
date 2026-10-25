from app.tests.utils import create_user, create_workspace


async def test_pasted_text_and_allowed_file_types_are_accepted(client):
    owner = await create_user(client, "owner")
    workspace = await create_workspace(client, owner)
    base = f"/api/v1/workspaces/{workspace['id']}/documents"

    pasted = await client.post(
        base,
        headers=owner["headers"],
        json={"title": "Pasted notes", "content": "Pasted project context and decisions."},
    )
    assert pasted.status_code == 201, pasted.text
    assert pasted.json()["embedding_status"] == "COMPLETE"

    text_file = await client.post(
        base,
        headers=owner["headers"],
        files={"file": ("../../../notes.txt", b"UTF-8 deployment notes", "text/plain")},
    )
    assert text_file.status_code == 201, text_file.text
    assert text_file.json()["filename"] == "notes.txt"
    markdown_file = await client.post(
        base,
        headers=owner["headers"],
        files={"file": ("runbook.md", b"# Release runbook\nCheck dependencies.", "text/markdown")},
    )
    assert markdown_file.status_code == 201, markdown_file.text
    assert markdown_file.json()["mime_type"] == "text/markdown"

    listed = await client.get(base, headers=owner["headers"])
    assert listed.json()["total"] == 3
    deleted = await client.delete(f"{base}/{markdown_file.json()['id']}", headers=owner["headers"])
    assert deleted.status_code == 204
    missing = await client.get(f"{base}/{markdown_file.json()['id']}", headers=owner["headers"])
    assert missing.status_code == 404


async def test_unsupported_and_oversized_documents_are_rejected_without_records(client):
    owner = await create_user(client, "owner")
    workspace = await create_workspace(client, owner)
    base = f"/api/v1/workspaces/{workspace['id']}/documents"

    unsupported = await client.post(
        base,
        headers=owner["headers"],
        files={"file": ("payload.pdf", b"not supported", "application/pdf")},
    )
    assert unsupported.status_code == 415
    assert ".txt and .md" in unsupported.json()["detail"]

    oversized = await client.post(
        base,
        headers=owner["headers"],
        files={"file": ("large.txt", b"x" * (5 * 1024 * 1024 + 1), "text/plain")},
    )
    assert oversized.status_code == 413
    assert "5 MB" in oversized.json()["detail"]
    listed = await client.get(base, headers=owner["headers"])
    assert listed.json()["total"] == 0
