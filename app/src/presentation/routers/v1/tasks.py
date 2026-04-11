"""Task routes for API v1."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from application import (
    CreateTaskCommand,
    CreateTaskResult,
    CreateTaskUseCase,
    ListTasksItem,
    ListTasksQuery,
    ListTasksResult,
    ListTasksUseCase,
    ProjectNotFoundError,
    TaskNotFoundError,
    TransitionTaskCommand,
    TransitionTaskResult,
    TransitionTaskUseCase,
)
from domain import InvalidTaskTransitionError, ProjectId, TaskId, UserId
from presentation.dependencies import (
    get_create_task_use_case,
    get_list_tasks_use_case,
    get_transition_task_use_case,
)
from presentation.schemas.tasks import (
    CreateTaskRequestSchema,
    TaskListResponseSchema,
    TaskResponseSchema,
    TransitionTaskRequestSchema,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])

CreateTaskUseCaseDependency = Annotated[
    CreateTaskUseCase,
    Depends(get_create_task_use_case),
]

ListTasksUseCaseDependency = Annotated[
    ListTasksUseCase,
    Depends(get_list_tasks_use_case),
]

TransitionTaskUseCaseDependency = Annotated[
    TransitionTaskUseCase,
    Depends(get_transition_task_use_case),
]


def _to_task_response(
    task: CreateTaskResult | ListTasksItem | TransitionTaskResult,
) -> TaskResponseSchema:
    return TaskResponseSchema(
        id=task.id.value,
        project_id=task.project_id.value,
        title=task.title,
        created_by=task.created_by.value,
        description=task.description,
        status=task.status,
        priority=task.priority,
        due_date=task.due_date,
        assigned_to=(None if task.assigned_to is None else task.assigned_to.value),
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def _to_task_list_response(result: ListTasksResult) -> TaskListResponseSchema:
    return TaskListResponseSchema(
        items=[_to_task_response(item) for item in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


def _invalid_transition_response(
    error: InvalidTaskTransitionError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "code": "INVALID_TRANSITION",
            "message": str(error),
            "details": {
                "current_status": error.current_status,
                "target_status": error.target_status,
            },
        },
    )


@router.get("", response_model=TaskListResponseSchema)
def list_tasks(
    use_case: ListTasksUseCaseDependency,
    project_id: UUID,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> TaskListResponseSchema:
    """List tasks for a project using bounded pagination."""
    result = use_case.execute(
        ListTasksQuery(
            project_id=ProjectId(project_id),
            page=page,
            page_size=page_size,
        )
    )
    return _to_task_list_response(result)


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


@router.post("/{task_id}/transition", response_model=TaskResponseSchema)
def transition_task(
    task_id: UUID,
    payload: TransitionTaskRequestSchema,
    use_case: TransitionTaskUseCaseDependency,
) -> TaskResponseSchema | JSONResponse:
    """Transition a task status and record an audit event."""
    command = TransitionTaskCommand(
        task_id=TaskId(task_id),
        target_status=payload.status,
    )

    try:
        result = use_case.execute(command)
    except TaskNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{error.task_id.value}' was not found.",
        ) from error
    except InvalidTaskTransitionError as error:
        return _invalid_transition_response(error)

    return _to_task_response(result)
