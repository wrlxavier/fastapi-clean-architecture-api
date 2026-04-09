import pytest

from domain import Project, ProjectId, WorkspaceId


def test_project_requires_non_empty_name() -> None:
    with pytest.raises(ValueError, match="project name must not be empty"):
        Project(id=ProjectId.new(), workspace_id=WorkspaceId.new(), name="   ")
