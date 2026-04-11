"""Seed deterministic data for local load-testing runs."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select

from infrastructure import create_session_factory
from infrastructure.database.models import ProjectModel, TaskModel, WorkspaceModel

DEFAULT_OWNER_ID = UUID("00000000-0000-0000-0000-000000000101")
DEFAULT_ASSIGNEE_ID = UUID("00000000-0000-0000-0000-000000000102")
DEFAULT_WORKSPACE_ID = UUID("00000000-0000-0000-0000-000000000201")
DEFAULT_PROJECT_ID = UUID("00000000-0000-0000-0000-000000000301")
DEFAULT_SEED_TASK_COUNT = 25


def _get_uuid_setting(name: str, default: UUID) -> UUID:
    raw_value = os.getenv(name)
    return default if raw_value is None else UUID(raw_value)


def _get_int_setting(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    return default if raw_value is None else int(raw_value)


def main() -> None:
    """Create a stable workspace/project fixture for local load tests."""
    owner_id = _get_uuid_setting("LOAD_TEST_USER_ID", DEFAULT_OWNER_ID)
    assignee_id = _get_uuid_setting("LOAD_TEST_ASSIGNEE_ID", DEFAULT_ASSIGNEE_ID)
    workspace_id = _get_uuid_setting("LOAD_TEST_WORKSPACE_ID", DEFAULT_WORKSPACE_ID)
    project_id = _get_uuid_setting("LOAD_TEST_PROJECT_ID", DEFAULT_PROJECT_ID)
    seed_task_count = _get_int_setting(
        "LOAD_TEST_SEED_TASK_COUNT",
        DEFAULT_SEED_TASK_COUNT,
    )
    timestamp = datetime.now(UTC)
    session_factory = create_session_factory()

    with session_factory.begin() as session:
        workspace = session.get(WorkspaceModel, workspace_id)
        if workspace is None:
            session.add(
                WorkspaceModel(
                    id=workspace_id,
                    name="Load Test Workspace",
                    owner_id=owner_id,
                    description="Deterministic fixture used by local load tests.",
                    created_at=timestamp,
                )
            )

        project = session.get(ProjectModel, project_id)
        if project is None:
            session.add(
                ProjectModel(
                    id=project_id,
                    workspace_id=workspace_id,
                    name="Load Test Project",
                    description="Synthetic project reserved for k6 scenarios.",
                    created_at=timestamp,
                )
            )

        existing_task_count = session.scalar(
            select(func.count())
            .select_from(TaskModel)
            .where(TaskModel.project_id == project_id)
        )
        existing_task_count = 0 if existing_task_count is None else existing_task_count

        tasks_to_create = max(seed_task_count - existing_task_count, 0)
        for index in range(
            existing_task_count + 1,
            existing_task_count + tasks_to_create + 1,
        ):
            session.add(
                TaskModel(
                    id=UUID(f"00000000-0000-0000-0000-{index:012d}"),
                    project_id=project_id,
                    title=f"Load test seed task {index:03d}",
                    created_by=owner_id,
                    description="Synthetic task used to warm the list endpoint.",
                    status="todo",
                    priority="medium",
                    due_date=None,
                    assigned_to=None,
                    created_at=timestamp,
                    updated_at=timestamp,
                )
            )

    print(
        json.dumps(
            {
                "load_test_user_id": str(owner_id),
                "load_test_assignee_id": str(assignee_id),
                "load_test_workspace_id": str(workspace_id),
                "load_test_project_id": str(project_id),
                "seed_task_count": max(seed_task_count, existing_task_count),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
