import uuid

from sqlalchemy import delete, func, select

from app.db.base import utcnow
from app.db.session import SessionLocal
from app.models.document import Document
from app.models.embedding import Embedding
from app.models.enums import EmbeddingSourceType
from app.services.embeddings import generate_source_embeddings
from app.tests.utils import create_user, create_workspace


async def create_document(client, user, workspace_id, title, content):
    response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/documents",
        headers=user["headers"],
        json={"title": title, "content": content},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_semantic_search_is_workspace_isolated(client):
    owner_a = await create_user(client, "alpha")
    owner_b = await create_user(client, "beta")
    workspace_a = await create_workspace(client, owner_a, "Alpha")
    workspace_b = await create_workspace(client, owner_b, "Beta")
    document_a = await create_document(
        client, owner_a, workspace_a["id"], "Alpha deployment", "Kubernetes deployment checklist for production clusters"
    )
    await create_document(
        client, owner_b, workspace_b["id"], "Beta private deployment", "Kubernetes private deployment instructions for Beta only"
    )

    response = await client.get(
        f"/api/v1/workspaces/{workspace_a['id']}/search",
        headers=owner_a["headers"],
        params={"q": "Kubernetes", "type": "document"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["mode"] == "semantic"
    assert body["items"]
    assert {item["source_id"] for item in body["items"]} == {document_a["id"]}
    assert all("Beta" not in item["title"] for item in body["items"])


async def test_text_search_fallback_when_embeddings_are_unavailable(client):
    owner = await create_user(client, "owner")
    workspace = await create_workspace(client, owner)
    document = await create_document(
        client, owner, workspace["id"], "Zebra runbook", "Zebra deployment fallback instructions"
    )
    with SessionLocal() as db:
        db.execute(delete(Embedding).where(Embedding.workspace_id == uuid.UUID(workspace["id"])))
        db.commit()

    response = await client.get(
        f"/api/v1/workspaces/{workspace['id']}/search",
        headers=owner["headers"],
        params={"q": "Zebra", "type": "document"},
    )
    assert response.status_code == 200
    assert response.json()["mode"] == "text"
    assert response.json()["items"][0]["source_id"] == document["id"]


async def test_mock_embedding_job_is_chunked_dimensional_and_idempotent(client):
    owner = await create_user(client, "owner")
    workspace = await create_workspace(client, owner)
    document = await create_document(
        client, owner, workspace["id"], "Long runbook", "alpha beta gamma " * 500
    )
    workspace_id = uuid.UUID(workspace["id"])
    document_id = uuid.UUID(document["id"])
    with SessionLocal() as db:
        embeddings = db.scalars(
            select(Embedding).where(
                Embedding.workspace_id == workspace_id,
                Embedding.source_id == document_id,
            )
        ).all()
        assert len(embeddings) == 2
        assert all(len(item.embedding) == 1536 for item in embeddings)

    result = generate_source_embeddings(
        EmbeddingSourceType.DOCUMENT, document_id, workspace_id
    )
    assert result == {"status": "complete", "chunks": 2}
    with SessionLocal() as db:
        count = db.scalar(
            select(func.count()).select_from(Embedding).where(
                Embedding.workspace_id == workspace_id,
                Embedding.source_id == document_id,
            )
        )
        assert count == 2
        stored = db.scalar(select(Document).where(Document.id == document_id))
        stored.deleted_at = utcnow()
        db.commit()
    skipped = generate_source_embeddings(
        EmbeddingSourceType.DOCUMENT, document_id, workspace_id
    )
    assert skipped == {"status": "skipped", "chunks": 0}


async def test_text_fallback_is_workspace_isolated_and_retrieves_only_matches(client):
    owner_a = await create_user(client, "alpha")
    owner_b = await create_user(client, "beta")
    workspace_a = await create_workspace(client, owner_a, "Alpha")
    workspace_b = await create_workspace(client, owner_b, "Beta")
    matching = await create_document(
        client, owner_a, workspace_a["id"], "Alpha Quasar runbook", "Quasar deployment instructions for Alpha"
    )
    await create_document(
        client, owner_a, workspace_a["id"], "Unrelated Alpha note", "Billing reconciliation without the query term"
    )
    await create_document(
        client, owner_b, workspace_b["id"], "Beta private Quasar", "Quasar deployment instructions private to Beta"
    )
    with SessionLocal() as db:
        db.execute(delete(Embedding))
        db.commit()

    response = await client.get(
        f"/api/v1/workspaces/{workspace_a['id']}/search",
        headers=owner_a["headers"],
        params={"q": "Quasar", "type": "document"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["mode"] == "text"
    assert len(response.json()["items"]) == 1
    assert response.json()["items"][0]["source_id"] == matching["id"]
    assert response.json()["items"][0]["search_mode"] == "text"
    assert "Beta" not in response.text
