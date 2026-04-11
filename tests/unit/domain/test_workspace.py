import pytest

from domain import UserId, Workspace, WorkspaceId


def test_workspace_requires_non_empty_name() -> None:
    with pytest.raises(ValueError, match="workspace name must not be empty"):
        Workspace(id=WorkspaceId.new(), name="   ", owner_id=UserId.new())
