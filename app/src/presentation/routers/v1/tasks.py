"""Task routes for API v1."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from application import (
    CreateTaskCommand,
    CreateTaskResult,
    CreateTaskUseCase,
    ProjectNotFoundError,
)
from domain import ProjectId, UserId
from presentation.dependencies import get_create_task_use_case
from presentation.schemas.tasks import CreateTaskRequestSchema, TaskResponseSchema

router = APIRouter(prefix="/tasks", tags=["tasks"])

CreateTaskUseCaseDependency = Annotated[
    CreateTaskUseCase,
    Depends(get_create_task_use_case),
]


def _to_task_response(result: CreateTaskResult) -> TaskResponseSchema:
    return TaskResponseSchema(
        id=result.id.value,
        project_id=result.project_id.value,
        title=result.title,
        created_by=result.created_by.value,
        description=result.description,
        status=result.status,
        priority=result.priority,
        due_date=result.due_date,
        assigned_to=(
            None if result.assigned_to is None else result.assigned_to.value
        ),
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@router.post("", response_model=TaskResponseSchema, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: CreateTaskRequestSchema,
    use_case: CreateTaskUseCaseDependency,
) -> TaskResponseSchema:
    """Create a new task inside an existing project."""
    command = CreateTaskCommand(
        project_id=ProjectId(payload.project_id),
        title=payload.title,
        created_by=UserId(payload.created_by),
        description=payload.description,
        priority=payload.priority,
        due_date=payload.due_date,
        assigned_to=(
            None if payload.assigned_to is None else UserId(payload.assigned_to)
        ),
    )

    try:
        result = use_case.execute(command)
    except ProjectNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{error.project_id.value}' was not found.",
        ) from error

    return _to_task_response(result)