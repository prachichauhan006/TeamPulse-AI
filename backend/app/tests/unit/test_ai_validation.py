import uuid

import pytest
from pydantic import ValidationError

from app.services.ai.mock import MockAIProvider
from app.services.ai.schemas import AIPlanOutput, AIWorkspaceUser, EmbeddingVector
from app.services.ai_validation import AIResponseValidationError, validate_plan_output

USERS = [AIWorkspaceUser(id=uuid.UUID(int=1), full_name="Workspace Owner")]
BRIEF = "Create a structured launch plan with owners, dependencies, and review checkpoints."


def test_strict_ai_schema_rejects_unexpected_fields():
    plan = MockAIProvider().generate_plan(BRIEF, USERS)
    payload = plan.model_dump()
    payload["untrusted_extra_field"] = "not allowed"
    with pytest.raises(ValidationError):
        AIPlanOutput.model_validate(payload)


def test_embedding_schema_rejects_wrong_dimensions():
    with pytest.raises(ValidationError):
        EmbeddingVector(values=[0.1] * 1535)


def test_unknown_dependency_reference_is_rejected_before_saving():
    plan = MockAIProvider().generate_plan(BRIEF, USERS)
    plan.tasks[0].depends_on = ["missing-task"]
    with pytest.raises(AIResponseValidationError):
        validate_plan_output(plan, USERS)


def test_circular_ai_dependencies_are_rejected_before_saving():
    plan = MockAIProvider().generate_plan(BRIEF, USERS)
    plan.tasks[0].depends_on = ["task-2"]
    with pytest.raises(AIResponseValidationError):
        validate_plan_output(plan, USERS)


def test_cross_workspace_ai_assignee_is_rejected():
    plan = MockAIProvider().generate_plan(BRIEF, USERS)
    plan.tasks[0].suggested_assignee_id = uuid.uuid4()
    with pytest.raises(AIResponseValidationError):
        validate_plan_output(plan, USERS)
